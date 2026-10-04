---
ticket: "T-020"
artifact: plan-iteration-log
status: active
---

# Plan iteration log: T-020

Append-only record of planning critique passes (`challenge-plan`). Does **not** bump the requirements iteration counter.

**Appended by:** `challenge-plan`, `criticize T-020 plan`

---

## Entries

### 2026-10-01 · challenge-plan · initial
- **Findings:** 19 (critical 2 / major 6 / minor 11), see [[T-020-critique-report]] § Plan critique, CR-19..CR-37.
- **Artifacts walked:** plan, components, task-breakdown, implementation-plan, effort-estimate (all present).
- **Changes made to the plan in this pass (the planner fixes its own artifacts):** CI step added as task 2c-2 (CR-19); `decide_failure` seam in 1a-4 and wired in 3a-5 (CR-20); `repo_root` and `on_limit` seam in 2a-2/2b-2 (CR-21); per-turn tool counter in 1a-2 (CR-22); `scheduled_retry` exempt from the startup sweep (CR-23); `started_utc` in 1a-2 (CR-24); `watchable` flag for API sessions (CR-25); marker-based escalation dedupe (CR-26); `list_active` terminal cache and one-shot Run grouping in `ready` (CR-32); `raised_by` on `tracker_add` (CR-33). Requirements text was not changed: every item is resolved inside the plan; none needed `evolve`.
- **Arithmetic corrected in-pass:** effort-estimate unit U6 (12.5h to 10.5h) and the Dev range (59-96h to 58-95h); totals now reconcile at 73.5h dev, 75.5h with verify.
- **Open items for the owner:** CR-19 edits `.github/workflows/verify.yml` (outside `console/`), so it needs acknowledgement before task 2c-2; CR-34 and CR-35 are accepted adjacent defects with todos to record.
- **Gate:** clear, 0 unresolved critical findings.
- **Next recommended:** `build T-020` starting at 0a-1 (T-020-01), then Phase 1 in order.

## Links
- [[T-020-summary]] · [[T-020-plan]] · [[T-020-critique-report]]
