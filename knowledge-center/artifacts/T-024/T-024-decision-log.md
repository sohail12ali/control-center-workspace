---
ticket: "T-024"
artifact: decision-log
---

# Decisions: T-024

All decided by the analyst on 2026-10-04 from code evidence; none needed a stakeholder answer. Final approval of the frozen requirements rests with harness/the owner.

## D1-split-dispatch-roots
**Decision:** `agent_tools.dispatch` gains an optional `workspace_root` (default `repo_root`). API sessions pass `repo_root=self.repo_root or self.cwd` and `workspace_root=self.cwd`. Console verbs, `tool_definitions`, `assistant_config.settings`, `multimodal.after_capture` and the approval notify follow the main repo; file tools, `run_command`, `prompt_build` and the approval diff preview stay on the worktree. `REGISTRY.request` gains `preview_root` (default `repo_root`).
**Rationale:** `dispatch` uses one argument both for `verbs_mod.run(repo_root, ...)` and for `_resolve(repo_root, path)` / `run_command` confinement (`console/server/agent_tools.py:73-87,237-258,363-391`). The plan's plain `self.cwd -> repo_root` swap would let API agents edit and run in the main tree, bypassing their worktree. Captures are written under the verb root, so `after_capture` must follow it (`multimodal.py:105-115`). `notify` config is gitignored and absent in a worktree (`.gitignore:76`), but the diff preview must read the file being edited (`agent_approvals.py:112-115`).
**Impact:** FR-5. `tests/test_api_session.py:608` fake needs the new parameter. Alternative rejected: a plain swap (regression); a second `dispatch_workspace` function (duplicates the verb/tool lookup).

## D2-env-seam-is-clean-env
**Decision:** Set `CONSOLE_REPO_ROOT` in `procs.clean_env(repo_root)`, not in `Backend.child_env`.
**Rationale:** `LiveSession.start` (the Claude `stream_json` path) calls only `clean_env` (`agent_session.py:547`); `child_env` is applied by `TurnSession._deliver` alone (L683-686) and returns `{}` for non-Codex backends (`agent_backends.py:582-588`). `clean_env` is also the seam for `agents.py:287` and `evals/runner.py:51`, and it already receives `repo_root`. T-025's run-identity vars can reuse it.
**Impact:** FR-1. Deviates from plan Phase A bullet 1 (seam only; the variable and its meaning are as planned). Set only when `repo_root` is truthy, so `clean_env(None)` callers are unchanged.

## D3-mcp-via-env-not-per-chat-config
**Decision:** Keep one project `.mcp.json` and add `"env": {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"}`; apply the same entry in `setup_editor('claude')`. Do not write a per-chat `--mcp-config` with an absolute path.
**Rationale:** A per-chat config adds a second `console` server next to the project one unless `--strict-mcp-config` is passed, which would also drop the user's other MCP servers; it also needs an `agents.toml` placeholder and a file per chat. The env route changes one tracked file. Docs (`https://code.claude.com/docs/en/mcp`, read via a summarising fetch) say `${VAR:-default}` expands in `env` and stdio servers inherit the parent env. A literal unexpanded string is harmlessly ignored by FR-2, so failure of expansion degrades to today's behaviour, never to something worse. `setup_editor` would otherwise erase the block (`setup_editor.py:47-70`). Cursor/VS Code entries stay pinned (`tests/test_setup_editor.py:30-34,66-72`).
**Impact:** FR-3. **UNCERTAIN, not testable in the suite:** whether the Claude CLI expands the variable and/or passes the parent env; AC-3d (live smoke) decides. The edit reaches only worktrees created after it is committed; smoke must use a fresh one. Deviates from plan Phase A bullet 3 (absolute-path MCP config).

## D4-find-repo-root-precedence-and-validity
**Decision:** Order is explicit `start` > `CONSOLE_REPO_ROOT` > cwd > package dir. The variable counts only if absolute, an existing directory, and a root (`_is_repo_root`) or resolvable via `workspace_config.resolve`. Otherwise ignored, with no upward walk from it and no exception.
**Rationale:** `mcp_server.py` passes an explicit `start` and tests pass tmp dirs; a variable must not override them. The existing candidate loop walks upward (`paths.py:94-104`), so an invalid value left in the list could silently select an ancestor. The plan says "before it walks up from cwd" - consistent. Reuses the same validation as every other candidate (T-017).
**Impact:** FR-2, BR-3, BR-4.

## D5-prompt-and-skill-resolution-stay-on-cwd
**Decision:** `agent_manager.send` -> `compose_prompt(repo_root=sess.cwd)` and `ApiSession`'s `prompt_build.build(self.cwd)` keep resolving against the worktree; only the misleading docstring (`agent_manager.py:391`) is corrected. The harness's finding 6 is therefore docstring-only.
**Rationale:** `#file` references and the orientation text name the tree the agent edits; skills/personas are committed files present in the worktree. Pointing them at main would show the agent files it cannot see in its own tree. Known limitation: skills or agents that exist only uncommitted in main are missing in a worktree - separate from this ticket.
**Impact:** FR-6 (AC-6d), FR-4 docstrings.

## D6-markdown-artifacts-deferred
**Decision:** Anchoring markdown artifacts that agents write with their own Edit/Write tools is out of scope for T-024; logged as Q1 (low, non-blocking, open) for the owner to decide before T-025/T-026.
**Rationale:** Agent file tools are confined to cwd by design (BR-2); anchoring the vault would need a path-mapping or a git-merge story, which is a design question larger than Phase A. Phase A fixes console-mediated state (TOML via verbs and `kanban.py`, telemetry, notify), which is what the epic names.
**Impact:** Q1 in `T-024-questions.toml`; flagged in [[T-024-analysis]] and the freeze report. Side effect to note: an agent running `python console/kanban.py ...` from a worktree will now write main's TOML, while its markdown artifacts stay in the worktree.

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
