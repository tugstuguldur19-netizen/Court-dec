"""The spell-checking engine.

It uses Hunspell dictionaries (the same .aff/.dic files LibreOffice uses),
read by spylls, a pure-Python Hunspell implementation. Nothing here touches
the network.
"""

import itertools
import os
import threading
from dataclasses import dataclass

from . import text as T

# Dictionaries are matched to an alphabet by their language code.
_CYRILLIC_LANGS = {"mn", "ru", "uk", "be", "bg", "kk", "ky", "sr", "mk", "tg", "tt", "ba"}

# Mongolian case endings that are written after a hyphen when attached to a
# name or abbreviation: "Дорж-д", "Б.Болд-ын", "ХХК-ийн".
CASE_ENDINGS = frozenset("""
    н ын ийн ний ны ий гийн гын
    г ыг ийг
    д т нд ад эд од өд
    аас ээс оос өөс иас иос наас нээс ноос нөөс гаас гээс гоос гөөс
    аар ээр оор өөр иар иор наар нээр ноор нөөр гаар гээр гоор гөөр
    тай тэй той
    руу рүү луу лүү
    аа ээ оо өө гаа гээ ыгаа ийгээ даа дээ доо дөө таа тээ тоо төө
    аасаа ээсээ оосоо өөсөө тайгаа тэйгээ тойгоо аараа ээрээ оороо өөрөө
    ынх ийнх ийнхан ынхан нар ууд үүд
""".split())


@dataclass
class Options:
    ignore_uppercase: bool = True
    ignore_with_digits: bool = True
    check_latin: bool = True


def find_dictionaries(*folders):
    """Return [(lang, path_without_extension)] for every .aff/.dic pair found.

    Mongolian comes first, then English, then anything else alphabetically.
    A dictionary in a later folder with the same name overrides an earlier one.
    """
    found = {}
    for folder in folders:
        if not folder or not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            stem, ext = os.path.splitext(name)
            if ext.lower() == ".aff" and os.path.isfile(os.path.join(folder, stem + ".dic")):
                found[stem] = os.path.join(folder, stem)
    order = {"mn": 0, "en": 1}
    stems = sorted(found, key=lambda s: (order.get(_lang(s), 2), s))
    return [(s, found[s]) for s in stems]


def find_wordlists(*folders):
    """Return paths of plain-text word lists (*.txt, one word per line)."""
    paths = []
    for folder in folders:
        if not folder or not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".txt") and not name.upper().startswith(("README", "LICENSE")):
                paths.append(os.path.join(folder, name))
    return paths


def _lang(stem):
    return stem.split("_")[0].split("-")[0].lower()


def script_of_dictionary(stem):
    return "cyrl" if _lang(stem) in _CYRILLIC_LANGS else "latn"


def _read_words(path):
    """Read a word list; accepts UTF-8 or UTF-16 (Office's CUSTOM.DIC format)."""
    with open(path, "rb") as f:
        raw = f.read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        data = raw.decode("utf-16")
    else:
        data = raw.decode("utf-8-sig", errors="replace")
    return [w.strip() for w in data.splitlines() if w.strip() and not w.startswith("#")]


class WordSet:
    """Accepted words, matched the way Hunspell matches dictionary words: a
    lowercase entry also accepts Capitalized and UPPERCASE forms, an entry
    with capitals also accepts its UPPERCASE form."""

    def __init__(self, words=()):
        self._exact = set()
        self._lower = set()
        self._upper = set()
        for w in words:
            self.add(w)

    def add(self, word):
        self._exact.add(word)
        self._upper.add(word.upper())
        if word == word.lower():
            self._lower.add(word)

    def __contains__(self, word):
        if word in self._exact:
            return True
        if word.lower() in self._lower:
            return word == word.capitalize() or word == word.upper()
        return word.isupper() and word in self._upper

    def __len__(self):
        return len(self._exact)


class Speller:
    """Checks words against all loaded dictionaries.

    The personal dictionary is a UTF-8 text file with one word per line, so it
    can be edited by hand, shared between colleagues, or replaced by a list of
    legal terms.
    """

    def __init__(self, dictionary_folders, personal_path=None, options=None):
        self.dictionary_folders = list(dictionary_folders)
        self.personal_path = personal_path
        self.options = options or Options()
        self.dictionaries = []  # [(stem, script, spylls Dictionary)]
        self.extra = WordSet()
        self.personal = WordSet()
        self.ignored = set()
        self._cache = {}
        self._lock = threading.RLock()

    # ---------- loading ----------

    def load(self, progress=None):
        """Load every dictionary found. Takes several seconds for Mongolian."""
        from spylls.hunspell import Dictionary

        pairs = find_dictionaries(*self.dictionary_folders)
        loaded = []
        for stem, path in pairs:
            if progress:
                progress(stem)
            d = Dictionary.from_files(path)
            # Suggestions try inserting and replacing every TRY character.
            # Capitals there only double the work: capitalisation is handled
            # separately by Hunspell's case logic.
            if d.aff.TRY:
                d.aff.TRY = "".join(c for c in d.aff.TRY if not c.isupper())
            loaded.append((stem, script_of_dictionary(stem), d))
        for path in find_wordlists(*self.dictionary_folders):
            for w in _read_words(path):
                self.extra.add(w)
        if self.personal_path and os.path.isfile(self.personal_path):
            for w in _read_words(self.personal_path):
                self.personal.add(w)
        with self._lock:
            self.dictionaries = loaded
            self._cache.clear()
        return [stem for stem, _, _ in loaded]

    @property
    def languages(self):
        return [stem for stem, _, _ in self.dictionaries]

    def _for_script(self, script):
        return [d for _, s, d in self.dictionaries if s == script]

    # ---------- checking ----------

    def is_correct(self, word):
        with self._lock:
            hit = self._cache.get(word)
            if hit is None:
                hit = self._check(word)
                self._cache[word] = hit
            return hit

    def _accepted(self, word):
        return word in self.ignored or word in self.personal or word in self.extra

    def _check(self, word):
        if self._accepted(word):
            return True
        script = T.script_of(word)
        if script is None:
            return True  # no dictionary for this alphabet: don't flag it
        if script == "latn" and not self.options.check_latin:
            return True
        dicts = self._for_script(script)
        if not dicts:
            return True
        if any(d.lookup(word) for d in dicts):
            return True
        parts = T.split_joined(word)
        if len(parts) > 1:
            return all(self._part_ok(parts, i, dicts) for i in range(len(parts)))
        return False

    def _part_ok(self, parts, i, dicts):
        part = parts[i]
        if self._accepted(part) or not any(ch.isalpha() for ch in part):
            return True
        prev = parts[i - 1] if i else ""
        # "ХХК-ийн", "2024-ний": a case ending after an abbreviation or number.
        if prev and (prev.isupper() or prev.isdigit()) and part.islower() and len(part) <= 7:
            return True
        if prev[:1].isupper() and part in CASE_ENDINGS:
            return True
        if prev.isdigit() and not self.options.ignore_with_digits:
            return True
        return any(d.lookup(part) for d in dicts)

    def misspellings(self, text):
        """Return [(start, end, word)] for every misspelled word in text."""
        out = []
        for start, end, word in T.words(
            text,
            ignore_uppercase=self.options.ignore_uppercase,
            ignore_with_digits=self.options.ignore_with_digits,
        ):
            if not self.is_correct(word):
                out.append((start, end, word))
        return out

    # ---------- suggestions ----------

    def suggest(self, word, limit=8):
        """Yield suggestions one by one, best first.

        Hunspell suggestions for Mongolian take a few seconds in total, but the
        first (usually the right one) arrives in well under a second, so the
        caller should show them as they come.
        """
        script = T.script_of(word)
        dicts = self._for_script(script) if script else []
        seen = set()
        for d in dicts:
            for s in itertools.islice(d.suggest(word), limit):
                if s not in seen:
                    seen.add(s)
                    yield s
                if len(seen) >= limit:
                    return

    # ---------- learning ----------

    def ignore(self, word):
        with self._lock:
            self.ignored.add(word)
            self._cache.clear()  # other spellings of the word may be cached

    def add_to_personal(self, word):
        with self._lock:
            self.personal.add(word)
            self._cache.clear()
        if self.personal_path:
            os.makedirs(os.path.dirname(self.personal_path) or ".", exist_ok=True)
            with open(self.personal_path, "a", encoding="utf-8") as f:
                f.write(word + "\n")

    def set_options(self, options):
        with self._lock:
            self.options = options
            self._cache.clear()
