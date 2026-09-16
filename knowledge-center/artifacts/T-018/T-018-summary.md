---
tags: [completed]
status: Complete
ticket: "T-018"
closed_date: "2026-09-16"
---

# T-018: Ticket-git-Run: worktree isolation per Run, ticket id in branch/PR, lane hints from PR open/merge, Run inspector diff

**Status:** Complete  
**Stage:** CLOSED  
**Owner:** Sohail Ali  
**Created:** 2026-09-16  
**Due:**  
**Closed:** 2026-09-16  

## Overview

Ticket-git-Run scope from `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` (T-018 section): default worktree isolation per Run (today `launch_role` and live chats share the tree — `agent_manager.py` states `sess.cwd` IS the workspace root), ticket id in branch name and PR title with `branch`/`pr_url` stored on the ticket or Run, lane hints from PR open/merge (human still closes via `close-work`), and a Run inspector showing branch/worktree path/diffstat. Depends on [[T-017-summary]] (Run object, ready/claim verbs, Backend SPI, audit log — all now closed) which this ticket builds on rather than re-derives. Out of scope: GitHub-like inline review comments, in-console app preview, webhook automations beyond today's schedules (all explicitly deferred per the plan doc).

## Current State

**CLARIFY (2026-09-16):** GROUND read of `agent_manager.py`, `runs.py`, `worktrees.py`, `verb_handlers.py`, `tickets.py`, T-016/T-017 artifacts confirmed the plan doc's claims and found no existing GitHub/PR integration; this repo's own hosting confirmed GitHub via `git remote -v`. Requirements drafted (8 FRs, 5 NFRs), `challenge-requirements` found 9 🟡 gaps (0 🔴), all self-resolved from precedent (decision-log a1-a5: `gh` CLI shell-out for PR state, ticket-vs-Run field split, worktree-per-ticket reuse, hints-never-auto-move, inspector extends existing Agents tab). Frozen at iteration 1, no open questions escalated.

**CANONICAL (2026-09-16):** `requirements stories` → 5 user stories. Read the real code surface (`tickets.py`, `runs.py`, `worktrees.py`, `agent_manager.py`, `verb_handlers.py`, `agents.js`, `schedules.py`, `setup_editor.py`) — routed **multi-layer** (10 components across data/service/UI, a 4-deep critical path, exceeds flat-mode's 1-component/≤6-task threshold). `analyze-components` → 10 components, 0 circular deps, bottleneck = `ticket-toml-git-fields`, critical path = the PR-state pipeline (ticket-toml-git-fields → gh-pr-state-reader/pr-set-setter → pr-state-verb → lane-hint-suggestion). `breakdown-tasks` → 11 tasks across 4 phases, 21.5h dev + 6.5h QC = 28h grand total (25-32h range), all 8 frozen ACs mapped. `plan risk` → 5 risks logged, 0 high×high. `challenge-plan` → 4 findings (0 critical / 2 major / 2 minor), all resolved or accepted with rationale; gate clear. No tech-select needed (`gh` CLI already decided, decision-log a1). Next: `@builder` on Phase 1.

**TEMPLATE (2026-09-16, builder):** All 11 tasks / 4 phases built and tested. Phase 1: `ticket.toml` gains `branch`/`pr_url`/`pr_state` + `set_pr` setter (`console/server/tickets.py`); Run record gains `worktree_path`/`worktree_branch`/`worktree_error` (`console/server/runs.py`). Phase 2: `agent_manager.create` resolves a per-ticket worktree (reuse-or-create, non-silent fallback) and threads it through both `delegate`/`launch_role` call sites in `verb_handlers.py`. Phase 3 (critical path): new `console/server/pr_state.py` (`gh` CLI shell-out, decision-log a1), `pr-check` verb (`console/config/verbs.toml` + `verb_handlers.pr_check`) writes PR state back via `set_pr`, and `_lane_hint` posts a suggestion comment on a PR-state transition — never a `ticket_move`/`close-work` call (decision-log a4, AST-verified). Phase 4: `worktrees.diff_stat()`, `verb_handlers._enrich_run` extends the `/api/runs` response with worktree display/diffstat/telemetry, and `console/static/agents.js`'s existing `runRow` shows it plus a copy-path affordance (decision-log a5, no new tab). Evidence: `pytest console/tests -o addopts="" -q` → 1406 passed (up from 1377 pre-ticket); SIMPLIFY pass fixed one telemetry-read inefficiency. Next: `@verifier`.

**VERIFY (2026-09-16):** `challenge-implementation` → `verify ready` → `validate-artifacts structure+links` → `reconcile`. 8/8 ACs PASS, 0 blockers, 100% FR→task→code→test traceability. Full suite independently re-run: `pytest console/tests -o addopts="" -q` → 1406 passed. Two non-blocking findings logged (a `test_never_calls_ticket_move_or_close_work` docs-accuracy overstatement, and no timeout on `pr_state.py`'s `gh` shell-out). Follow-up fix added `_GH_TIMEOUT=15` + a `subprocess.TimeoutExpired` handler in `pr_state.py`; independently re-verified in an addendum to [[T-018-verification]] — fresh full-suite re-run at 1407 passed (net-new regression test), a4 hard gate and AC1-AC8 unaffected. **Verdict: PASS.**

**CLOSED (2026-09-16):** Human explicitly approved close-work after both verification passes. No blockers outstanding.

**Artifacts:** [[T-018-context-snapshot]] · [[T-018-analysis]] · [[T-018-requirements-draft]] (frozen v1) · [[T-018-gap-analysis]] · [[T-018-decision-log]] · [[T-018-iteration-log]] · [[T-018-requirements]] (frozen) · [[T-018-user-stories]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]] · [[T-018-critique-report]] · [[T-018-plan-iteration-log]] · [[T-018-verification]]

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
