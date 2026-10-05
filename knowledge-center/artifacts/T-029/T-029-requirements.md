---
ticket: "T-029"
artifact: requirements
---

# Requirements: T-029

Source: step 1 of `.cursor/plans/console_clarity_audit_25d69f3c.plan.md`; roadmap in [[T-023-analysis]].

## Functional Requirements
1. FR-1 `about.js` Agents section describes the live steerable chat (approval card, per-ticket worktree); the one-shot limits (no steering, no worktree, no approval gate, plan-mode default) appear only in one sentence about `kanban.py agents launch`.
2. FR-2 `console/README.md` points at `desktop/` / `desktop/README.md` instead of "planned native shell".
3. FR-3 `console/README.md` gains a "four doors, one manager" section plus the four naming traps.
4. FR-4 The `agents.js` header comment says ticketed chats run in a per-ticket worktree.

## Non-Functional Requirements
1. Every new factual sentence is checked against code (file:line in [[T-029-verification]]).
2. No behaviour change; no edits to `console/server/*.py`.

## Acceptance Criteria
- [ ] AC-1 (FR-1) No "headless one-shot" / "No live steering" claim about the Agents tab remains in `about.js`.
- [ ] AC-2 (FR-2) "planned native shell" is gone from `console/README.md`.
- [ ] AC-3 (FR-3) README section names four doors and `backends/`, `jobs.py`, `agents.py`, `runs.py`.
- [ ] AC-4 (FR-4) `agents.js` no longer says chats run at the workspace root unconditionally.
- [ ] AC-5 `console/tests/test_docs_agree_with_config.py` still passes.

## Out of Scope
- Steps 2-4 of the audit (verify pile, shared chat store, polish).
- Editing `console/server/*.py` docstrings (T-024 is working there).

## Links
- [[T-029-summary]] · [[T-029-analysis]] · [[T-029-requirements]] · [[T-029-decision-log]] · [[T-029-plan]] · [[T-029-progress]] · [[T-029-verification]]
