"""Checking the document that is open in Word, Excel or PowerPoint right now.

Windows only. It talks to the running Office program through COM
automation (the pywin32 package), the same local interface VBA macros use.
No add-in has to be installed in Office and nothing goes over the network.

All calls into Office must happen on the GUI thread; only the spell-checking
of the collected text runs in the background.
"""

import sys

from . import text as T
from .model import Issue, Source, Unit


class NotRunning(Exception):
    """The Office program is not running or has no document open."""


class StaleIssue(Exception):
    """The text changed in Office since it was checked."""


def available():
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    return True


def _active_app(progid):
    import pythoncom
    import win32com.client

    try:
        return win32com.client.GetActiveObject(progid)
    except pythoncom.com_error:
        raise NotRunning(progid)


def _locate(current, old_text, start, end, word):
    """Find the word again if the text around it changed after the check."""
    if current == old_text:
        return start, end
    best = None
    i = current.find(word)
    while i >= 0:
        if T.standalone_at(current, i, i + len(word)):
            if best is None or abs(i - start) < abs(best - start):
                best = i
        i = current.find(word, i + 1)
    if best is None:
        raise StaleIssue(word)
    return best, best + len(word)


def _u16(text, start, end):
    """1-based start and length in UTF-16 units, as Office's Characters() wants."""
    return T.utf16_len(text[:start]) + 1, T.utf16_len(text[start:end])


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

WD_COLLAPSE_END = 0
WD_CHARACTER = 1
WD_PAGE_NUMBER = 3   # wdActiveEndPageNumber
STORY_KINDS = {1: "main", 2: "footnote", 3: "endnote", 4: "comment", 5: "textbox",
               6: "header", 7: "header", 8: "footer", 9: "footer", 10: "header", 11: "footer"}


class WordSource(Source):
    """Word keeps Range objects pointing at the same text while the document
    is edited, so each issue holds a Range found with Word's own Find."""

    app_name = "Word"

    def __init__(self, app=None):
        self.app = app or _active_app("Word.Application")
        try:
            self.doc = self.app.ActiveDocument
        except Exception:
            raise NotRunning("Word")
        if self.doc is None:
            raise NotRunning("Word")
        self.title = self.doc.Name

    def units(self):
        units, seen = [], set()
        for story in self.doc.StoryRanges:
            rng = story
            while rng is not None:
                kind = STORY_KINDS.get(rng.StoryType)
                text = rng.Text or ""
                key = (kind, text)
                if kind and text.strip() and key not in seen:
                    seen.add(key)
                    units.append(Unit(text=text, location=("story", kind), handle=rng))
                try:
                    rng = rng.NextStoryRange
                except Exception:
                    rng = None
        return units

    def make_issues(self, unit, hits):
        story = unit.handle
        ranges = []
        for word in sorted({w for _, _, w in hits}):
            if len(word) > 255:   # Word's Find limit
                continue
            found = self._find_all(story, word, whole_word=False)
            if not found:
                # Our idea of a word boundary disagreed with Word's text;
                # fall back to Word's own whole-word matching.
                found = self._find_all(story, word, whole_word=True)
            ranges += [(r.Start, word, r) for r in found]
        ranges.sort(key=lambda t: t[0])
        issues = []
        for _, word, rng in ranges:
            loc = unit.location
            if loc == ("story", "main"):
                try:
                    loc = ("page", rng.Information(WD_PAGE_NUMBER))
                except Exception:
                    pass
            issues.append(Issue(word=word, location=loc, unit=unit, extra={"range": rng}))
        return issues

    def _find_all(self, story, word, whole_word):
        rng = story.Duplicate
        find = rng.Find
        find.ClearFormatting()
        out, last = [], -1
        # Execute(FindText, MatchCase, MatchWholeWord, MatchWildcards,
        #         MatchSoundsLike, MatchAllWordForms, Forward, Wrap, Format)
        while find.Execute(word, True, whole_word, False, False, False, True, 0, False):
            start, end = rng.Start, rng.End
            if start <= last or end <= start:
                break
            last = start
            if whole_word or self._standalone(rng, word):
                out.append(rng.Duplicate)
            rng.Collapse(WD_COLLAPSE_END)
        return out

    @staticmethod
    def _standalone(rng, word):
        """Drop matches that are part of a longer word ("улсн" in "улсныг")."""
        probe = rng.Duplicate
        probe.MoveStart(WD_CHARACTER, -2)
        probe.MoveEnd(WD_CHARACTER, 2)
        text = probe.Text or ""
        offset = rng.Start - probe.Start
        i = text.find(word, max(0, offset - 1))
        if i < 0:
            return True
        return T.standalone_at(text, i, i + len(word))

    def context(self, issue):
        rng = issue.extra["range"]
        try:
            para = rng.Paragraphs.First.Range
            text = para.Text or ""
            word = rng.Text or issue.word
            i = text.find(word, max(0, rng.Start - para.Start - 2))
            if i < 0:
                i = text.find(word)
            if i >= 0:
                return T.context(text, i, i + len(word))
        except Exception:
            pass
        return issue.word, 0, len(issue.word)

    def select(self, issue):
        rng = issue.extra["range"]
        try:
            rng.Select()
            self.app.ActiveWindow.ScrollIntoView(rng, True)
        except Exception:
            pass

    def replace(self, issue, new):
        rng = issue.extra["range"]
        if (rng.Text or "") != issue.word:
            raise StaleIssue(issue.word)
        rng.Text = new
        self.dirty = True

    def close(self):
        self.doc = self.app = None


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

def _grid(value):
    """Range.Value is a scalar for one cell and a tuple of rows otherwise."""
    if isinstance(value, tuple):
        return [row if isinstance(row, tuple) else (row,) for row in value]
    return [(value,)]


def a1(row, col):
    letters = ""
    while col:
        col, rem = divmod(col - 1, 26)
        letters = chr(65 + rem) + letters
    return "%s%d" % (letters, row)


class ExcelSource(Source):
    app_name = "Excel"

    def __init__(self, app=None):
        self.app = app or _active_app("Excel.Application")
        try:
            self.wb = self.app.ActiveWorkbook
        except Exception:
            raise NotRunning("Excel")
        if self.wb is None:
            raise NotRunning("Excel")
        self.title = self.wb.Name

    def units(self):
        units = []
        for ws in self.wb.Worksheets:
            used = ws.UsedRange
            r0, c0 = used.Row, used.Column
            values = _grid(used.Value2)
            formulas = _grid(used.Formula)
            for i, row in enumerate(values):
                for j, v in enumerate(row):
                    if not isinstance(v, str) or not v.strip():
                        continue
                    f = formulas[i][j] if i < len(formulas) and j < len(formulas[i]) else None
                    if isinstance(f, str) and f.startswith("="):
                        continue   # a formula result, not typed text
                    r, c = r0 + i, c0 + j
                    units.append(Unit(text=v, location=("cell", ws.Name, a1(r, c)), handle=(ws, r, c)))
        return units

    def select(self, issue):
        ws, r, c = issue.unit.handle
        try:
            ws.Activate()
            ws.Cells(r, c).Select()
        except Exception:
            pass

    def _replace_in_unit(self, unit, start, end, new):
        ws, r, c = unit.handle
        cell = ws.Cells(r, c)
        current = cell.Value2
        if not isinstance(current, str):
            raise StaleIssue(unit.text[start:end])
        start, end = _locate(current, unit.text, start, end, unit.text[start:end])
        expected = current[:start] + new + current[end:]
        pos, length = _u16(current, start, end)
        # Characters() keeps the formatting of the rest of the cell; if Excel
        # refuses (very long cells), set the whole value instead.
        try:
            cell.GetCharacters(pos, length).Text = new
        except Exception:
            try:
                cell.Characters(pos, length).Text = new
            except Exception:
                pass
        if cell.Value2 != expected:
            cell.Value2 = expected
        unit.text = current
        return start, end

    def close(self):
        self.wb = self.app = None


# ---------------------------------------------------------------------------
# PowerPoint
# ---------------------------------------------------------------------------

MSO_GROUP = 6
MSO_PLACEHOLDER = 14
PP_PLACEHOLDER_BODY = 2


def _text_ranges(shape):
    try:
        if shape.Type == MSO_GROUP:
            for item in shape.GroupItems:
                yield from _text_ranges(item)
            return
        if shape.HasTable:
            table = shape.Table
            for r in range(1, table.Rows.Count + 1):
                for c in range(1, table.Columns.Count + 1):
                    frame = table.Cell(r, c).Shape.TextFrame
                    if frame.HasText:
                        yield frame.TextRange
            return
        if shape.HasTextFrame and shape.TextFrame.HasText:
            yield shape.TextFrame.TextRange
    except Exception:
        return


class PowerPointSource(Source):
    app_name = "PowerPoint"

    def __init__(self, app=None):
        self.app = app or _active_app("PowerPoint.Application")
        try:
            self.pres = self.app.ActivePresentation
        except Exception:
            raise NotRunning("PowerPoint")
        if self.pres is None:
            raise NotRunning("PowerPoint")
        self.title = self.pres.Name

    def units(self):
        units = []
        for slide in self.pres.Slides:
            n = slide.SlideIndex
            for shape in slide.Shapes:
                for tr in _text_ranges(shape):
                    units.append(Unit(text=tr.Text or "", location=("slide", n), handle=(slide, tr)))
            try:
                notes = slide.NotesPage.Shapes
            except Exception:
                continue
            for shape in notes:
                try:
                    if shape.Type != MSO_PLACEHOLDER or shape.PlaceholderFormat.Type != PP_PLACEHOLDER_BODY:
                        continue
                except Exception:
                    continue
                for tr in _text_ranges(shape):
                    units.append(Unit(text=tr.Text or "", location=("notes", n), handle=(slide, tr)))
        return [u for u in units if u.text.strip()]

    def select(self, issue):
        slide, tr = issue.unit.handle
        try:
            self.app.ActiveWindow.View.GotoSlide(slide.SlideIndex)
            if issue.location[0] == "slide":
                pos, length = _u16(issue.unit.text, issue.start, issue.end)
                tr.Characters(pos, length).Select()
        except Exception:
            pass

    def _replace_in_unit(self, unit, start, end, new):
        slide, tr = unit.handle
        current = tr.Text or ""
        start, end = _locate(current, unit.text, start, end, unit.text[start:end])
        pos, length = _u16(current, start, end)
        tr.Characters(pos, length).Text = new
        unit.text = current
        return start, end

    def close(self):
        self.pres = self.app = None


SOURCES = {"word": WordSource, "excel": ExcelSource, "powerpoint": PowerPointSource}
