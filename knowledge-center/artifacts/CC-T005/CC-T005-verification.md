---
ticket: "CC-T005"
artifact: verification
---

# Verification: CC-T005

**Verified:** 2026-08-29 · **Result:** PASS. Three items deferred deliberately and logged.

## Evidence

| Check | Result |
| --- | --- |
| `python -m pytest` | **467 passed, 1 skipped** |
| `python console/kanban.py harness lint` | `39 skills, 7 agents \| 0 error(s), 0 warning(s)` |
| `node --check` on every touched JS file | parses |
| Live server: `/palette.js` | 200, 9,019 bytes, real content |
| Live server: `/styles.css` | 200, contains `cp-panel` and `ct-d-add` |
| Live server: `/api/verbs?ticket=CC-T005` | 8 verbs with per-ticket availability |
| Live server: `/api/jobs` | 200 |

35 tests added (tool_preview 20, plugins 15).

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| The approval gate is a review, not a yes/no | **Met** | A write preview reports +N/−M with the changed lines; an edit whose target is missing says the call will fail; an ambiguous edit names the count |
| Any tab, ticket, verb or skill is one shortcut away | **Met** | Palette sources all four live; a test asserts it uses only icons that exist |
| Deterministic jobs are runnable from the UI | **Met** | Four routes verified live and by direct handler tests |
| Cost is attributable to a step | **Met** | Model, in/out tokens, cost and duration on each turn; a capped turn reads differently from a finished one |

## Two defects found

**1. `usage` events were being thrown away.** The chat store had `case "usage": return;` — so
`tokens_in` / `tokens_out` in the session header were initialised to zero and never moved.
Nobody would have noticed from the code: the fields existed, were rendered, and were always
truthfully reporting the zero they had been given. Fixed by folding the running total in, and
taking `max(incremental, reported)` at turn end so a backend that sends both is not
double-counted.

**2. A capped turn looked like a finished one.** `subtype` was dropped on the floor, so a turn
stopped by the tool-round limit rendered as "turn complete". It now says what happened.

## Two test bugs, caught by the tests themselves

Worth recording because both were in tests I had just written, and both would have passed
while asserting nothing:

- `test_index_loads_the_palette_before_the_router` compared substring positions, and matched
  the phrase "app.js" inside a *comment* I had written above the script tag. Rewritten to
  parse the actual `<script src>` order.
- `test_the_whole_registry_builds` called `build(root)` with the wrong arity, which raised
  rather than testing anything.

## What was deferred

Three items from the dossier's UI list, each logged as a todo rather than dropped:
composer `@`/`/` pickers (TD-1), artifact graph view (TD-2), ticket drawer (TD-3). The
reasoning is in [[CC-T005-plan]] § Deferred. The palette covers most of the navigation intent
the drawer and pickers would have served, which is why they lost the priority contest rather
than the argument.

## Accessibility notes

Not an afterthought, because a keyboard-first feature that only works with a mouse is not the
feature:

- The palette traps and restores focus, and responds to arrows, Enter and Escape.
- Selection is shown by background **and** a left rail, so it survives a high-contrast mode
  that flattens backgrounds.
- Diff lines carry a `+` / `−` mark as well as colour, so add/remove survives a colour-blind
  reader.
- The open animation is inside `prefers-reduced-motion: no-preference`.

## Effort

Estimated 12 h, actual ~9 h.

## Links
- [[CC-T005-summary]] · [[CC-T005-decision-log]] · [[CC-T005-plan]] · [[CC-T005-progress]] · [[CC-T005-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
