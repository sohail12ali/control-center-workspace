---
ticket: "T-024"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
created: "2026-10-04"
last_updated: "2026-10-04"
frozen_at: "2026-10-04"
frozen_iteration: 1
---

# Requirements Draft: T-024

> Frozen at iteration 1 on 2026-10-04. The canonical, condensed list is [[T-024-requirements]]; this file keeps the full rationale. Post-freeze changes go through `evolve`.

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Agents running in a ticket worktree must read and write console-managed state in the main repo, and keep editing code only in their worktree.

**Business driver:** Phase A of [[T-023-summary]]; every later phase (roles, sessions, wakeups, budgets) assumes cost, claims and comments from worktree agents land in one place.

**Raw intent verbatim:**
> "Ticket T-024 'Anchor every agent to the main repo' (Phase A of epic T-023)." Plan section "Phase A": add `CONSOLE_REPO_ROOT` to the child env, make `find_repo_root` honour it, use `repo_root` for `_record_turn` and API tool dispatch, write an absolute-path MCP config, test that a ticketed chat in a worktree writes telemetry, comments and claims to the main repo.

## 2. Context Summary

(From [[T-024-context-snapshot]] and [[T-024-analysis]].)

- **Similar existing features:** worktree isolation ([[T-018-summary]]), `BaseSession.repo_root` (`console/server/agent_session.py:87-97`), `procs.clean_env` (`console/server/procs.py:58-64`).
- **Affected code areas:** `server/procs.py`, `server/paths.py`, `.mcp.json`, `server/setup_editor.py`, `server/agent_session.py`, `server/agent_api_session.py`, `server/agent_tools.py`, `server/agent_approvals.py`, `server/agent_manager.py` (docstring).
- **Known risks from history:** T-020 CR-21 fixed one `cwd`-for-`repo_root` slip (`agent_session.py:94-95`); these are the remaining ones.

## 3. Scope

### In scope
- Export the anchor to agent children; make root discovery honour it; fix telemetry/notify/API-dispatch roots; keep the Claude MCP server on the main repo.

### Out of scope (explicit)
- `roles.toml`, prompt bundles, run-identity env vars (T-025); sessions (T-026); wakeups (T-027); budgets/doctor/reaper (T-028).
- Anchoring markdown artifacts agents write with their own file tools (Q1, deferred, non-blocking).
- Codex/cursor-agent parity; `.cursor/mcp.json` and `.vscode/mcp.json` entries (pinned by tests; not Claude chats).
- A per-chat `--mcp-config` (plan Phase A bullet 3), replaced by the env route (D3).
- Migrating state previously written into worktree copies (`git worktree list` shows none on 2026-10-04).
- Resolving `/skill`, `@agent`, `#file` and the API system prompt against main instead of the worktree (D5; uncommitted skills missing in a worktree is a known, separate limitation).

### Assumptions
- Claude Code expands `${CONSOLE_REPO_ROOT:-}` in `.mcp.json` `env` and/or passes the parent env to stdio servers (docs summary, `https://code.claude.com/docs/en/mcp`); verified only by AC-3d.

## 4. Functional Requirements

### FR-1: Agent children receive the anchor
`procs.clean_env(repo_root)` sets `CONSOLE_REPO_ROOT=abspath(repo_root)` when `repo_root` is truthy. This is the one seam both session types and `agents.py`/evals already use (D2).
- [ ] AC-1a `clean_env(repo)["CONSOLE_REPO_ROOT"] == os.path.abspath(repo)`.
- [ ] AC-1b `clean_env(None)` adds nothing; an inherited ambient value passes through unchanged.
- [ ] AC-1c with a `repo_root`, a stale inherited value is overwritten.
- [ ] AC-1d the variable is not in `DEFAULT_ENV_STRIP` and survives a custom `env_strip`.
- [ ] AC-1e for a ticketed chat whose cwd is a worktree, the env passed to `subprocess.Popen` by `LiveSession.start` and by `TurnSession._deliver` has `CONSOLE_REPO_ROOT` = main root, not the worktree.

### FR-2: Root discovery honours the anchor
Order: explicit `start` > `CONSOLE_REPO_ROOT` > cwd > console package dir. The variable is **valid** iff it is an absolute path to an existing directory that is a root (`_is_repo_root`) or resolves via `workspace_config.resolve`. An invalid value is ignored silently, with no upward walk from it (D4).
- [ ] AC-2a cwd = worktree, var = main -> `find_repo_root()` returns main.
- [ ] AC-2b var unset -> unchanged; the existing `tests/test_paths.py` passes unmodified.
- [ ] AC-2c each of: `""`, the literal `"${CONSOLE_REPO_ROOT:-}"`, a relative path, a nonexistent path, an existing non-root directory -> ignored; result equals the no-variable result; no exception.
- [ ] AC-2d an explicit `start` that is a valid root beats the variable.
- [ ] AC-2e a `workspace.toml`-renamed layout: var = the anchor `find_repo_root` returns there -> same anchor back.

### FR-3: Claude's MCP server stays on the main repo
`.mcp.json` console entry gains `"env": {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"}`; `setup_editor('claude')` writes the same entry so a re-run cannot erase it (D3). Cursor and VS Code entries are unchanged.
- [ ] AC-3a `.mcp.json` `mcpServers.console == {"command": "python", "args": ["console/mcp_server.py"], "env": {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"}}`.
- [ ] AC-3b `setup_editor('claude')` on a fresh dir writes an entry equal to the committed `.mcp.json` console entry; a second run reports `mcp_changed is False`; other servers in the file are preserved.
- [ ] AC-3c the existing cursor and vscode `test_setup_editor.py` assertions pass unmodified.
- [ ] AC-3d (live smoke, manual, recorded in [[T-024-verification]]) on a freshly created worktree (made after the `.mcp.json` change is committed), a Claude chat's `console_*` write verb (e.g. comment) lands in main's TOML, not the worktree's. If it does not, reopen via `evolve` (env pass-through assumption failed).
- [ ] AC-3e an MCP server started with cwd = a worktree-shaped dir and the variable = main serves main's tickets (`tests/test_mcp.py:5` already runs the entry-point script as a subprocess; reuse that harness).

### FR-4: Telemetry and turn-end notifications use the main repo
`_record_turn` and `_notify_turn_end` use `self.repo_root or self.cwd`; their docstrings stop calling `cwd` the repo root; `agent_manager.send`'s docstring stops calling `sess.cwd` the workspace root.
- [ ] AC-4a (first failing test) a ticketed session over a real git worktree, `repo_root` = main, one turn end: the record is in main `knowledge-center/telemetry/*.jsonl`; no `knowledge-center/telemetry` file exists in the worktree.
- [ ] AC-4b `notify.send` receives main root.
- [ ] AC-4c `verb_handlers._telemetry_by_session(main)` contains that session id with cost/tokens > 0 (read side finds what the write side wrote).
- [ ] AC-4d a session built with `repo_root=""` falls back to `cwd`; existing `test_telemetry.py` passes unmodified.

### FR-5: API sessions use main for console state and the worktree for the workspace
`agent_tools.dispatch(repo_root, name, arguments, workspace_root=None)`; `None` means `repo_root` (every existing caller unchanged, D1). `ApiSession` passes `repo_root=self.repo_root or self.cwd` and `workspace_root=self.cwd`.

| Call site | Root |
|---|---|
| console verbs (`dispatch`), `tool_definitions`, `assistant_config.settings`, `multimodal.after_capture`, `REGISTRY.request(repo_root=...)` (notify config) | main (`repo_root`) |
| `read_file/write_file/edit_file/list_files/search_files/run_command` confinement, `prompt_build.build`, approval diff preview | session cwd (worktree) |

`REGISTRY.request` gains `preview_root=None` (default `repo_root`).
- [ ] AC-5a a verb call from a worktree API chat (e.g. `comment`) mutates main's tracker; the worktree copy is untouched.
- [ ] AC-5b `write_file("x.txt", ...)` from that chat creates the file in the worktree and not in main.
- [ ] AC-5c `read_file` of `../x` and of an absolute path outside the worktree still return the "outside the workspace" error (`agent_tools.py:73-87`).
- [ ] AC-5d `run_command` with no `cwd` runs in the worktree.
- [ ] AC-5e an approval request notifies via main root while its diff preview reads the worktree copy of the file.
- [ ] AC-5f `after_capture` finds a capture a verb wrote under main.
- [ ] AC-5g the `tests/test_api_session.py:608` fake accepts `workspace_root`; all other `test_api_session.py` / `test_agent_tools.py` tests pass unmodified.

### FR-6: No change where there is no worktree
- [ ] AC-6a ticketless chat: `cwd == repo_root`; env var equals it; telemetry location identical to before.
- [ ] AC-6b non-git repo / `WorktreeError` fallback (`_resolve_worktree` returns `repo_root`): all roots equal; behaviour identical to before.
- [ ] AC-6c Codex `child_env` untouched (`tests/test_codex.py` unchanged).
- [ ] AC-6d `agent_manager.send` / `compose_prompt` and `prompt_build.build` still resolve against `cwd` (D5).

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Reliability | Anchoring code never raises; an invalid variable is ignored | 0 new exceptions on any AC-2c input | BR-3 |
| Performance | No extra process or file read on the spawn path; `find_repo_root` adds at most one `isdir` + `resolve` and only when the variable is set | 0 extra processes | |
| Security | The variable carries a path only; no secret; no new logging of env values | N/A - no secret data | `procs.clean_env` docstring: names only |
| Compatibility | Works on Windows, macOS, Linux: compare paths with `realpath`/`normcase` in tests | CI green on the existing 3-OS matrix | per memory note on cross-platform CI defects |
| Regression | Full suite `pytest -o addopts=""` count not reduced | >= count measured at build start (plan baseline 1867, unverified here) | judged from the tree, not subagent reports |
| Dependencies | No new dependency | 0 | |

## 6. Data Requirements

No new entities. Flow change only: telemetry JSONL, ticket TOML and notify config reads for a worktree chat move from `<worktree>/...` to `<main>/...`. Existing worktree-local copies are not migrated (none exist).

## 7. Business Rules

- **BR-1:** Console-managed state (ticket and tracker TOML, telemetry, runs, `console/.cache/`, notify config) lives only in the main repo.
- **BR-2:** Workspace file edits and shell commands an agent performs are confined to its session cwd (its worktree when ticketed).
- **BR-3:** `CONSOLE_REPO_ROOT` is a locator. It is validated; an invalid value is ignored and never raises.
- **BR-4:** An explicit `start` argument to `find_repo_root` beats the variable.
- **BR-5:** Change a call site's root only where its data is console state; the default for the new `dispatch` and `request` parameters keeps every other caller as is.

## 8. Edge Cases

- Ticketless chat, non-git repo, or worktree creation failure: `cwd == repo_root`; no behavioural change (FR-6).
- Variable empty, unexpanded, relative, nonexistent, or a non-root directory: ignored (AC-2c).
- Variable inherited into a chat that is not the target workspace: `clean_env` overwrites it when a `repo_root` is given (AC-1c).
- Worktree created before the `.mcp.json` change is committed: has the old file; relies on the inherited env (AC-3d uses a fresh worktree).
- Session constructed without `repo_root` (tests, `repo_root=""`): fall back to `cwd` (AC-4d).
- A `workspace.toml`-renamed layout: the anchor string, not a literal folder name (AC-2e).

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| Worktree isolation, [[T-018-summary]] (`agent_manager.py:142-146`) | conflict: cwd means "agent workspace", not "repo root" | high | isolate: split the two roots explicitly (FR-5) |
| `workspace.toml` resolution (`paths.py:94-97`) | reuse: validate the value via `workspace_config.resolve` / `_is_repo_root` | low | reuse (FR-2) |
| `setup_editor('claude')` (`setup_editor.py:103-113`) | conflict: rewrites the `console` entry | med | modify the claude entry only (FR-3) |
| Approvals + notify (`agent_approvals.py:87-147`) | conflict: one `repo_root` serves preview and notify | med | `preview_root` (FR-5) |
| Screenshot capture (`multimodal.py:105-115`) | overlap: resolved under the verb root | med | follows the verb root (FR-5) |
| `compose_prompt` / `prompt_build` | overlap: resolve against what the agent edits | low | keep on cwd (D5) |
| Gitignored `console/config/notify-local.toml`, `console/.cache/` | conflict today: absent in worktrees | med | fixed by anchoring |
| T-025..T-028 | downstream: add env vars on the same seam | low | reuse `clean_env` |

## 10. External Dependencies

- Claude Code CLI `.mcp.json` env handling (assumption above; AC-3d).

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner | Sohail Ali | state in one place; no regression | yes - plan approved 2026-10-04 ([[T-023-analysis]] "User decisions"); freeze hand-off goes to harness for the final APPROVED |

## 12. Open Questions (mirrored)

- Q1: should markdown artifacts that agents write with their own file tools land in main? - status: open, priority low, **non-blocking**, deferred out of scope (D6).

## 13. Challenge Findings (⚠)

None open. C1-C12 raised 2026-10-04 and closed in iteration 1; see [[T-024-iteration-log]].

## 14. Draft History

See [[T-024-iteration-log]]. Current iteration: **1**.

---

## Freeze Checklist

- [x] No `〈TBD〉` left
- [x] All ⚠ findings resolved (C1-C12; C9 and C11 resolved by explicit deferral, D3/D6)
- [x] No 🔴 gaps open ([[T-024-gap-analysis]])
- [x] No blocker/critical question open (Q1 is low, non-blocking)
- [x] Every FR has testable ACs
- [x] Every NFR has a target or N/A rationale
- [x] No new entities
- [x] Out-of-scope list non-empty
- [x] Sign-off recorded (plan approval; final APPROVED pending harness)
- [x] Interactions populated

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements-draft]] · [[T-024-context-snapshot]] · [[T-024-gap-analysis]] · [[T-024-iteration-log]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
