import json

import pytest

from offspell.__main__ import main

docx = pytest.importorskip("docx")


def test_check_command(tmp_path, monkeypatch, real_speller):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path = tmp_path / "a.docx"
    d = docx.Document()
    d.add_paragraph("Монгл улсын шүүх шийдвр гаргав. The cuort agreed.")
    d.save(path)
    out = tmp_path / "out.json"
    code = main(["check", str(path), "--json", "--suggest", "2", "--output", str(out), "--no-personal"])
    assert code == 1
    rows = json.loads(out.read_text(encoding="utf-8"))
    assert [(r["word"], r["where"]) for r in rows] == [
        ("Монгл", "Paragraph 1"), ("шийдвр", "Paragraph 1"), ("cuort", "Paragraph 1")]
    assert rows[0]["suggestions"][0] == "Монгол"

    clean = tmp_path / "b.docx"
    d = docx.Document()
    d.add_paragraph("Монгол улсын шүүх шийдвэр гаргав.")
    d.save(clean)
    assert main(["check", str(clean), "--no-personal"]) == 0
