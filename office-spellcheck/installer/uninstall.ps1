# uninstall.ps1 - removes Office Spellcheck for the current Windows user.
# The personal dictionary in %APPDATA%\OfficeSpellcheck is kept.

param(
    [string]$Target = $PSScriptRoot,
    [switch]$KeepFiles,
    [switch]$Quiet
)

$ErrorActionPreference = 'Continue'
$ProgId = 'OfficeSpellcheck.Addin'
$Clsid = '{AFFFDE13-884F-4B09-9A6A-67F1FE2D4BB3}'

function Remove-Key([string]$Path) {
    if (Test-Path -LiteralPath $Path) { Remove-Item -LiteralPath $Path -Recurse -Force }
}

$office = @(Get-Process -Name WINWORD, EXCEL, POWERPNT -ErrorAction SilentlyContinue)
if ($office.Count -gt 0 -and -not $Quiet) {
    Write-Host 'Word, Excel, PowerPoint-оо хаагаад Enter дарна уу.'
    Write-Host '  Please close Word, Excel and PowerPoint, then press Enter.' -ForegroundColor DarkGray
    [void](Read-Host)
}

Get-Process -Name OfficeSpellcheck -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($Target, [StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force -ErrorAction SilentlyContinue

foreach ($app in @('Word', 'Excel', 'PowerPoint')) {
    Remove-Key "HKCU:\Software\Microsoft\Office\$app\Addins\$ProgId"
    $list = "HKCU:\Software\Microsoft\Office\16.0\$app\Resiliency\DoNotDisableAddinList"
    if (Test-Path -LiteralPath $list) {
        Remove-ItemProperty -LiteralPath $list -Name $ProgId -ErrorAction SilentlyContinue
    }
}
Remove-Key "HKCU:\Software\Classes\$ProgId"
Remove-Key "HKCU:\Software\Classes\CLSID\$Clsid"
Remove-Key "HKCU:\Software\Classes\Wow6432Node\CLSID\$Clsid"
Remove-Key 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\OfficeSpellcheck'
$shortcut = Join-Path ([Environment]::GetFolderPath('Programs')) 'Office Spellcheck.lnk'
if (Test-Path -LiteralPath $shortcut) { Remove-Item -LiteralPath $shortcut -Force }

# Delete the program folder, but only if it really is ours.
if (-not $KeepFiles -and (Test-Path -LiteralPath (Join-Path $Target 'OfficeSpellcheck.exe')) `
        -and (Test-Path -LiteralPath (Join-Path $Target 'OfficeSpellcheckAddin.dll'))) {
    # This script runs from that folder, so delete it a moment after exiting.
    $cmd = 'ping 127.0.0.1 -n 3 >nul & rmdir /s /q "' + $Target + '"'
    Start-Process -FilePath cmd.exe -ArgumentList '/c', $cmd -WindowStyle Hidden
}

Write-Host 'Устгалаа. Хувийн толь бичиг %APPDATA%\OfficeSpellcheck-д хадгалагдсан хэвээр.'
Write-Host '  Uninstalled. Your personal dictionary in %APPDATA%\OfficeSpellcheck was kept.' -ForegroundColor DarkGray
