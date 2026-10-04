---
ticket: "T-021"
artifact: user-stories
created: "2026-10-01"
---

# User Stories: T-021

Extracted from the frozen [[T-021-requirements]] (11 FR, iteration 3). One story per outcome; acceptance criteria are the FR checklists, not restated here (one fact, one file). Task ids are in [[T-021-plan]].

**Created by:** `requirements T-021 stories` · **Validated by:** `validate-artifacts T-021 links`

## Stories

### US-1: A lint that tells me when skill text or roster claims drift
**As a** harness maintainer
**I want** `harness lint` to warn on skill descriptions over 300 characters and on a stale roster count in `README.md`
**So that** prompt bloat and doc drift show up in a check instead of in agent behaviour
**Acceptance Criteria:** FR-1 (5 criteria), FR-4 (3 criteria)
**Business Rules:** BR-7 (WARN, never red CI)
**Edge Cases:** 20 of 39 skills already exceed 300, so the lint prints 20 warnings and 0 errors from day one; agents are out of scope; empty description stays `missing-description`.
**Related Tasks:** T-021-04
**Priority:** Medium · **Story Points:** 3

### US-2: Plans that split work only where a split earns its keep
**As a** planner
**I want** one task-boundary rule in `plan`, pointed to by `breakdown-tasks`
**So that** I write the fewest tasks that complete and verify the job, each with a stated reason to exist
**Acceptance Criteria:** FR-2 (4 criteria)
**Business Rules:** BR-9 (one fact, one file)
**Edge Cases:** the 1-4 h and 0.5-3 h size caps still bound a merged task; both `description:` lines stay byte-identical.
**Related Tasks:** T-021-02
**Priority:** Medium · **Story Points:** 2

### US-3: Docs that match the shipped system
**As a** reader of the console and desktop docs
**I want** the verifiably stale statements fixed (worktree isolation, OpenRouter default, tray, feature comparison)
**So that** I do not plan around features that shipped or ones that do not exist
**Acceptance Criteria:** FR-3 (4 criteria)
**Business Rules:** NFR-8 (limits stated where read)
**Edge Cases:** the README phrase wraps across a line break; the same files legitimately say `enabled = false` for other rows, so the agreement test scopes to OpenRouter text.
**Related Tasks:** T-021-03
**Priority:** Low · **Story Points:** 3

### US-4: An Assistant that treats clipboard, OCR and web text as data
**As a** person talking to the Assistant
**I want** it to read all of its Safety rules and to ignore instructions hidden in clipboard, OCR, screenshot or web text
**So that** text I paste cannot make it call tools, approve things or leak credentials
**Acceptance Criteria:** FR-5 (5 criteria)
**Business Rules:** BR-10 (prompt text fits the cap it is read under)
**Edge Cases:** `assistant.md` is 4,725 chars against a 4,000 cap, so "You do not approve your own tool calls" is cut off today; the cap does not move.
**Related Tasks:** T-021-01
**Priority:** High · **Story Points:** 3

### US-5: Tickets nobody is working on become visible, and prose-only `blocked` is refused
**As a** harness orchestrator or builder
**I want** `console context` to flag an in-progress, verify or blocked ticket with no live Run, held claim or pending question, and the board move into `blocked` to need a next action
**So that** abandoned work is seen at the start of the next turn and `blocked` always names what unblocks it
**Acceptance Criteria:** FR-6 (6 criteria), FR-7 (5 criteria)
**Business Rules:** BR-1, BR-4, BR-5, BR-7, BR-8
**Edge Cases:** `open` and terminal lanes exempt; a stale claim is not a path; the human `owner` is not a path; nothing already blocked is touched.
**Related Tasks:** T-021-05, T-021-08
**Priority:** High · **Story Points:** 8

### US-6: A close that checks its evidence
**As a** project owner
**I want** `ticket move ... done` to refuse when the verification table is missing, has a non-pass or empty or phantom-evidence row, or a critical blocker, stale claim, escalated review or unchecked plan task is open
**So that** "done" is backed by something a program checked, with the limit stated (existence, not truth)
**Acceptance Criteria:** FR-8 (8 criteria), FR-9 (6 criteria)
**Business Rules:** BR-1, BR-2, BR-3, BR-4, BR-11
**Edge Cases:** 84 % of historical pass rows are prose, so prose warns and never blocks; board drag and hand edits bypass the gate; check and move are not atomic.
**Related Tasks:** T-021-06, T-021-07, T-021-09, T-021-12
**Priority:** High · **Story Points:** 13

### US-7: A deliberate, audited way past a block
**As a** human at the CLI
**I want** a separate `close-override` verb that needs `confirm` and a reason of at least 10 characters and leaves an audit row and a comment
**So that** a deliberate descope is possible without editing evidence to please the check
**Acceptance Criteria:** FR-10 (4 criteria)
**Business Rules:** BR-2, BR-6
**Edge Cases:** `needs_confirm` is a stray-call guard, not the human gate (open Q11); `blocked` has no override.
**Related Tasks:** T-021-10
**Priority:** Medium · **Story Points:** 3

### US-8: Agents that report a disposition and do not close their own work
**As a** harness, verifier or builder agent
**I want** protocol text that says the verifier reports `Disposition` and stops at `close-check`, the harness or user runs `close-work`, and the builder claims on its first task
**So that** the judge does not close and the liveness remedy for `in-progress` exists
**Acceptance Criteria:** FR-11 (4 criteria)
**Business Rules:** BR-2, BR-6, BR-9
**Edge Cases:** `harness.md` has 378 chars of headroom; `verifier.md` is also edited by T-020 FR-25; no new agent or skill file.
**Related Tasks:** T-021-11
**Priority:** High · **Story Points:** 3

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Lint for skill length and roster drift | Pending | Medium | 3 | T-021-04 |
| US-2 | Task-boundary rule | Pending | Medium | 2 | T-021-02 |
| US-3 | Stale docs fixed | Pending | Low | 3 | T-021-03 |
| US-4 | Assistant untrusted-content clause | Pending | High | 3 | T-021-01 |
| US-5 | Liveness and blocked guard | Pending | High | 8 | T-021-05, T-021-08 |
| US-6 | Evidence-gated close | Pending | High | 13 | T-021-06, T-021-07, T-021-09, T-021-12 |
| US-7 | Audited override | Pending | Medium | 3 | T-021-10 |
| US-8 | Disposition, no self-close | Pending | High | 3 | T-021-11 |

## Traceability Matrix

| Story | FR | Components | Tasks |
|-------|----|-----------|-------|
| US-1 | FR-1, FR-4 | `harness_lint.py` | T-021-04 |
| US-2 | FR-2 | `plan`, `breakdown-tasks` skills | T-021-02 |
| US-3 | FR-3 | docs, `agents.py` docstring | T-021-03 |
| US-4 | FR-5 | `assistant.md`, `prompt_build.PERSONA_CAP` | T-021-01 |
| US-5 | FR-6, FR-7 | `ticket_liveness.py`, `ticket_gate.py`, `context.py`, verb | T-021-05, T-021-08 |
| US-6 | FR-8, FR-9 | `close_check.py`, `ticket_gate.py`, `kanban.py`, verb | T-021-06, -07, -09, -12 |
| US-7 | FR-10 | `verb_handlers.close_override`, `audit.py`, verb | T-021-10 |
| US-8 | FR-11 | five prompt-facing files | T-021-11 |

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-requirements-draft]] · [[T-021-user-stories]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
