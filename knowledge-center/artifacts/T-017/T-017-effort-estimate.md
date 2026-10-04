---
ticket: "T-017"
artifact: effort-estimate
basis: "components"
confidence: "Medium"
---

# Effort estimate: T-017

**Produced by:** `estimate T-017 --mode upfront`. **Sources:** [[T-017-requirements]] · [[T-017-components]]

| Field | Value |
|-------|-------|
| Basis | components |
| Units estimated | 15 |
| Confidence | Medium |

---

## Executive summary

| Metric | Most likely | Lower | Upper | Days @ 8h |
|--------|------------:|------:|------:|----------:|
| Development | 140h | 98h | 176h | 17.5 |
| QC | 73.8h | 56.6h | 73.8h | 9.2 |
| Risk reserve | 21.4h | — | — | 2.7 |
| **Final / Complete** | **235.2h** | **154.6h** | **249.8h** | **29.4** |

> Calendar days are indicative only — no capacity/parallelism model applied.

---

## Assumptions
1. One engineer-equivalent (agent build session), no parallel pairing across components within a phase.
2. No external tracker integration ships in this ticket (SPI shape only, per FR-5/BR-4) — no "external integration" QC ratio applied.
3. High-risk cycle profile selected because two units carry an "unknown/spike" or "concurrency" adder (MCP resources' new change-bus plumbing; `claim`'s race-safety requirement).

---

## Units

| Unit ID | Source | Layer | Size | M (h) | Adders | Lower (h) | Upper (h) | Notes |
|---------|--------|-------|------|------:|--------|----------:|----------:|-------|
| U1 | ticket.toml schema extension | Data | S | 4 | none | 2.8 | 5.4 | claimed_by/claimed_at fields + mutator |
| U2 | `comments` tracker kind | Data | S | 4 | none | 2.8 | 5.4 | VALID_KINDS + scaffold, mirrors existing kinds |
| U3 | `workspace.toml` schema | Data | S | 4 | +30% new persisted structure | 3.6 | 7.0 | new file format |
| U4 | Backend SPI interface | Service | M | 8 | none | 5.6 | 10.0 | interface definition, 8 methods |
| U5 | Vault adapter | Service | L | 16 | +20% existing large component wrap | 13.4 | 24.0 | wraps tickets.py/trackers.py/vault.py |
| U6 | `kanban.py --json` audit + fixes | Service | M | 8 | none | 5.6 | 10.0 | audit ~30 subcommands + tests |
| U7 | Ticket-creation path collapse | Service | M | 8 | +20% existing rewrite | 6.7 | 12.0 | rewires cmd_ticket_create onto kickoff.py |
| U8 | MCP resources capability + notifications | Service | L | 16 | +50% unknown/spike (new change-bus) | 16.8 | 30.0 | resources/list, read, subscribe, notify |
| U9 | MCP Streamable HTTP transport | Service | L | 16 | +25% concurrency (multi-client) | 14.0 | 25.0 | mounts on existing `serve` |
| U10 | `find_repo_root` workspace.toml resolution | Service | M | 8 | none | 5.6 | 10.0 | new first branch, fallback unchanged |
| U11 | `ready` verb handler | Service | S | 4 | none | 2.8 | 5.0 | reuses `_IS_BLOCKER` |
| U12 | `claim` verb handler | Service | M | 8 | +25% concurrency/race-safety | 7.0 | 12.5 | atomic write, audit, idempotent re-claim |
| U13 | `comment` verb handler | Service | S | 4 | none | 2.8 | 5.0 | extends VALID_KINDS usage |
| U14 | Session stop-hook | Service | S | 4 | none | 2.8 | 5.0 | best-effort reminder, never crashes session end |
| U15 | `console setup <editor>` command | Service | M | 8 | none | 5.6 | 10.0 | 3 editors, idempotent, AGENTS.md snippet |

---

## By layer

| Layer | Units | Σ Lower | Σ M | Σ Upper | % of total |
|-------|------:|--------:|----:|--------:|-----------:|
| Data | 3 | 9.2 | 13.2 | 17.8 | 9% |
| Service | 12 | 88.8 | 126.8 | 158.5 | 91% |
| UI | 0 | 0 | 0 | 0 | 0% |
| Test | 0 (folded into per-unit AC, no separate test-layer units) | 0 | 0 | 0 | 0% |
| **Total** | 15 | 98.0 | 140.0 | 176.3 | 100% |

---

## QC estimation

| Dev layer | Dev M | QC ratio | Base QC (h) |
|-----------|------:|---------:|------------:|
| Data | 13.2 | 20% | 2.64 |
| Service | 126.8 | 25% | 31.70 |
| UI | 0 | 35% | 0 |
| Integration | 0 | 40% | 0 |
| **Base QC (Σ)** | | | **34.34** |

| Factor | Value |
|--------|-------|
| Cycle profile | High (concurrency adder on U12, unknown/spike adder on U8) |
| Cycle factor | x1.8 |
| UAT support | 12h (Dev Σ M = 140h, >80h band) |
| **QC total** | **73.8h** [56.6-73.8] |

---

## Final / Complete time

| Component | Most likely | Lower | Upper |
|-----------|------------:|------:|------:|
| Development | 140.0 | 98.0 | 176.3 |
| QC total | 73.8 | 56.6 | 73.8 |
| Risk reserve | 21.4 | — | — |
| **Final / Complete** | **235.2** | **154.6** | **249.8** |

---

## Complexity adders applied

| Unit | Adder | +% | Why |
|------|-------|---:|-----|
| U3 workspace.toml schema | New schema/persisted structure | +30% | new file format, no prior parser exists |
| U5 Vault adapter | Existing large component rewrite | +20% | wraps tickets.py/trackers.py/vault.py combined >100 LOC of call sites |
| U7 Ticket-creation path collapse | Existing large component rewrite | +20% | rewires kickoff.py + kanban.py cmd_ticket_create |
| U8 MCP resources + notifications | Unknown/spike required | +50% | change-notification "Bus" (plan's mermaid diagram) does not exist yet — greenfield design |
| U9 MCP HTTP transport | Concurrency/shared-state | +25% | multiple editor clients share one running process |
| U12 claim verb handler | Concurrency/shared-state | +25% | race-safety requirement (FR-8 AC), atomic write under concurrent calls |

---

## Risks widening the upper bound

| ID | Source | Effect |
|----|--------|--------|
| R1 | analysis.md F5 — no change-bus mechanism exists for MCP resource notifications | U8 could exceed L(16h) bucket if subscribe/notify plumbing needs its own persistence layer; upper bound already carries +50% |
| R2 | requirements FR-8 AC — concurrent-claim race safety | U12 test-writing (concurrent claim simulation) could run long if today's TOML write path isn't already atomic; verify before committing to lower bound |
| R3 | decision-log a1 — PowerShell dependency inherited by U7 | no effort risk (documented constraint, not new code), but flagged since it affects test-environment availability for U7's regression test |

---

## Recommendations
1. Re-run `estimate(mode=forecast)` once `breakdown-tasks` produces task-level actuals — components-basis confidence (Medium) should tighten once ≥5 tasks have real effort logged.
2. Confirm whether `tickets.py`/`trackers.py`'s existing TOML writes are already atomic (file-replace pattern) before finalizing U12's lower bound — if not, add an explicit sub-task for atomic-write plumbing rather than assuming it inside U12's estimate.
3. Treat U8 (MCP resources/change-bus) as the ticket's highest-uncertainty unit; consider a short spike/timebox before committing to its upper bound if `breakdown-tasks` shows it growing past 30h.

---

## Revision log

| Date | Basis | Dev Σ M | QC | Final/Complete | Range | Notes |
|------|-------|--------:|---:|----------------:|-------|-------|
| 2026-09-16 | components | 140.0h | 73.8h | 235.2h | 154.6-249.8h | Initial upfront sizing, 15 components |

## Links
- [[T-017-summary]] · [[T-017-requirements]] · [[T-017-components]] · [[T-017-effort-estimate]] · [[T-017-effort-forecast]]
