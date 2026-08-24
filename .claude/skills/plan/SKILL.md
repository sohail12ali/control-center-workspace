---
name: plan
description: CANONICAL stage — all planning in one skill. Decides approach and structure, writes plan.md. Flat mode decomposes simple tickets into atomic tasks with effort and dependencies directly in plan.md; multi-layer tickets chain analyze-components → breakdown-tasks → challenge-plan. Op risk extracts and rates risks from ticket artifacts into plan.md § Risks (re-run after every evolve/replan). Use only after requirements freeze passes.
---

# /plan

**When:** CANONICAL stage, after `requirements freeze` passes — the entry point for all planning. `plan {T} risk` also re-runs standalone after every `evolve` or `replan`.
**Order:** `requirements stories` → **plan** → (multi-layer: `analyze-components` → `breakdown-tasks` → `challenge-plan`) → build. `estimate(mode=upfront)` optionally precedes breakdown; `estimate(mode=forecast)` owns mid-build re-forecasting.
**Inputs:** `id` (required); `op` (optional): `full` (default) `| risk`; `mode` (default `staged`): `staged` review each step | `full` run whole chain | `resume` skip to next incomplete step.

## Steps

1. Read frozen `requirements.md`, `analysis.md`, `decision-log.md`, `{id}-user-stories.md`.
2. Decide approach: 3-5 line rationale citing ≥1 decision-log entry or analysis finding. Multiple viable approaches → `clarify`, don't guess. Unmade tech choices the slices imply → `tech-select` per topic before tasking.
3. Decide structure — **default single-layer**; escalate only when a rule fires:

**Single-layer / flat (default: one component/layer, ≤6 tasks, no real cross-ticket dependency chain):**
4. Write `plan.md` in full: Approach (3-5 lines) · Tasks (numbered checkboxes, each 1-4h, each with done-criteria) · Dependencies (blocks / blocked-by [[wikilinks]]) · Effort (total = sum of per-task hours) · Risks (op risk below). `estimate(mode=upfront)` only if total could exceed ~1 day or a stakeholder wants an envelope first. If nested, seed `SLICE/PHASE/` subdirs from `_template`; update `summary.md` links. If decomposition outgrows the flat thresholds mid-way, stop and switch to the multi-layer chain — never duplicate it here.

**Multi-layer (≥2 components/layers, >~6 tasks, or a real dependency chain):**
5. Write plan.md Approach/Slices, then chain: `analyze-components` → `{T}-components.md` · `estimate(mode=upfront)` (recommended at this scale) · `breakdown-tasks` → `{T}-task-breakdown.md` + `{T}-implementation-plan.md` · `challenge-plan` (gate below).

**op: risk (both paths; also standalone after evolve/replan):**
6. Scan for risk language: `analysis.md` Findings, `decision-log.md` rejected alternatives, `requirements.md` NFRs, `progress.md` Blockers, `{T}-critique-report.md` § Plan critique. If `challenge-plan` has run, pull forward `critical-path`/`rollback-gap` findings citing their `CR-{n}` — don't re-derive.
7. Score likelihood × impact (low/med/high each); cite the artifact line (or CR id) that surfaced each risk — never invent. Top risks (high×high, high×med, med×high) require explicit mitigation; flag any without. Structural plan defects (sequencing/traceability) are not rated here — hand to `challenge-plan`. A realized risk routes to `fix` + `evolve`.
8. Write/update `plan.md` § Risks table: Risk / Likelihood / Impact / Mitigation / Owner / Source.

## Output

`plan.md` (Approach/Slices/Tasks/Effort/Risks — flat case complete in one file); multi-layer adds `{T}-components.md`, `{T}-task-breakdown.md`, `{T}-implementation-plan.md` via the chain. Effort totals must reconcile with `estimate(mode=upfront)`'s envelope when one exists.

```
── plan: {T} ──
Structure:    {single-layer | multi-layer}
Artifacts:    plan.md{, {T}-components, {T}-task-breakdown, {T}-implementation-plan}
Effort:       {hours}h estimated
Risks:        {mitigated}/{total} (high×high: {N})
Plan critique: {N} findings ({c} critical) — multi-layer only
Next:         build {T} {first-slice} (if gate clear; else replan | clarify)
```

## Gate

- Reject if any acceptance criterion isn't covered by ≥1 task; no task without done-criteria; no effort without basis.
- Risks without mitigation block stage advance to TEMPLATE.
- Multi-layer tickets are not build-ready until `challenge-plan` reports zero unresolved critical findings.

**Version:** 2.0 — absorbed plan-effort (flat mode) and risk-scan (op risk) | **Updated:** 2026-08-23
