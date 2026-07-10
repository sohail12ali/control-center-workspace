#Requires -Version 5.1
<#
.SYNOPSIS
  Creates knowledge-center/logs/YYYY-MM/YYYY-MM-DD.{slug}.md from template if missing.

.EXAMPLE
  .\.claude\skills\log-work\scripts\New-ActivityDay.ps1
#>
[CmdletBinding()]
param(
    [DateTime]$Date = (Get-Date),
    [string]$Author,
    [string]$Slug
)

$ErrorActionPreference = 'Stop'
$getRoot = Join-Path $PSScriptRoot '..\..\_shared\scripts\Get-RepoRoot.ps1'
$repoRoot = & $getRoot -StartDir $PSScriptRoot

$ensureScript = Join-Path $PSScriptRoot 'Ensure-LogAuthor.ps1'
$ensureArgs = @{ RepoRoot = $repoRoot }
if ($Author) { $ensureArgs['AuthorOverride'] = $Author }
if ($Slug) { $ensureArgs['SlugOverride'] = $Slug }
$authorJson = & $ensureScript @ensureArgs | ConvertFrom-Json

$dateStr = $Date.ToString('yyyy-MM-dd')
$monthStr = $Date.ToString('yyyy-MM')
$dayDir = Join-Path $repoRoot "knowledge-center/logs/$monthStr"
$dayFile = Join-Path $dayDir "$dateStr.$($authorJson.Slug).md"
$template = Join-Path $repoRoot '.claude/skills/log-work/template.md'

if (Test-Path $dayFile) {
    Write-Output "Exists: $dayFile"
    return $dayFile
}

New-Item -ItemType Directory -Force -Path $dayDir | Out-Null

if (Test-Path $template) {
    $content = (Get-Content $template -Raw) `
        -replace 'YYYY-MM-DD', $dateStr `
        -replace 'Author Name', $authorJson.Name `
        -replace 'author-slug', $authorJson.Slug
} else {
    $content = @"
---
date: $dateStr
author: $($authorJson.Name)
author_slug: $($authorJson.Slug)
type: daily-log
---

# $dateStr

## Work

"@
}

Set-Content -Path $dayFile -Value $content -Encoding UTF8
Write-Output "Created: $dayFile"
return $dayFile
