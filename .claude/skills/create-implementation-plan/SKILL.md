---
name: create-implementation-plan
description: Synthesize requirements, components, and task-breakdown into one full phases → slices → tasks implementation plan. Use as the last planning step before build, once analyze-components and breakdown-tasks have both run.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Synthesize:
   - `requirements.md` — scope, acceptance criteria
   - `plan.md` — Approach/Slices/Risks
   - `{T}-components.md` — components and dependencies
   - `{T}-task-breakdown.md` — atomic tasks and effort
2. Write `knowledge-center/artifacts/{T}/{T}-implementation-plan.md`: ticket summary, phases with descriptions, per-phase slices, per-slice tasks with file-touch lists, and per level: effort, acceptance criteria, components involved, requirements satisfied.
3. Cross-link every level bidirectionally: requirements ↔ plan, components ↔ tasks, tasks ↔ implementation-plan.
4. Confirm effort totals match `{T}-task-breakdown.md`'s summary; if not, reconcile before finishing.

# Output
Path to `{T}-implementation-plan.md`, phase/slice/task counts, total effort. Ready for `challenge-plan`, then `build`.

# Rules
- Phase/slice/task descriptions must be human-readable, not table-only.
- Effort totals here must equal `{T}-task-breakdown.md` totals — no silent drift.
- File-touch lists must match actual implementation scope (don't pad or guess paths that don't exist in the repo).
- This is the master plan artifact — everything else (components, tasks) is an input, not a duplicate.

**Delegates to:** none.
**Called by:** `plan` (final synthesis step, after `breakdown-tasks`). **Follow-on:** `challenge-plan`, then `build`.
