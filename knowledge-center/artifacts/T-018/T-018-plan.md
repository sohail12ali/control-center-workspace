---
ticket: "T-018"
artifact: plan
---

# Plan: T-018

## Structure decision

**Multi-layer.** Surface area spans 3 real layers (data/schema, service/verb, UI) across 6 files (`tickets.py`, `runs.py`, `worktrees.py` or a sibling, `verb_handlers.py`/`verbs.toml`, `console/static/agents.js`, plus a schedules touchpoint), with 10 components and a real dependency chain (schema fields must exist before the verbs/UI that read or write them; the PR-state pipeline is 4 components deep). This exceeds the flat-mode threshold (1 component, ≤6 tasks, no chain) — routed to `analyze-components` → `breakdown-tasks` → `challenge-plan`. See [[T-018-components]] and [[T-018-task-breakdown]] for the full breakdown; this file carries Approach, Slices, and Risks only.

No new tech-select was required — `gh` CLI shell-out is already decided and recorded (decision-log a1); every other piece (worktrees, Run object, telemetry, Agents tab) is existing, in-repo machinery per [[T-018-analysis]] / [[T-018-context-snapshot]].

## Approach

Reuse everything that already exists (`worktrees.add`/`_find`/`branch_for`, the `claimed_by`/`claimed_at` schema-extension pattern, `telemetry.py` aggregation, the Agents-tab run row) and add exactly four new pieces of behavior: (1) call the existing worktree machinery from Run creation instead of leaving it unwired, (2) extend `ticket.toml` and the Run record with the git-identity fields decision-log a2 splits between them, (3) a small `gh`-CLI shell-out mirroring `worktrees._git` for PR state, feeding a suggestion-only lane hint, and (4) extend the existing Run inspector — never a new surface — with worktree/diffstat/cost fields already available or cheaply computed.

## Slices

### Slice 1 — Schema foundations
`ticket.toml` gains `branch`/`pr_url`/`pr_state`; the Run record gains `worktree_path`/`worktree_branch`/`worktree_error`. Both extend an existing, proven pattern (`claimed_by`/`claimed_at`) and have no dependency on each other — buildable and checkpoint-verifiable in parallel.

### Slice 2 — Worktree wiring
Wire `worktrees.add`/`_find` into the Run-creation path (`agent_manager.create`, consumed by both `launch_role` and ticketed chat starts) with reuse-on-second-call and non-silent fallback. Depends on Slice 1 (Run record fields to write worktree data into).

### Slice 3 — PR-state pipeline
`gh` shell-out reader → `set_pr` setter → an on-demand/`schedules.py`-callable verb → lane-hint suggestion (never `ticket_move`/`close-work`). Depends on Slice 1 (ticket fields); internally a 4-deep chain, the critical path of this ticket.

### Slice 4 — Diffstat + Run inspector
A read-only `git diff --stat` helper, a server-side extension of whatever already feeds the Agents tab's run list (to carry diffstat + telemetry to the client), then the `agents.js` UI extension itself. Depends on Slice 1 (worktree fields to display) and its own diffstat helper.

Each slice is independently checkpoint-verifiable per its own acceptance criteria (see [[T-018-task-breakdown]]) — the phased build order below supports building and reporting progress phase-by-phase without waiting on the whole ticket.

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Worktree resolution happens inside `agent_manager.create`, but the Run record is created one layer up in `verb_handlers.py` — the resolved path/branch/error must travel back up or it never reaches `runs_mod.create()`. | Med | Med | T-018-03's done-criteria explicitly requires the resolution result to surface on `agent_manager.create`'s return value (session snapshot) so both `verb_handlers.py` call sites (chat-create, `launch_role`) can pass it to `runs_mod.create()`. | Builder |
| A second `launch_role` call on the same ticket hits `worktrees.add`'s "never create over an existing path" guard (worktrees.py:152-155) if the wiring always calls `add()` instead of checking `_find()` first. | Low | Med | T-018-03's done-criteria requires a `_find()`-then-`add()` lookup, matching decision-log a3 explicitly. | Builder |
| `gh` CLI availability is an inferred fact, not verified on every machine that will run this (context-snapshot § Open Confirmations). | Med | Low | FR-6's AC already requires a clear non-fatal error path for missing/unauthenticated `gh` — T-018-05 tests this directly with a mocked subprocess; no crash regardless of environment. | Builder/Verifier |
| Lane-hint delivery surface ("badge/comment tracker") is left open by decision-log a4 ("badge/comment tracker") rather than pinned to one mechanism. | Med | Low | Not a blocking ambiguity — the only hard AC is "never calls `ticket_move`/`close-work`," which is grep-verifiable regardless of surface choice. Builder picks the simplest (reuse the existing comment tracker from T-017) and records the choice in progress.md. | Builder |
| The Agents-tab run list's current server response (feeding `agents.js`) has no diffstat/telemetry fields yet — an implicit new response-contract change. | Med | Med | Sequenced explicitly as its own task (T-018-10) before the frontend task (T-018-11), so the contract is fixed before the UI consumes it. | Builder |

No high×high risk identified — none requires escalation before build.

## Dependencies
- Blocks: —
- Blocked by: [[T-017-summary]] (closed; Run object, Backend SPI, `claimed_by`/`claimed_at` precedent — reused, not modified)

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]] · [[T-018-progress]] · [[T-018-verification]]
