---
ticket: "CC-T005"
artifact: progress
---

# Progress: CC-T005

## Status Summary
Stage: Closed — four tasks done, three items deferred with reasons.

## Dated Log

### 2026-08-29

**All four tasks done (~9 h vs 12 h est). 467 tests passing; harness lint clean.**

- **Diff cards.** `tool_preview.py` computes the change server-side, so the CLI hook path and
  the in-process API loop get it from one implementation and cannot drift. It is honest about
  its limits: an edit whose target text is absent says the call will fail *before* you approve
  it, an ambiguous edit names the occurrence count, and a shell command is shown rather than
  predicted. A preview that crashes never stops the question being asked — a gated tool must
  not run unreviewed because a diff failed.
- **Command palette.** Sourced entirely from things that already exist, so a new verb or
  ticket appears without touching it. A verb needing a ticket is greyed with the reason rather
  than offered and then failed.
- **Verbs over HTTP** as a plugin with no tab, following the codebase's own convention.
- **Per-turn cost.** Found that `usage` events were being discarded outright, so the header's
  token counters sat at zero forever while looking perfectly plausible.
- Fixed two bugs in tests I had just written — one compared substring positions and matched a
  word inside my own comment. Both are recorded in [[CC-T005-verification]] because a test
  that passes while asserting nothing is worse than no test.

- Done: CC-T005-01 through -04.
- Deferred: TD-1 composer pickers, TD-2 graph view, TD-3 ticket drawer.
- Next: CC-T006 (Phase 3b) — premises already recorded from the user's answers.

## Links
- [[CC-T005-summary]] · [[CC-T005-analysis]] · [[CC-T005-requirements]] · [[CC-T005-decision-log]] · [[CC-T005-plan]] · [[CC-T005-progress]] · [[CC-T005-verification]]

