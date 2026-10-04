---
ticket: "T-020"
artifact: task-breakdown
---

# Task breakdown: T-020

Atomic, test-first tasks. Task ID `{phase}{slice}-{n}` with the plan's `T-020-{nn}` id in brackets. Every task: one builder session (1-3h), names its FRs, its files, its tests and its verification command (the last three are in [[T-020-implementation-plan]]; the table here carries the FR, acceptance summary, effort and blocking notes). Every task ends with its touched-module tests passing and the full suite `python -m pytest -o addopts="" -q` not regressing (baseline 1445 collected, 1442 passed, 3 failed; task 0a-1 makes it 1445/0).

**Produced by:** `breakdown-tasks`. **Consumed by:** implementation-plan synthesis, `estimate(mode=forecast)`.

Shared-file flag in Notes: **[SHARED:file]** means another task also edits that file, so builders must run strictly in the listed order.

---

## Phase 0: Baseline green

### Slice 0a: date-rot fix

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 0a-1 (T-020-01) | Make the 3 failing `test_stop_hook.py` tests clock-independent by freezing `tickets.date` (the `_FrozenDate` pattern already at `test_stop_hook.py:62-75`); add a parametrised any-date test. Test-only edit | ticket-claims-data (test) | FR-19 AC3 | `test_stop_hook.py` passes at today's date and at 3 injected dates; semantic assertions unchanged; full suite 1445 passed / 0 failed | 1 | done | Record the 1445/1442/3 baseline in progress.md first. No production code. Actual ~0.5h (approx). Full suite 1448 passed / 0 failed (3 new params); `test_stop_hook.py` 20 passed; helper `test_stop_hook.py:31-45` |

---

## Phase 1: Run lifecycle foundation (Slice A part 1)

### Slice 1a: store, session state, config, reconcile

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 1a-1 (T-020-02) | `runs.py`: add `timed_out`/`scheduled_retry`, TERMINAL/ACTIVE, default-on-read fields, lock-guarded `update` (terminal+annotations in one write, then refused), `set_state` via `update`, `find_active_chat_run`, `os.replace` retry on `PermissionError` | run-store | FR-1, FR-2, NFR-8 | FR-1 3 ACs, FR-2 4 ACs; 8-thread no-lost-update x20 rounds; torn-read test | 3 | done | Bottleneck (9 dependents). Existing `test_runs.py` stays green. Actual ~1.5h (approx). `test_runs.py` 45 passed (33 new); full suite 1481 passed / 0 failed; `runs.py:19-24` (states), `update` `runs.py:176`. `_read` also retries `PermissionError` (reader-side Windows race found by the hammer test) |
| 1a-2 (T-020-03) | `BaseSession`: `last_output_at` (UTC) + monotonic, `started_utc`, `last_turn` (turn.end + rate_limit + bounded tool counts), `turn_count`, `stop_requested`; snapshot keys; `Approvals.pending_for` | session-state | FR-4 | FR-4 4 ACs; 10 000 lines < 2 s; ring overflow keeps `last_turn` | 3 | done | **[SHARED:agent_session.py]** first of five. Adds the tool-count evidence FR-13 needs (CR-22) and `started_utc` (CR-24). Actual ~1.5h (approx). `test_session_state.py` 17 passed; full suite 1498 passed / 0 failed. Also touched `agent_api_session.py:141` (one line, `ApiSession.stop` sets `_stopping`) so `stop_requested` is true for API chats. `agent_session.py:63,187,301-302,338-355`; `agent_approvals.py:197` |
| 1a-3 (T-020-04) | New `run_config.py`: readers for `[runs]`, `[runs.retry]`, `[claims]`, `[review]` with the decision-a5 defaults and warn-once fallback | run-config | NFR-10; config ACs FR-6/14/15/20/24 | Absent sections give defaults; non-numeric, non-list, `stall_kill<=suspect`, `max_rounds 0` fall back with exactly one warning | 2 | pending | Depends 1a-1 only for convention; no file overlap. Warn mechanism: stderr line, `_warned` set |
| 1a-4 (T-020-05) | New `run_sync.py`: `session_view`, pure `sync_run(run, view, now, startup=False, decide_failure=...)`, `sweep_startup`; `decide_failure` seam defaults to fail-closed `failed/unclassified`; API sessions flagged unwatchable | run-sync | FR-3 (AC1-AC4) | Table-driven rows, 3-Run startup sweep, terminal never changed, ring overflow, stop beats scheduled_retry, `scheduled_retry`+absent session untouched | 3 | pending | Depends 1a-1, 1a-2. AC5 (process_lost + one retry) completes in 3a-5 (CR-20) |

---

## Phase 2: Process hygiene (Slice A part 2)

### Slice 2a: kill, env, spawn sites

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 2a-1 (T-020-06) | `procs.py`: `kill_tree(proc, grace)` (ask, wait, force, reap; `nt` taskkill, POSIX own-group only), `tree_spawn_kwargs()`, `clean_env(repo_root=None)`; lazy `run_config` import | procs | FR-5, FR-6 | `nt`/`posix` fake tests, exited-process no-op, taskkill missing, foreign-group refusal; deny-list sentinel test; env_strip override | 3 | pending | **[SHARED:procs.py]**. Depends 1a-3 |
| 2a-2 (T-020-07) | Use procs at every spawn and kill site: `LiveSession.start/stop`, `TurnSession._deliver/interrupt/stop`, `agents.launch/stop_job`; add `BaseSession.kill_process()`, `repo_root` param through `build()`, `LiveSession.stop_wait_secs`; `agent_manager.create/resume` pass `repo_root` | session-spawn-sites | FR-5, FR-6, BR-11 | Fake-`Popen` kwargs carry `env=` without deny list and the right group/flags at all 3 sites; no bare `.kill()/.terminate()` left; existing `test_procs.py` flag tests unchanged | 3 | pending | **[SHARED:agent_session.py, agents.py, agent_manager.py]**. Depends 2a-1. Stop/interrupt pass `grace=2.0` (CR-29) |

### Slice 2b: caps and linger

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 2b-1 (T-020-08) | `procs.iter_capped_lines`; use it in `LiveSession._read`, `TurnSession._read_turn`, `agents._reader_thread`; replace the O(n^2) `sum(len)` with a running count | output-caps | FR-7 AC1, AC3 | 3 MiB line becomes one truncated event, next line parses; 10 000 lines < 1 s; `truncated` past 200 000 chars | 2 | pending | **[SHARED:agent_session.py, agents.py, procs.py]**. Depends 2a-2. Caps count decoded characters (CR-37) |
| 2b-2 (T-020-09) | Per-turn stdout byte cap: counter reset where `turn.start` is published (`send`, `_drain`), one `output_cap` notice, `on_limit` callback (set by `agent_manager`) writes the Run `failed/output_cap` first, then `kill_process()` | output-caps | FR-7 AC2, BR-9 | One notice and one kill past the cap; two turns under the cap trigger none; Run terminal before kill; chat without a Run still killed | 3 | pending | **[SHARED:agent_session.py, agent_manager.py]**. Depends 1a-1, 2b-1 (CR-21) |
| 2b-3 (T-020-10) | Lingering-after-result kill for `TurnSession` and `agents.launch`: kill the captured process after `linger_grace_secs`, notice `lingering_killed`; replace the `self._observe` swap in `_read_turn` with a per-reader flag | linger-kill | FR-8 | Result then sleep is killed within grace+1 s; exit inside grace is not killed; `LiveSession` never killed; kills the old proc not the next turn's | 3 | pending | **[SHARED:agent_session.py, agents.py]**. Depends 2b-1, 2b-2 (CR-31) |

### Slice 2c: real-process proof and CI

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 2c-1 (T-020-11) | New `test_proc_tree.py`: `sys.executable` fake CLI -> child -> grandchild, kill through `LiveSession.kill_process()`, prove all 3 pids gone; Windows-only control with plain `proc.kill()`; docstring states the reach limit | process-tree-proof | FR-9, NFR-3, NFR-11 | All 3 pids gone within 10 s; control grandchild alive then cleaned; no orphan if the test aborts | 3 | pending | Depends 2a-2. Orphan safety: bounded 60 s sleeps, marker in cmdline, fixture force-kill backstop (CR-30) |
| 2c-2 (T-020-12) | `.github/workflows/verify.yml`: add a step to the `desktop` matrix job that runs `console/tests/test_proc_tree.py` and `test_procs.py` with `::error::` annotation on failure | ci-matrix | FR-9 AC2, NFR-3 | Workflow YAML parses; step present with annotation; CI result recorded as pending push if not pushed | 1 | pending | Edits a file outside `console/` (CR-19): needs owner acknowledgement. Depends 2c-1 |

---

## Phase 3: Classify, watch, retry (Slice B)

### Slice 3a: pure classification modules

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 3a-1 (T-020-13) | `Normalizer._result` adds `errors`, `error`, `api_error_status`, `stop_reason` (bounded) | turn-evidence | FR-10 | Fixture with fields yields them; fixture without yields `[]`/`""`/null/`""`; existing keys unchanged | 1.5 | pending | `agent_normalize.py` only. No file overlap |
| 3a-2 (T-020-14) | New `run_failures.py`: `classify(turn_end, rate_limit, exit_code, stderr_tail)` with precedence order and the 20-row fixture table | run-failures | FR-11 | 20+ rows incl. real "Failed to authenticate" sample; success+is_error is `auth_required`; prose "rate limit" in a successful turn not failed; unknown is `unclassified` | 3 | pending | **[SHARED:run_failures.py]** 1/4. Depends 3a-1 |
| 3a-3 (T-020-15) | Quota reset parse in `run_failures.py`: `resets_at` s/ms by magnitude, prose `resets [at] 4pm (Zone)`, injectable zone resolver, horizon check | run-failures | FR-12 | Paperclip fixtures with fixed `now` incl. rollover; no-tzdata fallback `""`; s == ms; 12am/12pm/13pm | 3 | pending | **[SHARED:run_failures.py]** 2/4. Real-zone tests skip with a visible reason if tzdata is absent |
| 3a-4 (T-020-16) | `run_failures.liveness` (pure) + `PLANNING_ONLY` pattern constant + evidence collector in `run_sync.py` (comments since `created`, `worktrees.diff_stat`) | run-failures, run-sync | FR-13, BR-10 | Class table; plan-mode text is `advanced`; Bash-only empty is `empty`; 8 text fixtures; `plan_only`/`empty` never retried | 3 | pending | **[SHARED:run_failures.py, run_sync.py]** 3/4. Pattern ported from `paperclip/server/src/services/run-liveness.ts:65-67` |
| 3a-5 (T-020-17) | Retry table, caps, due time (`max(table, retry_not_before)`), `quota_max_wait`, `attempts`; real `decide_failure` replaces the fail-closed default in `sync_run` | run-retry-policy | FR-15, FR-3 AC5 | N+1 failures give N retries then `failed`; every non-retryable class zero retries; quota 3 h / unknown / 3 days; total cap 3 across classes; config overrides | 3 | pending | **[SHARED:run_failures.py, run_sync.py]** 4/4. Depends 3a-2, 3a-3, 3a-4, 1a-4 |

### Slice 3b: retry, watch, escalate

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 3b-1 (T-020-18) | Pure `evaluate(run, view, now, cfg)` in new `run_watchdog.py`: silence clock, suspect/kill thresholds, approval pause, flag-only mode, unwatchable sessions | run-watchdog | FR-14 (pure ACs) | 599/601/700/1801 s, approval 1 h, output resets clock, `stall_kill_secs=0`, API session never evaluated | 2 | pending | New file. Depends 1a-3, 1a-4 |
| 3b-2 (T-020-19) | `tick(repo_root, now)`: single-flight lock, per-Run isolation, `last_tick`/`errors`, terminal-then-kill order, `list_active` terminal-id cache; watchdog thread in `agent_manager` (`start_watchdog`, `shutdown_all` join), started from `agents_feature.apply`; audit actions | run-watchdog | FR-14 rest, NFR-6, NFR-7 | Run already `timed_out` when fake `kill_tree` fires; chat without Run skipped; Run A raising leaves Run B evaluated; concurrent ticks act once; join < 2 s; 100-Run tick < 100 ms | 3 | pending | **[SHARED:agent_manager.py, audit.py]**. Also edits `runs.py` (additive `list_active`) and one line in `features/agents_feature.py`. Depends 3b-1, 2a-2 |
| 3b-3 (T-020-20) | Retry execution in `run_watchdog.py`: due `scheduled_retry` -> `send` (live) or `resume` then `send` (dead); `resume_refused`; `retry_failed`; durable across restart | run-watchdog | FR-16 | Live: one `send`, `running`, `attempt=2`; dead + `ValueError` resume: `failed/resume_refused`, `create` never called; future due untouched, fresh watchdog retries at due time; stop request cancels | 3 | done | Depends 3b-2, 3a-5 |
| 3b-4 (T-020-21) | Escalation in `run_watchdog.py`: one idempotent comment via `verb_handlers.ticket_comment`, per-class action table, 300-char bound, no secrets | run-escalation | FR-17 | Table row per class + `resume_refused` + exhaustion; three syncs give one comment; `done` and ticketless Runs give none | 2 | done | Depends 3b-3 (CR-26: dedupe by `[run <id>]` marker, not a Run write) |

### Slice 3c: verbs

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 3c-1 (T-020-22) | `run-watch` and `run-retry` rows in `verbs.toml` + one-line handlers in `verb_handlers.py`; `run-retry` creates a new Run with `retry_of` | run-verbs | FR-18 | Counts `{synced,suspicious,killed,retried}`; `done`/unknown refused; one new Run, old file byte-identical, second call refused; both in MCP tool list and HTTP route | 3 | done | **[SHARED:verbs.toml, verb_handlers.py]** 1st. Depends 3b-4 |

---

## Phase 4: Claims and the review loop (Slice C)

### Slice 4a: claims

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 4a-1 (T-020-23) | `tickets.py`: `claimed_run` default on load/create, `parse_claimed_at`, `set_claim(..., claimed_run=)`; `VaultBackend.claim` stamps UTC `...Z` with injectable `now`; `claim` verb gains `run=` with sole-ACTIVE auto-link | ticket-claims-data, claim-verbs | FR-19 | UTC regexp; `parse_claimed_at` cases; older toml loads; link/auto-link/zero/two Runs; release clears; stop-hook tests still green | 3 | done | **[SHARED:tickets.py, verb_handlers.py, backends/]**. Depends 1a-1, 0a-1 |
| 4a-2 (T-020-24) | `tickets.claim_status(repo_root, ticket_id, now)` + pure `evaluate_claim`; reads `[claims]` | ticket-claims-data | FR-20, BR-6, BR-7 | Full branch table, planner/builder scenario, `scheduled_retry` is ACTIVE, config fallback | 3 | done | **[SHARED:tickets.py]**. Depends 4a-1, 1a-3 |
| 4a-3 (T-020-25) | Adopt a stale claim inside `tomlio.atomic_update` (`set_claim(..., adopt_stale=True)`), named refusal, `ticket.claim.adopt` audit + comment, `ready` lists stale with a `claim` object | claim-verbs | FR-21 | Existing claim tests unchanged; two threads adopt, one wins; audit row has previous holder and basis; `ready` includes stale, omits held | 3 | done | **[SHARED:tickets.py, vault_backend.py, verb_handlers.py, audit.py]**. Depends 4a-2 |
| 4a-4 (T-020-26) | `claim-release` verb (`needs_ticket`, `needs_confirm`): holder, stale, forced with reason >= 10 chars; audit rows; comment on force | claim-verbs | FR-22, BR-13 | Holder releases; non-holder refused; stale released by third party; force needs reason; verb on CLI list and MCP list | 2 | done | **[SHARED:verbs.toml, verb_handlers.py, audit.py]**. Depends 4a-3 |

### Slice 4b: review loop, digest, protocols

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 4b-1 (T-020-27) | `review_rounds`/`review_escalated` defaults; `tickets.record_review` under `atomic_update`; `review-round` verb; one critical question at the cap; `tracker_add` gains optional `raised_by` | review-counter | FR-24, BR-8 | Rounds 1-3 then escalate with exactly one question; 4th refused; approved/human_decision reset; older toml loads; `max_rounds` config | 3 | done | **[SHARED:tickets.py, verbs.toml, verb_handlers.py, audit.py]** (CR-33). Depends 4a-4 |
| 4b-2 (T-020-28) | `context.build` adds `claim`, `review`, `runs`; `format_markdown` prints one line each only when non-empty | context-digest | FR-23 | Stale claim + 2 rounds + failed Run gives 3 lines and JSON keys; plain ticket renders exactly as before | 2 | done | `context.py`. Depends 4a-2, 4b-1, 1a-1 |
| 4b-3 (T-020-29) | `verifier.md` step 10 and `fixer.md` step 1: `review-round` calls and `review.escalated` stop rule | agent-protocols | FR-25 | grep finds `review-round` in both; output contracts intact; `harness lint` 0/0 and `39 skills, 7 agents`; no new files | 1 | done | Edits only `.claude/agents/verifier.md`, `fixer.md`. Depends 4b-1, 4b-2 |

---

## Phase 5: VERIFY

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| 5a-1 (T-020-30) | Full suite count, harness lint, `console/static` untouched, grep checks, AC-by-AC evidence table in `T-020-verification.md` | all | All AC, NFR-1, NFR-4, NFR-5 | See implementation-plan § Phase 5 | 2 | pending | Verifier-owned. Depends all |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 0 | 1 | 1 | 0 | 0 | 100 |
| Phase 1 | 11 | 0 | 0 | 11 | 0 |
| Phase 2 | 18 | 0 | 0 | 18 | 0 |
| Phase 3 | 26.5 | 0 | 0 | 26.5 | 0 |
| Phase 4 | 17 | 0 | 0 | 17 | 0 |
| Phase 5 | 2 | 0 | 0 | 2 | 0 |
| **Total** | **75.5** | 0 | 0 | 75.5 | 0 |

Dev total 73.5h (Phases 0-4) + 2h verify = 75.5h; reconciles with [[T-020-effort-estimate]] (Dev 73.5h, range 58-95h; QC and reserve are separate rows there) and [[T-020-implementation-plan]].

## Conventions

**Status:** pending · in-progress · done · blocked (Notes say why). **Effort:** 0.5/1/1.5/2/3h buckets.
**Dependencies:** in Notes ("Depends ..."); the numbered order inside a phase is the build order.
**Rollback:** all changes are additive defaults on read; reverting a task is `git revert` of that task's commit; no data migration is written (Run and ticket records only gain optional fields, never lose keys).

## Links
- [[T-020-summary]] · [[T-020-plan]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-effort-estimate]] · [[T-020-critique-report]]
