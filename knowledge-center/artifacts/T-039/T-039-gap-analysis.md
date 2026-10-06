---
ticket: "T-039"
artifact: gap-analysis
status: resolved
created: "2026-10-06"
last_updated: "2026-10-06"
---

# Gap Analysis: T-039

**Sources:** [[T-039-requirements-draft]] · [[T-039-context-snapshot]]. Severity: 🔴 blocker, 🟡 major, 🟢 minor. All 14 gaps are resolved or accepted in the frozen [[T-039-requirements]]; none is a blocker.

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 1   | 1     |
| Business rules  | 0  | 2  | 0   | 2     |
| Edge cases      | 0  | 4  | 2   | 6     |
| NFRs            | 0  | 0  | 1   | 1     |
| Data / entities | 0  | 1  | 0   | 1     |
| Integrations    | 0  | 1  | 1   | 2     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 0  | 0   | 0     |
| **Total**       | **0** | **9** | **5** | **14** |

### Interactions with existing features

| Existing feature | Kind | Risk | Action |
|---|---|---|---|
| "Needs attention" panel (`overview.js:272-303`) | overlap | med | split into two panels, keep `ov.attention` id on repair |
| Overview nav badge (`app.js:286-295`) | overlap | med | count Needs you only (D-5, Q2) |
| Ticket "Stale (N+ days)" tile and chip (`overview.js:265,277`) | conflict (name) | low | distinct element and title (D-9) |
| `test_splitter.py` id and handler pins (`:1118-1160`) | conflict | med | update ids deliberately (D-16, NFR-8) |
| `C.panel`, `C.empty`, `C.prefs`, `.chip` tones, `<time>` | reuse | low | extend, no new component file |
| Heartbeat and `ui_version` reload (`app.js:347-441`) | reuse (not) | low | separate 30 s clock; offline case (D-8) |
| Assistant home `attention.blocked` (`assistant.js:123`) | overlap | low | keep legacy keys (D-6) |

Counts: overlap 3, conflict 2, reuse 2.

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-06 | G1-G14 | Raised by `challenge-requirements` (gaps dimension) on draft v0; closed in iteration 1 | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟢 | Other readers of the payload: Assistant home, `kanban overview`, static export, Telegram. Checked: no Telegram, agent or MCP code reads `needs_attention` | Additive payload (FR-1, NFR-6); no action elsewhere |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟡 | Which kinds are "only a human can resolve": summary said open or answered questions, pending approvals, reviews | D-2, D-3: open questions and approvals; answered to repair; no review kind. Q1 records the override path |
| G3 | 🟡 | "The agent never marks an item done" cannot be guaranteed system-wide: the CLI can set a tracker status; `review-round human_decision` is audit-checked only | FR-2 states it for the Overview, tests it, records the limit (D-15) |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G4 | 🟡 | Cap of 8 hides human-only items (9 open questions measured) | FR-3 cap 50 with exact count and "and N more" |
| G5 | 🟡 | Server down: a heartbeat-driven tick never runs | Own 30 s clock (D-8, FR-12), AC-8.4 |
| G6 | 🟡 | Collapsed panel hides a footer mark | Chip in header (D-12), AC-7.3 |
| G7 | 🟡 | Failed refetch could blank or silently keep old data | `asOf` moves only on success (D-14), AC-8.4 |
| G8 | 🟢 | Static export opened later; clock skew (future `asOf`); unparsable `asOf` | Server stamp (D-10); age clamps at 0; unparsable is stale (FR-7, AC-7.2) |
| G9 | 🟢 | "Stale" already means ticket idle days | Distinct `.fresh-mark` element and title (D-9) |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G10 | 🟢 | A per-tick text rewrite makes screen readers chatter | Rewrite only on change; mark is a constant-text `role="status"` (FR-13, FR-12) |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G12 | 🟡 | `questions` key changes meaning (open only) and `generated_at` is new | Documented in D-6; new `answered` key; tests AC-1.4 |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G13 | 🟡 | `test_splitter.py` pins exactly six `ov.*` ids, 18 overall, and the handler text on `attnPanel` | NFR-8, AC-5.1: update deliberately, keep `attnPanel` |
| G14 | 🟢 | Assistant home reads `attention.blocked` | Legacy key retained (AC-1.4) |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G11 | 🟡 | Header at 400 px with title, count chip, STALE chip and chevron | Title truncates, as-of row wraps, AC-14.1 |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | None found: the change is read-only and adds no audit event, secret, or personal data | — |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | None beyond the shared-file and line-ending rules (NFR-10, NFR-12) | — |

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
