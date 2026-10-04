---
ticket: "T-021"
artifact: gap-analysis
status: closed-except-G17
created: "2026-10-01"
last_updated: "2026-10-01"
---

# Gap Analysis: T-021

**Sources:** [[T-021-requirements-draft]] · [[T-021-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 2  | 0   | 2     |
| Business rules  | 3  | 1  | 0   | 4     |
| Edge cases      | 0  | 2  | 1   | 3     |
| NFRs            | 1  | 0  | 1   | 2     |
| Data / entities | 0  | 1  | 0   | 1     |
| Integrations    | 1  | 0  | 1   | 2     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 2  | 0   | 2     |
| Cross-cutting   | 0  | 3  | 0   | 3     |
| **Total**       | **5** | **12** | **3** | **20** |

19 of 20 are closed or accepted (Resolution Log); G17 stays open and non-blocking (needs a user edit, Q11). Every 🔴 was logged as a critical question and resolved under delegated authority.

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-01 | — | Initial pass from `challenge-requirements` (gaps) | analyst |
| 2026-10-01 | G3 | Q12 resolved: verifier reports a Disposition, harness or user closes (FR-11, a12) | analyst |
| 2026-10-01 | G4 | Q5 resolved: evidence classes and block/warn split (FR-8, a5) | analyst |
| 2026-10-01 | G5 | Q4 resolved: pending question and blocked owner/action defined (BR-4, BR-8, a4) | analyst |
| 2026-10-01 | G10 | Q9 resolved: trim `assistant.md`, keep cap (FR-5, a9) | analyst |
| 2026-10-01 | G13 | Q10 resolved: slice B after T-020, named consumption (a10) | analyst |
| 2026-10-01 | G1, G2, G6-G9, G11, G12, G14-G20 | Resolved or accepted in iterations 1 and 2 (see per-row resolution) | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | T-022 pins prompt/skill quotes; nobody lists which files this ticket edits | Resolved: file list in [[T-021-analysis]] § Recommended Path and [[T-021-requirements]]; T-022 builds after T-020 and T-021 |
| G2 | 🟡 | T-020 and T-021 edit the same files (`context.py`, `verb_handlers.py`, `verbs.toml`, `verifier.md`) | Resolved: T-020 builds first; FR-11 applies on top of T-020 FR-25; shared files listed |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G3 | 🔴 | Who closes a ticket is stated three ways (verifier step, contract, CLAUDE.md) (Q12) | Resolved: FR-11, BR-2 |
| G4 | 🔴 | What counts as evidence and what blocks versus warns is unstated (Q5) | Resolved: FR-8, BR-3, calibrated on 212 rows |
| G5 | 🔴 | "Pending question", "owner", "next action" undefined (Q4) | Resolved: BR-4, BR-8 |
| G6 | 🟡 | Whether the blocked rule is retroactive (Q3) | Resolved: transition-only, BR-1 |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G7 | 🟡 | Tickets with no verification table (T-019), several tables, markdown in status cells | Resolved: § 8, FR-8 status classes |
| G8 | 🟡 | A claim expires after 8 h with no Run while humans work for days | Resolved: `claim_stale` warn with re-claim as the heartbeat; blocks only at close |
| G9 | 🟢 | Check and move are not atomic | Accepted: window is small; audit records what was checked |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G10 | 🔴 | Persona text is capped at 4,000; `assistant.md` is 4,725 (Q9) | Resolved: FR-5, NFR-7, BR-10 |
| G11 | 🟢 | No performance target for scan/check | Resolved: NFR-6 |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G12 | 🟡 | Evidence ref syntax not defined | Resolved: grammar in FR-8, data entity row |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G13 | 🔴 | Depends on T-020 names and on Runs ever finishing (Q10) | Resolved: consumption table, slice split, adapt-at-start rule |
| G14 | 🟢 | New verbs must reach CLI, MCP, HTTP | Resolved: three `verbs.toml` rows, ACs assert MCP and `verb list` |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G15 | 🟡 | Board drag to done bypasses the gate | Accepted: human surface, UI out of scope (BR-11); todo TD-3 |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G16 | 🟡 | Override needs a reason and a trace | Resolved: FR-10, NFR-5 |
| G17 | 🟡 | A hard human gate on `close-override` needs a hand edit of `agents.toml` | Open, non-blocking: Q11; design works without |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G18 | 🟡 | 20 standing WARNs after FR-1 conflict with any later "0 warnings" criterion | Resolved: stated in analysis, edge cases and the final report; TD-1 trims then raises to ERROR |
| G19 | 🟡 | Semantic doc drift is not detectable deterministically | Accepted: limit stated (FR-4, NFR-8) |
| G20 | 🟡 | Rollout: gates must not touch existing tickets | Resolved: BR-1, NFR-4 |

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements-draft]] · [[T-021-requirements]] · [[T-021-context-snapshot]] · [[T-021-critique-report]] · [[T-021-iteration-log]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
