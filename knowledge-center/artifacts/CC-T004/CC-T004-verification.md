---
ticket: "CC-T004"
artifact: verification
---

# Verification: CC-T004

**Verified:** 2026-08-29 · **Result:** PASS. No gaps.

## Evidence

| Command | Result |
| --- | --- |
| `python -m pytest` | **432 passed, 1 skipped** |
| `python console/kanban.py harness lint` | `39 skills, 7 agents \| 0 error(s), 0 warning(s)` |
| `kanban schedule list` | both rows, parked, next run blank |
| `kanban schedule due` | `Nothing due this minute.` |
| `serve` with all parked | `scheduler: idle (2 schedule(s), all parked)` |
| `serve` with one enabled | `scheduler: harness-lint-weekday (0 9 * * 1-5) -> harness-lint, next 2026-08-31 09:00` |

46 tests added.

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| The cron subset is correct | **Met** | 14 table-driven match cases plus weekday 0/7 and the AND rule for day+weekday |
| Unsupported syntax never silently widens | **Met** | 10 rejected forms, each raising with the schedule id; a parked row is parsed too |
| Downtime does not flood the queue | **Met** | First tick fires nothing; a day-long gap yields one firing, not 1440 |
| Scheduled work is ordinary work | **Met** | Fires onto `JobQueue`, so same records, gates and states; job records `submitted_by: schedule:{id}` |
| A gated verb cannot fire unwatched | **Met** | Skipped unless `confirm = true` is in the committed row |
| The clock is visible | **Met** | Startup prints enabled schedules and next runs, or says idle |

## Design decisions

**No catch-up.** A scheduler that replayed missed firings would, after a weekend, submit
every job dozens of times at once — and these are real jobs on a real queue. The first tick
after startup establishes a baseline and fires nothing. The cost is that a firing missed
while the console was down is simply missed, which is the right trade for a board you leave
open on a workstation.

**Reject, never widen.** An unrecognised cron expression is refused at load, with the
schedule id in the message. The alternative — treating an unparsed field as `*` — turns a
typo into a job firing every minute, which is the worst available outcome and the hardest to
notice.

**AND, not real cron's OR.** When both day-of-month and day-of-week are restricted, POSIX
cron ORs them. This ANDs, because that is what someone who has not memorised the POSIX rule
expects, and the difference is documented in the config header, the README and the module.

**`confirm` lives in the file.** A scheduled job runs with nobody watching, so granting a
mutating verb its confirmation has to be a deliberate, committed act rather than something
the scheduler assumes.

**Shipped parked.** Both example schedules are read-only reports and still ship
`enabled = false`. A template must not start firing jobs nobody chose; a test enforces it.

## Links
- [[CC-T004-summary]] · [[CC-T004-decision-log]] · [[CC-T004-plan]] · [[CC-T004-progress]] · [[CC-T004-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
