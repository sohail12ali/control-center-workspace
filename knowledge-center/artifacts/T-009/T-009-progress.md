---
ticket: "T-009"
artifact: progress
---

# Progress: T-009

## Status Summary
Stage: VERIFY — built, tested, and driven live through the real tray menu.
See [[T-009-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-009-01 One painter — `tray_paint.rs`. Found while reading for this
    ticket: shell-side events (the microphone above all) folded into the state
    machine and never repainted the icon, because `repaint` was private to
    `tray_link` and driven only by the console's event stream.
  - T-009-02 Armed icon — a hollow ring for "the mic is open and gated",
    held steady rather than following each hands-free take.
  - T-009-03 The click — `click.rs`, a pure decision plus dispatch; a **Talk**
    menu row so Linux, which gets no left-click, has the same action.
  - T-009-04 `tray_click_action` (listen / show / hands_free), validated, and
    `console_settings.rs` as the shell's one settings reader.
  - T-009-05 The Assistant panel on the Settings tab — every writable key,
    `vision_models` read-only, refusals shown in the server's own words.
  - Corrected mid-run: the paint log reported the internal state rather than
    what was on screen; `Assistant::shown()` fixes that. The T-002 tray helper
    also needed a prefix match, because the icon's accessible name is its
    (now changing) tooltip.
- Verified: pytest 1076, cargo test 110, harness lint clean, and a live run
  with one confirmed click per mode.
- Blocked: —
- Next: close-work. Still on a human: one physical left-click (every live
  check went through the menu row, which is the same entry point), and the
  Linux path, which nothing here can run.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
