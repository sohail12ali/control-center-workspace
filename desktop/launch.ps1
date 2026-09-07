<#
.SYNOPSIS
  Launches the Delivery Console release build directly from a terminal, with
  a visible console attached by default.

.DESCRIPTION
  The shell is an unconditional GUI subsystem now (no console at all unless
  asked), so a terminal user who wants to see log output / errors inline
  needs `--console`; this script passes it through automatically. Use
  `-NoConsole` to launch silently instead, matching a Start-menu shortcut.

.PARAMETER NoConsole
  Launch without the `--console` flag.

.EXAMPLE
  .\launch.ps1
  .\launch.ps1 -NoConsole
#>
param(
    [switch]$NoConsole
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoRoot "desktop\src-tauri\target\release\delivery-console-desktop.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error ("Release exe not found at {0}. Build it first: " +
        "cargo build --release --manifest-path desktop/src-tauri/Cargo.toml" -f $ExePath)
    exit 1
}

$StartArgs = @{
    FilePath         = $ExePath
    WorkingDirectory = $RepoRoot
}
# Start-Process -ArgumentList rejects an empty array (PowerShell 5.1), so the
# key is only added when there is something to pass.
if (-not $NoConsole) {
    $StartArgs["ArgumentList"] = @("--console")
}

Start-Process @StartArgs
