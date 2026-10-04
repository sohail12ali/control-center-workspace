---
ticket: "T-020"
artifact: implementation-plan
---

# Implementation Plan: T-020

Master plan synthesising [[T-020-requirements]] (frozen, 25 FR / 11 NFR / 13 BR), [[T-020-plan]], [[T-020-components]] and [[T-020-task-breakdown]]. This file adds per-task file lists, named tests and verification commands. Task effort totals equal the breakdown's: 75.5h (73.5h dev + 2h verify).

## Ticket summary

Make a delegated chat Run survive real failures: a Run lifecycle that actually reaches terminal states, tree-kill and output hygiene for every agent child (Windows first), a failure classifier with quota reset parsing, a stall watchdog, a capped retry table, stale-claim adoption and release with audit, and a 3-round review-loop cap. Console server only, stdlib Python, no UI, no new skills or agents.

## Rules every task follows

1. **Test first.** Write the named tests, watch them fail for the stated reason, then implement. A task is done only when its tests pass, its touched-module tests pass, and the full suite shows no new failure.
2. **Commands** (repo root, bare `pytest` prints only dots here): module run `python -m pytest -o addopts="" -q console/tests/<file>.py`; full suite `python -m pytest -o addopts="" -q` (baseline 1445 collected, 1442 passed, 3 failed; 1445/0 after 0a-1; each task adds its own count).
3. **Fakes only** (NFR-4): no `claude`/`cursor-agent` spawn, no network, injectable clocks, no test sleep over 2 s. The only real process is `sys.executable` in task 2c-1.
4. **Shared files:** tasks marked [SHARED] run strictly in the listed order. Never edit a shared file for a later task early.
5. **Config files are never written by code** (BR-12). `verbs.toml` rows are hand-edited source, explicitly required by FR-18/22/24 (CR-27). Never touch `agents.toml`, `console.toml`, `schedules.toml`.
6. **Evidence:** after each task run `progress-tracker` with the pytest line and file:line (memory: delegated builds have mis-reported; verify from the tree and the count, not the subagent's status).

## Shared-file collision map

| File | Tasks, in required order |
|------|--------------------------|
| `console/server/agent_session.py` | 1a-2, 2a-2, 2b-1, 2b-2, 2b-3 |
| `console/server/agents.py` | 2a-2, 2b-1, 2b-3 |
| `console/server/agent_manager.py` | 2a-2, 2b-2, 3b-2 |
| `console/server/procs.py` | 2a-1, 2b-1 |
| `console/server/run_sync.py` | 1a-4, 3a-4, 3a-5 (2b-2 only imports) |
| `console/server/run_failures.py` | 3a-2, 3a-3, 3a-4, 3a-5 |
| `console/server/run_watchdog.py` | 3b-1, 3b-2, 3b-3, 3b-4 |
| `console/server/tickets.py` | 4a-1, 4a-2, 4a-3, 4b-1 |
| `console/server/verb_handlers.py` | 3c-1, 4a-1, 4a-3, 4a-4, 4b-1 |
| `console/config/verbs.toml` | 3c-1, 4a-4, 4b-1 |
| `console/server/audit.py` (`ACTIONS` :44) | 3b-2, 4a-3, 4a-4, 4b-1 |
| `console/server/backends/{base,vault_backend}.py` | 4a-1, 4a-3 |

---

## Phase 0: Baseline green

Makes the suite 1445/0 before any behaviour changes, so every later "no new failure" check is meaningful.

### Slice 0a
**0a-1 (T-020-01)** · FR-19 AC3 · 1h · no dependencies
- Files: `console/tests/test_stop_hook.py` only.
- Change: helper `_freeze_tickets_date(monkeypatch, y, m, d)` using the `_FrozenDate` subclass pattern at `test_stop_hook.py:62-75`; apply to `test_claim_with_no_update_is_stale` (:50), `TestCliOneApi::test_json_reports_stale_claims` (:100), `::test_plain_mode_prints_a_reminder_line` (:108) and `test_claim_then_comment_is_not_stale` (:56).
- Tests added: `TestDateIndependence::test_stale_claim_semantics_hold_on_any_calendar_date` (parametrised over 2026-09-16, 2027-03-01, 2031-12-31: claim with no update is reported, claim then comment is not).
- Verify: `python -m pytest -o addopts="" -q console/tests/test_stop_hook.py` then full suite; expect 0 failed. Record the pre-change 1445/1442/3 in progress.md.
- Done when: the 3 baseline failures pass without production code changes.

---

## Phase 1: Run lifecycle foundation

Without this nothing else has a state to act on: `runs.set_state` has no caller outside tests (`runs.py:107`).

### Slice 1a

**1a-1 (T-020-02)** · FR-1, FR-2, NFR-8 · 3h · depends: none
- Files: `console/server/runs.py`; tests in `console/tests/test_runs.py` (existing `TestRunStore` stays green).
- Change: `STATES` (:17) plus `timed_out`, `scheduled_retry`; `TERMINAL`, `ACTIVE`; `_with_defaults(rec)` applied in `get` (:82) and `list_runs` (:90); `update(repo_root, run_id, **fields)` under `tomlio._acquire_lock`/`_release_lock` on `<run>.json.lock`, field whitelist, `failure_detail` capped 500 with marker, `attempts` last 10, terminal refusal; `set_state` (:107) delegates to `update`; `find_active_chat_run(repo_root, chat_id)`; `_write` retries `os.replace` on `PermissionError` (Windows reader holding the file, CR-28).
- Tests added: `TestRunStates::test_states_are_old_six_plus_two_and_partitioned`, `::test_done_to_running_raises_and_file_unchanged`, `::test_existing_running_record_loads_and_lists_unchanged`; `TestRunDefaults::test_pre_t020_record_returns_every_new_key_with_default`; `TestRunUpdate::test_eight_threads_no_lost_update` (parametrised 20 rounds, NFR-8), `::test_terminal_with_annotations_one_write_then_refused_byte_identical`, `::test_failure_detail_truncated_with_marker`, `::test_unknown_field_refused`, `::test_reader_hammering_get_never_breaks_writer`, `::test_find_active_chat_run_ignores_terminal_and_other_executors`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_runs.py console/tests/test_run_inspector_data.py console/tests/test_ui_endpoints.py`.
- Done when: FR-1 and FR-2 checklists pass; `list_runs` complexity unchanged (still one file read per Run).

**1a-2 (T-020-03)** · FR-4 · 3h · depends: none (first edit of the shared session file) [SHARED:agent_session.py]
- Files: `console/server/agent_session.py`, `console/server/agent_approvals.py`; new `console/tests/test_session_state.py`.
- Change: module `_utc_now()` (UTC `...Z`, patchable; do not reuse local-naive `_now()` at :58, CR-24); in `_handle_line` (:255) stamp `last_output_at` and `_last_output_mono` before JSON parsing; `started_utc` set in `LiveSession.start`/`TurnSession.start`; `_observe` (:280) maintains `last_turn` = `{turn_end, rate_limit, tools}` (tools = bounded name counter from `tool.start`, CR-22), `turn_count`; public `stop_requested` property over `_stopping`; `snapshot()` (:162) exposes `last_output_at`, `turn_count`, `started_utc`, bounded `last_turn` summary. `Approvals.pending_for(chat)` (read-only, under `_lock`).
- Tests added: `TestOutputTimestamp::test_injected_clock_sets_last_output_at_and_snapshot`, `::test_no_output_is_empty_string_not_now`, `::test_non_json_line_counts_as_output`, `::test_ten_thousand_lines_under_two_seconds`; `TestLastTurn::test_survives_ring_overflow_by_ring_max_plus_one`, `::test_carries_last_rate_limit_notice_of_that_turn`, `::test_counts_tool_starts_for_the_turn`, `::test_turn_count_increments`; `TestPendingFor::test_lists_while_parked_empty_after_decide_or_forget`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_session_state.py console/tests/test_procs.py console/tests/test_api_session.py console/tests/test_assistant.py`.
- Done when: FR-4 checklist passes; `ApiSession` (subclass at `agent_api_session.py:72`) still constructs and runs its tests.

**1a-3 (T-020-04)** · NFR-10 and the config ACs of FR-6/14/15/20/24 · 2h · depends: none
- Files: new `console/server/run_config.py`; new `console/tests/test_run_config.py`.
- Change: `runs_cfg`, `retry_cfg`, `claims_cfg`, `review_cfg` over `boards.load_console_config(repo_root).get(section)`; defaults from decision a5 (suspect 600, kill 1800, tick 15, TTL 28800, dead-grace 60, delays 30/120, quota 2 retries, max-turns 2 at 1 s, process-lost 1 at 10 s, total 3, line cap 1 MiB, turn cap 64 MiB, linger 5, horizon 8 d, quota wait 21600, rounds 3, `env_strip` default 11 names, `watchdog_enabled` true); `[runs.retry]` nested via `tomlio` dotted tables; invalid value falls back with one stderr warning per (section, key, value) through `_warned`, `reset_warnings()` for tests.
- Tests added: `test_defaults_when_sections_absent`, `test_user_values_override`, `test_non_numeric_falls_back_with_exactly_one_warning`, `test_same_bad_value_warns_once_across_calls`, `test_stall_kill_not_above_suspect_rejected_defaults_used`, `test_stall_kill_zero_is_valid_flag_only`, `test_env_strip_non_list_falls_back`, `test_retry_table_nested_override`, `test_max_total_retries_zero_valid`, `test_review_max_rounds_zero_or_non_int_falls_back_to_3`, `test_claims_ttl_zero_disables_ttl`. Fixtures write extra sections into the `repo` fixture's `console.toml` and call `boards._console_cache.clear()`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_config.py console/tests/test_boards.py`.
- Done when: no code path writes any config file (grep `run_config.py` for `open(`/`dump`, expect none).

**1a-4 (T-020-05)** · FR-3 AC1-AC4 · 3h · depends: 1a-1, 1a-2 [SHARED:run_sync.py]
- Files: new `console/server/run_sync.py`; new `console/tests/test_run_sync.py`.
- Change: `session_view(session, pending_approvals)` from attributes only (`alive`, `busy`, queued depth via `snapshot()`, `last_turn`, `turn_count`, `last_output_at`, `stop_requested`, `started_utc`, `watchable = not backend.is_api`, `agent_api_session`'s transport per `agent_backends.py:358`); pure `sync_run(run, view, now, *, startup=False, decide_failure=_fail_closed)` returning a patch (empty for terminal, non-chat executor, or `scheduled_retry` unless stop requested, CR-23); precedence: terminal no-op, `stop_requested` interrupted/stopped, absent session (startup interrupted/process_lost; running server `decide_failure` with process_lost), pending approval `needs-approval`, busy or queued `running`, clean last turn `done` with liveness written in the same patch, failed last turn `decide_failure`; `sweep_startup(repo_root, registry, approvals, now)`. `_fail_closed` returns `failed/unclassified` and is replaced by the real policy in 3a-5 (CR-20).
- Tests added: `TestSyncRunTable::test_state_for_each_row` (parametrised over alive/dead/absent, busy, pending approval, last turn ok/error/none, queue, startup vs running), `TestStartupSweep::test_live_kept_dead_and_absent_interrupted_with_ended`, `TestTerminal::test_terminal_run_never_changed_even_after_another_turn`, `TestRing::test_overflowed_ring_still_yields_state_from_last_turn`, `TestStop::test_stop_requested_beats_scheduled_retry`, `TestRestart::test_scheduled_retry_with_absent_session_is_untouched_at_startup`, `TestSeam::test_failure_rows_call_decide_failure_with_turn_exit_and_stderr`, `TestScope::test_non_chat_executor_untouched`, `TestApiSession::test_api_session_is_reconciled_but_marked_unwatchable`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_sync.py console/tests/test_runs.py`; then full suite (phase 1 boundary, expect 0 failed).
- Done when: sync_run is pure (no filesystem, no clock reads; asserted by calling with `repo_root`-less fakes).

---

## Phase 2: Process hygiene

Stands alone from the Run logic: protects the machine for every chat (BR-9). Windows first; every POSIX branch proven by monkeypatching `procs.os.name` (existing pattern, `test_procs.py:88-104`).

### Slice 2a: kill, env, spawn sites

**2a-1 (T-020-06)** · FR-5, FR-6 · 3h · depends: 1a-3 [SHARED:procs.py]
- Files: `console/server/procs.py`; extend `console/tests/test_procs.py`.
- Change: `kill_tree(proc, grace=5.0)`: return at once if `proc.poll() is not None`; `nt`: `subprocess.run(["taskkill","/PID",n,"/T"], creationflags=CREATE_NO_WINDOW, stdout/stderr DEVNULL, check=False)`, `proc.wait(grace)`, then `/T /F`, then `proc.wait`; POSIX: `killpg` only when `os.getpgid(pid) == pid` (child leads its own group, BR-11), TERM, wait, KILL, otherwise `terminate`/`kill` on the single process; every `OSError`/`FileNotFoundError` swallowed, `proc.wait` decides. `tree_spawn_kwargs()`: POSIX `{"start_new_session": True}`, `nt` `{"creationflags": CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW}`. `clean_env(repo_root=None)`: `os.environ` minus `runs_cfg["env_strip"]`, `run_config` imported lazily. Port precedent: `desktop/sidecar.py:208-245`.
- Tests added (`test_procs.py`): `TestKillTree::test_nt_issues_taskkill_T_then_T_F_after_grace_with_no_window_flag`, `::test_posix_signals_term_then_kill_on_own_group_never_getpgrp`, `::test_posix_never_signals_a_group_it_does_not_lead`, `::test_already_exited_process_is_a_no_op`, `::test_taskkill_missing_does_not_raise`; `TestTreeSpawnKwargs::test_nt_flags`, `::test_posix_new_session`; `TestCleanEnv::test_deny_list_removed_and_auth_vars_kept`, `::test_env_strip_override_from_config`, `::test_non_list_env_strip_falls_back_with_one_warning`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_procs.py console/tests/test_run_config.py`.

**2a-2 (T-020-07)** · FR-5, FR-6, BR-11 · 3h · depends: 2a-1 [SHARED:agent_session.py, agents.py, agent_manager.py]
- Files: `console/server/agent_session.py` (Popen at :410 and :548; `LiveSession.stop` :476-492; `TurnSession.interrupt` :600, `.stop` :612), `console/server/agents.py` (Popen :243; `stop_job` :339), `console/server/agent_manager.py` (`create` :144 and `resume` :315 pass `repo_root=` to `agent_session.build`); extend `console/tests/test_procs.py`.
- Change: every spawn passes `env=procs.clean_env(repo_root)` and `**procs.tree_spawn_kwargs()`; `BaseSession.__init__` and `build()` (:629) gain keyword `repo_root=""`; new `BaseSession.kill_process(grace=5.0)` (calls `procs.kill_tree` on the current process, does not set `_stopping`); `LiveSession.stop_wait_secs = 10` class attribute replaces the literal at :490; stop and interrupt use `grace=2.0` (CR-29).
- Tests added: `TestLiveSessionStart::test_env_excludes_deny_list_and_group_flags_on_nt_and_posix`, `TestTurnSessionDeliver::test_env_and_group_flags`, `TestAgentsLaunch::test_env_and_group_flags`, `TestNoBareKill::test_no_bare_proc_kill_or_terminate_in_session_or_agents` (AST walk), `TestKillProcess::test_kill_process_calls_kill_tree_and_leaves_stopping_false`, `TestStopJob::test_stop_job_uses_kill_tree`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_procs.py console/tests/test_agent_resume.py console/tests/test_agent_manager_worktree.py console/tests/test_assistant.py`.
- Done when: the six existing `test_flag_*` cases for these spawn sites (`TestLiveSessionStart`, `TestTurnSessionDeliver`, `TestAgentsLaunch`, `test_procs.py:123-183`) are unchanged and green.

### Slice 2b: caps and linger

**2b-1 (T-020-08)** · FR-7 AC1, AC3 · 2h · depends: 2a-2 [SHARED:agent_session.py, agents.py, procs.py]
- Files: `console/server/procs.py` (`iter_capped_lines(stream, max_chars)`), `console/server/agent_session.py` (`LiveSession._read` :498, `TurnSession._read_turn` :576), `console/server/agents.py` (`_reader_thread` :180-196); new `console/tests/test_output_caps.py`.
- Change: bounded `readline(limit)` loop: an over-long line yields one truncated line ending in a marker and the remainder is read and discarded in cap-sized chunks; `_reader_thread` keeps a running character count instead of `sum(len(x))` per line, still sets `truncated` and keeps the last 1000 lines. Caps count decoded characters in text-mode pipes (CR-37, stated in the docstring).
- Tests added: `TestLineCap::test_three_mib_line_becomes_one_truncated_event_and_next_line_parses`, `::test_per_line_memory_bounded_by_cap_plus_marker` (stream fake records every `readline` size), `TestAgentsReader::test_ten_thousand_short_lines_under_one_second`, `::test_truncated_flag_set_past_200k_chars`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_output_caps.py console/tests/test_procs.py`.

**2b-2 (T-020-09)** · FR-7 AC2, BR-9 · 3h · depends: 1a-1, 2b-1 [SHARED:agent_session.py, agent_manager.py]
- Files: `console/server/agent_session.py`, `console/server/agent_manager.py`; extend `console/tests/test_output_caps.py`.
- Change: per-turn stdout byte counter reset where `turn.start` is published (`send` :220, `_drain` :246); on breach publish one `{type: notice, kind: output_cap}`, call keyword `on_limit(session, failure_class, detail)` first, then `kill_process()`; `agent_manager.create`/`resume` supply `on_limit` that calls `runs.find_active_chat_run(repo_root, sess.id)` then `runs.update(state="failed", failure_class="output_cap", end_reason="output_cap", ended=...)`; no Run means no callback work (CR-21).
- Tests added: `TestTurnCap::test_breach_publishes_one_notice_and_one_kill`, `::test_counter_resets_at_turn_start_two_turns_no_breach`, `::test_run_is_terminal_before_kill_is_called` (order recorder), `::test_chat_without_run_is_still_killed_without_error`, `::test_second_breach_after_kill_is_ignored`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_output_caps.py console/tests/test_runs.py`.

**2b-3 (T-020-10)** · FR-8 · 3h · depends: 2b-1, 2b-2 [SHARED:agent_session.py, agents.py]
- Files: `console/server/agent_session.py` (`TurnSession._read_turn` :562-598), `console/server/agents.py` (`_reader_thread`); new `console/tests/test_linger_kill.py`.
- Change: after the result event (`turn.end` for `TurnSession`; a parsed JSON line with `type == "result"` for `agents.launch`) start a timer for `linger_grace_secs`; if the captured process is still alive call `procs.kill_tree(captured)` and publish `lingering_killed`; the reader then ends through EOF and `finally`; replace the per-instance `self._observe = observe` swap by a per-reader `saw_end` holder so an overlapping next-turn reader cannot be clobbered (CR-31); `agents` job status is finalised after the kill.
- Tests added: `TestLinger::test_result_then_sleep_killed_within_grace_plus_one_second` (grace 0.2 s), `::test_exit_inside_grace_not_killed_no_notice`, `::test_live_session_alive_after_result_never_killed`, `::test_busy_false_and_queue_drains_when_process_lingers`, `::test_kill_targets_the_old_process_not_the_next_turns`, `::test_overlapping_readers_do_not_clobber_each_other`, `::test_agents_launch_result_then_linger_killed_and_status_finalised`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_linger_kill.py console/tests/test_output_caps.py console/tests/test_procs.py`.

### Slice 2c: real-process proof and CI

**2c-1 (T-020-11)** · FR-9, NFR-3, NFR-11 · 3h · depends: 2a-2
- Files: new `console/tests/test_proc_tree.py` only (fake CLI is an inline `sys.executable -c` string).
- Change: fake CLI starts a child that starts a grandchild (both spawned with `CREATE_NO_WINDOW` on `nt` so no console flashes), each sleeping at most 60 s, writing the three pids to a temp file named in the script and carrying a unique marker `T020-TREE-<uuid>` in the command line; test builds a real `agent_session.LiveSession` with a fake backend whose `session_argv` returns that command, waits up to 5 s for the pid file, calls `sess.kill_process(grace=1.0)`, polls up to 10 s that all three pids are gone (Windows: `ctypes.windll.kernel32.OpenProcess` + `GetExitCodeProcess` != 259; POSIX: `os.kill(pid, 0)` raises). Windows-only control test (`pytest.mark.skipif(os.name != "nt")`, builtin mark because `pytest.ini` has `--strict-markers`): plain `proc.kill()` leaves the grandchild alive; cleanup uses `procs.kill_tree` on a minimal pid adapter for the surviving live child, then a fixture finalizer force-kills every recorded pid (`taskkill /PID n /T /F` or `os.kill`) (CR-30). The module docstring and the reach-limit note state: a grandchild whose parent exited before the kill is out of reach of `taskkill /T`.
- No-orphan-on-abort safety: bounded sleeps; finalizer runs in `finally`/fixture teardown; marker lets a human find leftovers: `Get-CimInstance Win32_Process | Where-Object CommandLine -match 'T020-TREE'` must return nothing.
- Tests added: `TestProcessTree::test_kill_tree_leaves_no_orphan_root_child_or_grandchild`, `::test_windows_control_plain_kill_leaves_grandchild_alive` (skipped off `nt`).
- Verify: `python -m pytest -o addopts="" -q console/tests/test_proc_tree.py` (budget 15 s); then the PowerShell marker check above; also record whether the soft `taskkill /T` alone ends a no-window python tree (CR-29 measurement) in progress.md.

**2c-2 (T-020-12)** · FR-9 AC2, NFR-3 · 1h · depends: 2c-1
- Files: `.github/workflows/verify.yml` only (outside `console/`; needs owner acknowledgement, CR-19).
- Change: add a step to the `desktop` job (matrix windows/ubuntu/macos, :90-169) after the desktop pytest step: `python -m pytest console/tests/test_proc_tree.py console/tests/test_procs.py -o addopts="" -rA`, with the same `::error title=console process tests failed on ${{ matrix.os }}::$summary` annotation block (memory: Actions logs need sign-in, annotations do not).
- Tests added: none (CI config). Verify: there is no stdlib YAML parser, so review `git diff .github/workflows/verify.yml` for indentation against the neighbouring steps and run the same two test files locally; the real result is known only after a push and stays `PENDING-CI` in verification until then.

**Phase 2 boundary:** full suite `python -m pytest -o addopts="" -q` has 0 failed; `grep -nE "\.(kill|terminate)\(\)" console/server/agent_session.py console/server/agents.py` shows none outside `procs.py`.

---

## Phase 3: Classify, watch, retry

Pure modules first (cheap to test, no I/O), then the policy that joins them, then the thread and verbs. The watchdog thread is the first place the Run store and sessions meet live.

### Slice 3a: pure classification

**3a-1 (T-020-13)** · FR-10 · 1.5h · depends: none
- Files: `console/server/agent_normalize.py` (`_result` :300-324); new `console/tests/test_normalize_evidence.py`.
- Change: `turn.end` gains `errors` (list, each at most 500 chars, at most 10), `error` (500), `api_error_status` (int or null), `stop_reason` (64); existing keys and the `rate_limit` notice shape (:136-151) untouched. Fixtures are inline (the real "Failed to authenticate" sample is copied into the test; `console/.cache` is gitignored and never read).
- Tests added: `test_result_with_errors_status_and_stop_reason`, `test_result_without_fields_yields_empty_defaults`, `test_errors_bounded_ten_by_five_hundred`, `test_existing_turn_end_keys_unchanged`, `test_rate_limit_notice_shape_unchanged`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_normalize_evidence.py console/tests/test_session_state.py console/tests/test_assistant_reply.py console/tests/test_telemetry.py`.

**3a-2 (T-020-14)** · FR-11 · 3h · depends: 3a-1 [SHARED:run_failures.py 1/4]
- Files: new `console/server/run_failures.py`; new `console/tests/test_run_failures.py`.
- Change: `classify(turn_end, rate_limit, exit_code, stderr_tail)` returning `{class, retryable_class, detail, retry_not_before}`; precedence `auth_required`, `model_not_found`, `max_turns`, `unknown_session`, `poisoned_session`, `image_error`, `refusal` (structured fields only), `quota`, `transient_upstream` (only when not quota), `process_lost`, `output_cap`, `stalled`, `unclassified`; failed when `is_error` or `subtype != success` or non-zero exit; auth markers match terminal result fields only, never assistant prose; synthetic `subtype=process_exit` with exit 0 is neither success nor failure (liveness `empty`); module constants `CLASSES`, `NON_RETRYABLE`.
- Tests added: `TestClassifyTable::test_twenty_plus_rows` (parametrised, one per class, precedence conflicts, the real auth sample, "unauthorized" in a successful reply), `::test_success_subtype_with_is_error_is_auth_required`, `::test_rate_limit_words_in_successful_turn_not_failed`, `::test_unknown_text_on_failed_turn_is_unclassified_never_transient`, `::test_process_exit_zero_is_not_a_failure`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_failures.py`.

**3a-3 (T-020-15)** · FR-12 · 3h · depends: 3a-2 [SHARED:run_failures.py 2/4]
- Files: `console/server/run_failures.py`; new `console/tests/test_quota_reset.py`.
- Change: `parse_reset(rate_limit, text, now, cfg, _zone=ZoneInfo)`: (a) notice `resets_at` when status is `rejected`, epoch seconds or milliseconds by magnitude (above 1e11 means ms); (b) prose `resets [at] <h[:mm]am|pm> [(<zone>)]` after a quota marker (Paperclip pattern, `packages/adapters/claude-local/src/server/parse.ts`, fixtures `parse.test.ts:173,193,205,470`), next occurrence of that wall-clock time in the zone, `UTC`/`GMT` without a tz database, no zone means host-local; accepted only inside `(now, now + quota_parse_horizon_secs]`, else `""`; zone seam `_zone` so tests inject resolvers.
- Tests added: `test_paperclip_fixtures_with_fixed_now` (four prose fixtures incl. rollover to tomorrow), `test_zoneinfo_not_found_returns_empty_class_stays_quota`, `test_utc_parses_without_tzdata`, `test_seconds_and_milliseconds_same_instant`, `test_past_or_beyond_horizon_is_empty`, `test_12am_12pm_12_00am_and_13pm_rejected`, `test_host_local_when_no_zone_given`. Real-zone cases are `skipif` with a visible reason when `zoneinfo.ZoneInfo("America/Chicago")` cannot load (no tzdata on a bare Windows); the injected-resolver versions always run.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_quota_reset.py console/tests/test_run_failures.py -rs` (read the skip reasons).

**3a-4 (T-020-16)** · FR-13, BR-10 · 3h · depends: 3a-3, 1a-4 [SHARED:run_failures.py 3/4, run_sync.py]
- Files: `console/server/run_failures.py` (`liveness`, `PLANNING_ONLY`, `NEXT_STEPS` constants), `console/server/run_sync.py` (`collect_evidence(repo_root, run, view)`: ticket comments with `posted_on >= created`, `worktrees.diff_stat` (`worktrees.py:207`) when the Run has a worktree); new `console/tests/test_liveness.py`.
- Change: `liveness(turn, mode, evidence, ticket_state, text)` returns `{state, reason}` (state in completed, advanced, plan_only, empty, blocked, failed; reason at most 200 chars); evidence = file-mutating tools (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`, never `Bash`) or console mutating verbs from `last_turn.tools`, comments/tracker items since `created`, non-empty diffstat; `plan`/`ask` modes never `plan_only`; the pattern is ported from `D:\Workspace\research-workspace\paperclip\server\src\services\run-liveness.ts:65-67`.
- Tests added: `TestLivenessTable::test_each_class` (mode, evidence count, text, lane, new critical question), `::test_plan_mode_planning_text_is_advanced_default_mode_is_plan_only`, `::test_bash_only_turn_with_no_text_is_empty`, `::test_eight_reply_text_fixtures` (4 planning-only, 4 summaries with "next"/"will" mid-sentence), `::test_plan_only_and_empty_never_schedule_retry`, `TestCollectEvidence::test_comments_since_created_and_diffstat_counted`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_liveness.py console/tests/test_run_sync.py`.

**3a-5 (T-020-17)** · FR-15, FR-3 AC5 · 3h · depends: 3a-2, 3a-3, 3a-4, 1a-4 [SHARED:run_failures.py 4/4, run_sync.py]
- Files: `console/server/run_failures.py` (`RETRY_TABLE`, `decide(run, failure, now, cfg)`), `console/server/run_sync.py` (default `decide_failure` becomes `run_failures.decide`); extend `console/tests/test_run_failures.py` and `console/tests/test_run_sync.py`.
- Change: table `transient_upstream` 2 at 30 s/120 s; `quota` 2 at `max(60 s, retry_not_before - now + 60 s)` only when the reset is known and within `quota_max_wait_secs` (6 h); `max_turns` 2 at 1 s; `process_lost` 1 at 10 s; total cap `max_total_retries` 3; non-retryable list from 3a-2; due = `max(now + delay, retry_not_before)` (BR-4); returns a patch with `scheduled_retry`, `retry_not_before`, `retry_due`, `attempt`, `attempts` (last 10) or terminal `failed` with `end_reason=retry_exhausted` or the class; overrides from `[runs.retry]`.
- Tests added: `TestRetryTable::test_n_plus_one_failures_give_n_retries_then_failed` (per class), `::test_non_retryable_classes_fail_with_zero_retries` (parametrised over the list), `::test_quota_three_hours_ahead_due_not_before_reset_plus_sixty`, `::test_quota_unknown_or_three_days_fails_without_retry_and_keeps_reset_time`, `::test_total_cap_three_across_classes`, `::test_delay_override_changes_due_and_bad_value_warns_once`, `::test_max_total_retries_zero_disables_retry`; in `test_run_sync.py` `TestProcessLost::test_killed_externally_while_running_gives_process_lost_and_one_scheduled_retry`, `::test_same_run_absent_at_startup_is_interrupted_without_retry`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_failures.py console/tests/test_run_sync.py console/tests/test_liveness.py console/tests/test_quota_reset.py`.

### Slice 3b: watch, retry, escalate

**3b-1 (T-020-18)** · FR-14 pure ACs · 2h · depends: 1a-3, 1a-4 [SHARED:run_watchdog.py 1/4]
- Files: new `console/server/run_watchdog.py`; new `console/tests/test_run_watchdog.py`.
- Change: pure `evaluate(run, view, now, cfg)` returning an action (`none`, `suspect`, `kill`): only `running` Runs have a silence clock; silence = `now - last_output_at`, falling back to `started_utc`, then Run `created`, never to local-naive `started` (CR-24); pending approval pauses the clock (BR-5), the clock restarts from the approval's end; `stall_kill_secs == 0` is flag-only; `view.watchable` false (API session) returns `none` (CR-25).
- Tests added: `TestEvaluate::test_599_none_601_suspect_700_no_second_notice_1801_kill`, `::test_pending_approval_one_hour_never_suspect_or_kill`, `::test_output_at_1799_seconds_ago_resets_clock`, `::test_zero_kill_flags_suspicious_only_after_ten_hours`, `::test_api_session_never_evaluated`, `::test_fallback_chain_uses_utc_started_then_created`, `::test_thresholds_from_config_and_inverted_pair_rejected`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_run_config.py`.

**3b-2 (T-020-19)** · FR-14 rest, NFR-6, NFR-7 · 3h · depends: 3b-1, 2a-2 [SHARED:run_watchdog.py 2/4, agent_manager.py, audit.py]
- Files: `console/server/run_watchdog.py` (`tick`, `Watchdog` thread), `console/server/runs.py` (`list_active(repo_root, known_terminal)` added here, additive), `console/server/agent_manager.py` (`start_watchdog(repo_root)` with a lazy import of `run_watchdog` to avoid the `verb_handlers` cycle, `stop_watchdog`, `shutdown_all` :429 joins it), `console/server/features/agents_feature.py` (one call in `apply` :22-34, honouring `watchdog_enabled`), `console/server/audit.py` (`run.stall_kill`, `run.retry`, `run.retry_exhausted` in `ACTIONS`).
- Change: `tick(repo_root, now=None, registry=None)`: single-flight lock (loser returns `{busy: true}`), per-Run try/except with `errors` count, `last_tick`; startup sweep on the first tick; for a stall kill write `timed_out`/`stalled` with annotations first via `runs.update`, then publish the notice and `session.kill_process()`; Runs whose chat has no session or no Run are skipped; `list_active` skips ids already known terminal so a steady-state tick parses only active files (CR-32); audit rows for each automatic action.
- Tests added: `TestTick::test_run_is_timed_out_on_disk_when_fake_kill_tree_is_called`, `::test_following_sync_over_dead_session_returns_empty_patch`, `::test_chat_without_run_is_not_evaluated`, `::test_exception_in_run_a_still_evaluates_run_b_errors_is_one`, `::test_two_concurrent_ticks_act_once_loser_busy`, `::test_hundred_active_runs_under_100ms`, `::test_terminal_ids_not_reparsed_on_second_tick`; `TestThread::test_shutdown_all_joins_within_two_seconds`, `::test_watchdog_enabled_false_starts_no_thread`, `::test_stall_kill_writes_audit_row`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_runs.py console/tests/test_plugins.py console/tests/test_notify_audit.py`.

**3b-3 (T-020-20)** · FR-16 · 3h · depends: 3b-2, 3a-5 [SHARED:run_watchdog.py 3/4]
- Files: `console/server/run_watchdog.py` (`execute_due_retries`, wired into `tick`); extend `console/tests/test_run_watchdog.py`.
- Change: a `scheduled_retry` Run with `retry_due <= now` and no stop request: live session gets `send(continuation)`; session not alive goes through `agent_manager.resume(repo_root, sid, server_port=...)` then `agent_manager.send`; `ValueError`/`FileNotFoundError` from resume gives `failed/resume_refused` and `agent_manager.create` is never called (T-011 invariant, `agent_manager.py:282-285`); `RuntimeError`/`OSError` from send gives `failed/retry_failed` (CR-36); success writes `running`, `attempt + 1`; audit `run.retry`; due time lives on the record so a fresh watchdog over the same files resumes the schedule.
- Tests added: `TestRetryExecution::test_live_session_gets_one_send_and_run_is_running_attempt_two`, `::test_dead_session_resume_value_error_fails_resume_refused_and_never_creates`, `::test_send_error_fails_retry_failed`, `::test_future_due_untouched_then_retried_after_simulated_restart`, `::test_stop_request_cancels_pending_retry_run_interrupted`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_agent_resume.py`.

**3b-4 (T-020-21)** · FR-17, NFR-9 · 2h · depends: 3b-3 [SHARED:run_watchdog.py 4/4]
- Files: `console/server/run_watchdog.py` (`escalate(repo_root, run)`, `ACTION_TABLE`); extend `console/tests/test_run_watchdog.py`.
- Change: for a `failed`/`timed_out` Run with a ticket, list the ticket's comments, skip when one by `run-watchdog` already starts with `[run <id>]`, else call `verb_handlers.ticket_comment(repo_root, ticket=..., text=..., author="run-watchdog")` (audit and bus come with it); text states run id, class, detail at most 300 chars, attempts, next human action; no env values, no raw `result` beyond 300 chars; runs inside the single-flight tick after the terminal write, so no Run field is needed for dedupe (CR-26). No question and no lane move.
- Tests added: `TestEscalation::test_action_table_has_row_per_class_plus_resume_refused_and_exhaustion` (iterates `run_failures.CLASSES`), `::test_failed_run_one_comment_after_three_syncs`, `::test_done_and_ticketless_runs_post_nothing`, `::test_comment_never_contains_env_values_or_long_raw_result`, `::test_quota_comment_names_reset_time_when_known`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_watchdog.py console/tests/test_ready_claim_comment_verbs.py`.

### Slice 3c: verbs

**3c-1 (T-020-22)** · FR-18 · 3h · depends: 3b-4 [SHARED:verbs.toml, verb_handlers.py 1st]
- Files: `console/config/verbs.toml` (+ `run-watch`, `run-retry` rows after `run-show`, :110-114; `needs_confirm`), `console/server/verb_handlers.py` (`run_watch`, `run_retry`, one-liners with signature `(repo_root, ticket=None, ...)`); new `console/tests/test_run_verbs.py`.
- Change: `run_watch` calls the same `run_watchdog.tick` the thread uses and returns `{synced, suspicious, killed, retried, last_tick, errors}`; `run_retry(run_id)` creates a new Run with `retry_of`, `state=scheduled_retry`, due now, through the 3b-3 path, refused for a Run that is not `failed`/`timed_out`/`interrupted` or while a Run with that `retry_of` is ACTIVE; old record untouched.
- Tests added: `TestRunWatch::test_counts_and_no_mutation_when_no_runs`, `TestRunRetry::test_done_run_refused`, `::test_unknown_id_refused`, `::test_failed_run_creates_one_new_run_old_file_byte_identical`, `::test_second_call_while_new_run_active_refused_creates_nothing`, `TestOneApi::test_both_verbs_in_mcp_tool_list_with_derived_schema_and_http_route`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_run_verbs.py console/tests/test_verbs.py console/tests/test_mcp.py console/tests/test_mcp_http.py console/tests/test_plugins.py console/tests/test_runs.py`; then full suite (phase 3 boundary).

---

## Phase 4: Claims and the review loop

Claims read Run state (so they follow Phases 1 and 3). `claimed_at` changes shape here, so the stop-hook comparison is re-proved in 4a-1.

### Slice 4a: claims

**4a-1 (T-020-23)** · FR-19 · 3h · depends: 1a-1, 0a-1 [SHARED:tickets.py, verb_handlers.py, backends/ 1st]
- Files: `console/server/tickets.py` (`create` :38-87, `load` :90-106 `setdefault("claimed_run","")`, `parse_claimed_at`, `set_claim` :218 gains keyword `claimed_run=None`, cleared on release), `console/server/backends/base.py` + `vault_backend.py` (`claim(..., claimed_run="", now=None)` stamps `%Y-%m-%dT%H:%M:%SZ` UTC in place of `date.today()` at :77), `console/server/verb_handlers.py` (`ticket_claim` :437 gains `run=""`; no `run` and exactly one ACTIVE chat Run on the ticket links it, zero or two links nothing; an unknown `run` id is refused with a named error, so a bogus link cannot make a claim look dead); new `console/tests/test_claims.py`.
- Tests added: `TestClaimedAtUtc::test_verb_claim_stamps_utc_timestamp_matching_regex`, `TestParseClaimedAt::test_date_only_is_end_of_day_utc`, `::test_empty_and_garbage_are_none`, `::test_full_timestamp_as_is`, `TestClaimedRun::test_older_toml_without_claimed_run_loads_empty`, `::test_explicit_run_stored`, `::test_sole_active_chat_run_autolinked`, `::test_zero_or_two_active_runs_store_empty`, `::test_unknown_run_id_refused`, `::test_release_clears_claimed_run`, `TestStopHookWithUtcClaim::test_same_day_comment_after_full_timestamp_claim_clears_reminder` (in `test_stop_hook.py`).
- Verify: `python -m pytest -o addopts="" -q console/tests/test_claims.py console/tests/test_stop_hook.py console/tests/test_tickets.py console/tests/test_vault_backend.py console/tests/test_backends.py console/tests/test_ready_claim_comment_verbs.py`.
- Done when: existing `test_conflicting_claim_is_refused_by_name` and the 8-thread claim race (`test_tickets.py:166`) are unchanged and green.

**4a-2 (T-020-24)** · FR-20, BR-6, BR-7 · 3h · depends: 4a-1, 1a-3 [SHARED:tickets.py]
- Files: `console/server/tickets.py` (`evaluate_claim(ticket, runs_for_ticket, now, cfg)` pure; `claim_status(repo_root, ticket_id, now=None)` wrapper; imports `runs` and `run_config`); new `console/tests/test_claim_status.py`.
- Change: order as FR-20: no holder is `free`; linked Run ACTIVE is `held/run_live` regardless of age; linked Run terminal at least `dead_grace_secs` ago is `stale/run_dead`, inside grace `held`; linked id with no record is `stale/run_missing` only when `claimed_at` is known and older than the grace; unlinked: any ACTIVE chat Run on the ticket is `held/run_live`, unknown `claimed_at` is `held/unknown`, older than TTL is `stale/ttl` (TTL 0 disables); any exception returns `held/unknown`.
- Tests added: `TestClaimStatus::test_every_branch_with_injected_clock` (the nine rows of the FR-20 AC), `::test_planner_done_builder_live_is_stale_run_dead`, `::test_scheduled_retry_counts_as_active`, `::test_config_from_claims_section_invalid_falls_back_with_one_warning`, `::test_read_error_returns_held_unknown`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_claim_status.py console/tests/test_tickets.py console/tests/test_run_config.py`.

**4a-3 (T-020-25)** · FR-21, NFR-6, NFR-8 · 3h · depends: 4a-2 [SHARED:tickets.py, vault_backend.py, verb_handlers.py, audit.py]
- Files: `console/server/tickets.py` (`set_claim(..., adopt_stale=False, now=None, info=None)`: on conflict, `evaluate_claim` runs inside `_mutate` under the `atomic_update` lock; stale means swap and record previous holder, `claimed_at`, `claimed_run`, basis, age into `info`; held means `ClaimConflictError` whose message names holder, basis and `claim-release`), `console/server/backends/vault_backend.py` (`claim` passes `adopt_stale=True`; `ready` :57 loads Runs once, groups by ticket, includes stale-claimed tickets with a `claim` object and still omits held ones), `console/server/verb_handlers.py` (`ticket_claim` records `ticket.claim.adopt` with the previous-holder detail and posts a comment authored by the adopter), `console/server/audit.py` (`ACTIONS` + `ticket.claim.adopt`); new `console/tests/test_claim_adopt.py`.
- Tests added: `TestAdopt::test_two_threads_adopt_same_stale_claim_exactly_one_wins_final_holder_matches` (repeated 20 rounds, NFR-8), `::test_audit_row_has_previous_holder_basis_age`, `::test_comment_posted_by_adopter`, `::test_held_claim_still_refused_and_error_names_holder_basis_release`, `::test_same_identity_reclaim_refreshes_claimed_at`, `TestReady::test_stale_listed_with_claim_state_held_omitted`, `::test_ready_reads_runs_once`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_claim_adopt.py console/tests/test_ready_claim_comment_verbs.py console/tests/test_vault_backend.py console/tests/test_tickets.py console/tests/test_notify_audit.py`.

**4a-4 (T-020-26)** · FR-22, BR-13 · 2h · depends: 4a-3 [SHARED:verbs.toml, verb_handlers.py, audit.py]
- Files: `console/server/tickets.py` (`release_claim(repo_root, ticket_id, agent, force, reason, now)` under `atomic_update`), `console/config/verbs.toml` (`claim-release`, `needs_ticket`, `needs_confirm`, after the `claim` row :134-140), `console/server/verb_handlers.py` (`ticket_claim_release(repo_root, ticket=None, agent="", force="", reason="")`: audits `ticket.claim.release` / `ticket.claim.force_release`, comment on force, bus publish), `console/server/audit.py`; new `console/tests/test_claim_release.py`.
- Change: holder releases its own; anyone releases `stale`; a `held` claim of another identity is refused unless `force` set with `reason` of at least 10 characters; every outcome audited with previous holder, previous `claimed_at`, basis, caller identity, reason.
- Tests added: `TestRelease::test_holder_release_clears_all_three_fields`, `::test_non_holder_release_of_held_claim_refused_claim_kept`, `::test_stale_claim_released_by_third_identity_audit_has_basis`, `::test_force_with_empty_or_five_char_reason_refused`, `::test_force_with_reason_succeeds_audits_previous_holder_and_comments`, `::test_in_cli_list_and_mcp_tool_list_and_needs_confirm`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_claim_release.py console/tests/test_verbs.py console/tests/test_mcp.py console/tests/test_cli_json.py`.

### Slice 4b: review loop, digest, protocols

**4b-1 (T-020-27)** · FR-24, BR-8 · 3h · depends: 4a-4 [SHARED:tickets.py, verbs.toml, verb_handlers.py, audit.py]
- Files: `console/server/tickets.py` (`review_rounds`/`review_escalated` defaults in `create` and `load`, `record_review(repo_root, ticket_id, outcome, max_rounds)` under `atomic_update`, not added to `EDITABLE` :193), `console/config/verbs.toml` (`review-round`), `console/server/verb_handlers.py` (`ticket_review_round(repo_root, ticket=None, outcome="", agent="")`; `tracker_add` :530 gains optional `raised_by=""`, CR-33), `console/server/audit.py` (`ticket.review`); new `console/tests/test_review_round.py`.
- Change: `changes_requested` increments; at `[review].max_rounds` (3) sets `review_escalated`, then (outside the lock, only on that single transition) opens one critical question through `tracker_add(type="review", priority="critical", raised_by="review-loop")` plus a comment, returns `escalate: true`; while escalated `changes_requested` returns `{ok: false, escalated: true}` without incrementing; `approved` and `human_decision` reset both fields; every call audited with the caller identity.
- Tests added: `TestReviewRound::test_three_changes_requested_escalate_with_exactly_one_critical_question_in_blockers`, `::test_fourth_refused_rounds_stay_three_no_second_question`, `::test_approved_resets_and_interleaved_approved_prevents_escalation`, `::test_human_decision_clears_escalation_and_restarts_at_one`, `::test_older_toml_loads_zero_false_and_create_includes_fields`, `::test_max_rounds_config_five_and_invalid_falls_back_to_three`, `::test_each_call_audited_with_identity`, `::test_concurrent_changes_requested_create_one_question`, `TestTrackerAdd::test_raised_by_passes_through`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_review_round.py console/tests/test_tickets.py console/tests/test_mutation_verbs.py console/tests/test_trackers.py console/tests/test_ticket_create_collapse.py`.

**4b-2 (T-020-28)** · FR-23 · 2h · depends: 4a-2, 4b-1, 1a-1
- Files: `console/server/context.py` (`build` :166 adds `claim`, `review`, `runs`; `format_markdown` :225 prints one line each only when non-empty); extend `console/tests/test_context.py`.
- Change: JSON always carries the three keys with neutral values (stable shape for T-021); markdown lines appear only when `claimed_by`, `review_rounds > 0` or escalated, or any Run exists.
- Tests added: `TestClaimReviewRuns::test_stale_claim_two_rounds_one_failed_run_render_three_lines_and_json_keys`, `::test_plain_ticket_markdown_identical_to_before`, `::test_escalated_review_line_says_escalated`.
- Verify: `python -m pytest -o addopts="" -q console/tests/test_context.py console/tests/test_cli_json.py console/tests/test_mcp.py`.

**4b-3 (T-020-29)** · FR-25 · 1h · depends: 4b-1, 4b-2
- Files: `.claude/agents/verifier.md` (step 10 :22 and step 1), `.claude/agents/fixer.md` (step 1 :13); new `console/tests/test_agent_protocol_text.py`.
- Change: verifier on unmet criteria calls `review-round outcome=changes_requested` before routing to the fixer and stops, surfacing the escalation, when the reply says `escalate`; on a clean pass calls `outcome=approved`; verifier and fixer both read `console context` first and stop asking the user for a `human_decision` when `review.escalated` is true. Output contract blocks, frontmatter, roster untouched; no new file under `.claude/agents` or `.claude/skills`.
- Tests added: `test_verifier_and_fixer_mention_review_round_and_escalated_stop_rule`, `test_output_contract_blocks_intact`, `test_no_new_agent_or_skill_files` (counts 7 agent files, 39 skill dirs).
- Verify: `python -m pytest -o addopts="" -q console/tests/test_agent_protocol_text.py console/tests/test_harness_lint.py`, then `python console/kanban.py harness lint` (expect 0 errors, 0 warnings, `39 skills, 7 agents`).

**Phase 4 boundary:** full suite 0 failed.

---

## Phase 5: VERIFY (verifier-owned, task 5a-1 / T-020-30, 2h)

Evidence comes from commands, not from a builder's status line.

1. **Full suite:** `python -m pytest -o addopts="" -q`. Expected: 0 failed; passed = 1445 + the new tests added by tasks 0a-1..4b-3 (record the exact numbers; baseline before the ticket was 1445 collected, 1442 passed, 3 failed). Touched-module baseline of 222 passed must still pass (NFR-5).
2. **Harness lint:** `python console/kanban.py harness lint` gives 0 errors, 0 warnings and `39 skills, 7 agents`.
3. **NFR-1 `console/static` untouched:** `git diff --stat 0c42658 -- console/static` prints nothing; stdlib-only: scan every new or changed `console/server` file's imports against `sys.stdlib_module_names` (one-liner recorded in the verification file).
4. **NFR-3/NFR-11:** `test_proc_tree.py` green on Windows; PowerShell marker check `Get-CimInstance Win32_Process | Where-Object CommandLine -match 'T020-TREE'` returns nothing; reach limit stated in the test docstring and in the requirements § 8.
5. **NFR-4:** `python -m pytest -o addopts="" -q <the new test files> --durations=10` total under 30 s, proc-tree under 15 s, no test sleep above 2 s; `grep -nE "claude|cursor-agent"` in the new tests finds no argv or spawn.
6. **NFR-8:** concurrency tests (`eight_threads`, `two_threads_adopt`, `concurrent_changes_requested`) pass 20 consecutive runs (parametrised rounds plus `for i in $(seq 20); do python -m pytest -o addopts="" -q <test> || break; done`).
7. **BR-12/NFR-10:** `git diff --stat 0c42658 -- console/config` shows only `verbs.toml`; `agents.toml`, `console.toml`, `schedules.toml` untouched; no `open(...,"w")` in `run_config.py`.
8. **CI (FR-9 AC2):** if pushed, the Actions annotation for `desktop (windows-latest)` is read from the public API; if not pushed the row is `PENDING-CI`, stated plainly.
9. **Open Confirmations** carried into verification as PENDING, not PASS: `resetsAt` units and status words (Q14), `CLAUDECODE` nesting guard, long-tool-call output cadence (watchdog defaults generous, kill has an off switch).

### Evidence table skeleton for `T-020-verification.md`

Columns: `AC id | AC (short) | Task | Test (file::name) | Command | Result / evidence (file:line, count) | Status (PASS / FAIL / PENDING / PENDING-CI)`. One row per AC; the AC count per FR is fixed by the frozen requirements:

| FR | ACs | Task(s) | Test file(s) |
|----|----:|---------|--------------|
| FR-1 | 3 | 1a-1 | test_runs.py |
| FR-2 | 4 | 1a-1 | test_runs.py |
| FR-3 | 5 | 1a-4, 3a-5 | test_run_sync.py |
| FR-4 | 4 | 1a-2 | test_session_state.py |
| FR-5 | 4 | 2a-1, 2a-2 | test_procs.py |
| FR-6 | 3 | 2a-1, 2a-2, 1a-3 | test_procs.py, test_run_config.py |
| FR-7 | 3 | 2b-1, 2b-2 | test_output_caps.py |
| FR-8 | 3 | 2b-3 | test_linger_kill.py |
| FR-9 | 3 | 2c-1, 2c-2 | test_proc_tree.py, verify.yml |
| FR-10 | 2 | 3a-1 | test_normalize_evidence.py |
| FR-11 | 4 | 3a-2 | test_run_failures.py |
| FR-12 | 4 | 3a-3 | test_quota_reset.py |
| FR-13 | 5 | 3a-4 | test_liveness.py |
| FR-14 | 10 | 3b-1, 3b-2 | test_run_watchdog.py |
| FR-15 | 5 | 3a-5 | test_run_failures.py |
| FR-16 | 4 | 3b-3 | test_run_watchdog.py |
| FR-17 | 4 | 3b-4 | test_run_watchdog.py |
| FR-18 | 4 | 3c-1 | test_run_verbs.py |
| FR-19 | 5 | 0a-1, 4a-1 | test_stop_hook.py, test_claims.py |
| FR-20 | 4 | 4a-2 | test_claim_status.py |
| FR-21 | 4 | 4a-3 | test_claim_adopt.py |
| FR-22 | 4 | 4a-4 | test_claim_release.py |
| FR-23 | 2 | 4b-2 | test_context.py |
| FR-24 | 6 | 4b-1 | test_review_round.py |
| FR-25 | 3 | 4b-3 | test_agent_protocol_text.py + lint command |
| **Total** | **102** | | |

NFR-1..NFR-11 get one row each (evidence per the numbered checks above); the two ticket-level criteria (lint 0/0 at `39 skills, 7 agents`; touched-module baseline of 222 plus the 3 date-rot tests passing) get one row each: 115 rows in all.

---

## Effort reconciliation

| Phase | Tasks | Hours |
|-------|-------|------:|
| 0 | 0a-1 | 1 |
| 1 | 1a-1 (3), 1a-2 (3), 1a-3 (2), 1a-4 (3) | 11 |
| 2 | 2a-1 (3), 2a-2 (3), 2b-1 (2), 2b-2 (3), 2b-3 (3), 2c-1 (3), 2c-2 (1) | 18 |
| 3 | 3a-1 (1.5), 3a-2 (3), 3a-3 (3), 3a-4 (3), 3a-5 (3), 3b-1 (2), 3b-2 (3), 3b-3 (3), 3b-4 (2), 3c-1 (3) | 26.5 |
| 4 | 4a-1 (3), 4a-2 (3), 4a-3 (3), 4a-4 (2), 4b-1 (3), 4b-2 (2), 4b-3 (1) | 17 |
| 5 | 5a-1 | 2 |
| **Total** | 30 tasks | **75.5** |

Equals [[T-020-task-breakdown]] § Effort summary and [[T-020-plan]] § Effort; dev 73.5h sits inside [[T-020-effort-estimate]] 58-95h.

## Links
- [[T-020-summary]] · [[T-020-requirements]] · [[T-020-plan]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-effort-estimate]] · [[T-020-critique-report]] · [[T-020-plan-iteration-log]] · [[T-020-progress]] · [[T-020-verification]]
