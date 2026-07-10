---
name: breakdown-tasks
description: Break slices into atomic tasks with acceptance criteria and effort estimates, one component per task. Use after analyze-components (which includes the dependency graph) when a slice needs finer-grained tasks than plan-effort's flat list provides — typically for multi-layer tickets.
---

# Inputs
- `id` (required): ticket id
- `slice` (optional): specific slice; processes all slices if omitted

# Steps
1. For each slice in `plan.md` (or the named slice):
   - Break into 2-5 atomic tasks, ideally one component per task.
   - Task ID format: `{phase}-{slice}-{task}` (e.g. `2-3-2`).
   - Each task: description, component(s) it builds (link to `{T}-components.md`), requirement/AC it satisfies, testable acceptance criteria, effort estimate (0.5/1/1.5/2/3h — no micro-tasks, no mega-tasks), status, blocking notes.
2. Write `knowledge-center/artifacts/{T}/{T}-task-breakdown.md` from `template.md`: per-phase sections, per-slice subsections, per-task rows.
3. Add an effort summary table (by phase, by total).
4. Cross-check totals against `{T}-effort-estimate.md` if it exists (from `estimate-development`); flag if task totals exceed the estimate's upper bound by >10%.

# Output
Path to `{T}-task-breakdown.md`, task count, total effort hours. Ready for `create-implementation-plan`.

# Rules
- Task IDs must follow `{phase}-{slice}-{task}`.
- Every task links to ≥1 component and ≥1 requirement/acceptance criterion.
- Acceptance criteria must be testable/observable, not vague.
- Note blocking dependencies between tasks explicitly (e.g. "depends on 1b-1").
- If totals diverge materially from `{T}-effort-estimate.md`, don't silently accept — flag via `replan`.
- Template: `template.md` in this folder.

**Delegates to:** none.
**Called by:** `plan` (after `analyze-components`). **Follow-on:** `create-implementation-plan`, `generate-effort-forecast`.
