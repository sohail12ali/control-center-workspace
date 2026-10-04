---
ticket: "T-018"
artifact: gap-analysis
status: resolved
created: "2026-09-16"
last_updated: "2026-09-16"
---

# Gap Analysis: T-018

**Sources:** [[T-018-requirements-draft]] · [[T-018-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 0   | 0     |
| Business rules  | 0  | 2  | 0   | 2     |
| Edge cases      | 0  | 3  | 0   | 3     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 0  | 1  | 0   | 1     |
| Integrations    | 0  | 1  | 0   | 1     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 0  | 0   | 0     |
| Cross-cutting   | 0  | 1  | 0   | 1     |
| **Total**       | **0** | **9** | **0** | **9** |

No 🔴 (blocker) gaps found. All 🟡 gaps resolved in the v0→v1 draft revision (below), none deferred to a later ticket, none required escalation to the human — each was resolvable from existing codebase precedent (T-017's `claimed_by`/`claimed_at` schema-extension pattern, `worktrees.py`'s own stated safety rules, T-016's Run-object shape).

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-16 | BR-G1 | Added BR-2 + FR-1 worktree-reuse requirement | analyst |
| 2026-09-16 | BR-G2 | Added BR-5/BR-6 + FR-7 hint-only constraint with explicit non-automatic-move AC | analyst |
| 2026-09-16 | EDGE-G1 | Added edge case: manually deleted worktree treated as not-found | analyst |
| 2026-09-16 | EDGE-G2 | Added edge case: pre-existing branch reused via worktrees.add's existing behavior | analyst |
| 2026-09-16 | EDGE-G3 | Added edge case: `gh pr view` ambiguous/none-found handling in FR-6 | analyst |
| 2026-09-16 | NFR-G1 | Added Security NFR row: no token storage, `gh` manages its own auth | analyst |
| 2026-09-16 | DATA-G1 | Split fields between ticket.toml (durable identity) vs Run record (execution-specific) — decision-log a2 | analyst |
| 2026-09-16 | INT-G1 | Confirmed via `git remote -v`/`.github` that this repo is GitHub-hosted, making `gh` CLI a grounded (not assumed-from-nothing) choice — decision-log a1 | analyst |
| 2026-09-16 | UX-G1 | Specified Run inspector extends the existing agents.js view rather than a new tab, per T-016's own design intent | analyst |
| 2026-09-16 | XCUT-G1 | Added FR-2 explicitly protecting ticketless chats from an unconditional worktree default | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | None found — single ticket owner, internal tooling, no external stakeholder group | — |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| BR-G1 | 🟡 | Draft v0 didn't state what happens when a ticket already has a managed worktree and a second Run is launched against it — `worktrees.add` would raise | Reuse existing managed worktree (BR-2, FR-1 step 1-2) |
| BR-G2 | 🟡 | "Lane hints" is ambiguous between a UI-only suggestion and an actual `ticket_move` call | Explicit BR-5/BR-6 + acceptance criterion asserting no `ticket_move` call from this feature |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| EDGE-G1 | 🟡 | A worktree tracked by a Run record could be deleted outside the console | Treat as not-found, recreate (FR-1, §8) |
| EDGE-G2 | 🟡 | A branch matching the pattern might already exist from a prior manual checkout | `worktrees.add` already handles this (checks out existing branch); no new behavior needed, documented in §8 |
| EDGE-G3 | 🟡 | `gh pr view` could return zero or multiple PRs for a branch | FR-6: none → no-op; ambiguous → surfaced error, never guessed |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| NFR-G1 | 🟡 | No security/credential-handling statement for the new external dependency (`gh` CLI) | Added Security NFR row: no token ever stored in `console/`; `gh` manages its own auth |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| DATA-G1 | 🟡 | Draft v0 hadn't decided ticket.toml vs Run record as the home for the new git fields | Split by lifecycle: ticket-durable (`branch`/`pr_url`/`pr_state`) vs per-execution (`worktree_path`/`worktree_branch`/`worktree_error`) — decision-log a2 |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| INT-G1 | 🟡 | The ticket text assumes "PR open/merge" without naming a data source or hosting platform | Confirmed via `git remote -v`/`.github/workflows` that this repo is GitHub-hosted; `gh` CLI shell-out chosen over a REST/GraphQL client — decision-log a1 |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| UX-G1 | 🟡 | Ambiguity over whether the Run inspector is a new UI surface or an extension of the existing Agents tab | Extend existing `agents.js` run-detail view, per T-016's own "Agents tab becomes that inspector" design intent (T-016-summary.md:26) |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| — | — | None found — no new PII/regulated data introduced; existing audit mechanism (T-017 NFR-5) reused as-is | — |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| XCUT-G1 | 🟡 | Risk that "default worktree isolation" is read as unconditional and breaks every ticketless Assistant chat | FR-2 makes the ticket-scoped-only default explicit and testable |

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements-draft]] · [[T-018-context-snapshot]] · [[T-018-gap-analysis]] · [[T-018-iteration-log]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
