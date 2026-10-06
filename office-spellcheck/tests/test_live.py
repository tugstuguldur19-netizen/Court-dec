"""Live Office mode, tested against small fakes of the Word, Excel and
PowerPoint automation objects. The fakes copy the behaviour the code relies
on (live Word ranges that move with edits, 1-based UTF-16 Characters()),
so this checks our logic; it cannot prove what real Office does."""

import re

import pytest

from offspell.check import scan
from offspell.live import ExcelSource, PowerPointSource, StaleIssue, WordSource, a1


# ---------------------------------------------------------------- Word fakes

class Story:
    def __init__(self, text, kind=1):
        self.text = text
        self.kind = kind
        self.ranges = []


class FakeFind:
    def __init__(self, rng):
        self.rng = rng

    def ClearFormatting(self):
        pass

    def Execute(self, text, match_case, whole, wildcards, sounds, forms, forward, wrap, fmt):
        r = self.rng
        buf = r.story.text
        limit = len(buf) if r.start == r.end else r.end
        i = buf.find(text, r.start)
        while i >= 0 and i + len(text) <= limit:
            if not whole or ((i == 0 or not buf[i - 1].isalnum())
                             and (i + len(text) == len(buf) or not buf[i + len(text)].isalnum())):
                r.start, r.end = i, i + len(text)
                return True
            i = buf.find(text, i + 1)
        return False


class FakeParagraphs:
    def __init__(self, rng):
        self.rng = rng

    @property
    def First(self):
        buf = self.rng.story.text
        s = buf.rfind("\r", 0, self.rng.start) + 1
        e = buf.find("\r", self.rng.start)
        e = len(buf) if e < 0 else e + 1
        return type("P", (), {"Range": WRange(self.rng.story, s, e)})()


class WRange:
    def __init__(self, story, start, end):
        self.story, self.start, self.end = story, start, end
        story.ranges.append(self)
        self.selected = False

    Start = property(lambda self: self.start)
    End = property(lambda self: self.end)
    StoryType = property(lambda self: self.story.kind)
    NextStoryRange = None

    @property
    def Text(self):
        return self.story.text[self.start:self.end]

    @Text.setter
    def Text(self, new):
        s, e = self.start, self.end
        st = self.story
        st.text = st.text[:s] + new + st.text[e:]
        delta = len(new) - (e - s)
        for r in st.ranges:
            if r is self:
                continue
            if r.start >= e:
                r.start += delta
                r.end += delta
        self.end = s + len(new)

    @property
    def Duplicate(self):
        return WRange(self.story, self.start, self.end)

    @property
    def Find(self):
        return FakeFind(self)

    @property
    def Paragraphs(self):
        return FakeParagraphs(self)

    def Collapse(self, direction):
        if direction == 0:
            self.start = self.end
        else:
            self.end = self.start

    def MoveStart(self, unit, n):
        self.start = max(0, self.start + n)

    def MoveEnd(self, unit, n):
        self.end = min(len(self.story.text), self.end + n)

    def Information(self, what):
        return 1 + self.start // 40

    def Select(self):
        self.selected = True


class FakeWordApp:
    def __init__(self, *stories):
        ranges = [WRange(s, 0, len(s.text)) for s in stories]
        self.ActiveDocument = type("Doc", (), {"Name": "case.docx", "StoryRanges": ranges})()
        self.ActiveWindow = type("Win", (), {"ScrollIntoView": lambda self, r, top: None})()


def test_word_live(speller):
    main = Story("Монгол улс шүүхй улсныг улсн.\rcuort шүүхй нийгэм-улсн\r")
    header = Story("Монгл\r", kind=7)
    src = WordSource(app=FakeWordApp(main, header))
    issues = scan(src, speller)
    # "улсн" inside "улсныг" and in the hyphenated word is not a separate hit
    assert [(i.word, i.location) for i in issues] == [
        ("шүүхй", ("page", 1)), ("улсн", ("page", 1)), ("cuort", ("page", 1)),
        ("шүүхй", ("page", 1)), ("нийгэм-улсн", ("page", 2)),
        ("Монгл", ("story", "header")),
    ]
    text, s, e = src.context(issues[2])
    assert text == "cuort шүүхй нийгэм-улсн\r" and text[s:e] == "cuort"

    src.select(issues[0])
    assert issues[0].extra["range"].selected
    # replacing one word keeps the later ranges on their words
    src.replace(issues[0], "шүүх")
    src.replace(issues[3], "шүүх")
    src.replace(issues[1], "улс")
    assert main.text == "Монгол улс шүүх улсныг улс.\rcuort шүүх нийгэм-улсн\r"
    assert issues[2].extra["range"].Text == "cuort"
    src.replace(issues[5], "Монгол")
    assert header.text == "Монгол\r"


def test_word_stale(speller):
    main = Story("шүүхй\r")
    src = WordSource(app=FakeWordApp(main))
    [issue] = scan(src, speller)
    issue.extra["range"].Text = "abc"   # the user changed the word in Word
    with pytest.raises(StaleIssue):
        src.replace(issue, "шүүх")


# ---------------------------------------------------------------- Excel fakes

def u16(s):
    return len(s.encode("utf-16-le")) // 2


def from_u16(s, units):
    """Python index for a UTF-16 position."""
    n = 0
    for i, ch in enumerate(s):
        if n >= units:
            return i
        n += u16(ch)
    return len(s)


class Chars:
    def __init__(self, owner, pos, length):
        self.owner, self.pos, self.length = owner, pos, length

    @property
    def Text(self):
        t = self.owner.get()
        a = from_u16(t, self.pos - 1)
        return t[a:from_u16(t, self.pos - 1 + self.length)]

    @Text.setter
    def Text(self, new):
        t = self.owner.get()
        a = from_u16(t, self.pos - 1)
        b = from_u16(t, self.pos - 1 + self.length)
        self.owner.set(t[:a] + new + t[b:])

    def Select(self):
        self.owner.selected = (self.pos, self.length)


class Cell:
    def __init__(self, sheet, r, c):
        self.sheet, self.r, self.c = sheet, r, c

    def get(self):
        return self.sheet.cells[(self.r, self.c)]

    def set(self, v):
        self.sheet.cells[(self.r, self.c)] = v

    Value2 = property(get, set)

    def GetCharacters(self, pos, length):
        return Chars(self, pos, length)

    def Select(self):
        self.sheet.selected = (self.r, self.c)


class Sheet:
    def __init__(self, name, cells, formulas=None):
        self.Name, self.cells, self.formulas = name, dict(cells), formulas or {}
        self.selected = None

    @property
    def UsedRange(self):
        rows = [r for r, _ in self.cells]
        cols = [c for _, c in self.cells]
        r0, c0 = min(rows), min(cols)
        grid_v = tuple(tuple(self.cells.get((r, c)) for c in range(c0, max(cols) + 1))
                       for r in range(r0, max(rows) + 1))
        grid_f = tuple(tuple(self.formulas.get((r, c), self.cells.get((r, c)) or "")
                             for c in range(c0, max(cols) + 1)) for r in range(r0, max(rows) + 1))
        if len(grid_v) == 1 and len(grid_v[0]) == 1:
            grid_v, grid_f = grid_v[0][0], grid_f[0][0]
        return type("U", (), {"Row": r0, "Column": c0, "Value2": grid_v, "Formula": grid_f})()

    def Cells(self, r, c):
        return Cell(self, r, c)

    def Activate(self):
        pass


def test_excel_live(speller):
    s1 = Sheet("Хэрэг", {(2, 2): "Монгл улс шүүхй", (3, 2): 12.0, (3, 3): "cuortx",
                         (4, 28): "😀 шүүхй"}, formulas={(3, 3): '="cuort"&"x"'})
    s2 = Sheet("Нэг", {(1, 1): "гэрээй"})
    app = type("App", (), {"ActiveWorkbook": type("WB", (), {"Name": "a.xlsx", "Worksheets": [s1, s2]})()})()
    src = ExcelSource(app=app)
    issues = scan(src, speller)
    assert [(i.word, i.location) for i in issues] == [
        ("Монгл", ("cell", "Хэрэг", "B2")), ("шүүхй", ("cell", "Хэрэг", "B2")),
        ("шүүхй", ("cell", "Хэрэг", "AB4")), ("гэрээй", ("cell", "Нэг", "A1")),
    ]
    src.select(issues[3])
    assert s2.selected == (1, 1)
    src.replace(issues[0], "Монгол")       # the second word in the cell shifts
    src.replace(issues[1], "шүүх")
    assert s1.cells[(2, 2)] == "Монгол улс шүүх"
    src.replace(issues[2], "шүүх")         # emoji before the word: UTF-16 offsets
    assert s1.cells[(4, 28)] == "😀 шүүх"
    # the user edited the cell after the check: the word is found again
    s2.cells[(1, 1)] = "шинэ гэрээй"
    src.replace(issues[3], "гэрээ")
    assert s2.cells[(1, 1)] == "шинэ гэрээ"


def test_a1():
    assert [a1(1, 1), a1(5, 26), a1(7, 27), a1(9, 703)] == ["A1", "Z5", "AA7", "AAA9"]


# ---------------------------------------------------------------- PowerPoint fakes

class TR:
    def __init__(self, text):
        self.text = text
        self.selected = None

    def get(self):
        return self.text

    def set(self, v):
        self.text = v

    Text = property(get, set)

    def Characters(self, pos, length):
        return Chars(self, pos, length)


def shape(text=None, items=None, placeholder=None):
    frame = type("F", (), {"HasText": bool(text), "TextRange": TR(text or "")})()
    attrs = {"Type": 6 if items else (14 if placeholder else 1), "HasTable": 0, "HasTextFrame": -1,
             "TextFrame": frame, "GroupItems": items or []}
    if placeholder:
        attrs["PlaceholderFormat"] = type("PF", (), {"Type": placeholder})()
    return type("S", (), attrs)()


def test_powerpoint_live(speller):
    title = shape("Монгл улс")
    group = shape(items=[shape("cuort\rшүүхй")])
    notes = [shape("1", placeholder=13), shape("гэрээй", placeholder=2)]
    slide = type("Slide", (), {"SlideIndex": 1, "Shapes": [title, group],
                               "NotesPage": type("N", (), {"Shapes": notes})()})()
    went = []
    view = type("V", (), {"GotoSlide": lambda self, n: went.append(n)})()
    app = type("App", (), {"ActivePresentation": type("P", (), {"Name": "a.pptx", "Slides": [slide]})(),
                           "ActiveWindow": type("W", (), {"View": view})()})()
    src = PowerPointSource(app=app)
    issues = scan(src, speller)
    assert [(i.word, i.location) for i in issues] == [
        ("Монгл", ("slide", 1)), ("cuort", ("slide", 1)), ("шүүхй", ("slide", 1)), ("гэрээй", ("notes", 1)),
    ]
    src.select(issues[2])
    assert went == [1]
    src.replace(issues[1], "court")
    src.replace(issues[2], "шүүх")
    src.replace(issues[3], "гэрээ")
    assert group.GroupItems[0].TextFrame.TextRange.Text == "court\rшүүх"
    assert notes[1].TextFrame.TextRange.Text == "гэрээ"
    # text replaced completely in PowerPoint: the issue is reported as stale
    title.TextFrame.TextRange.Text = "өөр текст"
    with pytest.raises(StaleIssue):
        src.replace(issues[0], "Монгол")


def test_live_unavailable_off_windows():
    import sys

    from offspell import live
    if sys.platform != "win32":
        assert not live.available()
    assert re.match(r"^\w+$", live.SOURCES["word"].app_name)
