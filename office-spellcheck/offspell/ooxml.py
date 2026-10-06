"""Reading and correcting .docx, .xlsx and .pptx files directly.

These formats are zip files of XML. Text is split into "runs" by formatting,
so one word can be spread over several XML elements ("Монг" bold + "ол"
plain). Each paragraph/cell is turned into a Segment that maps character
offsets back to the elements, which lets a correction change only the
characters of the word and keep all formatting.

Everything else in the file (images, styles, macros) is copied byte for byte.
"""

import os
import posixpath
import re
import tempfile
import zipfile

from lxml import etree

from .model import Source, Unit

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
S = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


def w(tag):
    return "{%s}%s" % (W, tag)


def a(tag):
    return "{%s}%s" % (A, tag)


def s(tag):
    return "{%s}%s" % (S, tag)


def p(tag):
    return "{%s}%s" % (P, tag)


FALLBACK = "{%s}Fallback" % MC
ALTERNATE = "{%s}AlternateContent" % MC

SUPPORTED = (".docx", ".docm", ".dotx", ".dotm", ".xlsx", ".xlsm", ".xltx", ".xltm",
             ".pptx", ".pptm", ".potx", ".potm", ".ppsx", ".ppsm")
LEGACY = (".doc", ".xls", ".ppt", ".rtf")

_PARSER = etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True, remove_blank_text=False)


class UnsupportedFile(Exception):
    pass


# ---------------------------------------------------------------------------
# Segments: text with a map back to XML elements
# ---------------------------------------------------------------------------

class Piece:
    """One stretch of a segment's text.

    kind "text": the .text of an element, which a correction may change.
    kind "sep":  a tab, line break or object; fixed, never part of a word.
    kind "char": an element that stands for one character (Word's
                 non-breaking hyphen); removed if a correction covers it.
    """
    __slots__ = ("elem", "kind", "fixed")

    def __init__(self, elem, kind, fixed=""):
        self.elem = elem
        self.kind = kind
        self.fixed = fixed

    @property
    def value(self):
        return (self.elem.text or "") if self.kind == "text" else self.fixed


class Segment:
    def __init__(self, part, location, pieces, preserve_space=True):
        self.part = part
        self.location = location
        self.pieces = pieces
        self.preserve_space = preserve_space

    @property
    def text(self):
        return "".join(pc.value for pc in self.pieces)

    def replace(self, start, end, new):
        """Replace text[start:end] with new, keeping the formatting of the run
        that holds the first character of the word."""
        pos = 0
        placed = False
        for pc in list(self.pieces):
            val = pc.value
            ps, pe = pos, pos + len(val)
            pos = pe
            lo, hi = max(start, ps), min(end, pe)
            if pc.kind == "text":
                if not placed and ps <= start < pe:
                    self._set(pc, val[: start - ps] + new + val[hi - ps:])
                    placed = True
                elif lo < hi:
                    self._set(pc, val[: lo - ps] + val[hi - ps:])
            elif pc.kind == "char" and (lo < hi or (ps == pe and start < ps < end)):
                parent = pc.elem.getparent()
                if parent is not None:
                    parent.remove(pc.elem)
                self.pieces.remove(pc)
        if not placed:
            raise ValueError("word not found at %d..%d" % (start, end))

    def _set(self, pc, value):
        pc.elem.text = value
        if self.preserve_space:
            if value != value.strip() or "  " in value:
                pc.elem.set(XML_SPACE, "preserve")


# ---------------------------------------------------------------------------
# Package helpers
# ---------------------------------------------------------------------------

class Package:
    """The zip file, kept in memory; XML parts are parsed on demand."""

    def __init__(self, path):
        try:
            zf = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            raise UnsupportedFile(path)
        with zf:
            self.infos = zf.infolist()
            self.data = {i.filename: zf.read(i.filename) for i in self.infos}
        self.trees = {}
        self.dirty = set()

    def has(self, name):
        return name in self.data

    def tree(self, name):
        t = self.trees.get(name)
        if t is None:
            t = etree.fromstring(self.data[name], _PARSER).getroottree()
            self.trees[name] = t
        return t

    def root(self, name):
        return self.tree(name).getroot()

    def rels(self, part):
        """Return {rId: (type, target_part)} for a part."""
        folder, base = posixpath.split(part)
        rels_name = posixpath.join(folder, "_rels", base + ".rels")
        out = {}
        if rels_name not in self.data:
            return out
        for rel in self.root(rels_name).iter("{%s}Relationship" % PR):
            if rel.get("TargetMode") == "External":
                continue
            target = rel.get("Target", "")
            if target.startswith("/"):
                full = target.lstrip("/")
            else:
                full = posixpath.normpath(posixpath.join(folder, target))
            out[rel.get("Id")] = (rel.get("Type", "").rsplit("/", 1)[-1], full)
        return out

    def main_part(self):
        for rel in self.root("_rels/.rels").iter("{%s}Relationship" % PR):
            if rel.get("Type", "").endswith("/officeDocument"):
                return rel.get("Target").lstrip("/")
        raise UnsupportedFile("no main document part")

    def save(self, path):
        folder = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(suffix=".tmp", prefix=".spellcheck-", dir=folder)
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp, "w") as out:
                for info in self.infos:
                    name = info.filename
                    if name in self.dirty:
                        tree = self.trees[name]
                        data = etree.tostring(
                            tree, xml_declaration=True, encoding="UTF-8",
                            standalone=tree.docinfo.standalone if tree.docinfo.standalone is not None else True)
                        info = _copy_info(info)
                        info.compress_type = zipfile.ZIP_DEFLATED
                    else:
                        data = self.data[name]
                        info = _copy_info(info)
                    out.writestr(info, data)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


def _copy_info(info):
    """A fresh ZipInfo, so stale sizes or zip64 fields from the original are not reused."""
    new = zipfile.ZipInfo(info.filename, date_time=info.date_time)
    new.compress_type = info.compress_type
    new.external_attr = info.external_attr
    new.create_system = info.create_system
    return new


def _in_fallback(elem):
    for anc in elem.iterancestors():
        if anc.tag == FALLBACK:
            return True
    return False


# ---------------------------------------------------------------------------
# Word
# ---------------------------------------------------------------------------

_W_DESCEND = {w(t) for t in ("r", "hyperlink", "smartTag", "sdt", "sdtContent", "ins", "moveTo",
                              "customXml", "fldSimple", "dir", "bdo")}
_W_SEP = {w("tab"): "\t", w("ptab"): "\t", w("br"): "\n", w("cr"): "\n", w("sym"): " ",
          w("drawing"): " ", w("pict"): " ", w("object"): " ", w("footnoteReference"): " ",
          w("endnoteReference"): " ", w("commentReference"): " "}
CHOICE = "{%s}Choice" % MC
_W_CHAR = {w("noBreakHyphen"): "-", w("softHyphen"): ""}


def _word_pieces(elem, out):
    for child in elem:
        tag = child.tag
        if tag == w("t"):
            out.append(Piece(child, "text"))
        elif tag in _W_SEP:
            out.append(Piece(child, "sep", _W_SEP[tag]))
        elif tag in _W_CHAR:
            out.append(Piece(child, "char", _W_CHAR[tag]))
        elif tag in _W_DESCEND:
            _word_pieces(child, out)
        elif tag == ALTERNATE:
            # Same content in two forms; Word shows the first Choice it
            # understands, so read that one and never the Fallback copy.
            choice = child.find(CHOICE)
            if choice is not None:
                _word_pieces(choice, out)
            else:
                out.append(Piece(child, "sep", " "))
        # anything else (properties, deleted text, field codes, nested
        # paragraphs, unknown extensions) contributes no text here
    return out


def _word_location(para, kind, counters, numbering):
    """Describe where a paragraph is, for the list of issues."""
    for anc in para.iterancestors():
        if anc.tag == w("txbxContent"):
            return ("textbox",)
        if anc.tag == w("tc"):
            tr = anc.getparent()
            tbl = tr.getparent()
            row = [c for c in tbl if c.tag == w("tr")].index(tr) + 1
            col = [c for c in tr if c.tag == w("tc")].index(anc) + 1
            tables = numbering.setdefault("table", {})
            return ("table", tables.setdefault(tbl, len(tables) + 1), row, col)
        if anc.tag in (w("footnote"), w("endnote"), w("comment")):
            notes = numbering.setdefault(kind, {})
            return (kind, notes.setdefault(anc, len(notes) + 1))
    if kind == "paragraph":
        counters["paragraph"] = counters.get("paragraph", 0) + 1
        return ("paragraph", counters["paragraph"])
    return (kind, counters.setdefault(("part", kind), 0))


def load_word(pkg):
    main = pkg.main_part()
    parts = [(main, "paragraph")]
    order = {"header": [], "footer": [], "footnotes": [], "endnotes": [], "comments": []}
    for rtype, target in pkg.rels(main).values():
        if rtype in order and pkg.has(target):
            order[rtype].append(target)
    kinds = {"header": "header", "footer": "footer", "footnotes": "footnote",
             "endnotes": "endnote", "comments": "comment"}
    for rtype in ("header", "footer", "footnotes", "endnotes", "comments"):
        for target in sorted(order[rtype], key=_natural):
            parts.append((target, kinds[rtype]))

    segments = []
    header_no = {"header": 0, "footer": 0}
    for part, kind in parts:
        root = pkg.root(part)
        counters, numbering = {}, {}
        if kind in header_no:
            header_no[kind] += 1
            counters[("part", kind)] = header_no[kind]
        for para in root.iter(w("p")):
            if _in_fallback(para):
                continue
            pieces = _word_pieces(para, [])
            seg = Segment(part, None, pieces)
            if not seg.text.strip():
                if kind == "paragraph" and not any(anc.tag in (w("tc"), w("txbxContent"))
                                                   for anc in para.iterancestors()):
                    counters["paragraph"] = counters.get("paragraph", 0) + 1
                continue
            seg.location = _word_location(para, kind, counters, numbering)
            segments.append(seg)
    return segments


# ---------------------------------------------------------------------------
# PowerPoint (DrawingML text, also used for shapes in other files)
# ---------------------------------------------------------------------------

def _drawing_pieces(para):
    out = []
    for child in para:
        if child.tag == a("r"):
            t = child.find(a("t"))
            if t is not None:
                out.append(Piece(t, "text"))
        elif child.tag == a("br"):
            out.append(Piece(child, "sep", "\n"))
        elif child.tag == a("fld"):
            # Fields (slide number, date) are regenerated by PowerPoint.
            out.append(Piece(child, "sep", " "))
    return out


def _drawing_segments(pkg, part, location):
    segs = []
    for para in pkg.root(part).iter(a("p")):
        if _in_fallback(para):
            continue
        seg = Segment(part, location, _drawing_pieces(para), preserve_space=False)
        if seg.text.strip():
            segs.append(seg)
    return segs


def load_powerpoint(pkg):
    main = pkg.main_part()
    rels = pkg.rels(main)
    slides = []
    for sld in pkg.root(main).iter(p("sldId")):
        rid = sld.get("{%s}id" % R)
        if rid in rels and pkg.has(rels[rid][1]):
            slides.append(rels[rid][1])
    segments = []
    for n, slide in enumerate(slides, 1):
        segments += _drawing_segments(pkg, slide, ("slide", n))
        for rtype, target in pkg.rels(slide).values():
            if rtype == "notesSlide" and pkg.has(target):
                segments += _notes_segments(pkg, target, n)
    return segments


def _notes_segments(pkg, part, n):
    """Only the notes text, not the slide image or slide-number placeholders."""
    segs = []
    root = pkg.root(part)
    for sp in root.iter(p("sp")):
        ph = sp.find(".//" + p("ph"))
        if ph is None or ph.get("type") not in (None, "body"):
            continue
        body = sp.find(p("txBody"))
        if body is None:
            continue
        for para in body.iter(a("p")):
            seg = Segment(part, ("notes", n), _drawing_pieces(para), preserve_space=False)
            if seg.text.strip():
                segs.append(seg)
    return segs


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------

_CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def _col_number(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def _string_pieces(container):
    """Pieces of a shared string <si> or inline string <is>."""
    out = []
    for child in container:
        if child.tag == s("t"):
            out.append(Piece(child, "text"))
        elif child.tag == s("r"):
            t = child.find(s("t"))
            if t is not None:
                out.append(Piece(t, "text"))
        # <rPh> is a phonetic guide for East Asian text, not the cell text
    return out


def load_excel(pkg):
    main = pkg.main_part()
    rels = pkg.rels(main)
    sheets = []
    for sh in pkg.root(main).iter(s("sheet")):
        rid = sh.get("{%s}id" % R)
        if rid in rels and pkg.has(rels[rid][1]) and rels[rid][0] == "worksheet":
            sheets.append((sh.get("name"), rels[rid][1]))

    shared_part = None
    for rtype, target in rels.values():
        if rtype == "sharedStrings" and pkg.has(target):
            shared_part = target
    shared = list(pkg.root(shared_part).iter(s("si"))) if shared_part else []

    used = {}          # shared string index -> [(sheet_no, row, col, sheet_name, ref)]
    inline = []
    for sheet_no, (name, part) in enumerate(sheets):
        raw = pkg.data[part]
        has_inline = b"inlineStr" in raw
        if has_inline:
            cells = pkg.root(part).iter(s("c"))
        else:
            cells = (el for _, el in etree.iterparse(_bytes_io(raw), tag=s("c"), resolve_entities=False,
                                                     huge_tree=True))
        for c in cells:
            ctype = c.get("t")
            ref = c.get("r", "")
            m = _CELL_REF.match(ref)
            row, col = (int(m.group(2)), _col_number(m.group(1))) if m else (0, 0)
            if ctype == "s":
                v = c.find(s("v"))
                if v is not None and v.text and v.text.strip().isdigit():
                    used.setdefault(int(v.text), []).append((sheet_no, row, col, name, ref))
            elif ctype == "inlineStr":
                is_ = c.find(s("is"))
                if is_ is not None:
                    seg = Segment(part, ("cell", name, ref), _string_pieces(is_))
                    if seg.text.strip():
                        inline.append(((sheet_no, row, col), seg))
            if not has_inline:
                c.clear()

    keyed = []
    for idx, places in used.items():
        if idx >= len(shared):
            continue
        places.sort()
        seg = Segment(shared_part, None, _string_pieces(shared[idx]))
        if not seg.text.strip():
            continue
        _, _, _, name, ref = places[0]
        seg.location = ("cell", name, ref) if len(places) == 1 else ("cells", name, ref, len(places) - 1)
        keyed.append((places[0][:3], seg))
    keyed += inline
    keyed.sort(key=lambda kv: kv[0])
    return [seg for _, seg in keyed]


def _bytes_io(raw):
    import io
    return io.BytesIO(raw)


# ---------------------------------------------------------------------------
# The Source used by the window
# ---------------------------------------------------------------------------

def _natural(name):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", name)]


def kind_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in LEGACY:
        raise UnsupportedFile("legacy")
    if ext not in SUPPORTED:
        raise UnsupportedFile(ext or "no extension")
    return {"d": "word", "x": "excel", "p": "powerpoint"}[ext[1]]


class FileSource(Source):
    savable = True

    def __init__(self, path):
        self.path = path
        self.kind = kind_of(path)
        self.title = os.path.basename(path)
        self.pkg = Package(path)
        loader = {"word": load_word, "excel": load_excel, "powerpoint": load_powerpoint}[self.kind]
        self.segments = loader(self.pkg)

    def units(self):
        return [Unit(text=seg.text, location=seg.location, handle=seg) for seg in self.segments]

    def _replace_in_unit(self, unit, start, end, new):
        seg = unit.handle
        seg.replace(start, end, new)
        self.pkg.dirty.add(seg.part)

    def save(self, path=None):
        self.pkg.save(path or self.path)
        self.path = path or self.path
        self.dirty = False
