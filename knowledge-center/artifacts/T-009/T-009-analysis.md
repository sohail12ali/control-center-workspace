---
ticket: "T-009"
artifact: analysis
---

# Analysis: T-009

## Context

Two requests: make a single click on the tray icon start listening, with the
icon following the assistant's state; and put the Assistant's settings on the
Settings page.

## Current State

- The left-click handler in `tray.rs` called `show_main` and nothing else. The
  microphone was reachable only by global hotkey or over the native bridge.
- `GET`/`POST /api/assistant/settings` has existed since T-004, validated and
  round-tripping, with no UI — every setting, including the four hands-free
  keys from T-008, was hand-edited TOML.
- `tray_state` is a complete, well-tested state machine with icons for every
  state.

## Key Findings

- **The icon did not actually follow the state.** `apply` and `repaint` were
  private to `tray_link` and ran only when the console's SSE stream delivered
  an event. `listen`'s own `note` folded `ListenStart` / `Transcribing` /
  `Cancel` into the machine and stopped. So the second half of the request —
  "the icon changes based on the current state" — was not a small addition;
  it was missing plumbing, and a click that opened the mic with no feedback
  would have made it more visible, not less.
- **Hands-free had no icon of its own.** It reported `listening` per take and
  `idle` between them, so an always-on microphone flickered and, in the gaps,
  presented as an idle tray.
- **The click needs a mode, not just a behaviour.** A tray click opens the app
  in most software. Making it talk is right for this app and wrong for
  someone's expectations, and that is a setting, not an argument.
- **Linux gets no left-click at all.** libappindicator opens the menu on any
  click, so the gesture cannot exist there — which makes a menu row the
  substitute rather than a nicety.
- **The panel must not validate.** `assistant_config.update` already refuses
  bad values with sentences written for a human. A second copy in JavaScript
  would drift and would show a control that looked like it worked.

## Research

Read `tray.rs`, `tray_link.rs`, `listen.rs`, `tray_state.rs`, `icons.rs`,
`gen_tray_icons.py`, `assistant_config.py`,
`features/assistant_feature.py` (the settings routes), and `settings.js` —
where the Telegram panel is the closest existing pattern for a panel that
writes server state, and `test_stylesheet.py` is the reason to reuse its
classes rather than add CSS.

## Recommended Path

Painter first, then the armed icon, then the click, then the setting, then the
panel. Prove the click with the log rather than by eye: make the shell say
what it painted, so a live run can show the icon following the microphone
instead of someone asserting that it did.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
