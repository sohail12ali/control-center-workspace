---
ticket: "T-020"
artifact: effort-estimate
basis: "components"
confidence: "Medium"
---

# Effort estimate: T-020

**Produced by:** `estimate T-020 --mode upfront`. **Sources:** [[T-020-requirements]] · [[T-020-components]]. Task-level hours in [[T-020-task-breakdown]] reconcile to the Dev row below.

| Field | Value |
|-------|-------|
| Basis | components (21 components grouped into 12 estimable units) |
| Units estimated | 12 |
| Confidence | Medium (0.8x - 1.3x of most likely) |

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development (tasks incl. their own tests) | 73.5 | 58 | 95 | 9.2 |
| QC (derived, see note) | 41 | 32 | 41 | 5.1 |
| Risk reserve (components +10%) | 11.5 | - | - | 1.4 |
| **Final / Complete** | **126** | **90** | **136** | **15.8** |

> Calendar days are indicative only; no capacity or parallelism model. **Note:** every task is test-first, so Dev already includes authoring the automated tests. The QC row is the formula result (service ratio 25%, high-risk cycle x1.8 because process, concurrency and Windows adders are present) and covers verifier cycles, manual Windows probing and re-test rounds; phase 5 (2h, task 5a-1) is the only QC work scheduled as a task. The formula is a placeholder tuned for generic stacks, so treat QC as an upper envelope, not a commitment. Dev only: 9 working days, which matches the dossier's "about 2 weeks" once QC and CI waits are added.

## Units

| Unit | Source components | Layer | Size | M (h) | Adders | Lower | Upper | Notes |
|------|-------------------|-------|------|------:|--------|------:|------:|-------|
| U1 | run-store, run-config | data | M | 5 | concurrency +25% (folded) | 4 | 6.5 | tasks 1a-1, 1a-3 |
| U2 | session-state, run-sync | service | L | 6 | concurrency | 4.5 | 8 | 1a-2, 1a-4 |
| U3 | procs, session-spawn-sites | service | L | 6 | cross-platform | 4.5 | 8 | 2a-1, 2a-2 |
| U4 | output-caps, linger-kill | service | L | 8 | concurrency, >100 LOC rewrite | 6 | 10 | 2b-1..2b-3 (reader loops rewritten) |
| U5 | process-tree-proof, ci-matrix | e2e test | M | 4 | external (Windows tools) | 2.5 | 6 | 2c-1, 2c-2 |
| U6 | turn-evidence, run-failures (classify, quota, liveness) | service | XL | 10.5 | unknown zone data | 8.5 | 13.5 | 3a-1..3a-4 |
| U7 | run-retry-policy | service | M | 3 | - | 2.5 | 3.8 | 3a-5 |
| U8 | run-watchdog, run-escalation | service | XL | 10 | concurrency | 8 | 13 | 3b-1..3b-4 |
| U9 | run-verbs | verb | M | 3 | - | 2.5 | 3.8 | 3c-1 |
| U10 | ticket-claims-data, claim-verbs | data+verb | XL | 11 | concurrency, >100 LOC | 8.5 | 14 | 4a-1..4a-4 |
| U11 | review-counter, context-digest, agent-protocols | verb+docs | L | 6 | - | 5 | 7 | 4b-1..4b-3 |
| U12 | baseline date-rot fix | test | XS | 1 | - | 0.8 | 1.3 | 0a-1 (5a-1, 2h final verify, is counted under QC) |
| **Dev total (excl. 5a-1)** | | | | **73.5** | | **58** | **95** | |

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| R-1 | [[T-020-critique-report]] CR-31 | `agent_session.py` reader loops are rewritten twice (2b-1, 2b-3); regressions in unrelated chat tests widen U4 |
| R-2 | requirements Open Confirmation (no real `claude`) | `resetsAt` units and nesting guard unconfirmed; design accepts both, no hours added |
| R-3 | Windows process lessons (memory `cross-platform-defects-only-ci-finds`) | CI-only defect on a runner we cannot see locally adds a fix round to U5 |

## Recommendations
1. Build phases in order; do not parallelise `agent_session.py` tasks.
2. Re-forecast with `estimate(mode=forecast)` after phase 2 (about 5 completed tasks gives Medium confidence).
3. Resolve the CI workflow edit (CR-19) with the owner before task 2c-2.

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-10-01 | components | 73.5 | 41 | 126 | 90-136 | Initial sizing from [[T-020-components]]; task totals reconcile to 73.5h Dev + 2h verify |

## Links
- [[T-020-summary]] · [[T-020-requirements]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-effort-estimate]] · [[T-020-plan]]
