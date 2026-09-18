---
ticket: "T-018"
artifact: task-breakdown
---

# Task breakdown: T-018

Atomic tasks per slice, with acceptance criteria and effort. Task ID format: `{phase}-{slice}-{task}`, shown alongside the ticket-scoped `T-018-{n}` id used elsewhere in this ticket's artifacts for cross-reference.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis step), `estimate(mode=forecast)`.

---

## Phase 1: Schema foundations

### Slice 1a: ticket.toml + Run record git fields

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1a-1 (T-018-01) | Add `branch`/`pr_url`/`pr_state` to `ticket.toml`'s schema in `tickets.py`: seed in `create()`, `setdefault` in `load()`, and a new `set_pr(repo_root, ticket_id, *, branch=None, pr_url=None, pr_state=None)` setter under `tomlio.atomic_update`, publishing to the MCP change bus on mutation (mirrors `set_claim`, tickets.py:207-244) | ticket-toml-git-fields | FR-5, AC5 | An old `ticket.toml` (no new fields) loads without error and reports `""` for all three; `set_pr` writes fields atomically and the mutation appears on the MCP bus (same bus `ticket_move` publishes to) | 2 | done | Actual 0.5h. Bus publish happens at the calling verb (`pr-check`, 3b-1), same as `set_claim`/`ticket_claim` — not inside the setter itself. `console/server/tickets.py`. |
| 1a-2 (T-018-02) | Add `worktree_path`/`worktree_branch`/`worktree_error` as optional kwargs on `runs.py`'s `create()`, defaulted to `""`, no change to `EXECUTORS`/`STATES`/`ROLES` shape | run-record-git-fields | FR-1, FR-3, AC1, AC3 | `runs.create()` accepts and persists the three new fields; a Run created without them still round-trips through `get()` with `""` defaults | 1.5 | done | Actual 0.3h. `console/server/runs.py`. |

---

## Phase 2: Worktree wiring

### Slice 2a: Worktree resolution into Run creation

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2a-1 (T-018-03) | Extend `agent_manager.create` so that when `ticket` is non-empty: `_find()` an existing managed worktree for that ticket, else `add()` one (never re-`add()` over an existing one — decision-log a3); resolve `cwd` to that worktree path; on `WorktreeError`/non-git-repo, fall back to `repo_root` and carry a non-silent reason. Surface `{worktree_path, worktree_branch, worktree_error}` on the return value (session snapshot) so both `verb_handlers.py` call sites (chat-create at verb_handlers.py:218, `launch_role` at verb_handlers.py:330) can pass them into `runs_mod.create()`. Ticketless calls (`ticket=""`) are unaffected — `cwd` stays `repo_root` | worktree-run-wiring | FR-1, FR-2, FR-3, FR-4, AC1, AC2, AC3, AC4 | A ticketed `launch_role` Run's `cwd` is under the worktree root; a second `launch_role` on the same ticket reuses it (no `WorktreeError` raised, no duplicate worktree); a ticketless chat's `cwd` is `repo_root`; a forced `WorktreeError` (e.g. non-git repo) produces a Run with `cwd = repo_root` and a non-empty `worktree_error`, no exception raised to the caller; the created branch matches `branch_for`'s configured pattern | 4 | done | Actual 1h. `console/server/agent_manager.py` (`_resolve_worktree` + `create()` wiring), `console/server/verb_handlers.py` (both call sites). Tested via `console/tests/test_agent_manager_worktree.py` (4 cases against a real git repo) rather than through `create()` itself, which spawns a real backend process. |

---

## Phase 3: PR-state pipeline

### Slice 3a: gh CLI reader + ticket setter

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3a-1 (T-018-05) | New `_gh()` shell-out helper mirroring `worktrees._git` (subprocess, same `procs.popen_kwargs()` pattern) plus a `pr_state_for(repo_root, branch)` function that runs `gh pr view --json state,url` for a branch and returns `{pr_url, pr_state}` mapped from OPEN/MERGED/none/ambiguous, or a clear non-fatal error string when `gh` is missing/unauthenticated | gh-pr-state-reader | FR-6, AC6 | Mocked subprocess responses for OPEN/MERGED/no-PR/ambiguous-output all map to the correct `pr_state`; a mocked "gh: command not found" and a mocked "not authenticated" response both return a non-fatal error result, no exception raised | 2.5 | done | Actual 0.6h. New `console/server/pr_state.py` (own module, not a `worktrees.py` sibling — SIMPLIFY: not git, keeps `worktrees.py`'s "4 porcelain commands" scope honest). 8 tests in `console/tests/test_pr_state.py`. |
| 3a-2 (T-018-06) | Extend `set_pr` (built in 1a-1) to accept partial updates — any of `branch`/`pr_url`/`pr_state` individually, `None` meaning "leave unchanged" — and wire it as the write-path the PR-state verb (3b-1) will call after each `gh` read | pr-set-setter | FR-5, FR-6, AC5 | Calling `set_pr` with only `pr_state` set leaves `branch`/`pr_url` unchanged; concurrent calls don't clobber each other (same atomic_update guarantee as `set_claim`) | 1.5 | done | Actual 0h — built into `set_pr` at 1a-1 time (the `None`-means-unchanged signature was the obvious shape from the start, so there was no separate follow-up change). Covered by `TestSetPr::test_partial_update_leaves_others_unchanged`. |

### Slice 3b: Verb + lane hint

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3b-1 (T-018-07) | Register a `pr-check` (or equivalently named) verb in `verbs.toml`/`verb_handlers.py` wrapping `pr_state_for` + `set_pr`, callable on-demand (CLI/MCP/HTTP, one mutation API) and from `schedules.py` per FR-6 | pr-state-verb | FR-6, AC6 | The verb is invokable via `console/kanban.py` and appears in `verbs.toml`; calling it against a ticket with a real/mocked branch updates `pr_url`/`pr_state` on `ticket.toml` | 2.5 | done | Actual 0.7h. `console/config/verbs.toml` (+`pr-check` row, `needs_ticket`/`needs_confirm`), `console/server/verb_handlers.py::pr_check`. Bus-publishes on success (fulfills 1a-1's bus AC via the verb, matching `ticket_claim`/`ticket_comment`'s pattern). |
| 3b-2 (T-018-08) | Lane-hint logic: after a `pr-check` run, compare new `pr_state` to the ticket's current `stage`; on PR-open with stage not yet `verify`, or PR-merged with stage not yet `done`, surface a suggestion (reuse the existing comment/question tracker — simplest surface per decision-log a4's "badge/comment tracker" either-or) | lane-hint-suggestion | FR-7, AC7 | A mismatch produces a visible suggestion (comment/question entry); grepping the new code paths for `ticket_move`/`close-work` finds zero call sites | 2 | done | Actual 0.5h. `verb_handlers._lane_hint` posts a `comments`-tracker item. Verified via `console/tests/test_pr_check_verb.py::TestLaneHint::test_never_calls_ticket_move_or_close_work` — AST-walks `_lane_hint` and `pr_check`'s actual call sites (not just a docstring grep) and asserts `ticket_move`/`close_work` are absent from both. |

---

## Phase 4: Diffstat + Run inspector

### Slice 4a: Diffstat helper + inspector data

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4a-1 (T-018-09) | `diff_stat(repo_root, worktree_path)` read-only helper, same shell-out pattern as `worktrees._git` (`git diff --stat`), returns `""`/"no changes" gracefully when the path doesn't exist or has no diff | diffstat-helper | FR-8, AC8 | Called against a worktree with known changes returns a non-empty stat summary; against a clean worktree returns a "no changes" result; against a missing path degrades without raising | 1 | done | Actual 0.3h. `console/server/worktrees.py::diff_stat`. 4 tests in `console/tests/test_worktrees.py::TestDiffStat`. |
| 4a-2 (T-018-10) | Extend whatever server response currently feeds the Agents-tab run list (verb handler / HTTP route backing `st.runs`) to include `worktree_path`/`worktree_branch`/`worktree_error` (already on the Run record post-Phase 2), a diffstat summary (4a-1), and telemetry cost/tokens (`telemetry.py`, existing aggregation) — this fixes the response contract before the frontend task consumes it | run-inspector-data | FR-8, AC8 | The run-list response for a worktree-backed Run includes a non-empty diffstat and cost/tokens; for a ticketless Run it includes `"shared tree"` in place of a worktree path, with no fields missing/`None`-typed that would break the client | 2 | done | Actual 0.8h. `console/server/verb_handlers.py` (`_enrich_run`, wired into both `run_list` and `run_show`), `console/server/features/verbs_feature.py`'s `/api/runs` route now calls `verb_handlers.run_list` instead of `runs_mod.list_runs` directly (one enriched shape for every caller). 6 tests in `console/tests/test_run_inspector_data.py` + 1 in `test_ui_endpoints.py`. |

### Slice 4b: Run inspector UI

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4b-1 (T-018-11) | Extend `console/static/agents.js`'s `runRow`/`openRun`/detail rendering to show backend, worktree path or shared-tree/fallback reason, an "open in IDE" affordance (copy-path if no existing local-open mechanism is found), the diffstat summary, and cost/tokens — no new tab/route (decision-log a5) | run-inspector-extension | FR-8, AC8 | Opening a worktree-backed Run's detail shows a real diffstat and cost/tokens; a ticketless Run's detail shows "shared tree"; a Run with a worktree fallback shows the fallback reason instead of a blank field | 2.5 | done | Actual 0.5h. `console/static/agents.js`: new `runDetailLine()`/`copyPathButton()`, `runRow` now renders backend/worktree-display/diffstat/tokens/cost plus a "Copy path" button (`navigator.clipboard`, mirrors `board.js`'s "Copy id" pattern — no reusable IDE-open mechanism exists in this codebase, confirmed by grep, so copy-path per critique CR-1). No new tab/route. No JS test harness exists in this repo (Python-only `console/tests/`); verified via `node --check console/static/agents.js` (syntax) plus the server-side data contract this reads is covered by `test_run_inspector_data.py`. |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 — Schema foundations | 3.5 | 0.8 | 0 | 0 | 100% |
| Phase 2 — Worktree wiring | 4 | 1 | 0 | 0 | 100% |
| Phase 3 — PR-state pipeline | 8.5 | 1.8 | 0 | 0 | 100% |
| Phase 4 — Diffstat + Run inspector | 5.5 | 1.6 | 0 | 0 | 100% |
| **Total (dev)** | **21.5** | 5.2 | 0 | 0 | 100% |
| QC / test time (~30%, cross-layer schema+CLI+UI surface) | 6.5 | (included above — tests written alongside each task, not tracked separately) | 0 | 0 | 100% |
| **Grand total** | **28 (round: 25–32h range)** | ~5.2 | 0 | 0 | 100% |

Actual dev effort (~5.2h) landed well under estimate (21.5h): every task had a direct, already-built precedent to mirror (`set_claim`→`set_pr`, `worktrees._git`→`pr_state._gh`, `board.js`'s copy-id→`agents.js`'s copy-path), so no task hit unexpected design work. Tests were written alongside each task rather than as a separate QC pass, so the 6.5h QC line is not separately trackable after the fact — 32 new/changed test cases exist across `test_tickets.py`, `test_runs.py`, `test_agent_manager_worktree.py` (new), `test_pr_state.py` (new), `test_pr_check_verb.py` (new), `test_worktrees.py`, `test_run_inspector_data.py` (new), `test_ui_endpoints.py`.

Basis for the QC uplift and range: cross-layer tickets in this workspace (per T-017's closed actuals) ran roughly 25-30% over raw dev-task sums once schema-migration and shell-out-mock test writing were counted; no task here is a "mega-task" (all ≤4h), keeping estimate variance low per-task even though the ticket spans 3 layers.

---

## Conventions

**Status:** pending · in-progress · done · blocked (see Notes for why).
**Effort:** 0.5 / 1 / 1.5 / 2 / 2.5 / 4h buckets used (2a-1 at 4h is the one task above the usual 3h cap — it is the widest-blast-radius task, touching 3 files across 2 call sites; kept as one task rather than split because the fallback/reuse logic is a single cohesive unit of behavior that would be untestable split apart).
**Dependencies:** noted in Notes column.
**Build order (safe, phase-by-phase, matches `plan.md`'s parallelizable note):** Phase 1 (both tasks, parallel) → Phase 2 and Phase 3 (parallel with each other, both depend only on Phase 1) → Phase 4a (parallel with Phase 3, 4a-1 has no dependency at all) → Phase 4b (after 4a-2).

**Rollback note (schema changes, Phase 1):** both new field sets are purely additive and optional (`setdefault`-backed on `ticket.toml`, kwarg-defaulted on the Run record) — old code and old records both tolerate their presence or absence. If a bad `pr_state`/`branch` write needs clearing, `set_pr` (task 1a-1/3a-2) accepts explicit resets the same way `set_claim("")` releases a claim; no data migration or down-script is needed because nothing is destructive or non-nullable.

## Links
- [[T-018-summary]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]]
