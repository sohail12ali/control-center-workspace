---
ticket: "T-018"
artifact: user-stories
created: "2026-09-16"
---

# User Stories: T-018

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-018 stories` · **Validated by:** `validate-artifacts T-018 links` · **Verified by:** `validate-artifacts T-018 links`

## Stories

### US-1: Worktree isolation per Run

**As a** developer running multiple agent sessions against different tickets
**I want to** every ticketed Run to get its own git worktree, reused across sequential Runs on the same ticket
**So that** concurrent or sequential agent work on different tickets never interleaves file changes in the shared tree

**Acceptance Criteria:**
- [ ] `launch_role` for a ticketed Run runs with `cwd` under the configured worktree root, not `repo_root`; a second call for the same ticket reuses the same worktree.
- [ ] A ticketless chat's `cwd` is unchanged (`repo_root`).
- [ ] A non-git-repo or worktree failure produces a Run with `cwd = repo_root` and a visible fallback reason, no exception.
- [ ] A worktree created for a ticket has a branch matching the configured `branch_pattern`.

**Business Rules:**
- One worktree per ticket, reused across sequential Runs (decision-log a3) — never recreated per Run.
- Ticketless Runs/chats are unaffected (FR-2) — no default-on change to their `cwd`.

**Edge Cases:**
- Repo is not a git repo → fallback to shared tree, non-silent reason (FR-3).
- Second `launch_role` call on the same ticket while the first worktree still exists → reuse, not a `WorktreeError` crash (a3, worktrees.py:152-165).

**Related Components:** run-record-git-fields, worktree-run-wiring
**Related Tasks:** T-018-02, T-018-03

**Priority:** High
**Story Points:** 8

---

### US-2: Ticket carries branch/PR identity

**As a** human tracking a ticket's delivery
**I want to** `ticket.toml` to record the branch, PR URL, and PR state for the work
**So that** I can find "where's the code for this ticket" from the ticket itself, durable across however many Runs execute against it

**Acceptance Criteria:**
- [ ] `ticket.toml`'s new fields (`branch`, `pr_url`, `pr_state`) default cleanly on old tickets and persist correctly when set; mutation publishes to the MCP bus.

**Business Rules:**
- Fields are mutated only through a dedicated setter under the existing atomic-write lock (mirrors `set_claim`, decision-log a2/a3).
- Backward-compatible: old `ticket.toml` files without these fields load without error.

**Edge Cases:**
- Concurrent mutation of `pr_state` from two callers — race-safe via `tomlio.atomic_update`, same pattern as `set_claim`.

**Related Components:** ticket-toml-git-fields, pr-set-setter
**Related Tasks:** T-018-01, T-018-06

**Priority:** High
**Story Points:** 3

---

### US-3: Read-only PR state via `gh` CLI

**As a** the console
**I want to** resolve a ticket's PR state (open/merged/none/ambiguous) by shelling out to `gh pr view`, on demand or on a schedule
**So that** the board can reflect real PR state without a GitHub API client, token storage, or a new dependency

**Acceptance Criteria:**
- [ ] Mocked `gh pr view` responses (`OPEN`/`MERGED`/none/ambiguous) drive `pr_state` correctly, including a clear non-fatal error for `gh` missing/unauthenticated.

**Business Rules:**
- Shell-out only (decision-log a1) — no REST/GraphQL client, no credential storage in `console/`.
- Failures degrade gracefully (NFR Reliability) — never crash Run creation or any verb call.

**Edge Cases:**
- `gh` not installed → clear non-fatal error surfaced, `pr_state` left unchanged.
- `gh` installed but unauthenticated → same non-fatal degradation.
- No PR exists for the branch → `pr_state` reflects "none", not an error.

**Related Components:** gh-pr-state-reader, pr-set-setter, pr-state-verb
**Related Tasks:** T-018-05, T-018-06, T-018-07

**Priority:** High
**Story Points:** 5

---

### US-4: Lane hint from PR state, never an automatic move

**As a** human who owns the board
**I want to** see a suggestion when a ticket's PR opens or merges (move to verify / done)
**So that** I stay in control of `ticket_move`/`close-work` while still getting a nudge, per decision-log a4

**Acceptance Criteria:**
- [ ] A PR-state transition surfaces a suggestion without ever calling `ticket_move`/`close-work` — verifiable by code inspection/grep.

**Business Rules:**
- Suggestion only — no code path introduced by this ticket calls `ticket_move` or `close-work` (a4, BR-5/BR-6).
- Lane targets: PR open → `verify`, PR merged → `done` (board lane ids from `console/config/boards/tickets.toml`).

**Edge Cases:**
- PR state flips back (e.g. merged PR reverted) — out of scope to auto-correct; next poll just reports current state.

**Related Components:** lane-hint-suggestion, pr-state-verb
**Related Tasks:** T-018-07, T-018-08

**Priority:** Medium
**Story Points:** 3

---

### US-5: Run inspector shows worktree, diff, and cost

**As a** developer watching a Run
**I want to** the existing Agents-tab Run view to show backend, worktree path (or shared-tree/fallback reason), an "open in IDE" affordance, a `git diff --stat` summary, and cost/tokens
**So that** I can judge a Run's real-world impact without leaving the console, per T-016's "Agents tab is the inspector" decision (a5)

**Acceptance Criteria:**
- [ ] The Run inspector shows a real `git diff --stat` for a worktree-backed Run, "shared tree" for a ticketless one, and telemetry-accurate cost/tokens.

**Business Rules:**
- Extends `console/static/agents.js`'s existing run-detail rendering — no new tab, panel, or route (a5).
- Reads existing telemetry aggregation (`telemetry.py`) — no new instrumentation.

**Edge Cases:**
- Worktree resolution failed for this Run → inspector shows the fallback reason, not a blank/error state.
- `git diff --stat` on a worktree with no changes → renders "no changes" rather than an empty/broken panel.

**Related Components:** diffstat-helper, run-inspector-data, run-inspector-extension
**Related Tasks:** T-018-09, T-018-10, T-018-11

**Priority:** Medium
**Story Points:** 5

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Worktree isolation per Run | Pending | High | 8 | T-018-02, T-018-03 |
| US-2 | Ticket carries branch/PR identity | Pending | High | 3 | T-018-01, T-018-06 |
| US-3 | Read-only PR state via `gh` CLI | Pending | High | 5 | T-018-05, T-018-06, T-018-07 |
| US-4 | Lane hint from PR state, never an automatic move | Pending | Medium | 3 | T-018-07, T-018-08 |
| US-5 | Run inspector shows worktree, diff, and cost | Pending | Medium | 5 | T-018-09, T-018-10, T-018-11 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | run-record-git-fields, worktree-run-wiring | T-018-02, T-018-03 |
| US-2 | ticket-toml-git-fields, pr-set-setter | T-018-01, T-018-06 |
| US-3 | gh-pr-state-reader, pr-set-setter, pr-state-verb | T-018-05, T-018-06, T-018-07 |
| US-4 | lane-hint-suggestion, pr-state-verb | T-018-07, T-018-08 |
| US-5 | diffstat-helper, run-inspector-data, run-inspector-extension | T-018-09, T-018-10, T-018-11 |

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements-draft]] · [[T-018-user-stories]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
