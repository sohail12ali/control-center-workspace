---
ticket: "T-009"
artifact: decision-log
---

# Decisions: T-009

## one-painter-for-the-tray
**Decision:** `tray_paint` owns the only path from a state change to the icon,
holding the `AppHandle` in a `OnceLock`. `tray_link`, `listen` and
`hands_free` all call it.
**Rationale:** The icon lagged because `repaint` was private to `tray_link`
and reachable only from the console's event stream — so the microphone, which
the shell knows about and the console does not, could not repaint anything.
Threading an `AppHandle` into "record some audio" would put a UI type in the
signature of an audio function; a global set once at setup does not.
**Impact:** Painting before the handle is set is a no-op, which is what keeps
the state machine testable without a desktop session.

## the-click-is-a-table
**Decision:** `click::action(state, needs_approval, setting) -> Action` is
pure, and `act` is dispatch to entry points that already existed.
**Rationale:** The interesting half of a click is the decision, and a decision
with six states and three modes wants a test per row, not a live tray.
**Impact:** Eighteen combinations are covered by four unit tests; the live run
then only had to prove the wiring.

## a-permission-card-outranks-every-mode
**Decision:** `needs_approval` returns `ShowWindow` before the mode is even
consulted.
**Rationale:** A card is a question addressed to a human. Sending a take into
a chat that is blocked on one would queue words behind a modal nobody has read.
**Impact:** One early return, and a test that walks every mode and state.

## armed-outranks-listening
**Decision:** While hands-free holds the mic under a wake word, the icon shows
`armed` — including during a take. `listening` is reserved for push-to-talk,
or hands-free with the wake word off.
**Rationale:** Hands-free opens a take, discards it, and opens another. An
icon that followed the takes would flash red several times a minute while
telling the user nothing they can act on. What they can act on is the standing
fact: the mic is open, and gated.
**Impact:** `visual_state` gains two arms; `Event::ListenStart` inside
hands-free now repaints nothing, which is the point.

## the-paint-log-reports-what-is-shown
**Decision:** `tray_paint` logs `assistant.shown()`, not `state()`.
**Rationale:** Caught in the live run: the log said "painted idle" while the
armed icon was on screen, because armed is folded in at paint time. A log line
that contradicts the screen is worse than none.
**Impact:** `Assistant::shown()` exists so the two cannot drift.

## settings-validate-in-one-place
**Decision:** The Settings panel POSTs and shows whatever the server says. It
does not check values itself.
**Rationale:** `assistant_config.update` already validates every key and its
refusals are written for a human. A second copy in JavaScript would drift from
the one that actually decides, and the drift would show up as a control that
looks like it worked.
**Impact:** A refusal reloads the panel from the server, so what is on screen
is always what is stored.

## Links
- [[T-009-summary]] · [[T-009-analysis]] · [[T-009-requirements]] · [[T-009-decision-log]] · [[T-009-plan]] · [[T-009-progress]] · [[T-009-verification]]
