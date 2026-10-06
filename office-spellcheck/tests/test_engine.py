from offspell import text as T
from offspell.engine import Options, Speller


def words(s, **kw):
    return [w for _, _, w in T.words(s, **kw)]


def test_tokenizer_basics():
    assert words("Монгол улсын Үндсэн хууль.") == ["Монгол", "улсын", "Үндсэн", "хууль"]
    # initials are split off and single letters skipped
    assert words("Б.Батболд") == ["Батболд"]
    # hyphenated words stay together
    assert words("нийгэм-эдийн засаг") == ["нийгэм-эдийн", "засаг"]
    assert words("don't stop") == ["don't", "stop"]


def test_tokenizer_skips():
    # abbreviations in capitals, numbers, addresses
    assert words("ХХК ШШГЕГ") == []
    assert words("ХХК ШШГЕГ", ignore_uppercase=False) == ["ХХК", "ШШГЕГ"]
    assert words("2024-ний 15-ны") == []
    assert words("2024-ний", ignore_with_digits=False) == ["2024-ний"]
    assert words("www.shuukh.mn info@court.mn https://example.com/a-b") == []
    # an ending after a symbol is not a word of its own
    assert words("15%-ийн “Хаан банк”-ны") == ["Хаан", "банк"]


def test_script_of():
    assert T.script_of("шүүх") == "cyrl"
    assert T.script_of("Монгoл") == "cyrl"  # Latin "o" inside: still Mongolian
    assert T.script_of("court") == "latn"
    assert T.script_of("123") is None


def test_standalone_at():
    t = "улсн улсныг нийгэм-улсн улсн."
    assert T.standalone_at(t, 0, 4)
    assert not T.standalone_at(t, 5, 9)     # inside "улсныг"
    assert not T.standalone_at(t, 19, 23)   # second half of a hyphenated word
    assert T.standalone_at(t, 24, 28)


def test_context_window():
    text = "а" * 500 + " үг " + "б" * 500
    snip, s, e = T.context(text, 501, 503, width=20)
    assert snip[s:e] == "үг"
    assert snip.startswith("…") and snip.endswith("…")


def test_speller_checks_by_alphabet(speller):
    assert speller.is_correct("шүүх")
    assert speller.is_correct("шүүхийн")      # suffix rule from the .aff
    assert speller.is_correct("Шүүх")         # capitalised
    assert speller.is_correct("ШҮҮХ")
    assert not speller.is_correct("шүүхй")
    assert speller.is_correct("court")
    assert not speller.is_correct("cuort")
    # words in alphabets without a dictionary are never flagged
    assert speller.is_correct("法院")


def test_hyphen_rules(speller):
    assert speller.is_correct("нийгэм-эдийн")           # both halves are words
    assert speller.is_correct("Батболд-д")               # case ending after a name
    assert not speller.is_correct("шүүх-д")              # but not after a common noun
    assert not speller.is_correct("нийгэм-эдйн")


def test_wordlists_and_personal(speller, tmp_path):
    assert speller.is_correct("даалгасугай")   # from legal_terms.txt
    assert not speller.is_correct("Жишиг")
    speller.add_to_personal("жишиг")
    assert speller.is_correct("Жишиг") and speller.is_correct("ЖИШИГ")
    assert (tmp_path / "personal.txt").read_text(encoding="utf-8").strip() == "жишиг"
    # a new speller reads the personal dictionary back
    again = Speller(speller.dictionary_folders, str(tmp_path / "personal.txt"))
    again.load()
    assert again.is_correct("жишиг")


def test_ignore_and_options(speller):
    assert not speller.is_correct("cuort")
    speller.ignore("cuort")
    assert speller.is_correct("cuort")
    speller.set_options(Options(check_latin=False))
    assert speller.is_correct("anythingg")


def test_misspellings_offsets(speller):
    text = "Монгол улс шүүхй, cuort."
    hits = speller.misspellings(text)
    assert [(text[s:e], w) for s, e, w in hits] == [("шүүхй", "шүүхй"), ("cuort", "cuort")]


def test_suggestions(speller):
    assert "шүүх" in list(speller.suggest("шүүхй"))
    assert "court" in list(speller.suggest("cuort"))


def test_real_dictionary_legal_text(real_speller):
    text = ("Сүхбаатар дүүргийн Иргэний хэргийн анхан шатны шүүхийн шүүгч Б.Батболд даргалж, "
            "нэхэмжлэгч “Хаан банк” ХХК-ийн нэхэмжлэлтэй, хариуцагч Д.Дорж-д холбогдох зээлийн гэрээний "
            "үүргийн гүйцэтгэлд 15,000,000 төгрөг гаргуулах тухай иргэний хэргийг 2024 оны 3 дугаар "
            "сарын 15-ны өдөр хянан хэлэлцэв. Иргэний хуулийн 281 дүгээр зүйлийн 281.1-д заасныг баримтлан "
            "хариуцагчаас төгрөгийг гаргуулж нэхэмжлэгчид олгосугай.")
    assert real_speller.misspellings(text) == []
    bad = "Монгл улсн шийдвр Монгoл nonexistant"
    assert [w for _, _, w in real_speller.misspellings(bad)] == bad.split()
    assert next(real_speller.suggest("Монгoл")) == "Монгол"
    assert "шийдвэр" in list(real_speller.suggest("шийдвр", limit=3))
