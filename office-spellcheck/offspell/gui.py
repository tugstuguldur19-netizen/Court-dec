"""The window (Tkinter, part of Python, so nothing extra to install)."""

import locale
import os
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from . import live, paths
from . import text as T
from .check import build_issues, find_hits
from .engine import Options, Speller
from .i18n import tr, where
from .ooxml import SUPPORTED, FileSource, UnsupportedFile

MAX_SUGGESTIONS = 8


def _default_lang():
    try:
        if sys.platform == "win32":
            import ctypes
            # 0x50 is the primary language id for Mongolian
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x50:
                return "mn"
        code = (locale.getlocale()[0] or os.environ.get("LANG", "")).lower()
        return "mn" if code.startswith(("mn", "mongolian")) else "en"
    except Exception:
        return "en"


class Worker:
    """One background thread for all dictionary work, so the speller is never
    used from two threads at once. Results come back to the GUI thread
    through post(), which the window drains every 40 ms."""

    def __init__(self, root):
        self.root = root
        self.jobs = queue.Queue()
        self.results = queue.Queue()
        threading.Thread(target=self._run, daemon=True).start()
        self._drain()

    def submit(self, fn, *args):
        self.jobs.put((fn, args))

    def post(self, fn, *args):
        self.results.put((fn, args))

    def _run(self):
        while True:
            fn, args = self.jobs.get()
            try:
                fn(*args)
            except Exception as e:  # report, keep the thread alive
                self.post(self._report, e)

    def _report(self, e):
        messagebox.showerror("Error", "%s: %s" % (type(e).__name__, e))

    def _drain(self):
        try:
            while True:
                fn, args = self.results.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.root.after(40, self._drain)


class App:
    def __init__(self, root, open_path=None, live_kind=None):
        self.root = root
        self.settings = paths.load_settings()
        self.lang = self.settings.get("lang") or _default_lang()
        opts = Options(
            ignore_uppercase=self.settings.get("ignore_uppercase", True),
            ignore_with_digits=self.settings.get("ignore_with_digits", True),
            check_latin=self.settings.get("check_latin", True),
        )
        self.speller = Speller(paths.dictionary_folders(), paths.personal_dictionary(), opts)
        self.ready = False
        self.source = None
        self.pending = None          # a source waiting for the dictionaries
        self.issues = []
        self.current = None
        self.suggest_gen = 0
        self.scan_gen = 0
        self.suggest_cache = {}
        self.texts = []              # (widget, key) pairs to re-translate

        self.worker = Worker(root)
        self._build()
        self._retranslate()
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self.worker.submit(self._load_dictionaries)
        if open_path:
            root.after(100, lambda: self.open_path(open_path))
        elif live_kind in live.SOURCES and live.available():
            root.after(100, lambda: self.open_live(live_kind))

    # ------------------------------------------------------------ layout

    def _t(self, widget, key, attr="text"):
        self.texts.append((widget, key, attr))
        return widget

    def _build(self):
        root = self.root
        root.minsize(760, 480)
        root.geometry(self.settings.get("geometry", "980x620"))
        base = tkfont.nametofont("TkDefaultFont")
        self.big = base.copy()
        self.big.configure(size=max(11, base.cget("size") + 2))
        self.bold = base.copy()
        self.bold.configure(weight="bold")

        bar = ttk.Frame(root, padding=(8, 8, 8, 4))
        bar.pack(fill="x")
        self._t(ttk.Button(bar, command=self.ask_open), "open_file").pack(side="left")
        if live.available():
            for kind, key in (("word", "check_word"), ("excel", "check_excel"), ("powerpoint", "check_powerpoint")):
                self._t(ttk.Button(bar, command=lambda k=kind: self.open_live(k)), key).pack(side="left", padx=(6, 0))
        self.recheck_btn = self._t(ttk.Button(bar, command=self.recheck, state="disabled"), "recheck")
        self.recheck_btn.pack(side="left", padx=(12, 0))
        self._t(ttk.Button(bar, command=self.toggle_lang, width=9), "language").pack(side="right")

        body = ttk.PanedWindow(root, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=4)
        # give the list enough room for all three columns once the window is shown
        root.after(80, lambda: body.sashpos(0, max(360, int(root.winfo_width() * 0.4))))

        left = ttk.Frame(body)
        self.tree = ttk.Treeview(left, columns=("word", "where", "status"), show="headings", selectmode="browse")
        self.tree.column("word", width=120, minwidth=80, anchor="w")
        self.tree.column("where", width=130, minwidth=80, anchor="w")
        self.tree.column("status", width=130, minwidth=60, anchor="w")
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="left", fill="y")
        self.tree.tag_configure("done", foreground="#7d7e78")
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        body.add(left, weight=2)

        right = ttk.Frame(body, padding=(10, 0, 0, 0))
        body.add(right, weight=3)
        self._t(ttk.Label(right), "not_in_dict").pack(anchor="w")
        self.context = tk.Text(right, height=6, wrap="word", font=self.big, relief="solid", borderwidth=1,
                               padx=8, pady=6, cursor="arrow")
        self.context.tag_configure("err", foreground="#c62828", underline=True, font=self._bold_big())
        self.context.configure(state="disabled")
        self.context.pack(fill="x", pady=(2, 8))

        mid = ttk.Frame(right)
        mid.pack(fill="both", expand=True)
        sug = ttk.Frame(mid)
        sug.pack(side="left", fill="both", expand=True)
        self._t(ttk.Label(sug), "suggestions").pack(anchor="w")
        self.sugg = tk.Listbox(sug, height=8, font=self.big, activestyle="none", exportselection=False)
        self.sugg.pack(fill="both", expand=True, pady=(2, 6))
        self.sugg.bind("<<ListboxSelect>>", self._on_sugg_select)
        self.sugg.bind("<Double-Button-1>", lambda e: self.change())
        row = ttk.Frame(sug)
        row.pack(fill="x")
        self._t(ttk.Label(row), "change_to").pack(side="left")
        self.change_var = tk.StringVar()
        self.entry = ttk.Entry(row, textvariable=self.change_var, font=self.big)
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        self.entry.bind("<Return>", lambda e: self.change())

        btns = ttk.Frame(mid, padding=(10, 18, 0, 0))
        btns.pack(side="left", fill="y")
        self.action_btns = []
        for key, cmd in (("change", self.change), ("change_all", self.change_all), (None, None),
                         ("ignore", self.ignore), ("ignore_all", self.ignore_all), (None, None),
                         ("add", self.add_word)):
            if key is None:
                ttk.Frame(btns, height=10).pack()
                continue
            b = self._t(ttk.Button(btns, command=cmd, state="disabled"), key)
            b.pack(fill="x", pady=2)
            self.action_btns.append(b)

        bottom = ttk.Frame(root, padding=(8, 4, 8, 8))
        bottom.pack(fill="x")
        self.opt_vars = {}
        for name, key in (("ignore_uppercase", "opt_upper"), ("ignore_with_digits", "opt_digits"),
                          ("check_latin", "opt_latin")):
            var = tk.BooleanVar(value=getattr(self.speller.options, name))
            self.opt_vars[name] = var
            self._t(ttk.Checkbutton(bottom, variable=var, command=self._options_changed), key).pack(side="left", padx=(0, 12))
        self.save_btn = self._t(ttk.Button(bottom, command=self.save, state="disabled"), "save")
        self.save_btn.pack(side="right")

        status = ttk.Frame(root, padding=(8, 0, 8, 6))
        status.pack(fill="x")
        self.progress = ttk.Progressbar(status, length=160, mode="determinate")
        self.progress.pack(side="right")
        self.status = ttk.Label(status, anchor="w")
        self.status.pack(side="left", fill="x", expand=True)

        root.bind_all("<Control-o>", lambda e: self.ask_open())
        self.sugg.bind("<Return>", lambda e: self.change())

    def _bold_big(self):
        f = self.big.copy()
        f.configure(weight="bold")
        return f

    def _retranslate(self):
        self.root.title(tr("app_title", self.lang))
        for widget, key, attr in self.texts:
            widget.configure(**{attr: tr(key, self.lang)})
        for col, key in (("word", "col_word"), ("where", "col_where"), ("status", "col_status")):
            self.tree.heading(col, text=tr(key, self.lang))
        for idx, issue in enumerate(self.issues):
            self.tree.item(str(idx), values=self._row(issue))
        if self.current is None:
            self._show_hint()
        self._refresh_status()

    def toggle_lang(self):
        self.lang = "en" if self.lang == "mn" else "mn"
        self._retranslate()

    # ------------------------------------------------------------ dictionaries

    def _load_dictionaries(self):
        try:
            names = self.speller.load(
                progress=lambda n: self.worker.post(self._set_status, tr("loading", self.lang, name=n)))
        except Exception as e:
            self.worker.post(self._dictionaries_failed, e)
            return
        self.worker.post(self._dictionaries_loaded, names)

    def _dictionaries_failed(self, err):
        self.ready = True
        self.pending = None
        self._set_status(tr("no_dicts", self.lang, path=self.speller.dictionary_folders[-1]))
        messagebox.showerror(tr("app_title", self.lang), "%s: %s" % (type(err).__name__, err))

    def _dictionaries_loaded(self, names):
        self.ready = True
        if not names:
            self._set_status(tr("no_dicts", self.lang, path=self.speller.dictionary_folders[-1]))
            return
        self._refresh_status()
        if self.pending:
            src, self.pending = self.pending, None
            self.start_scan(src)

    # ------------------------------------------------------------ opening

    def _confirm_discard(self):
        if self.source is not None and self.source.savable and self.source.dirty:
            return messagebox.askyesno(tr("app_title", self.lang), tr("unsaved", self.lang), icon="warning")
        return True

    def ask_open(self):
        pattern = " ".join("*" + e for e in SUPPORTED)
        path = filedialog.askopenfilename(
            parent=self.root,
            filetypes=[(tr("filetypes_office", self.lang), pattern), (tr("filetypes_all", self.lang), "*.*")],
            initialdir=self.settings.get("last_dir") or os.path.expanduser("~"))
        if path:
            self.open_path(path)

    def open_path(self, path):
        if not self._confirm_discard():
            return
        try:
            src = FileSource(path)
        except UnsupportedFile as e:
            msg = tr("legacy", self.lang) if str(e) == "legacy" else tr("open_failed", self.lang, err=e)
            messagebox.showerror(tr("app_title", self.lang), msg)
            return
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("open_failed", self.lang, err=e))
            return
        self.settings["last_dir"] = os.path.dirname(os.path.abspath(path))
        self.start_scan(src)

    def open_live(self, kind):
        if not self._confirm_discard():
            return
        cls = live.SOURCES[kind]
        try:
            src = cls()
        except live.NotRunning:
            messagebox.showinfo(tr("app_title", self.lang), tr("not_running", self.lang, app=cls.app_name))
            return
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("live_failed", self.lang, app=cls.app_name, err=e))
            return
        self.start_scan(src)

    def recheck(self):
        if self.source is not None:
            self.start_scan(self.source)

    # ------------------------------------------------------------ checking

    def start_scan(self, src):
        if self.source is not None and self.source is not src:
            self.source.close()
        self.source = src
        self._clear_issues()
        if not self.ready:
            self.pending = src
            self._set_status(tr("wait_dicts", self.lang))
            return
        try:
            units = src.units()   # Office calls stay on this thread
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("live_failed", self.lang, app=src.title, err=e))
            return
        self.recheck_btn.configure(state="disabled")
        self.progress.configure(value=0, maximum=max(1, len(units)))
        self.scan_gen += 1
        gen = self.scan_gen

        def progress(done, total):
            self.worker.post(self._scan_progress, gen, done, total)

        def job():
            if gen != self.scan_gen:
                return   # a newer check was started meanwhile
            results = find_hits(self.speller, units, progress, cancelled=lambda: gen != self.scan_gen)
            self.worker.post(self._scan_done, gen, src, units, results)

        self.worker.submit(job)

    def _scan_progress(self, gen, done, total):
        if gen != self.scan_gen:
            return
        self.progress.configure(value=done, maximum=max(1, total))
        self._set_status(tr("checking", self.lang, done=done, total=total))

    def _scan_done(self, gen, src, units, results):
        if gen != self.scan_gen or src is not self.source:
            return
        try:
            self.issues = build_issues(src, units, results)
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("live_failed", self.lang, app=src.title, err=e))
            self.issues = []
        self.recheck_btn.configure(state="normal")
        for idx, issue in enumerate(self.issues):
            self.tree.insert("", "end", iid=str(idx), values=self._row(issue))
        self._refresh_status()
        self._update_save()
        if self.issues:
            self._select(0)
        else:
            self._show_message(tr("result_none", self.lang, title=src.title))

    def _clear_issues(self):
        self.issues = []
        self.current = None
        self.tree.delete(*self.tree.get_children())
        self._set_buttons(False)
        self._show_hint()

    # ------------------------------------------------------------ the list

    def _row(self, issue):
        if issue.status == "open":
            st = ""
        elif issue.status == "fixed":
            st = tr("status_fixed", self.lang, new=issue.replacement)
        else:
            st = tr("status_" + issue.status, self.lang)
        return (issue.word, where(issue.location, self.lang), st)

    def _on_tree_select(self, _event):
        sel = self.tree.selection()
        if sel and int(sel[0]) != self.current:
            self._show(int(sel[0]))

    def _select(self, idx):
        self.tree.selection_set(str(idx))
        self.tree.see(str(idx))
        self._show(idx)

    def _show(self, idx):
        self.current = idx
        issue = self.issues[idx]
        text, s, e = self.source.context(issue)
        if not isinstance(self.source, live.WordSource):
            text, s, e = T.context(text, s, e)
        self._set_context(text, s, e)
        self.source.select(issue)
        is_open = issue.status == "open"
        self._set_buttons(is_open)
        self.change_var.set(issue.replacement if issue.status == "fixed" else issue.word)
        self._load_suggestions(issue.word)

    def _set_context(self, text, s, e):
        c = self.context
        c.configure(state="normal")
        c.delete("1.0", "end")
        c.insert("1.0", text.replace("\r", "\n").replace("\x0b", "\n").replace("\x07", ""))
        if e > s:
            c.tag_add("err", "1.0 + %d chars" % s, "1.0 + %d chars" % e)
            c.see("1.0 + %d chars" % s)
        c.configure(state="disabled")

    def _show_hint(self):
        self._set_context(tr("start_hint", self.lang), 0, 0)
        self.sugg.delete(0, "end")
        self.change_var.set("")

    def _show_message(self, msg):
        self.current = None
        self._set_context(msg, 0, 0)
        self.sugg.delete(0, "end")
        self.change_var.set("")
        self._set_buttons(False)

    def _set_buttons(self, enabled):
        for b in self.action_btns:
            b.configure(state="normal" if enabled else "disabled")

    # ------------------------------------------------------------ suggestions

    def _load_suggestions(self, word):
        self.suggest_gen += 1
        gen = self.suggest_gen
        self.sugg.delete(0, "end")
        cached = self.suggest_cache.get(word)
        if cached is not None:
            self._fill_suggestions(cached, done=True)
            return
        self.sugg.insert("end", tr("finding", self.lang))
        self.sugg.itemconfigure(0, foreground="#7d7e78")

        def job():
            found = []
            if gen != self.suggest_gen:
                return
            for s in self.speller.suggest(word, limit=MAX_SUGGESTIONS):
                if gen != self.suggest_gen:
                    return        # the user moved on; don't cache a partial list
                found.append(s)
                self.worker.post(self._suggestion_arrived, gen, list(found))
            self.suggest_cache[word] = found
            self.worker.post(self._suggestions_done, gen, found)

        self.worker.submit(job)

    def _suggestion_arrived(self, gen, found):
        if gen == self.suggest_gen:
            self._fill_suggestions(found, done=False)

    def _suggestions_done(self, gen, found):
        if gen == self.suggest_gen:
            self._fill_suggestions(found, done=True)

    def _fill_suggestions(self, found, done):
        first_fill = self.sugg.size() == 0 or self.sugg.get(0) == tr("finding", self.lang)
        keep = self.sugg.curselection()
        self.sugg.delete(0, "end")
        for s in found:
            self.sugg.insert("end", s)
        if not done:
            self.sugg.insert("end", tr("finding", self.lang))
            self.sugg.itemconfigure("end", foreground="#7d7e78")
        elif not found:
            self.sugg.insert("end", tr("no_suggestions", self.lang))
            self.sugg.itemconfigure("end", foreground="#7d7e78")
        if not found:
            return
        if keep and keep[0] < len(found):
            self.sugg.selection_set(keep[0])
        elif first_fill and self.current is not None and self.issues[self.current].status == "open":
            self.sugg.selection_set(0)
            if self.change_var.get() == self.issues[self.current].word:   # not typed over by the user
                self.change_var.set(found[0])

    def _on_sugg_select(self, _event):
        sel = self.sugg.curselection()
        if not sel:
            return
        value = self.sugg.get(sel[0])
        if value in (tr("finding", self.lang), tr("no_suggestions", self.lang)):
            return
        self.change_var.set(value)

    # ------------------------------------------------------------ actions

    def _issue(self):
        if self.current is None:
            return None
        issue = self.issues[self.current]
        return issue if issue.status == "open" else None

    def _mark(self, issue, status, replacement=""):
        issue.status = status
        issue.replacement = replacement
        idx = self.issues.index(issue)
        self.tree.item(str(idx), values=self._row(issue), tags=("done",))

    def _replace(self, issue, new):
        try:
            self.source.replace(issue, new)
        except live.StaleIssue:
            messagebox.showwarning(tr("app_title", self.lang), tr("edit_failed", self.lang, err=tr("recheck", self.lang)))
            return False
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("edit_failed", self.lang, err=e))
            return False
        self._mark(issue, "fixed", new)
        return True

    def change(self):
        issue = self._issue()
        if not issue:
            return
        new = self.change_var.get().strip()
        if not new or new == issue.word:
            return self.ignore()
        if self._replace(issue, new):
            self._after_action()

    def change_all(self):
        issue = self._issue()
        if not issue:
            return
        new = self.change_var.get().strip()
        if not new or new == issue.word:
            return self.ignore_all()
        for other in [i for i in self.issues if i.status == "open" and i.word == issue.word]:
            if not self._replace(other, new):
                break
        self._after_action()

    def ignore(self):
        issue = self._issue()
        if issue:
            self._mark(issue, "ignored")
            self._after_action()

    def ignore_all(self):
        issue = self._issue()
        if not issue:
            return
        self.speller.ignore(issue.word)
        for other in self.issues:
            if other.status == "open" and other.word == issue.word:
                self._mark(other, "ignored")
        self._after_action()

    def add_word(self):
        issue = self._issue()
        if not issue:
            return
        self.speller.add_to_personal(issue.word)
        for other in self.issues:
            if other.status == "open" and other.word in self.speller.personal:
                self._mark(other, "added")
        self._after_action()

    def _after_action(self):
        self._update_save()
        self._refresh_status()
        n = len(self.issues)
        start = self.current if self.current is not None else -1
        for step in range(1, n + 1):
            idx = (start + step) % n
            if self.issues[idx].status == "open":
                self._select(idx)
                return
        msg = tr("done_all", self.lang)
        if self.source is not None and not self.source.savable and self.source.dirty:
            msg += "\n\n" + tr("live_saved_hint", self.lang, app=self.source.app_name)
        self._show_message(msg)

    def _options_changed(self):
        opts = Options(**{k: v.get() for k, v in self.opt_vars.items()})
        for k, v in self.opt_vars.items():
            self.settings[k] = v.get()
        if self.ready:
            self.speller.set_options(opts)
        else:
            self.speller.options = opts
        self.recheck()

    # ------------------------------------------------------------ saving

    def _update_save(self):
        ok = self.source is not None and self.source.savable and self.source.dirty
        self.save_btn.configure(state="normal" if ok else "disabled")

    def save(self):
        src = self.source
        if src is None or not src.savable:
            return
        folder, name = os.path.split(src.path)
        stem, ext = os.path.splitext(name)
        suffix = tr("corrected_suffix", self.lang)
        if not stem.endswith(suffix):
            stem += suffix
        path = filedialog.asksaveasfilename(
            parent=self.root, initialdir=folder, initialfile=stem + ext,
            defaultextension=ext, filetypes=[(ext.upper().lstrip("."), "*" + ext)])
        if not path:
            return
        try:
            src.save(path)
        except Exception as e:
            messagebox.showerror(tr("app_title", self.lang), tr("save_failed", self.lang, err=e))
            return
        src.title = os.path.basename(path)
        self._update_save()
        self._set_status(tr("saved", self.lang, path=path))

    # ------------------------------------------------------------ status

    def _set_status(self, msg):
        self.status.configure(text=msg)

    def _refresh_status(self):
        if not self.ready:
            return
        if self.source is None:
            self._set_status(tr("loaded", self.lang, names=", ".join(self.speller.languages) or "—"))
            return
        open_n = sum(1 for i in self.issues if i.status == "open")
        key = "result" if self.issues else "result_none"
        self._set_status(tr(key, self.lang, title=self.source.title, n=open_n))

    def quit(self):
        if not self._confirm_discard():
            return
        self.settings["lang"] = self.lang
        try:
            self.settings["geometry"] = self.root.winfo_geometry()
        except tk.TclError:
            pass
        paths.save_settings(self.settings)
        if self.source is not None:
            self.source.close()
        self.root.destroy()


def run(path=None, live_kind=None):
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)   # sharp text on high-DPI screens
        except Exception:
            pass
    root = tk.Tk()
    style = ttk.Style(root)
    if sys.platform != "win32" and "clam" in style.theme_names():
        style.theme_use("clam")
    App(root, open_path=path, live_kind=live_kind)
    root.mainloop()
    return 0
