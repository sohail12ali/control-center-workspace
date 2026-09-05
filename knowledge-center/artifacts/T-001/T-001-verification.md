---
ticket: "T-001"
artifact: verification
---

# Verification: T-001

Amended 2026-09-05 after the Tauri host swap. Earlier WinForms evidence is kept
as history below.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Tauri window, one header, live Console UI | PASS | `cargo build --manifest-path desktop/src-tauri/Cargo.toml` Finished `dev` (0 errors). Launched `delivery-console-desktop.exe`; `GET http://127.0.0.1:8790/api/config` 200 title Noble Delivery Console. Window is frameless (`decorations(false)`). Caption buttons are in `.brandrow` (`console/static/index.html` `#winControls`, `desktop-chrome.js`) |
| 2 | Process is `kanban.py serve` | PASS | `desktop/sidecar.py` spawn_serve still starts `python console/kanban.py serve` |
| 3 | Close / kill host ends spawned sidecar | PASS | Smoke 2026-09-05: owned pid assigned to job (`added=true`); `Stop-Process -Force` on the host → port 8790 down. Also `Destroyed` → `sidecar.py stop --pid` |
| 4 | Existing serve is reused and not killed | PASS | `desktop/tests/test_sidecar.py::TestEnsureLive::test_second_ensure_reuses_and_does_not_kill` |
| 5 | Browser serve works; no window buttons | PASS | `#winControls` has `hidden`; CSS `.win-controls { display: none }` unless `html.in-shell:not(.os-mac)` |
| 6 | `console/` has no new runtime deps | PASS | `test_no_package_managers_inside_console`; Cargo.toml is under `desktop/src-tauri/` |
| 7 | Automated sidecar tests | PASS | `python -m pytest desktop/tests` → 10 passed (including after POSIX `killpg` / Windows `close_fds=True`) |
| 8 | Min/max/close/drag on Windows | PASS (code + host IPC) | Loopback capability `loopback-chrome.json` grants window APIs to `http://127.0.0.1:*/*`. Buttons wired in `desktop-chrome.js`. Not a recorded click-test of each glyph |

## Test Results

| Command | Result |
|---------|--------|
| `python -m pytest desktop/tests` | **10 passed** |
| `cargo build --manifest-path desktop/src-tauri/Cargo.toml` | **Finished `dev`** with xwin CRT (`desktop/msvc-env.ps1`); VS Native Desktop UAC was cancelled so headers come from `%USERPROFILE%\.xwin` |

## Edge Cases Probed
- Ephemeral port, never 8790, in sidecar pytest
- `Command.output()` hang: serve inherited the ensure pipe on Windows until `close_fds=True`
- Force-kill of the host must not leave :8790 listening (job object)
- `find_repo_root` on a tree outside this repo raises

## History — WinForms host (2026-09-05, superseded)

Ran on Windows 10, Python 3.14.0, .NET SDK 10.0.301. `dotnet build desktop/host/DeliveryConsole.Desktop.csproj` 0 errors. That tree is removed; see [[T-001-decision-log]] `host-tauri-2`.

## Notes
Rustc 1.98.1. `link.exe` exists under VS 18 Community; desktop CRT headers were missing until xwin splat. Do not require admin VS workload if `.xwin` is present.

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
