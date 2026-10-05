---
ticket: "T-024"
artifact: user-stories
created: "2026-10-04"
---

# User Stories: T-024

Extracted from the frozen [[T-024-requirements]] (iteration 1). Four stories; every AC appears in exactly one.

**Created by:** `requirements T-024 stories` · **Validated by:** `validate-artifacts T-024 links`

## Stories

### US-1: A worktree chat's console tools reach the main repo

**As a** operator running a ticketed agent chat in its git worktree
**I want** the chat's console tools (MCP server, `kanban.py`, spawned agent processes) to locate the main repo through `CONSOLE_REPO_ROOT`
**So that** ticket and tracker state written from a worktree lands in the shared main repo, not on the `agent/T-xxx` copy

**Acceptance Criteria:**
- [ ] AC-1a, AC-1b, AC-1c, AC-1d, AC-1e (env set by `clean_env`, both session types)
- [ ] AC-2a, AC-2b, AC-2c, AC-2d, AC-2e (`find_repo_root` precedence and validity)
- [ ] AC-3a, AC-3b, AC-3c, AC-3d, AC-3e (`.mcp.json` + `setup_editor`, live smoke)

**Business Rules:**
- BR-1 console-managed state lives only in the main repo; BR-3 the variable is a validated locator and never raises; BR-4 explicit `start` beats the variable

**Edge Cases:**
- Empty, literal `${CONSOLE_REPO_ROOT:-}`, relative, nonexistent or non-root values are ignored; renamed `workspace.toml` layout; stale inherited value overwritten

**Related Components:** `console/server/procs.py`, `console/server/paths.py`, `.mcp.json`, `console/server/setup_editor.py`
**Related Tasks:** T-024-02, T-024-03, T-024-06 (AC-3d)

**Priority:** High
**Story Points:** 5

---

### US-2: Telemetry and turn-end notifications follow the main repo

**As a** operator reading the Runs board and cost analytics
**I want** each turn's telemetry record and turn-end notification written against the main repo
**So that** a worktree chat's Run shows its real cost and tokens instead of $0 / 0

**Acceptance Criteria:**
- [ ] AC-4a (first failing test), AC-4b, AC-4c, AC-4d

**Business Rules:**
- BR-1; BR-5 defaults keep other callers unchanged

**Edge Cases:**
- `repo_root=""` falls back to `cwd`

**Related Components:** `console/server/agent_session.py`, `console/server/agent_manager.py` (docstring)
**Related Tasks:** T-024-01 (red), T-024-04

**Priority:** High
**Story Points:** 2

---

### US-3: API agents keep edits in the worktree and state in main

**As a** operator running an API-backend chat on a ticket
**I want** console verbs, captures and approval notifications routed to the main repo while file tools, commands and diff previews stay on the worktree
**So that** the agent edits only its own branch and still updates shared ticket state

**Acceptance Criteria:**
- [ ] AC-5a, AC-5b, AC-5c, AC-5d, AC-5e, AC-5f, AC-5g

**Business Rules:**
- BR-2 workspace edits/commands are confined to the session cwd; BR-5 default arguments (`workspace_root=None`, `preview_root=None`) leave every other caller unchanged

**Edge Cases:**
- `../x` and absolute outside paths still rejected; capture written by a verb under main is found by `after_capture`

**Related Components:** `console/server/agent_tools.py`, `console/server/agent_api_session.py`, `console/server/agent_approvals.py`
**Related Tasks:** T-024-01 (red/guard), T-024-05

**Priority:** High
**Story Points:** 5

---

### US-4: Nothing changes for chats that have no worktree

**As a** operator using ticketless chats, non-git repos or Codex
**I want** behaviour identical to today
**So that** the anchoring fix cannot regress paths that never had the bug

**Acceptance Criteria:**
- [ ] AC-6a, AC-6b, AC-6c, AC-6d

**Business Rules:**
- BR-5; prompt/skill resolution stays on `cwd` (D5)

**Edge Cases:**
- `WorktreeError` fallback (`cwd == repo_root`); Codex `child_env` untouched

**Related Components:** `console/server/agent_manager.py`, `console/server/agent_backends.py`, `console/server/prompt_build.py`
**Related Tasks:** T-024-06

**Priority:** Medium
**Story Points:** 2

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | A worktree chat's console tools reach the main repo | Pending | High | 5 | T-024-02, 03, 06 |
| US-2 | Telemetry and turn-end notifications follow the main repo | Pending | High | 2 | T-024-01, 04 |
| US-3 | API agents keep edits in the worktree and state in main | Pending | High | 5 | T-024-01, 05 |
| US-4 | Nothing changes for chats that have no worktree | Pending | Medium | 2 | T-024-06 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | procs, paths, `.mcp.json`, setup_editor | T-024-02, T-024-03, T-024-06 |
| US-2 | agent_session, agent_manager (docstring) | T-024-01, T-024-04 |
| US-3 | agent_tools, agent_api_session, agent_approvals | T-024-01, T-024-05 |
| US-4 | agent_manager, agent_backends, prompt_build | T-024-06 |

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-requirements-draft]] · [[T-024-user-stories]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
