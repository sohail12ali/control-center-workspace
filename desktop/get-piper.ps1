# Fetch the neural text-to-speech engine and a voice into desktop/tts/
# (gitignored).
#
# Nothing in this repo downloads anything on its own. Run this once, and the
# shell speaks with it on the next reply; until then it falls back to the
# operating system's own synthesiser and says which one it used.
#
#   pwsh -File desktop/get-piper.ps1                  # amy, ~65 MB total
#   pwsh -File desktop/get-piper.ps1 -Voice en_GB-alba-medium
#   pwsh -File desktop/get-piper.ps1 -WhatIf          # show sizes, download nothing
#
# ## Why this exists
#
# Windows' System.Speech reaches only the old "Desktop" voices — on a typical
# machine that is Microsoft David and Zira, which is what "it sounds like a
# robot" actually means. Piper is a small neural synthesiser that runs offline
# on a CPU and sounds close to a person. Same trade as whisper.cpp for
# listening: a prebuilt binary and a model file, fetched deliberately, rather
# than a cloud service that would send every reply out of the building.

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # A Piper voice. `medium` quality is the sweet spot: ~60 MB, natural, and
    # real-time on a CPU. The `low` variants are half the size and audibly
    # worse; `high` is several times slower for little gain at this length of
    # utterance.
    [ValidateSet('en_US-amy-medium', 'en_US-ryan-medium', 'en_US-lessac-medium',
                 'en_GB-alba-medium', 'en_GB-northern_english_male-medium')]
    [string]$Voice = 'en_US-amy-medium',

    # Pinned, so two machines do not silently run different engines.
    [string]$Release = '2023.11.14-2',

    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $here 'tts'
$binZip = Join-Path $dest 'piper_windows_amd64.zip'
$modelFile = Join-Path $dest "$Voice.onnx"
$configFile = Join-Path $dest "$Voice.onnx.json"

$binUrl = "https://github.com/rhasspy/piper/releases/download/$Release/piper_windows_amd64.zip"

# Voice files live under a lang/region/name/quality path on Hugging Face.
$parts = $Voice -split '-'
$lang = $parts[0]                        # en_US
$name = $parts[1]                        # amy
$quality = $parts[2]                     # medium
$langShort = ($lang -split '_')[0]        # en
$voiceBase = "https://huggingface.co/rhasspy/piper-voices/resolve/main/$langShort/$lang/$name/$quality/$Voice.onnx"

Write-Host "piper $Release + voice $Voice  (~65 MB total)"
Write-Host "  into $dest"

if (-not (Test-Path $dest)) {
    if ($PSCmdlet.ShouldProcess($dest, 'create')) {
        New-Item -ItemType Directory -Path $dest -Force | Out-Null
    }
}

function Get-File($url, $path, $what) {
    if ((Test-Path $path) -and -not $Force) {
        Write-Host "  $what already here - skipping (use -Force to refetch)"
        return
    }
    if (-not $PSCmdlet.ShouldProcess($url, "download $what")) { return }
    Write-Host "  fetching $what ..."
    # Progress off: on a large file the built-in bar costs more time than the
    # download itself in some PowerShell versions.
    $prev = $ProgressPreference
    $ProgressPreference = 'SilentlyContinue'
    try {
        Invoke-WebRequest -Uri $url -OutFile $path -UseBasicParsing
    } finally {
        $ProgressPreference = $prev
    }
}

$piperExe = Join-Path $dest 'piper.exe'
if ((Test-Path $piperExe) -and -not $Force) {
    Write-Host "  piper.exe already here - skipping (use -Force to refetch)"
} else {
    Get-File $binUrl $binZip 'piper (windows amd64)'
    if (Test-Path $binZip) {
        if ($PSCmdlet.ShouldProcess($binZip, 'expand')) {
            Expand-Archive -Path $binZip -DestinationPath $dest -Force
            # The archive contains a `piper/` folder; flatten it so the shell
            # finds piper.exe beside its voices.
            $inner = Join-Path $dest 'piper'
            if (Test-Path $inner) {
                Get-ChildItem $inner | Move-Item -Destination $dest -Force
                Remove-Item $inner -Recurse -Force
            }
            Remove-Item $binZip -Force
        }
    }
}

Get-File $voiceBase $modelFile "voice $Voice"
Get-File "$voiceBase.json" $configFile 'voice config'

if (Test-Path $piperExe) {
    Write-Host ""
    Write-Host "Done. The shell picks this up on its next spoken reply."
    Write-Host "Pick the voice in Settings > Assistant, or set speak_voice."
} elseif (-not $WhatIfPreference) {
    Write-Warning "piper.exe is not in $dest - the shell will keep using the OS voice."
}
