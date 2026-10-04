---
ticket: "T-018"
artifact: critique-report
status: active
---

# Critique Report: T-018

Adversarial critique findings across stages. Find-don't-fix — resolutions happen via the owning stage's repair command.

## Plan critique

**Last run:** 2026-09-16 · `challenge-plan T-018`
**Summary:** 4 findings (critical 0 / major 2 / minor 2)

| CR-{n} | Severity | Kind | Pointer | Issue | Resolution |
|--------|----------|------|---------|-------|------------|
| CR-1 | minor | untestable | T-018-task-breakdown.md § 4b-1; requirements.md FR-8 | "Open in IDE affordance" has no reusable existing mechanism in this codebase — `console/server/setup_editor.py` only configures editor MCP servers, it does not open a given path in an editor — and FR-8's own AC bullet doesn't pin down the interaction, so "affordance" stays builder-decidable | accepted: not blocking — AC8 doesn't specify a mechanism; task 4b-1's Notes already default to a copy-path affordance if no local-open mechanism exists, verified true by this critique pass |
| CR-2 | minor | sequencing-risk | T-018-implementation-plan.md § Phase 3, Slice 3b file-touch list | Original draft listed `console/server/schedules.py` as a file to touch for the on-demand/scheduled PR-check verb; confirmed by reading `schedules.py:102` (`self.verb = (row.get("verb") or "").strip()`) that any registered verb is already schedulable via `console/config/schedules.toml` with no `schedules.py` code change needed | resolved: implementation-plan.md corrected in this pass to list `console/config/schedules.toml` (optional) instead of `schedules.py`; no effort-estimate change (3b-1's 2.5h already assumed verb registration only) |
| CR-3 | major | rollback-gap | T-018-task-breakdown.md § Phase 1 (schema tasks 1a-1, 1a-2) | Two schema additions (`ticket.toml` git fields, Run record git fields) had no rollback/migration-down note in the original draft | resolved: rollback note added to task-breakdown.md's Conventions section in this pass — both field sets are additive/optional (`setdefault`/kwarg-defaulted), no destructive or non-nullable change, `set_pr` already supports clearing a bad write the same way `set_claim("")` releases a claim |
| CR-4 | major | critical-path | T-018-plan.md § Risks vs T-018-components.md § Graph analysis | The critical path (Phase 1 → Slice 3a → Slice 3b, 4 tasks / 8.5h of the 21.5h dev total) is the ticket's highest-uncertainty stretch (new `gh`-CLI shell-out code, no existing precedent to lean on beyond `worktrees._git`'s pattern) but this wasn't called out as *the* place to watch for estimate drift | accepted: plan.md's existing "`gh` CLI availability" risk row already covers the reliability angle; this finding adds the explicit note (here, and should be the first thing `estimate(mode=forecast)` checks if re-run mid-build) that Phase 3, not Phase 2 or 4, is where a variance flag is most likely to originate — no plan.md edit needed, this report is the record |

**Traceability check:** all 8 frozen acceptance criteria (AC1-AC8) map to ≥1 task in `T-018-task-breakdown.md` (see `T-018-plan.md` § Approach cross-reference and each task row's Requirement/AC column) — no orphan AC, no orphan component, no orphan task (every task links to ≥1 component and ≥1 FR/AC).

**Effort check:** `T-018-task-breakdown.md` § Effort summary (21.5h dev / 28h grand total, 25-32h range) reconciles exactly with `T-018-implementation-plan.md` § Effort reconciliation — no unresolved drift (an 8.5h vs 6h Phase 3 mismatch was caught and corrected during this same pass, before this report was finalized; see CR-3/CR-4 pointers' surrounding context for the corrected figures).

**Gate:** clear — 0 unresolved critical findings. Ready for `build T-018` (or `/build T-018`).

## Links
- [[T-018-summary]] · [[T-018-plan]] · [[T-018-components]] · [[T-018-task-breakdown]] · [[T-018-implementation-plan]] · [[T-018-plan-iteration-log]]
