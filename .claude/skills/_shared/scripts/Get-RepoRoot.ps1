#Requires -Version 5.1
<#
.SYNOPSIS
  Walks up from StartDir until knowledge-center/ exists (workspace root).
#>
[CmdletBinding()]
param(
    [string]$StartDir = $PSScriptRoot
)

$ErrorActionPreference = 'Stop'
$dir = $StartDir
while ($dir) {
    if (Test-Path (Join-Path $dir 'knowledge-center')) {
        return $dir
    }
    $parent = Split-Path $dir -Parent
    if ($parent -eq $dir) { break }
    $dir = $parent
}
throw 'Could not locate repo root (knowledge-center/ missing).'
