---
ticket: "T-018"
artifact: analysis
---

# Analysis: T-018

## Context

T-018 is the second half of the console-improvement plan (`.cursor/plans/split-repo_delivery_os_4060c023.plan.md`), depending on the now-closed [[T-017-summary]] (Run object plumbing, Backend SPI, `ready`/`claim`/`comment` verbs). Scope: (1) worktree isolation per Run by default, (2) ticket id encoded in branch/PR, (3) lane hints from PR open/merge as a human-facing suggestion, (4) a Run inspector diffstat. See [[T-018-context-snapshot]] for cited findings.

## Current State

- Worktree commands (`add`/`remove`/`prune`/`list`) exist and work (`console/server/worktrees.py`, CLI-wired in `console/kanban.py:301-318`), but nothing calls `worktrees.add()` from Run creation. `launch_role` (verb_handlers.py:301-334) and live chats (`agent_manager.create`, agent_manager.py:64-138) both run with `cwd = repo_root` — confirmed at `agent_manager.py:328`'s own docstring: **"`sess.cwd` IS the workspace root (chats run there — see `create`)"** and at the `agent_session.build` call site (agent_manager.py:113-114) where `repo_root` is passed straight through as `cwd`.
- `branch_for(repo_root, name)` (worktrees.py:92-93) already implements "ticket id in branch name" via the configurable `agent/{ticket}` pattern (`DEFAULT_BRANCH_PATTERN`, worktrees.py:38) — this part of the ask is already built, just unused by Run creation.
- No `branch`/`pr_url`/`pr_state` field exists on `ticket.toml` (tickets.py:38-95) or on the Run record (runs.py:45-67) today.
- No GitHub/PR integration of any kind exists in `console/` — confirmed by grep. The workspace's own repo, however, is GitHub-hosted with Actions already configured (`.github/workflows`, `git remote -v`), making the `gh` CLI a zero-new-dependency path to PR state.
- The Agents tab (`console/static/agents.js`) already lists Runs (`runRow`/`openRun`, agents.js:226-258) but shows only `executor/backend/executor_id` and click-through to the chat — no worktree path, diffstat, IDE-open link, or cost/tokens. T-016 explicitly designates this tab as the place the Run inspector lives, not a new surface.
- Lane ids are fixed by `console/config/boards/tickets.toml`: `open`, `in-progress`, `blocked`, `verify`, `done` (`done` terminal). "Lane hints" target `verify` (PR opened) and `done` (PR merged).

## Key Findings

- Finding: `sess.cwd IS the workspace root` (agent_manager.py:328) confirms the plan doc's central claim verbatim — worktree isolation is a real gap, not already partially done.
- Finding: The "ticket id in branch" half of scope item 1 already exists as `branch_for`'s pattern; the actual gap is (a) nothing calls it from Run creation and (b) nothing records the resulting branch back onto the ticket for the UI/PR-title convention to reference.
- Finding: `claimed_by`/`claimed_at` (tickets.py, T-017 decision-log a3) is a direct, load-bearing precedent for adding `branch`/`pr_url`/`pr_state` the same way — same file, same setdefault-for-backward-compat pattern, same "a dedicated setter is the only mutator" rule.
- Finding: Worktrees are keyed by a single `name` and refuse to be created over an existing path (worktrees.py:152-155) — a ticket that spawns more than one Run (analyst, then builder, each via `launch_role`) needs Run creation to reuse an existing managed worktree for that ticket rather than erroring on the second launch.
- Finding: Most live chats have no ticket (`ticket=""` default, agent_manager.py:66) and cannot be keyed to a per-ticket worktree — an unconditional "always isolate" default would break every ticketless Assistant conversation, which is not in scope to change.
- Finding: No PR/GitHub client exists anywhere in this codebase; the repo being GitHub-hosted with Actions already running makes `gh` CLI shell-out (mirroring `worktrees.py`'s own "shell to porcelain, not a wrapper library" philosophy) the lowest-risk, dependency-free source of PR state — consistent with the ticket's explicit exclusion of building a real GitHub tracker-adapter and of webhook automation (polling via the existing `schedules.py` mechanism, or an on-demand verb call, stays within "today's schedules").
- Finding: Telemetry (`telemetry.py`) already aggregates `cost_usd`/`input_tokens`/`output_tokens` per session/ticket — the Run inspector's cost/tokens panel is a read, not new instrumentation.

## Research

No external research needed — every piece named in scope (worktree commands, Run object, `ready`/`claim` verbs, telemetry, Agents-tab UI) already exists in this codebase per T-016/T-017. The only external system introduced is GitHub PR state, and the repo's own hosting/CI already establishes `gh` CLI as available without a new dependency or credential-handling story.

## Recommended Path

1. **Worktree-per-Run default:** extend `agent_manager.create` (or a thin wrapper called by `launch_role` and ticket-scoped chat starts) to resolve/create a managed worktree for `ticket` via `worktrees.add`/`_find` when `ticket` is non-empty, reusing an existing one if already present, and falling back to the shared tree (with a surfaced, non-silent warning) when the repo is not a git repo or `ticket` is empty. Store the resulting `path`/`branch` back onto the Run record (extend `runs.py`'s schema) since a worktree is a property of *this* run's execution, not a durable ticket-level fact by itself.
2. **Ticket id in branch/PR:** no new branch-naming code needed — reuse `branch_for`. Add `branch`, `pr_url`, `pr_state` fields to `ticket.toml` (extend `tickets.py` exactly like `claimed_by`/`claimed_at`), plus a `pr-set` verb (agent/human records the URL once opened, the same "the agent already has this, no query needed" logic `launch_role` uses elsewhere) and document the PR-title convention (`[T-{n}] <summary>`) as a human/agent-followed rule, not console-enforced.
3. **Lane hints:** a small `gh`-shell-out helper (mirroring `worktrees._git`) resolves PR state for a ticket's `branch`; a verb (callable on demand or via `schedules.py`) compares state to the ticket's current lane and, on mismatch, raises a **suggestion** (e.g. surfaced via the existing comment/question tracker or a UI badge) — never an automatic `ticket_move`. Human still runs `close-work`.
4. **Run inspector diffstat:** extend `console/static/agents.js`'s run detail view (not a new tab) to show backend, worktree path, an "open in IDE" link (reusing whatever local-open mechanism already exists, if any — else a copy-path affordance), `git diff --stat` output (new small read-only helper in `worktrees.py` or a sibling module, same shell-out pattern), and telemetry cost/tokens (already aggregated).

This path adds no new external dependency, reuses every piece of existing machinery named in the ticket, and keeps all mutation on the existing one-mutation-API pattern (CLI/MCP/HTTP as adapters over verb handlers).

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
