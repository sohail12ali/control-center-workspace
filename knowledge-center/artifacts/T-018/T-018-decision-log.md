---
ticket: "T-018"
artifact: decision-log
---

# Decisions: T-018

## a1-gh-cli-shellout-for-pr-state
**Decision:** Read PR state via the `gh` CLI (`gh pr view --json state,url`), shelled out to exactly like `console/server/worktrees.py`'s `_git()` helper — no GitHub REST/GraphQL client, no token storage, no new dependency.
**Rationale:** GROUND-stage evidence (`git remote -v` → `github.com/sohail12ali/control-center-workspace`; `.github/workflows` exists) confirms this workspace's own repo is GitHub-hosted with Actions already configured, so `gh` CLI is a reasonable, low-risk assumption rather than an invented one. Building a real API client with credential handling would edge toward the explicitly excluded "GitHub Issues tracker adapter" territory and violate SIMPLIFY; `worktrees.py`'s own documented philosophy ("not a git wrapper... runs porcelain commands") is the direct precedent for shelling out to an already-installed CLI instead.
**Impact:** No new Python dependency, no new config file for credentials. NFR "Security" row states no token is ever stored in `console/`. A machine without `gh` installed/authenticated degrades per FR-6 AC3 (clear, non-fatal error) rather than crashing.

## a2-git-fields-split-between-ticket-and-run
**Decision:** `branch`, `pr_url`, `pr_state` live on `ticket.toml` (extended exactly like `claimed_by`/`claimed_at` in T-017 decision-log a3); `worktree_path`, `worktree_branch`, `worktree_error` live on the Run record (`runs.py`).
**Rationale:** Branch/PR identity is a property of the *ticket's* delivery work — durable across however many Runs execute against it, and the natural place a human looks up "where's the code for T-018." A worktree binding, by contrast, is fixed at the moment a specific Run starts and is meaningless to look up independent of that Run (T-016's Run object is explicitly the per-execution record). Splitting by lifecycle avoids either record owning data it doesn't semantically control, matching CANONICAL (one fact, one file).
**Impact:** `tickets.py` gains a `set_pr`-style setter following T-017's `set_claim` race-safety pattern (atomic_update). `runs.py`'s `create()` gains three optional keyword fields, defaulted to `""`, with no change to its existing tagged-union `EXECUTORS`/`STATES`/`ROLES` shape.

## a3-worktree-scoped-to-ticket-not-run
**Decision:** A worktree is created/reused per **ticket**, not per **Run** — a second `launch_role` call against the same ticket reuses the first Run's worktree rather than creating a new one.
**Rationale:** `worktrees.add` already refuses to create over an existing path and refuses two worktrees on the same branch (worktrees.py:152-165) — a "new worktree per Run" reading would make every second Run against a ticket fail outright, which cannot be the intended behavior given the ticket's own "isolation per Run" phrasing is about isolating *concurrent, different* tickets from each other, not spawning parallel checkouts of the *same* ticket. Sequential agent phases (analyst → planner → builder, all via `launch_role` against one ticket) are the common case per this workspace's own harness pipeline (CLAUDE.md's agent table), and they are not meant to run concurrently against each other on the same ticket.
**Impact:** FR-1 requires a lookup-before-create step; BR-2 states the reuse rule explicitly. True concurrent isolation (two *different* tickets, or two *different* agents on the same ticket at the same time) is still fully satisfied — the collision case this decision resolves is same-ticket, sequential-in-practice reuse, not concurrent contention.

## a4-lane-hints-never-call-ticket-move
**Decision:** PR-state-derived lane hints are surfaced as a human-visible suggestion only (badge/comment); no code path introduced by this ticket calls `ticket_move` or `close-work`.
**Rationale:** The task's own framing states this explicitly ("human still closes explicitly") and the plan doc repeats it ("merge can suggest done (human still closes via `close-work`)"). This is not inferred — it is a directly stated requirement, recorded here for traceability alongside the other decisions.
**Impact:** BR-5/BR-6, FR-7's acceptance criteria include a direct assertion that no `ticket_move` call occurs from this feature's code paths — a verifier can grep for this at build time.

## a5-run-inspector-extends-agents-tab-not-a-new-surface
**Decision:** The Run inspector diffstat/backend/worktree/cost view is built as an extension of `console/static/agents.js`'s existing run-detail rendering, not a new tab or panel.
**Rationale:** T-016's own scope statement is explicit: "the Agents tab becomes that inspector, not a parallel product" (T-016-summary.md:26). Building a second surface would directly contradict a design decision already locked in a closed-adjacent, still-open-in-Verify ticket, and would violate CANONICAL (one fact, one UI location for Run state).
**Impact:** `agents.js`'s `runRow`/`openRun`/detail-rendering functions gain new fields; no new route, tab, or top-level nav entry is added.

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
