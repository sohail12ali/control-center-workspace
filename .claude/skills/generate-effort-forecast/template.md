---
ticket: "{T}"
artifact: effort-forecast
mode: "{plan|track|replan}"
---

# Effort forecast: {T}

**Produced by:** `generate-effort-forecast {T}` (`mode={plan|track|replan}`). **Sources:** [[{T}-task-breakdown]] · [[{T}-implementation-plan]] · [[{T}-components]]

| Field | Value |
|-------|-------|
| Mode | {plan \| track \| replan} |
| Confidence | {Low \| Medium \| High} ({n} tasks with actuals) |

---

## Executive summary

| Metric | Hours |
|--------|------:|
| Total estimated | {X} |
| Actual to date | {Y} |
| Remaining dev (PERT E) | {Z} |
| QC (forecast or derived) | {QC} |
| Risk reserve | {R} |
| **Final / Complete** | **{Y+Z+QC+R}** |
| PERT band | {Lo} – {Hi} |

**Headline:** {on track / trending over / blocked / too early to call}

---

## Progress

| Status | Tasks | Est (h) | Actual (h) | % of est |
|--------|------:|--------:|-----------:|---------:|
| Done | | | | |
| In progress | | | | |
| Pending | | | | |
| Blocked | | — | — | — |
| **Total** | | | | |

---

## Variance (completed + partial)

| Task ID | Layer | Est | Actual | Variance | Note |
|---------|-------|----:|-------:|---------:|------|

**Stats:** mean {m}h · median {med}h · within ±0.5h: {n}% · within ±1h: {n}%

---

## By layer

| Layer | Tasks done | Mean variance | P multiplier | Pending est | Remaining E |
|-------|-----------:|---------------:|-------------:|------------:|------------:|
| Data | | | 1.35 | | |
| Service | | | 1.25 | | |
| UI | | | 1.20 | | |
| Test | | | 1.15 | | |
| QC / QA | | | 1.40 | | |

---

## QC forecast

| Field | Value |
|-------|-------|
| Source | {explicit rows \| derived} |
| Base QC | {QC_base}h |
| Cycle factor | x1.5 |
| UAT support | {2/4/8/12}h |
| **QC total** | **{QC}h** [{QC_lo}-{QC_hi}] |

---

## Final / Complete time

| Component | Hours |
|-----------|------:|
| Actual to date | {Y} |
| Remaining dev (PERT E) | {Z} |
| QC | {QC} |
| Risk reserve | {R} |
| **Final / Complete** | **{Y+Z+QC+R}** |

---

## Risks and blockers

| ID | Task | Risk |
|----|------|------|

---

## Recommendations
1. {e.g. re-estimate a trending-over layer via replan}

## Revision log

| Date | Mode | Remaining dev E | QC | Final/Complete | Notes |
|------|------|-----------------:|---:|----------------:|-------|

## Links
- [[{T}-summary]] · [[{T}-task-breakdown]] · [[{T}-implementation-plan]] · [[{T}-effort-estimate]] · [[{T}-effort-forecast]]
