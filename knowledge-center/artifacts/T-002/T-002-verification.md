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
| 4 | Header shows backend id or dash | PASS (dash case) / PENDING (backend id) | Win32 `MN_GETHMENU` read of the live menu, release exe 2026-09-06: item 0 text is `-`, state `MF_DISABLED` — dash shown and not a picker. The populated-backend case still needs the Agents tab open with a live chat (the header only updates when the tab paints and emits `desktop-session`) |
| 5 | Hide then left-click restores window | PASS | `WM_CLOSE` → window `IsWindowVisible=false`, process + serve still up; UIA Invoke on `NotifyItemIcon` → visible again |
| 6 | New chat opens form without `/send` | PASS | Release exe 2026-09-06. Window hidden via its own close (Tauri hide-to-tray) → `IsWindowVisible=False`; tray → New chat clicked at the item's DPI-correct rect → `IsWindowVisible=True`, and `GET /api/agents/chats` count unchanged (2 → 2), so nothing was auto-sent. Script: `ticket-scripts/tray-menu-lib.ps1` |
| 7 | Mute writes autoRead and stops speaking | PASS (tray side) / PENDING (speech) | Release exe 2026-09-06. `MF_CHECKED` before click = True; clicked `Mute replies`; re-read = False — the tray toggle flips real menu state. That autoRead then silences a spoken reply is not observable from outside the WebView2 process; needs one human listen |
| 8 | Interrupt HTTP or toast | PENDING — user click-through | The menu row is present and enabled (`MN_GETHMENU` read). Driving it meaningfully needs a turn in flight **in the webview's active chat**, and the active chat cannot be selected from outside the process. One human step remains |
| 9 | Close leaves serve; Quit owned/reused | PASS | Release exe 2026-09-06. Window close → hidden, `/api/config` still 200. Tray → Quit clicked → host pid gone, the serve it owned (pid 36260) gone, port 8790 closed. Reused-serve half remains as reasoned in [[T-001-verification]] AC3/AC4 |
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

## Manual smoke — 2026-09-06 (T-003 verifier pass, checklist for the user)

Rows 4/6/7/8/9 (header text, New chat, Mute, Interrupt, Quit) still can’t be driven by automation — confirmed again this pass via a second, independent UIA attempt against the T-003-verified release exe (`desktop/src-tauri/target/release/delivery-console-desktop.exe`): searching the full UI Automation tree found no drivable tray-icon element at all (stronger negative than the original finding above, which at least located a notify-icon element via UIA). Full script and output: [[T-003-verification]] § UIA attempt.

Below is the ~5-minute click-through a human should run against the release exe to close these rows. Each step states what to click and what should happen; note PASS/FAIL per step when done.

1. **Launch** the release exe (double-click, or `Start-Process desktop\src-tauri\target\release\delivery-console-desktop.exe`). Confirm the tray icon appears (Show Hidden Icons if not pinned).
2. **Row 5 recheck / Show**: left-click the tray icon (or right-click → "Show window"). Expect: the main window appears/focuses. *(Already PASS above via UIA Invoke — this step is a sanity recheck only.)*
3. **Row 6 — New chat**: right-click the tray icon → "New chat". Expect: the main window shows/focuses and a new chat form opens *without* an automatic `/send` (per FR/AC wording — no message should be pre-sent).
4. **Row 7 — Mute**: right-click → "Mute replies" (toggle). Expect: the check state flips, and `autoRead` stops speaking replies aloud for the active session (check via the header/console UI state, not just the checkmark).
5. **Row 7 (cont.) — Interrupt**: start an agent turn (from the header, ask something that takes a few seconds), then right-click → "Interrupt current turn" while it’s in flight. Expect: either an HTTP interrupt call succeeds (a toast/console log line) or a visible toast confirms the interrupt — not a silent no-op.
6. **Row 9 — Close vs Quit**: click the window’s close button (caption or Alt+F4) — expect the window hides, tray icon stays, `serve` process (check `Get-Process python`) keeps running. Then right-click the tray icon → "Quit" — expect the host process fully exits, and the `serve` process it owned also exits (or stays up if it was a pre-existing reused serve — check `owned` vs not per [[T-001-verification]] AC3/AC4 semantics).

Record each step’s PASS/FAIL directly in the Acceptance Criteria table above, replacing `PENDING` with `PASS`/`FAIL` and citing what was observed.

> **Superseded 2026-09-06** — steps 2, 3, 4 and 6 of this checklist were since driven automatically (see § Automated tray-menu drive below). Only step 5 (Interrupt) is still a human step; steps 4 and 3's header variant remain partly human for the speech and backend-id halves.

**Status of rows 4/6/7/8/9 after this pass: `PENDING — user click-through`.** Revised the same day by the automated drive below: 6 and 9 PASS, 4 and 7 PASS on their tray half, 8 still human.

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]

## Automated tray-menu drive — 2026-09-06 (supersedes the manual checklist for rows 4/6/7/9)

The earlier passes concluded the tray menu could not be automated. That was true
of **UI Automation** only. The menu is a standard Win32 popup (`#32768`), so it
can be read and clicked directly:

```
SendMessage(menuHwnd, MN_GETHMENU) -> HMENU
GetMenuStringW / GetMenuState / GetMenuItemRect  (after SetProcessDPIAware)
synthetic click at the item's centre
```

Live read of the release build's menu:

```
[0] [-]                      disabled=True   sep=False
[1] []                       disabled=True   sep=True
[2] [Show window]            disabled=False
[3] [New chat]               disabled=False
[4] [Mute replies]           disabled=False  checked=True
[5] [Interrupt current turn] disabled=False
[6] []                       disabled=True   sep=True
[7] [Quit]                   disabled=False
```

Eight rows, exactly the five skeleton actions plus a disabled header and two
separators — AC2 and AC3 re-confirmed against the live menu rather than the
source. Drives performed: Mute (check flipped True→False), New chat (hidden
window shown, no chat created), Show window (hidden→visible), Quit (host and
owned serve both exited, port closed).

Reusable helper: `ticket-scripts/tray-menu-lib.ps1` (see its README).

**Still on a human — one step:** row 8. Start a turn in the Agents tab, then
right-click the tray icon and choose "Interrupt current turn"; expect the turn
to stop or a toast, not a silent no-op. Optionally also confirm row 4's
backend-id case (header shows `claude` with a live chat on the Agents tab) and
row 7's speech half (a reply stops being read aloud after Mute).
