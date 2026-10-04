---
ticket: "T-018"
artifact: requirements
status: frozen
frozen_date: "2026-09-16"
---

# Requirements: T-018

> Frozen summary for `requirements stories`/planner consumption. Full detail (flows, data, edge cases, business rules) lives in [[T-018-requirements-draft]] (frozen v1) — this file is the canonical short form.

## Functional Requirements
1. **FR-1** Worktree isolation defaults on for any Run tied to a ticket — reuse an existing managed worktree for that ticket if one exists, else create one via `console/server/worktrees.py`.
2. **FR-2** A Run/chat with no ticket keeps running in the shared tree, unchanged.
3. **FR-3** Worktree resolution failure (non-git-repo, `WorktreeError`) falls back to the shared tree with a surfaced, non-silent reason — never a hard failure or a silent fallback.
4. **FR-4** Every worktree created for a ticket uses a branch name encoding that ticket's id, via the existing `branch_pattern` (default `agent/{ticket}`).
5. **FR-5** `ticket.toml` gains `branch`, `pr_url`, `pr_state` fields, defaulted for backward compatibility, mutated only through a dedicated setter under the existing atomic-write lock, publishing to the MCP change bus on every mutation.
6. **FR-6** A read-only helper resolves PR state via `gh pr view` (shell-out, no API client/token), on demand or via `console/server/schedules.py`, updating `pr_url`/`pr_state` on change.
7. **FR-7** PR state transitioning to open/merged surfaces a lane **suggestion** (verify/done respectively) — never an automatic `ticket_move` or `close-work` call.
8. **FR-8** The existing Run inspector (`console/static/agents.js`) is extended to show backend, worktree path (or shared-tree/fallback reason), an "open in IDE" affordance, `git diff --stat` summary, and cost/tokens from existing telemetry.

## Non-Functional Requirements
1. **Performance** — `git diff --stat`/`gh pr view` calls stay sub-second and non-blocking, consistent with existing subprocess patterns in `worktrees.py`.
2. **Reliability** — `gh`/git failures degrade gracefully everywhere (FR-3, FR-6, FR-8); never crash Run creation or the inspector.
3. **Auditability** — every new mutation (`branch`/`pr_url`/`pr_state`) is on the same audit trail T-017 built for `claimed_by`/`claim`.
4. **Compatibility** — pre-existing tickets/Runs with none of the new fields load without error (backward-compatible defaults).
5. **Security** — no new credential storage; `gh` CLI manages its own auth outside this codebase.

## Acceptance Criteria
- [ ] `launch_role` for a ticketed Run runs with `cwd` under the configured worktree root, not `repo_root`; a second call for the same ticket reuses the same worktree.
- [ ] A ticketless chat's `cwd` is unchanged (`repo_root`).
- [ ] A non-git-repo or worktree failure produces a Run with `cwd = repo_root` and a visible fallback reason, no exception.
- [ ] A worktree created for `T-018` has a branch matching the configured pattern.
- [ ] `ticket.toml`'s new fields default cleanly on old tickets and persist correctly when set; mutation publishes to the MCP bus.
- [ ] Mocked `gh pr view` responses (`OPEN`/`MERGED`/none/ambiguous) drive `pr_state` correctly, including a clear non-fatal error for `gh` missing/unauthenticated.
- [ ] A PR-state transition surfaces a suggestion without ever calling `ticket_move`/`close-work` — verifiable by code inspection/grep.
- [ ] The Run inspector shows a real `git diff --stat` for a worktree-backed Run, "shared tree" for a ticketless one, and telemetry-accurate cost/tokens.

## Out of Scope
- GitHub-like inline review comments sent back to the agent.
- In-console app preview.
- Webhook automations beyond today's `schedules.py` mechanism.
- Any Jira/Azure/Linear/GitHub Issues tracker adapter code (including turning `gh` PR-state reads into a ticket-source adapter — it stays a read-only hint).
- The 39→12 skill harness-kernel collapse.
- Voice/barge-in/VAD work (T-015's territory).
- Any change to T-015 or T-016 artifacts or code (read-only reference only).

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
