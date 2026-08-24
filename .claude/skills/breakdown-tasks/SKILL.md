---
name: breakdown-tasks
description: Multi-layer decomposition — break slices into atomic tasks with acceptance criteria and effort (one component per task), then synthesize requirements + components + tasks into the master phases → slices → tasks implementation plan. Use after analyze-components for tickets needing finer-grained tasks than plan's flat list; produces {T}-task-breakdown.md and {T}-implementation-plan.md, ready for challenge-plan.
---

# /breakdown-tasks

**When:** Multi-layer planning chain, after `analyze-components`, when a slice needs finer-grained tasks than `plan`'s flat list.
**Order:** analyze-components → **breakdown-tasks** → challenge-plan, then build. Called by `plan`; `estimate(mode=forecast)` follows once tasks have actuals.
**Inputs:** `id` (required); `slice` (optional — all slices if omitted).

## Steps — breakdown

1. For each slice in `plan.md` (or the named slice), break into 2-5 atomic tasks, ideally one component per task. Task ID `{phase}-{slice}-{task}` (e.g. `2-3-2`). Each task: description, component(s) built (link to `{T}-components.md`), requirement/AC satisfied, testable acceptance criteria, effort (0.5/1/1.5/2/3h — no micro- or mega-tasks), status, explicit blocking notes ("depends on 1b-1").
2. Write `{T}-task-breakdown.md` from `template.md` (this folder): per-phase sections, per-slice subsections, per-task rows, plus an effort summary table (by phase, total).
3. Cross-check totals against `{T}-effort-estimate.md` if it exists; task totals >10% over its upper bound → don't silently accept, flag via `replan`.

## Steps — implementation plan (synthesis)

4. Synthesize `requirements.md` (scope, AC) + `plan.md` (Approach/Slices/Risks) + `{T}-components.md` + `{T}-task-breakdown.md` into `{T}-implementation-plan.md`: ticket summary; phases with human-readable descriptions (not table-only); per-phase slices; per-slice tasks with file-touch lists matching actual repo paths (never pad or guess); per level: effort, acceptance criteria, components, requirements satisfied.
5. Cross-link every level bidirectionally: requirements ↔ plan, components ↔ tasks, tasks ↔ implementation-plan.
6. Confirm implementation-plan effort totals equal the breakdown's summary — reconcile before finishing, no silent drift.

## Output

- `{T}-task-breakdown.md` — every task links to ≥1 component and ≥1 requirement/AC; effort summary table.
- `{T}-implementation-plan.md` — the master plan artifact (components/tasks are inputs, not duplicates).

Report paths, phase/slice/task counts, total effort. Ready for `challenge-plan`, then build.

**Version:** 2.0 — absorbed create-implementation-plan as the synthesis step | **Updated:** 2026-08-23
