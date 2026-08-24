---
name: challenge-plan
description: Red-team planning artifacts (plan.md, components, task-breakdown, implementation-plan). Stress-test the plan before build. Use after breakdown-tasks (or plan flat mode for flat-task tickets) and before build; re-run after replan or any scope-changing evolve.
---

# /challenge-plan

**When:** After `breakdown-tasks` (or `plan` flat mode for flat tickets) and before build; re-run after `replan` or any scope-changing `evolve`.

**Order:** Final gate of the analyze-components → breakdown-tasks → **challenge-plan** chain. Called by `plan` or `criticize {T} plan`; gate clear → `build`, else `replan`/`clarify`.

**Inputs:** `id` (required).

## Steps
1. Ensure `{T}-critique-report.md` exists (scaffold per `.claude/skills/challenge-standards/rules.md` if missing); load that rules file for finding format and severity.
2. Read every planning artifact that exists: `requirements.md`, `plan.md`, `{T}-components.md`, `{T}-task-breakdown.md`, `{T}-implementation-plan.md`, `{T}-effort-estimate.md`. Each is considered or explicitly noted "missing — skip" with a reason.
3. Walk each category, assigning `CR-{n}` IDs (continue the ticket's sequence across stages):
   - **traceability** — AC without downstream task/component link; task without requirement link; orphan component
   - **scope-drift** — plan work not traceable to frozen requirements
   - **contradiction** — plan.md Approach vs. task-breakdown vs. component design conflict
   - **sequencing-risk** — consumer scheduled before its dependency; missing migration ordering; parallel slices with hidden dependency
   - **effort-unrealistic** — task/phase totals vs. `{T}-effort-estimate.md` envelope diverge >10% without rationale
   - **untestable** — task AC not observable; missing test surface in the plan
   - **layer-violation** — planned architecture breaks the project's own layering rules (e.g. UI calling the data layer directly)
   - **rollback-gap** — schema/API change with no rollback or migration-down note
   - **critical-path** — bottleneck understated or single-threaded risk unacknowledged (cross-check `analyze-components`'s graph output)
4. Write findings to `{T}-critique-report.md` § Plan critique (table rows; every finding has `CR-{n}`, severity, kind, pointer per `challenge-standards/rules.md`). Update its Summary counts (must match finding rows) and "Last run" for the Plan stage.
5. Mirror every **critical** finding needing a product/design decision to `{T}-questions.toml` via `console/kanban.py tracker add {T} questions "..." --set type=plan --set priority=high`.
6. Append an entry to `{T}-plan-iteration-log.md` (scaffold from `template.md` in this folder if missing). No requirements-iteration bump.
7. Do **not** edit `plan.md`, `{T}-components.md`, `{T}-task-breakdown.md`, or `{T}-implementation-plan.md` — findings only in the critique report.

## Output
`{T}-critique-report.md` § Plan critique + `{T}-plan-iteration-log.md` entry, plus:

```
── challenge-plan ──
Ticket:       {T}
Findings:     {N} total (critical {c} / major {m} / minor {n})
  traceability: {n}  scope-drift: {n}  contradiction: {n}  sequencing-risk: {n}
  effort-unrealistic: {n}  untestable: {n}  layer-violation: {n}  rollback-gap: {n}  critical-path: {n}
Report:       {T}-critique-report.md § Plan critique
Gate:         {clear | blocked — {c} critical}
Next:         {build {T} | replan {T} | clarify {T}}
```

## Gate
Unresolved critical findings block handoff to `build`. Clear = zero unresolved critical findings.

**Version:** 1.2 — lean rewrite | **Updated:** 2026-08-23
