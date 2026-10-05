---
ticket: "T-023"
artifact: analysis
---

# Analysis: T-023

## Context

Epic. The goal is for the control center to hold all of the development work on its own, with agents that carry out the dev workflow across projects. Paperclip (`D:\Workspace\research-workspace\paperclip`) runs the Claude and Codex CLIs as agents much better than the console does. This epic takes only Paperclip's **agent-execution** mechanics. The org-simulation features (CEO, hiring, org chart, company packages) are out of scope.

User decisions (2026-10-04):
- Agents wake on events; there is no timer loop.
- Permissions are set per role.
- Claude Code CLI is the only first-class backend for roles.
- The work is one epic with phased tickets.

## Current State

The console already has a solid layer for observing runs, delivered in T-016, T-018 and T-020:
- Live stream-json transcripts
- Run records with failure classes (`run_failures.py`, ported from Paperclip)
- A stall watchdog
- Capped retries
- Approval cards
- One worktree per ticket

What the console lacks is the layer that *drives* agents.

## Key Findings
- **`launch-role` is hard-wired to cursor-agent and passes no mode** (`console/server/verb_handlers.py:331-367`). Builders start in `plan` mode and cannot edit. Paperclip runs any role on Claude with `--append-system-prompt-file`, `--add-dir`, `--max-turns` and `--mcp-config --strict-mcp-config` (`packages/adapters/claude-local/src/server/execute.ts` `buildClaudeArgs`).
- **There are no sessions per ticket.** Each `delegate`/`launch-role` call starts a new chat. Paperclip keeps one session per (agent, task) and resumes it only when cwd and the prompt-bundle hash match (`heartbeat.ts` `getTaskSession` / `resolveNextSessionState`).
- **A Run covers only its first turn.** In Paperclip, Run = one wakeup and the session carries continuity between runs (`doc/spec/agent-runs.md`).
- **Nothing triggers a run.** `question_wake.deliver` only injects into a chat that is already live, and nothing consumes `ready`. Paperclip has a single `enqueueWakeup` with coalescing and wake reasons (`heartbeat.ts:26668`).
- **There is no spend cap.** Paperclip warns at 80% and hard-stops at 100% (`services/budgets.ts`).
- **The doctor only checks PATH.** Paperclip sends a hello probe through the real CLI and classifies the result (`claude-local/src/server/test.ts`).
- **Stale claims are only evaluated when a verb asks.** Paperclip reaps them in the background (`reapOrphanedRuns`, `sweepStaleIssueLocks`).
- **Bug: worktree chats resolve to the worktree, not the main repo.** Several paths are affected:
  - `telemetry.record_turn(self.cwd, …)` (`agent_session.py:472`)
  - `agent_tools.dispatch(self.cwd, …)` (`agent_api_session.py:355`)
  - the relative `.mcp.json` server path plus `paths.find_repo_root` (`paths.py:86-104`)

  Confirmed by reading the code; not yet reproduced at runtime. → [[T-024-summary]]

## Research

Three read-only surveys, done 2026-10-04: Paperclip's adapter and heartbeat internals, the console's run stack, and Paperclip's feature inventory. One correction to a common assumption: Paperclip's claude/codex adapters default to the ACP engine. The `--print --output-format stream-json` CLI lane is the one that matches the console's design.

### Folded in: console clarity audit

Source: `.cursor/plans/console_clarity_audit_25d69f3c.plan.md`. Its conclusion is to keep the codebase rather than rewrite it, and give it "one home, one work object, one launcher, and docs that match the code".

Three drift items, re-checked 2026-10-04:
- `console/static/about.js:207` says "No live steering".
- `console/README.md:17` describes a "planned native shell".
- `console/static/agents.js:16` says chats "run at the workspace root".

One audit claim is out of date: T-021 is not "unbuilt" (`T-021-progress.md` records tasks 1–17 done).

**Tension, and how it is resolved.** The audit says "do not move the seven-agent pipeline into the console". This epic stays within that rule:
- The pipeline remains in `.claude/agents/*.md` and the skills.
- The console only *launches, wakes, resumes and caps* Claude sessions that follow those protocols. It does not re-implement them.
- Every launch still goes through `agent_manager` (the audit's "one launcher").

## Recommended Path

**Order** (user decision 2026-10-04: T-025 onward waits on the Verify pile):
1. Now: [[T-029-summary]] (truth pass) and [[T-024-summary]] (worktree bug). Both are small and do not conflict.
2. Close or park the Verify pile, in this order: [[T-015-summary]], [[T-016-summary]], [[T-019-summary]] (walk each against the running shell), then [[T-020-summary]] (run the held checks, or record them as accepted limits), then [[T-021-summary]]. [[T-022-summary]]'s live smoke stays ASK-gated.
3. Then T-025 → T-028, which build on a closed Run model. [[T-030-summary]] (one chat surface) can run alongside this step.

Agent-epic phases, in dependency order. Each phase is its own ticket and runs through the full pipeline.

| Phase | Ticket | Scope |
|---|---|---|
| A | [[T-024-summary]] | Anchor every agent to the main repo: `CONSOLE_REPO_ROOT` in the child env, honoured by `find_repo_root`; telemetry and API tool dispatch on `repo_root`; an absolute MCP server path in the per-chat config |
| B | [[T-025-summary]] | New `console/config/roles.toml`: backend (default `claude`), mode, model, `max_turns`, `max_budget_usd`. Plan mode for analyst, planner, verifier and harness; `acceptEdits` for builder and fixer. Path guard on edits outside the worktree. A prompt bundle passed with `--append-system-prompt-file` on fresh sessions. Run-identity env vars. |
| C | [[T-026-summary]] | Sessions per (ticket, role) in `console/.cache/sessions/`, resumed only when cwd and bundle key match. Run = one wakeup. Chats started by hand also get a Run. |
| D | [[T-027-summary]] | `wakeups.py`: enqueue with coalescing, drained by the watchdog tick. 1 active Run per ticket plus a global cap. Triggers: a lane move, an answered question, a bug filed in verify, and a bounded continuation. All off by default. |
| E | [[T-028-summary]] | Budgets per run, per ticket and per month, from telemetry (warning at 80%, stop at 100%). A Claude hello probe in the doctor and before dispatch. A background claim reaper. |

Audit tickets that sit outside the agent phases:

| Ticket | Scope |
|---|---|
| [[T-029-summary]] | Rewrite the Agents section of About to describe live chat, and limit the one-shot caveats to `agents launch`. In the README, point "planned native shell" to `desktop/README.md` and add a "four doors, one manager" section. Fix the cwd comment in `agents.js`. |
| [[T-030-summary]] | The Assistant uses `ConsoleChatStore` / `ConsoleChatRender` instead of its own `EventSource` and log (`assistant.js:16`). `agent_manager` remains the only interactive launcher, and `agents launch` is labelled as the lesser CLI. |

Later candidates, not in this epic:
- From the audit's polish step:
  - A rotating sidecar `serve.log`
  - The chosen tray rows (dictate-without-send first; actuation stays gated)
  - Frontend tests for the chat store and the shell's Assistant-first ordering
  - Resume across a server restart (partly covered by [[T-026-summary]])
- A project/workspace registry for switching projects and tech stacks (builds on T-017's `workspace.toml`)
- Schedules that enqueue wakeups (routines)
- Codex and cursor parity

## Links
- [[T-023-summary]] · [[T-023-analysis]] · [[T-023-requirements]] · [[T-023-decision-log]] · [[T-023-plan]] · [[T-023-progress]] · [[T-023-verification]]
