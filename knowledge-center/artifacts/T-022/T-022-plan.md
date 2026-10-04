---
ticket: "T-022"
artifact: plan
structure: flat
---

# Plan: T-022

## Approach

Build `console/evals/` (three stdlib modules `scenario.py`, `grade.py`, `runner.py`) test-first, code and graders first, scenario authoring last. Grounding: [[T-022-decision-log]] `raw-transcript-fixtures` (fixtures are raw stream-json through the existing `Normalizer`; its three suspect behaviours are not fixed here, so graders must not depend on them), `deterministic-graders-no-judge`, `live-mode-safety-and-spend`, `failure-taxonomy-rules`; [[T-022-analysis]] F2-F5 (Normalizer drops `tool_result`, may duplicate `tool.start`, collapses usage to 0, `subtype="success"` can carry `is_error`).

**Structure: flat.** 13 tasks, one package, one linear dependency chain, no parallel components. `analyze-components` would produce a single-node graph, so the multi-layer chain is skipped on purpose (brief: flat up to about 12 tasks in one package; this is 13 because live mode is split in two). Task 11 onward is the only part that can be built in a different order of effort; the rest is strictly sequential.

**Hard ordering fact (T-020, T-021, T-022 build order).** T-022 is built LAST of the three. T-020 edits `.claude/agents/verifier.md` and `fixer.md` (FR-25), adds verbs `run-watch`, `run-retry`, `claim-release`, `review-round` and a stricter Run/claim model, and may add `procs.clean_env`/`kill_tree`. T-021 edits skill text (`plan`, `breakdown-tasks`, `close-work`), `console/config/assistant.md` and `console/server/harness_lint.py`. T-022's scenarios quote prompt text verbatim and the runner verifies the quotes (a drift detector by design). Therefore: (a) tasks 01-10 are code and test-only, use synthetic scenarios built in tests (tmp dirs), and quote no real prompt file; (b) the ten real scenarios, their 20 fixtures and all `[[source]]` quotes are authored in tasks 12-13 only, and each begins with "re-read the then-current prompt files and pin quotes to the final text"; (c) tasks 12-13 are held until T-020 and T-021 have shipped (check `knowledge-center/artifact-map.md`); building them earlier guarantees re-pinning rework.

**Shared-file discipline.** `verbs.toml`, `verb_handlers.py`, `kanban.py`, `verify.yml` and `console/README.md` are touched by other tickets. Every edit is an anchored `Edit` (never a rewrite), re-reading the file at task start. Any test over the verb list asserts membership (`{"evals-replay"} <= ids`), never equality.

**Rollback (CR-21).** Every change to a shared file is one anchored hunk, so the whole feature reverts by deleting `console/evals/`, the `test_evals_*.py` files and `evals_support.py`, the `evals-replay` row in `verbs.toml`, the `evals_replay` handler, the `evals` import line and block in `kanban.py`, the `verify.yml` step and the `console/README.md` pointer (FR-15's rollback sentence). No data migration, no schema, no `.claude/` file.

**Verification baseline.** Full suite `python -m pytest -o addopts="" -q`: 1445 collected, 1442 passed, 3 failed (date-rot in `console/tests/test_stop_hook.py`, fixed by T-020 FR-19; they will already be green if T-020 shipped). Each task is verified by its own test file plus "no new failure versus the baseline" on the full suite. Replay is the only eval mode ever run during build or verify; live is NEVER executed (no working Claude login, no price data, Q9/Q10 open).

## Slices

### Slice 1 - Foundations (tasks 01-03)
Package skeleton, Normalizer characterisation, transcript view, five graders. Everything else sits on these.

### Slice 2 - Definitions (tasks 04, 07)
Scenario schema, loader, provenance, subject checks, selection and `--changed`.

### Slice 3 - Replay, taxonomy, entry points (tasks 05, 06, 08)
Usage and failure classes, replay mode and results record, CLI block and the one read-only verb.

### Slice 4 - Live (tasks 09, 10)
Refusals, argv and prompt build, then the fake-spawn-tested driver. Never run for real.

### Slice 5 - Docs, CI, scenarios (tasks 11-13)
README and CI step first, then the ten scenarios and their fixtures with quotes pinned last, then the closing gate.

## Tasks

Estimates are planner judgement, not history. Basis for all: comparison with `console/server/harness_lint.py` (about 330 lines) plus `console/tests/test_harness_lint.py` (at least 226 lines), one builder session each, range stated per task. Every task: write the named tests first, see them fail for the right reason, then implement. Test helpers shared by the evals tests live in a new `console/tests/evals_support.py` (never `conftest.py`, a collision point).

### [x] T-022-01 - Package skeleton and Normalizer characterisation (1.5 h)
- **FR/AC:** FR-3 groundwork, FR-13 (collected with no `claude` on PATH), analyst finding that `Normalizer` has no tests.
- **Files:** NEW `console/evals/__init__.py` (docstring only), NEW `console/tests/test_evals_normalizer.py`, NEW `console/tests/evals_support.py` (raw-line builders: `init()`, `assistant_text()`, `assistant_tool()`, `result()`, `stream_tool()`).
- **Tests (named):** `TestNormalizerCharacterisation::test_assistant_tool_use_yields_tool_start_with_id_name_args` (`agent_normalize.py:280-282`), `::test_assistant_text_yields_text_done_with_text` (`:266-273`), `::test_exitplanmode_yields_tool_start_and_plan_event` (`:253-254`), `::test_result_yields_turn_end_with_is_error_and_subtype_keys` (`:313-323`, asserts keys present, never an exact dict, so T-020's additive fields do not break it), `::test_non_json_is_not_the_normalizers_job` (feed takes parsed dicts, `:96-97`). Documented-quirk class `TestSuspectBehaviours` (each docstring: "if this fails the Normalizer was fixed; graders stay valid, delete the matching guard in the view"): `::test_partial_then_complete_message_gives_two_tool_start_same_id` (`:223-230` vs `:280-282`), `::test_partial_path_text_done_is_empty_then_full_text_follows` (`:231-235`, `:273`), `::test_user_message_tool_result_is_swallowed_into_a_notice` (`:106-111`), `::test_missing_usage_collapses_to_zero_in_turn_end` (`:320-321`).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_normalizer.py`
- **Done-criteria:** nine tests green against UNMODIFIED `console/server/agent_normalize.py` (git diff shows no change there); each quirk is pinned with a docstring naming the grader behaviour it forces (de-duplicate by id, read text from non-empty `text.done`, never read `tool.result`, read usage from the raw `result`).
- **Basis:** 9 tests of 5-15 lines each, one 40-line helper module.
- **Depends on:** -

### [x] T-022-02 - Transcript view (2 h, range 1.5-2.5)
- **FR/AC:** FR-3 (all 4 AC), edge cases torn line / duplicate id.
- **Files:** NEW `console/evals/grade.py` (view part only: `TranscriptView`, `parse_lines`), NEW `console/tests/test_evals_view.py`.
- **Design (settled here so tests can name it):** `TranscriptView.feed(line)` is incremental (live mode reuses it); `from_lines(lines, strict)`; non-JSON line counted in `.noise`, and raises `GradingError` when `strict` (fixtures). Raw dicts are kept so the `result` object and usage are read raw. Calls de-duplicated by non-empty `id`, first wins, empty ids never merged; `ExitPlanMode` excluded from calls and its plan text from the `plan` event (de-duplicated by id). Text blocks = `text.done` events with non-empty `text`. `final` text = last non-empty assistant text block, else raw `result.result`, else empty (FR-3 does not define "final"; this is a planner interpretation, documented in README, see Risks R11). Disposition `no_result` when no `turn.end`.
- **Tests (named):** `test_same_tool_use_id_twice_yields_one_call`, `test_empty_ids_are_never_merged`, `test_exitplanmode_is_text_not_a_call`, `test_text_blocks_in_order_from_non_empty_text_done`, `test_partial_plus_complete_message_yields_text_once`, `test_final_text_prefers_last_block_then_raw_result`, `test_fixture_with_non_json_line_is_a_grading_error`, `test_live_mode_tolerates_non_json_and_counts_it`, `test_torn_last_line_in_live_is_ignored`, `test_no_turn_end_is_disposition_no_result`, `test_turn_end_exposes_is_error_and_subtype_and_raw_result`, `test_session_init_model_exposed`, `test_view_never_reads_tool_result_events` (a stream whose `tool.result` would change the outcome gives identical output).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_view.py console/tests/test_evals_normalizer.py`
- **Done-criteria:** 13 tests green; view survives each of the four suspect behaviours (duplicate `tool.start`, dropped `tool_result`, zero-collapsed usage, empty `text.done`) with identical output.
- **Basis:** about 120 lines of module, 13 small tests.
- **Depends on:** T-022-01

### [x] T-022-03 - Five deterministic graders (2.5 h, range 2-3)
- **FR/AC:** FR-4 (all 4 AC), BR-1, NFR Determinism.
- **Files:** `console/evals/grade.py` (add `KINDS`, `canonical(call)`, `run_check`, `grade`, `GRADER_VERSION = 1`), NEW `console/tests/test_evals_grade.py`.
- **Tests (named):** `test_canonical_bash_uses_command`, `test_canonical_edit_normalises_backslashes_and_notebook_path`, `test_canonical_skill_is_skill_space_args`, `test_canonical_other_tool_is_sorted_compact_json_ensure_ascii_false`, `test_call_matches_git_commit_in_bash_but_not_in_assistant_text`, `test_call_min_default_one_and_max_zero_forbids`, `test_first_call_passes_fails_and_no_call_fails`, `test_order_fails_when_before_has_no_earlier_first`, `test_order_passes_when_no_before_call_exists`, `test_text_scopes_final_all_any_and_present_false`, `test_text_all_includes_exitplanmode_plan`, `test_end_completed_fails_when_is_error_even_if_subtype_success`, `test_end_error_matches_is_error`, `test_no_turn_end_matches_neither_disposition`, `test_every_result_has_ok_detail_and_evidence_excerpt_le_200`, `test_grading_twice_is_byte_identical_json`, `test_grade_module_imports_no_time_random_socket_subprocess` (parse `grade.py` imports with `ast`), `test_regex_error_at_grade_time_is_a_grading_error`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_grade.py`
- **Done-criteria:** 18 tests green; `grade.py` still imports only `json`, `re`, `server.agent_normalize`; `GRADER_VERSION` constant exists and a test fails if the README is silent on it (added later in task 11).
- **Basis:** five small functions, 18 tests; dominant cost is the canonical-string table.
- **Depends on:** T-022-02

### [x] T-022-04 - Scenario schema, loader, provenance (3 h, range 2.5-3.5)
- **FR/AC:** FR-2 (all 5 AC), FR-11 (both AC, the second deferred to T-022-12 for the real workspace; the temp-copy half here), BR-1, BR-5, BR-12.
- **Files:** NEW `console/evals/scenario.py` (`Scenario`, `load_dir`, `load_file`, `validate`, `preflight`, `Problem(cls, reason, detail)`; imports `server.tomlio` and `evals.grade` constants only), NEW `console/tests/test_evals_scenario.py`.
- **Tests (named):** `test_loads_a_valid_scenario_with_source_and_checks`, `test_value_starting_with_a_quote_char_is_rejected_naming_file_and_key` (trailing `# comment` and single-quoted literal, both), `test_unknown_scenario_key_fails_as_grading`, `test_unknown_check_kind_fails`, `test_duplicate_check_id_fails`, `test_missing_fixture_fails` (pass or fail file absent), `test_invalid_regex_fails`, `test_mode_other_than_plan_fails`, `test_id_must_match_filename_and_pattern`, `test_prompt_over_800_chars_fails`, `test_vacuous_scenario_rejected_order_and_end_do_not_count`, `test_quote_with_newline_rejected`, `test_escaped_double_quote_inside_quote_value_round_trips` (covers the `"Bash(git commit:*)"` quote form, `tomlio._unescape`), `test_fail_checks_must_name_existing_check_ids`, `test_preflight_quote_missing_is_product_rule_moved`, `test_preflight_missing_source_file_is_product_rule_moved`, `test_preflight_reads_text_mode_so_crlf_matches`, `test_editing_quoted_sentence_in_temp_copy_fails_then_restore_passes`, `test_missing_subject_file_is_product_subject_missing` (agent:X, skill:S, core), `test_empty_and_does_nothing_transcripts_fail_a_synthetic_scenario` (the FR-2 AC4 helper `assert_not_vacuous(scenario)` that task 12 reuses over the real set), `test_scenario_sha256_is_newline_normalised`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_scenario.py`
- **Done-criteria:** 21 tests green; loader uses `tomlio` only (no `tomllib`); scenarios are top-level `[scenario]`, `[[source]]`, `[[check]]` per FR-2; every rejection names file and key; no real prompt file is read by any test (tmp repos only).
- **Basis:** loader about 200 lines; 21 tests; the vacuity helper reuses task 03.
- **Depends on:** T-022-03

### [x] T-022-05 - Usage and failure taxonomy (2 h, range 1.5-2.5)
- **FR/AC:** FR-7 (3 AC), FR-8 (3 AC), BR-4, BR-8, BR-11.
- **Files:** `console/evals/grade.py` (add `CLASSES`, `PRECEDENCE`, reason-code constants, `classify(view, results, limits)`, `primary(problems)`), `console/evals/runner.py` (NEW file; `usage_of(raw_result, repo_root)`, `totals(rows)`), NEW `console/tests/test_evals_taxonomy.py`, NEW `console/tests/test_evals_usage.py`.
- **Reason codes (settled so tests can name them):** grading `bad_scenario`, `bad_fixture`, `check_error`, `golden_failed`, `must_fail_passed`; infra `spawn_error`, `no_result`, `timeout`, `api_error`, `auth`, `rate_limit`, `overloaded`, `budget_cap`, `empty_turn`, `cli_error`; product `rule_moved`, `subject_missing`; model `behaviour`, `max_turns`, `tool_cap`.
- **Tests (named):** `test_auth_failure_shape_maps_to_infra_auth` (synthetic equivalent of the real failed-auth result: `is_error=true`, `subtype="success"`, `terminal_reason="api_error"`, message "Failed to authenticate", zero usage; written inline, never copied from `console/.cache`), `test_no_result_is_infra_no_result`, `test_error_max_budget_is_infra_budget_cap`, `test_empty_turn_is_infra_empty_turn`, `test_other_is_error_is_infra_cli_error`, `test_usable_completed_turn_failing_checks_is_model_behaviour`, `test_error_max_turns_is_model_max_turns`, `test_tool_calls_above_cap_is_model_tool_cap`, `test_golden_failed_and_must_fail_passed_are_grading`, `test_precedence_grading_over_infra_over_product_over_model`, `test_result_without_usage_key_is_unknown_not_zero`, `test_reported_zero_usage_and_cost_stay_zero_with_cost_source_backend`, `test_usage_block_with_one_key_missing_makes_only_that_key_unknown`, `test_missing_cost_with_known_tokens_falls_back_to_telemetry_price_table_else_unknown`, `test_totals_sum_known_only_and_flag_incomplete_with_unknown_count`, `test_replay_usage_renders_n_a`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_taxonomy.py console/tests/test_evals_usage.py`
- **Done-criteria:** 16 tests green; a test per class; precedence test uses crafted multi-condition input; `usage_of` reads only the raw `result` object (never `turn.end`); `telemetry.price` is the only pricing source and is called, never re-implemented.
- **Basis:** classifier about 80 lines, usage about 50 lines, 16 table-driven tests.
- **Depends on:** T-022-04

### [x] T-022-06 - Replay mode and results record (2.5 h, range 2-3)
- **FR/AC:** FR-5 (3 AC), FR-15 (2 AC), FR-7 replay half, BR-2, BR-6, BR-7.
- **Files:** `console/evals/runner.py` (add `replay(repo_root, scenarios, *, persist=True, cache_dir=None, scenarios_dir=None)`, `grade_transcript(path, scenario)`, `write_results`, `format_table`, `RUN_FIELDS`), NEW `console/tests/test_evals_replay.py`.
- **Behaviour:** per scenario: preflight (task 04), grade `{id}.pass.jsonl` (all checks pass) and `{id}.fail.jsonl` (parses cleanly, fails every `fail_checks` id), verdict and class per task 05. `--transcript PATH --scenario ID` mode grades one raw transcript (verdict pass/fail, class per FR-8, no fixture expectations). Output footer `replay proves the graders and fixtures, not live agent behaviour`. Cache dir default `resolve_rel(repo_root, "console/.cache/evals")`; tests always pass a tmp `cache_dir`. Run-level `complete` is true for replay (usage is `n/a`, not unknown), documented in README. `git_head` (FR-15) is read WITHOUT a process (challenge-plan CR-13): parse `.git/HEAD` (`ref:` line, then the loose ref file, then `packed-refs`; a `.git` file with `gitdir:` is followed; any failure gives `unknown`), because FR-5 AC1 forbids spawning a process in replay. The only replay path that runs a process is `--changed` (it must call `git`, task 07), and README says so.
- **Tests (named):** `test_replay_spawns_no_process_and_opens_no_socket` (patch `subprocess.Popen` and `socket.socket` to raise, plain replay only; `--changed` runs git, tested in task 07), `test_golden_that_fails_is_grading_and_exit_1`, `test_must_fail_fixture_that_passes_is_grading`, `test_must_fail_fixture_must_fail_every_declared_check_id`, `test_must_fail_fixture_with_torn_line_is_grading`, `test_footer_states_replay_proves_graders_not_live_behaviour`, `test_transcript_mode_grades_one_raw_transcript_without_fixture_expectations`, `test_results_json_has_every_run_and_scenario_field` (run_id, grader_version, git_head or `unknown`, backend, selected, complete; scenario, scenario_sha256, mode, verdict, class, reason, checks[], usage, model, duration_ms, transcript), `test_results_written_only_under_cache_evals` (tmp-tree snapshot before and after), `test_no_ticket_tracker_or_telemetry_file_changes`, `test_two_runs_get_separate_run_id_dirs`, `test_persist_false_writes_nothing`, `test_git_head_reads_dot_git_files_without_a_process` (loose ref, packed-refs, detached sha, `gitdir:` file) and `test_git_head_is_unknown_without_a_repo`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_replay.py`
- **Done-criteria:** 14 tests green using synthetic tmp scenarios and fixtures built from `evals_support`; no test needs the `git` executable.
- **Basis:** about 150 lines + 12 tests; fixture builders already exist from task 01.
- **Depends on:** T-022-05

### [x] T-022-07 - Selection, `--changed`, coverage (2 h, range 1.5-2.5)
- **FR/AC:** FR-9 (3 AC; the real-set halves of AC1 and AC2 are asserted in T-022-12/13), FR-1 AC3 logic, edge case unresolvable `--base`.
- **Files:** `console/evals/scenario.py` (add `select(scenarios, ...)`, `map_changed(paths)`, `changed_paths(repo_root, base, git=None)`, `coverage(repo_root, scenarios)`), NEW `console/tests/test_evals_selection.py`.
- **Mapping:** `.claude/agents/X.md` -> `agent:X`; `.claude/skills/S/**` -> `skill:S`; `CLAUDE.md`, `.claude/skills/harness-standards/**`, `.claude/settings.json` -> `core`; `console/evals/**` -> every scenario. `changed_paths` = union of `git diff --name-only <base>` and `git status --porcelain` (use `--untracked-files=all` so a new untracked skill file is listed by file); renames take the new path; the `git` callable is injectable and uses `procs.popen_kwargs()`.
- **Tests (named):** `test_touching_builder_md_selects_exactly_agent_builder_scenarios`, `test_skill_subdir_file_selects_skill_scenarios`, `test_core_files_select_core_scenarios`, `test_evals_dir_change_selects_every_scenario`, `test_selector_matching_zero_scenarios_is_refusal`, `test_changed_with_no_gated_file_is_nothing_to_gate`, `test_changed_files_with_no_covering_scenario_named_uncovered_and_exit_2_only_when_zero_selected`, `test_staged_unstaged_and_untracked_all_count` (fake git output for each), `test_porcelain_rename_takes_new_path`, `test_unresolvable_base_surfaces_git_error`, `test_coverage_counts_agents_and_lists_skills_without_scenario` (synthetic roster), plus one real-git test `test_real_git_repo_in_tmp_path` skipped via `skipif(shutil.which("git") is None)`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_selection.py`
- **Done-criteria:** 12 tests green; skill roster is `glob .claude/skills/*/SKILL.md` (same rule as `prompt_tokens._skills`, so reference bundles are not skills).
- **Basis:** about 110 lines + 12 tests.
- **Depends on:** T-022-04

### [x] T-022-08 - CLI block and `evals-replay` verb (2.5 h, range 2-3)
- **FR/AC:** FR-1 (4 AC), FR-12 (2 AC), BR-3, BR-10.
- **Files:** `console/evals/runner.py` (add `add_parser(sub)` and `cmd(args, repo_root)` returning an exit code via `sys.exit`; argparse for `list`, `replay`; `--json`, `--scenario` repeatable, `--agent`, `--skill`, `--all`, `--changed`, `--base`, `--transcript`, `--coverage`), `console/kanban.py` (ONE new import line after line 25 plus ONE block before `return parser` in `build_parser`, both anchored Edits; do NOT touch the line-19 import), `console/config/verbs.toml` (one `[[verb]]` row `evals-replay`, anchored after the `harness-lint` row), `console/server/verb_handlers.py` (one handler appended after `harness_lint_verb`, lazy `from evals import runner` inside it), NEW `console/tests/test_evals_cli.py`, NEW `console/tests/test_evals_verb.py`.
- **Decisions:** handlers run through MCP and `verb run --set k=v` receive STRINGS (`mcp.py:89` types every argument as string; `agent_models` coerces the same way), so `changed` is coerced with `str(changed).lower() in ("1","true","yes","on")`, so `changed="false"` is False. The verb calls replay with `persist=False` (it is advertised read-only). Exit code 2 is raised with `sys.exit(2)` from the handler, because `kanban.main` turns `ValueError` into exit 1 (`kanban.py:1040-1046`). All output ASCII; table `id  verdict  class  checks  usage`.
- **Tests (named):** `test_list_prints_every_scenario_id_subjects_and_mode_exit_0`, `test_replay_exit_0_on_healthy_set`, `test_replay_exit_1_when_a_golden_fixture_fails`, `test_replay_unknown_scenario_exit_2`, `test_changed_nothing_to_gate_exit_0`, `test_changed_uncovered_exit_2`, `test_json_flag_prints_the_results_record`, `test_output_is_ascii_even_when_evidence_excerpt_is_not` (escape with `backslashreplace`, so a cp1252 Windows console cannot raise `UnicodeEncodeError`), `test_build_parser_wires_evals_list_replay_and_json` (`kanban.build_parser().parse_args([...])`; never `kanban.main`, which loads `.env` and the real root), `test_non_pass_prints_scenario_check_class_reason_evidence`, `test_only_verb_handlers_imports_evals_among_server_modules` (git-free: scans `console/server/*.py` for `import evals` / `from evals`, expecting hits only in `verb_handlers.py`; a diff-stat check is in task 13), verb file: `test_registry_resolves_evals_replay_handler`, `test_verb_run_returns_same_verdicts_as_cli`, `test_changed_string_false_is_false_and_string_true_is_true`, `test_verb_list_contains_evals_replay_by_membership_not_equality`, `test_no_verb_can_spawn_claude_for_evals` (no verb id or handler name containing `evals` other than `evals-replay`; no `needs_confirm` on it), `test_mcp_tool_list_includes_evals_replay` (membership, `mcp.tool_list`).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_cli.py console/tests/test_evals_verb.py console/tests/test_mcp.py console/tests/test_verbs.py` then `python console/kanban.py evals list` (exit 0).
- **Done-criteria:** 18 new tests green; `test_mcp.py` and `test_verbs.py` unchanged and still green; `git diff --stat` shows only the five named files touched in `console/server`, `console/config`, `console/kanban.py`; `evals list` with zero scenarios prints an explicit "0 scenarios" and exits 0 (real set arrives in 12-13).
- **Basis:** about 140 lines argparse and table, 16 tests; the three shared-file edits are small anchored hunks.
- **Depends on:** T-022-06, T-022-07

### [x] T-022-09 - Live mode: refusals, argv, plan print (2 h, range 1.5-2.5)
- **FR/AC:** FR-6 AC1, AC2, AC5; refusal half of AC4; BR-3.
- **Files:** `console/evals/runner.py` (add `live_plan`, `build_live_command`, `refusals`; add the `live` subparser in `add_parser`), NEW `console/tests/test_evals_live_setup.py`.
- **Behaviour:** `kanban.py evals live <selector> --confirm [--model M] [--max-budget-usd N]`. Without `--confirm`: print the plan (scenarios, backend, model, mode `plan`, caps `180 s / 25 calls / $0.50`, `cost: UNKNOWN until run`) and exit 2 with no spawn. Refused (exit 2) when env `CI` is truthy (`1`, `true`, `yes`, any non-empty value other than `0`/`false`), when no selector and no `--all`, when preflight fails, when the backend is not `stream_json`. argv = `Backend.session_argv(mode="plan", model=..., persona=...)` plus `["--max-budget-usd", "%g" % n]`; prompt = `backend.compose_prompt(prompt, skill, persona, repo_root)`. A `claude` that is not on PATH raises `FileNotFoundError` from `_exe()`: recorded as `infra/spawn_error` in task 10, not a refusal.
- **Tests (named):** `test_live_without_confirm_exits_2_and_fake_spawn_never_called`, `test_live_with_ci_set_exits_2_even_with_confirm`, `test_ci_zero_or_false_does_not_count_as_ci`, `test_live_without_selector_or_all_exits_2`, `test_live_preflight_failure_exits_2_before_spawn`, `test_session_argv_called_with_mode_plan_only` (spy), `test_scenario_cannot_request_another_mode` (loader already rejects; assert argv anyway), `test_argv_carries_permission_mode_plan_agent_and_max_budget_default_0_50`, `test_model_flag_passed_through_and_omitted_when_empty`, `test_prompt_built_by_compose_prompt_with_skill_and_persona`, `test_plan_print_says_cost_unknown_until_run`, `test_non_stream_json_backend_refused`. Use the `on_path` pattern (`monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "/usr/bin/" + c)`, `test_agent_backends.py:57-66`) and copy the shipped `agents.toml` into the tmp repo for a real `claude` row.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_live_setup.py`
- **Done-criteria:** 12 tests green; on every refusal path `agent_manager.create`, `telemetry.record_turn`, `notify.send` and the fake `spawn` are patched to fail the test if called; nothing runs `claude`.
- **Basis:** about 90 lines + 12 tests.
- **Depends on:** T-022-08

### [x] T-022-10 - Live driver, tested only with a fake `spawn` (3 h, range 2.5-3.5)
- **FR/AC:** FR-6 AC3, AC4, AC6 (AC1, AC2, AC5 re-asserted on the success path), FR-15 live half (raw transcript, one `evals.live` audit record), FR-8 AC3 (one attempt), BR-7, BR-8, edge case concurrent runs.
- **Files:** `console/evals/runner.py` (add `run_live(repo_root, scenarios, *, spawn=subprocess.Popen, timeout=180, stop_grace=5, model="", max_budget_usd=0.50, env=None, cache_dir=None, run_id=None)`, `_drive(proc, view, ...)`, `_end(proc, grace)`), `console/tests/evals_support.py` (add `FakeProc`: scripted stdout lines, optional block-forever, records `stdin` writes, `terminate`/`kill` calls, can ignore terminate), NEW `console/tests/test_evals_live.py`.
- **Behaviour:** spawn argv from task 09 with `stdin=PIPE, stdout=PIPE, stderr=STDOUT` (stderr lines become counted noise, useful as evidence of a CLI or auth error), `text=True, encoding="utf-8", errors="replace", bufsize=1`, `creationflags=procs.no_window_flags(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))` as `agent_session.py:410-417`. Write ONE `{"type":"user","message":{"role":"user","content":[{"type":"text","text":wire}]}}` line (`agent_session.py:445-447`). A reader thread feeds a `queue.Queue`; the driver reads lines into the incremental view (task 02) until `result`, enforcing the wall-clock timeout and `max_tool_calls` after each line. End: close stdin, wait `stop_grace`, then `terminate()`, wait, then `kill()` (`agent_session.py:476-492`). Build-time check: re-read `console/server/procs.py` and `LiveSession.stop`; if T-020 added `procs.kill_tree` / `procs.clean_env`, call them the same way `LiveSession` does (`getattr(procs, "kill_tree", None)`), keeping the AC behaviour. Env: `procs.clean_env()` when it exists, else inherited as `LiveSession` does. Writes `{scenario}.raw.jsonl` and `results.json` under the run dir; exactly one `audit.record(repo_root, "evals.live", target=run_id, detail={scenarios, model, backend, outcome, run_id})` per invocation, never transcript text. `server/audit.py` is NOT edited (FR-1 AC4); `evals.live` is therefore not in `audit.ACTIONS`, so `kanban.py audit --action evals.live` is not an accepted filter; the unfiltered `audit` listing shows it (documented limitation, Risks R13).
- **Tests (named):** `test_fake_spawn_replaying_fixture_is_graded_exactly_as_replay_and_record_mode_is_live`, `test_live_path_never_calls_agent_manager_create_record_turn_or_notify_send` (patched to fail), `test_live_creates_no_worktree_run_or_chat_entry` (tmp-tree snapshot: no `console/.cache/agent-chats`, no runs, no worktree dir, no telemetry file), `test_process_that_never_emits_result_is_terminated_at_timeout_as_infra_timeout` (timeout injected at 0.2 s), `test_tool_calls_over_cap_terminate_as_model_tool_cap`, `test_spawn_oserror_is_infra_spawn_error`, `test_claude_not_on_path_is_infra_spawn_error`, `test_spawn_receives_no_window_creationflags_pipes_and_one_user_json_line`, `test_end_closes_stdin_then_terminates_then_kills_after_grace`, `test_stop_uses_kill_tree_when_procs_provides_it` (monkeypatched attribute), `test_behaviour_failure_is_scored_not_retried_one_spawn_per_scenario`, `test_usage_unknown_without_result_usage_and_known_when_reported`, `test_exactly_one_evals_live_audit_record_without_transcript_text`, `test_raw_transcript_written_only_under_the_run_dir`, `test_concurrent_runs_get_separate_run_id_dirs`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_live.py console/tests/test_evals_live_setup.py` then the full suite `python -m pytest -o addopts="" -q` (no new failures versus baseline).
- **Done-criteria:** 15 tests green; `grep -n "Popen" console/evals/runner.py` shows `spawn` is the only spawn path and its default is the only `subprocess.Popen` reference; NO test and NO command in this task runs `evals live --confirm` against the real `claude` (live smoke stays NOT RUN, Q9/Q10 open).
- **Checkpoint (CR-16):** half (a) = spawn, drive, end, grade (tests 1-9, suite green, commit boundary); half (b) = persistence, audit, side-effect and concurrency guards (tests 10-15). If (a) alone passes 2 h, stop there and open (b) as T-022-10b; both halves leave the suite green.
- **Basis:** about 170 lines (thread, queue, teardown) + `FakeProc` + 15 tests; the riskiest session of the ticket, hence the top of the range.
- **Depends on:** T-022-09

### [x] T-022-11 - README, fixture scan, deferred list (2 h, range 1.5-2)
- **FR/AC:** FR-14 (2 AC), FR-13 fixture scan AC, FR-10 Deferred AC, FR-2 documentation of doubled backslashes.
- **Files:** NEW `console/evals/README.md`, NEW `console/tests/test_evals_docs.py`, NEW `console/tests/test_evals_fixture_scan.py`.
- **README content (checklist):** format with doubled backslashes, no trailing comments, single-line prompt and quote; the five check kinds; the canonical call string; `final` text definition (R11); taxonomy and precedence; reason codes; what replay does NOT prove and that one live pass is not reliability; usage UNKNOWN rule; how to add a scenario (steps, and re-pin the quote in the SAME change that edits the cited rule); `--changed` gating; `Normalizer` coupling (graders read only calls, text, `turn.end`; tool results ignored); `GRADER_VERSION` bump rule; promotion of a live transcript to a fixture is manual and scrubbed; **Deferred:** claim before work, stop on a claim conflict, reason (no prompt states the rule, BR-9), natural moment (T-020 item 5). The README sentence about who runs `evals replay --changed` reads "any change that edits a gated file runs it in its verify step"; see Risks R14 for why T-020/T-021 are not named.
- **Tests (named):** `test_every_check_kind_in_grade_py_appears_in_readme`, `test_readme_states_replay_does_not_prove_live_behaviour_and_one_live_pass_is_not_reliability`, `test_readme_mentions_grader_version_and_deferred_claim_scenarios`, NFR guards (CR-14): `test_evals_package_never_references_env_files_or_dotenv` (scans `console/evals/*.py`; the `CI` check and the child-env hand-off are the only `environ` uses), `test_evals_package_is_exactly_three_modules_and_stdlib_only` (file set equals `__init__`, `scenario`, `grade`, `runner`; imports are stdlib, `server.*` or `evals.*`), fixture scan: `test_scan_flags_user_profile_paths` (`C:\Users\`, `/Users/`, `/home/`), `test_scan_flags_key_like_strings` (`sk-` or `ghp_` plus 16 word characters), `test_scan_flags_openrouter_and_bearer`, `test_committed_fixtures_are_clean` (real `console/evals/fixtures`; passes on an empty dir for now, the 20-file floor is added in task 13).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_evals_docs.py console/tests/test_evals_fixture_scan.py`
- **Done-criteria:** 9 tests green; README contains no quote or rule text from any prompt file (so it cannot itself drift).
- **Basis:** about 150 lines of prose, two short test modules.
- **Depends on:** T-022-10

### [x] T-022-12 - Scenarios 1-5, fixtures, quote pinning (3 h, range 2.5-3.5) - HOLD until T-020 and T-021 have shipped
- **FR/AC:** FR-10 (scenarios 1-5 of Appendix A), FR-11 AC2 (real-workspace guard), FR-2 AC4 over the real set, FR-9 AC3 real, FR-13 real-workspace test.
- **Step 0 (mandatory, first):** re-read the THEN-CURRENT text of `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/{analyst,harness,verifier,builder,fixer}.md`, `.claude/skills/{trace-context,handoff,progress-tracker,questions}/SKILL.md` and `console/config/verbs.toml` (for the MCP names in fixtures), run `grep -n` for every Appendix A quote, and pin each `[[source]] quote` to the final text. Known drift candidates: `verifier.md` step 10 (T-020 FR-25 adds `review-round`; prefer the output-contract quote `Blockers: {count} (each with file:line evidence)`; the golden-pass fixture for scenario 3 includes a `mcp__console__review-round` call if the final step 10 requires one, and no check forbids it), `progress-tracker` (T-021 touches the `blocked` contract), `CLAUDE.md` (T-021 doc-drift audit). If a rule is gone or changed meaning, STOP: do not weaken a check and do not invent a rule; hand back to the orchestrator for an `evolve` of Appendix A (BR-9: a rule no prompt states gets no scenario and moves to README Deferred).
- **Files:** NEW `console/evals/scenarios/{trace-context-first,stop-on-failed-gate,blocker-carries-evidence,no-work-exit,never-hand-edit-ticket-toml}.toml`, NEW ten fixtures `console/evals/fixtures/{id}.{pass,fail}.jsonl` (raw stream-json, synthetic ticket `EV-001`, no real paths or secrets; at least one fixture uses the partial-message envelope `stream_event` plus complete `assistant` message and one carries a `user` `tool_result` message, so the de-duplication and ignore-results behaviour are exercised), NEW `console/tests/test_evals_real_set.py`.
- **Tests (named, parametrised over the scenario ids found on disk, so they stay green at task 12 and 13):** `test_real_scenarios_load_and_preflight_clean` (real workspace, `REAL_WORKSPACE` pattern of `test_harness_lint.py:210`), `test_real_replay_is_green_and_exit_0`, `test_every_real_scenario_fails_empty_and_does_nothing_transcript` (reuses task 04 helper), `test_must_fail_fixtures_fail_exactly_their_declared_checks`, `test_each_scenario_has_a_source_a_positive_check_and_existing_subjects`, `test_no_committed_scenario_quotes_a_file_that_is_missing`.
- **Verify:** `python console/kanban.py evals replay` (exit 0, record the table) and `python -m pytest -o addopts="" -q console/tests -k evals`
- **Done-criteria:** 5 scenarios and 10 fixtures committed; replay green; each must-fail fixture trips every declared `fail_checks` id and nothing else is asserted about it; Appendix A regexes copied exactly with doubled backslashes; no fixture matches the scan of task 11.
- **Basis:** 5 TOML files of 25-40 lines, 10 fixtures of 5-20 lines, one parametrised test module.
- **Depends on:** T-022-11 and (external) T-020, T-021 shipped

### [x] T-022-13 - Scenarios 6-10, CI step, README pointer, closing gate (2.5 h, range 2-3) - HOLD as task 12
- **FR/AC:** FR-10 (all 4 AC), FR-9 AC2 (7/7 agents), FR-13 AC1 and AC3, FR-1 AC4, FR-6 manual AC (recorded NOT RUN), NFR Performance, BR-10.
- **Step 0 (mandatory, first):** repeat the re-read and quote pinning of task 12 for `CLAUDE.md`, `.claude/settings.json`, `.claude/agents/{deployer,harness,planner,builder}.md`, `.claude/skills/{do,evolve}/SKILL.md`. Scenario 6 quotes `.claude/settings.json` `"Bash(git commit:*)"`: the escaped-quote form is covered by a loader test; an unquoted substring `Bash(git commit:*)` is acceptable if the final text still contains it.
- **Files:** NEW scenarios `{no-commit-unasked,post-freeze-change-uses-evolve,deploy-is-ask-gated,planner-refuses-unfrozen,evolve-logs-before-editing}.toml`, NEW ten fixtures, `console/tests/test_evals_real_set.py` (add `test_ten_starter_ids_present_by_membership`, `test_at_least_twenty_fixtures`, `test_coverage_reports_7_of_7_agents_and_names_uncovered_skills` asserting `len(uncovered) == total_skills - len(covered)` and the six covered skills by membership, never a literal 33), `console/tests/test_evals_fixture_scan.py` (raise the floor to 20 files), `.github/workflows/verify.yml` (one step `Eval replay (free, no model)` running `python console/kanban.py evals replay` appended to the `harness` job after `Lint skills and agents`, anchored Edit; added per the planning brief, optional because FR-13 states the existing pytest job already collects the tests: delete the step if the user prefers strict FR-13), `console/README.md` (short pointer to `console/evals/README.md`, anchored Edit; done last because T-021's doc-drift audit edits this file).
- **Closing gate commands (record outputs in progress.md via `progress-tracker`):** `time python console/kanban.py evals replay` (NFR: 5 s or less), `python console/kanban.py evals list --coverage` (7/7 agents; report the uncovered skill count, expected 33 of 39 today), `python console/kanban.py evals replay --changed` (exit code and selection), `python console/kanban.py harness lint` (0 errors, no new warnings vs the pre-T-022 baseline (T-021 adds ~20), 39 skills, 7 agents), `python -m pytest -o addopts="" -q console/tests -k evals`, full suite `python -m pytest -o addopts="" -q` (no new failures versus baseline), `git diff --stat` (no change under `.claude/`, no new agent or skill, no change to any ticket, tracker or telemetry file, `console/server` changed only in `verb_handlers.py`). The FR-6 manual smoke is recorded **NOT RUN** (no Claude login, no price data; Q9, Q10); the verifier copies that status into `T-022-verification.md`.
- **Verify:** the closing gate commands above.
- **Done-criteria:** 10 scenarios, 20 fixtures, replay green and within 5 s, harness lint 0/0, full suite no worse than baseline, NOT RUN line recorded. Portability (CR-15): local Python is 3.14 but CI runs 3.11 and 3.13, so `grep` the new modules and tests for 3.12-only syntax (same-quote nested f-strings, `type` statements, PEP 695 generics, `itertools.batched`) before finishing; the CI result for py3.11 stays PENDING until pushed and is reported as such. Report honestly if any command was not run.
- **Basis:** same shape as task 12 plus a 6-command gate.
- **Depends on:** T-022-12

## Acceptance-criterion map (51 criteria)

| FR | AC | Task(s) |
|---|---|---|
| FR-1 | list exits 0 with ids, subjects, mode | 08 (real set 13) |
| FR-1 | replay exit 0 / 1 / 2 | 08 (real set 12) |
| FR-1 | `--changed` nothing-to-gate 0, uncovered 2 | 07, 08 |
| FR-1 | only `verb_handlers.py` changes in `console/server`; one `evals` block; ASCII | 08, 13 (diff stat) |
| FR-2 | quote-start value rejected, file and key named | 04 |
| FR-2 | unknown key / kind / duplicate id / missing fixture / bad regex / mode is `grading` | 04 |
| FR-2 | vacuous scenario rejected | 04 |
| FR-2 | every scenario fails empty and does-nothing transcript | 04 (helper), 12, 13 |
| FR-2 | newline quote rejected | 04 |
| FR-3 | duplicate tool_use id is one call | 02 |
| FR-3 | graders never read `tool.result` | 02 |
| FR-3 | non-JSON fixture line is `grading`, live tolerates | 02 |
| FR-3 | no `turn.end` is `no_result` | 02 |
| FR-4 | byte-identical grading, no `time`/`random`/`socket`/`subprocess` | 03 |
| FR-4 | `git commit` call matches, same text does not | 03 |
| FR-4 | `order` fail and pass cases | 03 |
| FR-4 | `end completed` fails on `is_error` with `subtype=success` | 03 |
| FR-5 | no process, no socket in replay | 06 |
| FR-5 | failing golden / passing must-fail is `grading`, exit 1 | 06 |
| FR-5 | one-line replay disclaimer | 06 |
| FR-6 | no `--confirm` exit 2, spawn never called | 09 |
| FR-6 | `CI=1` exit 2, no spawn | 09 |
| FR-6 | fake spawn graded as replay, `mode="live"` | 10 |
| FR-6 | never `agent_manager.create`/`record_turn`/`notify.send`; no worktree, Run, chat | 09 (refusal path), 10 |
| FR-6 | `session_argv` with `mode="plan"` only | 09 |
| FR-6 | timeout `infra/timeout`; over cap `model/tool_cap` | 10 |
| FR-6 | manual smoke, recorded NOT RUN | 13 (recorded; run is not performed) |
| FR-7 | no `usage` key renders UNKNOWN | 05 |
| FR-7 | reported zero stays zero, `cost_source="backend"` | 05 |
| FR-7 | two-scenario run with one unknown is partial | 05 |
| FR-8 | one test per class, auth shape is `infra/auth` | 05 |
| FR-8 | precedence | 05 |
| FR-8 | no retry of behaviour failures | 10 |
| FR-9 | `builder.md` selects exactly `agent:builder` scenarios | 07 (real set 12) |
| FR-9 | `list --coverage` 7/7 agents, names uncovered skills | 07, 13 |
| FR-9 | missing subject file is `product` | 04, 07 |
| FR-10 | 10 scenarios + 20 fixtures, replay green, coverage 7/7 and 33 skills | 12, 13 |
| FR-10 | each scenario cites a quote that is a substring | 12, 13 |
| FR-10 | must-fail fixtures trip declared checks, no empty pass | 12, 13 |
| FR-10 | claim scenarios in README Deferred | 11 |
| FR-11 | temp-copy edit fails preflight, restore passes | 04 |
| FR-11 | real-workspace guard test passes | 12, 13 |
| FR-12 | registry resolves handler, `verb run` equals CLI | 08 |
| FR-12 | no verb can spawn `claude` for evals | 08 |
| FR-13 | `pytest -k evals` passes with no network, no `claude` | 01 to 13 (each task), 13 gate |
| FR-13 | fixture scan fails on planted strings | 11 |
| FR-13 | harness lint 0/0, 7 agents, 39 skills | 13 |
| FR-14 | README states replay limits and one live pass | 11 |
| FR-14 | test: every check kind in README | 11 |
| FR-15 | `results.json` validates | 06 (live fields 10) |
| FR-15 | nothing written outside `console/.cache/evals/` except audit | 06, 10, 13 (diff stat) |

Coverage: 51 of 51 criteria mapped; the only one not executed in this ticket is the FR-6 manual smoke (mapped to a task that records NOT RUN).

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-022-01 - Package skeleton, Normalizer characterisation | 1.5 h | 9 tests + helper module |
| T-022-02 - Transcript view | 2 h | about 120 lines + 13 tests |
| T-022-03 - Five graders | 2.5 h | five functions + 18 tests |
| T-022-04 - Scenario schema, loader, provenance | 3 h | about 200 lines + 21 tests |
| T-022-05 - Usage and taxonomy | 2 h | about 130 lines + 16 tests |
| T-022-06 - Replay mode and results record | 2.5 h | replay + record + 14 tests |
| T-022-07 - Selection, `--changed`, coverage | 2 h | git mapping + 12 tests |
| T-022-08 - CLI block and `evals-replay` verb | 2.5 h | argparse + table + verb + 18 tests |
| T-022-09 - Live refusals, argv, plan print | 2 h | 11 tests |
| T-022-10 - Live driver with fake spawn | 3 h | thread reader + teardown + 12 tests |
| T-022-11 - README, NFR guards, fixture scan | 2 h | doc + 9 tests |
| T-022-12 - Scenarios 1-5, fixtures, pin | 3 h | 5 TOML + 10 fixtures |
| T-022-13 - Scenarios 6-10, pin, closing gate | 2.5 h | 5 TOML + 10 fixtures + gate |
| **Total** | **30.5 h** (range 25-38 h) | sum of task estimates; no history behind it |

### Acceptance criterion coverage

Requirements carry 51 acceptance criteria (FR-1:4, FR-2:5, FR-3:4, FR-4:4, FR-5:3, FR-6:7, FR-7:3, FR-8:3, FR-9:3, FR-10:4, FR-11:2, FR-12:2, FR-13:3, FR-14:2, FR-15:2). Mapping: the section "Acceptance-criterion map" above (51 of 51 mapped).

## Risks

Scored likelihood x impact. High x high: 0. Every med x med or higher has a mitigation. Source is the artifact line that surfaced it.

| ID | Risk | L | I | Mitigation | Owner | Source |
|----|------|---|---|-----------|-------|--------|
| R1 | Quote drift: T-020 (verifier.md step 10, fixer.md) and T-021 (plan, breakdown-tasks, close-work, `blocked` contract, assistant.md, harness_lint, possibly CLAUDE.md and README) edit text the scenarios quote | High | Med | T-022 is built last; tasks 01-11 quote no real file; tasks 12-13 start by re-reading and pinning, and are HELD until T-020 and T-021 have shipped; drift-sensitive scenarios named (1, 3, 5, 7); preflight turns any later drift into `product/rule_moved` | Builder | requirements Interactions table, edge cases; [[T-022-critique-report]] CR-12 |
| R2 | A rule a scenario encodes changed meaning (for example verifier now calls `review-round` first), not just wording | Med | Med | Task 12/13 step 0: stop and ask for an `evolve` of Appendix A rather than weaken a check; golden fixture for scenario 3 follows the final protocol | Builder | T-020 FR-25 |
| R3 | Normalizer quirks (duplicate `tool.start`, dropped `tool_result`, zero-collapsed usage, empty `text.done` on the partial path) corrupt graders | Med | Med | Task 01 characterisation tests BEFORE reliance; task 02 view is independent of all four; usage read from the raw `result` | Builder | analysis F2-F4; `agent_normalize.py:106-111,223-235,280-289,313-323` |
| R4 | Hand-authored fixtures do not match the real CLI envelope (envelope with partial messages, `tool_result` placement, `plan`-mode `tool_use` all unconfirmed) | Med | Med | Fixtures include the partial-message envelope and a `user` `tool_result` line; replay claims to prove graders only (BR-6, README); TD-1 confirms against a real stream; first authorised smoke tunes prompts, never checks | Builder | context-snapshot section 6 |
| R5 | Live cannot be exercised here (Q9, Q10 open): FR-6 smoke AC unobservable | High | Low | Accepted (CR-6): fake `spawn` covers logic; smoke recorded NOT RUN; nothing in any task runs `evals live --confirm` | Verifier | CR-6, CR-9, CR-10 |
| R6 | `plan` mode may emit no tool call, so `first_call` fails as `model` (known confound) | Med | Med | Accepted (CR-9): tuned by prompt wording at the first smoke, never by weakening a check; replay unaffected | Owner at smoke | CR-9 |
| R7 | `tomlio` subset traps: trailing `# comment` corrupts a value, single quotes, backslashes, escaped `"` inside a quote value | Med | Med | Loader rejects quote-initial values naming file and key (task 04); escaped-quote round-trip test; README documents doubled backslashes | Builder | analysis TOML-subset bullet; `tomlio.py:30-31` |
| R8 | Process teardown on Windows: `terminate()` does not kill grandchildren, orphan `claude` could linger after a timeout | Med | Med | Task 10 mirrors `LiveSession.stop` and uses `procs.kill_tree` when T-020 has landed it; stdin closed first; timeouts and teardown tested with `FakeProc`; real orphan test is part of the not-run smoke | Builder | `agent_session.py:476-492`; T-020 FR-5, FR-9 |
| R9 | Merge conflicts on shared files (`kanban.py`, `verbs.toml`, `verb_handlers.py`, `verify.yml`, `console/README.md`) with T-020 and T-021 | Med | Low | Anchored Edits only, re-read at task start, `kanban.py` import on its own new line (not line 19), `console/README.md` pointer last | Builder | brief; `kanban.py:19,1023` |
| R10 | A test asserting the exact verb list breaks when other tickets add verbs | Low | Med | All new tests assert membership; existing exact-name tests inspected (`test_mcp.py:137` is a fixture-registry, `:375` uses subset) | Builder | grep of `console/tests` |
| R11 | FR-3 says "final text" without defining it | Med | Low | Decided in task 02: last non-empty assistant text block, else raw `result.result`; documented in README (task 11); tests in task 02. If the user prefers the opposite order it is a one-line change in `grade.py` | Planner / Builder | requirements FR-3 |
| R12 | Verb handler arguments arrive as strings (MCP types all as string), so `changed="false"` would be truthy | Med | Med | Handler coerces with the `agent_models` convention; test in task 08 | Builder | `mcp.py:89`; `verb_handlers.py:94` |
| R13 | `evals.live` is not in `audit.ACTIONS` (editing `audit.py` would violate FR-1 AC4), so `kanban.py audit --action evals.live` is rejected by argparse choices | Low | Low | Accepted: `audit.record` does not validate actions (`audit.py:94-119`); the unfiltered listing shows the record; documented in README | Builder | `kanban.py:917`; `audit.py:44` |
| R14 | Requirements FR-14 and the Interactions table say T-020 and T-021 run `evals replay --changed` in their verify step, but T-022 is built after both, so that cannot happen | High | Low | README wording generalised (any change editing a gated file); tasks 12-13 act as the retroactive check for T-020/T-021 edits; flagged to the orchestrator for an `evolve` of FR-14 if the build order stands | Orchestrator | requirements FR-14; brief ordering fact |
| R15 | `--changed` assumes `repo_root` is the git top-level; otherwise paths gain a prefix and no file maps (false "nothing to gate") | Low | Med | True in this workspace; documented; the git-backed test uses a tmp repo whose root is the top-level | Builder | design |
| R16 | CI baseline: 3 date-rot failures in `test_stop_hook.py` until T-020 FR-19 ships | Med | Low | Each task verified by its own files plus "no new failure versus baseline" on the full suite | Builder | brief |
| R17 | `Backend.session_argv` raises `FileNotFoundError` when `claude` is not on PATH, including in CI and tests | High | Low | Tests patch `agent_backends.shutil.which` (`test_agent_backends.py:57-66`); real absence is `infra/spawn_error` | Builder | `agent_backends.py:501-506` |
| R19 | Local Python is 3.14, CI is 3.11 and 3.13: a 3.12+-only construct passes locally and fails CI | Med | Med | Task 13 grep for 3.12-only syntax; no `tomllib`; py3.11 result reported PENDING until CI runs | Builder | NFR Portability; `verify.yml:30` |
| R20 | T-022 cannot close before T-020 and T-021 ship (tasks 12-13 are held) | Med | Med | Tasks 01-11 (about 21.5 h of 30.5 h) are independent and can be built and verified first; if T-021 slips the orchestrator chooses: wait, or build 12-13 early and re-pin later (about 1 h rework per drifted quote) | Orchestrator | brief ordering fact |
| R18 | Estimates have no history behind them | High | Low | Ranges stated; total 25-38 h; re-forecast after task 04 (the first task with real friction) | Planner | estimate basis |

## Dependencies
- Blocks: -
- Blocked by: [[T-020-summary]] (verifier/fixer prompts, new verbs, Run/claim model, possibly `procs.kill_tree`/`clean_env`) and [[T-021-summary]] (skill text, `assistant.md`, `harness_lint.py`) for tasks 12-13 only. Tasks 01-11 have no cross-ticket dependency.

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements]] · [[T-022-user-stories]] · [[T-022-decision-log]] · [[T-022-critique-report]] · [[T-022-plan-iteration-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
