---
ticket: "T-018"
artifact: implementation-plan
---

# Implementation Plan: T-018

Master plan synthesizing [[T-018-requirements]], [[T-018-plan]], [[T-018-components]], and [[T-018-task-breakdown]]. Components and tasks are inputs here, not duplicated in full — this file adds the human-readable narrative and file-touch lists.

## Ticket summary

Ticket-git-Run: default a git worktree per ticketed Run (reused across sequential Runs on the same ticket), carry the ticket's branch/PR identity on `ticket.toml`, read PR state via `gh` CLI shell-out, surface a lane-hint suggestion on PR open/merge (human still closes explicitly), and extend the existing Agents-tab Run inspector with worktree/diffstat/cost. Builds entirely on closed T-017 (Run object, Backend SPI, `claimed_by`/`claimed_at` precedent) and in-verify T-016 (Agents tab as the inspector) — both read-only reference, not modified.

## Phase 1 — Schema foundations

Two independent schema extensions, both following the exact `claimed_by`/`claimed_at` precedent from T-017 (`tickets.py:207-244`). No behavior changes yet — this phase only makes the fields exist so later phases have somewhere to write.

### Slice 1a: ticket.toml + Run record git fields
- **Tasks:** 1a-1 (T-018-01), 1a-2 (T-018-02)
- **Files touched:** `console/server/tickets.py` (schema + `set_pr` setter), `console/server/runs.py` (`create()` kwargs)
- **Components:** ticket-toml-git-fields, run-record-git-fields
- **Requirements satisfied:** FR-5 (fully), groundwork for FR-1/FR-3
- **Acceptance criteria:** AC5 (ticket fields default/persist/publish); groundwork for AC1/AC3
- **Effort:** 3.5h
- **Checkpoint:** both schema extensions independently unit-verifiable (old-ticket load, new-field round-trip) before any wiring depends on them.

## Phase 2 — Worktree wiring

Makes FR-1/FR-2/FR-3/FR-4 real by calling the already-built `worktrees` module from the one place Run creation happens.

### Slice 2a: Worktree resolution into Run creation
- **Tasks:** 2a-1 (T-018-03)
- **Files touched:** `console/server/agent_manager.py` (`create()`), `console/server/verb_handlers.py` (chat-create call site ~line 218, `launch_role` ~line 330)
- **Components:** worktree-run-wiring
- **Requirements satisfied:** FR-1, FR-2, FR-3, FR-4
- **Acceptance criteria:** AC1, AC2, AC3, AC4
- **Effort:** 4h
- **Checkpoint:** independently verifiable via three scenarios — ticketed launch (worktree cwd), ticketless chat (unchanged cwd), forced failure (fallback + reason) — before Phase 3/4 need any of it.
- **Depends on:** Phase 1 (run-record-git-fields for the write-back target).

## Phase 3 — PR-state pipeline

The ticket's deepest dependency chain (4 components) and its critical path. Entirely new functionality — no existing PR/GitHub code to extend.

### Slice 3a: gh CLI reader + ticket setter
- **Tasks:** 3a-1 (T-018-05), 3a-2 (T-018-06)
- **Files touched:** new `_gh()`/`pr_state_for()` (in `console/server/worktrees.py` as a sibling function, or a new small `console/server/pr_state.py` — builder's call at implementation time, given SIMPLIFY), `console/server/tickets.py` (`set_pr` completeness check)
- **Components:** gh-pr-state-reader, pr-set-setter
- **Requirements satisfied:** FR-5, FR-6
- **Acceptance criteria:** AC5, AC6
- **Effort:** 4h
- **Depends on:** Phase 1 (ticket-toml-git-fields for `branch` to query and fields to write).

### Slice 3b: Verb + lane hint
- **Tasks:** 3b-1 (T-018-07), 3b-2 (T-018-08)
- **Files touched:** `console/config/verbs.toml`, `console/server/verb_handlers.py`, `console/config/schedules.toml` (optional — any registered verb is already schedulable via its `verb =` row, `schedules.py:102`, so no `schedules.py` code change is needed), the existing comment/question tracker module for the suggestion surface
- **Components:** pr-state-verb, lane-hint-suggestion
- **Requirements satisfied:** FR-6, FR-7
- **Acceptance criteria:** AC6, AC7
- **Effort:** 4.5h
- **Depends on:** Slice 3a.
- **Checkpoint:** AC7 ("no `ticket_move`/`close-work` call path") is grep-verifiable independent of everything else in the ticket — a cheap, high-value verification gate.

## Phase 4 — Diffstat + Run inspector

Extends the existing Agents-tab inspector (decision-log a5) — no new UI surface.

### Slice 4a: Diffstat helper + inspector data
- **Tasks:** 4a-1 (T-018-09), 4a-2 (T-018-10)
- **Files touched:** new `diff_stat()` helper (same module choice as Slice 3a's helper — colocate with `worktrees.py` or the new pr-state sibling), the server route/verb backing `console/static/agents.js`'s `st.runs` data
- **Components:** diffstat-helper, run-inspector-data
- **Requirements satisfied:** FR-8
- **Acceptance criteria:** AC8 (data half)
- **Effort:** 3h
- **Depends on:** Phase 1 (worktree fields on the Run record) for 4a-2; 4a-1 has no dependency and can start anytime.

### Slice 4b: Run inspector UI
- **Tasks:** 4b-1 (T-018-11)
- **Files touched:** `console/static/agents.js` (`runRow`, `openRun`, detail rendering)
- **Components:** run-inspector-extension
- **Requirements satisfied:** FR-8
- **Acceptance criteria:** AC8 (UI half, completing the criterion)
- **Effort:** 2.5h
- **Depends on:** Slice 4a (the data contract must exist before the UI renders it).

## Build order (critical path)

```
Phase 1 (1a-1, 1a-2 — parallel)
   ├─→ Phase 2 (2a-1)                         ─┐
   ├─→ Phase 3a (3a-1, 3a-2 — parallel)         │  Phase 2 and Phase 3
   │       └─→ Phase 3b (3b-1 → 3b-2)          │  proceed in parallel;
   └─→ Phase 4a-2 (needs 1a-2)                 │  both depend only on
           (4a-1 has no dependency —            │  Phase 1
            can start anytime)                 ─┘
Phase 4a (4a-1, 4a-2) → Phase 4b (4b-1)
```

Critical path (longest chain): **Phase 1 → 3a-1/3a-2 → 3b-1 → 3b-2** (4 tasks, ~11.5h of the ~19h dev total) — this is the ticket's PR-state pipeline, matching `T-018-components.md`'s graph analysis. Phase 2 and Phase 4 are not on the critical path and can be built/verified in whatever order suits checkpoint reporting.

## Effort reconciliation

Task-breakdown summary (corrected): Phase 1 3.5h + Phase 2 4h + Phase 3 8.5h (3a-1 2.5h + 3a-2 1.5h + 3b-1 2.5h + 3b-2 2h) + Phase 4 5.5h = **21.5h dev**, + ~6.5h QC (30%) = **28h grand total (25-32h range)**. This implementation plan's phase totals (3.5 + 4 + 8.5 + 5.5 = 21.5h) match task-breakdown's effort-summary table exactly — no drift.

## Links
- [[T-018-summary]] · [[T-018-requirements]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]]
