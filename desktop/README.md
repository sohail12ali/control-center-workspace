# Desktop shell (phase 1)

Native window around the existing Delivery Console. The HTTP server is still
`python console/kanban.py serve`. This folder does not replace it.

The host is **Tauri 2** (`src-tauri/`). Caption buttons live in the Console
header (hidden in a normal browser). macOS uses overlay traffic lights;
Windows and Linux draw min / max / close in HTML. The **system tray** is a
remote control of the live Agents chat: Show window, New chat, Mute replies,
Interrupt, Quit. Closing the window hides to the tray; **Quit** in the tray
menu exits. Quit still does not kill a `kanban.py serve` the shell did not
start.

## Run

From the workspace root you need **Rust** (`rustc`, `cargo`) and an MSVC
linker. On Windows, if `cargo build` cannot find `vcruntime.h`, either:

1. Install Visual Studio workload **Desktop development with C++**, or
2. Source `desktop/msvc-env.ps1` (uses `link.exe` from VS plus CRT/SDK from
   [xwin](https://github.com/Jake-Shadle/xwin) under `%USERPROFILE%\.xwin`).

Then:

```bash
cargo run --manifest-path desktop/src-tauri/Cargo.toml
```

If port 8790 (or whatever `console/config/console.toml` sets) is already
serving, the window attaches and **will not** kill that server on Quit. If
the shell started the server, Quit (not hide-to-tray) stops it. Force-killing
the host also stops a server it started (Windows job object).

### macOS

Xcode Command Line Tools. The window uses `titleBarStyle: Overlay`.

### Linux (Debian/Ubuntu)

`libwebkit2gtk-4.1-dev`, `build-essential`, `libssl-dev`, `librsvg2-dev`,
`patchelf`, `pkg-config`. Python 3 on PATH.

Browser access is unchanged:

```bash
python console/kanban.py serve
```

## Tests

```bash
python -m pytest desktop/tests
```

Those cover spawn, reuse, and stop. They use an ephemeral port, not 8790.

## Layout

| Path | Role |
|------|------|
| `sidecar.py` | start / probe / stop `kanban.py serve` |
| `src-tauri/` | Tauri 2 window |
| `features.toml` | tray / hotkey / Settings feature registry (`knowledge-center/wiki/desktop-assistant.md`) |
| `msvc-env.ps1` | Windows INCLUDE/LIB for incomplete VS installs |
| `tests/` | pytest for the sidecar |
