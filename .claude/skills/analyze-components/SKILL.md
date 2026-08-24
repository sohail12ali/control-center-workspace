---
name: analyze-components
description: Analyze ticket scope, map all components (data layer, service layer, UI layer, or whatever layers the target project actually has) with dependencies, and build the dependency graph — critical path, bottlenecks, circular-dependency detection, safe build order. Use after requirements are frozen and before task breakdown, when a ticket touches enough surface area that an implicit task list would miss components or their dependencies. Re-run the graph analysis (step 6) mid-build to re-check blocking relationships if scope shifts.
---

# /analyze-components

**When:** After requirements freeze, first step of the multi-layer planning chain; re-run step 6 mid-build if scope shifts.

**Order:** analyze-components → breakdown-tasks (tasks + implementation-plan synthesis) → challenge-plan. Called by `plan` (after Approach/Slices drafted) and `replan` (mid-build re-check).

**Inputs:** `id` (required).

## Steps
1. Read frozen `requirements.md` and `plan.md` (Approach/Slices, if `plan` already ran).
2. Identify the project's actual component layers from repo structure — don't assume a fixed set (typical: data / service / UI; adapt names to the project).
3. Per layer, list every component the ticket touches or creates: name, type, purpose, dependencies, slice, status.
4. Link every component to ≥1 acceptance criterion/requirement — no orphans.
5. Write `knowledge-center/artifacts/{T}/{T}-components.md` from `template.md` (this folder), including the raw ASCII dependency chain (what calls what, top to bottom) and a status-summary row count per layer.
6. **Dependency graph analysis** (same pass, not a separate skill):
   - Node = component, edge = "depends on". Classify each: root (no deps) / leaf (nothing depends on it) / middle.
   - Detect anomalies: circular deps, missing/undeclared deps, isolated components. Circular dependency is a blocker — surface it, don't silently resolve.
   - Critical path = longest chain by dependency count (weight by effort hours once `{T}-task-breakdown.md` exists). Bottleneck = most-depended-on component; flag if still pending.
   - If `{T}-task-breakdown.md` exists (re-run case): cross-reference component vs task blocking, note parallelizable tasks, record suggested build order in that file's Notes — never edit beyond Notes; otherwise just report it.
7. If component count is far outside 5-12, reconsider ticket scope with the user.

## Output
`{T}-components.md` (per-layer component tables with name/type/purpose/dependencies/slice/status, ASCII dependency chain, status-summary per layer), plus:

```
── analyze-components: {T} ──
Components: {N} across {L} layers
Dependencies: {N} edges  Depth: {N}
Root: {list}   Leaf: {list}
Circular deps: {none | list}
Critical path: {A → B → C} ({N} components, {N}h if effort known)
Parallelizable: {yes — list independent chains | no — linear chain}
Suggested build order: {phase-by-phase list}
Artifact: {T}-components.md
Next: breakdown-tasks {T}
```

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
