---
ticket: "T-017"
artifact: requirements
status: frozen
frozen_date: "2026-09-16"
source: T-017-requirements-draft.md (iteration 2)
---

# Requirements: T-017 — Delivery Console core

> Frozen from [[T-017-requirements-draft]] (iteration 2, `challenge-requirements` pass complete, 0 open blockers). Full rationale, assumptions, edge cases, and NFR detail live in the draft — this file is the canonical, stable reference for `requirements stories` / planning.

## Functional Requirements
1. **FR-1** — Uniform `--json` contract across every `console/kanban.py` subcommand.
2. **FR-2** — Collapse the dual ticket-creation path (`kanban.py cmd_ticket_create` vs `server/kickoff.py create_ticket`) into one.
3. **FR-3** — MCP `resources` capability + change notifications, additive to today's stdio tool-only surface (`console/server/mcp.py`).
4. **FR-4** — MCP Streamable HTTP transport mounted on the existing `serve` command; stdio stays available.
5. **FR-5** — Tracker Backend SPI (shape only: list/show/create/move/set/comment/ready/claim), vault as the sole registered adapter.
6. **FR-6** — `workspace.toml` support in `find_repo_root`, optional and backward compatible with today's sibling-folder resolution.
7. **FR-7** — `ready` verb: unblocked, unclaimed tickets.
8. **FR-8** — `claim` verb: agent identity (`claimed_by`/`claimed_at`), race-safe, audited.
9. **FR-9** — `comment` verb: attributed, timestamped, non-blocking (`comments` tracker kind).
10. **FR-10** — Session stop-hook reminding an agent to update its claimed ticket before exiting.
11. **FR-11** — `console setup cursor|claude|vscode` command: writes MCP client config + `AGENTS.md` snippet.

Full description, actor, trigger, flow, and acceptance criteria per FR: [[T-017-requirements-draft]] §4.

## Non-Functional Requirements
1. `--json` uniformity adds no material CLI latency.
2. `find_repo_root` behaves identically for checkouts without `workspace.toml` (100% backward compatible).
3. Ticket creation still fails honestly (`PowerShellUnavailable`, not a traceback) from every entry point after FR-2's collapse.
4. MCP HTTP transport security: no new auth scheme — same trust boundary as today's unauthenticated local `serve` (explicitly deferred `〈TBD〉`, documented rationale in draft §5, non-blocking).
5. `claim`/`comment`/kickoff-collapse mutations are all recorded in `console/server/audit.py`'s existing audit log.
6. `claim` is race-safe: two concurrent claims by different identities never both succeed.
7. `console setup <editor>` output is self-explanatory for first-time editor wiring.

## Acceptance Criteria
- [ ] Every `kanban.py` subcommand audited; each supports or always emits `--json`; new tests assert valid JSON per subcommand group.
- [ ] `ticket create` (CLI) and `kickoff` (verb) produce identical artifacts from equivalent inputs; `cmd_ticket_create`'s old bare-TOML-only path is no longer reachable as a public action.
- [ ] `initialize` declares `resources` capability; `resources/list`/`resources/read` return ticket-context data; a mutation triggers a change notification to a subscribed session.
- [ ] `serve` answers MCP calls over HTTP with the same tool results as stdio, on the same running process.
- [ ] Backend SPI interface exists, is used by `ready`/`claim`/`comment`/`ticket-move` handlers, has exactly one adapter (vault), and contains zero Jira/Azure/Linear/GitHub Issues code.
- [ ] `find_repo_root` passes existing (unchanged) tests with no `workspace.toml`, and a new split-repo fixture test with one present.
- [ ] `ready` excludes blocked (existing `_IS_BLOCKER` logic) and claimed tickets; identical via CLI/MCP/HTTP.
- [ ] `claim` sets `claimed_by`/`claimed_at`, refuses a conflicting claim with a named error, is race-safe under concurrent calls, and is audited.
- [ ] `comment` appends to a new `comments` tracker kind, attributed + timestamped, never blocks release, readable via `tracker list <id> comments`.
- [ ] Stop-hook test: claim → no update → session end → reminder recorded; claim → update → session end → no reminder; hook never crashes session end.
- [ ] `console setup cursor|claude|vscode` is idempotent, writes to each editor's documented config location, and includes an `AGENTS.md` snippet warning against hand-editing ticket/tracker TOML.

## Out of Scope
- Real Jira/Azure Boards/Linear/GitHub Issues tracker-backend adapters (SPI shape only).
- The 39→12 skill harness-kernel collapse.
- Voice/barge-in/VAD work (T-015's territory).
- Worktree-per-Run, ticket-id-in-branch, PR linkage, lane-hints-from-git, Run-inspector diffstat (all T-018, depends on this ticket).
- Any modification to T-015/T-016 artifacts or `console/server/runs.py` (read-only reference only).
- UI EventSource / WebSocket live-sync beyond MCP resource-change notifications for editor clients. Plan's mermaid diagram shows `Bus → HTTP` for UI EventSource too, but the 5-item scope list does not name it. **User-confirmed 2026-09-16: out of scope for T-017**, matching the plan's literal scope list; MCP resource-change notifications ship here, UI EventSource push is a future follow-up. See [[T-017-decision-log]] a8 and [[T-017-requirements-draft]] §13.

## Assumptions carried forward (see [[T-017-decision-log]] for full rationale)
- A1: kickoff-path collapse inherits the existing PowerShell dependency (documented, not fixed).
- A2: `comment` stored as a new `comments` tracker kind.
- A3: `claimed_by`/`claimed_at` are new, distinct `ticket.toml` fields.
- A4: the new interface is called "Backend SPI" in code/design language, to avoid colliding with `console/server/trackers.py`'s existing questions/bugs/todos CRUD.
- A5: MCP Streamable HTTP targets the already-declared `2025-06-18` protocol version — no version bump.
- A6: `ready` reuses the existing `_IS_BLOCKER` predicate; no new blocking-logic engine.
- A7: `workspace.toml` is optional; absence must reproduce today's behavior exactly.

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
