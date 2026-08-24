---
name: reconcile
description: Detect and fix drift between artifacts of one ticket — plan task vs requirement vs progress vs verification. Use after `evolve`, after long pauses, and as part of `close-work`.
---

# /reconcile

**When:** A ticket's artifacts may have drifted apart — plan task vs requirement vs progress vs verification.

**Order:** After every `evolve`, after long pauses, and inside `close-work`.

**Inputs:** `id` (required, ticket id).

## Steps

1. Run all checks; collect mismatches:
   - Every acceptance criterion in `requirements.md` covered by ≥1 task in `plan.md`.
   - Every `[x]` task in `plan.md` referenced in `progress.md`.
   - Every progress `done:` references a real plan task.
   - Every criterion in `verification.md` exists in `requirements.md`.
   - `summary.md` Status matches actual progress (no `Open` while progress entries exist; no `Complete` while tasks unchecked).
   - `artifact-map.md` row matches `summary.md` Status.
2. Classify each mismatch: `auto-fixable` (status/index sync) vs `needs-decision` (criterion lost a task).
3. Auto-fix in place; log to `progress.md`.
4. `needs-decision` → emit a Q via `questions(op=add)`; route to `clarify` or `evolve`.

## Output

Diff of fixes applied + list of unresolved drifts.

## Gate

- Auto-fix only sync issues, never semantic ones.
- Never delete user-authored content to "reconcile" — demote to a Q instead.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
