---
tags: [active]
status: In Progress
ticket: "T-022"
---

# T-022: Agent evals: golden-prompt checks for roles and skills

**Status:** In Progress  
**Stage:** TEMPLATE (eval runner and the 10 scenarios are in the tree; live smoke NOT RUN)  
**Owner:** Sohail Ali  
**Created:** 2026-10-01  
**Due:**  

## Overview

Give the 7 role agents and 39 skills a regression test. There are no agent evals today, so a prompt or skill edit cannot be checked for behaviour changes. Scope is item 9 of the Paperclip adoption dossier: a stdlib-only golden-prompt runner (proposed home `console/evals/`) that replays fixed scenarios through the `claude` backend and asserts behaviour — claim before work, stop on a conflict, `blocked` needs a reason, no-work exit. Failures are classified product / model / grading / infra, and missing usage is recorded as unknown, never zero. The point is to gate later skill changes, including any shrinking of the skill set (Paperclip's own 728-line skill is the cautionary tale: its tightening plan requires evals first).

## Current State

Built 2026-10-04: `console/evals/` replays 10 scenarios (20 fixtures) with exit 0 in under a second. `evals list --coverage` reports 7/7 agents and 33 uncovered skills. Live smoke is **NOT RUN** (Q9, Q10). Formal verify has not been closed. Design and the freeze remain in [[T-022-requirements]] and [[T-022-decision-log]].

## Links
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]]
- Predecessor roadmap: [[INV-2026-08-29-control-center-v3-dossier]]
- Related: [[T-020-summary]] · [[T-021-summary]]
- Design trail: [[T-022-context-snapshot]] · [[T-022-requirements-draft]] · [[T-022-gap-analysis]] · [[T-022-critique-report]] · [[T-022-iteration-log]] · [[T-022-plan-iteration-log]] · [[T-022-user-stories]]
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
