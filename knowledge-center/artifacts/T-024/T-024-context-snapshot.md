---
ticket: "T-024"
artifact: context-snapshot
status: draft
created: "2026-10-04"
last_updated: "2026-10-04"
scope: codebase + history
---

# Context Snapshot: T-024

> Frozen facts only. Narrative and recommendation live in [[T-024-analysis]]; this file is the cited fact base for [[T-024-requirements-draft]]. Paths are under `console/` unless noted.

## 1. Intent (echo)

Make every agent chat use the main repo (not its worktree) for console-managed state, while code edits stay in the worktree. Phase A of [[T-023-summary]].

## 2. Codebase Findings

### Adjacent features already built
| Feature | Entry point | Reuse opportunity | Source |
|---|---|---|---|
| Per-ticket worktree, cwd override | `agent_manager._resolve_worktree`, `create` | cwd == repo_root fallback already exists | `server/agent_manager.py:65-81,142-146` |
| Session carries `repo_root` separately from `cwd` | `BaseSession.__init__` | use it; fallback `repo_root or cwd` | `server/agent_session.py:87-97` |
| Child env builder for every agent spawn | `procs.clean_env(repo_root)` | single seam for the env var | `server/procs.py:58-64`; callers `agent_session.py:547,683`, `agents.py:287`, `evals/runner.py:51` |
| Root discovery incl. `workspace.toml` | `paths.find_repo_root`, `_is_repo_root` | add one candidate, same validation | `server/paths.py:34-37,70-108` |
| Workspace-vs-verb split already needed | `agent_tools.dispatch`, `_resolve` | add optional `workspace_root` | `server/agent_tools.py:73-87,237-258,363-391` |
| Editor MCP config writer | `setup_editor.setup_editor` | claude entry gains env | `server/setup_editor.py:47-70,103-113` |
| Telemetry write/read | `telemetry.record_turn`, `verb_handlers._telemetry_by_session` | write side must use the read side's root | `server/telemetry.py:120`, `server/verb_handlers.py:370-424` |

### Patterns / conventions
- Tests build a git fixture repo and worktrees with the `gitrepo` fixture (`tests/test_agent_manager_worktree.py:26-37`); API-session tests monkeypatch `agent_tools.dispatch` with `fake(repo_root, name, arguments)` (`tests/test_api_session.py:608`) - a new `dispatch` parameter breaks that fake's signature.
- `tests/test_procs.py:425-452` (`TestCleanEnv`) pins the strip behaviour; `tests/test_paths.py` pins sibling-walk and `workspace.toml` resolution.
- `console/config/notify-local.toml` and `console/.cache/` are gitignored (`.gitignore:76`, `:66`), so absent from any worktree.

## 3. Historical Findings

| Ticket | What it did | Lesson |
|---|---|---|
| [[T-018-summary]] | Worktree per ticketed Run (FR-1/2/4), `cwd` = worktree, fallback to `repo_root` | introduced the cwd/repo_root split; ticketless callers unchanged |
| T-020 (CR-21) | `BaseSession.repo_root`, "`cwd` is a worktree for a ticketed Run, so it cannot stand in" (`agent_session.py:94-95`) | the principle exists; telemetry/notify/API paths were not updated |
| T-017 | `workspace.toml`, `workspace_config.resolve`, `setup_editor` | root may be renamed/relocated; validation must reuse `workspace_config.resolve` |
| [[T-023-summary]] | Epic; Phase A = this ticket | later phases add run-identity env vars (`CONSOLE_RUN_ID`...) to the same env seam |

No incident record of the bug in production: `git worktree list` shows only the main checkout on 2026-10-04.

## 4. External Systems in the Loop

- Claude Code CLI: reads project `.mcp.json` from its cwd, spawns the stdio MCP server. Docs (`https://code.claude.com/docs/en/mcp`) say `${VAR}` / `${VAR:-default}` expand in `command/args/env/url/headers`.

## 5. Preliminary Risks Spotted

- Splitting the roots wrongly flips the API file tools onto the main tree.
- Fix reaches Claude chats only through `LiveSession`; `child_env` alone would miss it.
- `.mcp.json` change reaches worktrees created after commit only.
- `setup_editor('claude')` would erase a hand-added `env` block.

## 6. Open Confirmations

- Claude passes the parent env to the stdio MCP server and expands `${CONSOLE_REPO_ROOT:-}` - from docs via a summarising fetch, not run. Confirm in the live smoke on a fresh worktree.
- The worktree-chat bug itself is not reproduced at runtime (read from code only).
- Full-suite baseline (1867 tests per the plan) was not re-run in this analyst stage.

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-04 | `console context T-024` | ticket state | trace-context |
| 2026-10-04 | Read | `agent_manager.py`, `agent_session.py`, `agent_api_session.py`, `agent_tools.py`, `agent_backends.py`, `paths.py`, `procs.py`, `agent_approvals.py`, `tool_preview.py`, `multimodal.py`, `setup_editor.py`, `verb_handlers.py` | re-verify harness findings |
| 2026-10-04 | Grep | `CONSOLE_REPO_ROOT`, `find_repo_root(`, `clean_env(`, `.cwd` | callers and absence of the var |
| 2026-10-04 | Read | `tests/test_setup_editor.py`, `test_api_session.py`, `test_agent_manager_worktree.py`, `test_procs.py` | what pins the shapes |
| 2026-10-04 | Bash | `git worktree list`, `git ls-files .mcp.json`, `.gitignore` | no existing worktrees; tracked files |
| 2026-10-04 | WebFetch | `code.claude.com/docs/en/mcp` | env expansion in `.mcp.json` |

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements-draft]] · [[T-024-context-snapshot]] · [[T-024-gap-analysis]] · [[T-024-iteration-log]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
