---
name: challenge-plan
description: Red-team planning artifacts (plan.md, components, task-breakdown, implementation-plan). Stress-test the plan before build. Use after create-implementation-plan (or plan-effort for flat-task tickets) and before build; re-run after replan or any scope-changing evolve.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Ensure `{T}-critique-report.md` exists (scaffold per `.claude/skills/challenge-standards/rules.md` if missing).
2. Load `.claude/skills/challenge-standards/rules.md` for finding format and severity.
3. Read whichever planning artifacts exist: `requirements.md`, `plan.md`, `{T}-components.md`, `{T}-task-breakdown.md`, `{T}-implementation-plan.md`, `{T}-effort-estimate.md`.
4. Walk each category; assign `CR-{n}` IDs (continue the ticket's sequence across stages):
   - **traceability** — acceptance criterion without a downstream task/component link; task without a requirement link; orphan component
   - **scope-drift** — plan work not traceable to frozen requirements
   - **contradiction** — plan.md Approach vs. task-breakdown vs. component design conflict
   - **sequencing-risk** — a consumer scheduled before its dependency; missing migration ordering; parallel slices with a hidden dependency
   - **effort-unrealistic** — task/phase totals vs. `{T}-effort-estimate.md` envelope diverge >10% without rationale
   - **untestable** — task acceptance criteria not observable; missing test surface in the plan
   - **layer-violation** — planned architecture breaks the project's own layering rules (e.g. UI calling the data layer directly)
   - **rollback-gap** — schema/API change in the plan with no rollback or migration-down note
   - **critical-path** — bottleneck understated, or a single-threaded risk unacknowledged (cross-check `analyze-components`'s dependency-graph output)
5. Write findings to `{T}-critique-report.md` § Plan critique (table rows). Update its Summary counts and "Last run" for the Plan stage.
6. For every **critical** finding needing a product/design decision, log it to `{T}-questions.md` (stage: `plan`, priority: `high`).
7. Append an entry to `{T}-plan-iteration-log.md` (scaffold from `template.md` if missing). No requirements-iteration bump.
8. Do **not** edit plan artifacts in place — findings only in the critique report.

# Output
```
── challenge-plan ──
Ticket:       {T}
Findings:     {N} total (critical {c} / major {m} / minor {n})
  traceability: {n}  scope-drift: {n}  contradiction: {n}  sequencing-risk: {n}
  effort-unrealistic: {n}  untestable: {n}  layer-violation: {n}  rollback-gap: {n}  critical-path: {n}
Report:       {T}-critique-report.md § Plan critique
Gate:         {clear | blocked — {c} critical}
Next:         {build {T} | revise {T} | replan {T} | clarify {T}}
```

# Rules
- Every planning artifact that exists is considered, or explicitly noted "missing — skip" with a reason.
- Every finding has `CR-{n}`, severity, kind, pointer per `challenge-standards/rules.md`.
- No silent edits to `plan.md`, `{T}-components.md`, `{T}-task-breakdown.md`, or `{T}-implementation-plan.md` — findings only.
- Summary table counts must match the finding rows.
- Critical findings needing a product decision are mirrored to `{T}-questions.md`.
- Template: `template.md` in this folder (plan-iteration-log scaffold).

**Delegates to:** none (analysis/critique only).
**Called by:** `plan` (final gate before `build`), or `criticize {T} plan`. **Follow-on:** `build` if gate clear, else `revise`/`replan`/`clarify`.
