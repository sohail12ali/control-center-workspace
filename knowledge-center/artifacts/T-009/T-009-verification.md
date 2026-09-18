---
ticket: "T-009"
artifact: verification
---

# Verification: T-009

Verified 2026-09-07. **pytest 1076 passed**, **cargo test 110 passed** (97
before T-009), harness lint clean, plus a live run driving the real tray menu
of the release build and reading what the shell painted.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | The click resolves correctly in every state and mode | PASS | Unit table: idle/muted/armed → Talk, listening → SendNow, speaking → StopSpeaking, thinking → ShowWindow; `show` always shows; `hands_free` toggles but still stops a reply |
| 2 | A permission card outranks everything | PASS | Unit: every mode × every state with `needs_approval` → ShowWindow |
| 3 | An unrecognised setting falls back rather than doing nothing | PASS | Unit: `"nonsense"` and `""` behave as `listen` |
| 4 | Opening the mic repaints the tray at once | PASS | Live log: `tray: click in idle -> Talk` at 12:19:59, `tray: painted listening` at 12:20:02 — the repaint follows the mic, with no console event involved. Before this ticket that line did not exist for any shell-side event |
| 5 | Hands-free shows `armed`, without flicker | PASS | Live: `-> ToggleHandsFree` → `tray: painted armed` → `hands-free: on`; off → `painted idle`. Unit: `ListenStart` and `Cancel` inside hands-free report no visual change |
| 6 | Send-now works from the icon | PASS | Live: `tray: click in listening -> SendNow` → `painted idle`, `listening=false` on `GET /listen/state` |
| 7 | Every mode reachable from the setting | PASS | Live, one confirmed click per mode: `show` → ShowWindow, `hands_free` → ToggleHandsFree, `listen` → Talk/SendNow |
| 8 | `tray_click_action` validates | PASS | Three values round-trip; `"sing"` is refused with a message naming all three and nothing is stored; the committed `assistant.toml` ships the same default |
| 9 | The Settings panel reads and writes | PASS | In the browser: the panel renders every writable key with live values; changing Tray icon click to `show` saved (`toast ok :: Saved`, `GET` confirms `"show"`), and the row's own hint changed to describe the new mode; restored to `listen` |
| 10 | A refusal shows the server's own words | PASS | Setting the wake word to `"c"` produced `toast err :: hands_free_wake_word needs at least two characters` and the field reloaded to `console` — the panel never re-implements the rules |
| 11 | The menu carries a **Talk** row | PASS | Read from the live menu via `MN_GETHMENU`: ten rows, `Talk` at index 3, enabled |
| 12 | Linux click path | **NOT TESTED** | libappindicator delivers no left-click, which is why the Talk row exists; CI builds it, nothing here runs it. See Notes |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1076 passed
cargo test (desktop/src-tauri)        ->  110 passed
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

Live run (release build, tray menu driven through Win32, one confirmed click
per step), from `console/.cache/desktop/host.log`:

```
12:19:59  tray: click in idle -> Talk
12:20:02  tray: painted listening
12:20:05  tray: click in listening -> SendNow
12:20:08  tray: painted idle
12:20:26  tray: click in listening -> ShowWindow          (setting = show)
12:20:35  tray: click in listening -> ToggleHandsFree     (setting = hands_free)
12:20:38  tray: painted armed
12:20:38  hands-free: on (wake word required: yes, "console")
12:20:44  tray: click ... -> ToggleHandsFree
12:20:47  tray: painted idle
```

## Two things the live run corrected

**The paint log lied.** It first reported `state()`, so it printed "painted
idle" at the moment the armed icon went up — armed and muted are folded in at
paint time, not stored in `state`. `Assistant::shown()` now exists and is what
gets logged, with a test asserting the two disagree exactly where it matters.

**The T-002 tray helper stopped finding the icon.** It matched the accessible
name exactly against "Delivery Console", and the tray icon's accessible name
*is* its tooltip — which now changes with the state ("Delivery Console -
listening"). Fixed to match by prefix in
`knowledge-center/artifacts/T-002/ticket-scripts/tray-menu-lib.ps1`. The
failure was itself evidence that the tooltip repaint works.

## Notes

### What a human still has to do

The OS delivering a left-click to the app is three lines in `tray.rs`, and it
is the one step here that was not exercised: every live check above went
through the **Talk** menu row, which enters `click::act` at exactly the same
point. That path was already working before this ticket (it called
`show_main`), so the risk is small — but it is untested, and saying otherwise
would be a claim about a mouse nobody moved.

### The menu is now ten rows

T-002's verification lists eight. `Talk` (T-009) and `Hands-free listening`
(T-008) have since been added — recorded there as well so the row list stays
the record of what the menu actually is.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
