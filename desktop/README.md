# Desktop shell (phase 1)

Native window around the existing Delivery Console. The HTTP server is still
`python console/kanban.py serve`. This folder does not replace it.

The host is **Tauri 2** (`src-tauri/`). Caption buttons live in the Console
header (hidden in a normal browser). macOS uses overlay traffic lights;
Windows and Linux draw min / max / close in HTML. The **system tray** is a
remote control of the live Agents chat: Show window, Talk, New chat, Mute
replies, Hands-free listening, Interrupt, Quit. A **left-click on the icon** is
state-aware — talk, send, or stop the voice — and is configurable through
Settings → Assistant. Closing the window hides to the tray; **Quit** in the tray
menu exits. Quit still does not kill a `kanban.py serve` the shell did not
start. A second launch while one is already running focuses the existing
window instead of opening a duplicate (`tauri-plugin-single-instance`).

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

`cargo run` no longer opens a console window in debug builds either — the
host is an unconditional GUI subsystem in both profiles now. Pass `--console`
(or set `DESKTOP_CONSOLE=1`) to get one back for troubleshooting; on Windows
this attaches to the launching terminal, or allocates a fresh one if there
isn't one, and is a no-op on Linux/macOS. Lifecycle events and any error a
window used to swallow silently are written to
`console/.cache/desktop/host.log` (rotates to `.1` at 1 MiB) regardless.

If port 8790 (or whatever `console/config/console.toml` sets) is already
serving, the window attaches and **will not** kill that server on Quit. If
the shell started the server, Quit (not hide-to-tray) stops it. Force-killing
the host also stops a server it started (Windows job object).

### macOS

Xcode Command Line Tools. The window uses `titleBarStyle: Overlay`.

### Linux (Debian/Ubuntu)

`libwebkit2gtk-4.1-dev`, `build-essential`, `libssl-dev`, `librsvg2-dev`,
`patchelf`, `pkg-config`. Python 3 on PATH. (A later ticket's own crates —
audio, tray-indicator, xcb — extend this list when they land; today's set
covers only what this crate's own `Cargo.toml` needs.)

Browser access is unchanged:

```bash
python console/kanban.py serve
```

## Release build & launchers

```bash
cargo build --release --manifest-path desktop/src-tauri/Cargo.toml
```

(On Windows, source `desktop/msvc-env.ps1` first if you hit the `vcruntime.h`
error above.) The release exe lands at
`desktop/src-tauri/target/release/delivery-console-desktop(.exe)`.

**Windows** — `desktop/install-shortcut.ps1` writes a Start-menu `.lnk`
pointed at the release exe (working directory = repo root); re-running it
overwrites cleanly. `-Desktop` / `-Startup` add a Desktop or Startup-folder
copy. `desktop/launch.ps1` launches the release exe directly from a terminal
with `--console` on by default (`-NoConsole` to launch silently, matching the
shortcut).

**macOS / Linux** — `desktop/install-launcher.sh` writes a minimal `.app`
skeleton (macOS, default `~/Applications/Delivery Console.app` —
`CFBundleIdentifier com.noble.deliveryconsole`, so mic/Screen-Recording
permissions attach to a stable identity) or a `.desktop` file (Linux,
`~/.local/share/applications/delivery-console.desktop`). `--target=macos` /
`--target=linux` forces which one runs, for CI or cross-checking (default:
detected from `uname -s`). Neither is packaged (no `.dmg`/`AppImage`/NSIS
installer) — that is deferred, see `T-003-decision-log.md`.

**Editor/agent launchers** — `.vscode/launch.json` is the Cursor/VS Code Run
and Debug config. `Delivery Console (desktop)` is `cargo run` of the Tauri
shell from the workspace root (`--console` so host logs land in the
terminal); `Delivery Console (desktop, release)` runs the already-built
release exe. Same build/run commands are also `Terminal → Run Task`.
`.claude/launch.json` names `desktop-shell` (the release exe) and
`console-serve` (`python console/kanban.py serve`, port 8790) for tooling
that reads launch configs; it is descriptive only, not consumed by any code
in this repo yet.

Every log path is under `console/.cache/desktop/` (gitignored):
`host.log` — Rust host lifecycle (append, rotates to `.1` at 1 MiB);
`serve.log` — the sidecar's own stdout/stderr (append, no rotation yet — a
known, accepted limitation, see the decision log).

## Tests

```bash
python -m pytest desktop/tests
cargo test --manifest-path desktop/src-tauri/Cargo.toml
```

`test_sidecar.py` covers spawn, reuse, log capture, and stop (ephemeral port,
not 8790). `test_pe_subsystem.py` reads the PE header of any built exe and
skips if none exists. `test_install_launcher.py` runs the real
`install-launcher.sh` under `bash` against scratch paths. `cargo test`
covers the file logger (rotation, UTC timestamps).

## Layout

| Path | Role |
|------|------|
| `sidecar.py` | start / probe / stop `kanban.py serve`; captures its output to `serve.log` |
| `src-tauri/` | Tauri 2 window (`logger.rs`, `main.rs`, `tray.rs`, `sidecar.rs`, `job.rs`) |
| `install-shortcut.ps1` | Windows Start-menu `.lnk` installer |
| `launch.ps1` | Windows terminal launcher (`--console` by default) |
| `install-launcher.sh` | macOS `.app` skeleton / Linux `.desktop` file |
| `features.toml` | tray / hotkey / Settings feature registry (`knowledge-center/wiki/desktop-assistant.md`) |
| `msvc-env.ps1` | Windows INCLUDE/LIB for incomplete VS installs |
| `tests/` | pytest for the sidecar, PE subsystem, and the launcher script |

## Voice

Push-to-talk is **Ctrl+Alt+Space** (Cmd+Option+Space on macOS), registered
from Rust so no webview capability is widened for it. A chord another
application already owns fails loudly in `host.log` rather than silently doing
nothing.

Speech recognition needs an engine, fetched deliberately and never
automatically:

```powershell
powershell -File desktop/get-whisper.ps1
```

It lands in `desktop/stt/` (gitignored) and the shell finds it on the next
listen. `GET /listen/state` on the bridge reports whether speech is available,
which microphone is selected, and whether the engine is loaded.

Reading replies aloud uses the OS synthesiser — nothing to install. Both
capabilities are probed rather than assumed, so `/health` tells the truth
about this machine.

Module layout, all under `src-tauri/src/`:

| File | Role |
|------|------|
| `audio.rs` | microphone capture, downmix, resample to 16 kHz, VAD end-pointing |
| `stt.rs` | spawns and talks to `whisper-server`; keeps the model warm |
| `tts.rs` | reads a reply aloud through the OS synthesiser; `stop()` is barge-in |
| `listen.rs` | one spoken command: record, transcribe, hand to the console |
| `tray_state.rs` | the icon's state machine (pure, unit-tested) |
| `tray_link.rs` | follows the console's event stream so the tray is right when hidden |
| `tray_paint.rs` | the one place a state change becomes pixels — every source of events calls it |
| `click.rs` | what one left-click means, as a table |
| `hands_free.rs` | always-on listening: wake word, echo handling, session cap |
| `console_settings.rs` | the shell's one reader of the Assistant's settings |
| `bridge.rs` | the loopback API the console calls |
| `capture.rs` · `ocr.rs` · `clipboard.rs` | screen, text-in-image, clipboard |
| `icons.rs` | the tray PNGs, embedded; generated by `desktop/icons/gen_tray_icons.py` |
