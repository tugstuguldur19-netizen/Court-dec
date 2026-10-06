"""Entry point.

    python -m offspell                    open the window
    python -m offspell FILE               open the window and check FILE
    python -m offspell --live word        open the window and check the open Word
                                          document (also: excel, powerpoint)
    python -m offspell check FILE...      list possible errors in Office files
"""

import argparse
import json
import sys

from . import paths


def _speller(args):
    from .engine import Options, Speller

    opts = Options(
        ignore_uppercase=not args.check_uppercase,
        ignore_with_digits=not args.check_digits,
        check_latin=not args.no_english,
    )
    folders = paths.dictionary_folders() + (args.dict or [])
    sp = Speller(folders, None if args.no_personal else paths.personal_dictionary(), opts)
    if not sp.load():
        sys.exit("No dictionaries found. Run fetch_dictionaries.py or use --dict FOLDER.")
    return sp


def cmd_check(args):
    from .check import scan
    from .i18n import where
    from .ooxml import FileSource, UnsupportedFile

    sp = _speller(args)
    found = 0
    report = []
    out = open(args.output, "w", encoding="utf-8") if args.output else sys.stdout
    for path in args.files:
        try:
            src = FileSource(path)
        except (UnsupportedFile, OSError) as e:
            if sys.stderr:
                print("%s: cannot read (%s)" % (path, e), file=sys.stderr)
            report.append({"file": path, "error": str(e)})
            continue
        for issue in scan(src, sp):
            found += 1
            sugg = list(sp.suggest(issue.word, limit=args.suggest)) if args.suggest else []
            row = {"file": path, "word": issue.word, "where": where(issue.location, args.lang),
                   "context": issue.unit.text, "suggestions": sugg}
            report.append(row)
            if not args.json:
                line = "%s\t%s\t%s" % (path, row["where"], issue.word)
                if sugg:
                    line += "\t→ " + ", ".join(sugg)
                print(line, file=out)
    if args.json:
        json.dump(report, out, ensure_ascii=False, indent=2)
        print(file=out)
    if out is not sys.stdout:
        out.close()
    return 1 if found else 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] not in (["check"], ["-h"], ["--help"]):
        from .gui import run
        if argv[:1] == ["--live"] and len(argv) > 1:
            return run(live_kind=argv[1].lower())
        # "OfficeSpellcheck.exe report.docx", or a file dropped on the icon
        return run(path=argv[0] if argv else None)
    parser = argparse.ArgumentParser(prog="offspell", description="Offline spellchecker for Word, Excel and PowerPoint")
    sub = parser.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="list possible spelling errors in .docx/.xlsx/.pptx files")
    c.add_argument("files", nargs="+")
    c.add_argument("--suggest", type=int, default=0, metavar="N", help="also show up to N suggestions per word")
    c.add_argument("--json", action="store_true", help="print the result as JSON")
    c.add_argument("--output", metavar="FILE", help="write the result to FILE instead of the screen")
    c.add_argument("--lang", choices=["en", "mn"], default="en", help="language of location labels")
    c.add_argument("--dict", action="append", metavar="FOLDER", help="extra folder with .aff/.dic or .txt word lists")
    c.add_argument("--check-uppercase", action="store_true", help="also check words in UPPERCASE")
    c.add_argument("--check-digits", action="store_true", help="also check words that contain digits")
    c.add_argument("--no-english", action="store_true", help="do not check Latin-alphabet words")
    c.add_argument("--no-personal", action="store_true", help="ignore the personal dictionary")
    args = parser.parse_args(argv)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
