---
ticket: "T-020"
artifact: progress
---

# Progress: T-020

## Status Summary
Stage: TEMPLATE (build) — Phase 0, Phase 1 done; Phase 2 through T-020-10 done (2c next).

## Dated Log

### 2026-10-01 — T-020-01 (0a-1) Fix the 3 date-rot stop-hook tests (FR-19 AC3)
- Baseline before any change (full suite, `python -m pytest -o addopts="" -q`, 132 s): **1445 collected, 1442 passed, 3 failed** — the 3 failures are `TestStaleClaims::test_claim_with_no_update_is_stale`, `TestCliOneApi::test_json_reports_stale_claims`, `::test_plain_mode_prints_a_reminder_line` (bug D-1).
- Done: test-only edit of `console/tests/test_stop_hook.py`. Helper `_freeze_tickets_date` (`:31-45`) pins `tickets.date.today()` and `trackers._now_iso()` (the two clocks staleness reads; the second is needed so a comment is "after" the claim on any injected date). Applied to `test_claim_with_no_update_is_stale`, `test_claim_then_comment_is_not_stale`, `test_json_reports_stale_claims`, `test_plain_mode_prints_a_reminder_line`. New `TestDateIndependence::test_stale_claim_semantics_hold_on_any_calendar_date` (3 params: 2026-09-16, 2027-03-01, 2031-12-31). No production code changed (`git diff --stat -- console/server` empty).
- Red first: with the helper stubbed to `pass`, 6 failed (the 3 baseline + the 3 new params), for the stated reason (real `updated` date later than the fixture `claimed_at`). Then helper implemented.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_stop_hook.py` -> `20 passed`. Full suite -> `1448 passed in 169.69s` (1445 + 3 new params, 0 failed).
- Effort: ~0.5h actual (approximate) vs 1h estimated.
- Next: T-020-02 (1a-1).

### 2026-10-01 — T-020-02 (1a-1) Run store: states, defaults on read, locked update (FR-1, FR-2, NFR-8)
- Done: `console/server/runs.py`: `STATES` + `timed_out`, `scheduled_retry` (`:19-20`); `TERMINAL`, `ACTIVE` (`:23-24`); `update` (`:176`), `find_active_chat_run` (`:155`), `set_state` (`:217`); `_defaults`/`_with_defaults` applied in `get` and `list_runs` (still one file read per Run); `update()` under `tomlio._acquire_lock`/`_release_lock` on `<run>.json.lock` with a field whitelist (`UPDATABLE`), `failure_detail` capped at 500 incl. `...[truncated]` marker, `attempts` last 10, terminal refusal (ValueError, nothing written); `set_state` delegates to `update`; `find_active_chat_run`; `_write` retries `os.replace` on `PermissionError`.
- Tests added in `console/tests/test_runs.py` (33 new): `TestRunStates` (3, named per plan), `TestRunDefaults::test_pre_t020_record_returns_every_new_key_with_default` plus 2 extras (stored value not replaced, mutable defaults not shared), `TestRunUpdate::test_eight_threads_no_lost_update` x20 rounds, `::test_terminal_with_annotations_one_write_then_refused_byte_identical`, `::test_failure_detail_truncated_with_marker`, `::test_unknown_field_refused`, `::test_reader_hammering_get_never_breaks_writer`, `::test_find_active_chat_run_ignores_terminal_and_other_executors`, plus extras `::test_attempts_keeps_the_last_ten`, `::test_bad_state_and_missing_run_refused`.
- Red first: 31 failed / 14 passed before implementation (AttributeError: no `update`, `TERMINAL`, ...).
- Finding (plan said only `_write` needs the Windows retry): the reader hammer test showed `runs.get`/`list_runs` themselves raise `PermissionError` while a replace is in flight (20 errors in one run), so `_read` carries the same bounded retry. Fix is in `runs.py` `_read`; no design change.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_runs.py` -> `45 passed` (~13 s, 6 consecutive runs all green = 120 eight-thread rounds). `... test_runs.py test_run_inspector_data.py test_ui_endpoints.py` (plan verify) plus `test_assistant.py`, `test_workspace_rename_e2e.py` -> `162 passed`. Full suite -> `1481 passed in 147.01s` (1448 + 33, 0 failed).
- Time-dependent: the 20-round concurrency test costs ~0.45 s per round (lock-file polling at 0.05 s), so ~9 s of the module's ~13 s; no explicit test sleep over 2 s.
- Effort: ~1.5h actual (approximate) vs 3h estimated.
- Next: T-020-03 (1a-2).

### 2026-10-01 — T-020-03 (1a-2) Session output timestamp, last-turn memory, `pending_for` (FR-4)
- Done: `console/server/agent_session.py`: `_utc_now()` (`:63`, UTC `...Z`, patchable; local-naive `_now()` untouched), `TOOL_NAMES_MAX` (`:72`), session attributes `started_utc`, `last_output_at`, `_last_output_mono`, `last_turn`, `turn_count`; `stop_requested` property over `_stopping` (`:187`); `snapshot()` gains `started_utc`, `last_output_at`, `turn_count`, bounded `last_turn` summary; `_handle_line` stamps both clocks before parsing (`:301-302`); `_observe` keeps the turn's last `rate_limit` notice and a bounded tool-name counter and, on `turn.end`, replaces `last_turn` whole (`:338-355`, before the drain thread can start); `started_utc` set in `LiveSession.start` (`:483`) and `TurnSession.start` (`:597`). `console/server/agent_approvals.py`: `Approvals.pending_for(chat)` (`:197`), read-only under `_lock`, excludes already-answered entries.
- Deviation from the plan's file list: `console/server/agent_api_session.py:141` one line (`ApiSession.stop` now sets `self._stopping = True`). `ApiSession.stop` does not call the base class, so without it `stop_requested` is False after a human stops an API chat and the reconcile (1a-4) would read the stop as a crash. Covered by `TestStopRequested::test_api_session_stop_sets_it`.
- Tests: new `console/tests/test_session_state.py`, 17 tests: `TestOutputTimestamp` (5: the 4 named plus the monotonic stamp), `TestStartedUtc` (2), `TestLastTurn` (7: the 4 named plus none-until-a-turn-ends, bounded tool names, synthetic process_exit turn), `TestStopRequested` (2), `TestPendingFor::test_lists_while_parked_empty_after_decide_or_forget`.
- Red first: 17 failed (missing attributes / `pending_for`) before implementation.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_session_state.py` -> `17 passed in 1.34s` (10 000 lines: 0.13 s; ring overflow: 0.09 s). Plan verify set plus `test_agent_resume.py`, `test_agent_backends.py` -> `184 passed`. Full suite -> `1498 passed in 146.37s` (1481 + 17, 0 failed).
- Limits stated honestly: (1) `last_turn["tools"]` counts `tool.start` events; with `--include-partial-messages` a CLI may also repeat a call in its final assistant message, so a call can count twice (presence is what FR-13 reads; not verified against a real claude stream). (2) `ApiSession` publishes `tool.start` straight to the stream and never through `_observe`, so `last_turn["tools"]` is always empty for API sessions, and `started_utc` stays "" (its own `start`). Both matter to 3a-4 (liveness evidence) and 3b-1 (watch fallback chain); API sessions are unwatchable anyway (CR-25).
- Effort: ~1.5h actual (approximate) vs 3h estimated.
- Next: T-020-04 (1a-3).

### 2026-10-02 - T-020-04 (1a-3) Run config readers (NFR-10)
- Done: new `console/server/run_config.py`: `runs_cfg`, `retry_cfg`, `claims_cfg`, `review_cfg`, `DEFAULT_ENV_STRIP` (11 names, decision a5), `reset_warnings`; warn-once per (section, key, value) via `_warned` on stderr; unreadable `console.toml` or non-table section gives defaults + one warning; no write path (test greps the source). `[runs.retry]` nested table read from `runs["retry"]`.
- Test file `console/tests/test_run_config.py` (written by the interrupted builder) reviewed against NFR-10 and the plan list: correct, no change needed; it was red only by `ImportError` (module missing). 20 tests, all plan-named ones present.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_config.py console/tests/test_boards.py` -> `29 passed`; module alone `20 passed`.
- Decision: when `stall_kill_secs` is non-zero and not above `stall_suspect_secs`, both fall back to 600/1800 (the test pins this).

### 2026-10-02 - T-020-05 (1a-4) Run to session reconcile (FR-3 AC1-4)
- Done: new `console/server/run_sync.py`: `session_view` (`:27`), pure `sync_run` (`:74`), `sweep_startup` (`:113`), fail-closed `_fail_closed` seam (`:16`). Precedence: terminal/non-chat no-op; stop request; `scheduled_retry` untouched; absent or dead-without-ended-turn = startup `interrupted/server_restart` else seam `process_lost`; alive: approval, busy/queued/no turn yet = running; last turn clean `done`, failed = seam (`process_exit` subtype = `process_lost`, else `turn_error`).
- Tests: new `console/tests/test_run_sync.py`, 39 tests: `TestSyncRunTable::test_state_for_each_row` (18 rows) plus 5 extras, `TestStartupSweep` (2), `TestTerminal` (4 params), `TestRing`, `TestStop` (2), `TestRestart`, `TestSeam` (2), `TestScope` (2), `TestApiSession`, `TestSessionView`.
- Red first: collection `ImportError: cannot import name 'run_sync'`; then 39 passed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_sync.py console/tests/test_runs.py` -> `84 passed`. Full suite -> `1557 passed in 120.20s` (1498 + 20 + 39, 0 failed).
- Gaps (todos recorded): sessions retain no stderr so the view passes `""`; no `liveness` written on `done` (FR-13 arrives in 3a-4), patch carries `end_reason`, `ended`, `last_output_at`. FR-3 AC5 (retry) is 3a-5 by plan.
- Next: T-020-06 (2a-1).

### 2026-10-02 - T-020-06 (2a-1) procs: kill_tree, tree_spawn_kwargs, clean_env (FR-5, FR-6)
- Done: `console/server/procs.py`: `tree_spawn_kwargs` (`:49`), `clean_env` (`:58`, lazy `run_config`), `kill_tree` (`:84`; nt `taskkill /T` then `/T /F` via `_taskkill`, no-window flag; POSIX `killpg` only when `getpgid(pid) == pid`, else single-process terminate/kill; OSError swallowed, `proc.wait` decides; exited process is a no-op). `CREATE_NEW_PROCESS_GROUP` spelled out (0x200).
- Tests (`console/tests/test_procs.py`, 11 new): `TestKillTree` x6 (the 5 named plus `test_nt_polite_ask_that_works_is_not_forced`), `TestTreeSpawnKwargs` x2, `TestCleanEnv` x3. Red first: 11 failed (AttributeError, functions absent).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_procs.py console/tests/test_run_config.py` -> `47 passed`. Full suite -> `1568 passed in 124.50s` (1557 + 11, 0 failed).
- Note: POSIX kill signal uses `getattr(signal, "SIGKILL", 9)` so the posix branch is provable on Windows.
- Next: T-020-07 (2a-2).

### 2026-10-02 - T-020-07 (2a-2) Wire spawn and kill sites (FR-5, FR-6, BR-11)
- Done: `agent_session.py`: `BaseSession.repo_root` + `kill_process(grace=5.0)`; `LiveSession.stop_wait_secs = 10`; both Popens pass `env=procs.clean_env(repo_root or None)` + `**procs.tree_spawn_kwargs()`; `LiveSession.stop`, `TurnSession.interrupt/stop` use `procs.kill_tree(grace=2.0)`; `build(..., repo_root="")`. `agents.py`: launch Popen env + tree kwargs; `stop_job` kills the tree outside the job lock. `agent_manager.py`: `create` and `resume` pass `repo_root=`.
- Tests (12 collected, `test_procs.py`): env+group flags for LiveSession/TurnSession/agents.launch (x nt/posix), `TestNoBareKill` (AST; `os.kill(pid, sig)` signal send in live interrupt deliberately allowed), `TestKillProcess` x3, `TestStopJob`, `TestRepoRootThreading`. Red first: 12 failed. Existing 6 `test_flag_*` spawn cases unchanged and green.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_procs.py console/tests/test_agent_resume.py console/tests/test_agent_manager_worktree.py console/tests/test_assistant.py` -> `117 passed`. Full suite -> `1580 passed in 140.97s` (1568 + 12, 0 failed).
- Behaviour note: `TurnSession.interrupt` now blocks up to the 2 s grace (was non-blocking terminate).
- Next: T-020-08 (2b-1).

### 2026-10-02 - T-020-08 (2b-1) Per-line cap, O(1) one-shot buffer accounting (FR-7 AC1, AC3)
- Done: `procs.iter_capped_lines(stream, max_chars)` + `LINE_TRUNCATED` (`procs.py:120-146`, bounded `readline(cap+1)`, remainder discarded in chunks, counts characters per CR-37); used by `LiveSession._read`, `TurnSession._read_turn` (cap via `BaseSession._line_cap()` -> `run_config.runs_cfg`) and `agents._reader_thread` (running `total_len`, recomputed only when trimming to the last 1000 lines).
- Tests (new `console/tests/test_output_caps.py`, 7): `TestLineCap` x5 (the 2 named, exact-cap, no-newline/empty, reader-loop through `_read_turn` with `max_line_bytes=200` in a tmp console.toml), `TestAgentsReader` x2 (named). Red first: 6 failed, 1 passed (`truncated` flag test pins existing behaviour; the 10k-lines test failed on the old O(n^2) sum).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_output_caps.py console/tests/test_procs.py` -> `46 passed`. Full suite -> `1587 passed in 147.39s` (1580 + 7, 0 failed).
- Next: T-020-09 (2b-2).

### 2026-10-02 - T-020-09 (2b-2) Per-turn output cap with `on_limit` seam (FR-7 AC2, BR-9)
- Done: `agent_session.py`: `BaseSession(on_limit=None)`, `_turn_chars`/`_cap_hit`, `_reset_turn_output()` called where `turn.start` is published (`send`, `_drain`), `_count_output` called from `_handle_line`; first breach publishes one `{type: notice, kind: output_cap}`, calls `on_limit(session, "output_cap", detail)` (exceptions swallowed), then `kill_process(grace=2.0)`; `build(on_limit=)`. `agent_manager.py`: `_make_on_limit(repo_root)` (finds the active chat Run, `runs.update` failed/output_cap/ended; no Run or already-terminal = no-op) passed from `create` and `resume`.
- Tests (extend `test_output_caps.py`, 10): `TestTurnCap` x7 (5 named plus drain-reset and failing-callback), `TestOnLimitHook` x3 (Run written, terminal Run untouched, create supplies `on_limit`). Red first: 8 failed.
- Unit note: the cap counts decoded characters (+1 per line), like the line cap; the config key keeps the plan's `..._bytes` name.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_output_caps.py console/tests/test_runs.py` -> `62 passed`. Full suite -> `1597 passed in 140.73s` (1587 + 10, 0 failed).
- Limit: a breach before the caller (`verb_handlers`) has created the Run finds none and only kills; the Run is then created `running` and reconcile (run_sync) catches the dead session.
- Next: T-020-10 (2b-3).

### 2026-10-02 - T-020-10 (2b-3) Lingering-after-result kill (FR-8)
- Done: `agent_session.py`: `_handle_line` now returns True when the line produced a `turn.end`; `TurnSession._read_turn` drops the per-instance `self._observe` swap for a per-reader `saw_end` and arms `_arm_linger(proc)` (threading.Timer, `linger_grace_secs`) on the first turn end; `_linger_kill(proc)` kills the captured process (never `self.proc`) via `procs.kill_tree` and publishes `{notice, kind: lingering_killed}`; the timer is cancelled when the reader ends. `LiveSession` untouched (never killed by this rule). `agents.py`: `_is_result_line`, `_linger_kill(job, proc)` (sets `job["lingering_killed"]`, appends a console line to the buffer); `_reader_thread` arms the timer on the first parsed `type == "result"` line and finalises status after the kill: a process we ended after its result is `done`, not `error`.
- Tests (new `console/tests/test_linger_kill.py`, 9): the 7 named (busy/queue one is parametrised x2) plus `test_agents_launch_exit_inside_grace_is_not_killed`. Process order caveat: the implementation was written before these tests in this task; red-ness was shown by mutation instead (arming disabled -> 4 failed, restored -> 9 passed).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_linger_kill.py console/tests/test_output_caps.py console/tests/test_procs.py` -> `65 passed`. Full suite -> `1606 passed in 111.48s` (1597 + 9, 0 failed).
- Stops here: 2c-1 (real-process test) and 2c-2 (CI edit) are a later session.

### 2026-10-02 - T-020-11 (2c-1) Real-process tree-kill proof (FR-9, NFR-3, NFR-11)
- Done: new `console/tests/test_proc_tree.py`: fake CLI = `sys.executable` script written to tmp (root -> child -> grandchild, each sleeps 30 s, pids appended to a file, `T020-TREE-<uuid>` marker in the script and argv, `CREATE_NO_WINDOW` on nt). Fixture `tree` (`:112`) force-kills every recorded pid and any spawned Popen in teardown. Docstring states the `taskkill /T` reach limit.
- Tests: `TestProcessTree::test_kill_tree_leaves_no_orphan_root_child_or_grandchild` (real `LiveSession`, `kill_process(grace=1.0)`), `::test_windows_control_plain_kill_leaves_grandchild_alive` (nt only; cleanup via `kill_tree` on a pid adapter).
- Deviation: the script is a tmp file, not a `-c` string (a child needs `__file__` to respawn itself).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_proc_tree.py` -> `2 passed in 4.15s`. Orphan check: PowerShell `Get-CimInstance Win32_Process` filtered on `T020-TRE[E]` -> 0 matches (an unbracketed pattern also matches the querying shell itself). Other python.exe in `tasklist` predate the run and are not ours.
- CR-29 measurement (script, Windows, no-window python tree): soft `taskkill /PID <root> /T` alone returns 128 ("can only be terminated forcefully"); all three processes stayed alive after 1.5 s. The `/F` fallback in `kill_tree` is required, not defensive.
- Full suite -> `1608 passed` (with 2c-2).

### 2026-10-02 - T-020-12 (2c-2) CI step for the process tests (FR-9 AC2)
- Done: `.github/workflows/verify.yml:171-181`, new `desktop`-job step after the desktop pytest step: `python -m pytest console/tests/test_proc_tree.py console/tests/test_procs.py -o addopts="" -rA` with the same `::error title=console process tests failed on ${{ matrix.os }}::$summary` block. Local edit only, not pushed; CR-19 stays open for the owner. No YAML parser: reviewed the diff for indentation against the neighbouring step.
- Evidence: the same two files locally -> `41 passed in 15.79s`. Real CI result: PENDING-CI.

### 2026-10-02 - T-020-13 (3a-1) Failure evidence on turn.end (FR-10)
- Done: `console/server/agent_normalize.py`: `_failure_evidence` (`:57`, bounds `EVIDENCE_TEXT_MAX=500`, `EVIDENCE_ERRORS_MAX=10`), spread into the `turn.end` dict in `_result`. New keys `errors`, `error`, `api_error_status` (int, not bool, else null), `stop_reason` (64); existing keys and the rate_limit notice untouched.
- Tests: new `console/tests/test_normalize_evidence.py`, 8. Red first: 6 failed (KeyError 'errors'), 2 pins passed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_normalize_evidence.py console/tests/test_session_state.py console/tests/test_assistant_reply.py console/tests/test_telemetry.py` -> `79 passed`.

### 2026-10-02 - T-020-14 (3a-2) run_failures.classify (FR-11)
- Done: new `console/server/run_failures.py`: `CLASSES`, `RETRYABLE`, `NON_RETRYABLE` (`:16-24`), `classify` (`:162`). Markers ported from Paperclip `parse.ts`; applied to terminal fields (result, error, errors) of a failed turn only; stderr joins the haystack for model/session/image/quota/transient but never auth. Not failed => class "". Refusal is structured only and counts on a clean exit. `output_cap` and `stalled` are in `CLASSES` but set by their detectors, never by `classify`. `retryable_class` = class in {quota, transient_upstream, max_turns, process_lost}.
- Tests: new `console/tests/test_run_failures.py`, 36 (28 table rows plus 8). Red first: collection ImportError.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_failures.py` -> `36 passed`. Full suite -> `1652 passed` (1608 + 8 + 36).
- Limit: `classify` has no backend argument, so "non-Claude backends map to process_lost/unclassified only" is not enforced here; the caller must pass no turn_end for them (decide in 3a-5).

### 2026-10-02 - T-020-15 (3a-3) Quota reset parsing (FR-12)
- Done: `run_failures.py`: `parse_reset(rate_limit, text, now, cfg, _zone=None)` (`:146`) with `_notice_reset` (rejected only; s/ms by 1e11) and `_prose_reset` (quota marker + `resets [at] h[:mm]am|pm [(zone)]`; `UTC`/`GMT` need no tzdata; no zone = host-local; unknown zone = ""; window `(now, now+horizon]`). `classify(..., now=None, cfg=None)` fills `retry_not_before` for quota/transient only when `now` is given. `_zone=None` resolves `zoneinfo.ZoneInfo` at call time so monkeypatching it works.
- Tests: new `console/tests/test_quota_reset.py`, 19 (5 prose fixtures x injected and x real zoneinfo, rest). The real-zone cases ran here (tzdata present for America/Chicago); they skip with a reason on a bare host.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_quota_reset.py console/tests/test_run_failures.py -rs` -> `55 passed`, no skips. Full suite -> `1671 passed in 135.00s`.
- Next: T-020-16 (3a-4), not started.

### 2026-10-02 - T-020-16 (3a-4) Run-liveness classes and evidence collector (FR-13, BR-10)
- Done: `console/server/run_failures.py` (appended): `liveness(turn, mode, evidence, ticket_state, text)`, `tool_evidence`, `PLANNING_ONLY`, `NEXT_STEPS`, `FILE_TOOLS`, `MUTATING_VERBS`. `console/server/run_sync.py`: `collect_evidence(repo_root, run, view)`, `_liveness`; the `done` patch now carries `liveness` in the same patch as the terminal state (FR-2); `session_view` carries `mode`. `console/server/agent_session.py` `_last_turn_summary` additively carries `result` (2000), `error`, `errors`, `api_error_status`, `stop_reason`, `resets_at` (the classifier and liveness need them; the ring is not read).
- Tests: new `console/tests/test_liveness.py` (`TestLivenessTable::test_each_class`, plan-mode vs default-mode, bash-only empty, eight reply fixtures, plan_only/empty never schedule retry; `TestCollectEvidence` x4; `TestDonePatchCarriesLiveness`). Red first: `NameError`/`ImportError` (functions absent).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_liveness.py console/tests/test_run_sync.py console/tests/test_run_failures.py console/tests/test_quota_reset.py` -> `160 passed`. Full suite (run together with 3a-5) -> `1737 passed in 132.17s`, 0 failed.
- Decisions: the planning-only pattern is anchored to the reply start (mid-sentence "next"/"will" in a summary is not `plan_only`); tracker items carry a date only, so they are compared by day; comments by full timestamp.
- Limits: sessions keep no stderr (view passes `""`); `output_cap` and `stalled` come only from their own detectors, never `classify`.
- Effort: estimated 3h; actual not timed (built together with 3a-5).

### 2026-10-02 - T-020-17 (3a-5) Retry table, caps, due time; real decide_failure (FR-15, FR-3 AC5)
- Done: `console/server/run_failures.py` (appended): `decide(run, failure, now, cfg)`, `_retry_delay`, `ATTEMPTS_KEPT`. Per-class and total caps, due = `max(now + delay, retry_not_before)` (BR-4), quota only with a known reset inside `quota_max_wait_secs`, attempts history (last 10); terminal `end_reason` is `retry_exhausted` or the class. `console/server/run_sync.py`: `decide_default` replaces `_fail_closed` as the default seam; it classifies only when `run["backend"] == "claude"` (other backends map to `process_lost` or `unclassified`, so the non-Claude rule lives here); unreadable clock fails closed; terminal failed patches also carry `ended` and `liveness {failed}`; a `scheduled_retry` patch carries neither.
- Tests: extended `console/tests/test_run_failures.py` (`TestRetryTable`, 24 cases) and `console/tests/test_run_sync.py` (`TestProcessLost` x2, `TestDefaultPolicy`, session-view evidence test). Red first: `ImportError`/`NameError` (decide absent).
- Change to existing tests: three `TestSyncRunTable` rows that expected `failed` for a lost process now expect `scheduled_retry` (FR-3 AC5: one retry).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_liveness.py console/tests/test_run_sync.py console/tests/test_run_failures.py console/tests/test_quota_reset.py` -> `160 passed`. Full suite -> `1737 passed in 132.17s`, 0 failed (1671 + 66).
- Next: T-020-18 (3b-1).

### 2026-10-02 - T-020-18 (3b-1) Pure watchdog evaluate (FR-14 pure ACs, BR-5)
- Done: new `console/server/run_watchdog.py`: `parse_utc`, `_silent_since`, `evaluate(run, view, now, cfg)` returning `{action, silence_secs}` (`none|suspect|kill`). Only a `running` chat Run with a watchable session has a clock; pending approval pauses it; `view["clock_floor"]` (UTC stamp, to be set by the tick when an approval ends) restarts it; fallback chain `last_output_at`, `started_utc`, Run `created`, else fail closed to `none`; `suspect` fires once (Run `liveness.state == "suspicious"` suppresses it); `stall_kill_secs == 0` never kills.
- Tests: new `console/tests/test_run_watchdog.py` (`TestEvaluate`, 10: the 7 plan-named plus clock-restart, state/executor scope, parse_utc). Process caveat: the implementation was written before the tests in this task (no red run; the tests were written against the spec ACs).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_run_config.py` -> `30 passed`. Full suite -> `1747 passed in 135.41s`, 0 failed.
- Open for 3b-2: the tick must set `clock_floor` when it sees a Run leave a pending approval, and write `liveness={state: suspicious}` on `suspect`.

### 2026-10-02 - T-020-19 (3b-2) Watchdog tick and thread (FR-14, NFR-6, NFR-7)
- Done: `console/server/run_watchdog.py`: `tick(repo_root, now, registry, approvals, startup)` (single-flight lock, `{busy: True}` for the loser; first tick runs `sweep_startup`; per-Run try/except with `errors`; sync then evaluate; suspect writes `liveness=suspicious` and one `stall_suspect` notice; kill writes `timed_out/stalled` with annotations first, then notice, audit, `kill_process(grace=2.0)`; chats with no Run are never touched, Runs with no session are skipped), `Watchdog` thread (Event wait), `reset`, `last_tick`; the tick stamps `clock_floor` when an approval ends (BR-5). `console/server/runs.py`: `list_active(repo_root, known_terminal)`. `console/server/agent_manager.py`: `start_watchdog` (lazy import, honours `watchdog_enabled`, one thread per repo), `stop_watchdog`, `shutdown_all` stops it first. `console/server/features/agents_feature.py`: one call in `apply`. `console/server/audit.py`: `run.stall_kill`, `run.retry`, `run.retry_exhausted` added to `ACTIONS` (anchored). Retry audit `run.retry_exhausted` is written when a sync patch ends `retry_exhausted`; `run.retry` is for 3b-3.
- Tests (`console/tests/test_run_watchdog.py`, 18 new): `TestTick` x13 (the 7 plan-named plus suspect-once, zero-kill config, no-session skip, API session, approval pause and restart, startup sweep), `TestListActive`, `TestThread` x4. Red first: all errored on the missing `run_watchdog.reset`.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_runs.py console/tests/test_plugins.py console/tests/test_notify_audit.py` -> `156 passed`. Full suite -> `1765 passed in 134.17s`, 0 failed.
- Note: the 100-run timing test warms up with one tick first; Windows scans just-written files on first read (about 1.5 s for 100 files here), a host effect. Steady-state tick is under 100 ms.
- Limit: `retried` is always 0 (execution is 3b-3). Stopped here as scoped.

### 2026-10-02 - T-020-20 (3b-3) Retry execution (FR-16)
- Done: `console/server/run_watchdog.py`: `CONTINUATION` :78, `_end_failed` :166, `_retry_one` :173, wired into the `tick` loop ahead of the no-session skip. Due `scheduled_retry`: live session gets `send`; dead one goes `resume` then `send`; resume `ValueError`/`FileNotFoundError` -> `failed/resume_refused` (never `create`); send `RuntimeError`/`OSError` -> `failed/retry_failed`; success -> `running`, `attempt+1`, audit `run.retry`; stop request -> `interrupted`; unreadable due time left alone.
- Tests: `TestRetryExecution` (7 functions, 9 cases) in `console/tests/test_run_watchdog.py`. Red first: 7 failed before implementation.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_agent_resume.py` -> `49 passed`. Full suite -> `1774 passed in 151.35s`, 0 failed.
- Seam: the registry passed to `tick` may offer `get/resume/send/server_port` (`agent_manager` does).
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-21 (3b-4) Escalation comment (FR-17, NFR-9)
- Done: `console/server/run_watchdog.py`: `ACTION_TABLE` (every `run_failures.CLASSES` plus `resume_refused`, `retry_exhausted`, `retry_failed`), `_scrub` (credential-named env values redacted), `_comment_text` (detail <=300), `escalate(repo_root, run)`; called from `_apply`, so every tick write that ends a Run `failed`/`timed_out` (sync failure, stall kill, resume refused, retry failed) posts. Idempotent by the `[run <id>]` marker on a `run-watchdog` comment (no Run field, CR-26); goes through `verb_handlers.ticket_comment` (audit + bus). Unknown ticket: stderr note, no comment file created.
- Tests: `TestEscalation` (8) in `console/tests/test_run_watchdog.py`. Red first: 8 failed before implementation.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_ready_claim_comment_verbs.py` -> `68 passed`. Full suite -> `1782 passed in 114.74s`, 0 failed.
- Limit: a Run that ends failed outside the tick (nothing does today) would not be escalated; terminal Runs are never re-listed.
- Effort: estimated 2h; actual not timed.

### 2026-10-02 - T-020-22 (3c-1) Verbs run-watch and run-retry (FR-18)
- Done: `console/config/verbs.toml` rows `run-watch`, `run-retry` (both `needs_confirm`) after `run-show`; `console/server/verb_handlers.py` `run_watch` (same `run_watchdog.tick` as the thread; `{busy}` when it is in flight) and `run_retry` (one-liner); `console/server/run_watchdog.py` `manual_retry` (lock-guarded check-and-create; refuses unknown, non-ended and already-retried-while-active; new Run via `runs.create(retry_of, retry_due)`, old record never written); `console/server/runs.py` `create` gained `retry_of`/`retry_due` (additive; returns defaults-filled record).
- Tests: new `console/tests/test_run_verbs.py` (11 cases: `TestRunWatch` x2, `TestRunRetry` incl. byte-identical old file for 3 ended states and a tick that executes the created Run, `TestOneApi` MCP tools/list + HTTP route pattern). Red first: 10 failed (unknown verb).
- Evidence: module set (test_run_verbs, test_verbs, test_mcp, test_mcp_http, test_plugins, test_runs, test_run_watchdog) -> `198 passed`. Full suite -> `1793 passed in 118.47s`, 0 failed (1 unrelated warning: tomlio concurrent-writer thread PermissionError, logged as a T-020 todo).
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-23 (4a-1) claimed_at UTC + claimed_run (FR-19, CR-34)
- Done: `console/server/tickets.py` `claimed_run` in `create`, `load` default `""`, `parse_claimed_at` :222, `set_claim(..., claimed_run=None)` (None keeps the link on a same-holder refresh, release clears); `console/server/backends/{base,vault_backend}.py` `claim(..., claimed_run="", now=None)` stamps `%Y-%m-%dT%H:%M:%SZ` UTC; `console/server/verb_handlers.py` `ticket_claim(..., run="")` (unknown run refused by name; no `run` links the sole ACTIVE chat Run on the ticket, zero or two link nothing); `console/server/stop_hook.py` `_LOCAL_TZ` seam + `_updated_floor` :65: `ticket.updated` is a LOCAL date, so a full-timestamp claim is converted to its local date before comparing (comments compare UTC-to-UTC; date-only legacy claims unchanged). Chosen over changing `updated` to UTC because `updated` is stamped in many places outside this task.
- Tests: new `console/tests/test_claims.py` (13: UTC regex, injected clock, parse x3, older toml, explicit/auto/zero-or-two/other-ticket/unknown/release/refresh) and `TestStopHookWithUtcClaim` (6 cases incl. UTC+5, UTC-8, UTC midnight, next-local-day move, UTC comment) in `test_stop_hook.py`. Red first: 18 failed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_claims.py console/tests/test_stop_hook.py console/tests/test_tickets.py console/tests/test_vault_backend.py console/tests/test_backends.py console/tests/test_ready_claim_comment_verbs.py` -> `128 passed`. Full suite -> `1812 passed in 168.22s`, 0 failed. Existing stop-hook and claim tests unchanged.
- Limit: a same-local-day move after a claim is still not seen as an update (as before: `updated` is date-only).
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-24 (4a-2) Stale-claim rule (FR-20, BR-6, BR-7)
- Done: `console/server/tickets.py` `evaluate_claim` (pure) and `claim_status` (fail-closed wrapper, any exception -> `held/unknown`); imports `run_config`, `runs`.
- Tests: new `console/tests/test_claim_status.py` (6: `test_every_branch_with_injected_clock`, `test_unlinked_branches`, `test_planner_done_builder_live_is_stale_run_dead`, `test_scheduled_retry_counts_as_active`, `test_config_from_claims_section_invalid_falls_back_with_one_warning`, `test_read_error_returns_held_unknown`). Red first: 6 failed (no `claim_status`).
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_claim_status.py console/tests/test_tickets.py console/tests/test_run_config.py` -> `68 passed`. Full suite -> `1818 passed in 138.28s`, 0 failed.
- Note: unlinked branch treats ANY ACTIVE Run on the ticket (not only chat) as protecting the claim (fail-closed, BR-6); held bases `run_grace`/`fresh`/`unknown` added.
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-25 (4a-3) Adopt a stale claim; ready lists it (FR-21, NFR-6, NFR-8)
- Done: `console/server/tickets.py` `set_claim(..., adopt_stale, now, info)` (re-evaluates via `_verdict_now` inside the `atomic_update` lock; conflict message names holder, basis, `claim-release`); `claim_status` refactored onto `_verdict_now`; `backends/vault_backend.py` `claim` adopts and `ready` reads Runs once and lists stale claims with a `claim` object (held omitted); `backends/base.py` signature; `verb_handlers.py` `ticket_claim` records `ticket.claim.adopt` (previous holder/at/run, basis, age) and comments as the adopter; `audit.py` `ACTIONS` + `ticket.claim.adopt`.
- Tests: new `console/tests/test_claim_adopt.py` (9: TestAdopt x7 incl. 20-round two-thread race, TestReady x2). Red first: 8 failed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_claim_adopt.py console/tests/test_ready_claim_comment_verbs.py console/tests/test_vault_backend.py console/tests/test_tickets.py console/tests/test_notify_audit.py console/tests/test_claim_status.py console/tests/test_claims.py` -> `167 passed`. Race test run as 20 separate pytest invocations (each 20 rounds): 20 passed, 0 failed. Full suite -> `1827 passed in 152.65s`, 0 failed.
- Note: an adopted claim writes only the `ticket.claim.adopt` row (not also `ticket.claim`). Unlinked claim with ANY active Run on the ticket stays held (so a stale claim must be linked to a dead Run or time out).
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-26 (4a-4) claim-release verb with audited force path (FR-22, BR-13)
- Done: `console/server/tickets.py` `release_claim` (under `atomic_update`; holder, stale or forced; refusal returns an outcome dict); `console/server/verb_handlers.py` `_truthy`, `ticket_claim_release` (audits `ticket.claim.release` / `ticket.claim.force_release` with previous holder/at/run, basis, caller, reason; comment + bus on force); `console/config/verbs.toml` row `claim-release` (`needs_ticket`, `needs_confirm`) after `claim`; `console/server/audit.py` `ACTIONS` + both actions.
- Tests: new `console/tests/test_claim_release.py` (7 functions, 9 cases: holder release, non-holder refused, stale by third, force with empty/short/whitespace reason x3, force success, missing agent/unclaimed, CLI+MCP list+needs_confirm). Red first: 9 failed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_claim_release.py console/tests/test_verbs.py console/tests/test_mcp.py console/tests/test_cli_json.py` -> `82 passed`. Full suite -> `1836 passed in 148.28s`, 0 failed.
- Note: a refused attempt is audited too (outcome `error: ...`); unclaimed ticket returns `ok:true, released:false`. Force with a short reason is refused even when the caller would not need force.
- Effort: estimated 2h; actual not timed.

### 2026-10-02 - T-020-27 (4b-1) review-round verb and counter (FR-24, BR-8)
- Done: `console/server/tickets.py` `review_rounds`/`review_escalated` in `create` and `load` defaults, `REVIEW_OUTCOMES`, `record_review` (under `atomic_update`; not in `EDITABLE`); `console/config/verbs.toml` row `review-round` (`needs_ticket`, `needs_confirm`); `console/server/verb_handlers.py` `ticket_review_round` (threshold from `run_config.review_cfg`; on the single escalation transition, outside the lock, one critical question via `tracker_add(type="review", priority="critical", raised_by="review-loop")` plus a comment; no lane move; every call and refusal audited with the caller) and `tracker_add` gained `raised_by`; `console/server/audit.py` `ticket.review`.
- Tests: new `console/tests/test_review_round.py` (13: TestReviewRound x12 incl. escalation, fourth refused, approved/interleaved, human_decision, older toml, config 5 and invalid, audit, refused audit, unknown outcome, 6-thread race, verb gates; TestTrackerAdd x1). Red first: 12 failed, 1 passed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_review_round.py console/tests/test_tickets.py console/tests/test_mutation_verbs.py console/tests/test_trackers.py console/tests/test_ticket_create_collapse.py` -> `100 passed`. Full suite -> `1849 passed in 1178.41s` (0 failed; wall time was about 8x the usual ~150 s, a host effect - the new tests run in under 7 s together).
- Effort: estimated 3h; actual not timed.

### 2026-10-02 - T-020-28 (4b-2) Context digest shows claim, review and run facts (FR-23)
- Done: `console/server/context.py` `run_facts`; `build` adds always-present keys `claim` (the `claim_status` dict), `review` (`rounds`, `escalated`), `runs` (`total`, `active`, `failed`, `latest{id,state,role,failure_class}`); `format_markdown` prints one `**Claim**`/`**Review**`/`**Runs**` line each only when non-empty (reads with `.get`, so a plain ticket renders as before).
- Tests: `TestClaimReviewRuns` (3) in `console/tests/test_context.py` (three lines + JSON keys; plain ticket identical and neutral keys; escalated line). Red first: 3 failed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_context.py console/tests/test_cli_json.py console/tests/test_mcp.py` -> `64 passed`. Full suite -> `1852 passed in 103.71s`, 0 failed.
- Effort: estimated 2h; actual not timed.

### 2026-10-02 - T-020-29 (4b-3) Verifier and fixer protocols use the counter (FR-25)
- Done: `.claude/agents/verifier.md` step 1 (reads `review.escalated`) and step 10 (clean -> `review-round outcome=approved` then `close-work`; unmet -> `review-round outcome=changes_requested agent=verifier` before routing to the fixer; stop and surface on `escalate`); `.claude/agents/fixer.md` step 1 (stop when `review.escalated`, no `human_decision` prompt). Output contract blocks, frontmatter and roster untouched; no new agent or skill file.
- Tests: new `console/tests/test_agent_protocol_text.py` (3: `test_verifier_and_fixer_mention_review_round_and_escalated_stop_rule`, `test_output_contract_blocks_intact`, `test_no_new_agent_or_skill_files` - 7 agent files, 39 skill dirs with SKILL.md). Red first: 2 failed.
- Evidence: `python -m pytest -o addopts="" -q console/tests/test_agent_protocol_text.py console/tests/test_harness_lint.py` -> `28 passed`. `python console/kanban.py harness lint` -> `39 skills, 7 agents | 0 error(s), 0 warning(s)`. Full suite -> `1855 passed in 113.22s`, 0 failed.
- Effort: estimated 1h; actual not timed.

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-decision-log]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
