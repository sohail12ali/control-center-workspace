---
ticket: "T-022"
artifact: user-stories
created: "2026-10-01"
---

# User Stories: T-022

Extracted from frozen [[T-022-requirements]] (15 FR, 10 NFR rows, 12 BR). Six stories; every FR is traced to at least one. Task ids refer to [[T-022-plan]].

**Created by:** `requirements T-022 stories` · **Validated by:** `validate-artifacts T-022 links`

## Stories

### US-1: Catch a behaviour change after a prompt edit, for free
**As a** harness maintainer
**I want to** run `python console/kanban.py evals replay` after editing an agent or skill file
**So that** I find out in seconds, at no cost, whether the graders, fixtures and cited rules still agree.

**Acceptance Criteria:**
- [ ] `evals replay` exits 0 on the committed set, 1 when a golden fixture fails, 2 on an unknown `--scenario` (FR-1, FR-5).
- [ ] Replay spawns no process and opens no socket, and says it proves graders and fixtures, not live behaviour (FR-5, BR-2, BR-6).
- [ ] The whole committed set replays in 5 s or less (NFR Performance).

**Business Rules:** BR-2, BR-6, BR-10
**Edge Cases:** empty or does-nothing transcript fails every scenario; a golden fixture that fails or a must-fail fixture that passes is a `grading` error.
**Related Components:** `console/evals/runner.py`, `console/evals/grade.py`
**Related Tasks:** T-022-03, T-022-06, T-022-08
**Priority:** High · **Story Points:** 5

### US-2: Author a scenario that cannot pass vacuously
**As a** harness maintainer
**I want to** describe a behaviour as one TOML file with a closed set of deterministic checks and a pass and a must-fail fixture
**So that** a green scenario means the check can fail and the rule it encodes really exists in a committed prompt.

**Acceptance Criteria:**
- [ ] Loader rejects trailing-comment/single-quoted values, unknown keys or check kinds, duplicate check ids, missing fixtures, bad regexes, `mode != "plan"`, newline quotes (FR-2).
- [ ] A scenario with no positive check is rejected; every committed scenario fails an empty and a does-nothing transcript (FR-2).
- [ ] Five check kinds behave as specified; grading is byte-identical across runs (FR-4).
- [ ] Preflight verifies each `[[source]]` quote verbatim in its file; a moved rule is `product/rule_moved` (FR-11).
- [ ] `console/evals/README.md` documents the format, check kinds and how to add a scenario (FR-14).

**Business Rules:** BR-1, BR-5, BR-12
**Edge Cases:** CRLF checkouts match quotes (text-mode read); torn line in a fixture is `grading`; duplicate `tool_use` id is one call.
**Related Components:** `console/evals/scenario.py`, `console/evals/grade.py`, `console/evals/README.md`
**Related Tasks:** T-022-01, T-022-02, T-022-03, T-022-04, T-022-11
**Priority:** High · **Story Points:** 8

### US-3: Know which failures are mine to fix
**As a** harness maintainer reading a red run
**I want to** see one class per failure (grading, infra, product, model), a reason code, and an evidence excerpt
**So that** I fix the right thing first and never misread a login failure as a prompt regression.

**Acceptance Criteria:**
- [ ] One test per class asserts class and reason; the real auth-failure shape maps to `infra/auth` (FR-8).
- [ ] Higher precedence wins when several conditions hold: grading > infra > product > model (FR-8, BR-11).
- [ ] Usage and cost are `UNKNOWN`, never 0, unless the raw `result` reports a number; totals with an unknown are marked partial (FR-7, BR-4).
- [ ] Behaviour failures are not retried (FR-8, BR-8).

**Business Rules:** BR-4, BR-8, BR-11
**Edge Cases:** `is_error=true` with `subtype="success"`; usage block present with one key missing; reported zero stays zero.
**Related Components:** `console/evals/grade.py`, `console/evals/runner.py`
**Related Tasks:** T-022-01, T-022-02, T-022-05
**Priority:** High · **Story Points:** 5

### US-4: Gate a prompt edit by the scenarios that cover it
**As a** developer editing `.claude/agents/X.md` or a skill
**I want to** run `evals replay --changed` and see exactly the scenarios whose `subjects` cover my diff, and which changed files are uncovered
**So that** T-020, T-021 and later skill shrinking are gated by evidence without running everything.

**Acceptance Criteria:**
- [ ] Touching `.claude/agents/builder.md` selects exactly the scenarios with `agent:builder` (FR-9).
- [ ] `--changed` with nothing gated exits 0 "nothing to gate"; changed gated files with zero covering scenarios exit 2 and name the files (FR-1, FR-9).
- [ ] `evals list --coverage` reports 7/7 agents and names each skill without a scenario (FR-9, FR-10).
- [ ] A subject naming a missing file fails preflight as `product` (FR-9).

**Business Rules:** BR-5, BR-12
**Edge Cases:** staged, unstaged and untracked files all count; unresolvable `--base` exits 2 with the git error.
**Related Components:** `console/evals/scenario.py`, `console/evals/runner.py`, `console/kanban.py` (evals block)
**Related Tasks:** T-022-07, T-022-08, T-022-12, T-022-13
**Priority:** High · **Story Points:** 5

### US-5: Spend money on a real model only on purpose
**As the owner of the Claude login**
**I want** `evals live` to run only with an explicit `--confirm`, never under `CI`, in read-only `plan` mode, one attempt per scenario, with no side effects on tickets, telemetry, notifications, worktrees or Runs
**So that** a live eval can never surprise me with spend or mutate the vault, and its cost is recorded as UNKNOWN unless the CLI reports it.

**Acceptance Criteria:**
- [ ] Without `--confirm`, or with `CI=1`, exit 2 and the fake `spawn` is never called (FR-6).
- [ ] With a fake `spawn` replaying a fixture, grading equals replay and the record carries `mode="live"` (FR-6).
- [ ] No `agent_manager.create`, `telemetry.record_turn`, `notify.send`, worktree, Run or chat entry; one `evals.live` audit record without transcript text (FR-6, FR-15, BR-7).
- [ ] A process with no `result` is terminated at the timeout as `infra/timeout`; exceeding `max_tool_calls` is `model/tool_cap` (FR-6).
- [ ] There is no live verb and no MCP path to `live` (FR-12, BR-3).
- [ ] The one real smoke run is recorded NOT RUN until Q9 is answered (FR-6 manual AC).

**Business Rules:** BR-3, BR-7, BR-8
**Edge Cases:** two concurrent live runs use separate `run_id` dirs; claude not on PATH is `infra/spawn_error`.
**Related Components:** `console/evals/runner.py`, `console/config/verbs.toml`, `console/server/verb_handlers.py`
**Related Tasks:** T-022-08, T-022-09, T-022-10, T-022-13
**Priority:** Medium · **Story Points:** 8

### US-6: Start with ten grounded scenarios and a CI signal
**As a** harness maintainer
**I want** ten starter scenarios (one per cited rule, 7/7 agents covered) with 20 fixtures, a CI replay signal, and fixtures scanned for leaked paths and keys
**So that** the suite is useful on day one, stays free in CI, and cannot leak a workstation path or key through a promoted transcript.

**Acceptance Criteria:**
- [ ] 10 scenario files and 20 fixtures exist; `evals replay` is green; each must-fail fixture fails its declared `fail_checks` (FR-10).
- [ ] Every `[[source]]` quote is a substring of its cited file at build time; the real-workspace guard test passes (FR-10, FR-11).
- [ ] Claim-before-work and stop-on-claim-conflict are listed in README § Deferred (FR-10).
- [ ] Fixture scan fails on a planted `C:\Users\x` or `sk-` string (FR-13).
- [ ] `harness lint` stays 0/0 at 39 skills, 7 agents; `pytest -k evals` passes with no network and no `claude` on PATH (FR-13).
- [ ] Results record validates; nothing is written outside `console/.cache/evals/` except the audit record (FR-15).

**Business Rules:** BR-5, BR-9, BR-10
**Edge Cases:** a quoted rule that T-020/T-021 edit trips `product/rule_moved` until re-pinned in the same change.
**Related Components:** `console/evals/scenarios/`, `console/evals/fixtures/`, `.github/workflows/verify.yml`
**Related Tasks:** T-022-06, T-022-11, T-022-12, T-022-13
**Priority:** High · **Story Points:** 8

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Catch a behaviour change, for free | Pending | High | 5 | 03, 06, 08 |
| US-2 | Author a scenario that cannot pass vacuously | Pending | High | 8 | 01, 02, 03, 04, 11 |
| US-3 | Know which failures are mine to fix | Pending | High | 5 | 01, 02, 05 |
| US-4 | Gate a prompt edit by covering scenarios | Pending | High | 5 | 07, 08, 12, 13 |
| US-5 | Spend money on a real model only on purpose | Pending | Medium | 8 | 08, 09, 10, 13 |
| US-6 | Ten grounded scenarios and a CI signal | Pending | High | 8 | 06, 11, 12, 13 |

## Traceability Matrix

| Story | FRs | Components | Tasks |
|-------|-----|-----------|-------|
| US-1 | FR-1, FR-5 | runner, grade | 03, 06, 08 |
| US-2 | FR-2, FR-3, FR-4, FR-11, FR-14 | scenario, grade, README | 01, 02, 03, 04, 11 |
| US-3 | FR-7, FR-8 | grade, runner | 01, 02, 05 |
| US-4 | FR-9 | scenario, runner, kanban evals block | 07, 08, 12, 13 |
| US-5 | FR-6, FR-12, FR-15 | runner, verbs.toml, verb_handlers | 08, 09, 10, 13 |
| US-6 | FR-10, FR-13, FR-15 | scenarios/, fixtures/, verify.yml | 06, 11, 12, 13 |

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements]] · [[T-022-requirements-draft]] · [[T-022-user-stories]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-critique-report]] · [[T-022-progress]] · [[T-022-verification]]
