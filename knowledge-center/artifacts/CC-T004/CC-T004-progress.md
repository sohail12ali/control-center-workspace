---
ticket: "CC-T004"
artifact: progress
---

# Progress: CC-T004

## Status Summary
Stage: Closed — all three tasks done.

## Dated Log

### 2026-08-29

**All three tasks done (~5 h vs 7 h est). 432 tests passing; harness lint clean.**

- `schedules.py` + `config/schedules.toml` + `kanban schedule list|due`, and the ticker
  started by `serve` itself.
- The parser rejects what it does not understand rather than widening it. `@daily`, `L`,
  `W`, `#`, out-of-range values and inverted ranges all raise with the schedule id. Treating
  an unparsed field as `*` would turn a typo into a job firing every minute.
- No catch-up, by design. The first tick sets a baseline; a day-long gap produces one firing
  rather than 1440. Tested.
- Fires onto the existing `JobQueue`, so scheduled work gets durable records, submission-time
  gates, and the `interrupted` state if the process dies — nothing new to trust.
- Startup says what the clock will do, or that it is idle. A scheduler nobody can see running
  is a scheduler nobody trusts.
- Fixed a stale rule in `console/SKILL.md` that still said there was no worktree isolation.

- Done: CC-T004-01, -02, -03.
- Blocked: nothing in this ticket.
- Next: **Phase 3b needs two decisions from the user** — how the console should be reachable
  remotely, and which notification channel. Neither is mine to pick.

## Links
- [[CC-T004-summary]] · [[CC-T004-analysis]] · [[CC-T004-requirements]] · [[CC-T004-decision-log]] · [[CC-T004-plan]] · [[CC-T004-progress]] · [[CC-T004-verification]]

