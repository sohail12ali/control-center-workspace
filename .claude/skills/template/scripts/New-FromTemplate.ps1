#Requires -Version 5.1
<#
.SYNOPSIS
  Renders a markdown template to a target path with placeholder substitution.

.EXAMPLE
  .\.claude\skills\template\scripts\New-FromTemplate.ps1 -TemplatePath 'knowledge-center/artifacts/_template/questions.md' -OutputPath 'knowledge-center/artifacts/T042/T042-questions.md' -Ticket 'T042'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TemplatePath,

    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [string]$Ticket,
    [string]$Title,
    [hashtable]$Replace = @{},

    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$getRoot = Join-Path $PSScriptRoot '..\..\_shared\scripts\Get-RepoRoot.ps1'
$repoRoot = & $getRoot -StartDir $PSScriptRoot

function Resolve-RepoPath {
    param([string]$Root, [string]$Path)
    if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
    return (Join-Path $Root ($Path -replace '/', '\'))
}

$templateFile = Resolve-RepoPath -Root $repoRoot -Path $TemplatePath
$outputFile = Resolve-RepoPath -Root $repoRoot -Path $OutputPath

if (-not (Test-Path $templateFile)) {
    throw "Template not found: $templateFile"
}

if ((Test-Path $outputFile) -and -not $Force) {
    Write-Output "Exists: $outputFile"
    return $outputFile
}

$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ssK')
$dateStr = (Get-Date).ToString('yyyy-MM-dd')
$titleValue = if ($Title) { $Title } elseif ($Ticket) { $Ticket } else { 'Untitled' }

# PowerShell hashtable keys are case-insensitive, so '{TITLE}' and '{Title}'
# cannot both live in $map — string .Replace() below IS case-sensitive, so both
# casings are applied explicitly via $ordinalPairs instead.
$map = @{
    '{ID}' = $Ticket
    '{T}' = $Ticket
    '{TIMESTAMP}' = $timestamp
    '{DATE}' = $dateStr
    '{YYYY-MM-DD}' = $dateStr
}
foreach ($key in $Replace.Keys) {
    $token = if ($key.StartsWith('{') -and $key.EndsWith('}')) { $key } else { '{' + $key + '}' }
    $map[$token] = [string]$Replace[$key]
}

$content = Get-Content $templateFile -Raw
foreach ($entry in $map.GetEnumerator()) {
    if ($entry.Value) {
        $content = $content.Replace($entry.Key, $entry.Value)
    }
}

$ordinalPairs = @(
    @{ Key = '{TITLE}'; Value = $titleValue }
    @{ Key = '{Title}'; Value = $titleValue }
)
foreach ($pair in $ordinalPairs) {
    if ($pair.Value) {
        $content = $content.Replace($pair.Key, $pair.Value)
    }
}

$outputDir = Split-Path $outputFile -Parent
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
}

Set-Content -Path $outputFile -Value $content -Encoding UTF8
Write-Output "Created: $outputFile"
return $outputFile
