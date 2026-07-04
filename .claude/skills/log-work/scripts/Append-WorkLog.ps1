#Requires -Version 5.1
<#
.SYNOPSIS
  Atomically appends a work bullet to the current author's per-author daily log.

.EXAMPLE
  .\.claude\skills\log-work\scripts\Append-WorkLog.ps1 -Ticket 'T013' -Category Development -Text 'Rate shop refactor build green'
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Ticket,

    [Parameter(Mandatory = $true)]
    [ValidateSet('Development', 'Code Review', 'Testing', 'Design', 'Documentation', 'Internal')]
    [string]$Category,

    [Parameter(Mandatory = $true)]
    [string]$Text,

    [double]$Hours,
    [DateTime]$Date = (Get-Date),
    [string]$Author,
    [string]$Slug
)

$ErrorActionPreference = 'Stop'

$newDayScript = Join-Path $PSScriptRoot 'New-ActivityDay.ps1'
$newDayArgs = @{ Date = $Date }
if ($Author) { $newDayArgs['Author'] = $Author }
if ($Slug) { $newDayArgs['Slug'] = $Slug }
$dayFile = (@(& $newDayScript @newDayArgs))[-1]

$hourPart = if ($PSBoundParameters.ContainsKey('Hours')) { " ~$Hours h" } else { '' }
$bullet = "- **$Ticket** [$Category]$hourPart $Text"

$content = [System.IO.File]::ReadAllText($dayFile)
if ($content -match [regex]::Escape($bullet.Trim())) {
    Write-Output "Skipped (duplicate): $bullet"
    return $dayFile
}

if ($content -notmatch '(?m)^## Work\s*$') {
    if (-not $content.EndsWith("`n")) { $content += "`n" }
    $content += "`n## Work`n"
}

$content = $content.TrimEnd() + "`n$bullet`n"
[System.IO.File]::WriteAllText($dayFile, $content, [System.Text.UTF8Encoding]::new($false))

Write-Output "Appended: $bullet"
return $dayFile
