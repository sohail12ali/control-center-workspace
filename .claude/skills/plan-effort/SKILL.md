---
name: plan-effort
description: CANONICAL-stage. Decomposes frozen requirements into atomic tasks with effort estimates, dependencies, and risks, for tickets simple enough for a single flat plan.md. Writes plan.md. Use only after requirements are frozen (freeze-requirements passed). For tickets spanning several components/layers, prefer the analyze-components -> breakdown-tasks chain (which produces {T}-components.md and {T}-task-breakdown.md) and reserve this skill for the lightweight flat case.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `requirements.md`, `analysis.md`, `decision-log.md`.
2. Decide structure (same threshold as `plan`'s step 3 — don't re-litigate it per skill):
   - **Flat** (default here): one component/layer, **≤6 tasks**, no real cross-ticket dependency chain. Single task list in `plan.md`.
   - **Multi-layer**: ≥2 components/layers, >6 tasks, or a real dependency chain — hand off to `analyze-components` -> `breakdown-tasks` -> `create-implementation-plan` instead of decomposing inline — those skills produce dedicated `{T}-components.md` / `{T}-task-breakdown.md` / `{T}-implementation-plan.md` artifacts built for that scale. Don't duplicate that decomposition here.
3. Write `plan.md`:
   - Approach (3-5 lines)
   - Tasks: numbered checkboxes, each 1-4h, with done-criteria
   - Dependencies (blocks / blocked-by [[wikilinks]])
   - Effort: total + per-task hours; total must equal sum. `estimate-development` is **opt-in overhead, not a default step** — only run it first when the total looks like it could exceed ~1 day, a stakeholder explicitly asked for an order-of-magnitude number before commitment, or the per-task numbers feel implausible even to the author. For a genuinely small ticket, just add the task hours and move on.
   - Risks: each with mitigation (`risk-scan`)
4. If nested, create `SLICE/PHASE/` subdirs and seed each from `_template`.
5. Update `summary.md` to link new slices/phases.
6. Mid-build, once tasks have actuals, effort re-forecasting is `generate-effort-forecast`'s job, not this skill's — don't hand-roll variance math here.

# Output
Path to plan.md and the next unchecked task.

# Rules
- Reject if any acceptance criterion isn't covered by >=1 task.
- No task without done-criteria. No effort without basis.
- If the ticket turns out to need more structure than a flat list mid-decomposition, stop and switch to the `analyze-components` chain rather than forcing it into `plan.md`.

**See also:** `estimate-development` (pre-task order-of-magnitude budget), `generate-effort-forecast` (mid-build variance/PERT once tasks have actuals) — this skill owns the initial flat decomposition only; it does not replace either.
