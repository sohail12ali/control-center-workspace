---
ticket: "T-002"
artifact: verification
---

# Verification: T-002

Windows smoke 2026-09-05 against
`desktop/src-tauri/target/debug/delivery-console-desktop.exe` (pid 26688).
Loopback `GET /api/config` → 200.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Tray icon present after launch | PASS | Hidden window class `tray_icon_app`; UIA `NotifyItemIcon` named “Delivery Console” under Show Hidden Icons |
| 2 | Menu is skeleton only | PASS | `tray.rs` ids only; pytest `test_features.py` |
| 3 | Header is not a backend picker | PASS | Header `MenuItem` enabled=false (`tray.rs`) |
| 4 | Header shows backend id or dash | PENDING | JS emit path served (`/desktop-tray.js` contains `desktop-session`). Live header text not read from the native menu |
| 5 | Hide then left-click restores window | PASS | `WM_CLOSE` → window `IsWindowVisible=false`, process + serve still up; UIA Invoke on `NotifyItemIcon` → visible again |
| 6 | New chat opens form without `/send` | PENDING | `agents.js` serves `trayAction` / `newChat`. Menu click not driven (UIA right-click did not expose a host-owned menu) |
| 7 | Mute writes autoRead and stops speaking | PENDING | Same as 6 |
| 8 | Interrupt HTTP or toast | PENDING | Same as 6. Bare `POST .../chats/missing/interrupt` from PowerShell is 403 (not the webview origin) |
| 9 | Close leaves serve; Quit owned/reused | PARTIAL | Close/hide leaves serve 200 (owned or not). Quit not clicked — would exit the smoke host |
| 10 | features.toml skeleton available | PASS | pytest `TestSkeletonAvailable` |
| 11 | Browser unchanged | PASS | Tray is native; `desktop-tray.js` no-ops without `__TAURI__` |
| 12 | No shell/fs on loopback | PASS | `loopback-chrome.json` window + `core:event:default` only |
| 13 | Host builds | PASS | `cargo build --manifest-path desktop/src-tauri/Cargo.toml` |
| 14 | Sidecar tests | PASS | `python -m pytest desktop/tests` 13 passed |

## Test Results

```
python -m pytest desktop/tests -q
.............                                                            [100%]
```

```
cargo build --manifest-path desktop/src-tauri/Cargo.toml
Finished `dev` profile [unoptimized + debuginfo] target(s) in 4.80s
```

Hide / Show (Win32 + UIA, same session):

```
pid=26688 hwnd=2164818 vis=True tray=True serve=up:200
after-close alive=True vis=False tray=True serve=up:200
NotifyItemIcon Invoke → vis=True serve=up:200
```

## Edge Cases Probed
- Catalog: non-skeleton rows remain `available = false` (pytest)
- Loopback capability: no `shell` / `fs`
- Caption close does not destroy the process or drop `/api/config`
- Tray button is under **Show Hidden Icons** on this machine (not pinned to the visible tray)

## Notes

The app was left running after smoke so the native menu (New chat / Mute /
Interrupt / Quit) can be clicked by hand. Automated right-click did not yield
a host-owned UIA menu (Cursor’s open plan doc contains the same strings).

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
