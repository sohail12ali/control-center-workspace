---
ticket: "T-036"
artifact: plan-iteration-log
status: active
---

# Plan iteration log: T-036

Append-only record of planning critique passes (`challenge-plan`). Does **not** bump the requirements iteration counter.

**Appended by:** `challenge-plan`, `criticize T-036 plan`

---

## Entries

### 2026-10-05 · challenge-plan · initial
- **Findings:** 12 (critical 0 / major 5 / minor 7): CR-26..CR-37 in [[T-036-critique-report]] § Plan critique
- **By kind:** traceability 1 · scope-drift 1 · contradiction 3 · sequencing-risk 2 · effort-unrealistic 1 · untestable 2 · layer-violation 0 · rollback-gap 1 · critical-path 1
- **Artifacts walked:** plan, components, task-breakdown, implementation-plan, effort-estimate (requirements read as the AC source; all present, none skipped)
- **Disposition:** 6 resolved by plan edits the same day (CR-26 scratch Node smokes in tasks 08, 09, 17; CR-27 `SERVER_PREFS` flag in tasks 07 and 09; CR-28 per-task `.pre-NN` copies; CR-29 import inside `hydrate()`; CR-32 `audit.ACTIONS` re-check in task 22; CR-37 selector-ownership tests in task 17), 6 accepted with rationale (CR-30, 31, 33, 34, 35, 36). No critical finding, so no `replan` and no question mirrored to `T-036-questions.toml`.
- **Side effects of the edits:** plan Risks grew from 20 to 23 (R-21, R-22, R-23); task 09 now needs at least 6 source tests (was 5), task 17 at least 9 (was 8); task efforts unchanged (the added work sits inside each task's basis range); build total still 44.5 h.
- **Not changed, by design:** requirements (AC-41 wording is flagged in CR-31, not rewritten; `evolve` is the route if the owner wants it changed); the other artifacts' task counts.
- **Next recommended:** `build T-036` (first build task 00, which moves the lane); re-run `challenge-plan` after any `replan` or scope-changing `evolve`; `estimate(mode=forecast)` after task 10.

## Links
- [[T-036-summary]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-effort-estimate]] · [[T-036-critique-report]]
- [[T-036-decision-log]] · [[T-036-progress]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-verification]]
