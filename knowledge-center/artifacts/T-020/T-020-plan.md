---
ticket: "T-020"
artifact: plan
---

# Plan: T-020

## Structure decision

**Multi-layer.** 21 components over four layers (data, service, verb/API, protocol/CI), 30 tasks, and a real dependency chain (Run store -> reconcile -> retry policy -> watchdog -> escalation -> verbs; claims read Run state). Far past the flat threshold (1 component, at most 6 tasks), so planning ran `analyze-components` -> `estimate(upfront)` -> `breakdown-tasks` -> `challenge-plan`. Detail: [[T-020-components]], [[T-020-task-breakdown]], [[T-020-implementation-plan]] (file lists, named tests, verification commands), [[T-020-effort-estimate]]. This file is the master phases -> slices -> tasks view.

No new `tech-select`: everything is stdlib and existing machinery (decision-log a6 fixed `taskkill /T` over Job Objects; `zoneinfo` is stdlib with a fail-closed fallback).

## Approach

Build the Run lifecycle first (decision a1: `runs.set_state` has no caller outside tests, `runs.py:107`), because retry, liveness and stale-claim all read Run state. Harden child processes at the session layer as its own phase (a4, a6: the watchdog protects work, hygiene protects the machine, so hygiene applies to every chat). Then the pure classifier modules, the retry policy and a watchdog thread owned by `agent_manager` (a13, a14), then claims and the review counter on `ticket.toml` (a7, a8, a9, a12). Every task is test-first and ends with its touched-module tests green; the suite stays green at every task boundary. Fakes, injected clocks and `os.name` patching only; the single real-process test uses `sys.executable`. The plan hit eight design gaps in the frozen requirements that are resolved in the plan, not by rewriting requirements (CR-19..CR-26 in [[T-020-critique-report]]).

## Slices

- **Slice A (Phases 0-2): lifecycle + hygiene.** Baseline fix, Run store, session state, config readers, reconcile; kill/env/caps/linger; real-process proof and CI step.
- **Slice B (Phase 3): classify, watch, retry.** Evidence on `turn.end`, classifier, quota reset, liveness, retry table, watchdog, retry execution, escalation, verbs.
- **Slice C (Phase 4): claims and review loop.** UTC `claimed_at`, `claimed_run`, `claim_status`, adoption, `claim-release`, `review-round`, context digest, verifier/fixer text.
- **Phase 5: VERIFY.** Evidence table, lint, suite count, NFR checks.

Hard build order = the task order below. Shared-file tasks never run in parallel (collision map in [[T-020-implementation-plan]]).

## Tasks

### Phase 0: baseline green

### [x] T-020-01 — 0a-1 Fix the 3 date-rot stop-hook tests (FR-19 AC3) (1h)
- **Files:** `console/tests/test_stop_hook.py` (test only). **Tests:** `TestDateIndependence::test_stale_claim_semantics_hold_on_any_calendar_date`.
- **Done-criteria:** `test_stop_hook.py` passes at today's date and 3 injected dates; full suite 1445 passed / 0 failed. **Basis:** 4 tests, one pattern already in the file (:62-75). **Depends on:** —

### Phase 1: Run lifecycle foundation

### [x] T-020-02 — 1a-1 Run store: states, defaults on read, locked update (FR-1, FR-2) (3h)
- **Files:** `console/server/runs.py`, `console/tests/test_runs.py`. **Verify:** `python -m pytest -o addopts="" -q console/tests/test_runs.py`.
- **Done-criteria:** FR-1 and FR-2 checklists; 8 threads x 20 rounds no lost update; terminal immutable byte-identical. **Basis:** 7 ACs, lock via existing `tomlio._acquire_lock`, Windows replace retry. **Depends on:** T-020-01

### [x] T-020-03 — 1a-2 Session output timestamp, last-turn memory, `pending_for` (FR-4) (3h)
- **Files:** `console/server/agent_session.py`, `console/server/agent_approvals.py`, new `console/tests/test_session_state.py` [SHARED:agent_session.py].
- **Done-criteria:** FR-4 checklist; 10 000 lines < 2 s; `ApiSession` tests unchanged. **Basis:** 4 ACs, 2 files, retained tool counts for FR-13. **Depends on:** T-020-01

### [x] T-020-04 — 1a-3 `run_config.py` readers with warn-once fallback (NFR-10) (2h)
- **Files:** new `console/server/run_config.py`, new `console/tests/test_run_config.py`.
- **Done-criteria:** defaults, overrides, invalid values fall back with exactly one warning, no config write. **Basis:** 4 sections, pattern `jobs._config` (`jobs.py:67`). **Depends on:** T-020-02

### [x] T-020-05 — 1a-4 `run_sync.py`: `session_view`, pure `sync_run`, startup sweep (FR-3 AC1-4) (3h)
- **Files:** new `console/server/run_sync.py`, new `console/tests/test_run_sync.py` [SHARED:run_sync.py].
- **Done-criteria:** table-driven rows, 3-Run sweep, terminal never changed, ring overflow, stop beats `scheduled_retry`, `scheduled_retry`+absent session untouched; failure rows go through a fail-closed `decide_failure` seam. **Basis:** 5 ACs, pure function with a large row table. **Depends on:** T-020-02, T-020-03

### Phase 2: process hygiene

### [x] T-020-06 — 2a-1 `procs.py`: `kill_tree`, `tree_spawn_kwargs`, `clean_env` (FR-5, FR-6) (3h)
- **Files:** `console/server/procs.py`, `console/tests/test_procs.py` [SHARED:procs.py].
- **Done-criteria:** `nt` and POSIX branches proven by `os.name` patching, own-group-only `killpg`, exited-process no-op, deny list stripped and auth vars kept. **Basis:** 7 ACs, port of `desktop/sidecar.py:208-245`. **Depends on:** T-020-04

### [x] T-020-07 — 2a-2 Wire spawn and kill sites; `kill_process()`; `repo_root` on sessions (FR-5, FR-6) (3h)
- **Files:** `console/server/agent_session.py`, `console/server/agents.py`, `console/server/agent_manager.py`, `console/tests/test_procs.py` [SHARED:agent_session.py, agents.py, agent_manager.py].
- **Done-criteria:** all three spawn sites pass clean `env=` and group flags; no bare `.kill()/.terminate()` in session or agents; the 6 existing spawn-site flag tests (`test_procs.py:123-183`) unchanged. **Basis:** 6 call sites, 3 files. **Depends on:** T-020-06

### [x] T-020-08 — 2b-1 Per-line cap, O(1) one-shot buffer accounting (FR-7 AC1, AC3) (2h)
- **Files:** `console/server/procs.py`, `agent_session.py`, `agents.py`, new `console/tests/test_output_caps.py` [SHARED].
- **Done-criteria:** 3 MiB line truncated, next line parses; 10 000 lines < 1 s; `truncated` kept. **Basis:** 3 ACs, one helper, three loops. **Depends on:** T-020-07

### [x] T-020-09 — 2b-2 Per-turn output cap with `on_limit` seam, Run written before kill (FR-7 AC2) (3h)
- **Files:** `agent_session.py`, `agent_manager.py`, `console/tests/test_output_caps.py` [SHARED]. **Done-criteria:** one notice + one kill past the cap, none across two turns, Run terminal first, no-Run chat still killed. **Basis:** counter reset at two `turn.start` publish points, callback plumbing. **Depends on:** T-020-02, T-020-08

### [x] T-020-10 — 2b-3 Lingering-after-result kill (FR-8) (3h)
- **Files:** `agent_session.py`, `agents.py`, new `console/tests/test_linger_kill.py` [SHARED]. **Done-criteria:** killed within grace+1 s, not killed when it exits in time, `LiveSession` exempt, old process (not next turn's) is killed, no `_observe` swap. **Basis:** rewrite of `_read_turn`, 7 tests with real tiny timers. **Depends on:** T-020-08, T-020-09

### [x] T-020-11 — 2c-1 Real-process tree tests, Windows control (FR-9) (3h)
- **Files:** new `console/tests/test_proc_tree.py`. **Done-criteria:** root, child, grandchild gone within 10 s through `kill_process`; Windows control leaves the grandchild alive then cleans it; no `T020-TREE` process remains; reach limit in the docstring. **Basis:** ctypes pid probes, two platforms, orphan safety. **Depends on:** T-020-07

### [x] T-020-12 — 2c-2 CI step so process tests run on the Windows runner (FR-9 AC2, NFR-3) (1h)
- **Files:** `.github/workflows/verify.yml` (outside `console/`; needs owner acknowledgement). **Done-criteria:** step added to the `desktop` matrix job with `::error::` annotation; result `PENDING-CI` until pushed. **Basis:** one YAML step beside two existing ones. **Depends on:** T-020-11

### Phase 3: classify, watch, retry

### [x] T-020-13 — 3a-1 `turn.end` failure evidence (FR-10) (1.5h)
- **Files:** `console/server/agent_normalize.py`, new `console/tests/test_normalize_evidence.py`. **Done-criteria:** evidence fields and defaults, bounds, existing keys unchanged. **Basis:** 2 ACs, one function (:300-324). **Depends on:** T-020-03

### [x] T-020-14 — 3a-2 Failure classifier (FR-11) (3h)
- **Files:** new `console/server/run_failures.py`, new `console/tests/test_run_failures.py` [SHARED:run_failures.py]. **Done-criteria:** 20+ fixture rows, `success+is_error` is auth, prose never classifies, unknown is `unclassified`. **Basis:** 12 classes, precedence table. **Depends on:** T-020-13

### [x] T-020-15 — 3a-3 Quota reset time (FR-12) (3h)
- **Files:** `run_failures.py`, new `console/tests/test_quota_reset.py` [SHARED]. **Done-criteria:** Paperclip fixtures incl. rollover, no-tzdata fail closed, seconds equal ms, 12-hour edges. **Basis:** 4 ACs, zone seam, DST-sensitive fixtures. **Depends on:** T-020-14

### [x] T-020-16 — 3a-4 Run-liveness classes and evidence collector (FR-13) (3h)
- **Files:** `run_failures.py`, `run_sync.py`, new `console/tests/test_liveness.py` [SHARED]. **Done-criteria:** class table, plan-mode exemption, Bash-only is `empty`, 8 text fixtures, never retried. **Basis:** 5 ACs, pattern port from Paperclip `run-liveness.ts:65-67`. **Depends on:** T-020-15, T-020-05

### [x] T-020-17 — 3a-5 Retry table, caps, due time; real `decide_failure` (FR-15, FR-3 AC5) (3h)
- **Files:** `run_failures.py`, `run_sync.py`, `test_run_failures.py`, `test_run_sync.py` [SHARED]. **Done-criteria:** N+1 failures give N retries then `failed`, zero retries for non-retryable, quota 3 h / unknown / 3 days, total cap 3, config overrides. **Basis:** 5 ACs + 2 sync rows, arithmetic edge cases. **Depends on:** T-020-14, T-020-15, T-020-16, T-020-05

### [x] T-020-18 — 3b-1 Pure stall `evaluate` (FR-14 pure ACs) (2h)
- **Files:** new `console/server/run_watchdog.py`, new `console/tests/test_run_watchdog.py`. **Done-criteria:** 599/601/700/1801 s, approval pause, output resets clock, flag-only, API session never evaluated, UTC fallback chain. **Basis:** 7 tests, pure. **Depends on:** T-020-04, T-020-05

### [x] T-020-19 — 3b-2 `tick`, single-flight, thread lifecycle, terminal-before-kill (FR-14, NFR-6, NFR-7) (3h)
- **Files:** `run_watchdog.py`, `runs.py` (`list_active`), `agent_manager.py`, `features/agents_feature.py`, `audit.py` [SHARED]. **Done-criteria:** Run already `timed_out` when `kill_tree` fires, per-Run isolation, concurrent ticks act once, join < 2 s, 100-Run tick < 100 ms, terminal ids not re-parsed. **Basis:** 10 ACs, thread + lock. **Depends on:** T-020-18, T-020-07

### [x] T-020-20 — 3b-3 Retry execution via `send` / `resume` (FR-16) (3h)
- **Files:** `run_watchdog.py`, `test_run_watchdog.py` [SHARED]. **Done-criteria:** live `send` once and `attempt=2`, resume refusal gives `failed/resume_refused` and never `create`, durable across restart, stop cancels. **Basis:** 4 ACs, T-011 invariant. **Depends on:** T-020-19, T-020-17

### [x] T-020-21 — 3b-4 Escalation comment, idempotent (FR-17) (2h)
- **Files:** `run_watchdog.py`, `test_run_watchdog.py` [SHARED]. **Done-criteria:** action-table row per class, three syncs one comment, `done`/ticketless none, no secrets. **Basis:** 4 ACs, marker-based dedupe. **Depends on:** T-020-20

### [x] T-020-22 — 3c-1 `run-watch` and `run-retry` verbs (FR-18) (3h)
- **Files:** `console/config/verbs.toml`, `console/server/verb_handlers.py`, new `console/tests/test_run_verbs.py` [SHARED]. **Done-criteria:** counts and no mutation on empty, refusals, one new Run with old file byte-identical, both verbs in MCP list and HTTP route. **Basis:** 4 ACs, two handlers. **Depends on:** T-020-21

### Phase 4: claims and review loop

### [x] T-020-23 — 4a-1 UTC `claimed_at`, `claimed_run`, auto-link (FR-19) (3h)
- **Files:** `tickets.py`, `backends/base.py`, `backends/vault_backend.py`, `verb_handlers.py`, new `console/tests/test_claims.py` [SHARED]. **Done-criteria:** UTC regexp, `parse_claimed_at` cases, older toml loads, link/auto-link/zero/two/unknown run, release clears, stop-hook green. **Basis:** 5 ACs, 4 files. **Depends on:** T-020-02, T-020-01

### [x] T-020-24 — 4a-2 `claim_status` (FR-20) (3h)
- **Files:** `tickets.py`, new `console/tests/test_claim_status.py` [SHARED]. **Done-criteria:** all nine rows, planner/builder scenario, `scheduled_retry` ACTIVE, config fallback. **Basis:** 4 ACs, 9-row table. **Depends on:** T-020-23, T-020-04

### [x] T-020-25 — 4a-3 Adopt stale claim under lock; `ready` lists stale (FR-21) (3h)
- **Files:** `tickets.py`, `vault_backend.py`, `verb_handlers.py`, `audit.py`, new `console/tests/test_claim_adopt.py` [SHARED]. **Done-criteria:** two threads one winner (20 rounds), audit row with previous holder and basis, existing claim tests unchanged. **Basis:** 4 ACs, concurrency. **Depends on:** T-020-24

### [x] T-020-26 — 4a-4 `claim-release` with audited force (FR-22) (2h)
- **Files:** `tickets.py`, `verbs.toml`, `verb_handlers.py`, `audit.py`, new `console/tests/test_claim_release.py` [SHARED]. **Done-criteria:** holder, stale and forced paths, reason of at least 10 chars, verb in CLI and MCP lists. **Basis:** 4 ACs, one mutator. **Depends on:** T-020-25

### [x] T-020-27 — 4b-1 Review counter and `review-round` verb (FR-24) (3h)
- **Files:** `tickets.py`, `verbs.toml`, `verb_handlers.py` (+ `tracker_add` `raised_by`), `audit.py`, new `console/tests/test_review_round.py` [SHARED]. **Done-criteria:** rounds 1-3 then one critical question, 4th refused, resets, older toml loads, config threshold. **Basis:** 6 ACs, verb + mutator. **Depends on:** T-020-26

### [x] T-020-28 — 4b-2 Context digest: claim, review, runs (FR-23) (2h)
- **Files:** `console/server/context.py`, `console/tests/test_context.py`. **Done-criteria:** three markdown lines and JSON keys; plain ticket renders as before. **Basis:** 2 ACs, additive. **Depends on:** T-020-24, T-020-27, T-020-02

### [x] T-020-29 — 4b-3 Verifier and fixer protocol text (FR-25) (1h)
- **Files:** `.claude/agents/verifier.md`, `.claude/agents/fixer.md`, new `console/tests/test_agent_protocol_text.py`. **Done-criteria:** `review-round` and the `review.escalated` stop rule in both, contracts intact, lint 0/0 at `39 skills, 7 agents`, no new agent or skill file. **Basis:** two short text edits + grep tests. **Depends on:** T-020-27, T-020-28

### Phase 5: verify

### [x] T-020-30 — 5a-1 Final verification and evidence table (all FR, NFR-1/4/5) (2h)
- **Files:** `T-020-verification.md` (verifier). **Done-criteria:** the eight checks in [[T-020-implementation-plan]] § Phase 5 with cited output: full suite count, harness lint, `console/static` untouched, stdlib-only imports, process-tree marker check, 20-run concurrency, config untouched, CI status. **Basis:** command runs plus 115-row table. **Depends on:** T-020-01..T-020-29

## Effort

| Phase | Tasks | Estimate | Basis |
|-------|-------|---------:|-------|
| 0 | T-020-01 | 1 h | 4 tests, existing pattern |
| 1 | T-020-02..05 | 11 h | 7+4+5+4 ACs, 4 files, locking |
| 2 | T-020-06..12 | 18 h | 3 shared files, 2 platforms, real-process test |
| 3 | T-020-13..22 | 26.5 h | 12 classes, 10-AC watchdog, thread, verbs |
| 4 | T-020-23..29 | 17 h | 5 mutators, concurrency, protocols |
| 5 | T-020-30 | 2 h | commands + evidence table |
| **Total** | 30 tasks | **75.5 h** | 73.5 h dev + 2 h verify; envelope 58-95 h dev, Medium confidence ([[T-020-effort-estimate]]) |

### Acceptance criterion coverage

All 102 FR-level acceptance criteria, 11 NFRs and 2 ticket-level criteria map to at least one task; none are orphaned. Task rows list their FR in [[T-020-task-breakdown]]; the per-AC table skeleton is in [[T-020-implementation-plan]] § Phase 5.

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| FR-1 (3), FR-2 (4) | T-020-02 |
| FR-3 (5) | T-020-05 (AC1-4), T-020-17 (AC5) |
| FR-4 (4) | T-020-03 |
| FR-5 (4) | T-020-06, T-020-07 |
| FR-6 (3) | T-020-06, T-020-07, T-020-04 |
| FR-7 (3) | T-020-08, T-020-09 |
| FR-8 (3) | T-020-10 |
| FR-9 (3) | T-020-11, T-020-12 |
| FR-10 (2) | T-020-13 |
| FR-11 (4) | T-020-14 |
| FR-12 (4) | T-020-15 |
| FR-13 (5) | T-020-16 |
| FR-14 (10) | T-020-18, T-020-19 |
| FR-15 (5) | T-020-17 |
| FR-16 (4) | T-020-20 |
| FR-17 (4) | T-020-21 |
| FR-18 (4) | T-020-22 |
| FR-19 (5) | T-020-01 (AC3), T-020-23 |
| FR-20 (4) | T-020-24 |
| FR-21 (4) | T-020-25 |
| FR-22 (4) | T-020-26 |
| FR-23 (2) | T-020-28 |
| FR-24 (6) | T-020-27 |
| FR-25 (3) | T-020-29 |
| NFR-1..NFR-11 | T-020-30 (checks 1-9), plus the per-task tests named in each NFR |
| Ticket-level (lint 0/0; 222 baseline + 3 date-rot) | T-020-01, T-020-29, T-020-30 |

## Risks

Source column cites the artifact line or `CR-{n}` that surfaced the risk. High x high: none.

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| Shared-file collisions: `agent_session.py` is edited by five tasks, `verbs.toml`/`verb_handlers.py` by three, `tickets.py` by four | Med | Med | One builder, strict order, collision map in the implementation plan, one commit per task, full suite at each phase boundary | Builder | components graph analysis |
| Write-once Run store assumption: Runs were never updated, so other readers (Agents tab `console/static/overview.js:139`, `assistant_feature.py:133`, `verbs_feature.py:95`) may meet new states or fields; `console/.cache/runs/` is empty here so nothing was observed live | Med | Med | Defaults on read, additive fields only, old record test (1a-1), UI untouched (NFR-1). Not verified in a browser: new state names may render with a default tone; UI is Tier 3, out of scope | Builder/Verifier | analysis § Current State |
| Watchdog kills a legitimately silent long tool call (output cadence during tools unverified) | Low | High | Defaults 10/30 min, `stall_kill_secs=0` flag-only, `watchdog_enabled=false`, terminal record then escalation comment, `run-retry` path; approval waits never count | Builder | CR-10, context-snapshot § Open Confirmations |
| `taskkill /T` reach limit (grandchild whose parent exited first) and soft ask ineffective on windowless processes, so each kill costs the full grace | High | Med | Limit stated in test docstring and requirements; Job Object deferred as a todo; stop/interrupt use `grace=2.0`; 2c-1 measures whether the soft ask works and records it | Builder | decision a6, CR-29 |
| No real `claude` available: `resetsAt` units, status vocabulary, `CLAUDECODE` nesting guard unconfirmed | High | Med | Open Confirmations (Q14); both units accepted by magnitude, prose fallback, otherwise no retry (fail closed); verification marks these PENDING, never PASS | Verifier | context-snapshot § 6 |
| CI-only defects: the console `tests` job is ubuntu-only; POSIX branches are proven only by `os.name` patching; a Windows runner result is unknowable until pushed | Med | Med | Task 2c-2 adds the process tests to the windows/ubuntu/macos `desktop` job; `PENDING-CI` stated plainly; `::error::` annotations | Builder | CR-19, memory cross-platform-defects-only-ci-finds |
| Windows `PermissionError` on `os.replace` of a Run file a reader holds open, and flaky lock acquisition | Med | Med | Replace retry in `runs._write`, torn-read hammer test, 20-round concurrency parametrisation | Builder | CR-28, `tomlio.py:279-297` |
| Orphan `python` processes left by an aborted process-tree test on Windows | Med | Low | Bounded 60 s sleeps, fixture finalizer force-kills recorded pids, `T020-TREE` marker and PowerShell check in verify | Builder | memory stray-terminal-root-cause |
| `trackers.add` is an unlocked read-modify-write (adjacent defect): concurrent comments can lose an update | Low | Low | Single-flight tick, marker-based idempotent escalation, todo recorded; not fixed here | Builder | CR-35 |
| Stop-hook compares `ticket.toml` `updated` (local date) with UTC `claimed_at`: a UTC+5 user can lose the reminder between 00:00 and 05:00 local | Low | Low | Fail-quiet (a missed reminder, never a wrong expiry); todo; test pins same-day behaviour | Builder | CR-34 |
| Delegated build reports success the disk contradicts (T-004) | Med | Med | Evidence per task = pytest line and file:line via `progress-tracker`; verifier re-runs the full suite | Verifier | memory subagent-status-not-evidence |
| Parallel tickets T-021/T-022 edit the same tree and read this ticket's field names | Med | Low | Names `liveness`, `claim_status`, `review` are the contract; rebase before 3c-1, 4a-4, 4b-1; no edits to their files | Builder | requirements § 10 |

12 of 12 risks have a stated mitigation; high x high: 0.

## Open Confirmations (not blocking, carried into verification)

Q12 human gate for `claim-release force` / `review-round human_decision` (user edits `agents.toml` by hand); Q13 phone alert on stall/escalation (user edits `[notify].events`); Q14 one captured real quota stream. The design works without all three.

## Dependencies
- Blocks: [[T-021-summary]] (liveness lint reads `liveness` and `claim_status`), [[T-022-summary]] (evals of claim/escalate behaviour).
- Blocked by: none (T-016, T-017, T-018 are shipped; read and extended in place).

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-user-stories]] · [[T-020-decision-log]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-effort-estimate]] · [[T-020-critique-report]] · [[T-020-plan-iteration-log]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
