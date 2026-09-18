---
ticket: "T-004"
artifact: effort-estimate
basis: "components"
confidence: "Medium"
---

# Effort estimate: T-004

> **STALE as of amendment 2026-09-06 — see [[T-004-decision-log]] § Amendment 2026-09-06 and the Revision log at the bottom of this file.** Every number below (Units table, QC math, Executive summary, 85.0h Final/Complete) still reflects the pre-amendment 12-component scope. Post-descope, `T-004-task-breakdown.md`'s Dev total is **40.5h** (was 47.5h) across 36 tasks (was 41) — C9/FR-8 (6.5h) and task 3-7-3 (1.5h) deferred to T-006, 2 new FR-6 tasks added (1h). This file is **not recomputed**; re-run `estimate(mode=forecast)` before citing Final/Complete for scheduling.

**Produced by:** `estimate T-004 --mode upfront`. **Sources:** [[T-004-requirements]] · [[T-004-components]] · [[T-004-task-breakdown]]

| Field | Value |
|-------|-------|
| Basis | components (each unit's M taken from `T-004-task-breakdown.md`'s per-component task sums — finest available, no separate T-shirt re-sizing) |
| Units estimated | 12 |
| Confidence | Medium |

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | 47.5 | 33.3 | 68.4 | 5.9 |
| QC | 29.8 | 23.7 | 29.8 | 3.7 |
| Risk reserve | 7.7 | — | — | 1.0 |
| **Final / Complete** | **85.0** | **57.0** | **98.2** | **10.6** |

> Calendar days are indicative only — no capacity/parallelism model applied. QC upper equals QC most-likely because the high-risk cycle profile (below) already sits at the top of the 1.3-1.8x band.

---

## Assumptions
1. One engineer, no parallel pairing; the 3-phase build order (`T-004-components.md`) is followed, not fully parallelized.
2. Frontend JS tasks (`agents.js`, `assistant.js`, `settings.js`) have dev effort counted under UI but no dedicated automated-test cost beyond what's already in their task hours — this repo has no JS unit-test harness, so their QC is manual smoke, folded into the UAT support line, not a separate JS-test layer.
3. `console/config/assistant.md`'s persona-text authoring (C3) is counted as service/plumbing effort, not a separate docs/artifact layer — it is small and load-bearing (safety rules), not reference documentation.

---

## Units

| Unit ID | Source | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------|-------|------|------:|--------|----------:|----------:|-------|
| C0 | audit ACTIONS | service | XS | 1.0 | — | 0.7 | 1.25 | zero-risk, pattern reuse |
| C1 | session/extra threading | service | M | 5.5 | — | 3.85 | 6.9 | bottleneck; 6 files touched but each additive |
| C8 | file-based memory | data | S | 3.0 | — | 2.1 | 4.05 | gitignored `.cache` pattern already exists |
| C10 | native_bridge stub | service | XS | 1.0 | — | 0.7 | 1.25 | isolated leaf, trivial |
| C2 | assistant_feature.py routes | service | M | 7.0 | — | 4.9 | 8.75 | 5 routes, one plugin row |
| C3 | persona + second root | service | S | 3.0 | — | 2.1 | 3.75 | pattern reuse (persona_text) |
| C6 | new verbs | service | M | 7.0 | — | 4.9 | 8.75 | kickoff verb is the real work (3h of the 7) |
| C4 | injected context | service | S | 2.0 | — | 1.4 | 2.5 | assembly only — caps/truncation already proven in `prompt_build.build` |
| C5 | fast-command table | service | M | 6.0 | Unknown/spike (no analogue) | 4.2 | 9.0 (7.5 base ×1.2, see below) | novel — highest risk concentration #1 |
| C7 | settings picker | service+UI | S | 4.5 | — | 3.15 | 5.5 | service 3.0 + UI 1.5 |
| C9 | reply path + is_assistant | service+UI | M | 6.5 | Unknown/spike (no analogue) | 4.55 | 8.7 (7.25 base, +15% widened) | novel — highest risk concentration #2 |
| C11 | CLI parity | service | XS | 1.0 | — | 0.7 | 1.25 | argparse subgroup pattern |
| **Total** | | | | **47.5** | | **33.3** | **59.5** (68.4 after unknowns widening, see Risks) | |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total |
|-------|------:|--------:|----:|--------:|-----------:|
| Data | 1 (C8) | 2.1 | 3.0 | 4.05 | 6% |
| Service | 10 (C0,C1,C10,C2,C3,C6,C4,C5,C7-svc,C9-svc,C11) | 28.7 | 41.0 | 51.25 | 86% |
| UI | 2 (C7-UI, C9-UI) | 2.45 | 3.5 | 4.2 | 8% |
| Test | — | — | — | — | folded into each unit's own hours (bottom-up tasks already include test-writing time) |
| **Total** | 12 | **33.25** | **47.5** | **59.5** | 100% |

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Data | 3.0 | 20% | 0.6 |
| Service | 41.0 | 25% | 10.25 |
| UI | 3.5 | 35% | 1.225 |
| Integration | 0 | 40% | 0 |
| **Base QC (Σ)** | | | **12.075 ≈ 12.1** |

| Factor | Value |
|--------|-------|
| Cycle profile | High risk (C5 and C9 both carry the "Unknown/spike required" adder — novel, no in-repo analogue) |
| Cycle factor | ×1.8 |
| UAT support | 8h (Dev Σ M = 47.5h falls in the 41-80h band) |
| **QC total** | **29.8h** [23.7-29.8] |

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | 47.5 | 33.3 | 68.4 |
| QC total | 29.8 | 23.7 | 29.8 |
| Risk reserve | 7.7 | — | — |
| **Final / Complete** | **85.0** | **57.0** | **98.2** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|
| C5 (fast-command table) | Unknown / spike required | +50% conceptually reflected in the base M already (6h vs 1-3h for pattern-reuse units); +15% additional Dev-upper widening applied at the aggregate level | No existing analogue beyond `telegram_bot._dispatch`'s dispatch *shape*; natural-language whole-utterance matching/normalisation is net-new (`T-004-components.md` risk flag) |
| C9 (reply path + is_assistant) | Unknown / spike required | same treatment as C5 | No prior mechanism distinguishes "this chat" from "the assistant's own chat" (`T-004-components.md` risk flag) |

Dev upper after the +15% unknowns widening: 59.5 × 1.15 = **68.4h** (used in the executive summary above in place of the un-widened 59.5h).

---

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| R1 | `T-004-components.md` — C5 fast-command table flagged novel/no-analogue | +15% Dev upper (applied); high-risk QC cycle factor (×1.8, applied) |
| R2 | `T-004-components.md` — C9 reply-path/is_assistant guard flagged novel/no-analogue | same as R1 |
| R3 | Frontend tasks (3-7-3, 3-8-5, 3-8-6) have no automated test harness in this repo | QC relies on manual smoke recorded in `T-004-verification.md`; if a JS regression harness is later added, QC hours for these 3 tasks (3.5h Dev) would need re-forecasting |

---

## Recommendations
1. **Reconcile before build:** this bottom-up estimate (47.5h Dev, 85.0h Final/Complete ≈ 10.6 days) diverges materially from the source plan's stated "M · 3 d" (24h) sizing — see reconciliation note below. Confirm with the ticket owner whether the 3-day figure was a rough T-shirt guess (pre-decomposition) or a hard constraint before committing to a schedule.
2. Reforecast via `estimate(mode=forecast)` once the first few Phase-1 tasks (C1's bottleneck slice) have actuals — C1 is the piece most likely to reveal whether the "additive kwargs through 3-4 files" framing in `T-004-components.md` holds up in practice.
3. Treat C5 and C9 as the tasks to build (and pad) first within their phase, consistent with `T-004-components.md`'s own guidance ("plan/estimate effort here, not in the plumbing").

---

## Reconciliation against the source plan's sizing

The programme plan (`our-project-is-in-optimized-treasure.md` § "Programme — tickets in delivery order") sizes T-004 as **"M · 3 d"** (≈24h at 8h/day). This bottom-up estimate's Dev-only total is **47.5h** (≈2.0x) and its Final/Complete total is **85.0h** (≈3.5x). This is a genuine, plainly-stated divergence, not a rounding difference:

- The plan's "M · 3 d" was an order-of-magnitude programme-level T-shirt size assigned before any component decomposition existed (it sits in a table alongside T-003 "S · 2 d" and T-005 "L · 4-5 d" — a comparative sizing across 5 tickets, not a task-level roll-up).
- `T-004-components.md`'s own dependency-graph analysis independently flagged 2 of 12 components (C5, C9) as carrying real, unbounded implementation risk with no in-repo analogue — exactly the kind of risk a pre-decomposition T-shirt size cannot see.
- 41 atomic tasks against 12 components, most touching 3-6 real files each (`T-004-task-breakdown.md`), is a larger surface than "M" (8h baseline per the T-shirt table) implies even before QC/reserve.

**This is not force-fit to 3 days.** The recommendation is to carry the bottom-up number (47.5h Dev / 85.0h Final/Complete, ≈10.6 days indicative) forward into `T-004-implementation-plan.md` and flag the gap to the ticket owner explicitly, rather than silently reporting "3 days" alongside a 41-task breakdown that cannot fit it.

---

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-09-06 | components (from task-breakdown) | 47.5 | 29.8 | 85.0 | 57.0-98.2 | Initial bottom-up sizing, post-`breakdown-tasks`. Diverges from plan's pre-decomposition "M · 3d" — see reconciliation note. |
| 2026-09-06 (amendment) | — | — | — | **STALE** | — | Post-descope (see [[T-004-decision-log]] § Amendment 2026-09-06): C9 (6.5h) deferred in full to T-006, task 3-7-3 (1.5h) deferred to T-006, 2 new FR-6 tasks added (1h). `T-004-task-breakdown.md`'s Dev total is now **40.5h** (was 47.5h). The Units table above, its QC/complexity-adder math, and the 85.0h Final/Complete figure are **not recomputed here** — they still reflect the pre-amendment 12-component scope and should not be cited as current. Re-run `estimate(mode=forecast)` before using this artifact for scheduling. |

## Links
- [[T-004-summary]] · [[T-004-requirements]] · [[T-004-components]] · [[T-004-task-breakdown]] · [[T-004-implementation-plan]] · [[T-004-effort-estimate]] · [[T-004-effort-forecast]]
