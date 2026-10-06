"""What the app works with: places that hold text ("sources") and the
possible misspellings found in them ("issues").

A source is either an Office file on disk or a document that is open in Word,
Excel or PowerPoint right now. Both expose the same small interface so the
window does not care which one it is talking to.
"""

from dataclasses import dataclass, field


@dataclass(eq=False)
class Issue:
    word: str
    location: tuple            # e.g. ("paragraph", 12) or ("cell", "Sheet1", "B3")
    unit: object = None        # the text unit (paragraph, cell, shape) it is in
    start: int = 0             # offsets of the word inside the unit's text
    end: int = 0
    status: str = "open"       # open | fixed | ignored | added
    replacement: str = ""
    extra: dict = field(default_factory=dict)


@dataclass(eq=False)
class Unit:
    """A piece of text to check: one paragraph, cell, shape, or Word story."""
    text: str
    location: tuple
    handle: object = None


class Source:
    """Base class. Subclasses fill in the Office-specific parts."""

    title = ""
    savable = False   # True for files: corrections are written with save()
    dirty = False

    def units(self):
        """Return the list of Units to check. Called on the GUI thread."""
        raise NotImplementedError

    def make_issues(self, unit, hits):
        """Turn [(start, end, word)] found in a unit into Issues."""
        issues = [Issue(word=w, location=unit.location, unit=unit, start=s, end=e) for s, e, w in hits]
        unit.issues = issues  # so a replacement can shift the others in this unit
        return issues

    def context(self, issue):
        """Return (text, start, end): the text around the word, for display."""
        return issue.unit.text, issue.start, issue.end

    def select(self, issue):
        """Show the word in Office. Nothing to do for files."""

    def replace(self, issue, new):
        """Replace the word and keep other issues in the same unit aligned."""
        unit = issue.unit
        where = self._replace_in_unit(unit, issue.start, issue.end, new)
        start, end = where or (issue.start, issue.end)
        unit.text = unit.text[:start] + new + unit.text[end:]
        delta = len(new) - (end - start)
        for other in getattr(unit, "issues", ()):
            if other is not issue and other.start >= end:
                other.start += delta
                other.end += delta
        issue.start, issue.end = start, start + len(new)
        self.dirty = True

    def _replace_in_unit(self, unit, start, end, new):
        """Make the change. May return the (start, end) actually replaced if
        the text moved; it then also sets unit.text to the text before the change."""
        raise NotImplementedError

    def save(self, path):
        raise NotImplementedError

    def close(self):
        """Release anything held (COM objects, file contents)."""

