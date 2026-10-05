---
ticket: "T-024"
artifact: verification
---

# Verification: T-024

Verified 2026-10-05 by the orchestrating session. Two delegated runs (the harness that built this ticket, then a verifier) both stalled before writing this file. Every row below was re-run by hand; the subagents' status claims are not used as evidence.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1a | `clean_env(repo)` sets `CONSOLE_REPO_ROOT` to the absolute repo path | PASS | `console/tests/test_procs_anchor.py::TestCleanEnvAnchor::test_ac1a_the_main_root_is_set_as_an_absolute_path` |
| AC-1b | `clean_env(None)` adds nothing; an ambient value passes through | PASS | `console/tests/test_procs_anchor.py::TestCleanEnvAnchor::test_ac1b_without_a_root_nothing_is_added_and_ambient_passes_through` |
| AC-1c | A stale inherited value is overwritten | PASS | `console/tests/test_procs_anchor.py::TestCleanEnvAnchor::test_ac1c_a_stale_inherited_value_is_overwritten` |
| AC-1d | Not stripped by the default or a custom `env_strip` | PASS | `console/tests/test_procs_anchor.py::TestCleanEnvAnchor::test_ac1d_not_stripped_by_the_default_env_strip`, `console/tests/test_procs_anchor.py::TestCleanEnvAnchor::test_ac1d_not_stripped_by_a_custom_env_strip` |
| AC-1e | The `LiveSession`/`TurnSession` child env holds the main root | PASS | `console/tests/test_procs_anchor.py::TestSpawnedChildHoldsTheMainRoot::test_ac1e_live_session_start`, `console/tests/test_procs_anchor.py::TestSpawnedChildHoldsTheMainRoot::test_ac1e_turn_session_deliver` |
| AC-2a | cwd = worktree and var = main resolves to main | PASS | `console/tests/test_repo_root_anchor.py::TestAnchor::test_ac2a_cwd_in_a_worktree_resolves_to_the_variable` |
| AC-2b | Var unset gives unchanged behaviour; `test_paths.py` unmodified | PASS | `console/tests/test_repo_root_anchor.py::TestAnchor::test_ac2b_unset_variable_resolves_from_cwd_as_before`; `console/tests/test_paths.py` has no diff (`git diff --quiet`) and passes |
| AC-2c | Invalid values are ignored without raising | PASS | `console/tests/test_repo_root_anchor.py::TestInvalidVariableIsIgnored::test_ac2c_same_result_as_no_variable_and_no_exception` (6 params: empty, literal, relative, nonexistent, non-root-dir, file) |
| AC-2d | An explicit `start` beats the variable | PASS | `console/tests/test_repo_root_anchor.py::TestAnchor::test_ac2d_an_explicit_start_beats_the_variable` |
| AC-2e | The anchor round-trips through a layout renamed by `workspace.toml` | PASS | `console/tests/test_repo_root_anchor.py::TestWorkspaceTomlLayout::test_ac2e_renamed_layout_round_trips_the_anchor` |
| AC-3a | The `.mcp.json` entry carries the env | PASS | `console/tests/test_mcp_anchor.py::test_ac3a_the_committed_mcp_json_entry`; `.mcp.json` |
| AC-3b | `setup_editor('claude')` writes the same entry and is idempotent | PASS | `console/tests/test_mcp_anchor.py::TestSetupEditorClaude::test_ac3b_writes_the_committed_entry_and_is_idempotent` |
| AC-3c | cursor/vscode entries are unchanged | PASS | `console/tests/test_mcp_anchor.py::TestSetupEditorClaude::test_ac3c_cursor_and_vscode_entries_carry_no_env`; `console/tests/test_setup_editor.py` has no diff and passes |
| AC-3d | Live smoke: a Claude chat in a fresh worktree writes through a `console_*` verb into main's TOML | PASS — live 2026-10-05 (second attempt) | Code in `9455478`. Worktree `.claude/worktrees/T-024` (branch `agent/T-024`) was created after that commit. First attempt, chat `569bed5d941a`: the CLI denied `mcp__console__comment`, because no allow rule existed (T-025 bug D-1, a pre-existing gap). After the D-1 fix (`console/server/agent_approvals.py` `CONSOLE_TOOLS_ALLOW`), chat `efcfb0c8223b` (claude haiku, mode=default, cwd = the worktree) called `mcp__console__comment` and replied DONE. Comment C1 is in **main's** `knowledge-center/artifacts/T-024/T-024-comments.toml`, and the worktree's copy has 0 entries. |
| AC-3e | An MCP server started in a worktree with the var set serves main | PASS | `console/tests/test_mcp_anchor.py::TestServerFromAWorktree::test_ac3e_the_variable_points_a_worktree_started_server_at_main` |
| AC-4a | Turn telemetry lands in main, none under the worktree | PASS | `console/tests/test_worktree_anchor.py::TestWorktreeTelemetryAnchor::test_ac4a_turn_record_lands_in_the_main_repo`, `console/tests/test_worktree_anchor.py::TestWorktreeTelemetryAnchor::test_ac4a_nothing_is_written_under_the_worktree` |
| AC-4b | `notify.send` receives the main root | PASS | `console/tests/test_worktree_anchor.py::TestNotifyAndFallback::test_ac4b_the_turn_end_notification_gets_the_main_root` |
| AC-4c | `_telemetry_by_session(main)` sees the worktree chat | PASS | `console/tests/test_worktree_anchor.py::TestWorktreeTelemetryAnchor::test_ac4c_by_session_totals_see_the_worktree_chat` |
| AC-4d | `repo_root=""` falls back to cwd; `test_telemetry.py` unmodified | PASS | `console/tests/test_worktree_anchor.py::TestNotifyAndFallback::test_ac4d_no_repo_root_falls_back_to_cwd`; `console/tests/test_telemetry.py` has no diff |
| AC-5a | A verb from a worktree API chat mutates main | PASS | `console/tests/test_api_session_roots.py::TestApiSessionSplitRoots::test_ac5a_a_verb_from_a_worktree_chat_mutates_main` |
| AC-5b | `write_file` lands in the worktree | PASS | `console/tests/test_api_session_roots.py::TestApiSessionSplitRoots::test_ac5b_write_file_still_lands_in_the_worktree` |
| AC-5c | Paths outside the worktree are still refused | PASS | `console/tests/test_api_session_roots.py::TestWorkspaceStaysConfined::test_ac5c_paths_outside_the_worktree_are_still_refused` |
| AC-5d | `run_command` without a cwd runs in the worktree | PASS | `console/tests/test_api_session_roots.py::TestWorkspaceStaysConfined::test_ac5d_run_command_without_cwd_runs_in_the_worktree` |
| AC-5e | Approval: notify goes via main, the diff reads the worktree file | PASS | `console/tests/test_api_session_roots.py::TestApprovalRoots::test_ac5e_notify_goes_to_main_and_the_diff_reads_the_worktree_file` |
| AC-5f | `after_capture` finds a capture written under main | PASS | `console/tests/test_api_session_roots.py::TestCaptureFollowsMain::test_ac5f_a_capture_written_under_main_reaches_the_model` |
| AC-5g | Only the dispatch fake in `test_api_session.py` changed | PASS | `git diff console/tests/test_api_session.py` = the `fake(...)` signature at about line 608 plus its passthrough, nothing else; `console/tests/test_agent_tools.py` has no diff |
| AC-6a | Ticketless chat: one root everywhere | PASS | `console/tests/test_anchor_regressions.py::TestUnchangedWhenCwdIsTheRepoRoot::test_ac6a_ticketless_chat_has_one_root_everywhere` |
| AC-6b | Worktree failure leaves all roots equal | PASS | `console/tests/test_anchor_regressions.py::TestUnchangedWhenCwdIsTheRepoRoot::test_ac6b_a_failed_worktree_leaves_all_roots_equal` |
| AC-6c | Codex `child_env` untouched | PASS | `console/tests/test_codex.py` has no diff and passes |
| AC-6d | Prompt resolution stays on cwd | PASS | `console/tests/test_anchor_regressions.py::TestPromptResolutionStaysOnCwd::test_ac6d_send_composes_against_the_session_cwd`, `console/tests/test_anchor_regressions.py::TestPromptResolutionStaysOnCwd::test_ac6d_the_api_system_prompt_is_built_from_the_cwd` |

## Test Results

```
python -m pytest -o addopts="" -q -p no:cacheprovider console          2255 passed in 225.25s
T-024 files (repo_root/worktree/mcp/procs/api_session_roots/regressions)  40 passed in 11.45s
pinned files (paths, setup_editor, telemetry, codex, agent_tools, mcp, api_session)  179 passed in 13.11s
```

The 2255 total also includes tests from concurrent, unrelated work in the same working tree (`console/tests/test_workspace_check.py`, the secret-check verb), so it is not a clean T-024 delta. There were no failures and no errors.

## Edge Cases Probed
- An explicit `start` that is not a root falls through to the variable rather than walking up from it: `console/tests/test_repo_root_anchor.py::TestAnchor::test_an_explicit_start_that_is_no_root_falls_through_to_the_variable`.
- An invalid variable is never walked up from: `test_no_upward_walk_from_an_invalid_variable`.
- A broken `workspace.toml` does not raise: `test_a_broken_workspace_toml_does_not_raise`.
- An approval with no `preview_root` keeps using `repo_root`: `test_without_preview_root_the_preview_uses_repo_root`.

## Notes

**Limit (challenge-implementation).** `.mcp.json` still launches the relative `console/mcp_server.py`. Inside a worktree, the server *code* is therefore the worktree branch's copy, while *state* anchors to main through the env var. The anchor only works if that branch copy already contains this ticket's `paths.py` and `.mcp.json`. That means worktrees cut from a commit **before** T-024 lands keep the old behaviour until they are rebased or recreated. This is why AC-3d needs a **fresh** worktree after the commit (see T-024-plan.md, task T-024-06). It is acceptable for now, because every chat Run creates or reuses `agent/{ticket}` worktrees, and those can be recreated. The longer-term fix is to point the per-chat MCP config at the main repo's absolute `mcp_server.py`; that is noted for [[T-025-summary]], which already rewrites the per-chat launch.

**AC-4a red-first** is recorded by the builder in [[T-024-progress]] (task T-024-01: AC-4a ×2, AC-4c and AC-5a red, then green). I did not re-observe the red run; I re-verified only the green state. The builder's name diff against the 2215 baseline (0 missing, 40 new) also comes from progress; my own run reproduces the 2255 total.

**Open, not blocking:** CR-3. The preview root for the Claude hook path (`console/server/features/agents_feature.py`) was left unchanged and is tracked as a T-024 todo.

**Status:** all criteria pass. AC-3d first failed on a pre-existing permission gap (T-025 D-1); that was fixed the same day and the smoke re-run passed.

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
