$src = 'D:\Workspace\control-center-workspace\knowledge-center\assets\images'
$dst = 'D:\Workspace\noble-wave\noble-salah\assets\images\steps'

# Male steps 1-6, 8-9 (PNG)
foreach ($n in @(1,2,3,4,5,6,8,9)) {
    $f = "male_step_$n.png"
    $s = Join-Path $src $f
    $d = Join-Path $dst $f
    Copy-Item $s $d -ErrorAction Stop
    Write-Host "Copied $f"
}

# Convert male_step_7.jpg -> male_step_7.png using System.Drawing
Add-Type -AssemblyName System.Drawing
$jpgPath = Join-Path $src 'male_step_7.jpg'
$pngPath = Join-Path $dst 'male_step_7.png'
$img = [System.Drawing.Image]::FromFile($jpgPath)
$img.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)
$img.Dispose()
Write-Host "Converted male_step_7.jpg -> male_step_7.png"

# Female steps 2, 4-9 (available; skip 1 which has space, skip 3 which doesn't exist)
foreach ($n in @(2,4,5,6,7,8,9)) {
    $f = "female_step_$n.png"
    $s = Join-Path $src $f
    $d = Join-Path $dst $f
    Copy-Item $s $d -ErrorAction Stop
    Write-Host "Copied $f"
}

# Copy female_step_ 1.png (with space) -> female_step_1.png (no space)
$spacedSrc = Join-Path $src 'female_step_ 1.png'
$renamedDst = Join-Path $dst 'female_step_1.png'
Copy-Item $spacedSrc $renamedDst -ErrorAction Stop
Write-Host "Copied female_step_ 1.png -> female_step_1.png"

Write-Host "Done."
