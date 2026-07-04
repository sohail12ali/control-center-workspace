---
name: generate-effort-forecast
description: Forecast remaining ticket effort from task-breakdown actuals — variance, PERT scenarios, component-layer calibration, QC forecast (explicit QC rows or derived from remaining dev), and a Final/Complete projected total (Actual + remaining dev + QC + risk reserve). Use mid-build after breakdown-tasks, during replan, or when checking progress. Complements estimate-development (pre-task, order-of-magnitude).
---

# Inputs
- `id` (required): ticket id
- `mode` (optional, default `track`): `plan` (baseline only, no actuals) | `track` (variance + forecast) | `replan` (bias-adjust remaining, hand off to `replan` skill)

# Storage
- Reads: `{T}-task-breakdown.md` (canonical); falls back to `plan.md` tasks if no task-breakdown exists. Also `{T}-implementation-plan.md`, `{T}-components.md`, prior `{T}-effort-forecast.md` for historical bias.
- Writes: `knowledge-center/artifacts/{T}/{T}-effort-forecast.md` from `template.md`.

Parse task rows for: Task ID, Effort/Effort(h), Status, Notes, Component. Variance = actual − estimated (positive = took longer).

# Method

## 1. Aggregate (track/replan)
Totals: estimated, actual (done + partial in-progress), remaining (pending + blocked + in-progress remainder). Per phase and per component-layer: mean/median variance, outliers `|variance| ≥ 1h`. Accuracy: % tasks within ±0.5h and ±1h.

## 2. PERT forecast (remaining work)
For each open task with only a point estimate `M`:

| Symbol | Rule |
|--------|------|
| O (optimistic) | 0.7 × M |
| M (most likely) | point estimate from task-breakdown |
| P (pessimistic) | M × layer_multiplier (below) |

Expected: `E = (O + 4M + P) / 6`. Std dev: `σ = (P − O) / 6`.
Remaining (ticket): sum E over open tasks; range `[Σ O, Σ P]`; 68% band `Σ E ± sqrt(Σ σ²)`.

## 3. Cone of uncertainty (confidence)

| Completed tasks with actuals | Confidence |
|-------------------------------|------------|
| 0-4 | Low |
| 5-8 | Medium |
| 9+ | High |

## 4. Component-layer multipliers (P and replan bias)

| Layer | P multiplier | Typical underestimate driver |
|-------|--------------|-------------------------------|
| Data / schema | 1.35 | Migration/rollback safety, parity checks |
| Service / API | 1.25 | Contract drift, validation edge cases |
| UI | 1.20 | State, navigation, platform quirks |
| E2E / integration test | 1.50 | Env flakiness, fixture gaps |
| Unit/API test | 1.15 | Fixture setup |
| QC / QA | 1.40 | Re-test rounds, UAT churn |
| Docs / artifact | 1.10 | — |

After 5+ completed tasks in a layer, replace the multiplier with `1 + mean(positive_variance)/M` for that layer (cap 2.0).

## 5. QC forecast
Explicit QC rows (tagged `qc`/`qa`/`uat`/`regression`) → forecast with standard PERT using the QC/QA multiplier (1.40). No explicit rows → derive: `QC E = Σ (remaining dev E per layer × QC ratio)` using ratios data 20% · service 25% · UI 35% · integration 40%, then × 1.5 cycle factor + UAT support (2/4/8/12h by projected dev total band). Label derived QC explicitly.

## 6. Final / Complete time

| Component | Hours |
|-----------|------:|
| Actual to date | {Y} |
| Remaining dev (PERT E) | {Z} |
| QC (forecast or derived) | {QC} |
| Risk reserve (Low +20% / Medium +12% / High +5%, on Z+QC) | {R} |
| **Final / Complete** | **{Y+Z+QC+R}** |

Range: `[Y + ΣO + QC_lo, Y + ΣP + QC_hi]`. Restate days@8h as indicative when confidence < High.

## 7. Patterns → actions
Consistent positive variance in a layer → recommend +15-25% buffer on pending tasks (`replan`). Blocked tasks → exclude from E, list under Risks. Critical path (from `analyze-components`) trending over → flag. QC trending over cycle factor → raise QC multiplier, flag defect-density risk.

# Output

```
── generate-effort-forecast: {T} ──
Mode:           {plan|track|replan}
Confidence:     {Low|Medium|High} ({n} tasks with actuals)
Estimated:      {X}h | Actual: {Y}h | Remaining dev E: {Z}h [{Lo}-{Hi}h]
Variance:       mean {+/-}h | outliers: {ids}
PERT:           realistic {E}h | optimistic {O}h | pessimistic {P}h
QC:             {QC}h ({explicit rows | derived from remaining dev})
Risk reserve:   {R}h (+{%})
Final/Complete: {F}h ({F/8}d, indicative) [{Flo}-{Fhi}h]
Layers at risk: {list}
Next:           replan {T} | breakdown-tasks {T} | generate-effort-forecast {T} (re-run)
```

# Rules
- Evidence from task rows, not invented hours.
- Do not treat estimates as commitments when confidence is Low.
- Blocked tasks: remaining effort = 0 until unblocked.
- QC is forecast from explicit rows when present, else derived from remaining dev — always label which; never fold into dev E.
- Final/Complete = Actual + Remaining dev E + QC + reserve — report each component, not just the total.
- Template: `template.md` in this folder.

**Delegates to:** none.
**Called by:** mid-build progress checks, `replan` (as its variance/critical-path input), optionally `estimate-development`'s follow-on once task-level actuals exist.
