---
ticket: "T-018"
artifact: components
---

# Components: T-018

Tracks every component this ticket touches, its dependencies, and its build status.

**Produced by:** `analyze-components`. **Consumed by:** `breakdown-tasks`.

---

## Data layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| ticket-toml-git-fields | schema extension | `branch`/`pr_url`/`pr_state` on `ticket.toml`, defaulted for backward compat (`tickets.py` `create`/`load`), same pattern as `claimed_by`/`claimed_at` | — | 1 | FR-5, AC5 | pending |
| run-record-git-fields | schema extension | `worktree_path`/`worktree_branch`/`worktree_error` on the Run record (`runs.py` `create`) | — | 1 | FR-1, FR-3, AC1, AC3 | pending |

## Service layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| worktree-run-wiring | service logic | Resolve/reuse/create a per-ticket worktree from `agent_manager.create` (consumed by both `launch_role` and ticketed chat-start call sites in `verb_handlers.py`); fallback to `repo_root` with a surfaced reason on `WorktreeError`/non-git-repo; write result onto the Run record | run-record-git-fields; `worktrees.add`/`_find`/`branch_for` (existing, unmodified) | 2 | FR-1, FR-2, FR-3, FR-4, AC1, AC2, AC3, AC4 | pending |
| gh-pr-state-reader | external CLI shell-out | `gh pr view --json state,url` shelled out to (mirrors `worktrees._git`), parses OPEN/MERGED/none/ambiguous, degrades non-fatally if `gh` missing/unauthenticated | ticket-toml-git-fields (needs `branch` to query) | 3 | FR-6, AC6 | pending |
| pr-set-setter | data mutator | `tickets.set_pr`-style setter (branch/pr_url/pr_state), atomic-lock mutation, publishes to the MCP change bus, mirrors `set_claim`'s race-safety | ticket-toml-git-fields | 3 | FR-5, FR-6, AC5 | pending |
| pr-state-verb | verb handler | On-demand (and `schedules.py`-callable) verb wrapping gh-pr-state-reader + pr-set-setter; registered in `verbs.toml`/`verb_handlers.py` | gh-pr-state-reader, pr-set-setter | 3 | FR-6, AC6 | pending |
| lane-hint-suggestion | business logic | Compares new `pr_state` to the ticket's current lane; on open→verify / merged→done mismatch, raises a human-visible suggestion; contains **no** `ticket_move`/`close-work` call path (decision-log a4) | pr-state-verb | 3 | FR-7, AC7 | pending |
| diffstat-helper | read-only git helper | `git diff --stat` for a worktree path, same shell-out pattern as `worktrees._git`, degrades gracefully (no worktree / no changes) | — | 4 | FR-8, AC8 | pending |
| run-inspector-data | service/API | Extends whatever server response already feeds the Agents-tab run list with diffstat output + telemetry cost/tokens, alongside the worktree fields already on the Run record | run-record-git-fields, diffstat-helper, `telemetry.py` (existing, unmodified) | 4 | FR-8, AC8 | pending |

## UI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| run-inspector-extension | view extension | `console/static/agents.js` `runRow`/`openRun`/detail rendering extended with backend, worktree path or shared-tree/fallback reason, "open in IDE" affordance, diffstat summary, cost/tokens — no new tab/route (decision-log a5) | run-inspector-data | 4 | FR-8, AC8 | pending |

---

## Dependency graph

```
ticket-toml-git-fields
  └─ pr-set-setter
  |    └─ pr-state-verb
  |         └─ lane-hint-suggestion
  └─ gh-pr-state-reader
       └─ pr-state-verb (see above)

run-record-git-fields
  └─ worktree-run-wiring (also reads worktrees.add/_find/branch_for — existing)
  └─ run-inspector-data
       └─ run-inspector-extension

diffstat-helper
  └─ run-inspector-data (see above)
```

### Graph analysis

- **Root (no deps):** ticket-toml-git-fields, run-record-git-fields, diffstat-helper.
- **Leaf (nothing depends on them):** worktree-run-wiring, lane-hint-suggestion, run-inspector-extension.
- **Middle:** pr-set-setter, gh-pr-state-reader, pr-state-verb, run-inspector-data.
- **Circular deps:** none.
- **Isolated components:** none — every component sits on a path to ≥1 acceptance criterion.
- **Critical path:** `ticket-toml-git-fields → {pr-set-setter, gh-pr-state-reader} → pr-state-verb → lane-hint-suggestion` — 4 components deep, the longest chain in the ticket (Slice 3, the PR-state pipeline).
- **Bottleneck:** `ticket-toml-git-fields` — 4 downstream components (pr-set-setter, gh-pr-state-reader indirectly via needing `branch`, pr-state-verb, lane-hint-suggestion) all sit behind it; it is Slice 1 and scheduled first for exactly this reason.
- **Parallelizable:** yes — Slice 1's two components have no mutual dependency (build together); Slice 2 (worktree wiring) and Slice 3 (PR pipeline) share no dependency on each other once Slice 1 is done and can proceed in parallel; Slice 4's diffstat-helper is independent of everything and can start anytime.

---

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data | 2 | 2 | 0 | 0 |
| Service | 6 | 6 | 0 | 0 |
| UI | 1 | 1 | 0 | 0 |
| **Total** | 9 | 9 | 0 | 0 |

*(Note: run-inspector-data straddles service/API — counted once, under Service, to avoid double-counting against the UI total.)*

## Links
- [[T-018-summary]] · [[T-018-requirements]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]]
