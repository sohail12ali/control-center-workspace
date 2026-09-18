---
ticket: "T-016"
artifact: critique-report
---

# Critique report: T-016

## Requirements critique

**Last run:** 2026-09-11 · `challenge-requirements` (gaps + redteam)

| Severity | Count |
|---|---|
| critical | 2 |
| major | 4 |
| minor | 1 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | critical | unstated-assumption | draft §3 / FR-6 | Cursor may mean IDE or `cursor-agent` CLI | resolved: requirements iterate 2026-09-11 Q1b |
| CR-2 | critical | untestable | FR-6 AC | Launch cannot be observed until Q1 | resolved: FR-6 names cursor-agent |
| CR-3 | major | contradiction | FR-2 vs jobs.py:5 | Jobs track verbs, not agent subprocesses | resolved: Q2 tagged union |
| CR-4 | major | ambiguity | FR-1 | Drawers vs tabs unspecified | resolved: Q4 first tab |
| CR-5 | major | scope-creep | FR-5 / Q3 | Extra verbs not in locked In list | resolved: deferred |
| CR-6 | major | spof | §10 | Hybrid Run needs Cursor open | accepted: missing cursor-agent is honest fail |
| CR-7 | minor | nfr-unmeasurable | §5 Scalability | Cap depends on store | resolved: chats not under jobs cap |

## Plan critique

**Last run:** 2026-09-11 · `challenge-plan` (initial)

| Severity | Count |
|---|---|
| critical | 0 |
| major | 0 |
| minor | 1 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-8 | minor | sequencing-risk | plan Approach vs FR-1 “NAV_ORDER when in-shell” | Server `NAV_ORDER` cannot see `html.in-shell`; plan already mitigates via frontend sort | accepted: plan Approach names frontend sort |

Gate: **clear** (zero unresolved critical).
- [[T-016-requirements-draft]] · [[T-016-gap-analysis]] · [[T-016-decision-log]]

## Implementation critique

**Last run:** 2026-09-11 · `challenge-implementation` (all slices)

| Severity | Count |
|---|---|
| critical | 0 |
| major | 0 |
| minor | 2 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-9 | minor | test-gap | FR-1 TC-E-001 | Native-shell first tab is source-pinned (`app.js` + `html.in-shell`), not opened in Tauri this pass | accepted: no desktop session in this verify; unit pins the sort |
| CR-10 | minor | plan-drift | plan Phase 2 vs `verbs_feature.py` `GET /api/runs` | Plan allowed "verb or session extra"; a read GET was added for first-paint (no EventSource) | accepted: thinner than POST `run-list`; still not `jobs.py` |

Gate: **clear** (zero unresolved critical).

## Resolution log

| Date | Command | Notes |
|---|---|---|
| 2026-09-11 | challenge-requirements | CR-1..7 |
| 2026-09-11 | challenge-plan | CR-8 accepted |
| 2026-09-11 | challenge-implementation | CR-9, CR-10 accepted |

