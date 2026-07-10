---
name: reconcile
description: Detect and fix drift between artifacts of one ticket — plan task vs requirement vs progress vs verification. Use after `evolve`, after long pauses, and as part of `close-work`.
---

# Inputs
- `id` (required): ticket id

# Checks
1. Every acceptance criterion in `requirements.md` covered by ≥1 task in `plan.md`.
2. Every `[x]` task in `plan.md` referenced in `progress.md`.
3. Every progress `done:` references a real plan task.
4. Every criterion in `verification.md` exists in `requirements.md`.
5. `summary.md` Status matches actual progress (no `Open` while progress entries exist; no `Complete` while tasks unchecked).
6. `artifact-map.md` row matches `summary.md` Status.

# Steps
1. Run all checks; collect mismatches.
2. For each: classify `auto-fixable` (status/index sync) vs `needs-decision` (criterion lost a task).
3. Auto-fix in place; log to `progress.md`.
4. For `needs-decision`: emit a Q via `questions(op=add)` and route to `clarify` or `evolve`.

# Output
Diff of fixes applied + list of unresolved drifts.

# Rules
- Auto-fix only sync issues, not semantic ones.
- Never delete user-authored content to "reconcile"; demote to a Q instead.
