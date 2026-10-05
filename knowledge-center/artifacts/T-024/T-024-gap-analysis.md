---
ticket: "T-024"
artifact: gap-analysis
status: open
created: "2026-10-04"
last_updated: "2026-10-04"
---

# Gap Analysis: T-024

**Sources:** [[T-024-requirements-draft]] · [[T-024-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 0   | 0     |
| Business rules  | 0  | 1  | 0   | 1     |
| Edge cases      | 1  | 1  | 0   | 2     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 0  | 0  | 0   | 0     |
| Integrations    | 1  | 1  | 0   | 2     |
| UX / UI         | 0  | 0  | 0   | 0     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 1  | 1  | 0   | 2     |
| **Total**       | **3** | **5** | **0** | **8** |

All gaps were closed in iteration 1 (see Resolution Log); zero open at freeze.

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-04 | — | Initial pass from `challenge-requirements` (gaps) | analyst |
| 2026-10-04 | G-EDGE-1, G-INT-1, G-X-1 | closed in iteration 1: FR-2 validity rules, FR-3 setup_editor, FR-5 root split | analyst |
| 2026-10-04 | G-BR-1, G-EDGE-2, G-NFR-1, G-INT-2, G-X-2 | closed in iteration 1 (BR-3/BR-4, FR-6, NFR table, AC-3d smoke, Q1 deferred) | analyst |

---

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G-BR-1 | 🟡 | No rule says the anchor is only a locator that must be validated, nor that an explicit `start` argument wins. | BR-3, BR-4. |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G-EDGE-1 | 🔴 | "Valid" `CONSOLE_REPO_ROOT` undefined: empty, literal `${CONSOLE_REPO_ROOT:-}` (unexpanded), relative, nonexistent, non-root dir. A walk-up from a bad value could silently pick an ancestor. | FR-2: absolute existing dir that is a root or resolves via `workspace.toml`; no walk-up from the env value; else ignored. |
| G-EDGE-2 | 🟡 | Ticketless / non-git / `repo_root=""` unchanged behaviour not stated as ACs. | FR-6, FR-4 fallback `repo_root or cwd`. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G-NFR-1 | 🟡 | All targets `〈TBD〉`. | Concrete: no new deps/processes; suite count not reduced from the count measured at build start; no raise. |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G-INT-1 | 🔴 | `setup_editor('claude')` would erase the `.mcp.json` env block on next run. | FR-3: claude entry carries the env block; cursor/vscode untouched. |
| G-INT-2 | 🟡 | Claude's env pass-through / `${VAR:-}` expansion unverified; `.mcp.json` edit does not reach worktrees created before it is committed. | AC-3d live smoke on a fresh worktree; UNCERTAIN recorded in decision D3. |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G-X-1 | 🔴 | Root split for API sessions unspecified (verbs vs file tools; approvals preview vs notify; capture path). | FR-5 table. |
| G-X-2 | 🟡 | Markdown artifacts written by agent file tools stay in the worktree. | Out of scope; Q1 (open, low, non-blocking). |

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements-draft]] · [[T-024-context-snapshot]] · [[T-024-gap-analysis]] · [[T-024-iteration-log]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]]
