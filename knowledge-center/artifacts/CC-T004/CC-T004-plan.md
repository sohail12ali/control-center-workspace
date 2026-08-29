---
ticket: "CC-T004"
artifact: plan
---

# Plan: CC-T004

## Approach

Phase 3a — the half of remote dispatch that needs no decision from the user.

Phase 3 as scoped in the dossier is five things: worktrees (done in CC-T002), a job queue
(done in CC-T002), a scheduler, a remote surface, and push notifications. The last two are
**not buildable without the user**: exposing the console beyond localhost is a security
decision with several legitimate answers, and a notification channel needs a choice and
probably credentials. Building either on my own judgement would be picking for them.

The scheduler needs none of that, so it ships now and the rest waits on an answer.

**The console is the clock.** No cron entry, no systemd unit, no Task Scheduler — three
different answers to the same question, none of which belong in a workspace template. The
cost is real and gets said out loud rather than buried: nothing fires while the console is
not running.

## Tasks

### [x] CC-T004-01 — Cron subset and schedule registry (3 h)

- [x] `console/config/schedules.toml` + `console/server/schedules.py`
- [x] Five-field parser: `*`, `N`, `A-B`, `*/S`, `A-B/S`, comma lists; Sunday as 0 or 7
- [x] Unsupported syntax (`@daily`, `L`, `W`, `#`) **rejected at load with the schedule id**
- [x] Disabled rows still parsed, so a broken expression is found now
- **Done-criteria:** the grammar is pinned by table-driven tests; every unsupported form
  raises rather than defaulting to `*`.
- **Depends on:** —

### [x] CC-T004-02 — Ticker on the job queue (2 h)

- [x] Fires due schedules by submitting to `JobQueue`, so scheduled work gets the same
      durable records, gates and honest states as anything else
- [x] First tick establishes a baseline and fires nothing; missed minutes are skipped
- [x] One broken schedule cannot stop the others or kill the ticker
- [x] `confirm` must be granted in the file — a scheduled job runs unwatched
- **Done-criteria:** a day-long gap produces one firing, not 1440; the job record names the
  schedule that fired it.
- **Depends on:** CC-T004-01

### [x] CC-T004-03 — Server integration and CLI (2 h)

- [x] `serve` starts the ticker and prints what it will run, or says it is idle
- [x] `kanban schedule list` (with next run) and `schedule due` (dry run)
- **Done-criteria:** startup output names each enabled schedule and its next run; with all
  parked it says so rather than staying silent.
- **Depends on:** CC-T004-02

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T004-01 — Cron subset | 3 h | grammar + rejection + tests |
| CC-T004-02 — Ticker | 2 h | queue integration + no-catch-up |
| CC-T004-03 — Server + CLI | 2 h | lifecycle + reporting |
| **Total** | **7 h** | |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| A cron expression is misread and fires far more often than intended | Med | High | Unsupported syntax is rejected at load rather than treated as `*`; the grammar is pinned by table-driven tests | Builder |
| Catch-up after downtime floods the queue | High | High | No catch-up at all — the first tick sets a baseline and fires nothing | Builder |
| A scheduled job runs a gated verb unwatched | Med | High | `confirm` must be granted per row in a committed file; without it the firing is skipped | Builder |
| People assume it fires while the console is off | High | Med | Said in the config header, the README, the skill, and the server's own startup line | Builder |

## Out of scope — blocked on the user

- **Remote surface** (auth, binding beyond localhost, tunnel) — a security decision with
  several defensible answers.
- **Push notifications** — needs a channel choice and credentials. Without it, a remote run
  stalls at the first gated tool and the 300-second timeout denies it, so this is a hard
  prerequisite for remote, not a nicety.

## Links
- [[CC-T004-summary]] · [[CC-T004-decision-log]] · [[CC-T004-plan]] · [[CC-T004-progress]] · [[CC-T004-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T003-summary]]
