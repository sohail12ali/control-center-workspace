---
ticket: "T-014"
artifact: progress
---

# Progress: T-014

## Status Summary
Stage: VERIFY — the delegation loop driven end to end. See
[[T-014-verification]].

## Dated Log

### 2026-09-08
- Done:
  - T-014-01 `work_backend`/`work_model`; `where` overrides so the shipped
    lm-studio row reaches 192.168.1.14 with agents.toml untouched.
  - T-014-02 Residency and capabilities from whatever the base URL answers,
    with `None` kept distinct from "nothing loaded".
  - T-014-03 The `delegate` verb, gated on every API-backed row, with a
    watcher that reports the result back into the Assistant chat.
  - T-014-04 Talk and Work rows in Settings with real model dropdowns, loaded
    marks and one confirm before an unloaded model.
- Two bugs found by running it: a delegation started from a terminal hung
  because its approval card had no port to appear from (now refused), and the
  result was never reported because the watcher waited for the chat to die
  rather than the turn to end (now reports on turn end).
- Verified: pytest 1173, lint clean; live loop — card raised, approved, "24"
  answered, notice returned.
- Not verified: a LOCAL model answering through the Assistant or choosing to
  delegate — the LM Studio box dropped twice mid-session.
- Blocked: —
- Next: re-run the local half when that box is up.

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
