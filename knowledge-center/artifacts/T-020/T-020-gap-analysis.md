---
ticket: "T-020"
artifact: gap-analysis
status: resolved-pending-freeze
created: "2026-10-01"
last_updated: "2026-10-01"
---

# Gap Analysis: T-020

**Sources:** [[T-020-requirements-draft]] · [[T-020-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 1   | 1     |
| Business rules  | 2  | 1  | 0   | 3     |
| Edge cases      | 1  | 3  | 0   | 4     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 0  | 2  | 0   | 2     |
| Integrations    | 0  | 0  | 1   | 1     |
| UX / UI         | 0  | 0  | 1   | 1     |
| Compliance      | 0  | 1  | 0   | 1     |
| Cross-cutting   | 0  | 1  | 0   | 1     |
| **Total**       | **3** | **9** | **3** | **15** |
| **Open after iteration 2** | **0** | **0** | **0** | **0** (G1, G12, G13, G14 accepted with rationale; the rest closed) |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-01 | — | Initial pass from `challenge-requirements` (gaps + redteam) on draft v0 | analyst |
| 2026-10-01 | G2, G3, G5 | 🔴 closed in iteration 1 (FR-19/20/21, FR-3, FR-4); Q1-Q3 answered by delegated default | analyst |
| 2026-10-01 | G4, G6, G7, G8, G9, G10, G11, G15 | 🟡 closed in iteration 1 (BR-9, FR-11, FR-14, FR-7, FR-4, FR-13, switches) | analyst |
| 2026-10-01 | G14 | 🟡 accepted: verb layer cannot verify human vs agent; audit + protocol; Q12 open non-blocking | analyst |
| 2026-10-01 | G1, G12, G13 | 🟢 accepted (Q13 non-blocking; string args normalised; no UI in scope) | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟢 accepted | The human on escalation is reached only by a ticket comment; no push (Telegram) because new notify kinds need a user edit of `console.toml` | Q13 (non-blocking, user-only); design works without |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🔴 closed | No link from a claim to the Run that owns it; "any active Run on the ticket protects the claim" blocks a new owner whose own Run is live | Q1: `claimed_run` on `ticket.toml`, explicit `run=` or auto-link to the sole ACTIVE Run; rewrite FR-19/20/21 |
| G3 | 🔴 closed | BR-1 (terminal immutable) vs a live chat taking later turns after its Run is `done` | Q2: a Run covers its chat until the first terminal state; later turns untracked; state in § 3 and § 8 |
| G4 | 🟡 closed | BR-9 ("hand-started chats never auto-killed") contradicts FR-7/FR-8 hygiene kills that apply to every chat | Narrow BR-9 to stall kill, retry and reconcile; hygiene kills apply to all chats |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G5 | 🔴 closed | Session ring holds 4000 events; a tick every 15 s can miss a `turn.end` that scrolled out | Q3: `BaseSession` keeps `last_turn` + turn counter; `sync_run` reads attributes, not the ring (FR-4) |
| G6 | 🟡 closed | `TurnSession` synthesises `turn.end subtype=process_exit` with `is_error=False` on exit 0 and no result (`agent_session.py:591`) | FR-11: exit 0 without a real result is liveness `empty`, not success and not failure |
| G7 | 🟡 closed | Watchdog thread can die silently; `run-watch` and the thread can act twice on one Run | FR-14: per-Run exception isolation, single-flight tick lock, `last_tick` and error count surfaced by `run-watch` |
| G8 | 🟡 closed | A legitimately silent long tool call could be killed at 1800 s; the CLI's output cadence during tools is unverified | Keep generous default; `stall_kill_secs = 0` means flag only; Open Confirmation in snapshot |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G9 | 🟡 closed | FR-7 caps total stdout per session lifetime: a multi-day interactive chat would be killed for being long, not runaway | Cap per turn (`max_turn_output_bytes`, 64 MiB, reset at `turn.start`) |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G10 | 🟡 closed | "Approval pending for this chat" has no read helper on `Approvals` | Add read-only `REGISTRY.pending_for(chat)`; FR-3 and FR-14 use it |
| G11 | 🟡 closed | `Bash` as mutating evidence makes every run `advanced` (reads use Bash too) | Evidence = `Write/Edit/MultiEdit/NotebookEdit`, console mutating verbs, non-empty worktree `diff --stat`; drop `Bash` (FR-13) |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G12 | 🟢 accepted | Verb args reach handlers as strings over MCP (`force`, `outcome`); T-021 consumes `liveness`, `claim_status`, `review` | Validate and normalise string args in handlers; record field names as the T-021 contract (FR-2, FR-13, FR-20, FR-23) |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G13 | 🟢 accepted | No UI in scope: failures are visible only through ticket comments, `run-show`, `console context`, audit | Accept; UI is Tier 3 |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G14 | 🟡 accepted | The verb layer cannot tell a human from an agent, so `human_decision` and `force` are honour-system plus audit | Accept and state (BR-8, BR-13); Q12 offers the user-side `gated_tools` gate |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G15 | 🟡 closed | No off switches or rollback note for new automatic behaviour | `[runs].watchdog_enabled`, `max_total_retries = 0`, `stall_kill_secs = 0`, `[claims].ttl_secs = 0` (TTL off); additive fields only, so rollback is "stop reading them" |

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements-draft]] · [[T-020-context-snapshot]] · [[T-020-gap-analysis]] · [[T-020-iteration-log]] · [[T-020-decision-log]] · [[T-020-critique-report]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
