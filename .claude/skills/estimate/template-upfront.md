---
ticket: "{T}"
artifact: effort-estimate
basis: "{scope|components}"
confidence: "{Low|Medium}"
---

# Effort estimate: {T}

**Produced by:** `estimate {T} --mode upfront`. **Sources:** [[{T}-requirements]] · [[{T}-components]]

| Field | Value |
|-------|-------|
| Basis | {scope \| components} |
| Units estimated | {n} |
| Confidence | {Low \| Medium} |

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | {M} | {Lo} | {Hi} | {M/8} |
| QC | {QC} | {QC_lo} | {QC_hi} | {QC/8} |
| Risk reserve | {R} | — | — | {R/8} |
| **Final / Complete** | **{F}** | **{Flo}** | **{Fhi}** | **{F/8}** |

> Calendar days are indicative only — no capacity/parallelism model applied.

---

## Assumptions
1. {e.g. one engineer, no parallel pairing}
2. {e.g. no unforeseen external integration beyond those listed}

---

## Units

| Unit ID | Source | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------|-------|------|------:|--------|----------:|----------:|-------|
| U1 | | | | | | | | |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total |
|-------|------:|--------:|----:|--------:|-----------:|
| Data | | | | | |
| Service | | | | | |
| UI | | | | | |
| Test | | | | | |
| **Total** | | | | | 100% |

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Data | | 20% | |
| Service | | 25% | |
| UI | | 35% | |
| Integration | | 40% | |
| **Base QC (Σ)** | | | {QC_base} |

| Factor | Value |
|--------|-------|
| Cycle profile | {low/standard/high} |
| Cycle factor | x{1.3/1.5/1.8} |
| UAT support | {2/4/8/12}h |
| **QC total** | **{QC}h** [{QC_lo}-{QC_hi}] |

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | {M} | {Lo} | {Hi} |
| QC total | {QC} | {QC_lo} | {QC_hi} |
| Risk reserve | {R} | — | — |
| **Final / Complete** | **{F}** | **{Flo}** | **{Fhi}** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|

---

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|

---

## Recommendations
1. {e.g. resolve open question before committing}
2. {e.g. reforecast via estimate(mode=forecast) after task-breakdown exists}

---

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| {date} | {scope} | | | | {Flo}-{Fhi} | Initial rough sizing |

## Links
- [[{T}-summary]] · [[{T}-requirements]] · [[{T}-components]] · [[{T}-effort-estimate]] · [[{T}-effort-forecast]]
