---
ticket: "T-004"
artifact: gap-analysis
status: open
created: "2026-09-06"
last_updated: "2026-09-06"
---

# Gap Analysis: T-004

**Sources:** [[T-004-requirements-draft]] · [[T-004-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 0  | 1   | 1     |
| Business rules  | 1  | 2  | 0   | 3     |
| Edge cases      | 0  | 3  | 1   | 4     |
| NFRs            | 1  | 1  | 0   | 2     |
| Data / entities | 1  | 0  | 1   | 2     |
| Integrations    | 0  | 1  | 1   | 2     |
| UX / UI         | 0  | 1  | 0   | 1     |
| Compliance      | 0  | 0  | 1   | 1     |
| Cross-cutting   | 1  | 0  | 0   | 1     |
| **Total**       | **4** | **8** | **4** | **17** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-09-06 | — | Initial pass from `challenge-requirements` (gaps) | — |
| 2026-09-06 | all rows below | Populated by `challenge-requirements T-004` — none resolved yet, all carried into requirements-draft.md §13 as ⚠ findings; targeted for close in the next `requirements enrich`/`iterate` pass, none require a stakeholder decision (zero blocking questions raised) | analyst |
| 2026-09-06 | STAKE-1 | Added "Future implementer" stakeholder row to §11 naming the T-005/T-006 forward-compat concern | analyst |
| 2026-09-06 | BR-GAP-1 | Added structural pytest AC to FR-2 asserting `.claude/agents/*.md` count stays 7 | analyst |
| 2026-09-06 | BR-GAP-2 | Added fake-`send()`-returns-fast-command-text regression AC to FR-2 for BR-1 | analyst |
| 2026-09-06 | BR-GAP-3 | Named the validation rule (reuse `agent_manager.create`'s installed/enabled check) + added rejected-invalid-backend AC to FR-7 | analyst |
| 2026-09-06 | EDGE-GAP-1 | Chose truncate-with-stated-marker (FR-4's existing pattern); FR-3/BR-7 now enforce the ≤4,000-char cap at read time with an audit log line and a new AC | analyst |
| 2026-09-06 | EDGE-GAP-2 | Reworded FR-6 flow + the Edge Cases §8 bullet to state PS-unavailable is routine on macOS/Linux, rare on Windows (plan.md:74); no new AC needed | analyst |
| 2026-09-06 | EDGE-GAP-3 | Added a fourth `error` result variant + AC to FR-1, and a matching Edge Cases §8 bullet | analyst |
| 2026-09-06 | EDGE-GAP-4 | FR-7 now states explicitly that a backend change only affects the next brand-new session, never a live/reused one; added AC + Edge Cases bullet | analyst |
| 2026-09-06 | NFR-GAP-1 | FR-1 now enumerates all 5 `/api/assistant/stream` event names with field shapes, sourced from plan.md:145 | analyst |
| 2026-09-06 | NFR-GAP-2 | Added a "Concurrency" NFR row: single-writer-per-process by construction, no locking library needed | analyst |
| 2026-09-06 | DATA-GAP-1 | Added a Data Requirements entity row for the 5 SSE event types (same root cause/edit as NFR-GAP-1) | analyst |
| 2026-09-06 | DATA-GAP-2 | Added an `assistant.toml` forward-compat note (unknown keys ignored, additive reads) citing `notify.py`'s own pattern | analyst |
| 2026-09-06 | INT-GAP-1 | Added the missing "PS 5.1-safe template rendering" row to §9 Interactions | analyst |
| 2026-09-06 | INT-GAP-2 | Added a "Verb→tool generic exposure" row to §9 confirming intended scope, plus a new BR-9 stating the same rule | analyst |
| 2026-09-06 | UX-GAP-1 | Added a minimal UI-contract flow step to FR-8 (single input+send box; placement/keybinding left to builder) rather than a full out-of-scope declaration, since `assistant.js`'s palette is plan-scoped (plan.md:145) | analyst |
| 2026-09-06 | COMP-GAP-1 | Added a secret-pattern decline guard + AC to FR-9; updated §5's Compliance NFR row; recorded as a design decision | analyst |
| 2026-09-06 | CROSS-GAP-1 | Named the double-speech mechanism (`is_assistant` flag on `session.started`/`meta`, checked by `agents.js`'s `autoRead`); recorded as a design decision in [[T-004-decision-log]] | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| STAKE-1 | 🟢 | No row for the future T-005/T-006 implementer, whose concern is that `native_bridge.py`'s always-unavailable stub shape and the reply-watcher/`attention`-event contract (FR-8, FR-11) stay extensible without rework once T-005 lands — plan.md:84-85 makes both tickets depend on T-004. | Add a stakeholder row (same person, forward-compat hat) naming this concern explicitly. |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| BR-GAP-1 | 🔴 | BR-3 ("zero new agents") is invoked by FR-2 but none of FR-2's ACs test it — no `.claude/agents/` file-count assertion anywhere, unlike BR-4 which FR-9 tests directly via a diff grep. | Add an explicit AC (e.g. structural check that `.claude/agents/` count is unchanged at 7 post-diff). |
| BR-GAP-2 | 🟡 | BR-1's only AC is subjective code review ("no code path inspects a model reply"); no regression test traps a future violation (e.g. a fake `send()` returning fast-command-shaped text). | Add a fake-manager pytest asserting the dispatcher doesn't re-fire on a reply that happens to match a table pattern. |
| BR-GAP-3 | 🟡 | FR-7's "validates" step (settings POST) names no validation rule — does it reject an unknown/uninstalled `backend` value? | Name the rule (reuse `agent_manager.create`'s installed/enabled check) and add a rejected-invalid-backend AC. |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| EDGE-GAP-1 | 🟡 | Windows argv-cap-exceeded behavior is stated as an undecided OR ("fail loudly or truncate"); `assistant.md`'s own ≤4,000-char cap is never enforced at read time. | Pick one behavior (candidate: reuse FR-4's "truncate + stated marker" pattern) and add a concrete AC. |
| EDGE-GAP-2 | 🟡 | "PowerShell unavailable" is framed as an edge case, but on macOS/Linux (2 of 3 target OSes, no pwsh listed in Build prerequisites) it may be the routine path for the `kickoff` fast command. | Reword to state expected frequency per OS; no new AC needed (both branches already tested). |
| EDGE-GAP-3 | 🟡 | No `error` result variant defined for `say` when `agent_manager.create`/`send` itself fails (only `handled/sent/queued` documented). | Add an edge case + AC defining an `error` result shape and its spoken text. |
| EDGE-GAP-4 | 🟢 | Backend changed via Settings/`use {backend}` while the reused live Assistant chat is still active — unspecified whether the change applies only to the next NEW session (implied, not stated). | State explicitly in FR-7 that only new-session creation reads `assistant.toml`'s default. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| NFR-GAP-1 | 🔴 | `/api/assistant/stream`'s event vocabulary (`attention`, `reply`, `speaking.*`) is undocumented; none of these three event types has any publish call site anywhere in the repo today (confirmed via grep of `agent_events.py`/`agent_session.py`/`agent_api_session.py`/`agent_normalize.py`/`agent_approvals.py`) — FR-1 has no schema for this route at all. | Pull the plan's own named event list (plan.md:145) into FR-1 + add a Data Requirements entity naming each event's fields. |
| NFR-GAP-2 | 🟡 | No NFR covers concurrent-write safety for `console/.cache/assistant/*` plain files (`session.json`, `memory.md`, last-reply) — unlike the repo's proven TOML writer; at least two write paths can race on `memory.md`/last-reply. | Add an NFR row (or reuse `tomlio`'s atomic-write pattern) for these files. |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| DATA-GAP-1 | 🔴 | Same root cause as NFR-GAP-1: no Data Requirements entity for the new SSE event schema (`attention`/`reply`/`speaking.*`) consumed by `assistant.js` and (later) T-005's Rust tray state machine. | Add an entity row per event type with its field list, sourced from plan.md:145/175. |
| DATA-GAP-2 | 🟢 | `assistant.toml`'s forward-compatibility is unstated, even though T-005/T-006 are both expected to add keys to the same file. | Add "unknown keys ignored, new keys additive" as a one-line data note. |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| INT-GAP-1 | 🟢 | §9 Interactions (7 rows) undercounts context-snapshot.md §2's "Similar / adjacent features" table (8 rows) — missing "PS 5.1-safe template rendering (`New-FromTemplate.ps1`)" as its own row. | Add the missing row, or explicitly fold it into the "Kickoff skill" row with a note. |
| INT-GAP-2 | 🟡 | `agent_tools.py`'s generic verb→tool exposure ("every row in `verbs.toml` becomes a tool," `agent_tools.py:9-11,321`) means the 3 new verbs become callable by **every** existing chat + the MCP tool list, not only the Assistant — §9 never names or cross-checks this ripple. | Add an Interactions row naming this effect; confirm intended (persona doc's own "tool preferences" language implies yes, plan.md:151). |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| UX-GAP-1 | 🟡 | No FR states the "Ask assistant" palette box's own UI contract (visibility trigger, keybinding/placement, reply render location) despite `assistant.js` being new and in-scope, and the plan's manual e2e AC presuming it works. | Add a minimal FR (or extend FR-8) describing the palette's trigger/visibility contract. |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| COMP-GAP-1 | 🟢 | No guard/accepted-risk note for `remember`-ing a secret (API key, password) into a plaintext `memory.md` that is re-injected into every future session's prompt (FR-4). Low severity — single-user local tool. | Add an explicit accepted-risk line, or a basic secret-pattern check, decided at enrich. |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| CROSS-GAP-1 | 🔴 | FR-8's double-speech guard mechanism is still unnamed after this pass (the draft itself deferred naming it to `challenge-requirements`; analysis.md:263-269 flagged the same gap at GROUND). | `requirements enrich`/planner names a concrete mechanism (e.g. a `meta.owner="assistant"` flag checked by `agents.js`'s autoRead handler) and rewrites FR-8's AC around it. |

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements-draft]] · [[T-004-context-snapshot]] · [[T-004-gap-analysis]] · [[T-004-iteration-log]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
