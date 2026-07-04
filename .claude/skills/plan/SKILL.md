---
name: plan
description: CANONICAL stage — umbrella orchestrator for planning. Decides approach and structure, then chains the deeper planning skills for multi-layer tickets. Writes/updates plan.md. Pairs with `plan-effort` (flat task-level decomposition) or the analyze-components (includes dependency graph) -> breakdown-tasks -> create-implementation-plan -> challenge-plan chain (multi-layer decomposition with a dedicated critique gate).
---

# Inputs
- `id` (required): ticket id
- `mode` (optional, default `staged`): `staged` (review each step) | `full` (run the whole chain without pausing) | `resume` (skip to the next incomplete step)

# Steps
1. Read frozen `requirements.md`, `analysis.md`, `decision-log.md`.
2. Decide approach: 3-5 line rationale tying chosen path to constraints/decisions. If multiple viable approaches, run `clarify` instead of guessing.
3. Decide structure. Use a concrete tiebreaker, not gut feel — **default to single-layer** and only escalate to multi-layer when a rule below actually fires:
   - **Single-layer** (default): touches exactly one component/layer, the anticipated task list is **≤6 tasks**, and no task depends on another ticket's unfinished work. Flat task list — write plan.md Approach/Slices/Risks, then hand off directly to `plan-effort` for Tasks/Effort. Stop here; the deeper chain below is unnecessary overhead — do not run it "just in case."
   - **Multi-layer** — escalate only if **any** of these hold: touches **≥2 components/layers** (e.g. data + service + UI), the flat task list would exceed **~6 tasks**, or a real cross-task dependency chain exists that `plan-effort`'s flat list can't express. Write plan.md Approach/Slices, then chain the deeper planning skills in sequence:
     1. `analyze-components` — map every component and its dependencies to `{T}-components.md`, including critical path, bottlenecks, and build order (same pass, no separate skill)
     2. `breakdown-tasks` — atomic per-component tasks to `{T}-task-breakdown.md`
     3. `estimate-development` (optional, before or alongside `breakdown-tasks`) — order-of-magnitude budget envelope to check task totals against
     4. `create-implementation-plan` — synthesize everything into `{T}-implementation-plan.md`
     5. `challenge-plan` — red-team the assembled plan; gate on zero unresolved critical findings
4. Pull risks from analysis + decision-log; rate likelihood x impact (`risk-scan` if >=3 risks). Re-run `risk-scan` after `challenge-plan` if it surfaced new risk-shaped findings.
5. Report gate status: if `challenge-plan` (multi-layer) or `plan-effort`'s own AC-coverage check (single-layer) is clear, hand off to `build`; else `revise`/`replan`/`clarify`.

# Output
```
── plan: {T} ──
Structure:    {single-layer | multi-layer}
Artifacts:    plan.md{, {T}-components, {T}-task-breakdown, {T}-implementation-plan}
Effort:       {hours}h estimated
Risks:        {mitigated}/{total} (high x high: {N})
Plan critique: {N} findings ({c} critical) — multi-layer only
Next:         build {T} {first-slice} (if gate clear; else revise | replan | clarify)
```

# Rules
- Don't decompose tasks here directly; that's `plan-effort` (flat) or `breakdown-tasks` (multi-layer).
- Approach must reference at least one decision-log entry or analysis finding.
- Multi-layer tickets are not build-ready until `challenge-plan` reports a clear gate (zero unresolved critical findings).
- Effort totals from `breakdown-tasks`/`create-implementation-plan` must reconcile with `estimate-development`'s envelope, if one was produced — don't let them silently diverge.

**Delegates to:** `plan-effort` (single-layer); `analyze-components`, `breakdown-tasks`, `estimate-development`, `create-implementation-plan`, `challenge-plan` (multi-layer); `risk-scan` (both).
