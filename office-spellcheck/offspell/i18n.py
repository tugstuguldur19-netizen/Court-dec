"""Interface text in Mongolian and English."""

STRINGS = {
    "app_title": {"en": "Office Spellcheck (offline)", "mn": "Зөв бичгийн шалгагч (офлайн)"},
    "open_file": {"en": "Open file…", "mn": "Файл нээх…"},
    "check_word": {"en": "Open Word document", "mn": "Нээлттэй Word"},
    "check_excel": {"en": "Open Excel workbook", "mn": "Нээлттэй Excel"},
    "check_powerpoint": {"en": "Open PowerPoint", "mn": "Нээлттэй PowerPoint"},
    "recheck": {"en": "Check again", "mn": "Дахин шалгах"},
    "language": {"en": "Монгол", "mn": "English"},
    "loading": {"en": "Loading dictionaries… {name}", "mn": "Толь бичиг ачаалж байна… {name}"},
    "loaded": {"en": "Dictionaries: {names}", "mn": "Толь бичиг: {names}"},
    "no_dicts": {"en": "No dictionaries found. Put .aff/.dic files in: {path}",
                 "mn": "Толь бичиг олдсонгүй. .aff/.dic файлуудыг энд хуулна уу: {path}"},
    "wait_dicts": {"en": "The dictionaries are still loading. The check starts as soon as they are ready.",
                   "mn": "Толь бичиг ачаалж дуусаагүй байна. Дуусмагц шалгаж эхэлнэ."},
    "checking": {"en": "Checking… {done} of {total}", "mn": "Шалгаж байна… {done}/{total}"},
    "result": {"en": "{title}: {n} possible errors", "mn": "{title}: {n} алдаа байж болзошгүй"},
    "result_none": {"en": "{title}: no spelling errors found", "mn": "{title}: алдаа олдсонгүй"},
    "col_word": {"en": "Word", "mn": "Үг"},
    "col_where": {"en": "Where", "mn": "Байршил"},
    "col_status": {"en": "Status", "mn": "Төлөв"},
    "not_in_dict": {"en": "Not in dictionary:", "mn": "Толь бичигт байхгүй:"},
    "suggestions": {"en": "Suggestions:", "mn": "Санал болгох үгс:"},
    "finding": {"en": "Finding suggestions…", "mn": "Зөвлөмж хайж байна…"},
    "no_suggestions": {"en": "(no suggestions)", "mn": "(зөвлөмж алга)"},
    "change_to": {"en": "Change to:", "mn": "Солих үг:"},
    "change": {"en": "Change", "mn": "Солих"},
    "change_all": {"en": "Change all", "mn": "Бүгдийг солих"},
    "ignore": {"en": "Ignore", "mn": "Алгасах"},
    "ignore_all": {"en": "Ignore all", "mn": "Бүгдийг алгасах"},
    "add": {"en": "Add to dictionary", "mn": "Толь бичигт нэмэх"},
    "save": {"en": "Save corrected file…", "mn": "Засварласан файлыг хадгалах…"},
    "opt_upper": {"en": "Ignore words in UPPERCASE", "mn": "ТОМ үсгээр бичсэн үгийг алгасах"},
    "opt_digits": {"en": "Ignore words with numbers", "mn": "Тоо орсон үгийг алгасах"},
    "opt_latin": {"en": "Check English words", "mn": "Англи үгийг шалгах"},
    "status_open": {"en": "", "mn": ""},
    "status_fixed": {"en": "fixed → {new}", "mn": "зассан → {new}"},
    "status_ignored": {"en": "ignored", "mn": "алгассан"},
    "status_added": {"en": "added", "mn": "нэмсэн"},
    "start_hint": {"en": "Open a .docx, .xlsx or .pptx file, or check a document that is open in Office.",
                   "mn": ".docx, .xlsx, .pptx файл нээх эсвэл Office-д нээлттэй байгаа баримтыг шалгана уу."},
    "done_all": {"en": "All words have been reviewed.", "mn": "Бүх үгийг хянаж дууслаа."},
    "saved": {"en": "Saved: {path}", "mn": "Хадгаллаа: {path}"},
    "save_failed": {"en": "Could not save the file. If it is open in Office, close it there and try again.\n\n{err}",
                    "mn": "Файлыг хадгалж чадсангүй. Office-д нээлттэй бол хаагаад дахин оролдоно уу.\n\n{err}"},
    "open_failed": {"en": "Could not open the file.\n\n{err}", "mn": "Файлыг нээж чадсангүй.\n\n{err}"},
    "legacy": {"en": "Old .doc/.xls/.ppt files can't be read directly. Open the file in Office and use the "
                     "“Open Word / Excel / PowerPoint” button, or save it as .docx/.xlsx/.pptx first.",
               "mn": "Хуучин .doc/.xls/.ppt файлыг шууд уншиж чадахгүй. Файлыг Office-д нээгээд "
                     "“Нээлттэй Word / Excel / PowerPoint” товчийг дарна уу, эсвэл .docx/.xlsx/.pptx болгож хадгална уу."},
    "not_running": {"en": "{app} is not running, or no document is open in it.",
                    "mn": "{app} нээгдээгүй, эсвэл түүнд нээлттэй баримт алга."},
    "live_failed": {"en": "Could not talk to {app}.\n\n{err}", "mn": "{app}-тай холбогдож чадсангүй.\n\n{err}"},
    "live_saved_hint": {"en": "Corrections are made directly in {app}. Save the document there.",
                        "mn": "Засвар {app} дотор шууд хийгдэнэ. Баримтаа тэндээс хадгална уу."},
    "unsaved": {"en": "You have corrections that are not saved yet. Discard them?",
                "mn": "Хадгалаагүй засвар байна. Хадгалахгүйгээр үргэлжлүүлэх үү?"},
    "corrected_suffix": {"en": " (corrected)", "mn": " (зассан)"},
    "filetypes_office": {"en": "Office files", "mn": "Office файлууд"},
    "filetypes_all": {"en": "All files", "mn": "Бүх файл"},
    "edit_failed": {"en": "Could not change the word: {err}", "mn": "Үгийг сольж чадсангүй: {err}"},
    # locations
    "loc_paragraph": {"en": "Paragraph {0}", "mn": "{0}-р догол мөр"},
    "loc_table": {"en": "Table {0}, row {1}, column {2}", "mn": "{0}-р хүснэгт, {1}-р мөр, {2}-р багана"},
    "loc_textbox": {"en": "Text box", "mn": "Текст хайрцаг"},
    "loc_header": {"en": "Header {0}", "mn": "Толгой {0}"},
    "loc_footer": {"en": "Footer {0}", "mn": "Хөл {0}"},
    "loc_footnote": {"en": "Footnote {0}", "mn": "Зүүлт тайлбар {0}"},
    "loc_endnote": {"en": "Endnote {0}", "mn": "Төгсгөлийн тайлбар {0}"},
    "loc_comment": {"en": "Comment {0}", "mn": "Сэтгэгдэл {0}"},
    "loc_slide": {"en": "Slide {0}", "mn": "{0}-р слайд"},
    "loc_notes": {"en": "Slide {0} notes", "mn": "{0}-р слайдын тэмдэглэл"},
    "loc_cell": {"en": "{0}!{1}", "mn": "{0}!{1}"},
    "loc_cells": {"en": "{0}!{1} and {2} more", "mn": "{0}!{1} ба өөр {2}"},
    "loc_story": {"en": "{0}", "mn": "{0}"},
    "story_main": {"en": "Text", "mn": "Үндсэн текст"},
    "story_header": {"en": "Header", "mn": "Толгой"},
    "story_footer": {"en": "Footer", "mn": "Хөл"},
    "story_footnote": {"en": "Footnotes", "mn": "Зүүлт тайлбар"},
    "story_endnote": {"en": "Endnotes", "mn": "Төгсгөлийн тайлбар"},
    "story_comment": {"en": "Comments", "mn": "Сэтгэгдэл"},
    "story_textbox": {"en": "Text box", "mn": "Текст хайрцаг"},
    "story_other": {"en": "Other", "mn": "Бусад"},
}


def tr(key, lang="en", **kw):
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry["en"]
    return text.format(**kw) if kw else text


def where(location, lang="en"):
    """Human-readable location, e.g. ("table", 2, 3, 1) -> "Table 2, row 3, column 1"."""
    if not location:
        return ""
    kind, args = location[0], location[1:]
    if kind == "story":
        args = [tr("story_" + str(args[0]), lang)] if args else [""]
    entry = STRINGS.get("loc_" + kind)
    if entry is None:
        return " ".join(str(x) for x in location)
    return (entry.get(lang) or entry["en"]).format(*args)
