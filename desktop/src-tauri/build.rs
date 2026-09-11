fn main() {
    // tauri_build only declares rerun-if-changed for tauri.conf.json and
    // capabilities/, so regenerating the icons leaves the previous ones
    // embedded in the exe — a rebuild that silently ships the old mark.
    // The bundle icons are a build input; say so.
    for icon in ["icons/icon.ico", "icons/32x32.png", "icons/128x128.png"] {
        println!("cargo:rerun-if-changed={icon}");
    }
    tauri_build::build()
}
