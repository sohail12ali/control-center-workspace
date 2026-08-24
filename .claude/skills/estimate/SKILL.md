---
name: estimate
description: Unified effort estimation for a ticket. Mode `upfront` — pre-breakdown Dev+QC sizing from scope, requirements, or components (T-shirt sizing, generic component-layer baselines, QC effort, ranges with a cone of uncertainty, Final/Complete total). Use before or alongside breakdown-tasks, when a stakeholder needs an order-of-magnitude duration before task-level decomposition exists. Mode `forecast` — mid-build re-forecast from task-breakdown actuals (variance, PERT scenarios, QC forecast, Final/Complete projected total). Use after breakdown-tasks, during replan, or when checking progress.
---

# /estimate

**When:** `upfront` — pre-breakdown order-of-magnitude sizing, before/alongside `breakdown-tasks` (its budget envelope; called by `plan`/`planner`, optionally `analyst` pre-freeze). `forecast` — mid-build re-forecast from actuals, after `breakdown-tasks`, during `replan` (its variance/critical-path input), or on progress checks.

**Inputs:** `id` (required); `mode` (auto): `forecast` if task-breakdown/plan tasks exist with ≥1 actual logged, else `upfront`; `basis` (upfront, auto): `scope` (requirements only, coarsest) | `components` (finest pre-task — prefer finest available); `forecast_mode` (forecast, default `track`): `plan` (baseline, no actuals) | `track` (variance + forecast) | `replan` (bias-adjust remaining, hand off to `replan`).

**Reads:** upfront — `requirements.md` (scope) or `{T}-components.md` (components). Forecast — `{T}-task-breakdown.md` (canonical; fallback `plan.md` tasks), `{T}-implementation-plan.md`, `{T}-components.md`, prior `{T}-effort-forecast.md` (historical bias). Task-row fields: Task ID, Effort/Effort(h), Status, Notes, Component. Variance = actual − estimated (positive = took longer).

## Steps — mode: upfront
1. Decompose into estimable units: `scope` = one unit per functional area (3-8 units); `components` = one unit per `{T}-components.md` row (8-25 units).
2. T-shirt size per unit (discrete — pick one bucket, don't interpolate):

| Size | Hours (M) | Description |
|------|----------:|-------------|
| XS | 2 | Trivial config / one-field tweak |
| S | 4 | Single CRUD path / one small edit |
| M | 8 | Standard feature slice (one layer, moderate complexity) |
| L | 16 | Multi-component change, complex logic |
| XL | 32 | New module, cross-layer feature, migration |
| XXL | 64 | Cross-repo/architectural change — split before estimating |

3. Tag each unit with its layer; per-unit range `[lower_mult × M, upper_mult × M]`. Placeholder table — re-tune once for the actual stack before trusting numbers:

| Layer | Lower mult | Upper mult | Why upper drifts |
|-------|-----------:|-----------:|-------------------|
| data / schema | 0.7 | 1.35 | Migration/rollback safety, data parity |
| service / API | 0.7 | 1.25 | Contract drift, validation edge cases |
| UI | 0.7 | 1.20 | State, navigation, platform quirks |
| E2E / integration test | 0.6 | 1.50 | Environment flakiness, fixture gaps |
| unit/API test | 0.8 | 1.15 | Fixture setup |
| docs / artifact | 0.9 | 1.10 | — |

4. Complexity adders (applied to M before range calc; cap total at +100% per unit):

| Adder | +% to M | Trigger |
|-------|--------:|---------|
| New schema / migration | +30% | unit touches new persisted structure |
| Cross-repo touch | +25% | spans more than one owned repo/package |
| Existing large component rewrite | +20% | unit modifies >100 LOC of existing logic |
| External system integration | +40% | third-party API, payment, messaging, etc. |
| Unknown / spike required | +50% | open question blocks it |
| Concurrency / shared-state | +25% | queues, locking, batch processing |

5. Aggregate dev effort: per layer sum lower/M/upper. Dev total = sum across layers; Dev range = `[Σ lower, Σ upper]`; Dev most likely = `Σ M`.
6. QC (manual/regression/UAT, distinct from dev-authored automated tests in the `test` layer; QC derives from Dev, never invented — zero Dev in a layer = zero QC). Base QC = `Σ (layer dev M × QC ratio)`:

| Dev layer | QC ratio |
|-----------|---------:|
| data / schema | 20% |
| service / API | 25% |
| UI | 35% |
| external integration | 40% |
| test layers | 0% (already automated dev) |

   Cycle factor:

| Profile | Trigger | Factor |
|---------|---------|-------:|
| Low risk | few/no adders | ×1.3 |
| Standard | default | ×1.5 |
| High risk | integration/spike/concurrency adder present | ×1.8 |

   UAT support (fixed, by Dev Σ M): ≤16h → 2h · 17-40h → 4h · 41-80h → 8h · >80h → 12h. `QC total = (Base QC × cycle factor) + UAT`; QC range: lower `Base QC × 1.3 + UAT`, upper `Base QC × 1.8 + UAT`.
7. Cone of uncertainty:

| Basis | Confidence | Expected actual vs M |
|-------|------------|-----------------------|
| scope | Low | 0.5x – 2x |
| components | Medium | 0.8x – 1.3x (reforecast via `estimate(mode=forecast)` after `breakdown-tasks`) |

8. Risks → adjustments: per open blocker — blocks scoping → placeholder XL unit marked `pending-clarification`, excluded from totals; widens unknowns → Dev upper +15%.
9. Final/Complete: risk reserve on `(Dev M + QC total)` — scope +20% · components +10%. Days @ 8h = Final / 8 (indicative — no capacity model; never quote a delivery date).

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | Σ M | Σ lower | Σ upper |
| QC | QC total | QC lower | QC upper |
| Risk reserve | reserve% × (Dev M + QC) | — | — |
| **Final / Complete** | **Dev M + QC + reserve** | **Dev lower + QC lower** | **Dev upper + QC upper** |

## Output — upfront
`knowledge-center/artifacts/{T}/{T}-effort-estimate.md` from `template-upfront.md` — update in place on finer-basis re-run, append a Revision log row, never a second artifact; Dev, QC, and reserve reported separately (breakdown must be auditable). Plus:

```
── estimate(upfront): {T} ──
Basis:          {scope|components} ({n} units)
Confidence:     {Low|Medium}
Development:    {M}h [{Lo}-{Hi}h]
By layer:       data {x}h · service {y}h · ui {z}h · test {t}h
QC:             {QC}h (x{cycle factor} + {UAT}h UAT support)
Risk reserve:   {R}h (+{reserve%})
Final/Complete: {F}h ({F/8}d at 8h/day) [{Flo}-{Fhi}h]
Next:           analyze-components {T} | breakdown-tasks {T} | estimate(mode=forecast) {T}
```

## Steps — mode: forecast
1. Aggregate (track/replan) from task rows — evidence, not invented hours: totals estimated / actual (done + partial in-progress) / remaining (pending + blocked + in-progress remainder); per phase and per layer: mean/median variance, outliers `|variance| ≥ 1h`; accuracy = % tasks within ±0.5h and ±1h. Blocked tasks: remaining effort = 0 until unblocked; exclude from E, list under Risks.
2. PERT per open task with point estimate `M`:

| Symbol | Rule |
|--------|------|
| O (optimistic) | 0.7 × M |
| M (most likely) | point estimate from task-breakdown |
| P (pessimistic) | M × layer_multiplier (step 4) |

   Expected `E = (O + 4M + P) / 6`; std dev `σ = (P − O) / 6`. Ticket remaining: `Σ E` over open tasks; range `[Σ O, Σ P]`; 68% band `Σ E ± sqrt(Σ σ²)`.
3. Confidence (cone of uncertainty) — don't treat estimates as commitments when Low:

| Completed tasks with actuals | Confidence |
|-------------------------------|------------|
| 0-4 | Low |
| 5-8 | Medium |
| 9+ | High |

4. Layer multipliers (P and replan bias). After 5+ completed tasks in a layer, replace with `1 + mean(positive_variance)/M` for that layer (cap 2.0):

| Layer | P multiplier | Typical underestimate driver |
|-------|--------------|-------------------------------|
| Data / schema | 1.35 | Migration/rollback safety, parity checks |
| Service / API | 1.25 | Contract drift, validation edge cases |
| UI | 1.20 | State, navigation, platform quirks |
| E2E / integration test | 1.50 | Env flakiness, fixture gaps |
| Unit/API test | 1.15 | Fixture setup |
| QC / QA | 1.40 | Re-test rounds, UAT churn |
| Docs / artifact | 1.10 | — |

5. QC forecast: explicit QC rows (tagged `qc`/`qa`/`uat`/`regression`) → standard PERT with the 1.40 multiplier. None → derive `QC E = Σ (remaining dev E per layer × QC ratio)` (data 20% · service 25% · UI 35% · integration 40%) × 1.5 cycle factor + UAT support (2/4/8/12h by projected dev total band). Always label explicit vs derived; never fold QC into dev E.
6. Final/Complete = Actual + Remaining dev E + QC + reserve — report each component, not just the total. Range `[Y + ΣO + QC_lo, Y + ΣP + QC_hi]`; restate days@8h as indicative when confidence < High.

| Component | Hours |
|-----------|------:|
| Actual to date | {Y} |
| Remaining dev (PERT E) | {Z} |
| QC (forecast or derived) | {QC} |
| Risk reserve (Low +20% / Medium +12% / High +5%, on Z+QC) | {R} |
| **Final / Complete** | **{Y+Z+QC+R}** |

7. Patterns → actions: consistent positive variance in a layer → recommend +15-25% buffer on pending tasks (`replan`); critical path (from `analyze-components`) trending over → flag; QC trending over cycle factor → raise QC multiplier, flag defect-density risk.

## Output — forecast
`knowledge-center/artifacts/{T}/{T}-effort-forecast.md` from `template-forecast.md`, plus:

```
── estimate(forecast): {T} ──
Forecast mode:  {plan|track|replan}
Confidence:     {Low|Medium|High} ({n} tasks with actuals)
Estimated:      {X}h | Actual: {Y}h | Remaining dev E: {Z}h [{Lo}-{Hi}h]
Variance:       mean {+/-}h | outliers: {ids}
PERT:           realistic {E}h | optimistic {O}h | pessimistic {P}h
QC:             {QC}h ({explicit rows | derived from remaining dev})
Risk reserve:   {R}h (+{%})
Final/Complete: {F}h ({F/8}d, indicative) [{Flo}-{Fhi}h]
Layers at risk: {list}
Next:           replan {T} | breakdown-tasks {T} | estimate(mode=forecast) {T} (re-run)
```

**Version:** 1.2 — lean rewrite | **Updated:** 2026-08-23
