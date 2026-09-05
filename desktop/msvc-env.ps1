# Windows INCLUDE/LIB for cargo when VS has the linker but not CRT headers.
# Usage (from workspace root):  . .\desktop\msvc-env.ps1
#
# Prefers %USERPROFILE%\.xwin (xwin splat). Falls back to VS onecore libs
# plus the Windows SDK for pure-Rust links.

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
$msvcRoot = "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Tools\MSVC"
$msvcVer = Get-ChildItem $msvcRoot -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
$msvc = if ($msvcVer) { $msvcVer.FullName } else { $null }
$kit = "C:\Program Files (x86)\Windows Kits\10"
$kitVer = Get-ChildItem (Join-Path $kit "Lib") -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1
$kv = if ($kitVer) { $kitVer.Name } else { "10.0.26100.0" }
$xwin = Join-Path $env:USERPROFILE ".xwin"

if (Test-Path $cargoBin) {
    $env:Path = "$cargoBin;$env:Path"
}
if ($msvc) {
    $env:Path = "$(Join-Path $msvc 'bin\Hostx64\x64');$env:Path"
}

if (Test-Path (Join-Path $xwin "crt\include\vcruntime.h")) {
    $crtInc = Join-Path $xwin "crt\include"
    $sdkInc = Join-Path $xwin "sdk\include"
    $crtLib = Join-Path $xwin "crt\lib\x86_64"
    $umLib = Join-Path $xwin "sdk\lib\um\x86_64"
    $ucrtLib = Join-Path $xwin "sdk\lib\ucrt\x86_64"
    $env:INCLUDE = "$crtInc;$(Join-Path $sdkInc 'ucrt');$(Join-Path $sdkInc 'um');$(Join-Path $sdkInc 'shared');$(Join-Path $sdkInc 'winrt');$(Join-Path $sdkInc 'cppwinrt')"
    $env:LIB = "$crtLib;$umLib;$ucrtLib"
    Write-Host "msvc-env: using xwin at $xwin"
} elseif ($msvc) {
    $env:LIB = "$(Join-Path $msvc 'lib\onecore\x64');$(Join-Path $kit "Lib\$kv\ucrt\x64");$(Join-Path $kit "Lib\$kv\um\x64")"
    Write-Host "msvc-env: xwin missing; LIB is onecore+SDK only (no vcruntime.h)"
} else {
    Write-Host "msvc-env: no MSVC and no xwin"
}
