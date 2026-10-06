---
ticket: "T-039"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
created: "2026-10-06"
last_updated: "2026-10-06"
---

# Requirements Draft: T-039

> Working document, now **frozen at iteration 1**. The numbered FRs, ACs and NFRs live in [[T-039-requirements]] (one fact, one file); this draft keeps the narrative, rules, edge cases and history. Post-freeze changes go through `evolve`.

**Legend:** `⚠` challenge finding (all closed, see [[T-039-critique-report]]) · tags **[PY]** pytest, **[BROWSER]** needs a real browser (not verified by any agent).

---

## 1. Intent

**Stakeholder:** Sohail Ali (owner).

**Outcome:** one list that only a person clears, apart from what needs repair; every panel says when its data is from and marks itself STALE past a threshold.

**Business driver:** a personal "AI OS" dashboard video ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]) showed both; today the Overview mixes the two kinds and silently shows old data.

**Raw intent verbatim:**
> a list reserved for what only a human can resolve ("Needs you"; the agent never marks an item done, only a person clears it) separate from items that need repair (failed or timed-out runs, stale or unowned tickets); every panel shows its own timestamp and is marked STALE after a threshold, rather than hiding or silently showing old data.

## 2. Context Summary

(Condensed from [[T-039-context-snapshot]])

- **Similar existing features:** `needs_attention` (`console/server/overview.py:36-100`), Overview "Needs attention" panel (`overview.js:272-303`), nav badge (`app.js:286-295`), `C.panel` (`core.js:228-245`), shared prefs (`prefs_store.py`), static export (`export.py:50-52`).
- **Affected code areas:** `overview.py`, `overview.js`, `core.js`, `app.js`, `styles.css`, `about.js`; tests `test_attention.py`, `test_splitter.py`, plus new ones.
- **Known risks from history:** shared files with T-037; pinned test ids; heartbeat only fires on success.

## 3. Scope

### In scope
- Needs you / Needs repair split in payload, page and badge; `generated_at`; `fresh` option on `C.panel`; STALE mark; `staleAfterSecs` preference; Refresh button; static export stamp.

### Out of scope (explicit)
- Routines board (T-040), brain views (T-038), clock, heatmap, deep-work bar, gate countdown, system gauges (user's list).
- Non-Overview panels, a Settings control, auto-refresh, a new JS file, server-side prevention of agent status changes (smallest ticket of the four).

### Assumptions
- Answered questions are repair, not human wait (Q1). The badge counts Needs you only (Q2). Threshold 300 s (D-11).

## 4. Functional Requirements

FR-1..FR-14 with acceptance criteria AC-1.1..AC-14.2 are in [[T-039-requirements]] (44 ACs: 24 [PY], 20 [BROWSER]). Rationale per decision: [[T-039-decision-log]].

## 5. Non-Functional Requirements

NFR-1..NFR-12 in [[T-039-requirements]] (ES5, CSS rules, no new file/script, 900 px cliff, no dependency, compatibility, testable server logic, deliberate test-pin update, cost, line endings, baseline, shared files).

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `attention` payload | exists | adds `needs_you`, `needs_repair`, `answered`, `counts.needs_you`, `counts.needs_repair`; entries gain `type`, `ref`, `priority` | derived per request, never stored | `overview.py:36-100` |
| `full_overview` payload | exists | adds `generated_at` | derived | `overview.py:140-147` |
| view preference `staleAfterSecs` | new key in existing store | number 30..86400 | user-set, synced by T-036 | `prefs_store.py` |

### Data flows
trackers, runs, approvals registry, tickets -> `needs_attention` -> `/api/overview` and static `data.js` -> Overview panels and nav badge; `generated_at` -> `C.panel` `fresh.asOf` -> `<time>` and STALE chip. Jobs/Schedules: browser fetch time -> `fresh.asOf`.

### Retention / archival
None; nothing is stored beyond the one preference.

## 7. Business Rules

- **BR-1:** Needs you contains only items a person must act on: open questions, pending approvals.
- **BR-2:** Needs repair contains items the system or an agent fixes; answered-not-applied questions are among them.
- **BR-3:** Nothing on the Overview marks anything done or dismisses it; an item leaves when its underlying state changes.
- **BR-4:** Data is never hidden or replaced because it is old; it is marked STALE and keeps its time.
- **BR-5:** The "as of" time is when the data was produced (server stamp), or for Jobs/Scheduled when the browser last fetched successfully; it never advances on a failed fetch.

## 8. Edge Cases

- More than 50 open items: first 50, exact count, "and N more" (FR-3).
- Server stopped after load: panels stay and age into STALE (AC-8.4).
- Collapsed stale panel: chip still visible (AC-7.3).
- Old static export: STALE on open (AC-11.1).
- Clock skew or unparsable stamp: age 0 or stale (AC-7.2).
- Invalid preference value: default 300 (AC-9.2).
- Zero items: positive empty states (FR-5).

## 9. Interactions with Existing Features

See the table in [[T-039-gap-analysis]] (overlap 3, conflict 2, reuse 2).

## 10. External Dependencies

- None. No new package or service. Telegram approvals unchanged.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner | Sohail Ali | list semantics, badge, STALE wording | yes (Q1, Q2 defaults to confirm) |
| Console users (desktop app, browsers) | — | fast, not noisy | no |

## 12. Open Questions (mirrored)

Mirrored from `T-039-questions.toml`.

- Q1: answered questions in Needs repair (default) or Needs you? — status: open, low, non-blocking
- Q2: badge counts Needs you only (default) or also a repair count? — status: open, low, non-blocking

## 13. Challenge Findings (⚠)

All 16 (CR-1..CR-16) resolved or accepted; see [[T-039-critique-report]]. No open ⚠.

## 14. Draft History

See [[T-039-iteration-log]]. Current iteration: **1**. Frozen 2026-10-06.

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred
- [x] All ⚠ findings resolved or explicitly accepted with rationale (CR-11, CR-16 accepted)
- [x] All blocker open questions answered (none are blockers; Q1, Q2 non-blocking with defaults)
- [x] Every FR has at least one testable acceptance criterion (14 FRs, 44 ACs)
- [x] Every NFR has a concrete target or documented reason for absence (12)
- [x] Every new/changed entity has a canonical reference or creation plan
- [x] Out-of-scope list is non-empty
- [ ] Stakeholder sign-off recorded: pending the parent session / user (Q1, Q2 defaults)
- [x] Frozen requirements written to [[T-039-requirements]] (no separate `-requirements-summary` file: the frozen file is the summary the stories op reads)

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
- Upstream: [[INV-2026-10-06-maps-os-ui-adoption-dossier]]
