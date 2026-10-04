---
tags: [active]
status: Open
ticket: "T-020"
---

# T-020: Reliable Runs: classify failures, catch stalls, retry with caps, reap stale claims

**Status:** Open  
**Stage:** VERIFY (built and independently verified; held in `verify` — see Current State)
**Owner:** Sohail Ali  
**Created:** 2026-10-01  
**Due:**  

## Overview

Make a Run survive the ways agent runs actually fail. Today a Run is a pointer record: no stall watchdog, no retry or backoff, no failure classification, and `claimed_at` is recorded but never read. Scope is items 1–6 of the Paperclip adoption dossier: Claude failure classifiers (incl. quota-reset parsing), run-liveness classifier plus stall watchdog, retry table with caps, child-process hygiene (Windows tree-kill), stale-claim rule, and a 3-round review-loop cap. Console server only; stdlib Python.

## Current State

All 30 plan tasks built and independently verified 2026-10-02/03: full suite **1867 passed, 0 failed**, `harness lint` 0/0 at 39 skills and 7 agents, `console/static` untouched ([[T-020-verification]]). The verifier found three real defects, all fixed and re-verified: D-A (`run-watch` from the CLI/MCP would have interrupted healthy Runs; now returns `skipped` outside the server), D-B (output-cap failures were silent), D-C (Windows `os.replace` flake; bounded retry, 20/20 concurrency loop). Baseline bug D-1 (3 date-rotted stop-hook tests) verified fixed.

**Held in `verify`, not closed**, because five acceptance rows cannot be verified here: the new Windows CI step has not run on a real runner (Q15, local edit only, nothing pushed); Claude's `resetsAt` units and the `CLAUDECODE` nesting guard were never checked against a real `claude` (Q14); the human gate on `claim-release force` and `review-round human_decision` needs a hand edit of `agents.toml` `gated_tools` (Q12); the phone alert needs a `console.toml` edit (Q13). T-021 consumes `tickets.claim_status`, `claimed_run`, `review_escalated`, `runs.ACTIVE` and the FR-23 digest keys exactly as built.

## Links
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]]
- Related: [[T-021-summary]] (liveness lint builds on this ticket's run-liveness and stale-claim work) · [[T-022-summary]] (evals gate later changes)
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-requirements-draft]] · [[T-020-context-snapshot]] · [[T-020-gap-analysis]] · [[T-020-critique-report]] · [[T-020-iteration-log]] · [[T-020-decision-log]] · [[T-020-user-stories]] · [[T-020-components]] · [[T-020-effort-estimate]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-plan-iteration-log]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
