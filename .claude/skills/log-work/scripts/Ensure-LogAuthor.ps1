#Requires -Version 5.1
<#
.SYNOPSIS
  Resolves log author display name and slug; auto-creates author.local from Git when missing.

.DESCRIPTION
  Returns JSON: { "Name": "...", "Slug": "...", "Path": "..." }
  Creates knowledge-center/logs/author.local only when it does not exist.

.PARAMETER AuthorOverride
  Optional display name override (--author=).

.PARAMETER SlugOverride
  Optional slug override (--slug=).

.PARAMETER RepoRoot
  Repository root (default: auto-detect from script location).

.EXAMPLE
  .\.claude\skills\log-work\scripts\Ensure-LogAuthor.ps1
#>
[CmdletBinding()]
param(
    [string]$AuthorOverride,
    [string]$SlugOverride,
    [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$getRoot = Join-Path $PSScriptRoot '..\..\_shared\scripts\Get-RepoRoot.ps1'
if (-not $RepoRoot) {
    $RepoRoot = & $getRoot -StartDir $PSScriptRoot
}

function ConvertTo-AuthorSlug {
    param([string]$Name)
    if ([string]::IsNullOrWhiteSpace($Name)) { return 'unknown' }
    $s = $Name.ToLowerInvariant().Trim()
    $s = $s -replace '[_\s]+', '-'
    $s = $s -replace '[^a-z0-9-]', ''
    $s = $s -replace '-{2,}', '-'
    $s = $s.Trim('-')
    if ([string]::IsNullOrWhiteSpace($s)) { return 'unknown' }
    return $s
}

function Get-GitConfigValue {
    param([string]$Key, [string]$Cwd)
    try {
        $val = git -C $Cwd config --get $Key 2>$null
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace($val)) {
            return $val.Trim()
        }
    } catch { }
    return $null
}

$authorFile = Join-Path $RepoRoot 'knowledge-center/logs/author.local'
$logsDir = Split-Path $authorFile -Parent

$name = $null
$slug = $null

if (-not [string]::IsNullOrWhiteSpace($AuthorOverride)) {
    $name = $AuthorOverride.Trim()
    $slug = if (-not [string]::IsNullOrWhiteSpace($SlugOverride)) {
        $SlugOverride.Trim().ToLowerInvariant()
    } else {
        ConvertTo-AuthorSlug -Name $name
    }
}
elseif (Test-Path $authorFile) {
    $lines = @(Get-Content $authorFile -Encoding UTF8 | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    if ($lines.Count -ge 1) { $name = $lines[0] }
    if ($lines.Count -ge 2) { $slug = $lines[1] }
    if (-not $slug -and $name) {
        $slug = ConvertTo-AuthorSlug -Name $name
        $content = "$name`n$slug"
        Set-Content -Path $authorFile -Value $content -Encoding UTF8 -NoNewline
        Add-Content -Path $authorFile -Value '' -Encoding UTF8
    }
}
else {
    $name = Get-GitConfigValue -Key 'user.name' -Cwd $RepoRoot
    if (-not $name) {
        $name = $env:USERNAME
        if (-not $name) { $name = $env:USER }
    }
    if (-not $name) {
        $email = Get-GitConfigValue -Key 'user.email' -Cwd $RepoRoot
        if ($email -and $email -match '^([^@]+)@') {
            $name = $email
            $slug = $Matches[1].ToLowerInvariant()
        }
    }
    if (-not $slug -and $name) {
        $slug = ConvertTo-AuthorSlug -Name $name
    }

    if ($name -and $slug) {
        if (-not (Test-Path $logsDir)) {
            New-Item -ItemType Directory -Force -Path $logsDir | Out-Null
        }
        $content = "$name`n$slug"
        Set-Content -Path $authorFile -Value $content -Encoding UTF8 -NoNewline
        Add-Content -Path $authorFile -Value '' -Encoding UTF8
    }
}

if (-not [string]::IsNullOrWhiteSpace($SlugOverride) -and -not [string]::IsNullOrWhiteSpace($AuthorOverride)) {
    $slug = $SlugOverride.Trim().ToLowerInvariant()
}

if (-not $name) { $name = 'Unknown' }
if (-not $slug) { $slug = ConvertTo-AuthorSlug -Name $name }

[PSCustomObject]@{
    Name = $name
    Slug = $slug
    Path = $authorFile
} | ConvertTo-Json -Compress
