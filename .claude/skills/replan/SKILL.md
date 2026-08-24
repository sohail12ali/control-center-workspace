---
name: replan
description: Re-analyze and break down phases/slices when scope or architecture changes mid-build. Use when the plan's estimate is invalidated by scope drift, an evolve entry, or an estimate(mode=forecast) variance flag.
---

# /replan

**When:** Mid-build re-entry into planning — scope/architecture shift, an `evolve` entry, or `estimate(mode=forecast)` flags >10% variance without rationale. Small single-task effort correction → use `progress-tracker(task_id=...)`/direct edit instead.

**Order:** Called by user or `harness`. Delegates to `estimate`, `analyze-components`, `breakdown-tasks`, `plan risk`; re-run `challenge-plan` after (it re-gates any scope-changing replan).

**Inputs:** `id` (required).

## Steps
1. `trace-context` — load current state of all artifacts.
2. `estimate(mode=forecast, forecast_mode=replan)` — see where estimates drifted.
3. Re-run `analyze-components`'s dependency-graph pass — critical-path impact of the change.
4. Re-estimate scope: new/changed phases, slices, components.
5. Validate the new breakdown against `requirements.md` and the plan's Approach.
6. Update `plan.md` (and `{T}-task-breakdown.md`/`{T}-implementation-plan.md` if they exist): add a replan note, mark superseded phases — never delete/overwrite prior plan history.
7. Re-run `plan risk` if scope changed; report the delta.

## Output
Updated `plan.md` (+ `{T}-task-breakdown.md`/`{T}-implementation-plan.md` if present) with replan note and superseded markers, plus:

```
── replan: {T} ──
Old: {N} phases, {N} slices, {N}h
New: {N} phases, {N} slices, {N}h
Key change: {one line}
Effort forecast: estimate(mode=forecast) {T}
Dependency check: analyze-components {T}
Next: breakdown-tasks {T} | build {T} {slice}
```

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
