@echo off
rem Build dist\OfficeSpellcheck\OfficeSpellcheck.exe on Windows.
rem Needs Python 3.10+ from python.org (with "tcl/tk" ticked) and internet once.
cd /d "%~dp0"
python -m pip install -r requirements.txt -r requirements-dev.txt || exit /b 1
python fetch_dictionaries.py || exit /b 1
python -m PyInstaller --noconfirm --windowed --name OfficeSpellcheck ^
  --add-data "dictionaries;dictionaries" ^
  --copy-metadata spylls --collect-submodules spylls ^
  --hidden-import win32timezone ^
  OfficeSpellcheck.py || exit /b 1
echo.
echo Done: dist\OfficeSpellcheck\OfficeSpellcheck.exe
