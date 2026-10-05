---
ticket: "T-024"
artifact: analysis
---

# Analysis: T-024

## Context

Phase A of epic [[T-023-summary]] ([[T-023-analysis]] row A; plan: `C:\Users\Sohail\.claude\plans\paperclip-is-doing-so-cozy-wigderson.md` section "Phase A"). A ticketed chat runs with `cwd` = its managed git worktree. Several call sites then use that worktree as if it were the main repo, so ticket state, telemetry and console verbs can land on the `agent/T-xxx` branch copy instead of the shared main repo. Found by code reading; **not yet reproduced at runtime** (the builder reproduces it with a failing test first). `git worktree list` currently shows no worktree, so there is no stray worktree-local state to inspect or migrate.

## Current State

- `agent_manager.create` sets `cwd = repo_root`, and for a ticketed call replaces it with the worktree (`console/server/agent_manager.py:142-146`, via `_resolve_worktree` L65-81, which falls back to `repo_root` on `WorktreeError`). `repo_root` is passed separately to `agent_session.build(..., repo_root=repo_root)` (L163-169) and kept as `BaseSession.repo_root` (`agent_session.py:87-97`, comment L94-95: "`cwd` is a worktree for a ticketed Run, so it cannot stand in"). T-020 CR-21 already established this distinction; later code did not follow it.
- **Env.** `LiveSession.start` (Claude `stream_json`, `agent_session.py:536-549`) spawns with `procs.clean_env(self.repo_root or None)` only. `TurnSession._deliver` (L683-686) additionally applies `backend.child_env(...)`, which returns `{}` except for Codex auth (`agent_backends.py:582-588`). No `CONSOLE_REPO_ROOT` exists anywhere in `console/`, `.claude/` or `.mcp.json` (grep, 2026-10-04; only T-023's analysis names it).
- **Root discovery.** `paths.find_repo_root` (`console/server/paths.py:70-108`) tries `start`, cwd, then the console package dir, and accepts any dir with `knowledge-center/` + `console/` (`_is_repo_root` L34-37) or resolving through `workspace.toml`. A worktree is a full checkout, so it qualifies. `.mcp.json` is `python console/mcp_server.py` (relative); `console/mcp_server.py:45` calls `find_repo_root(start)` with `start=None`, so a Claude chat in a worktree gets an MCP server rooted at the worktree.
- **Telemetry / notify.** `_record_turn` calls `telemetry.record_turn(self.cwd, ...)` (`agent_session.py:473`; docstring L463 wrongly says `self.cwd` is the repo root); `_notify_turn_end` uses `notify.send(self.cwd, ...)` (L451). The read side, `verb_handlers._telemetry_by_session`/`_enrich_run` (L370-424), reads the main `repo_root`, so a worktree chat's Run shows $0 / 0 tokens.
- **API backend** (`agent_api_session.py`): `prompt_build.build(self.cwd)` L108; `tool_definitions(self.cwd)` L178; `multimodal.after_capture(self.cwd, ...)` L272; `REGISTRY.request(..., repo_root=self.cwd)` L351; `agent_tools.dispatch(self.cwd, ...)` L355; `assistant_config.settings(self.cwd)` L366.
- `agent_manager.send` passes `sess.cwd` as `repo_root` to `backend.compose_prompt` (L401) under a docstring that calls `sess.cwd` "the workspace root" (L391).

## Key Findings

- **The `dispatch` argument is overloaded.** `agent_tools.dispatch(repo_root, ...)` (`agent_tools.py:363-391`) uses one argument for the console verbs (`verbs_mod.run(repo_root, ...)`) and for the confined file tools (`_resolve(repo_root, path)` L73-87, `run_command` L237-258 via `_resolve(repo_root, cwd or ".")`). The plan's "swap `self.cwd` -> `repo_root`" would make API agents edit and run commands in the **main** tree, bypassing their worktree: a regression worse than the bug. The fix must split the two roots. -> D1 in [[T-024-decision-log]].
- **`child_env` is the wrong seam.** The plan puts `CONSOLE_REPO_ROOT` in `Backend.child_env`, but the Claude `LiveSession` never calls it, so the main path would stay unfixed. Both session types (and `agents.py:287`, `evals/runner.py:51`) already go through `procs.clean_env(repo_root)`. -> D2.
- **Verb root drags other call sites with it.** Screenshot verbs write captures under the verb root; `multimodal.after_capture` resolves the capture under the root it is given (`multimodal.py:105-115`), so once verbs run on main it must look in main too (L272). -> D1.
- **Approvals need two roots.** `REGISTRY.request(repo_root=...)` uses one value for the diff preview (`tool_preview.build`, reads the file being edited, `agent_approvals.py:112-115`; must read the worktree) and for `notify.send` (config, must be main; `console/config/notify-local.toml` is gitignored, `.gitignore:76`, so a worktree has none; `console/.cache/` is gitignored too, L66). Only the API session calls `request` (grep). -> D1.
- **`.mcp.json` env block and `setup_editor`.** `setup_editor('claude')` rewrites the `console` entry wholesale (`server/setup_editor.py:47-70`, `entry_stdio` L103). Adding an `env` block to `.mcp.json` alone would be erased the next time someone runs it. Cursor and VS Code entries are pinned exact by tests (`tests/test_setup_editor.py:30-34`, `66-72`); the Claude test pins only `args` (L54-62).
- **An edited `.mcp.json` only reaches worktrees created after it is committed** (`.mcp.json` is tracked, `git ls-files`); a worktree made earlier keeps the old file. Hence the env var must also work when it is inherited, and the live smoke must use a fresh worktree.
- **Claude's behaviour (UNCERTAIN, external).** Docs (`https://code.claude.com/docs/en/mcp`, fetched 2026-10-04 via a summarising tool, so not verbatim-verified) say `.mcp.json` expands `${VAR}` and `${VAR:-default}` in `command`, `args`, `env`, `url`, `headers`, and imply stdio servers inherit the parent environment. Not testable in this repo's suite; the explicit `env` block is the belt-and-braces and is verified only by the live smoke.
- **Side effect that is the point:** an agent in a worktree running `python console/kanban.py ...` through Bash also reaches `find_repo_root()` (`kanban.py:1076`) and will now mutate main's TOML, not the worktree copy.
- **Not in scope but real (Q1):** Markdown artifacts written by an agent with its own Edit/Write tools still land in the worktree's `knowledge-center/artifacts/` (that is the agent's cwd), while `ticket.toml` and trackers go to main. Whether the vault should be anchored to main is a separate design question.

## Research

Re-verified by reading the cited lines on 2026-10-04 (all findings above match the harness's grounding). No runtime reproduction: no worktree exists and the harness asked for a failing test instead. Prior art: `[[T-018-summary]]` worktree isolation, T-020 CR-21 (`repo_root` on the session), T-017 `workspace.toml` / `workspace_config.resolve`.

## Recommended Path

One small, test-first change set (the builder writes the failing tests first, then fixes):

1. `procs.clean_env(repo_root)`: when `repo_root` is truthy set `CONSOLE_REPO_ROOT=abspath(repo_root)` (covers both session types and agent runs). FR-1.
2. `paths.find_repo_root`: after an explicit `start`, honour a **valid** `CONSOLE_REPO_ROOT`; invalid/empty/unexpanded values fall through silently. FR-2.
3. `.mcp.json` and `setup_editor('claude')`: add `"env": {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"}`. FR-3.
4. Session: `self.repo_root or self.cwd` for `_record_turn` and `_notify_turn_end`; fix docstrings. FR-4.
5. API session: split roots. Verbs, `tool_definitions`, `assistant_config`, `after_capture`, approval notify -> `repo_root`; file tools, `run_command`, diff preview, `prompt_build` -> `cwd`. `dispatch` gains an optional `workspace_root` (default = `repo_root`, so every other caller is unchanged). FR-5.
6. Pin the no-regression cases (ticketless, non-git fallback). FR-6.

**First failing test** (see report/[[T-024-requirements]] AC-4a): a ticketed session built over a git worktree with `repo_root=main`, one turn end, asserts the telemetry record is in main's `knowledge-center/telemetry/` and absent from the worktree's.

**Deviation from the plan, flagged:** Phase A bullet 3 ("per-chat MCP config with an absolute path to `mcp_server.py`") is replaced by the env-var route (D3): a per-chat `--mcp-config` would duplicate the project's `console` server unless `--strict-mcp-config` is added, which would also drop the user's other MCP servers. Phase A bullet 1's seam (`Backend.child_env`) is replaced by `procs.clean_env` (D2).

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
