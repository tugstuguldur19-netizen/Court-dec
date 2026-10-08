# Office Spellcheck · Зөв бичгийн шалгагч

An offline spellchecker for **Word, Excel and PowerPoint**, for **Mongolian (Cyrillic)
and English**. It works without internet, without any online API and without AI:
it compares every word with Hunspell dictionaries stored on your computer, the same
dictionaries LibreOffice uses.

**Word, Excel, PowerPoint**-д зориулсан **монгол (кирилл) болон англи** хэлний зөв
бичгийн шалгагч. Интернэт, API, хиймэл оюун ухаан ашиглахгүй. Үг бүрийг таны
компьютерт хадгалагдсан Hunspell толь бичигтэй тулгаж шалгана.

---

## Монгол заавар

### Суулгах
1. GitHub-ийн **Actions → Office Spellcheck** хэсгээс хамгийн сүүлийн амжилттай
   ажилласан (ногоон) ажлыг нээгээд **OfficeSpellcheck-windows** файлыг татаж авна.
2. ZIP файлыг задлаад, доторх **install.cmd** дээр давхар дарна. Админ эрх
   шаардлагагүй. Word, Excel, PowerPoint нээлттэй бол хаахыг асууна.
3. Word, Excel эсвэл PowerPoint-оо нээхэд **Home** болон **Review** табд
   **"Зөв бичиг → Алдаа шалгах"** товч гарна. Start цэсэнд **Office Spellcheck** нэмэгдэнэ.

Устгах: **Settings → Apps → "Зөв бичиг - Office Spellcheck" → Uninstall**.

Windows "Unknown publisher" гэж анхааруулбал **More info → Run anyway** дарна (програм
тоон гарын үсэггүй учраас).

### Ашиглах
- **"Алдаа шалгах" товч** (Word, Excel, PowerPoint-ын Home/Review таб) — нээлттэй
  баримтыг шалгагчид нээнэ. Анх дарахад толь бичиг 10 орчим секунд ачаална; цонхыг
  нээлттэй орхивол дараагийн дарах бүрт шууд нээгдэнэ.
- **Файл нээх…** — `.docx`, `.xlsx`, `.pptx` файлыг шалгана. Засварласны дараа
  **Засварласан файлыг хадгалах…** дарж хадгална. Анхны файл өөрчлөгдөхгүй
  (өөр нэрээр хадгалагдана).
- **Нээлттэй Word / Excel / PowerPoint** — тухайн програмд одоо нээлттэй байгаа
  баримтыг шууд шалгана. Алдаатай үгийг сонгоход Word дотор тэр үг тодорч
  харагдана. Засвар баримтад шууд орно, баримтаа Word-оос хадгална.
  (Хуучин `.doc`, `.xls`, `.ppt` файлыг ч ингэж шалгаж болно.)
- Алдаа бүр дээр: **Солих**, **Бүгдийг солих**, **Алгасах**, **Бүгдийг алгасах**,
  **Толь бичигт нэмэх**. Санал болгох үгс нэг нэгээрээ гарч ирнэ, эхнийх нь ихэвчлэн зөв.
- Тохиргоо: ТОМ үсгээр бичсэн үг (ХХК, ШШГЕГ), тоо орсон үг (2024-ний) болон англи
  үгийг шалгах эсэх.
- Товчлол: `Enter` = Солих, `Ctrl+O` = Файл нээх. Санал болгосон үг дээр давхар дарвал солигдоно.

### Хувийн толь бичиг
"Толь бичигт нэмэх" дарсан үгс `%APPDATA%\OfficeSpellcheck\personal.txt` файлд
хадгалагдана. Мөр бүрд нэг үг. Хуулийн нэр томьёо, шүүхийн нэр, хүний нэрийн
жагсаалтыг `.txt` файл болгоод `%APPDATA%\OfficeSpellcheck\dictionaries\` хавтсанд
хийвэл бүгдийг зөв гэж үзнэ. Office-ийн `CUSTOM.DIC` файлыг ч шууд хуулж болно.

### Зөвлөмж: Word-ын улаан зураасыг арилгах
Word монгол текстийг англиар шалгаж бүх үгийн доор улаан зураас татдаг. Текстээ
сонгоод **Review → Language → Set Proofing Language → Mongolian** эсвэл
**Do not check spelling or grammar** гэж тохируулна.

### Товч гарахгүй бол
- Word: **File → Options → Add-ins → Manage: COM Add-ins → Go…** хэсэгт
  **"Зөв бичиг (Office Spellcheck)"** сонгогдсон эсэхийг шалгана.
- Тэнд байхгүй эсвэл "Disabled Items"-д орсон бол **install.cmd**-г дахин ажиллуулаад
  Office-оо дахин нээнэ.
- Word-оо **"Run as administrator"**-аар бүү нээ: Windows ийм үед хэрэглэгчийн
  нэмэлтүүдийг (add-in) ачаалдаггүй.

---

## English guide

### Install
1. On GitHub open **Actions → Office Spellcheck**, pick the latest green run and
   download **OfficeSpellcheck-windows**.
2. Unzip it and double-click **install.cmd**. No administrator rights are needed; it
   asks you to close Word, Excel and PowerPoint if they are open. It copies the app to
   `%LOCALAPPDATA%\Programs\OfficeSpellcheck` and adds a Start menu shortcut.
3. Open Word, Excel or PowerPoint: the **"Зөв бичиг → Алдаа шалгах"** button is on the
   **Home** and **Review** tabs.

To remove it: **Settings → Apps → "Зөв бичиг - Office Spellcheck" → Uninstall**.

The app is not code-signed, so Windows SmartScreen may say "Unknown publisher":
choose **More info → Run anyway**.

### Use
- **The ribbon button** (Home and Review tabs in Word, Excel and PowerPoint) opens the
  checker on the document you are working on. The first click loads the dictionaries
  (about 10 seconds); leave the checker window open and later clicks open instantly.
- **Open file…** checks a `.docx`, `.xlsx` or `.pptx` file (also the macro and
  template variants). Fix the words, then **Save corrected file…**; it suggests a
  new name, so the original stays as it was.
- **Open Word document / Open Excel workbook / Open PowerPoint** checks the document
  that is open in that program right now. Selecting an error highlights it in
  Office, and corrections go straight into the document (save it in Office as usual).
  This also works for old `.doc`/`.xls`/`.ppt` files. Windows only.
- For each word: **Change**, **Change all**, **Ignore**, **Ignore all**,
  **Add to dictionary**. Suggestions appear one by one; the first is usually right.
- Options: skip words in UPPERCASE (abbreviations such as ХХК), skip words with
  digits (2024-ний), check English words.
- Keys: `Enter` = Change, `Ctrl+O` = Open file. Double-click a suggestion to use it.
- You can also drop a file onto `OfficeSpellcheck.exe`, or start it with
  `OfficeSpellcheck.exe --live word` (or `excel`, `powerpoint`). If the checker is
  already open, that window takes the request.

**If the button does not appear:** in Word open **File → Options → Add-ins**, choose
**Manage: COM Add-ins → Go…** and tick **"Зөв бичиг (Office Spellcheck)"**. If it is
missing or listed under **Disabled Items**, run **install.cmd** again and restart Office.
Don't start Office with **Run as administrator**: Windows does not load per-user add-ins
into programs running as administrator.

What is checked: Word body text, tables, text boxes, headers, footers, footnotes,
endnotes and comments (not deleted tracked changes or field codes); Excel text
cells on every sheet (not formulas); PowerPoint slides, tables, grouped shapes and
speaker notes. Charts and SmartArt are not checked.

### Personal dictionary and word lists
Words you add are stored in `%APPDATA%\OfficeSpellcheck\personal.txt`, one per line.
Any `.txt` word list placed in `%APPDATA%\OfficeSpellcheck\dictionaries\` is accepted
too: legal terms, court names, people's names. Office's own `CUSTOM.DIC` works as is.
More Hunspell dictionaries (`xx_YY.aff` + `.dic`, for example Russian) can go in the
same folder.

### Tip: stop Word underlining every Mongolian word
Select the text, then **Review → Language → Set Proofing Language → Mongolian**,
or tick **Do not check spelling or grammar**.

### Command line
```
OfficeSpellcheck.exe check report.docx --suggest 3 --json --output result.json
python -m offspell check *.docx *.xlsx --suggest 3
```
The exit code is 1 when possible errors were found, 0 when none were.

---

## Run from source / build the .exe

Needs Python 3.10 or newer (on Windows from python.org, with Tcl/Tk), and internet
once to download the packages and dictionaries.

```
cd office-spellcheck
python -m pip install -r requirements.txt
python fetch_dictionaries.py        # one-time download into ./dictionaries
python OfficeSpellcheck.py          # the window
```

Tests: `python -m pip install -r requirements-dev.txt && python -m pytest`.
On Windows, `build_windows.bat` builds `dist\OfficeSpellcheck\` with the app, the add-in
and `install.cmd` (it also needs the .NET SDK for the add-in).
The GitHub workflow `.github/workflows/office-spellcheck.yml` runs the tests on Linux
and Windows, builds the .exe, checks it on a sample file, and uploads the zip.

### How it works
- `offspell/engine.py`: loads the Hunspell dictionaries with
  [spylls](https://github.com/zverok/spylls) (pure Python). Cyrillic words go to the
  Mongolian dictionary, Latin words to English. A word with a Latin look-alike letter
  inside ("Монгoл" typed with a Latin "o") is still treated as Mongolian, and the
  dictionary suggests the fix. Hyphenated names with case endings ("Д.Дорж-д",
  "ХХК-ийн") are accepted.
- `offspell/ooxml.py`: reads `.docx/.xlsx/.pptx` as XML. A word split over several
  formatting runs is fixed in place, keeping the formatting where the word starts;
  every other part of the file is copied byte for byte.
- `offspell/live.py`: talks to running Word/Excel/PowerPoint over COM (pywin32).
- `offspell/gui.py`: the Tkinter window. Spell-checking runs on a background thread.
- `offspell/instance.py`: keeps one window; a second start hands its request over
  through a token-protected socket on 127.0.0.1.
- `addin/`: the ribbon button, a COM add-in for .NET Framework 4.8 (built into Windows
  10 and 11), registered per user by `installer/install.ps1`. `addin/test/` holds a C++
  program that loads it through COM the way Office does; CI runs it in 64-bit and 32-bit.

### Licences
- Mongolian dictionary `mn_MN`: © Batmunkh Dorjgotov, LaTeX Project Public License 1.3,
  <https://bataak.github.io/dict-mn/>. Shipped unmodified with its README.
- English dictionary `en_US`: SCOWL, © Kevin Atkinson and others (see `README_en_US.txt`).
- spylls: Mozilla Public License 2.0. lxml: BSD. pywin32: PSF.

### Known limits
- Live mode and the ribbon button need Windows and desktop Office. They were tested
  against simulated Office objects and a COM client that loads the add-in like Office
  does, not yet inside a real Office install. If a button says Office is not running
  while it is, check that Office and this app run as the same user (both not "as
  administrator").
- Suggestions for Mongolian take 1–4 seconds in total; the best one usually shows
  in under a second.
- Grammar is not checked, only spelling.
