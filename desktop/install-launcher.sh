#!/usr/bin/env bash
# Installs a desktop launcher for the Delivery Console release build:
# macOS -> a minimal .app skeleton (needed so mic/Screen-Recording
# permissions attach to a stable bundle identity); Linux -> a .desktop
# file under the user's applications directory. Windows has its own
# desktop/install-shortcut.ps1 — this script refuses there so the two never
# disagree about which is authoritative.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_ID="com.noble.deliveryconsole"
APP_NAME="Delivery Console"
RELEASE_BIN="$REPO_ROOT/desktop/src-tauri/target/release/delivery-console-desktop"

usage() {
    cat <<USAGE
Usage: install-launcher.sh [--target=macos|linux] [app-dir]

  --target   Force which installer runs (default: detected from
             \`uname -s\`). Mainly for CI: a Linux runner has no macOS
             hardware, but the .app skeleton is pure file/plist writing,
             so its structure is still provable there.
  app-dir    macOS only. Where to write the .app bundle.
             Default: \$HOME/Applications/$APP_NAME.app
USAGE
}

os_name() {
    case "$(uname -s)" in
        Darwin) echo "macos" ;;
        Linux) echo "linux" ;;
        *) echo "unsupported" ;;
    esac
}

install_macos() {
    local app_dir="${1:-$HOME/Applications/$APP_NAME.app}"
    local contents="$app_dir/Contents"
    local macos_dir="$contents/MacOS"

    mkdir -p "$macos_dir" "$contents/Resources"

    cat > "$contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleIdentifier</key>
    <string>$BUNDLE_ID</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleExecutable</key>
    <string>delivery-console-desktop</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>0.1.0</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Delivery Console uses the microphone for voice commands to the workspace assistant.</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
PLIST

    if [ -f "$RELEASE_BIN" ]; then
        ln -sf "$RELEASE_BIN" "$macos_dir/delivery-console-desktop"
    else
        echo "warning: release binary not found at $RELEASE_BIN — .app written without the executable symlink; build first, then re-run" >&2
    fi

    echo "macOS .app skeleton written: $app_dir"
}

install_linux() {
    local apps_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    local desktop_file="$apps_dir/delivery-console.desktop"

    mkdir -p "$apps_dir"

    cat > "$desktop_file" <<DESKTOP
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Native shell for the Delivery Console
Exec=$RELEASE_BIN
Path=$REPO_ROOT
Terminal=false
Categories=Development;Utility;
StartupWMClass=delivery-console-desktop
DESKTOP

    chmod +x "$desktop_file"
    echo ".desktop file written: $desktop_file"
    if [ ! -f "$RELEASE_BIN" ]; then
        echo "warning: release binary not found at $RELEASE_BIN — build first: cargo build --release --manifest-path desktop/src-tauri/Cargo.toml" >&2
    fi
}

main() {
    local target=""
    local args=()
    for arg in "$@"; do
        case "$arg" in
            --target=*) target="${arg#--target=}" ;;
            -h|--help) usage; exit 0 ;;
            *) args+=("$arg") ;;
        esac
    done

    if [ -z "$target" ]; then
        target="$(os_name)"
    fi

    case "$target" in
        macos) install_macos "${args[0]:-}" ;;
        linux) install_linux ;;
        *)
            echo "unsupported target: $target (expected macos or linux; Windows has its own desktop/install-shortcut.ps1)" >&2
            exit 1
            ;;
    esac
}

main "$@"
