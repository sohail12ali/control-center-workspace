Add-Type -AssemblyName System.Drawing

$dst = 'D:\Workspace\noble-wave\noble-salah\assets\images\steps'
$files = Get-ChildItem $dst -Filter '*.png' | Sort-Object Name

Write-Host ("Count: " + $files.Count)
Write-Host ""

$oversized = @()
foreach ($f in $files) {
    $img = [System.Drawing.Image]::FromFile($f.FullName)
    $w = $img.Width
    $h = $img.Height
    $img.Dispose()
    $flag = if ($w -gt 600 -or $h -gt 800) { " *** EXCEEDS 600x800 ***" } else { "" }
    Write-Host ($f.Name + "  " + $w + "x" + $h + $flag)
    if ($flag -ne "") { $oversized += $f.Name }
}

Write-Host ""
if ($oversized.Count -gt 0) {
    Write-Host "OVERSIZED files: $oversized"
} else {
    Write-Host "All images within 600x800 bounds."
}
