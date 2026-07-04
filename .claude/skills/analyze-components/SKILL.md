---
name: analyze-components
description: Analyze ticket scope, map all components (data layer, service layer, UI layer, or whatever layers the target project actually has) with dependencies, and build the dependency graph — critical path, bottlenecks, circular-dependency detection, safe build order. Use after requirements are frozen and before task breakdown, when a ticket touches enough surface area that an implicit task list would miss components or their dependencies. Re-run the graph analysis (step 6) mid-build to re-check blocking relationships if scope shifts.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read frozen `requirements.md` and `plan.md` (Approach/Slices, if `plan` already ran).
2. Identify the project's actual component layers from repo structure (don't assume a fixed set) — typical examples: **data layer** (schema, migrations, stored logic), **service layer** (APIs, business logic, repositories), **UI layer** (views, view-models, components). Adapt names to what the project uses.
3. For each layer, list the components this ticket must touch or create: name, type (e.g. table/endpoint/view), purpose, dependencies (what it calls or reads), which slice it belongs to, status.
4. Link every component to at least one acceptance criterion or requirement.
5. Write `knowledge-center/artifacts/{T}/{T}-components.md` from `template.md`, including the raw ASCII dependency chain (what calls what, top to bottom) and a status-summary row count per layer.
6. **Dependency graph analysis** (same pass — this is not a separate skill):
   - Build the dependency graph from the components just listed (node = component, edge = "depends on").
   - Classify each component: root (no dependencies), leaf (nothing depends on it), middle (both).
   - Detect anomalies: circular dependencies, missing/undeclared dependencies, isolated components not in any chain.
   - Find the critical path (longest dependency chain) and bottlenecks (components with the most dependents).
   - If `{T}-task-breakdown.md` already exists (re-run case), cross-reference component blocking with task blocking, note which tasks can run in parallel, and record the suggested build order in that file's Notes — otherwise just report it.

# Output
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
Next: breakdown-tasks {T} | create-implementation-plan {T}
```

# Rules
- Don't invent layers the project doesn't have — ground in actual repo structure.
- Every component traces to ≥1 requirement/acceptance criterion; no orphans.
- Circular dependency is a blocker — surface it before planning continues; don't silently resolve it.
- Critical path = longest chain by dependency count (weight by effort hours once `{T}-task-breakdown.md` exists).
- Bottleneck = component most other components depend on; flag if it's still pending.
- 5-12 components is a typical range for one ticket; far outside that, reconsider ticket scope with the user.
- Re-running for a mid-build dependency re-check never edits `{T}-task-breakdown.md` beyond its Notes — analysis only.
- Template: `template.md` in this folder.

**Delegates to:** none.
**Called by:** `plan` (after Approach/Slices are drafted), `replan` (mid-build re-check). **Follow-on:** `breakdown-tasks`, `create-implementation-plan`.
