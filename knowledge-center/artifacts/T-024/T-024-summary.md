---
tags: [active]
status: In Progress
ticket: "T-024"
---

# T-024: Anchor every agent to the main repo (worktree chats write state to the wrong tree)

**Status:** In Progress  
**Stage:** VERIFY (build: T-024-01..05 done, 06 code part done; AC-3d manual smoke outstanding)  
**Owner:** Sohail Ali  
**Created:** 2026-10-04  
**Due:**  

## Overview

Phase A of epic [[T-023-summary]]. A ticketed agent chat runs with `cwd` = its git worktree, but several call sites use that worktree where they mean the main repo: telemetry and turn-end notifications (`console/server/agent_session.py:451,473`), the API backend's tool dispatch (`agent_api_session.py:355`), and the Claude MCP server (relative `.mcp.json` path + `paths.find_repo_root`). Console state from worktree agents can therefore land on the `agent/T-xxx` copy. This ticket anchors console-managed state to the main repo with a `CONSOLE_REPO_ROOT` variable and a root split for API sessions, while file edits stay in the worktree. Found by reading code; not yet reproduced at runtime.

## Current State

- GROUND/CLARIFY done 2026-10-04: [[T-024-analysis]], [[T-024-context-snapshot]], [[T-024-gap-analysis]] (0 open), [[T-024-iteration-log]] (iteration 1).
- Requirements **frozen** at iteration 1: [[T-024-requirements]] (FR-1..FR-6, AC-1a..AC-6d). Decisions D1-D6: [[T-024-decision-log]].
- One open, non-blocking question: Q1 (should agent-written markdown artifacts be anchored to main; deferred).
- Uncertain until the live smoke (AC-3d): whether the Claude CLI expands/passes `CONSOLE_REPO_ROOT` to the MCP server.
- T-024-01 done: baseline `2215 passed` before; AC-4a, AC-4c, AC-5a reproduced red, AC-5b green ([[T-024-progress]]).
- Next: T-024-02..05 (tasks 02/04/05 independent).

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
