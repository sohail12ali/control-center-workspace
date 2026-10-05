---
ticket: "T-024"
artifact: requirements
status: frozen
frozen_at: "2026-10-04"
frozen_iteration: 1
---

# Requirements: T-024 (frozen, iteration 1)

Intent: agents in a ticket worktree read and write console-managed state in the main repo and edit code only in their worktree. Phase A of [[T-023-summary]]. Full rationale, interactions and edge cases: [[T-024-requirements-draft]]; history: [[T-024-iteration-log]]; decisions D1-D6: [[T-024-decision-log]]. Post-freeze changes go through `evolve`.

## Functional Requirements

1. **FR-1** `procs.clean_env(repo_root)` sets `CONSOLE_REPO_ROOT=abspath(repo_root)` when `repo_root` is truthy (`console/server/procs.py:58-64`; used by `agent_session.py:547,683`, `agents.py:287`).
2. **FR-2** `paths.find_repo_root` order: explicit `start` > valid `CONSOLE_REPO_ROOT` > cwd > package dir (`console/server/paths.py:70-108`). Valid = absolute, existing dir, and `_is_repo_root` or `workspace_config.resolve` succeeds. Invalid is ignored silently; no upward walk from it.
3. **FR-3** `.mcp.json` console entry gains `env: {CONSOLE_REPO_ROOT: "${CONSOLE_REPO_ROOT:-}"}`; `setup_editor('claude')` writes the same entry; cursor/vscode entries unchanged (`console/server/setup_editor.py:103-113`).
4. **FR-4** `_record_turn` and `_notify_turn_end` use `self.repo_root or self.cwd` (`agent_session.py:451,473`); stale docstrings fixed (`agent_session.py:463`, `agent_manager.py:391`).
5. **FR-5** `agent_tools.dispatch(repo_root, name, arguments, workspace_root=None)` (None = `repo_root`). `ApiSession` sends verbs, `tool_definitions`, `assistant_config.settings`, `after_capture` and approval-notify to `repo_root`; file tools, `run_command`, `prompt_build` and the approval diff preview stay on the session cwd. `REGISTRY.request` gains `preview_root=None` (`agent_api_session.py:108,178,272,351,355,366`).
6. **FR-6** No behavioural change for ticketless chats, non-git repos or worktree-creation failure (`cwd == repo_root`), Codex `child_env`, or `compose_prompt`/`prompt_build` resolution.

## Non-Functional Requirements

| Category | Target |
|---|---|
| Reliability | anchoring never raises; invalid variable ignored (all AC-2c inputs) |
| Performance | no extra process; at most one `isdir` + `resolve` in `find_repo_root`, only when the variable is set |
| Security | path only; no secret; no new env-value logging |
| Compatibility | Windows/macOS/Linux; paths compared with `realpath`/`normcase` |
| Regression | `pytest -o addopts=""` count >= count measured at build start (plan baseline 1867, unverified) |
| Dependencies | none added |

## Acceptance Criteria

FR-1
- [ ] AC-1a `clean_env(repo)["CONSOLE_REPO_ROOT"] == abspath(repo)`
- [ ] AC-1b `clean_env(None)` adds nothing; an ambient value passes through
- [ ] AC-1c a stale inherited value is overwritten when `repo_root` is given
- [ ] AC-1d not stripped by default or custom `env_strip`
- [ ] AC-1e `LiveSession.start` and `TurnSession._deliver` Popen env holds main root for a ticketed worktree chat

FR-2
- [ ] AC-2a cwd = worktree, var = main -> main
- [ ] AC-2b var unset -> unchanged; `tests/test_paths.py` passes unmodified
- [ ] AC-2c `""`, literal `"${CONSOLE_REPO_ROOT:-}"`, relative, nonexistent, existing non-root dir -> ignored, same result as no variable, no exception
- [ ] AC-2d explicit valid `start` beats the variable
- [ ] AC-2e `workspace.toml`-renamed layout round-trips the anchor

FR-3
- [ ] AC-3a `.mcp.json` console entry equals `{command: python, args: [console/mcp_server.py], env: {CONSOLE_REPO_ROOT: "${CONSOLE_REPO_ROOT:-}"}}`
- [ ] AC-3b `setup_editor('claude')` writes an entry equal to the committed one; re-run `mcp_changed is False`; other servers preserved
- [ ] AC-3c existing cursor/vscode `test_setup_editor.py` assertions pass unmodified
- [ ] AC-3d live smoke on a fresh worktree: a Claude chat's `console_*` write verb lands in main's TOML (manual; recorded in [[T-024-verification]]; failure -> `evolve`)
- [ ] AC-3e MCP server subprocess (harness at `tests/test_mcp.py:5`) with cwd = worktree-shaped dir and var = main serves main's tickets

FR-4
- [ ] AC-4a **first failing test**: ticketed session over a real git worktree, `repo_root` = main, one turn end -> record in main `knowledge-center/telemetry/*.jsonl`, none under the worktree
- [ ] AC-4b `notify.send` receives main root
- [ ] AC-4c `verb_handlers._telemetry_by_session(main)` contains the session with cost/tokens > 0
- [ ] AC-4d `repo_root=""` falls back to `cwd`; `test_telemetry.py` unmodified

FR-5
- [ ] AC-5a verb call (e.g. `comment`) from a worktree API chat mutates main's tracker, not the worktree copy
- [ ] AC-5b `write_file("x.txt", ...)` creates the file in the worktree, not main
- [ ] AC-5c `read_file` of `../x` or an absolute outside-path still errors "outside the workspace" (`agent_tools.py:73-87`)
- [ ] AC-5d `run_command` without `cwd` runs in the worktree
- [ ] AC-5e approval: notify via main root, diff preview reads the worktree file
- [ ] AC-5f `after_capture` finds a capture a verb wrote under main
- [ ] AC-5g the `tests/test_api_session.py:608` fake accepts `workspace_root`; all other `test_api_session.py`/`test_agent_tools.py` tests unmodified

FR-6
- [ ] AC-6a ticketless chat: env var == cwd == `repo_root`; telemetry location unchanged
- [ ] AC-6b non-git / `WorktreeError` fallback: all roots equal, behaviour unchanged
- [ ] AC-6c Codex `child_env` untouched (`tests/test_codex.py` unmodified)
- [ ] AC-6d `agent_manager.send`/`compose_prompt` and `prompt_build.build` still resolve against `cwd`

## Business Rules

- BR-1 console-managed state lives only in the main repo · BR-2 workspace edits/commands are confined to the session cwd · BR-3 the variable is a validated locator, never raises · BR-4 explicit `start` beats the variable · BR-5 default arguments keep all other callers unchanged.

## Data entities

None new. Existing worktree-local state is not migrated (no worktree exists, `git worktree list`, 2026-10-04).

## Out of Scope

- `roles.toml`, prompt bundles, run-identity env vars (T-025); sessions (T-026); wakeups (T-027); budgets/doctor/reaper (T-028).
- Anchoring markdown artifacts that agents write with their own file tools (Q1, open, low, non-blocking, D6).
- Codex/cursor-agent parity; `.cursor/mcp.json`, `.vscode/mcp.json`.
- Per-chat `--mcp-config` (plan Phase A bullet 3), replaced by FR-3 (D3).
- Resolving skills/`#file`/API system prompt against main (D5).

## Open items at freeze

- Q1 (non-blocking). UNCERTAIN until AC-3d: Claude's env pass-through/expansion. Not reproduced at runtime: the bug itself (AC-4a is the reproduction).

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-requirements-draft]] · [[T-024-iteration-log]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
