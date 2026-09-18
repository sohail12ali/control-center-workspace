---
ticket: "T-009"
artifact: requirements
---

# Requirements: T-009

Two asks — a click that talks, and a Settings control for the Assistant —
plus a defect found while reading the code for the first one: shell-side state
changes never repainted the tray at all.

## Functional Requirements
1. One left-click on the tray icon does the useful thing for the state the
   icon is showing: talk when idle, send the take in progress when listening,
   stop a reply being read aloud, show the window when only a human can help.
2. That behaviour is configurable: plain "show the window", or arm/disarm
   hands-free.
3. The icon repaints when the SHELL's state changes — the microphone opening
   above all — not only when the console's event stream sends something.
4. Hands-free has its own icon, distinct from a take in progress.
5. Every setting the Assistant reads can be changed from the Settings tab, and
   an invalid value is refused with the server's own explanation.
6. On Linux, where the toolkit gives the app no left-click, the same action is
   one click away in the menu.

## Non-Functional Requirements
1. One painter. Every source of tray events uses it; no module keeps a private
   copy of "how to draw the icon".
2. One settings reader in the shell. No second TOML parser, no cached value
   that would need a restart to take effect.
3. The click decision is a pure function, testable without a tray, a
   microphone or a desktop session.
4. No new CSS: the panel is built from the classes the Settings tab already
   has.

## Acceptance Criteria
- [x] 1. `click::action` returns the right action for every state, in all
      three modes, and a permission card outranks all of them.
- [x] 2. An unrecognised setting falls back to the default rather than leaving
      the icon inert.
- [x] 3. Opening the microphone repaints the tray immediately.
- [x] 4. Hands-free shows `armed`, and takes inside it do not flicker the icon.
- [x] 5. `tray_click_action` validates against exactly three values and the
      committed file ships the same default.
- [x] 6. The Settings panel reads and writes every writable key, shows
      `vision_models` read-only, and surfaces a refusal without inventing its
      own copy of the rules.
- [x] 7. The menu carries a **Talk** row.

## Out of Scope
- A double-click or modifier gesture for the window (the menu row is the way).
- Interrupting a running turn from the icon — the window has that button, and
  a single click is too easy to hit for something that discards work.
- Verifying the Linux click path on Linux: CI builds it, nothing runs it.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
