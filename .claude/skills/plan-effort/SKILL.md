---
name: plan-effort
description: CANONICAL-stage. Decomposes frozen requirements into atomic tasks with effort estimates, dependencies, and risks. Writes plan.md. Use only after requirements pass validate.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `requirements.md`, `analysis.md`, `decision-log.md`.
2. Decide structure: flat tasks, or nested `SLICE → PHASE-{ENTITIES|DB|API|UI}` for multi-layer work.
3. Write `plan.md`:
   - Approach (3-5 lines)
   - Tasks: numbered checkboxes, each 1-4h, with done-criteria
   - Dependencies (blocks / blocked-by [[wikilinks]])
   - Effort: total + per-task hours; total must equal sum
   - Risks: each with mitigation
4. If nested, create `SLICE/PHASE/` subdirs and seed each from `_template`.
5. Update `summary.md` to link new slices/phases.

# Output
Path to plan.md and the next unchecked task.

# Rules
- Reject if any acceptance criterion isn't covered by ≥1 task.
- No task without done-criteria. No effort without basis.
