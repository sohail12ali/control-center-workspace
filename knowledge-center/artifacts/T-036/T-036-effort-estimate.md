---
ticket: "T-036"
artifact: effort-estimate
basis: "components"
confidence: "Medium"
---

# Effort estimate: T-036

**Produced by:** `estimate T-036 --mode upfront`. **Sources:** [[T-036-requirements]] · [[T-036-components]]

| Field | Value |
|-------|-------|
| Basis | components |
| Units estimated | 15 (K1-K6, U1-U7, X1, X2) |
| Confidence | Medium (0.8x to 1.3x of M, per the cone; no actuals yet) |

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | 64.2 | 46.1 | 77.6 | 8.0 |
| QC | 40.7 | 31.6 | 40.7 | 5.1 |
| Risk reserve | 10.5 | — | — | 1.3 |
| **Final / Complete** | **115.4** | **77.7** | **118.2** | **14.4** |

> Calendar days are indicative only — no capacity/parallelism model applied. This is the generic model's envelope; the plan's own build total is 44.5 h of Dev work (see Reconciliation) and is reported separately in [[T-036-plan]].

---

## Assumptions
1. One builder, serial work: the six shared files carry other tickets' uncommitted hunks, so parallel edits are not planned.
2. Dev-authored automated tests are inside each unit (there is no JS runner; JS is covered by Python source-regexp tests).
3. The 31 [BROWSER] acceptance criteria cannot be run by the pipeline; their manual execution is QC, not Dev.
4. Q1-Q5 defaults hold (Q2 sidecar included as a SHOULD; dropping K6 removes about 4 h M).
5. No new dependency, no Rust change, no `tech-select` needed (every choice is `confirm-existing`: stdlib `json`, `hashlib`, `threading`, `tomlio._replace`, `fetch keepalive`).

---

## Units

| Unit ID | Source | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------|-------|------|------:|--------|----------:|----------:|-------|
| K1 | prefs_store.py | service | S | 6.2 | new persisted structure +30%, concurrency +25% | 4.3 | 7.8 | pure module, lock, validation, import/reset; tests included |
| K2 | prefs_feature.py + plugins row | service | S | 4.0 | — | 2.8 | 5.0 | four routes, provider, audit calls, first real-HTTP test in this repo |
| K3 | audit.ACTIONS | service | XS | 2.0 | — | 1.4 | 2.5 | one tuple edit beside a foreign hunk; XS is the floor |
| K4 | ui_version.py | service | S | 4.0 | — | 2.8 | 5.0 | stat-only digest, vanish/unlistable rules |
| K5 | shell_feature.config() | service | XS | 2.0 | — | 1.4 | 2.5 | three fields over time, foreign-dirty file |
| K6 | desktop/sidecar.py (SHOULD) | service | S | 4.0 | — | 2.8 | 5.0 | fake-server tests; droppable |
| U1 | core.js C.prefs | UI | M | 10.0 | concurrency/shared-state +25% (M 8 -> 10) | 7.0 | 12.0 | map, debounce, keepalive flush, retry, hydrate bound, migration |
| U2 | core.js holdReload | UI | XS | 2.0 | — | 1.4 | 2.4 | tiny registry |
| U3 | app.js boot + pickup + nav once-guard | UI | S | 4.0 | — | 2.8 | 4.8 | foreign hunks around the edit |
| U4 | app.js compare/notice/idle/busy/guard | UI | M | 12.0 | unknown / spike +50% (A-6, A-7 unverified) (M 8 -> 12) | 8.4 | 14.4 | largest new JS block |
| U5 | agents.js + todos.js holds | UI | XS | 2.0 | — | 1.4 | 2.4 | one call each |
| U6 | settings.js storage() + wording, about.js | UI | S | 4.0 | — | 2.8 | 4.8 | foreign hunks; T-031 edits the same file |
| U7 | styles.css notice class | UI | XS | 2.0 | — | 1.4 | 2.4 | mid-file insert, stylesheet tests |
| X1 | README, plugins.toml, registry.py text | docs | XS | 2.0 | — | 1.8 | 2.2 | wording only |
| X2 | release note + verification plan | docs | S | 4.0 | — | 3.6 | 4.4 | relaunch step, BROWSER list |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total (M) |
|-------|------:|--------:|----:|--------:|---------------:|
| Data | 0 | 0.0 | 0.0 | 0.0 | 0% |
| Service | 6 | 15.5 | 22.2 | 27.8 | 34.6% |
| UI | 7 | 25.2 | 36.0 | 43.2 | 56.1% |
| Test | 0 (inside units) | 0.0 | 0.0 | 0.0 | 0% |
| Docs | 2 | 5.4 | 6.0 | 6.6 | 9.3% |
| **Total** | **15** | **46.1** | **64.2** | **77.6** | 100% |

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Data | 0.0 | 20% | 0.0 |
| Service | 22.2 | 25% | 5.6 |
| UI | 36.0 | 35% | 12.6 |
| Integration | 0.0 | 40% | 0.0 |
| Docs | 6.0 | 0% (no ratio in the model) | 0.0 |
| **Base QC (Σ)** | | | **18.2** |

| Factor | Value |
|--------|-------|
| Cycle profile | high risk (spike and concurrency adders present) |
| Cycle factor | x1.8 |
| UAT support | 8 h (Dev Σ M 41-80 h) |
| **QC total** | **40.7 h** [31.6-40.7] |

Reading of this number: the generic ratios overshoot the real manual surface. The actual QC work is the 31 [BROWSER] checks plus the Tauri-webview pass (AC-22), which a person must run; [[T-036-plan]] task 22 holds the 2 h pipeline part and the plan hands the rest to the verifier and the owner as "not verified in a browser" rather than hiding it inside a Dev task.

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | 64.2 | 46.1 | 77.6 |
| QC total | 40.7 | 31.6 | 40.7 |
| Risk reserve (+10%, components basis) | 10.5 | — | — |
| **Final / Complete** | **115.4** | **77.7** | **118.2** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|
| K1 | New schema / migration | +30% | new persisted file `console/.cache/prefs.json` |
| K1 | Concurrency / shared-state | +25% | module lock over read-modify-write on a threaded server |
| U1 | Concurrency / shared-state | +25% | debounce, in-flight flush, retry, re-apply of queued deltas over hydrate/import |
| U4 | Unknown / spike required | +50% | A-6 (hidden WebView2 window) and A-7 (reload re-runs the Rust init script) are unverified |

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| R-1 | [[T-036-plan]] § Risks, shared dirty files | a foreign hunk lands mid-build; re-read/retry costs time on U3, U4, U6, K5, K3, U7 |
| R-2 | NFR-2, 3.11 | a 3.12+ construct found only in CI; local Python is 3.14 |
| R-3 | A-6, A-7 | a defect found in the webview after build (AC-22 says fix page-side before ship) |
| R-4 | first real-HTTP test for `httpd.Handler` | no existing pattern (`test_ui_endpoints.py` uses the router only) |

## Reconciliation with the task breakdown

- Dev tasks total **44.5 h** ([[T-036-task-breakdown]]); envelope Dev M 64.2 h, range [46.1, 77.6]. Tasks are 3.5% under the lower bound and nowhere near the 10%-over-upper replan trigger.
- The gap to M is explained, not hidden: six units sit on the 2 h XS floor while their tasks total about 5.5 h (about +6.5 h), U4 carries a 4 h spike adder that the plan handles by [BROWSER] verification and a "fix page-side before ship" rule instead of build time, and K1/U1 adders add about 4 h over their task hours.
- Task-level PERT (layer multipliers service 1.25, UI 1.20, docs 1.10, test 1.15; no actuals, so confidence Low): expected 43.8 h, range 31.2-53.8 h. Re-run `estimate(mode=forecast)` after 5+ tasks have actuals.

## Recommendations
1. Treat 44.5 h as the build budget and 46-54 h as the realistic band; use the envelope's QC and reserve lines only as order-of-magnitude.
2. Q2 (sidecar) is the one separable block: dropping tasks 19-20 removes 3 h of tasks and 4 h of envelope M.
3. Re-forecast with `estimate(mode=forecast)` after task 10 (end of the prefs half) and after `replan` if a shared-file collision forces rework.

---

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-10-05 | components | 64.2 | 40.7 | 115.4 | 77.7-118.2 | Initial sizing from [[T-036-components]]; task total 44.5 h reconciled above |

## Links
- [[T-036-summary]] · [[T-036-requirements]] · [[T-036-components]] · [[T-036-plan]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-effort-estimate]] · [[T-036-critique-report]]
- [[T-036-decision-log]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-user-stories]] · [[T-036-verification]]
