---
ticket: "T-018"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
created: "2026-09-16"
last_updated: "2026-09-16"
---

# Requirements Draft: T-018

> Working requirements document. Frozen at iteration 1 — see [[T-018-iteration-log]].

**Command reference:**
- **Created by:** `requirements T-018 draft`
- **Grounded by:** `analyze T-018` → [[T-018-context-snapshot]]
- **Gaps surfaced by:** `challenge-requirements T-018 (gaps dimension)` → [[T-018-gap-analysis]]
- **Frozen by:** `requirements T-018 freeze` → [[T-018-requirements]]

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Give every agent Run its own git worktree, link tickets to their branch/PR, surface PR-state as a lane suggestion, and let the Run inspector show what changed.

**Business driver:** Concurrent agent Runs on the same ticket/repo today share one working tree — two Runs editing the same files interleave silently (per `worktrees.py`'s own stated rationale). This is the second half of the console-improvement plan, unblocked now that T-017's Run/claim/Backend-SPI plumbing is closed.

**Raw intent verbatim:**
> "Ticket-git-Run: worktree isolation per Run, ticket id in branch/PR, lane hints from PR open/merge, Run inspector diff" — ticket title; scope confirmed against `.cursor/plans/split-repo_delivery_os_4060c023.plan.md`'s T-018 section.

## 2. Context Summary

(Condensed from [[T-018-context-snapshot]])

- **Similar existing features:** [[T-017-summary]] (Run object, Backend SPI, `claimed_by`/`claimed_at` schema-extension precedent) · [[T-016-summary]] (Run object, Agents-tab inspector)
- **Affected code areas:** `console/server/worktrees.py` (reuse, minor extension), `console/server/agent_manager.py` (cwd resolution), `console/server/verb_handlers.py` (`launch_role`, new verbs), `console/server/runs.py` (schema), `console/server/tickets.py` (schema), `console/static/agents.js` (Run inspector UI)
- **Known risks from history:** worktree collision on a ticket's second Run (worktrees.py:152-155 refuses to create over an existing path); most live chats are ticketless and must not be forced into worktree isolation

## 3. Scope

### In scope
- Default worktree isolation for any Run tied to a ticket (`launch_role`, and any future ticket-scoped chat start) — reusing existing `console/server/worktrees.py` commands, not rewriting them.
- Ticket id in branch name (already implemented by `branch_for`'s `agent/{ticket}` pattern — this ticket wires Run creation to actually call it) and in PR title (a documented convention, human/agent-followed).
- `branch`, `pr_url`, `pr_state` fields on `ticket.toml`, extended the same way `claimed_by`/`claimed_at` were in T-017.
- A verb to record/refresh PR state (agent/human-driven for "opened"; `gh`-CLI-shell-out-driven, on-demand or via `console/server/schedules.py`, for "merged" detection).
- Lane **hints** surfaced to a human when PR state changes (opened → suggest `verify`; merged → suggest `done`) — never an automatic `ticket_move`; the human still runs `close-work`.
- Run inspector (extending `console/static/agents.js`'s existing run view, not a new tab): backend, worktree path, an "open in IDE" affordance, `git diff --stat` summary, cost/tokens from existing telemetry (`console/server/telemetry.py`).

### Out of scope (explicit)
- GitHub-like inline review comments sent back to the agent — a future ticket's scope, per the plan doc's own "later" list.
- In-console app preview — not requested, no infrastructure for it exists.
- Webhook automations beyond today's schedules — PR-state checks use on-demand verb calls or the existing polling `schedules.py` mechanism; no webhook receiver is built.
- Any Jira/Azure/Linear/GitHub Issues tracker adapter code — T-017 shipped the Backend SPI shape only; T-018 does not add a real adapter for any of these, including GitHub Issues (PR-state reading via `gh` CLI is not a tracker adapter — it never becomes a ticket source, only a read-only hint into the existing vault-backed ticket).
- The 39→12 skill harness-kernel collapse — unrelated, separate future ticket.
- Voice/barge-in/VAD work — T-015's territory, not touched.
- Any change to [[T-015-summary]] or [[T-016-summary]] artifacts or code — read-only reference only.

### Assumptions
- `gh` CLI is installed and authenticated on any machine that wants PR-state lane hints, given this repo is GitHub-hosted with Actions already configured (`.github/workflows`, `git remote -v`). Documented as NFR-1 / edge case rather than escalated — see [[T-018-decision-log]] a1.
- A worktree is scoped to the life of a ticket's git work, not to one single Run — a ticket that spawns multiple Runs (analyst, then builder) reuses its one managed worktree rather than erroring.

## 4. Functional Requirements

### FR-1: Worktree isolation defaults on for ticket-scoped Runs
**Description:** Any Run creation that names a ticket resolves (creating if absent, reusing if already managed) an isolated git worktree for that ticket, and the Run's session runs with that worktree as its cwd instead of the shared repo root.

**Actor:** `launch_role` verb handler; any future ticket-scoped chat-start path.

**Trigger:** A Run is created with a non-empty `ticket`.

**Preconditions:**
- The repo is a real git repository (`worktrees._require_git_repo`).
- `ticket` is a valid, non-empty ticket id.

**Flow:**
1. Look up whether a managed worktree already exists for this ticket (`worktrees.list_worktrees` + name match).
2. If yes, reuse its path as the new session's cwd.
3. If no, call `worktrees.add(repo_root, ticket)` to create one on the configured branch pattern, then use its path as cwd.
4. Record the worktree's `path` and `branch` on the Run record.
5. Start the session (`agent_session.build`) with that path as `cwd`, not `repo_root`.

**Postconditions / observable outcomes:**
- Two concurrent Runs on different tickets never share a working directory.
- Two Runs on the *same* ticket share the same worktree (sequential reuse), not a fresh one each time.

**Acceptance criteria (testable):**
- [ ] `launch_role(repo_root, ticket="T-XXX", role=...)` results in a session whose `cwd` is under the configured worktree root, not `repo_root`.
- [ ] Calling `launch_role` twice for the same ticket reuses the same worktree path (no `WorktreeError: already exists`).
- [ ] The created/reused worktree's `path` and `branch` are present on the resulting Run record.

**Business rules invoked:** BR-1, BR-2

### FR-2: Ticketless Runs keep the shared tree
**Description:** A Run/chat with no ticket (`ticket=""`) is unaffected by FR-1 — it continues to run with `cwd = repo_root`, exactly as today.

**Actor:** Any live Assistant chat started without a ticket.

**Trigger:** Run/chat creation with `ticket` empty or missing.

**Preconditions:** None beyond today's.

**Flow:**
1. Skip worktree resolution entirely when `ticket` is falsy.

**Postconditions / observable outcomes:** No behavior change for the majority of today's Assistant chats.

**Acceptance criteria (testable):**
- [ ] A chat started with no ticket has `cwd == repo_root`, unchanged from current behavior.

**Business rules invoked:** BR-1

### FR-3: Non-git-repo and worktree-failure fallback is explicit, not silent
**Description:** When the repo is not a git repository, or worktree creation otherwise fails, Run creation falls back to `cwd = repo_root` and surfaces a non-silent warning (in the Run record and/or the chat transcript) rather than failing the whole Run or hiding the fallback.

**Actor:** Run-creation path (FR-1's flow).

**Trigger:** `worktrees.add`/`_require_git_repo` raises `WorktreeError`.

**Preconditions:** None.

**Flow:**
1. Catch `WorktreeError` around the worktree-resolution step.
2. Fall back to `repo_root` as cwd.
3. Record the fallback reason on the Run record (e.g. a `worktree_error` field or an inline note), so the inspector (FR-8) can show it.

**Postconditions / observable outcomes:** A Run never silently starts in a different place than what the inspector reports.

**Acceptance criteria (testable):**
- [ ] Running `launch_role` in a non-git-repo test fixture produces a Run with `cwd = repo_root` and a visible fallback reason, not a raised exception that kills the Run.

**Business rules invoked:** BR-3

### FR-4: Ticket id encoded in branch name
**Description:** Every worktree created for a ticket uses a branch name that encodes that ticket's id, via the existing configurable `branch_pattern` (default `agent/{ticket}`).

**Actor:** `worktrees.add`/`branch_for` (already implemented — this FR is the "wire it up" requirement, not new branch logic).

**Trigger:** Worktree creation (FR-1 step 3).

**Preconditions:** None beyond FR-1's.

**Flow:** Reuse `worktrees.branch_for(repo_root, ticket)` unchanged.

**Postconditions / observable outcomes:** Every branch created by this flow contains its ticket id and is discoverable by pattern.

**Acceptance criteria (testable):**
- [ ] A worktree created for `T-018` produces a branch matching the configured pattern (default: `agent/T-018`).

**Business rules invoked:** BR-2

### FR-5: `branch`/`pr_url`/`pr_state` recorded on the ticket
**Description:** `ticket.toml` gains three new fields — `branch`, `pr_url`, `pr_state` (`""` | `"open"` | `"merged"` | `"closed"`) — defaulted for backward compatibility on old tickets, mutated only through a dedicated setter (mirroring `tickets.set_claim`).

**Actor:** Any verb/handler that creates a worktree (sets `branch`) or records a PR (sets `pr_url`/`pr_state`).

**Trigger:** Worktree creation (sets `branch`); an agent/human recording a newly opened PR, or the PR-state check (FR-6) updating `pr_state`.

**Preconditions:** Ticket exists.

**Flow:**
1. `tickets.create`/`tickets.load` gain the three new fields with `""` defaults (same pattern as `claimed_by`/`claimed_at`).
2. A new setter (e.g. `tickets.set_pr` or reuse of a generic `set_field`) writes `branch`/`pr_url`/`pr_state` under the existing atomic-write lock.
3. Every mutation publishes to the MCP change-notification bus, matching `ticket_move`'s existing pattern.

**Postconditions / observable outcomes:** `console context {T}` and the ticket card can show branch/PR state without any new read path.

**Acceptance criteria (testable):**
- [ ] A ticket created before this change loads without error and reports `branch=""`, `pr_url=""`, `pr_state=""`.
- [ ] Setting `pr_url` and `pr_state` persists to `ticket.toml` and is visible on the next `tickets.load`.
- [ ] The mutation publishes a change notification on the same bus `ticket_move` uses.

**Business rules invoked:** BR-2, BR-4

### FR-6: PR-state check via `gh` CLI shell-out
**Description:** A read-only helper resolves a ticket's PR state (open/merged/closed/none) for its recorded `branch`, by shelling out to `gh pr view --json state` (or equivalent), mirroring `worktrees.py`'s `_git()` shell-out pattern — no GitHub API client or token handling is added.

**Actor:** A verb (callable on demand) and/or a `schedules.py` job.

**Trigger:** On-demand verb call, or a configured schedule tick.

**Preconditions:** `gh` CLI installed and authenticated; ticket has a non-empty `branch`.

**Flow:**
1. Shell out to `gh pr view <branch> --json state,url` (exact args TBD at build time) in the repo root.
2. On success, update `ticket.toml`'s `pr_url`/`pr_state` via FR-5's setter if changed.
3. On `gh` missing/unauthenticated/no-PR-found, no-op (do not error the whole check) and leave state unchanged.

**Postconditions / observable outcomes:** `pr_state` reflects GitHub's real PR state without any webhook or polling daemon beyond the existing `schedules.py` clock.

**Acceptance criteria (testable):**
- [ ] Given a mocked `gh` response of `{"state": "OPEN", "url": "..."}`, the ticket's `pr_state` becomes `"open"` and `pr_url` is set.
- [ ] Given a mocked `gh` response of `{"state": "MERGED"}`, `pr_state` becomes `"merged"`.
- [ ] `gh` not installed/unauthenticated produces a clear, non-fatal error surfaced to the caller — never a silent no-op with no signal at all.

**Business rules invoked:** BR-4, BR-5

### FR-7: Lane hint on PR state change — suggestion only
**Description:** When `pr_state` transitions to `"open"`, the ticket's card/inspector shows a suggestion to move to the `verify` lane; when it transitions to `"merged"`, a suggestion to move to `done`. No automatic `ticket_move` call is ever made.

**Actor:** The FR-6 check (produces the transition); the UI/verb layer (surfaces the suggestion).

**Trigger:** `pr_state` changes from its previous value.

**Preconditions:** Ticket's current lane differs from the suggested one (no suggestion if already there).

**Flow:**
1. FR-6 detects a `pr_state` change.
2. Compare to the ticket's current `stage`.
3. If different from the lane the new state implies, surface a hint (e.g. a badge on the card, or an entry via the existing comment/question tracker) — but never call `ticket_move`.

**Postconditions / observable outcomes:** A human sees "PR opened — suggest moving to Verify" or "PR merged — suggest moving to Done" and acts (or not) explicitly.

**Acceptance criteria (testable):**
- [ ] PR transitioning to `open` while the ticket is in `in-progress` produces a visible suggestion to move to `verify`; the ticket's `stage` field is unchanged until a human runs `ticket move`.
- [ ] PR transitioning to `merged` produces a visible suggestion to move to `done`; `close-work`'s existing gate is still required to actually close.
- [ ] No code path in this ticket calls `ticket_move`/`close-work` automatically from a PR-state change.

**Business rules invoked:** BR-5, BR-6

### FR-8: Run inspector shows worktree, diffstat, IDE-open, and cost/tokens
**Description:** The existing Run detail view in `console/static/agents.js` is extended to show: backend, worktree path (or "shared tree" + fallback reason per FR-3), an "open in IDE" affordance, a `git diff --stat` summary against the worktree's base, and cost/tokens pulled from existing telemetry aggregation.

**Actor:** Anyone viewing a Run in the Agents tab.

**Trigger:** Opening a Run's detail view.

**Preconditions:** A Run record exists (any executor kind); worktree/diffstat panels degrade gracefully for a Run with no worktree (ticketless, per FR-2, or fallback per FR-3).

**Flow:**
1. Fetch the Run record (existing `run_show` verb).
2. If it has a worktree path, shell out to `git diff --stat` in that path (new small read-only helper, same shell-out pattern as `worktrees.py`).
3. Fetch telemetry aggregation for the Run's session/ticket (existing `telemetry.py` functions).
4. Render all of it in the existing run-detail panel, not a new tab.

**Postconditions / observable outcomes:** A human can see what a Run changed and what it cost without leaving the console.

**Acceptance criteria (testable):**
- [ ] Opening a Run tied to a worktree with uncommitted changes shows a non-empty `git diff --stat` summary matching what `git diff --stat` would print directly in that worktree.
- [ ] Opening a ticketless Run (no worktree) shows "shared tree" rather than an error or blank panel.
- [ ] Cost/tokens shown match the existing telemetry aggregation for that Run's session.

**Business rules invoked:** BR-7

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | `git diff --stat` and `gh pr view` calls must not block the UI thread / main server loop noticeably | Sub-second for a typical worktree; async/non-blocking if the existing chat-session infra already runs subprocess calls off the request thread | Consistent with `worktrees.py`'s own subprocess pattern |
| Reliability | `gh` CLI absence/failure never fails Run creation or the inspector view | Graceful degrade, explicit message, no crash | FR-3, FR-6, FR-8 |
| Auditability | Every `branch`/`pr_url`/`pr_state` mutation is on the same audit trail as `claimed_by`/`claim` (T-017 NFR-5 precedent) | Every mutation logged | Reuses T-017's audit mechanism, no new one built |
| Compatibility | Pre-existing tickets/Runs with no `branch`/`pr_url`/`pr_state`/worktree fields load without error | 100% backward compatible | `setdefault` pattern, per tickets.py:91-93 precedent |
| Security | No new credential storage — `gh` CLI manages its own auth outside this codebase | No token ever stored in `console/` config or TOML | Matches "no Jira/Azure/Linear/GitHub adapter code" exclusion in spirit |
| Assumption-as-dependency | `gh` CLI installed/authenticated is a documented environment assumption, not a build-time check | Not exhaustively guarded; a clear runtime message on absence (FR-6 AC3) is the only handling | Decision-log a1 |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `ticket.toml` (changed) | exists ([[T-017-summary]] added `claimed_by`/`claimed_at`) | + `branch`, `pr_url`, `pr_state` | create → update via dedicated setter → never archived (persists with the ticket) | tickets.py:38-95, FR-5 |
| Run record (changed) | exists (`runs.py`, T-016) | + `worktree_path`, `worktree_branch`, `worktree_error` (fallback reason) | set at Run creation, never mutated after (a Run's worktree is fixed for its lifetime) | runs.py:45-67, FR-1/FR-3 |

### Data flows
`worktrees.add`/`_find` → Run record (`worktree_path`/`worktree_branch`) → Run inspector (FR-8) reads Run record + shells `git diff --stat` on `worktree_path` → renders.

`gh pr view` (FR-6) → `tickets.set_pr` (FR-5) → ticket.toml `pr_url`/`pr_state` → lane-hint comparison (FR-7) → UI suggestion.

### Retention / archival
No new retention concern — fields live with their existing parent record (ticket.toml persists indefinitely per current convention; Run records already persist under `console/.cache/runs/`, gitignored, same lifecycle as today).

## 7. Business Rules

- **BR-1:** A Run is isolated into its own worktree if and only if it names a ticket; a ticketless Run always uses the shared tree.
- **BR-2:** A ticket's worktree/branch is reused across multiple Runs against that ticket, never recreated while a managed one already exists for it.
- **BR-3:** A worktree-resolution failure never fails the Run itself — it falls back to the shared tree with a surfaced, non-silent reason.
- **BR-4:** `branch`/`pr_url`/`pr_state` are mutated only through a dedicated setter under the existing atomic-write lock — never hand-edited, never written by more than one code path.
- **BR-5:** A PR-state change may only ever produce a *suggestion*; no code path in this ticket is permitted to call `ticket_move` or `close-work` automatically.
- **BR-6:** A lane hint is only shown when it would actually change something (current lane ≠ suggested lane) — no redundant nagging.
- **BR-7:** The Run inspector must degrade gracefully (never error) for any Run missing a worktree, diffstat, or telemetry data.

## 8. Edge Cases

- A ticket's worktree was manually deleted outside the console (e.g. `rm -rf`) — `worktrees.list_worktrees`/`_find` would no longer find it; FR-1 must treat this as "not found" and create fresh, not error on a stale Run-record path.
- A ticket's branch already exists (created by a human, not via `worktrees.add`) — `worktrees.add` already handles "branch exists, worktree doesn't" (worktrees.py:168-173) by checking it out rather than creating a new branch; FR-1/FR-4 rely on this unchanged.
- `gh pr view` finds more than one PR for a branch, or none — FR-6 treats "none" as `pr_state=""` (no-op) and "ambiguous" as a surfaced error, never a guess.
- Two Runs launched for the same ticket in rapid succession (race) — worktree reuse (FR-1 step 1-2) must use the same lock discipline as `tickets.set_claim`'s TOCTOU fix (T-017 decision-log a3) to avoid a double-create race.
- A worktree with uncommitted changes is asked to be removed by an unrelated cleanup path — out of scope for this ticket (existing `worktrees.remove`'s dirty-check, worktrees.py:191-197, is unchanged and untouched).

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[T-017-summary]] Backend SPI / `ticket_move` | FR-7's suggestion must never call this directly | Medium (easy to conflate "hint" with "move") | Isolate — FR-7 explicitly forbids calling `ticket_move` |
| [[T-016-summary]] Run object / Agents-tab inspector | FR-1/FR-3 extend the Run schema; FR-8 extends the existing inspector view | Low — additive fields, no removal | Modify (additively) — read-only reference for T-016's own artifacts, but its *code* (`runs.py`, `agents.js`) is the direct extension point |
| `console/server/worktrees.py` commands | FR-1/FR-4 call `add`/`list_worktrees`/`_find` as-is | Low | Reuse, no changes to worktrees.py's existing public behavior |
| `console/server/tickets.py` schema | FR-5 extends it exactly like `claimed_by`/`claimed_at` | Low | Extend, matching precedent |
| `console/server/schedules.py` | FR-6 may run as a scheduled job | Low | Reuse, no scheduler changes needed |

## 10. External Dependencies

- **`gh` CLI** (GitHub's official CLI) — must be installed and authenticated on any machine that wants PR-state lane hints (FR-6/FR-7). Not a new library dependency; a subprocess shell-out only, same pattern as `worktrees.py`'s `git` calls.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Ticket owner | Sohail Ali | Scope matches the plan doc's T-018 section; worktree isolation actually isolates concurrent Runs | yes |

## 12. Open Questions (mirrored)

None open. No blocking question required human input beyond what GROUND evidence (GitHub hosting, existing shell-out philosophy, T-017 precedent) already resolved — see [[T-018-decision-log]] for the reasoning behind each inferred decision.

## 13. Challenge Findings (⚠)

(See [[T-018-gap-analysis]] for the full pass. Findings resolved below; all accepted with rationale, none blocking.)

- ⚠ Worktree collision on a ticket's second Run — **resolution:** FR-1 explicitly requires reuse of an existing managed worktree (BR-2); addressed, not deferred.
- ⚠ Ticketless-chat regression risk if worktree isolation were unconditional — **resolution:** FR-2 makes this explicit and testable.
- ⚠ No existing GitHub/PR integration or credential story — **resolution:** decision-log a1 (shell out to `gh` CLI, no new dependency/token handling), NFR "Security" row states no token storage is added.
- ⚠ Ambiguity between "hint" and an automatic lane move — **resolution:** BR-5/FR-7 explicitly forbid automatic `ticket_move`; acceptance criteria test for it.
- ⚠ Run vs ticket as the storage location for git fields — **resolution:** decision-log a2 splits them: `branch`/`pr_url`/`pr_state` (ticket-durable identity) on `ticket.toml`; `worktree_path`/`worktree_branch`/`worktree_error` (this-execution-specific) on the Run record.

## 14. Draft History

See [[T-018-iteration-log]] for per-iteration diff + rationale.

Current iteration: **1**

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred
- [x] All ⚠ findings resolved or explicitly accepted with rationale
- [x] All blocker open questions answered (none existed)
- [x] Every FR has at least one testable acceptance criterion
- [x] Every NFR has a concrete target or documented reason for absence
- [x] Every new/changed entity has a canonical reference or creation plan
- [x] Out-of-scope list is non-empty
- [x] Stakeholder sign-off recorded (ticket owner Sohail Ali, scope matches plan doc — no separate sign-off session run since this is a solo-owned internal tooling ticket; flagged in progress notes)
- [x] `T-018-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements-draft]] · [[T-018-context-snapshot]] · [[T-018-gap-analysis]] · [[T-018-iteration-log]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
