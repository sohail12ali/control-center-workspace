# Fetch the speech-to-text engine and model into desktop/stt/ (gitignored).
#
# Nothing in this repo downloads anything on its own. Run this once, and the
# shell picks the binary up on its next listen; until then the tray reports
# listening as unavailable and says why, rather than failing when you speak.
#
#   pwsh -File desktop/get-whisper.ps1              # base.en, ~150 MB
#   pwsh -File desktop/get-whisper.ps1 -Model small.en
#   pwsh -File desktop/get-whisper.ps1 -WhatIf      # show sizes, download nothing
#
# Why prebuilt rather than building whisper.cpp here: building it needs CMake
# and LLVM, neither of which this machine has, and requiring a C toolchain to
# talk to your own computer is a poor trade. The official release ships a
# `whisper-server` binary that speaks HTTP, which is all the shell needs.

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # ggml model. base.en is the sensible default: ~150 MB, good enough for
    # short spoken commands, fast on a CPU. small.en is ~470 MB and better on
    # accents and background noise.
    [ValidateSet('tiny.en', 'base.en', 'small.en', 'medium.en')]
    [string]$Model = 'base.en',

    # Pin the whisper.cpp release by its GIT TAG, which is not the same string
    # as the release title: the release shown as "v1.9.3" is tagged `b4938`,
    # and the asset URLs use the tag. Using the title 404s — verified.
    # A moving 'latest' would mean two machines silently running different
    # engines, so this stays pinned.
    [string]$Release = 'b4938',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $here 'stt'
$binZip = Join-Path $dest 'whisper-bin-x64.zip'
$modelFile = Join-Path $dest "ggml-$Model.bin"

$binUrl = "https://github.com/ggml-org/whisper.cpp/releases/download/$Release/whisper-bin-x64.zip"
$modelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.bin"

$sizes = @{
    'tiny.en'   = '~75 MB'
    'base.en'   = '~150 MB'
    'small.en'  = '~470 MB'
    'medium.en' = '~1.5 GB'
}

Write-Host "whisper.cpp $Release (release v1.9.3) + ggml-$Model ($($sizes[$Model]))"
Write-Host "  engine: $binUrl"
Write-Host "  model : $modelUrl"
Write-Host "  into  : $dest"

if (-not $PSCmdlet.ShouldProcess($dest, 'download the speech engine and model')) {
    Write-Host 'Nothing downloaded (-WhatIf).'
    return
}

New-Item -ItemType Directory -Force -Path $dest | Out-Null

# --- engine ---------------------------------------------------------------
$serverExe = Join-Path $dest 'whisper-server.exe'
if ((Test-Path $serverExe) -and -not $Force) {
    Write-Host "engine: already present ($serverExe)"
}
else {
    Write-Host 'engine: downloading...'
    Invoke-WebRequest -Uri $binUrl -OutFile $binZip -UseBasicParsing
    Write-Host 'engine: extracting...'
    Expand-Archive -Path $binZip -DestinationPath $dest -Force
    # The archive nests its binaries; lift them to the top so the shell has
    # one place to look.
    Get-ChildItem -Path $dest -Recurse -Include 'whisper-server.exe', 'whisper-cli.exe', '*.dll' |
        ForEach-Object {
            $target = Join-Path $dest $_.Name
            if ($_.FullName -ne $target) { Move-Item -Force $_.FullName $target }
        }
    Remove-Item $binZip -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path $serverExe)) {
        Write-Warning "whisper-server.exe not found after extracting. Contents:"
        Get-ChildItem -Path $dest | Select-Object -ExpandProperty Name
    }
}

# --- model ----------------------------------------------------------------
if ((Test-Path $modelFile) -and -not $Force) {
    Write-Host "model: already present ($modelFile)"
}
else {
    Write-Host "model: downloading $($sizes[$Model])..."
    Invoke-WebRequest -Uri $modelUrl -OutFile $modelFile -UseBasicParsing
}

Write-Host ''
Write-Host 'Done. Present in desktop/stt/:'
Get-ChildItem -Path $dest | ForEach-Object {
    '  {0,-28} {1,10:N0} bytes' -f $_.Name, $_.Length
}
Write-Host ''
Write-Host 'The shell finds these on its next launch. Check with:'
Write-Host '  python console/kanban.py verb run desktop-listen-state'
