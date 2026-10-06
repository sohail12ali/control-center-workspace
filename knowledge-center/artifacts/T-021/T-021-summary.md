---
tags: [completed]
status: Complete
ticket: "T-021"
closed_date: 2026-10-05
---

# T-021: Honest close: enforce evidence, liveness and skill hygiene instead of asking for them

**Status:** Complete  
**Stage:** Closed 2026-10-05  
**Owner:** Sohail Ali  
**Created:** 2026-10-01  
**Due:**  

## Overview

Turn the honesty gates from policy into checks. Gate 6 says every "done" claim is backed by cited evidence, but nothing enforces it, and delegated builds have mis-reported before (memory `subagent-status-not-evidence`). Scope is items 7, 8 and 10–13 of the Paperclip adoption dossier: a liveness-contract lint (a non-terminal ticket needs a live run, a claim or a pending question; `blocked` needs an owner and an action), an evidence-gated `close-work`, a skill-description lint (≤ 300 chars, use-when / not-when), the plan-to-tasks boundary rule in `plan` and `breakdown-tasks`, a doc-drift audit, and an untrusted-content clause in `console/config/assistant.md`. Mostly lint rules and skill text; item 13 is the dossier's own inference, not a Paperclip finding.

## Current State

GROUND and CLARIFY are done; requirements are frozen at iteration 3 ([[T-021-requirements]]: 11 FR, 8 NFR, 11 BR). Nothing is built. Settled by GROUND: the doc-drift claims were re-checked (two of the dossier's are only partly stale; OpenRouter "ships disabled" is stale in three places); item 7 does not live in harness lint and waits for T-020's Run lifecycle, while items 10-13 do not wait; the evidence gate is calibrated to 212 historical verification rows (block on empty, phantom and non-pass evidence, warn on prose). Two slices: A (FR-1..FR-5, no T-020 dependency) and B (FR-6..FR-11, after T-020). One open, non-blocking question (Q11, a human gate on `close-override`, needs a hand edit of `agents.toml`). Next: `@planner` runs `requirements T-021 stories`.

## Close note (2026-10-05)

Closed during the Verify-pile walk ([[T-023-analysis]]). All 17 plan tasks are done, and close-check is ok: 12 rows pass, 11 of them with evidence it can resolve. The close-check, ticket gate and close-override built here were used to close T-016, T-020, T-024 and T-029 the same day. Q11 was resolved by the owner's T-020 Q12 decision: `close-override` is gated in commit `4338cb1`. TD-4 is fixed (the stale openrouter comment in `agents.toml`). TD-1 to TD-3 moved to the `_shared` todos as TD-2 to TD-4. Note: the summary had stayed at 'Open / CLARIFY' while the build finished; [[T-021-progress]] is the record. Evidence: [[T-021-verification]].

## Links
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]]
- Related: [[T-020-summary]] (run liveness and stale claims)
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-requirements-draft]] · [[T-021-context-snapshot]] · [[T-021-gap-analysis]] · [[T-021-critique-report]] · [[T-021-iteration-log]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
