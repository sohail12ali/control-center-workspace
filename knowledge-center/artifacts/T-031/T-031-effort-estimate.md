---
ticket: "T-031"
artifact: effort-estimate
basis: "components"
confidence: "Low"
---

# Effort estimate: T-031

**Produced by:** `estimate T-031 --mode upfront`. **Sources:** [[T-031-requirements]] · [[T-031-components]]

| Field | Value |
|-------|-------|
| Basis | components (13 units from 15 components; see map below) |
| Units estimated | 13 |
| Confidence | **Low**, stricter than the skill's "Medium" for a components basis. Reasons: the skill's T-shirt table is a placeholder that nobody has tuned for this stack; the vault holds **no recorded actuals** to tune it with (searched the T-006, T-010, T-013, T-015, T-016, T-019, T-024, T-029 plans, task breakdowns and estimates: no hour figures); swap time and memory for small.en/medium.en, cpal enumeration on the bridge thread and every non-Windows behaviour are unmeasured. |

This is the **top-down envelope** using the skill's table unmodified (human-team hours). The plan of record is the **bottom-up task total** in [[T-031-plan]] (builder hours). The reconciliation is in the last section; do not read the two as the same quantity.

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | 132.4 | 92.9 | 166.0 | 16.6 |
| QC (verifier stage, derived) | 72.7 | 55.8 | 72.7 | 9.1 |
| Risk reserve (+10%, components basis) | 20.5 | n/a | n/a | 2.6 |
| **Final / Complete** | **225.6** | **148.8** | **238.7** | **28.2** |

> Calendar days are indicative only: no capacity or parallelism model applied; never a delivery date.

---

## Assumptions
1. One builder who can run commands; no parallel pairing; serial execution (the dirty shared files forbid parallel edits anyway).
2. Engine binaries are out of scope (Q1 resolved, D-3); no downloader for them.
3. Windows is the only OS with hardware and a toolchain on hand; Linux/macOS get CI only and are labelled unverified.
4. Hugging Face stays reachable and the pinned commits stay available for the headless proof (AC-40).
5. QC is the verifier stage (`challenge-implementation`, `verify`, human UAT, hardware checks), not the builder's own final verification tasks (35-39), which sit in Development as E2E/integration work.

---

## Units

Layer tags use the skill's table. "Shell" and "console" service units both take the service multipliers (0.7 / 1.25).

| Unit ID | Source (component) | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------------------|-------|------|------:|--------|----------:|----------:|-------|
| U1 | K1 + K2 catalog and keys on disk | data | S (4) | 5.2 | new schema +30% | 3.6 | 7.0 | values come from D-2; no invention |
| U2 | S1 transfer engine | service | M (8) | 11.2 | external system +40% | 7.8 | 14.0 | Range, retry, https-only redirects, local test server |
| U3 | S2 verify and atomic install | service | S (4) | 4.0 | none | 2.8 | 5.0 | fault injection at four points |
| U4 | S3 jobs, inventory, delete | service | M (8) | 10.0 | concurrency +25% | 7.0 | 12.5 | threads, pause/cancel, per-id job |
| U5 | S4 settings schema + `APPLIES` | service | S (4) | 4.0 | none | 2.8 | 5.0 | |
| U6 | S5 routes and shell client | service | M (8) | 8.0 | none | 5.6 | 10.0 | pinned route-set test also edited |
| U7 | R1 STT lifecycle (staleness, swap, hint) | service | L (16) | 23.2 | concurrency +25%, large rewrite +20% | 16.2 | 29.0 | mandatory mutex-free swap |
| U8 | R2 device layer | service | L (16) | 23.2 | concurrency +25%, large rewrite +20% | 16.2 | 29.0 | cpal, audio.rs/piper.rs/cue.rs/loops |
| U9 | R3 preview and tests | service | M (8) | 10.0 | concurrency +25% | 7.0 | 12.5 | mic-test thread, tone |
| U10 | R4 bridge surface | service | M (8) | 8.0 | none | 5.6 | 10.0 | loopback-request test harness |
| U11 | U1 Settings UI | UI | L (16) | 16.0 | none | 11.2 | 19.2 | no JS test harness; shared dirty files |
| U12 | D1 docs and compat | docs | S (4) | 4.0 | none | 3.6 | 4.4 | |
| U13 | Q1 verification (E2E/integration) | E2E | S (4) | 5.6 | external system +40% | 3.4 | 8.4 | headless run needs the internet for tiny.en |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total (M) |
|-------|------:|--------:|----:|--------:|---------------:|
| Data | 1 | 3.6 | 5.2 | 7.0 | 3.9% |
| Service (console 5, shell 4) | 9 | 71.1 | 101.6 | 127.0 | 76.7% |
| UI | 1 | 11.2 | 16.0 | 19.2 | 12.1% |
| Docs | 1 | 3.6 | 4.0 | 4.4 | 3.0% |
| Test (E2E/integration) | 1 | 3.4 | 5.6 | 8.4 | 4.2% |
| **Total** | **13** | **92.9** | **132.4** | **166.0** | 100% |

Unit-level tests are inside each unit (the skill's separate "unit/API test" layer is not double-counted).

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Data | 5.2 | 20% | 1.04 |
| Service (excluding U2) | 90.4 | 25% | 22.60 |
| Integration (U2, Hugging Face) | 11.2 | 40% | 4.48 |
| UI | 16.0 | 35% | 5.60 |
| Test / docs | 9.6 | 0% | 0 |
| **Base QC (sum)** | | | **33.72** |

| Factor | Value |
|--------|-------|
| Cycle profile | high risk (external-integration and concurrency adders present) |
| Cycle factor | x1.8 |
| UAT support | 12 h (Dev sum of M 132.4 is above 80) |
| **QC total** | **72.7 h** [55.8 to 72.7] |

Mechanical result of the skill's table; hardware checks ([HW]) are the part that needs a person and is the likeliest to slip.

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | 132.4 | 92.9 | 166.0 |
| QC total | 72.7 | 55.8 | 72.7 |
| Risk reserve (+10% of Dev M + QC) | 20.5 | n/a | n/a |
| **Final / Complete** | **225.6** | **148.8** | **238.7** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|
| U1 | New schema | 30 | new committed catalog file + on-disk manifest |
| U2, U13 | External system integration | 40 | Hugging Face + CDN redirects, rate limits |
| U4, U9 | Concurrency / shared state | 25 | background threads, pause/cancel, mic-test thread |
| U7, U8 | Concurrency / shared state | 25 | engine slot swap; device generation across loops |
| U7, U8 | Existing large component rewrite | 20 | more than 100 LOC changed in `stt.rs`, `audio.rs`/`piper.rs`/`cue.rs` |

No unit reaches the +100% cap. No "spike required" adder: no open blocker (Q1 and Q2 resolved).

---

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| E-1 | Windows cargo environment ([[T-031-plan]] risk R-2) | each Rust task pays 1-2 min per build cycle; a broken `msvc-env` stalls Phase 1 and 4-5 |
| E-2 | Swap time and memory for small.en/medium.en unmeasured (D-6) | the swap test and headless proof may expose a design problem late |
| E-3 | cpal enumeration from the bridge thread untested (context snapshot §6) | device tasks may need a worker thread, adding a task |
| E-4 | Shared dirty files (`settings.js`, `styles.css`) | UI tasks carry re-read and diff-check overhead; one clobber costs a re-do |
| E-5 | No JS test harness | UI defects surface only at the manual checklist (task 38) |

---

## Recommendations
1. Treat the bottom-up total in [[T-031-plan]] as the plan of record and this envelope as the pessimistic reference.
2. Re-run `estimate(mode=forecast)` after task 05 (first five tasks logged), then at each phase boundary, and `replan` if variance passes 25%.
3. Calibrate the table: after this ticket, record builder actuals per layer so the next estimate can replace the placeholder multipliers (the forecast mode does this after 5+ completed tasks per layer).

---

## Reconciliation with the task breakdown

| Quantity | Value |
|----------|------:|
| Envelope Development (M / lower / upper) | 132.4 / 92.9 / 166.0 h |
| Plan of record, sum of task estimates ([[T-031-task-breakdown]]) | 83.5 h |
| Plan PERT expected E / optimistic O / pessimistic P | 82.9 / 58.5 / 105.2 h |
| Plan vs envelope M | 63% |
| Plan vs envelope lower bound | -10.1% (under, not over) |

The rule in `breakdown-tasks` flags task totals **over** the upper bound by more than 10%; this is under the lower bound, so it is not flagged by that rule, but it is a divergence, so it is stated and recorded as a plan finding (CR-23 in [[T-031-critique-report]]). Rationale: (1) the envelope uses the skill's placeholder table and generic adders, untuned and human-team based, while the plan sizes 39 tasks bottom-up in 0.5-3 h buckets with named test evidence; (2) sixteen tasks sit at the 3 h bucket cap, so the plan carries the "stop and `replan` if a task will not fit" rule rather than hiding overrun in a larger bucket; (3) QC (72.7 h) is not in the plan total and is verifier-stage work. The plan's own pessimistic total (105.2 h) overlaps the envelope's lower bound (92.9 h) but not its most-likely figure; if actuals track the envelope, the plan is low by about 1.6x, and the forecast checkpoint after task 05 is where that would first show.

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-10-05 | components | 132.4 | 72.7 | 225.6 | 148.8-238.7 | Initial sizing at CANONICAL; table untuned; no actuals in vault |

## Links
- [[T-031-summary]] · [[T-031-requirements]] · [[T-031-components]] · [[T-031-effort-estimate]] · T-031-effort-forecast (not produced)
- [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan]] · [[T-031-critique-report]] · [[T-031-analysis]] · [[T-031-decision-log]] · [[T-031-user-stories]] · [[T-031-plan-iteration-log]] · [[T-031-progress]] · [[T-031-verification]]
- Also: [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-release]] · [[T-031-requirements-draft]]
