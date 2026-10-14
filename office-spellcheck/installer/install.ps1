# install.ps1 - installs Office Spellcheck for the current Windows user.
# No administrator rights are needed: everything goes into the user's own
# folders and the HKEY_CURRENT_USER part of the registry.
#
#   - copies the app to %LOCALAPPDATA%\Programs\OfficeSpellcheck
#   - registers the "Зөв бичиг" ribbon button for Word, Excel and PowerPoint
#   - adds a Start menu shortcut and an entry in Settings > Apps (for uninstalling)

param(
    [string]$Target = (Join-Path $env:LOCALAPPDATA 'Programs\OfficeSpellcheck'),
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$Source = $PSScriptRoot
$Version = '1.1.0'
$ProgId = 'OfficeSpellcheck.Addin'
$Clsid = '{AFFFDE13-884F-4B09-9A6A-67F1FE2D4BB3}'
$ClassName = 'OfficeSpellcheck.Connect'
$AssemblyName = 'OfficeSpellcheckAddin, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null'
$OfficeApps = @('Word', 'Excel', 'PowerPoint')

function Say([string]$mn, [string]$en) {
    Write-Host $mn
    Write-Host ('  ' + $en) -ForegroundColor DarkGray
}

function Ensure-Key([string]$Path) {
    if (Test-Path -LiteralPath $Path) { return }
    Ensure-Key (Split-Path -Path $Path -Parent)
    New-Item -Path $Path -Force | Out-Null
}

function Set-RegValue([string]$Path, [string]$Name, $Value, [string]$Type = 'String') {
    Ensure-Key $Path
    if ($Name -eq '') {
        Set-Item -LiteralPath $Path -Value $Value
    } else {
        New-ItemProperty -LiteralPath $Path -Name $Name -Value $Value -PropertyType $Type -Force | Out-Null
    }
}

# --- 1. Office keeps the add-in file open while it runs -------------------
$office = @(Get-Process -Name WINWORD, EXCEL, POWERPNT -ErrorAction SilentlyContinue)
if ($office.Count -gt 0 -and -not $Quiet) {
    Say 'Word, Excel, PowerPoint-оо хаагаад Enter дарна уу.' 'Please close Word, Excel and PowerPoint, then press Enter.'
    [void](Read-Host)
}

# --- 2. Stop an open checker window from an older install -----------------
Get-Process -Name OfficeSpellcheck -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and $_.Path.StartsWith($Target, [StringComparison]::OrdinalIgnoreCase) } |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

# --- 3. Copy the files -----------------------------------------------------
$sourceFull = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\')
New-Item -ItemType Directory -Force -Path $Target | Out-Null
$targetFull = (Resolve-Path -LiteralPath $Target).Path.TrimEnd('\')
if ($sourceFull -ne $targetFull) {
    # Drop the bundled Python runtime of an older version before copying.
    $old = Join-Path $targetFull '_internal'
    if (Test-Path -LiteralPath $old) { Remove-Item -LiteralPath $old -Recurse -Force }
    Get-ChildItem -LiteralPath $sourceFull | Copy-Item -Destination $targetFull -Recurse -Force
}
# Files from a downloaded zip are marked "from the internet"; .NET refuses to
# load an add-in marked that way, so remove the mark.
Get-ChildItem -LiteralPath $targetFull -Recurse -File | Unblock-File

$Dll = Join-Path $targetFull 'OfficeSpellcheckAddin.dll'
$Exe = Join-Path $targetFull 'OfficeSpellcheck.exe'
foreach ($f in @($Dll, $Exe)) {
    if (-not (Test-Path -LiteralPath $f)) { throw "Missing file: $f" }
}
# Written the way regasm writes it: the plain path, not URL-escaped, so a
# user folder with Mongolian letters (C:\Users\Төгстөгөлдөр) stays readable.
$CodeBase = 'file:///' + ($Dll -replace '\\', '/')

# --- 4. Register the add-in as a COM class (64-bit and 32-bit Office) ----
Set-RegValue "HKCU:\Software\Classes\$ProgId" '' $ClassName
Set-RegValue "HKCU:\Software\Classes\$ProgId\CLSID" '' $Clsid
foreach ($clsRoot in @('HKCU:\Software\Classes\CLSID', 'HKCU:\Software\Classes\Wow6432Node\CLSID')) {
    $key = "$clsRoot\$Clsid"
    Set-RegValue $key '' $ClassName
    Set-RegValue "$key\ProgId" '' $ProgId
    Set-RegValue "$key\Implemented Categories\{62C8FE65-4EBB-45e7-B440-6E39B2CDBF29}" '' ''
    foreach ($ip in @("$key\InprocServer32", "$key\InprocServer32\1.0.0.0")) {
        if ($ip.EndsWith('InprocServer32')) {
            Set-RegValue $ip '' 'mscoree.dll'
            Set-RegValue $ip 'ThreadingModel' 'Both'
        }
        Set-RegValue $ip 'Class' $ClassName
        Set-RegValue $ip 'Assembly' $AssemblyName
        Set-RegValue $ip 'RuntimeVersion' 'v4.0.30319'
        Set-RegValue $ip 'CodeBase' $CodeBase
    }
}

# --- 5. Tell Word, Excel and PowerPoint to load it at startup ------------
foreach ($app in $OfficeApps) {
    $key = "HKCU:\Software\Microsoft\Office\$app\Addins\$ProgId"
    Set-RegValue $key 'FriendlyName' 'Зөв бичиг (Office Spellcheck)'
    Set-RegValue $key 'Description' 'Монгол, англи үгийн алдааг офлайнаар шалгах / Offline Mongolian and English spellchecker'
    Set-RegValue $key 'LoadBehavior' 3 'DWord'
    # Ask Office not to switch the add-in off if it once starts slowly.
    Set-RegValue "HKCU:\Software\Microsoft\Office\16.0\$app\Resiliency\DoNotDisableAddinList" $ProgId 1 'DWord'
}

# --- 6. Start menu shortcut and the uninstall entry -----------------------
# WScript.Shell cannot store paths with letters such as "ө" and "ү", so the
# shortcut is written through the Unicode shell interface (IShellLinkW).
$shellLinkCode = @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

namespace OfficeSpellcheckInstaller
{
    [ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
    interface IShellLinkW
    {
        void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder file, int max, IntPtr findData, int flags);
        void GetIDList(out IntPtr idl);
        void SetIDList(IntPtr idl);
        void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder name, int max);
        void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string name);
        void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder dir, int max);
        void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string dir);
        void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder args, int max);
        void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string args);
        void GetHotkey(out short hotkey);
        void SetHotkey(short hotkey);
        void GetShowCmd(out int showCmd);
        void SetShowCmd(int showCmd);
        void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder path, int max, out int index);
        void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string path, int index);
        void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string path, int reserved);
        void Resolve(IntPtr hwnd, int flags);
        void SetPath([MarshalAs(UnmanagedType.LPWStr)] string file);
    }

    [ComImport, Guid("00021401-0000-0000-C000-000000000046")]
    class ShellLink { }

    public static class Shortcut
    {
        public static void Create(string lnk, string target, string workDir, string description)
        {
            var link = (IShellLinkW)new ShellLink();
            link.SetPath(target);
            link.SetWorkingDirectory(workDir);
            link.SetDescription(description);
            link.SetIconLocation(target, 0);
            ((IPersistFile)link).Save(lnk, true);
        }

        public static string Target(string lnk)
        {
            var link = (IShellLinkW)new ShellLink();
            ((IPersistFile)link).Load(lnk, 0);
            var sb = new StringBuilder(1024);
            link.GetPath(sb, sb.Capacity, IntPtr.Zero, 0);
            return sb.ToString();
        }
    }
}
'@
$programs = [Environment]::GetFolderPath('Programs')
$shortcut = Join-Path $programs 'Office Spellcheck.lnk'
try {
    if (-not ('OfficeSpellcheckInstaller.Shortcut' -as [type])) { Add-Type -TypeDefinition $shellLinkCode }
    [OfficeSpellcheckInstaller.Shortcut]::Create($shortcut, $Exe, $targetFull, 'Зөв бичгийн шалгагч / Office Spellcheck')
} catch {
    # A missing shortcut must not stop the install: the ribbon button works without it.
    Say ('Start цэсний холбоос үүсгэж чадсангүй: ' + $_.Exception.Message) `
        ('Could not create the Start menu shortcut (the ribbon button still works): ' + $_.Exception.Message)
}

$uninstall = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\OfficeSpellcheck'
$sizeKb = [int]((Get-ChildItem -LiteralPath $targetFull -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1KB)
Set-RegValue $uninstall 'DisplayName' 'Зөв бичиг - Office Spellcheck'
Set-RegValue $uninstall 'DisplayVersion' $Version
Set-RegValue $uninstall 'Publisher' 'Office Spellcheck'
Set-RegValue $uninstall 'InstallLocation' $targetFull
Set-RegValue $uninstall 'DisplayIcon' "$Exe,0"
Set-RegValue $uninstall 'UninstallString' ('powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $targetFull 'uninstall.ps1') + '"')
Set-RegValue $uninstall 'NoModify' 1 'DWord'
Set-RegValue $uninstall 'NoRepair' 1 'DWord'
Set-RegValue $uninstall 'EstimatedSize' $sizeKb 'DWord'

Write-Host ''
Say 'Суулгаж дууслаа. Word, Excel эсвэл PowerPoint-оо нээхэд Home болон Review табд "Зөв бичиг" товч гарна.' `
    'Installed. Open Word, Excel or PowerPoint: the "Зөв бичиг" button is on the Home and Review tabs.'
Say ('Байршил: ' + $targetFull) ('Location: ' + $targetFull)
