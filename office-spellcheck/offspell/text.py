"""Splitting text into words to check.

Everything here is plain string work, so it is shared by the file mode and the
live Office mode, and it is easy to test.
"""

import re

# Characters that join two halves of one word: "нийгэм-эдийн", "don't".
JOINERS = "-‐‑'’"

# A token is a run of letters/digits, optionally joined by hyphens or apostrophes.
# "_" counts as \w in Python, so it is excluded explicitly.
_TOKEN = re.compile(r"[^\W_]+(?:[" + re.escape(JOINERS) + r"][^\W_]+)*")

# Web and e-mail addresses are never spell-checked.
_ADDRESS = re.compile(
    r"(?:\b(?:https?|ftp)://|\bwww\.)\S+"
    r"|[\w.+-]+@[\w-]+(?:\.[\w-]+)+"
    r"|\b[\w-]+(?:\.[\w-]+)*\.(?:mn|com|org|net|gov|edu|info|io|ru|cn|kr|jp|de|uk|us)\b",
    re.IGNORECASE,
)

# Mongolian case endings written after a number or abbreviation in quotes:
# "15%-ийн", "(3)-р", "”-ын". The ending alone is not a word, so it is skipped.
_MAX_ATTACHED_ENDING = 7


def script_of(word):
    """Return "cyrl", "latn" or None for the alphabet a word is written in.

    A word with any Cyrillic letter is treated as Cyrillic, so a Latin
    look-alike typed by mistake ("Монгoл" with a Latin "o") is still checked
    by the Mongolian dictionary, which knows how to suggest the fix.
    """
    latin = False
    for ch in word:
        if "Ѐ" <= ch <= "ԯ":
            return "cyrl"
        if ("a" <= ch <= "z") or ("A" <= ch <= "Z") or ("À" <= ch <= "ɏ"):
            latin = True
    return "latn" if latin else None


def _is_attached_ending(text, start, word):
    """True for "ийн" in "15%-ийн": a short lowercase ending after a hyphen
    that follows a symbol or digit, not a letter."""
    if start < 2 or text[start - 1] not in JOINERS:
        return False
    before = text[start - 2]
    if before.isalpha():
        return False
    return len(word) <= _MAX_ATTACHED_ENDING and word.islower()


def words(text, *, ignore_uppercase=True, ignore_with_digits=True):
    """Yield (start, end, word) for every word in text that should be checked.

    Skips single letters, web/e-mail addresses, words without letters, and
    optionally ALL-CAPS words (abbreviations such as "ХХК") and words that
    contain digits ("2024-ний"), the same defaults Word uses.
    """
    masked = text
    if "." in text or "@" in text:
        masked = _ADDRESS.sub(lambda m: " " * len(m.group()), text)
    for m in _TOKEN.finditer(masked):
        word = m.group()
        if len(word) < 2:
            continue
        has_digit = any(ch.isdigit() for ch in word)
        if has_digit:
            if ignore_with_digits or not any(ch.isalpha() for ch in word):
                continue
        if ignore_uppercase and word.isupper():
            continue
        if _is_attached_ending(masked, m.start(), word):
            continue
        yield m.start(), m.end(), word


def split_joined(word):
    """Split "нийгэм-эдийн" into its parts; apostrophes are kept inside parts."""
    return [p for p in re.split("[-‐‑]", word) if p]


def is_word_char(ch):
    return ch.isalnum()


def standalone_at(text, start, end):
    """True if text[start:end] is a whole token, not part of a longer one.

    Used by the live Word mode, where Word's Find returns substrings and we
    must drop matches such as "улсн" inside "улсныг".
    """
    def joined(i, step):
        # Character at i is a joiner with a word character on its far side.
        j = i + step
        return 0 <= i < len(text) and text[i] in JOINERS and 0 <= j < len(text) and is_word_char(text[j])

    if start > 0 and (is_word_char(text[start - 1]) or joined(start - 1, -1)):
        return False
    if end < len(text) and (is_word_char(text[end]) or joined(end, 1)):
        return False
    return True


def utf16_len(s):
    """Length of s in UTF-16 code units, which is how Office counts characters."""
    return len(s.encode("utf-16-le")) // 2


def context(text, start, end, width=160):
    """Return (snippet, start, end) with the word placed inside a short window."""
    if len(text) <= width * 2:
        return text, start, end
    lo = max(0, start - width)
    hi = min(len(text), end + width)
    prefix = "…" if lo > 0 else ""
    suffix = "…" if hi < len(text) else ""
    snippet = prefix + text[lo:hi] + suffix
    shift = len(prefix) - lo
    return snippet, start + shift, end + shift
