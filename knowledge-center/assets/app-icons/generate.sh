#!/usr/bin/env bash
# Rasterize all app-icon outputs from the SVG sources via Inkscape.
# Output layout matches Play Store / App Store / Android / iOS conventions.

set -euo pipefail

INK="/c/Program Files/Inkscape/bin/inkscape.exe"
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/source"

render() {
  local svg="$1" out="$2" w="$3" h="$4"
  mkdir -p "$(dirname "$out")"
  "$INK" --export-type=png --export-filename="$out" \
         --export-width="$w" --export-height="$h" \
         "$svg" >/dev/null 2>&1
  echo "  $(basename "$out") (${w}x${h})"
}

echo "== Master =="
render "$SRC/logo-master.svg"     "$ROOT/master/icon-1024.png"          1024 1024
render "$SRC/logo-master.svg"     "$ROOT/master/icon-512.png"           512  512

echo "== App Store (iOS marketing, no alpha — rect bg already white) =="
render "$SRC/logo-master.svg"     "$ROOT/app-store/AppIcon-1024.png"    1024 1024

echo "== Play Store =="
render "$SRC/logo-master.svg"     "$ROOT/play-store/icon-512.png"       512  512
render "$SRC/feature-graphic.svg" "$ROOT/play-store/feature-graphic.png" 1024 500

echo "== Android adaptive =="
render "$SRC/logo-foreground.svg" "$ROOT/android/ic_launcher_foreground.png" 1024 1024
render "$SRC/logo-background.svg" "$ROOT/android/ic_launcher_background.png" 1024 1024

echo "== Android legacy mipmap (square ic_launcher.png) =="
render "$SRC/logo-master.svg"     "$ROOT/android/mipmap-mdpi/ic_launcher.png"     48  48
render "$SRC/logo-master.svg"     "$ROOT/android/mipmap-hdpi/ic_launcher.png"     72  72
render "$SRC/logo-master.svg"     "$ROOT/android/mipmap-xhdpi/ic_launcher.png"    96  96
render "$SRC/logo-master.svg"     "$ROOT/android/mipmap-xxhdpi/ic_launcher.png"  144 144
render "$SRC/logo-master.svg"     "$ROOT/android/mipmap-xxxhdpi/ic_launcher.png" 192 192

echo "== iOS AppIcon set =="
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-20x20@1x.png"      20    20
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-20x20@2x.png"      40    40
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-20x20@3x.png"      60    60
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-29x29@1x.png"      29    29
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-29x29@2x.png"      58    58
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-29x29@3x.png"      87    87
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-40x40@1x.png"      40    40
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-40x40@2x.png"      80    80
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-40x40@3x.png"     120   120
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-60x60@2x.png"     120   120
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-60x60@3x.png"     180   180
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-76x76@1x.png"      76    76
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-76x76@2x.png"     152   152
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-83.5x83.5@2x.png" 167   167
render "$SRC/logo-master.svg" "$ROOT/ios/Icon-App-1024x1024@1x.png" 1024 1024

echo "== Web favicons =="
render "$SRC/logo-master.svg" "$ROOT/web/favicon-16.png"   16  16
render "$SRC/logo-master.svg" "$ROOT/web/favicon-32.png"   32  32
render "$SRC/logo-master.svg" "$ROOT/web/favicon-48.png"   48  48
render "$SRC/logo-master.svg" "$ROOT/web/icon-192.png"    192 192
render "$SRC/logo-master.svg" "$ROOT/web/icon-512.png"    512 512

echo
echo "Done."
