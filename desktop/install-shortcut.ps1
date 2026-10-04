<#
.SYNOPSIS
  Installs a Start-menu shortcut for the Delivery Console desktop shell's
  release build, with optional Desktop/Startup copies.

.DESCRIPTION
  TargetPath is the release exe; WorkingDirectory is the repo root. Re-running
  this script overwrites any existing shortcut cleanly (idempotent) rather
  than erroring or creating a duplicate.

.PARAMETER Desktop
  Also place a shortcut on the current user's Desktop.

.PARAMETER Startup
  Also place a shortcut in the current user's Startup folder (launches at
  logon).

.EXAMPLE
  .\install-shortcut.ps1
  .\install-shortcut.ps1 -Desktop -Startup
#>
param(
    [switch]$Desktop,
    [switch]$Startup
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoRoot "desktop\src-tauri\target\release\delivery-console-desktop.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error ("Release exe not found at {0}. Build it first: " +
        "cargo build --release --manifest-path desktop/src-tauri/Cargo.toml" -f $ExePath)
    exit 1
}

function New-ShortcutAt {
    param([Parameter(Mandatory)][string]$LinkPath)
    $dir = Split-Path -Parent $LinkPath
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($LinkPath)
    $shortcut.TargetPath = $ExePath
    $shortcut.WorkingDirectory = $RepoRoot
    $shortcut.IconLocation = $ExePath
    $shortcut.Description = "Delivery Console"
    $shortcut.Save()
    Write-Host "Shortcut written: $LinkPath"
}

$StartMenuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-ShortcutAt (Join-Path $StartMenuDir "Delivery Console.lnk")

if ($Desktop) {
    $DesktopDir = [Environment]::GetFolderPath("Desktop")
    New-ShortcutAt (Join-Path $DesktopDir "Delivery Console.lnk")
}

if ($Startup) {
    $StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
    New-ShortcutAt (Join-Path $StartupDir "Delivery Console.lnk")
}
