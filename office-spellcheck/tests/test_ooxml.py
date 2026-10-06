"""Reading and correcting real Office files.

The fixtures are built with python-docx, openpyxl and python-pptx (test-only
dependencies), then corrected with offspell and read back with the same
libraries to prove the files are still valid and the formatting survived.
"""

import zipfile

import pytest

from offspell.check import scan
from offspell.ooxml import FileSource, UnsupportedFile

docx = pytest.importorskip("docx")
openpyxl = pytest.importorskip("openpyxl")
pptx = pytest.importorskip("pptx")


def fix_all(src, speller, mapping):
    issues = scan(src, speller)
    for issue in issues:
        if issue.word in mapping:
            src.replace(issue, mapping[issue.word])
    return issues


# ---------------------------------------------------------------- Word

def make_docx(path):
    d = docx.Document()
    p = d.add_paragraph()
    p.add_run("Монгол ")
    bold = p.add_run("шүү")       # the misspelled word is split over two runs
    bold.bold = True
    p.add_run("хй шийдвэр, cuort.")
    d.add_paragraph("")
    d.add_paragraph("улс шийдвр улс шийдвр")
    t = d.add_table(rows=2, cols=2)
    t.cell(1, 0).text = "гэрээ гэрээй"
    d.sections[0].header.paragraphs[0].text = "Монгл улс"
    d.sections[0].footer.paragraphs[0].text = "шүүх"
    d.save(path)


def test_docx_find_and_fix(tmp_path, speller):
    path = tmp_path / "a.docx"
    make_docx(path)
    src = FileSource(str(path))
    issues = fix_all(src, speller, {"шүүхй": "шүүх", "cuort": "court", "шийдвр": "шийдвэр",
                                    "гэрээй": "гэрээ", "Монгл": "Монгол"})
    assert [(i.word, i.location) for i in issues] == [
        ("шүүхй", ("paragraph", 1)),
        ("cuort", ("paragraph", 1)),
        ("шийдвр", ("paragraph", 3)),
        ("шийдвр", ("paragraph", 3)),
        ("гэрээй", ("table", 1, 2, 1)),
        ("Монгл", ("header", 1)),
    ]
    out = tmp_path / "b.docx"
    src.save(str(out))

    d = docx.Document(str(out))
    para = d.paragraphs[0]
    assert para.text == "Монгол шүүх шийдвэр, court."
    # the corrected word took the formatting of the run where it started
    assert [(r.text, bool(r.bold)) for r in para.runs] == [
        ("Монгол ", False), ("шүүх", True), (" шийдвэр, court.", False)]
    assert d.paragraphs[2].text == "улс шийдвэр улс шийдвэр"
    assert d.tables[0].cell(1, 0).text == "гэрээ гэрээ"
    assert d.sections[0].header.paragraphs[0].text == "Монгол улс"
    # nothing left to fix
    assert scan(FileSource(str(out)), speller) == []


def test_docx_untouched_parts_are_identical(tmp_path, speller):
    path = tmp_path / "a.docx"
    make_docx(path)
    src = FileSource(str(path))
    fix_all(src, speller, {"cuort": "court"})
    out = tmp_path / "b.docx"
    src.save(str(out))
    with zipfile.ZipFile(path) as a, zipfile.ZipFile(out) as b:
        assert a.namelist() == b.namelist()
        changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert changed == ["word/document.xml"]


W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' \
       'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"'


def write_raw_docx(path, body_xml):
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>',
        "word/document.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document %s mc:Ignorable=""><w:body>%s</w:body></w:document>' % (W_NS, body_xml),
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)


def test_docx_tracked_changes_fields_and_hyphens(tmp_path, speller):
    body = (
        # deleted text and field codes are not checked; inserted text is
        '<w:p><w:del><w:r><w:delText>cuort</w:delText></w:r></w:del>'
        '<w:ins><w:r><w:t xml:space="preserve">шүүхй </w:t></w:r></w:ins>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>PAGEE xyzzy</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
        # a non-breaking hyphen element inside a word
        '<w:p><w:r><w:t>нийгэм</w:t></w:r><w:r><w:noBreakHyphen/></w:r><w:r><w:t>эдйн</w:t></w:r></w:p>'
        # a tab separates words
        '<w:p><w:r><w:t>улс</w:t><w:tab/><w:t>гэрээй</w:t></w:r></w:p>'
        # text box: Word writes it twice, the copy in mc:Fallback is skipped
        '<w:p><w:r><mc:AlternateContent><mc:Choice Requires="wps"><w:drawing><w:txbxContent>'
        '<w:p><w:r><w:t>Монгл</w:t></w:r></w:p></w:txbxContent></w:drawing></mc:Choice>'
        '<mc:Fallback><w:pict><w:txbxContent><w:p><w:r><w:t>Монгл</w:t></w:r></w:p></w:txbxContent>'
        '</w:pict></mc:Fallback></mc:AlternateContent></w:r></w:p>'
        # runs wrapped in alternate content directly in a paragraph
        '<w:p><mc:AlternateContent><mc:Choice Requires="w14"><w:r><w:t>гэрээй хууль</w:t></w:r></mc:Choice>'
        '<mc:Fallback><w:r><w:t>гэрээй хууль</w:t></w:r></mc:Fallback></mc:AlternateContent></w:p>'
    )
    path = tmp_path / "raw.docx"
    write_raw_docx(path, body)
    src = FileSource(str(path))
    issues = scan(src, speller)
    assert [(i.word, i.location) for i in issues] == [
        ("шүүхй", ("paragraph", 1)),
        ("нийгэм-эдйн", ("paragraph", 2)),
        ("гэрээй", ("paragraph", 3)),
        ("Монгл", ("textbox",)),
        ("гэрээй", ("paragraph", 5)),
    ]
    for issue, new in zip(issues, ["шүүх", "нийгэм-эдийн", "гэрээ", "Монгол", "гэрээ"]):
        src.replace(issue, new)
    out = tmp_path / "out.docx"
    src.save(str(out))
    with zipfile.ZipFile(out) as z:
        xml = z.read("word/document.xml").decode("utf-8")
    assert "<w:delText>cuort</w:delText>" in xml          # deleted text untouched
    assert '<w:t xml:space="preserve">шүүх </w:t>' in xml
    assert "noBreakHyphen" not in xml                      # replaced by a plain hyphen
    assert "<w:t>нийгэм-эдийн</w:t>" in xml
    assert 'mc:Ignorable=""' in xml                        # namespaces kept as they were
    assert docx.Document(str(out)).paragraphs[2].text == "улс\tгэрээ"
    assert '<mc:Choice Requires="w14"><w:r><w:t>гэрээ хууль</w:t>' in xml
    assert [i.word for i in scan(FileSource(str(out)), speller)] == []


# ---------------------------------------------------------------- Excel

def write_excel_style_xlsx(path):
    """A workbook laid out the way Excel saves it: all text in sharedStrings.xml."""
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            '</Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/></Relationships>' % rel,
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook %s xmlns:r="%s"><sheets>'
            '<sheet name="Хэрэг" sheetId="1" r:id="rId1"/><sheet name="Second" sheetId="2" r:id="rId2"/>'
            '</sheets></workbook>' % (ns, rel),
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="%s/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="%s/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="%s/sharedStrings" Target="sharedStrings.xml"/>'
            '</Relationships>' % (rel, rel, rel),
        "xl/sharedStrings.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<sst %s count="5" uniqueCount="4">'
            '<si><t>шийдвэр</t></si>'
            '<si><r><rPr><b/></rPr><t>Монг</t></r><r><t xml:space="preserve">л улс</t></r></si>'
            '<si><t>the cuort of</t></si>'
            '<si><t>unused cuort</t></si>'
            '</sst>' % ns,
        "xl/worksheets/sheet1.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet %s><sheetData>'
            '<row r="1"><c r="A1" t="s"><v>0</v></c></row>'
            '<row r="2"><c r="B2" t="s"><v>1</v></c></row>'
            '<row r="3"><c r="C3"><v>1234</v></c><c r="D3" t="str"><f>"cuort"&amp;"x"</f><v>cuortx</v></c></row>'
            '<row r="5"><c r="A5" t="s"><v>1</v></c></row>'
            '</sheetData></worksheet>' % ns,
        "xl/worksheets/sheet2.xml": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet %s><sheetData><row r="1"><c r="A1" t="s"><v>2</v></c></row></sheetData></worksheet>' % ns,
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


def test_xlsx_shared_strings(tmp_path, speller):
    path = tmp_path / "a.xlsx"
    write_excel_style_xlsx(path)
    src = FileSource(str(path))
    issues = fix_all(src, speller, {"Монгл": "Монгол", "cuort": "court"})
    # a shared string used by two cells is reported once; unused strings and
    # formula results are not reported
    assert [(i.word, i.location) for i in issues] == [
        ("Монгл", ("cells", "Хэрэг", "B2", 1)),
        ("cuort", ("cell", "Second", "A1")),
    ]
    out = tmp_path / "b.xlsx"
    src.save(str(out))
    with zipfile.ZipFile(out) as z:
        sst = z.read("xl/sharedStrings.xml").decode("utf-8")
    # the word now sits in the bold run where it started; the rest stays plain
    assert ('<r><rPr><b/></rPr><t>Монгол</t></r><r><t xml:space="preserve"> улс</t></r>') in sst
    wb = openpyxl.load_workbook(out)
    assert wb["Хэрэг"]["B2"].value == "Монгол улс"
    assert wb["Хэрэг"]["A5"].value == "Монгол улс"
    assert wb["Хэрэг"]["C3"].value == 1234
    assert wb["Хэрэг"]["D3"].value == '="cuort"&"x"'      # formulas are not touched
    assert wb["Second"]["A1"].value == "the court of"


def test_xlsx_from_openpyxl(tmp_path, speller):
    path = tmp_path / "a.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Хэрэг"
    ws["B2"] = "Монгл улс"
    ws["B2"].font = openpyxl.styles.Font(bold=True)
    ws["C3"] = 1234
    ws["D4"] = '=CONCATENATE("cuort", "x")'
    wb.create_sheet("Second")["A1"] = "the cuort of"
    wb.save(path)
    src = FileSource(str(path))
    issues = fix_all(src, speller, {"Монгл": "Монгол", "cuort": "court"})
    assert [(i.word, i.location) for i in issues] == [
        ("Монгл", ("cell", "Хэрэг", "B2")),
        ("cuort", ("cell", "Second", "A1")),
    ]
    out = tmp_path / "b.xlsx"
    src.save(str(out))
    wb2 = openpyxl.load_workbook(out)
    assert wb2["Хэрэг"]["B2"].value == "Монгол улс"
    assert wb2["Хэрэг"]["B2"].font.bold
    assert wb2["Хэрэг"]["D4"].value == '=CONCATENATE("cuort", "x")'
    assert wb2["Second"]["A1"].value == "the court of"


def test_xlsx_inline_strings(tmp_path, speller):
    path = tmp_path / "inline.xlsx"
    wb = openpyxl.Workbook()
    wb.active["A1"] = "x"
    wb.save(path)
    # rewrite the sheet with an inline string cell, as some exporters do
    with zipfile.ZipFile(path) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    sheet = parts["xl/worksheets/sheet1.xml"].decode("utf-8")
    start = sheet.index("<sheetData>")
    end = sheet.index("</sheetData>") + len("</sheetData>")
    sheet = sheet[:start] + ('<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>шүүхй гэрээ</t></is></c>'
                             '</row></sheetData>') + sheet[end:]
    parts["xl/worksheets/sheet1.xml"] = sheet.encode("utf-8")
    with zipfile.ZipFile(path, "w") as z:
        for n, data in parts.items():
            z.writestr(n, data)
    src = FileSource(str(path))
    issues = fix_all(src, speller, {"шүүхй": "шүүх"})
    assert [(i.word, i.location) for i in issues] == [("шүүхй", ("cell", "Sheet", "A1"))]
    src.save(str(path))
    assert openpyxl.load_workbook(path).active["A1"].value == "шүүх гэрээ"


# ---------------------------------------------------------------- PowerPoint

def test_pptx_find_and_fix(tmp_path, speller):
    path = tmp_path / "a.pptx"
    prs = pptx.Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[1])
    s1.shapes.title.text = "Монгл улс"
    body = s1.placeholders[1].text_frame
    body.text = "шийдвэр"
    para = body.add_paragraph()
    r1 = para.add_run()
    r1.text = "the cu"
    r2 = para.add_run()
    r2.text = "ort"
    r2.font.italic = True
    s1.notes_slide.notes_text_frame.text = "гэрээй"
    s2 = prs.slides.add_slide(prs.slide_layouts[5])
    s2.shapes.title.text = "улс"
    tbl = s2.shapes.add_table(1, 2, 0, 0, 3000000, 500000).table
    tbl.cell(0, 1).text = "шүүхй"
    prs.save(path)

    src = FileSource(str(path))
    issues = fix_all(src, speller, {"Монгл": "Монгол", "cuort": "court", "гэрээй": "гэрээ", "шүүхй": "шүүх"})
    assert [(i.word, i.location) for i in issues] == [
        ("Монгл", ("slide", 1)),
        ("cuort", ("slide", 1)),
        ("гэрээй", ("notes", 1)),
        ("шүүхй", ("slide", 2)),
    ]
    out = tmp_path / "b.pptx"
    src.save(str(out))
    prs2 = pptx.Presentation(str(out))
    a, b = prs2.slides
    assert a.shapes.title.text == "Монгол улс"
    runs = a.placeholders[1].text_frame.paragraphs[1].runs
    assert [(r.text, bool(r.font.italic)) for r in runs] == [("the court", False), ("", True)]
    assert a.notes_slide.notes_text_frame.text == "гэрээ"
    assert b.shapes[1].table.cell(0, 1).text == "шүүх"


# ---------------------------------------------------------------- misc

def test_unsupported(tmp_path):
    p = tmp_path / "old.doc"
    p.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(UnsupportedFile):
        FileSource(str(p))
    q = tmp_path / "broken.docx"
    q.write_bytes(b"not a zip")
    with pytest.raises(UnsupportedFile):
        FileSource(str(q))
