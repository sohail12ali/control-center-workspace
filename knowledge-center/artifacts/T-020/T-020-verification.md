---
ticket: "T-020"
artifact: verification
---

# Verification: T-020

Verifier run 2026-10-02 (plan task 5a-1). Everything below was run by the verifier; nothing is taken from builder reports. Test evidence = `python -m pytest -o addopts="" -rA -q <T-020 files>` (473 tests incl. touched suites; 472 passed, 1 Windows flake, see Defects) plus the full suite. Legend: PASS / FAIL / NOT VERIFIED. "T:" = test run and passed.

**Verdict: READY WITH CAVEATS** - 1 HIGH defect (D-A), 1 MEDIUM (D-B), 1 LOW/MEDIUM flake (D-C). Not routed to close-work by the verifier.

## Acceptance Criteria (AC-by-AC evidence table)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| FR-1a | STATES = old six + timed_out, scheduled_retry; TERMINAL/ACTIVE partition | PASS | T: test_runs.py::TestRunStates::test_states_are_old_six_plus_two_and_partitioned |
| FR-1b | set_state(done->running) raises, file unchanged | PASS | T: TestRunStates::test_done_to_running_raises_and_file_unchanged |
| FR-1c | old `running` record loads/lists | PASS | T: TestRunStates::test_existing_running_record_loads_and_lists_unchanged |
| FR-2a | pre-T-020 record returns all new keys | PASS | T: TestRunDefaults::test_pre_t020_record_returns_every_new_key_with_default |
| FR-2b | 8 threads, no lost update | PASS | T: TestRunUpdate::test_eight_threads_no_lost_update[0..19] (20/20); but see NFR-8 |
| FR-2c | one-write terminal update, then refused, byte-identical | PASS | T: test_terminal_with_annotations_one_write_then_refused_byte_identical |
| FR-2d | failure_detail >500 truncated with marker | PASS | T: test_failure_detail_truncated_with_marker |
| FR-3a | table over session states | PASS | T: test_run_sync.py::TestSyncRunTable::test_state_for_each_row |
| FR-3b | startup sweep live/dead/absent | PASS | T: TestStartupSweep::test_live_kept_dead_and_absent_interrupted_with_ended |
| FR-3c | terminal never changed | PASS | T: TestTerminal::test_terminal_run_never_changed_even_after_another_turn |
| FR-3d | ring overflow still right | PASS | T: TestRing::test_overflowed_ring_still_yields_state_from_last_turn |
| FR-3e | external kill -> process_lost + one retry; startup -> interrupted no retry | PASS | T: TestProcessLost (2 tests) |
| FR-4a | injected clock sets last_output_at, in snapshot | PASS | T: test_session_state.py::TestOutputTimestamp::test_injected_clock_sets_last_output_at_and_snapshot |
| FR-4b | no output -> "" | PASS | T: test_no_output_is_empty_string_not_now |
| FR-4c | last_turn survives RING_MAX+1 | PASS | T: TestLastTurn::test_survives_ring_overflow_by_ring_max_plus_one |
| FR-4d | pending_for lists/clears | PASS | T: TestPendingFor::test_lists_while_parked_empty_after_decide_or_forget |
| FR-5a | nt: taskkill /T then /T /F, no-window | PASS | T: test_procs.py::TestKillTree::test_nt_issues_taskkill_T_then_T_F_after_grace_with_no_window_flag |
| FR-5b | posix: TERM then KILL on own group, never getpgrp | PASS | T: test_posix_signals_term_then_kill_on_own_group_never_getpgrp, test_posix_never_signals_a_group_it_does_not_lead |
| FR-5c | already-exited no-op | PASS | T: test_already_exited_process_is_a_no_op |
| FR-5d | no bare proc.kill()/terminate() in agent_session.py/agents.py | PASS | `grep -nE "\.(kill\|terminate)\(\)" console/server/agent_session.py console/server/agents.py` -> no output (rc=1); T: TestNoBareKill |
| FR-6a | clean_env drops deny list keeps auth vars | PASS | T: TestCleanEnv::test_deny_list_removed_and_auth_vars_kept; default list = 11 names incl. CLAUDECODE, CLAUDE_CODE_MESSAGING_TOKEN |
| FR-6b | three spawn sites pass env= | PASS | T: TestLiveSessionStart::test_env_excludes_deny_list_and_group_flags_on_nt_and_posix, TestTurnSessionDeliver::test_env_and_group_flags, TestAgentsLaunch::test_env_and_group_flags |
| FR-6c | [runs].env_strip override; non-list falls back, one warning | PASS | T: test_env_strip_override_from_config, test_non_list_env_strip_falls_back_with_one_warning |
| FR-7a | 3 MiB line -> one truncated event, next parses | PASS | T: test_output_caps.py::TestLineCap::test_three_mib_line_becomes_one_truncated_event_and_next_line_parses |
| FR-7b | per-turn cap: one notice, one kill; two turns none | PASS | T: TestTurnCap::test_breach_publishes_one_notice_and_one_kill, test_counter_resets_at_turn_start_two_turns_no_breach |
| FR-7c | 10 000 lines <1 s; truncated past 200k | PASS | T: TestAgentsReader (2 tests) |
| FR-8a | result then sleep killed within grace+1 | PASS | T: test_linger_kill.py::test_result_then_sleep_killed_within_grace_plus_one_second; test_busy_false_and_queue_drains_when_process_lingers[False/True] |
| FR-8b | exit inside grace: no kill/notice | PASS | T: test_exit_inside_grace_not_killed_no_notice |
| FR-8c | LiveSession never killed by rule | PASS | T: test_live_session_alive_after_result_never_killed |
| FR-9a | real tree: root/child/grandchild gone | PASS | T: test_proc_tree.py::test_kill_tree_leaves_no_orphan_root_child_or_grandchild (not skipped, Windows 11). Process listing of python processes before and after: `diff` IDENTICAL (only 4 `console/mcp_server.py` processes) |
| FR-9b | Windows control: plain kill leaves grandchild alive | PASS (local) | T: test_windows_control_plain_kill_leaves_grandchild_alive (ran, not skipped). "Runs in CI on the Windows runner": NOT VERIFIED (PENDING-CI, Q15) |
| FR-9c | known limit stated in docstring and edge cases | PASS | console/tests/test_proc_tree.py:9-10; requirements-draft section 8; decision-log line 39 |
| FR-10a | turn.end carries errors/error/api_error_status/stop_reason; defaults [] "" null "" | PASS | T: test_normalize_evidence.py::test_result_with_errors_status_and_stop_reason, test_result_without_fields_yields_empty_defaults |
| FR-10b | existing normaliser tests unchanged | PASS | full suite 1855 passed |
| FR-11a | >=20-row table | PASS | T: test_run_failures.py::test_twenty_plus_rows (+ test_assistant_prose_never_reaches_auth) |
| FR-11b | success+is_error auth sample -> auth_required | PASS | T: test_success_subtype_with_is_error_is_auth_required |
| FR-11c | "rate limit" in successful text not failed | PASS | T: test_rate_limit_words_in_successful_turn_not_failed |
| FR-11d | unknown text -> unclassified | PASS | T: test_unknown_text_on_failed_turn_is_unclassified_never_transient |
| FR-12a | Paperclip prose fixtures incl. rollover | PASS | T: test_quota_reset.py::TestProse::test_paperclip_fixtures_with_fixed_now, ..._with_real_zoneinfo |
| FR-12b | no tzdata: non-UTC "", class quota; UTC parses | PASS | T: test_zoneinfo_not_found_returns_empty_class_stays_quota, test_utc_parses_without_tzdata |
| FR-12c | seconds == ms; past/horizon "" | PASS | T: test_seconds_and_milliseconds_same_instant, test_past_or_beyond_horizon_is_empty |
| FR-12d | 12am/12pm/12:00am, 13pm rejected | PASS | T: test_12am_12pm_12_00am_and_13pm_rejected |
| FR-12e | resetsAt units against a real claude stream | PASS — real stream 2026-10-05 | `console/.cache/agent-chats/569bed5d941a.log` (a real claude-haiku-4-5 stream from the T-024 smoke) carries `rate_limit_event.rate_limit_info.resetsAt: 1791182400`, which is **epoch seconds** (2026-10-05T06:40Z, `rateLimitType: five_hour`). The normalizer kept it as `resets_at: 1791182400`, and `console/server/run_failures.py` `parse_reset` on that notice (status forced to `rejected`, now=03:00Z) → `2026-10-05T06:40:00Z`. Observed status vocabulary: `allowed` only; a real `rejected` event and failed result line are still unobserved (Q14 remainder). |
| FR-13a | table over classes | PASS | T: test_liveness.py::TestLivenessTable::test_each_class |
| FR-13b | plan mode text -> advanced; default mode -> plan_only | PASS | T: test_plan_mode_planning_text_is_advanced_default_mode_is_plan_only |
| FR-13c | Bash-only empty text -> empty | PASS | T: test_bash_only_turn_with_no_text_is_empty |
| FR-13d | 8 reply fixtures | PASS | T: test_eight_reply_text_fixtures |
| FR-13e | plan_only/empty never retried | PASS | T: test_plan_only_and_empty_never_schedule_retry |
| FR-14a | 599/601/700/1801 sequence | PASS | T: test_run_watchdog.py::TestEvaluate::test_599_none_601_suspect_700_no_second_notice_1801_kill |
| FR-14b | pending approval 1 h never suspect/kill | PASS | T: test_pending_approval_one_hour_never_suspect_or_kill, TestTick::test_pending_approval_pauses_then_clock_restarts_when_it_ends |
| FR-14c | output 1799 s ago resets | PASS | T: test_output_at_1799_seconds_ago_resets_clock |
| FR-14d | timed_out on disk before kill; later sync empty | PASS | T: TestTick::test_run_is_timed_out_on_disk_when_fake_kill_tree_is_called, test_following_sync_over_dead_session_returns_empty_patch |
| FR-14e | chat without Run not evaluated | PASS | T: TestTick::test_chat_without_run_is_not_evaluated |
| FR-14f | thresholds from [runs]; inverted pair rejected | PASS | T: test_thresholds_from_config_and_inverted_pair_rejected; test_run_config.py::test_stall_kill_not_above_suspect_rejected_defaults_used |
| FR-14g | shutdown_all joins <2 s | PASS | T: TestThread::test_shutdown_all_joins_within_two_seconds |
| FR-14h | kill=0 flag only; watchdog_enabled=false no thread | PASS | T: test_zero_kill_flags_suspicious_only_after_ten_hours, test_zero_kill_config_never_kills, test_watchdog_enabled_false_starts_no_thread |
| FR-14i | error in Run A, Run B still evaluated, errors==1 | PASS | T: test_exception_in_run_a_still_evaluates_run_b_errors_is_one |
| FR-14j | two concurrent ticks act once | PASS (in-process only) | T: test_two_concurrent_ticks_act_once_loser_busy. The lock is per process; the CLI/MCP process is separate, see D-A |
| FR-15a | N+1 failures -> N retries then failed | PASS | T: test_run_failures.py::test_n_plus_one_failures_give_n_retries_then_failed[*] |
| FR-15b | non-retryable straight to failed | PASS | T: test_non_retryable_classes_fail_with_zero_retries |
| FR-15c | quota 3 h ahead >= reset+60 s; empty/3 days -> fail, comment names reset | PASS | T: test_quota_three_hours_ahead_due_not_before_reset_plus_sixty, test_quota_unknown_or_three_days_fails_without_retry_and_keeps_reset_time; TestEscalation::test_quota_comment_names_reset_time_when_known |
| FR-15d | total cap 3 | PASS | T: test_total_cap_three_across_classes |
| FR-15e | [runs.retry] delay override; non-numeric falls back | PASS | T: test_delay_override_changes_due_and_bad_value_warns_once |
| FR-16a | live session: one send, running, attempt 2 | PASS | T: TestRetryExecution::test_live_session_gets_one_send_and_run_is_running_attempt_two |
| FR-16b | resume ValueError -> failed/resume_refused, no create | PASS | T: test_dead_session_resume_value_error_fails_resume_refused_and_never_creates |
| FR-16c | future due untouched; retried after simulated restart | PASS | T: test_future_due_untouched_then_retried_after_simulated_restart |
| FR-16d | stop cancels pending retry | PASS | T: test_stop_request_cancels_pending_retry_run_interrupted |
| FR-17a | action table row for every class + resume_refused + exhaustion | PASS | T: TestEscalation::test_action_table_has_row_per_class_plus_resume_refused_and_exhaustion |
| FR-17b | exactly one comment over 3 syncs | PASS | T: test_failed_run_one_comment_after_three_syncs |
| FR-17c | done / ticketless: none | PASS | T: test_done_and_ticketless_runs_post_nothing |
| FR-17d | no env values / raw result >300 | PASS | T: test_comment_never_contains_env_values_or_long_raw_result |
| FR-17 intent | every failed/timed_out end with a ticket gets one comment | PASS (re-verified) | D-B: a Run failed by the output-cap path (agent_manager.py `_make_on_limit`, runs.update direct) gets no comment and no audit row. Repro in throwaway workspace: on_limit(output_cap) -> Run failed/output_cap; `run_watchdog.tick` -> comments by run-watchdog = [] | RE-VERIFIED 2026-10-03 after fix D-B: test_output_caps.py::TestOnLimitHook::test_cap_failure_posts_one_escalation_comment_and_one_audit_row (hook fired twice -> one comment, one audit row); full suite 1867 passed.
| FR-18a | run-watch with confirm: counts, nothing mutated with no Runs | PASS | T: test_run_verbs.py::TestRunWatch::test_counts_and_no_mutation_when_no_runs. Real repo: `run-list` -> count 0, then `verb run run-watch --confirm` -> `{synced:0,suspicious:0,killed:0,retried:0,errors:0,busy:false,...,ok:true}`; tracked git status unchanged |
| FR-18b | run-retry on done / unknown -> ok:false | PASS | T: TestRunRetry::test_done_run_refused, test_unknown_id_refused; throwaway CLI: `run-retry --confirm --set run_id=nope` -> `{ok:false,error:"no run nope"}` |
| FR-18c | run-retry on failed: one new Run, old byte-identical; second refused | PASS | T: test_failed_run_creates_one_new_run_old_file_byte_identical, test_second_call_while_new_run_active_refused_creates_nothing |
| FR-18d | both verbs in MCP list + HTTP route | PASS | T: TestOneApi::test_both_verbs_in_mcp_tool_list_with_derived_schema_and_http_route; `verb list` shows run-retry, run-watch |
| FR-18 intent | run-watch safe from the CLI/MCP process | PASS (re-verified) | D-A (HIGH) | RE-VERIFIED 2026-10-03 after fix D-A: `python console/kanban.py verb run run-watch --confirm` from the CLI returns {ok:true, skipped:'no live session registry in this process', synced:0,...} and mutates nothing; tests test_run_verbs.py (skipped, owns_registry, server ticks but never sweeps) and test_run_watchdog.py::test_explicit_startup_tick_sweeps pass.
| FR-19a | claimed_at UTC regex | PASS | T: test_claims.py::TestClaimedAtUtc::test_verb_claim_stamps_utc_timestamp_matching_regex; throwaway CLI claim -> `claimed_at = "2026-10-02T16:40:37Z"` |
| FR-19b | parse_claimed_at date-only/empty/garbage | PASS | T: TestParseClaimedAt (3 tests) |
| FR-19c | test_stop_hook passes on any date | PASS (today only) | T: test_stop_hook.py all pass on 2026-10-02 (the 3 D-1 date-rot tests now pass). Other dates not run (cannot change the clock); injected-clock seam read in stop_hook.py `_LOCAL_TZ`/`_updated_floor` |
| FR-19d | older toml loads, claimed_run "" | PASS | T: TestClaimedRun::test_older_toml_without_claimed_run_loads_empty |
| FR-19e | claimed_run explicit / auto / zero-or-two / release | PASS | T: test_explicit_run_stored, test_sole_active_chat_run_autolinked, test_zero_or_two_active_runs_store_empty, test_release_clears_claimed_run |
| FR-20a | every branch with injected clock | PASS | T: test_claim_status.py::test_every_branch_with_injected_clock, test_unlinked_branches |
| FR-20b | planner done + builder live -> stale/run_dead | PASS | T: test_planner_done_builder_live_is_stale_run_dead |
| FR-20c | scheduled_retry is ACTIVE | PASS | T: test_scheduled_retry_counts_as_active |
| FR-20d | [claims] config, invalid falls back | PASS | T: test_config_from_claims_section_invalid_falls_back_with_one_warning |
| FR-21a | existing ready/claim/comment tests unchanged | PASS | full suite 1855 passed (includes test_ready_claim_comment_verbs.py) |
| FR-21b | two threads adopt: one wins | PASS (flaky) | T: test_claim_adopt.py::test_two_threads_adopt_same_stale_claim_exactly_one_wins_final_holder_matches passes in full suite and 6 reruns; FAILED once (PermissionError in tomlio os.replace) - D-C |
| FR-21c | one ticket.claim.adopt row with previous_holder, basis | PASS | T: test_audit_row_has_previous_holder_basis_age |
| FR-21d | ready lists stale, omits held | PASS | T: TestReady::test_stale_listed_with_claim_state_held_omitted |
| FR-22a | holder release clears three fields; non-holder refused | PASS | T: test_claim_release.py::test_holder_release_clears_all_three_fields, test_non_holder_release_of_held_claim_refused_claim_kept; throwaway CLI bob non-force -> `ok:false ... only the holder may release it` |
| FR-22b | stale release by third identity, audit basis | PASS | T: test_stale_claim_released_by_third_identity_audit_has_basis |
| FR-22c | force needs reason >=10; success audited + comment | PASS | T: test_force_with_empty_or_five_char_reason_refused, test_force_with_reason_succeeds_audits_previous_holder_and_comments; throwaway CLI: reason=short -> "force needs a reason of at least 10 characters"; valid -> `forced:true, previous_holder:"alice"`; ticket.toml claim fields cleared; audit shows ticket.claim.force_release |
| FR-22d | in verb list + MCP list; no confirm -> VerbError | PASS | T: test_in_cli_list_and_mcp_tool_list_and_needs_confirm; CLI `verb run claim` without --confirm -> "requires explicit confirmation" |
| FR-22 gate | human gate on force (gated_tools in agents.toml) | PASS — decided and driven 2026-10-05 | Q12: the owner chose to gate `claim-release`, `review-round` and `close-override`. They are in `console/config/agents.toml` `gated_tools`: `mcp__console__*` for claude, `console_*` for all 4 API rows. Tested by `console/tests/test_desktop_verbs.py::TestConsoleVerbAccess`. Live: chat `efcfb0c8223b` called `mcp__console__claim-release`, which raised approval card `5e582a9779f0`; it was denied, and the agent was told 'A human denied this mcp__console__claim-release call.' The gate covers the whole verb, not only `force=1`: an agent releasing its own claim also gets a card. |
| FR-23a | stale claim + 2 rounds + failed Run -> three lines + JSON keys | PASS | T: test_context.py::TestClaimReviewRuns::test_stale_claim_two_rounds_one_failed_run_render_three_lines_and_json_keys |
| FR-23b | plain ticket renders as before | PASS | T: test_plain_ticket_markdown_identical_to_before |
| FR-24a | 3 changes_requested -> escalate, one critical question in blockers | PASS | T: test_review_round.py::test_three_changes_requested_escalate_with_exactly_one_critical_question_in_blockers; throwaway CLI rounds 1,2,3 -> third `escalate:true`; Q1 priority critical, raised_by review-loop |
| FR-24b | fourth refused, rounds stay 3, no second question | PASS | T: test_fourth_refused_rounds_stay_three_no_second_question; CLI 4th -> `ok:false, escalated:true, rounds:3` |
| FR-24c | approved resets; interleaved approved prevents escalation | PASS | T: test_approved_resets_and_interleaved_approved_prevents_escalation |
| FR-24d | human_decision clears escalation, restart at 1 | PASS | T: test_human_decision_clears_escalation_and_restarts_at_one |
| FR-24e | older toml 0/false; create includes; not EDITABLE | PASS | T: test_older_toml_loads_zero_false_and_create_includes_fields, test_not_user_editable |
| FR-24f | max_rounds=5; 0/non-int -> 3 | PASS | T: test_max_rounds_config_five_and_invalid_falls_back_to_three |
| FR-24 gate | human gate on human_decision | PASS — 2026-10-05 | `review-round` is gated under both spellings: `console/tests/test_desktop_verbs.py::TestConsoleVerbAccess::test_the_overriding_verbs_are_gated_for_claude`, `console/tests/test_desktop_verbs.py::TestConsoleVerbAccess::test_the_overriding_verbs_are_gated_for_every_api_backend`. It uses the same hook path that was driven live for FR-22. The gate covers the whole verb, not only `human_decision`. |
| FR-25a | review-round + review.escalated in verifier.md/fixer.md; contracts intact | PASS | grep: verifier.md:13,22; fixer.md:13; T: test_agent_protocol_text.py (3 tests) |
| FR-25b | harness lint 0/0 at 39 skills, 7 agents | PASS | `python console/kanban.py harness lint` -> `39 skills, 7 agents \| 0 error(s), 0 warning(s)` |
| FR-25c | no new files under .claude/agents or skills | PASS | `git status --short .claude` -> only M fixer.md, M verifier.md |
| NFR-1 | stdlib only; no console/static change | PASS | `git diff --stat -- console/static` empty; imports in run_*.py and added imports in console/server diff are all stdlib (os, re, sys, math, signal, subprocess, time, threading, zoneinfo, datetime) or intra-package |
| NFR-2 | unknown never zero/success | PASS | T: test_no_output_is_empty_string_not_now, test_unclassified_failure_is_never_retried, test_every_branch (held/unknown), test_unreadable_ticket_fails_closed_to_zero |
| NFR-3 | Win+py3.14 primary; os.name-patched nt/posix tests; CI matrix green | PASS (local) / CI NOT VERIFIED | nt/posix tests ran (FR-5, TestTreeSpawnKwargs). New verify.yml step has never run on a real runner (PENDING-CI, Q15) |
| NFR-4 | fakes only, no real claude, new set <30 s, sleeps <=2 s | PASS (re-verified) | grep: no claude/cursor-agent spawn in new tests (only `backend="claude"` strings); max sleep 0.6 s; but new-test set took 31.50 s and 33.01 s vs <30 s target (host load); real-process test 1.9 s | RE-MEASURED 2026-10-03: the 18 new test files (349 tests) ran in 23.14 s (target 30 s); max sleep 0.3 s after trimming test_linger_kill.py; no assertion weakened.
| NFR-5 | old data loads; baseline + 3 date-rot pass; roster unchanged | PASS | full suite 1855 passed; test_stop_hook passes; lint 39/7 |
| NFR-6 | every automatic/forced change leaves a trace | PASS with gap | stall kill, adopt, release, force release, review: audit rows (T: test_stall_kill_writes_audit_row, test_each_call_audited_with_identity, CLI audit counts). Retry scheduled is traced only by the Run record (no audit row); output_cap failure has transcript notice but no comment (D-B) |
| NFR-7 | tick over 100 Runs <100 ms; 10 000 lines <2 s | PASS | T: test_hundred_active_runs_under_100ms, test_ten_thousand_lines_under_two_seconds |
| NFR-8 | concurrency tests pass 20 consecutive runs | PASS (re-verified) | loop of 20 runs of the 4 concurrency tests: 19 pass, 1 fail (PermissionError `os.replace` in unchanged tomlio.py:344). Two further isolated failures seen (test_claim_adopt, test_review_round concurrent). D-C | RE-VERIFIED 2026-10-03 after fix D-C (tomlio._replace bounded retry, TestReplaceRetry): 20 consecutive runs of the claim-adopt, review-round and tomlio concurrency tests = 20 pass, 0 fail (orchestrator run).
| NFR-9 | no secret in log/transcript/comment/audit; identity env stripped | PASS (note) | T: FR-6 and FR-17d tests. Note: `_scrub` runs only on the comment path; Run `failure_detail` (<=500 chars of API error text) is not scrubbed |
| NFR-10 | thresholds from console.toml with defaults; config never written | PASS | T: test_run_config.py (18 tests incl. TestNeverWrites); `git diff --stat` agents.toml/console.toml/schedules.toml empty; only verbs.toml changed (+37 lines: run-watch, run-retry, claim-release, review-round) |
| NFR-11 | known limits stated | PASS | see FR-9c |
| BR-1 | terminal immutable | PASS | FR-1b, FR-2c, FR-3c |
| BR-2 | unclassified/non-retryable never retried | PASS | FR-11d, FR-15b |
| BR-3 | bounded retries, human told once | PASS | FR-15a/d, FR-17b |
| BR-4 | no retry before retry_not_before | PASS | T: test_never_before_retry_not_before |
| BR-5 | silence clock paused during approval | PASS | FR-14b |
| BR-6 | live owner Run never stale | PASS (code) / see D-A | T: test_every_branch_with_injected_clock (3-day-old claim, live Run -> held/run_live). D-A can flip a live Run to interrupted and so end the protection |
| BR-7 | unknown never expires | PASS | T: test_read_error_returns_held_unknown; empty claimed_at -> held/unknown |
| BR-8 | only approved/human_decision reset | PASS | FR-24c/d; CLI: `approved` after escalation resets (as specified) |
| BR-9 | chat without Run never killed/retried/reconciled; hygiene applies to all | PASS | T: test_chat_without_run_is_not_evaluated, TestTurnCap::test_chat_without_run_is_still_killed_without_error |
| BR-10 | read-only mode never plan_only | PASS | T: test_read_only_mode_never_plan_only |
| BR-11 | every kill is tree kill; no group signal without own group | PASS | FR-5a/b |
| BR-12 | no direct TOML writes by automatic actors; one shared tick | PASS | grep `tomlio\.` in console/server/run_*.py -> none; watchdog writes via runs.update/verb_handlers.ticket_comment; verb run_watch calls run_watchdog.tick; claim/review use tickets.py atomic_update writers; config untouched |
| BR-13 | force needs confirm + reason >=10, audited | PASS | FR-22c |

## Test Results

- Full suite, run 1: `python -m pytest -o addopts="" -q` -> `1855 passed, 2 warnings in 304.58s (0:05:04)` (0 failed; the 2 warnings include a PytestUnhandledThreadExceptionWarning, PermissionError in test_tomlio concurrent writers, the known flake, which did not fail the run). No rerun was needed.
- T-020 + touched files, `-rA`: `1 failed, 472 passed in 43.15s` - the failure was test_claim_adopt two-thread test (PermissionError, tomlio os.replace). New-test-only run: `1 failed, 341 passed` (test_review_round concurrent, same PermissionError); reruns: 6x `67 passed`, 5x `22 passed`, 3x `206 passed`, final new-set run `342 passed, 2 warnings in 31.50s`.
- `python console/kanban.py harness lint` -> `39 skills, 7 agents | 0 error(s), 0 warning(s)`.
- `git diff --stat -- console/static` -> empty. No `proc.kill()/terminate()` in agent_session.py/agents.py (grep rc=1).
- Process-tree tests (test_proc_tree.py, test_linger_kill.py, test_procs.py): `50 passed in 9.57s`; python process list before vs after: identical (4 `console/mcp_server.py` only).
- git status after all runs equals the status at start; no file outside the expected set changed (artifact-map.md and telemetry/2026-09.jsonl were already modified at start). Only console/config change: verbs.toml.
- Verbs against a throwaway workspace copy (scratchpad `ws/`, ticket T-900): run-retry, claim, claim-release (non-holder, short reason, forced), review-round (rounds 1-4, approved, human_decision) all behaved per FR-18/22/24. T-020/T-021/T-022 tracker state never touched. Real repo: `run-list` showed 0 Runs, so `run-watch --confirm` was run once (no-op).

## Defects (found by the verifier 2026-10-02; D-A, D-B, D-C, D-E, D-F fixed by the fixer and re-verified by the orchestrator 2026-10-03)

- **D-A HIGH** console/server/run_watchdog.py:315-345 + run_sync.py:201-221 + verb_handlers.py:413-421. `run-watch` run from the CLI or MCP server process has an empty `agent_manager` registry and a fresh `_swept` set, so its first tick treats every ACTIVE chat Run as "no session at startup" and writes `interrupted/server_restart` (terminal, immutable). Repro (throwaway ws): create a `running` chat Run for chat "chat-live-in-server"; `python console/kanban.py verb run run-watch --confirm` -> `synced:1`; run-list shows `state: interrupted, end_reason: server_restart`. In production this would end healthy Runs owned by the server, and after the 60 s grace make their claims stale (BR-6). A scheduled_retry Run would likewise be resumed from the wrong process (double retry with the server thread; `_tick_lock` is per process). Agents reach `run-watch` through the MCP process, so this is reachable. Suggested remedy for the fixer: refuse (or no-op) the verb unless running inside the server process, or skip the startup sweep and retry execution when the registry is not the server's.
- **D-B MEDIUM** console/server/agent_manager.py (`_make_on_limit`, `runs.update` direct) vs run_watchdog.py:183-192 (only `_apply` escalates). A Run failed by the output cap has no escalation comment and no audit row; the `output_cap` row in ACTION_TABLE (run_watchdog.py:123) is unreachable. Violates the FR-17 intent and NFR-6.
- **D-C LOW/MEDIUM** unchanged console/server/tomlio.py:344 (`os.replace` with no retry) on Windows: concurrent unlocked readers (now more of them: claim_status, watchdog escalate, ready) make a claim/review write raise PermissionError. New concurrency tests fail intermittently (19/20 loop; 3 failures seen in about 14 runs). NFR-8 therefore not met on this host. Adjacent to TD-2; a retry-on-PermissionError in tomlio would fix it.
- Observations: failure_detail not scrubbed of credential-shaped values (NFR-9, low risk); `ticket.toml updated` still local `date.today()` (handled in stop_hook via `_updated_floor`); the new-test set is 31.5 s vs a 30 s target.

## Edge Cases Probed
- Real-process tree kill on Windows (root, child, grandchild) and the plain-kill control: both ran, no orphans.
- CLI run-watch with a live-looking Run (D-A), output-cap failure escalation (D-B), four-round review loop, forced release with short/valid reason, run-retry on unknown id, non-holder release.
- Not probed: empty/huge `failure_detail` through a real stream; cross-process lock contention beyond the above.

## Notes
- Not verified: new CI step on a real Windows runner (PENDING-CI, Q15); resetsAt units and the CLAUDECODE nesting guard against a real `claude` (Q14, no spawn allowed); human gate on claim-release force / review-round human_decision (Q12, needs agents.toml hand edit); phone alert (Q13).
- `verify cases`: no separate {T}-test-cases.md was produced; the FR checklists above are the case map.
- Reconcile drift (not fixed, verifier writes only this file): T-020-summary.md "Current State" still says build at T-020-03, status Open; artifact-map.md row says Open; D-1 in T-020-bugs.toml still open although the 3 tests pass; T-020-plan-iteration-log.md and T-020-release.md Links blocks list only 3 siblings (convention: all siblings). "[[link]]" in requirements-draft.md:22 is a legend, not a dead link.
- validate-artifacts: all 24 files in the ticket end with a Links block; every wikilink resolves.
- Ticket moved to lane `verify`. close-work not run.

## Re-verification 2026-10-03

After the fixer's changes: full suite `1867 passed`; `harness lint` 39 skills, 7 agents, 0 errors, 0 warnings; `git diff --stat -- console/static` empty. Not seen red first: the D-E scrub test (written before the fix but not run against the unfixed code). Still NOT VERIFIED: CI part of FR-9b/NFR-3 (the new workflow step has not run on a real Windows runner, Q15), FR-12e resetsAt units (Q14, no real claude), the human gate for claim-release force and review-round human_decision (Q12). Known intermittent Windows PermissionError thread warning from tomlio is mitigated by the retry but can still be seen as a warning on a loaded host.

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-decision-log]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
