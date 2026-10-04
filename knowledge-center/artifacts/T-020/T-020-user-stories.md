---
ticket: "T-020"
artifact: user-stories
created: "2026-10-01"
---

# User Stories: T-020

Extracted from frozen [[T-020-requirements]] (25 FR / 11 NFR / 13 BR). Each story's acceptance criteria are the FR checklists it groups, cited by id, not restated. Task links are filled from [[T-020-task-breakdown]].

**Created by:** `requirements T-020 stories` · **Validated by:** `validate-artifacts T-020 links`

## Stories

### US-1: A Run has a real lifecycle
**As a** console owner delegating work to agents
**I want** every chat Run to move through queued/running/done/failed/timed_out/interrupted/scheduled_retry and stay terminal once finished
**So that** the record never says `running` forever and every later feature can trust Run state.

**Acceptance Criteria:** FR-1, FR-2, FR-3, FR-4 checklists.
**Business Rules:** BR-1 (terminal immutable), BR-9 (no Run, no reconcile).
**Edge Cases:** Run whose session left the registry becomes `interrupted`, never `done`; a chat taking another turn after `done` is untracked; ring overflow still reconciles via `last_turn`.
**Related Components:** run-store, session-state, run-config, run-sync
**Related Tasks:** 1a-1, 1a-2, 1a-3, 1a-4
**Priority:** High · **Story Points:** 8

### US-2: Agent child processes never leak or run away
**As a** user on Windows 11 (primary) and CI on Linux/macOS
**I want** a stopped or killed agent to take its whole process tree with it, with a clean environment, bounded output and no lingering process after its result
**So that** orphan processes, runaway output and nested-session env leakage do not accumulate on my machine.

**Acceptance Criteria:** FR-5, FR-6, FR-7, FR-8, FR-9 checklists.
**Business Rules:** BR-9 (hygiene applies to every chat), BR-11 (tree kill, never a foreign group).
**Edge Cases:** `taskkill` missing or process already gone; over-long line; grandchild whose parent exited first is out of reach (documented limit).
**Related Components:** procs, session-spawn-sites, output-caps, linger-kill, process-tree-proof, ci-matrix
**Related Tasks:** 2a-1, 2a-2, 2b-1, 2b-2, 2b-3, 2c-1, 2c-2
**Priority:** High · **Story Points:** 13

### US-3: Failures are classified, including when quota resets
**As a** console owner running Runs unattended
**I want** a failed turn classified (auth, quota, transient, refusal, process lost, ...) with a reset time parsed from quota messages, and successful turns graded advanced/plan_only/empty/blocked
**So that** retry and escalation act on the real cause, and unknown text is never guessed into a retry.

**Acceptance Criteria:** FR-10, FR-11, FR-12, FR-13 checklists.
**Business Rules:** BR-2, BR-4, BR-10.
**Edge Cases:** `subtype:"success"` with `is_error:true`; quota zone unresolvable (no tzdata); refusal with exit 0; read-only modes never `plan_only`.
**Related Components:** turn-evidence, run-failures
**Related Tasks:** 3a-1, 3a-2, 3a-3, 3a-4
**Priority:** High · **Story Points:** 8

### US-4: Stalled and failed Runs recover or tell a human once
**As a** console owner who is not watching
**I want** a watchdog that flags then stops a silent Run, retries transient failures with caps and delays, and leaves one ticket comment with the next action when it gives up
**So that** a hung or rate-limited run is freed or handed back without me polling.

**Acceptance Criteria:** FR-14, FR-15, FR-16, FR-17, FR-18 checklists.
**Business Rules:** BR-2, BR-3, BR-4, BR-5, BR-9, BR-12.
**Edge Cases:** approval pending for an hour is never a stall; tick races a human stop (terminal wins); restart mid-`scheduled_retry`; `max_total_retries = 0` disables retry; watchdog off switch.
**Related Components:** run-retry-policy, run-watchdog, run-escalation, run-verbs
**Related Tasks:** 3a-5, 3b-1, 3b-2, 3b-3, 3b-4, 3c-1
**Priority:** High · **Story Points:** 13

### US-5: A dead owner's claim can be taken over safely
**As an** agent (builder after planner) or the owner
**I want** claims stamped with UTC time and linked to the owning Run, expired only when the owner is provably gone, and released or force-released with an audit trail
**So that** work is not blocked by a finished agent and a live agent's ticket is never stolen.

**Acceptance Criteria:** FR-19, FR-20, FR-21, FR-22 checklists.
**Business Rules:** BR-6, BR-7, BR-13.
**Edge Cases:** planner's linked Run done while builder's Run is live (stale `run_dead`); empty `claimed_at` is `held/unknown`; two adopters race; `scheduled_retry` counts as live.
**Related Components:** ticket-claims, claim-verbs
**Related Tasks:** 0a-1, 4a-1, 4a-2, 4a-3, 4a-4
**Priority:** High · **Story Points:** 13

### US-6: The review loop stops after three rounds and agents can see why
**As a** console owner
**I want** a per-ticket review-round counter that escalates a stalemate to me as one critical question, and `console context` showing claim, review and latest-Run facts
**So that** verifier and fixer do not loop forever and every agent reads the same facts at turn start.

**Acceptance Criteria:** FR-23, FR-24, FR-25 checklists.
**Business Rules:** BR-8 (only approved/human_decision reset).
**Edge Cases:** fourth `changes_requested` refused while escalated; older `ticket.toml` loads with 0/false; escalation question resolved but `human_decision` not called.
**Related Components:** review-counter, context-digest, agent-protocols
**Related Tasks:** 4b-1, 4b-2, 4b-3
**Priority:** Medium · **Story Points:** 5

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Run lifecycle | Pending | High | 8 | 1a-1..1a-4 |
| US-2 | Process hygiene | Pending | High | 13 | 2a-1..2c-2 |
| US-3 | Classification | Pending | High | 8 | 3a-1..3a-4 |
| US-4 | Watch, retry, escalate | Pending | High | 13 | 3a-5, 3b-1..3b-4, 3c-1 |
| US-5 | Claims | Pending | High | 13 | 0a-1, 4a-1..4a-4 |
| US-6 | Review loop + context | Pending | Medium | 5 | 4b-1..4b-3 |

## Traceability Matrix

| Story | FRs | Components | Tasks |
|-------|-----|-----------|-------|
| US-1 | FR-1..FR-4 | run-store, session-state, run-config, run-sync | 1a-1..1a-4 |
| US-2 | FR-5..FR-9 | procs, session-spawn-sites, output-caps, linger-kill, process-tree-proof, ci-matrix | 2a-1..2c-2 |
| US-3 | FR-10..FR-13 | turn-evidence, run-failures | 3a-1..3a-4 |
| US-4 | FR-14..FR-18 | run-retry-policy, run-watchdog, run-escalation, run-verbs | 3a-5, 3b-1..3b-4, 3c-1 |
| US-5 | FR-19..FR-22 | ticket-claims, claim-verbs | 0a-1, 4a-1..4a-4 |
| US-6 | FR-23..FR-25 | review-counter, context-digest, agent-protocols | 4b-1..4b-3 |

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-requirements-draft]] · [[T-020-user-stories]] · [[T-020-decision-log]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
