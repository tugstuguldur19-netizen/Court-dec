@echo off
rem Installs Office Spellcheck and the "Zuv bichig" ribbon button for this Windows user.
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
