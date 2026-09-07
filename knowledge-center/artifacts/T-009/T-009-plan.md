---
ticket: "T-009"
artifact: plan
---

# Plan: T-009

## Approach

Five parts, in dependency order. The painter goes first because a click that
opens the microphone with no visible feedback would be worse than no click at
all.

## Tasks

### [x] T-009-01 — One painter (1 h)
- [x] `tray_paint.rs`: `attach`, `note`, `repaint`
- [x] `tray_link` and `listen` call through it; `main` attaches after the tray
- **Done-criteria:** opening the mic repaints immediately; no handle set is a
  no-op, so the state machine still tests without a desktop session
- **Depends on:** —

### [x] T-009-02 — The armed icon (1 h)
- [x] `gen_tray_icons.py` gains `armed`; four PNGs regenerated and committed
- [x] `State::Armed`, `Event::Armed(bool)`, `visual_state` rule, tooltip
- [x] `hands_free` raises it on start and clears it on stop
- **Done-criteria:** hands-free shows armed and does not flicker per take
- **Depends on:** T-009-01

### [x] T-009-03 — The click (2 h)
- [x] `click.rs`: `Action`, the pure `action()`, and `act()`
- [x] Left-click wired in `tray.rs`; a **Talk** menu row for Linux
- **Done-criteria:** every state and mode resolves to the documented action
- **Depends on:** T-009-02

### [x] T-009-04 — The setting (1 h)
- [x] `tray_click_action` in `DEFAULTS`/`WRITABLE`, validated against three values
- [x] `console_settings.rs`: the shell's one settings reader; `hands_free`
      reuses it
- **Done-criteria:** a bad value is refused; the click reads it fresh
- **Depends on:** T-009-03

### [x] T-009-05 — The Settings panel (2 h)
- [x] `assistant()` panel in `settings.js`, every writable key plus read-only
      `vision_models`
- **Done-criteria:** values round-trip; a refusal shows the server's sentence
- **Depends on:** T-009-04

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-009-01 — One painter | 1 h | moving existing code |
| T-009-02 — Armed icon | 1 h | the generator does the drawing |
| T-009-03 — The click | 2 h | new module + tray wiring |
| T-009-04 — The setting | 1 h | mirrors T-008's settings work |
| T-009-05 — Settings panel | 2 h | modelled on the Telegram panel |
| **Total** | **7 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1, 2 | T-009-03 |
| 3 | T-009-01 |
| 4 | T-009-02 |
| 5 | T-009-04 |
| 6 | T-009-05 |
| 7 | T-009-03 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| A click that opens the mic with no feedback | High | High | The painter lands first, and the live run reads the paint log | Builder |
| Users expect a click to open the window | Med | Med | `tray_click_action` = `show` restores it; the menu still has Show window | Builder |
| Linux gets no click at all | High | Med | The **Talk** menu row is the substitute, present on every platform | Builder |
| The panel and the server disagree about what is valid | Med | Med | The panel validates nothing; it shows the server's refusal | Builder |

## Dependencies
- Blocks: —
- Blocked by: T-008 (hands-free), T-006 (voice)

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
