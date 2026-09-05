---
ticket: "T-002"
artifact: gap-analysis
status: open
created: "2026-09-05"
last_updated: "2026-09-05"
---

# Gap Analysis: T-002

**Sources:** [[T-002-requirements-draft]] · [[T-002-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 0   | 0     |
| Business rules  | 0  | 0  | 0   | 0     |
| Edge cases      | 0  | 1  | 0   | 1     |
| NFRs            | 0  | 0  | 1   | 1     |
| Data / entities | 0  | 0  | 0   | 0     |
| Integrations    | 0  | 1  | 0   | 1     |
| UX / UI         | 0  | 0  | 1   | 1     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 0  | 0   | 0     |
| **Total**       | **0** | **2** | **2** | **4** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-05 | — | Initial pass from `challenge-requirements` (gaps) | — |
| 2026-09-05 | G1 | Folded into FR-5 iterate | analyst |
| 2026-09-05 | G2 | Accepted: smoke AC | analyst |
| 2026-09-05 | G3 | Folded into FR-1 iterate | analyst |
| 2026-09-05 | G4 | Folded into NFR usability | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | FR-5 does not say which chat to interrupt if more than one is `busy` | Interrupt the Agents tab’s selected chat if busy; else the first busy chat in the existing chats list (`agents.js` `st.chats`); never create a chat |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟢 | Tray-icon presence has no automated test harness (T-001 sidecar tests are headless) | AC evidence is manual/smoke plus unit tests for sidecar-unaffected hide/quit; say so in NFR Usability/Testing |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G3 | 🟡 | FR-1 header backend name: Rust does not know `meta.agent`; no event specified | JS emits backend label on chat open/change; native menu header updates; default `—` until first event |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G4 | 🟢 | No tray tooltip / idle icon spec | Use product name “Delivery Console” as tooltip; bundled icon; idle only |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | — | — |

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements-draft]] · [[T-002-context-snapshot]] · [[T-002-gap-analysis]] · [[T-002-iteration-log]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
