---
name: estimate-development
description: Upfront development + QC time estimation from scope, requirements, or components — T-shirt sizing, generic component-layer baselines, QC effort (per-layer % x re-test cycles + UAT), ranges with a cone of uncertainty, and a consolidated Final/Complete time (Dev + QC + risk reserve). Use pre-breakdown, when a stakeholder needs an order-of-magnitude duration before task-level decomposition exists. Complements generate-effort-forecast (task-level, mid-build).
---

# Inputs
- `id` (required): ticket id
- `basis` (optional, auto-detected): `scope` (requirements only, coarsest) | `components` (component list, finest pre-task). Prefer the finest available.

# Storage
- Reads (by basis): `scope` → `requirements.md`; `components` → `{T}-components.md`.
- Writes: `knowledge-center/artifacts/{T}/{T}-effort-estimate.md` from `template.md`. Update in place on re-run (finer basis); append a Revision log row, never a second artifact.

# Method

## 1. Decompose into estimable units
- `scope` basis: one unit per functional area in requirements (3-8 units).
- `components` basis: one unit per row in `{T}-components.md` (8-25 units).

## 2. T-shirt size per unit

| Size | Hours (M) | Description |
|------|----------:|-------------|
| XS | 2 | Trivial config / one-field tweak |
| S | 4 | Single CRUD path / one small edit |
| M | 8 | Standard feature slice (one layer, moderate complexity) |
| L | 16 | Multi-component change, complex logic |
| XL | 32 | New module, cross-layer feature, migration |
| XXL | 64 | Cross-repo/architectural change — split before estimating |

## 3. Apply a component-layer baseline

Tag each unit with the layer it belongs to (project-specific — e.g. `data`, `service`, `ui`, `test`, `docs`; adapt names to the actual project). Layer baseline = the M column above; multiply for the upper bound only.

| Layer | Lower mult | Upper mult | Why upper drifts |
|-------|-----------:|-----------:|-------------------|
| data / schema | 0.7 | 1.35 | Migration/rollback safety, data parity |
| service / API | 0.7 | 1.25 | Contract drift, validation edge cases |
| UI | 0.7 | 1.20 | State, navigation, platform quirks |
| E2E / integration test | 0.6 | 1.50 | Environment flakiness, fixture gaps |
| unit/API test | 0.8 | 1.15 | Fixture setup |
| docs / artifact | 0.9 | 1.10 | — |

Per-unit range: `[lower_mult × M, upper_mult × M]`.

## 4. Complexity adders (before range calc)

| Adder | +% to M | Trigger |
|-------|--------:|---------|
| New schema / migration | +30% | unit touches new persisted structure |
| Cross-repo touch | +25% | spans more than one owned repo/package |
| Existing large component rewrite | +20% | unit modifies >100 LOC of existing logic |
| External system integration | +40% | third-party API, payment, messaging, etc. |
| Unknown / spike required | +50% | open question blocks it |
| Concurrency / shared-state | +25% | queues, locking, batch processing |

Cap total adders at +100% per unit.

## 5. Aggregate development effort
Per layer: sum lower/M/upper. Dev total = sum across layers. Dev range = `[Σ lower, Σ upper]`. Dev most likely = `Σ M`.

## 6. QC estimation
QC = manual/regression/UAT effort distinct from dev-authored automated tests (already counted in the `test` layer).

**6a. Base QC — % of dev M per QC-bearing layer:**

| Dev layer | QC ratio |
|-----------|---------:|
| data / schema | 20% |
| service / API | 25% |
| UI | 35% |
| external integration | 40% |
| test layers | 0% (already automated dev) |

`Base QC = Σ (layer dev M × QC ratio)`.

**6b. QC cycle factor:**

| Profile | Trigger | Factor |
|---------|---------|-------:|
| Low risk | few/no adders | ×1.3 |
| Standard | default | ×1.5 |
| High risk | integration/spike/concurrency adder present | ×1.8 |

**6c. UAT support (fixed, by Dev Σ M):** ≤16h → 2h · 17-40h → 4h · 41-80h → 8h · >80h → 12h.

`QC total = (Base QC × cycle factor) + UAT support`. QC range: lower = `Base QC × 1.3 + UAT`; upper = `Base QC × 1.8 + UAT`.

## 7. Cone of uncertainty

| Basis | Confidence | Expected actual vs M |
|-------|------------|-----------------------|
| scope | Low | 0.5x – 2x |
| components | Medium | 0.8x – 1.3x (reforecast via `generate-effort-forecast` after `breakdown-tasks`) |

## 8. Risks → adjustments
For each open blocker: if it blocks scoping, add a placeholder XL unit marked `pending-clarification` and exclude from totals; if it widens unknowns, bump Dev upper by +15%.

## 9. Final / Complete time
Risk reserve on `(Dev M + QC total)`: scope +20% · components +10%.

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | Σ M | Σ lower | Σ upper |
| QC | QC total | QC lower | QC upper |
| Risk reserve | reserve% × (Dev M + QC) | — | — |
| **Final / Complete** | **Dev M + QC + reserve** | **Dev lower + QC lower** | **Dev upper + QC upper** |

Days @ 8h = Final / 8 (indicative — no capacity model).

# Output

```
── estimate-development: {T} ──
Basis:          {scope|components} ({n} units)
Confidence:     {Low|Medium}
Development:    {M}h [{Lo}-{Hi}h]
By layer:       data {x}h · service {y}h · ui {z}h · test {t}h
QC:             {QC}h (x{cycle factor} + {UAT}h UAT support)
Risk reserve:   {R}h (+{reserve%})
Final/Complete: {F}h ({F/8}d at 8h/day) [{Flo}-{Fhi}h]
Next:           analyze-components {T} | breakdown-tasks {T} | generate-effort-forecast {T}
```

# Rules
- T-shirt sizing is discrete — pick one bucket, don't interpolate.
- Never quote a delivery date; days = hours/8, indicative only.
- QC is always derived from Dev, never invented — zero Dev in a layer means zero QC for it.
- Report Dev, QC, and reserve separately, not just the Final total — the breakdown must be auditable.
- Update the same artifact on re-run with a finer basis; keep a Revision log.
- Template: `template.md` in this folder.

**Delegates to:** none.
**Called by:** `planner`/`plan` for a pre-breakdown budget envelope; optionally `analyst` for rough pre-freeze sizing. **Follow-on:** `breakdown-tasks`, then `generate-effort-forecast` once task-level actuals exist.
