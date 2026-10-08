@echo off
rem Build dist\OfficeSpellcheck\ (the app, the Office add-in and the installer) on Windows.
rem Needs Python 3.10+ from python.org (with "tcl/tk" ticked), the .NET SDK,
rem and internet once.
cd /d "%~dp0"
python -m pip install -r requirements.txt -r requirements-dev.txt || exit /b 1
python fetch_dictionaries.py || exit /b 1
python -m PyInstaller --noconfirm --windowed --name OfficeSpellcheck ^
  --add-data "dictionaries;dictionaries" ^
  --copy-metadata spylls --collect-submodules spylls ^
  --hidden-import win32timezone ^
  OfficeSpellcheck.py || exit /b 1
dotnet build addin\OfficeSpellcheckAddin.csproj -c Release -nologo || exit /b 1
copy /y addin\bin\Release\net48\OfficeSpellcheckAddin.dll dist\OfficeSpellcheck\ >nul || exit /b 1
copy /y installer\install.cmd dist\OfficeSpellcheck\ >nul
copy /y installer\install.ps1 dist\OfficeSpellcheck\ >nul
copy /y installer\uninstall.ps1 dist\OfficeSpellcheck\ >nul
copy /y README.md dist\OfficeSpellcheck\ >nul
echo.
echo Done: dist\OfficeSpellcheck\  (run install.cmd from there)
