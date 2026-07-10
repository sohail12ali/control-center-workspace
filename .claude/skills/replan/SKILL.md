---
name: replan
description: Re-analyze and break down phases/slices when scope or architecture changes mid-build. Use when the plan's estimate is invalidated by scope drift, an evolve entry, or a generate-effort-forecast variance flag.
---

# Inputs
- `id` (required): ticket id

# Steps
1. `trace-context` — load current state of all artifacts.
2. Run `generate-effort-forecast(mode=replan)` — see where estimates drifted.
3. Re-run `analyze-components`'s dependency-graph pass — check critical-path impact of the change.
4. Re-estimate scope: identify new/changed phases, slices, components.
5. Validate the new breakdown against `requirements.md` and the plan's Approach.
6. Update `plan.md` (and `{T}-task-breakdown.md`/`{T}-implementation-plan.md` if they exist): add a replan note, mark superseded phases, don't delete history.
7. Report the delta.

# Output
```
── replan: {T} ──
Old: {N} phases, {N} slices, {N}h
New: {N} phases, {N} slices, {N}h
Key change: {one line}
Effort forecast: generate-effort-forecast {T}
Dependency check: analyze-components {T}
Next: breakdown-tasks {T} | build {T} {slice}
```

# Rules
- Never silently overwrite prior plan history — mark superseded, keep the record.
- Re-run `risk-scan` after any replan that changes scope.
- If the change is small (single task effort correction), use `update-task-status`/direct edit instead of a full replan.

**Delegates to:** `generate-effort-forecast`, `analyze-components`, `breakdown-tasks`, `risk-scan`.
**Called by:** user or `harness` when scope/architecture shifts, or `generate-effort-forecast` flags a >10% variance without rationale.
