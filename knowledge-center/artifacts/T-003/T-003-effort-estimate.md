---
ticket: "T-003"
artifact: effort-estimate
basis: "components"
confidence: "Medium"
---

# Effort estimate: T-003

**Produced by:** `estimate T-003 --mode upfront`. **Sources:** [[T-003-requirements]] · [[T-003-components]]

| Field | Value |
|-------|-------|
| Basis | components |
| Units estimated | 15 |
| Confidence | Medium |

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | 47 | 32 | 59 | 5.9 |
| QC | 27 | 22 | 27 | 3.4 |
| Risk reserve | 7 | — | — | 0.9 |
| **Final / Complete** | **81** | **54** | **86** | **10.1** |

> Calendar days are indicative only — no capacity/parallelism model applied. This is coarse, generic-baseline sizing per the estimate skill's T-shirt table; it deliberately runs wider than the bottom-up `{T}-task-breakdown.md` total (see Recommendations) because it does not yet know this ticket is grounded in an unusually detailed, file:line-level programme plan.

---

## Assumptions
1. One engineer (Sohail Ali), no parallel pairing across layers.
2. Generic T-shirt baselines (XS/S/M) applied per component's actual scope, not mechanically defaulted to M.
3. `A6` (release build) is sized for authored/verification effort, not wall-clock build time — the build itself is multi-minute and must not be interleaved with other Rust edits (see [[T-003-components]] bottleneck note).

---

## Units

| Unit ID | Source | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------|-------|------|------:|--------|----------:|----------:|-------|
| A1 | main.rs | service | S | 4 | — | 2.8 | 5.0 | subsystem+console hatch+panic hook |
| A2 | logger.rs | service | S | 4 | — | 2.8 | 5.0 | new file, rotation logic |
| A3 | tray.rs | service | XS | 2 | — | 1.4 | 2.5 | log::warn! wiring only |
| A4 | single-instance integration | service | S | 4 | +40% ext-integration, +25% concurrency (cap 100%, applied 65%) | 4.62 | 8.25 | effective M 6.6h — new 3rd-party crate + quit-race handling |
| A5 | sidecar.rs extra_env | service | XS | 2 | — | 1.4 | 2.5 | plumbing only |
| A6 | release build artifact | service | XS | 2 | — | 1.4 | 2.5 | authored/verification effort; wall-clock separately multi-minute |
| B1 | procs.py | service | XS | 2 | — | 1.4 | 2.5 | new module |
| B2 | six spawn-site edits | service | S | 4 | — | 2.8 | 5.0 | six call sites + test_procs.py |
| B3 | sidecar.py | service | XS | 2 | — | 1.4 | 2.5 | log redirect + inline constant |
| C1 | Windows scripts | service | S | 4 | — | 2.8 | 5.0 | install-shortcut.ps1 + launch.ps1 |
| C2 | install-launcher.sh | service | S | 4 | — | 2.8 | 5.0 | macOS .app + Linux .desktop, one script |
| C3 | .claude/launch.json | service | XS | 2 | — | 1.4 | 2.5 | static config |
| D1 | verify.yml desktop job | test | S | 4 | — | 2.4 | 6.0 | 3-OS matrix YAML |
| E1 | Close T-001 | service | XS | 2 | — | 1.4 | 2.5 | close-work, all ACs already PASS |
| E2 | Close T-002 | service | XS | 2 | — | 1.4 | 2.5 | manual click-through + close-work |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total |
|-------|------:|--------:|----:|--------:|-----------:|
| Service (Rust host, Python server, launch scripts, ticket closure) | 14 | 29.82 | 42.6 | 53.25 | 91% |
| Test (CI) | 1 | 2.4 | 4 | 6.0 | 9% |
| **Total** | 15 | **32.2** | **46.6** | **59.25** | 100% |

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Service | 42.6 | 25% | 10.65 |
| Test (CI) | 4 | 0% | 0 |
| **Base QC (Σ)** | | | **10.65** |

| Factor | Value |
|--------|-------|
| Cycle profile | High (external-integration + concurrency adders present on A4) |
| Cycle factor | x1.8 |
| UAT support | 8h (Dev Σ M 46.6h falls in the 41-80h band) |
| **QC total** | **27.2h** [21.8-27.2] |

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | 46.6 | 32.2 | 59.25 |
| QC total | 27.2 | 21.8 | 27.2 |
| Risk reserve | 7.4 | — | — |
| **Final / Complete** | **81.2** | **54.0** | **86.5** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|
| A4 | External system integration | +40% | `tauri-plugin-single-instance` is a net-new third-party crate |
| A4 | Concurrency / shared-state | +25% | Second-launch race during quit must be handled cleanly (FR-4 explicit AC) |

---

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| R1 | [[T-003-decision-log]] § Single-instance dependency pick | Plugin link failure → descope, not extra hours (bounds the risk rather than widening it) |
| R2 | [[T-003-components]] § Dependency graph analysis (A6 bottleneck) | Release build gates 3 downstream units; a build-environment hiccup would widen C1/C2/E2 more than shown here |
| R3 | [[T-003-requirements]] FR-8 | CI job "green" confirmation depends on an ASK-gated push outside this estimate's authored-effort scope |

---

## Recommendations
1. Treat this as the outer envelope, not the working number — `{T}-task-breakdown.md`'s bottom-up total (21h dev, post-`challenge-plan`) is grounded in the approved programme plan's file:line-level detail and comes in below this estimate's lower bound; that is expected here (the programme plan already resolved most of the uncertainty a generic T-shirt baseline assumes) and is not a `replan` trigger (the flag only fires on totals *exceeding* the upper bound).
2. Re-forecast via `estimate(mode=forecast)` once builder tasks have actuals, particularly around A4 (single-instance) and A6 (release build), the two units carrying this estimate's only complexity adders/bottleneck.

---

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-09-06 | components | 46.6 | 27.2 | 81.2 | 54.0-86.5 | Initial upfront sizing, pre-breakdown |

## Links
- [[T-003-summary]] · [[T-003-requirements]] · [[T-003-components]] · [[T-003-effort-estimate]] · [[T-003-task-breakdown]]
