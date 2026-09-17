---
ticket: "T-016"
artifact: gap-analysis
status: open
created: "2026-09-11"
last_updated: "2026-09-11"
---

# Gap Analysis: T-016

**Sources:** [[T-016-requirements-draft]] · [[T-016-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 1   | 1     |
| Business rules  | 1  | 0  | 0   | 1     |
| Edge cases      | 0  | 1  | 1   | 2     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 1  | 0  | 0   | 1     |
| Integrations    | 1  | 0  | 0   | 1     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 1  | 0   | 1     |
| **Total**       | **3** | **4** | **2** | **9** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-11 | G2,G5,G6,G7,G8,G9 | Closed in iterate from Q1–Q4 | Irshad |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟢 | Only Irshad is named; no second operator persona (remote Telegram user). | Accept: one-user workspace. |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🔴 | Hybrid “launch in Cursor” has no rule for what happens if Cursor is not running. | Q1; if (a), degrade to a prompt package on disk. |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G3 | 🟡 | Two Runs on one ticket: merge vs parallel not AC’d beyond “allow two”. | Keep allow-two; inspector groups by ticket. |
| G4 | 🟢 | Empty ticket strip (no active tickets). | Home still shows Assistant; strip empty is valid. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G5 | 🟡 | Run concurrency cap unmeasurable until Q2. | Bind cap to chosen store. |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G6 | 🔴 | Run entity has no canonical file/schema (Q2). | Decision log after Q2; then a module next to `jobs.py` or an extension of it. |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G7 | 🔴 | No Cursor inbound start API in-repo (Q1). | Stakeholder pick a/b/c. |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G8 | 🟡 | “Drawers” vs tabs (Q4) changes information architecture tests. | Pick tab vs chrome. |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G9 | 🟡 | Q3 extra verbs could expand T-016 past locked In. | Default defer; confirm. |

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements-draft]] · [[T-016-context-snapshot]] · [[T-016-gap-analysis]] · [[T-016-iteration-log]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
