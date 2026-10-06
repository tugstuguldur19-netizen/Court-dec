"""Drive the window: open a file, fix words, save. Skipped without a display."""

import time

import pytest

tk = pytest.importorskip("tkinter")
docx = pytest.importorskip("docx")

from conftest import DATA  # noqa: E402
from offspell import gui, paths  # noqa: E402


@pytest.fixture
def root(monkeypatch, tmp_path):
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    monkeypatch.setattr(paths, "dictionary_folders", lambda: [DATA])
    monkeypatch.setattr(paths, "user_dir", lambda: str(tmp_path / "user"))
    yield r
    try:
        r.destroy()
    except tk.TclError:
        pass


def pump(root, cond, timeout=30):
    end = time.time() + timeout
    while time.time() < end:
        root.update()
        if cond():
            return
        time.sleep(0.02)
    raise AssertionError("timed out")


def test_open_fix_save(root, tmp_path, monkeypatch):
    src = tmp_path / "in.docx"
    d = docx.Document()
    d.add_paragraph("Монгол улс шүүхй cuort шүүхй.")
    d.save(src)
    out = tmp_path / "out.docx"
    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda **kw: str(out))
    errors = []
    for name in ("showerror", "showwarning", "showinfo", "askyesno"):   # never block the test on a dialog
        monkeypatch.setattr(gui.messagebox, name, lambda *a, **k: errors.append(a))

    app = gui.App(root, open_path=str(src))
    pump(root, lambda: app.issues)
    assert [i.word for i in app.issues] == ["шүүхй", "cuort", "шүүхй"]
    # suggestions stream in and the first one is put in the "Change to" box
    pump(root, lambda: app.change_var.get() == "шүүх")
    app.change_all()
    assert [i.status for i in app.issues] == ["fixed", "open", "fixed"]
    assert app.current == 1                       # moved on to the next open word
    app.change_var.set("court")
    app.change()
    assert str(app.save_btn.cget("state")) == "normal"
    app.save()
    assert not errors
    assert docx.Document(str(out)).paragraphs[0].text == "Монгол улс шүүх court шүүх."

    app.toggle_lang()
    assert app.tree.heading("word")["text"] == "Үг"
    app.quit()
