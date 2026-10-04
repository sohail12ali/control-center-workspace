---
ticket: "T-017"
artifact: gap-analysis
status: resolved
created: "2026-09-16"
last_updated: "2026-09-16"
---

# Gap Analysis: T-017

**Sources:** [[T-017-requirements-draft]] · [[T-017-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 1  | 0   | 1     |
| Business rules  | 0  | 0  | 0   | 0     |
| Edge cases      | 0  | 1  | 0   | 1     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 0  | 1  | 0   | 1     |
| Integrations    | 0  | 0  | 1   | 1     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 1  | 0   | 1     |
| **Total**       | **0** | **5** | **1** | **6** |

No 🔴 (blocker) gaps. All 🟡 gaps were resolvable from GROUND-stage evidence and closed as documented assumptions (Auto Mode: proceed, don't stall on judgment calls a human doesn't need to make).

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-16 | — | Initial pass from `challenge-requirements` (gaps) | analyst |
| 2026-09-16 | S-1 | Accepted as documented assumption (A3) | analyst |
| 2026-09-16 | E-1 | Accepted as documented assumption + AC (FR-8 concurrency AC) | analyst |
| 2026-09-16 | N-1 | Accepted as documented, deferred NFR (§5 Security row) | analyst |
| 2026-09-16 | D-1 | Accepted as documented assumption (A2) | analyst |
| 2026-09-16 | U-1 | Accepted as ⚠, treated out-of-scope pending confirmation (§13) | analyst |
| 2026-09-16 | C-1 | Accepted as documented assumption (A4) | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| S-1 | 🟡 | No named owner for the future T-018 worktree/branch work that depends on `claim`'s field contract | Recorded as an informational (non-sign-off) stakeholder row (§11); `claimed_by`/`claimed_at` field names frozen in this ticket so T-018 doesn't need a schema migration |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | none found | — |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| E-1 | 🟡 | Concurrent `claim` calls on the same ticket — race condition not addressed by any existing atomic-write pattern documented in the codebase for `ticket.toml` | Added as explicit edge case (§8) and acceptance criterion (FR-8); builder must reuse/extend the atomic-write approach `tickets.py`/`trackers.py` already need for any concurrent CLI use |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| N-1 | 🟡 | No auth/security model specified for the new MCP-over-HTTP transport | Documented as an explicit, deferred `〈TBD〉` in NFR §5 with rationale (console has no existing auth boundary either); not blocking since this mirrors today's `serve` trust model |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| D-1 | 🟡 | No existing storage target for `comment` (trackers.py's `VALID_KINDS` doesn't include it, and its own header calls new kinds "reserved") | Resolved via A2: add `comments` as a 4th kind, non-blocking (mirrors `todos`) |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| I-1 | 🟢 | Editor MCP config file locations for `console setup cursor|claude|vscode` are not all confirmed with file:line evidence (this workspace's own `.mcp.json` exists; Cursor/VS Code per-editor conventions are external, not in this repo) | Non-blocking: implementation detail for planner/builder to confirm per-editor at build time; requirements only mandates the outcome (FR-11), not the exact file path |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| U-1 | 🟡 | Plan's mermaid diagram implies UI EventSource live-sync as part of "one API," not named in the explicit 5-item scope list | Flagged as ⚠ in requirements §13; treated as out-of-scope for T-017 pending explicit user confirmation, since scope-list + out-of-scope list are the canonical scope statements per task instructions |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | none found | — |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| C-1 | 🟡 | "Tracker SPI" (plan's ticket-backend abstraction) collides in name with `console/server/trackers.py` (questions/bugs/todos CRUD) | Resolved via A4: new interface named "Backend SPI" in requirements/code; plan's "tracker-spi" kept only as the scope-item label |

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements-draft]] · [[T-017-context-snapshot]] · [[T-017-gap-analysis]] · [[T-017-iteration-log]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
