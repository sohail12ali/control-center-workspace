---
ticket: "T-017"
artifact: components
---

# Components: T-017

Layers below are project-fitted: this is a CLI/MCP/HTTP console, not a data/service/UI web app, so layers are **Data**, **Backend (SPI)**, **Protocol (CLI/MCP/HTTP handlers)**, **Ops (hooks/onboarding)**.

**Produced by:** `analyze-components` (dependency graph below, same pass). **Consumed by:** `breakdown-tasks`.

Note on count: 15 components across 4 layers, slightly above the skill's 5-12 default. Not a scope-reconsideration trigger — the count tracks the ticket's own already-frozen 5 scope items / 11 FRs at their natural grain (one component per FR-sized unit of work); flagged here per protocol rather than silently accepted.

---

## Data layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| ticket.toml schema extension | schema | Add `claimed_by`/`claimed_at` fields, distinct from `owner` | none | ready-claim-hooks | FR-8, A3 | done — `console/server/tickets.py` (`set_claim`), `console/tests/test_tickets.py` |
| `comments` tracker kind | schema | Add `comments` to `trackers.py` `VALID_KINDS`; `{T}-comments.toml` scaffold | none | ready-claim-hooks | FR-9, A2 | done — `console/server/trackers.py`, `console/tests/test_trackers.py` |
| `workspace.toml` schema | schema | New file format: `name`, `vault`, `console`, `projects` | none | workspace-contract | FR-6, A7 | done — new `console/server/workspace_config.py`, `console/tests/test_workspace_config.py` |

## Backend (SPI) layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| Backend SPI interface | interface module (new, e.g. `console/server/backends/base.py`) | Define `list`/`show`/`create`/`move`/`set`/`comment`/`ready`/`claim` as one interface, named distinctly from `trackers.py` (a4) | existing `tickets.py`, `trackers.py`, `vault.py` (wrapped, not rewritten) | tracker-spi | FR-5 | done — new `console/server/backends/{__init__.py,base.py}` (`abc.ABC`), `console/tests/test_backends.py`; stub import wired into `verb_handlers.py` |
| Vault adapter | adapter (implements Backend SPI) | Sole registered implementation; delegates to existing `tickets.py`/`trackers.py`/`vault.py` | Backend SPI interface | tracker-spi | FR-5 | pending |

## Protocol layer (CLI / MCP / HTTP handlers)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| `kanban.py` `--json` audit + fixes | CLI | Audit every subcommand, add/normalize `--json` | none | one-api | FR-1 | done — `console/kanban.py` (`export`/`reset`/`notify who` gained `--json`; the rest of `build_parser()` already had it — see `test_cli_json.py` for the full audit), `console/tests/test_cli_json.py` |
| Ticket-creation path collapse | CLI/verb | Rewrite `cmd_ticket_create` to call `kickoff.py`'s `create_ticket`; remove bare-TOML-only path | existing `kickoff.py`, `tickets.py` | one-api | FR-2, A1 | done — `console/kanban.py`, `console/server/kickoff.py` (`ticket_id`/`priority`/`url` kwargs), audited via `console/server/audit.py`; `console/tests/test_ticket_create_collapse.py` |
| MCP resources capability + notifications | MCP protocol | `resources/list`, `resources/read`, subscribe/notify; extend `initialize` capabilities | existing `mcp.py`, `verb_handlers.ticket_context`; new change-notification plumbing | mcp-first-class | FR-3, A5 | done — `console/server/mcp.py`, new `console/server/bus.py`; wired into `verb_handlers.ticket_move`; `console/tests/test_mcp.py`, `console/tests/test_bus.py` |
| MCP Streamable HTTP transport | MCP protocol | Mount MCP-over-HTTP (POST + GET/SSE) on the existing `serve` process | MCP resources capability (needs the same tool/resource set to mirror over HTTP) | mcp-first-class | FR-4, A5 | pending |
| `find_repo_root` workspace.toml resolution | CLI/core | Try `workspace.toml` upward search first; fall back unchanged to sibling-folder check | `workspace.toml` schema | workspace-contract | FR-6, A7 | pending |
| `ready` verb handler | verb | List unblocked + unclaimed tickets | Vault adapter (Backend SPI), existing `_IS_BLOCKER` | ready-claim-hooks | FR-7, A6 | pending |
| `claim` verb handler | verb | Set `claimed_by`/`claimed_at`, race-safe, audited | Vault adapter (Backend SPI), ticket.toml schema extension, `audit.py` | ready-claim-hooks | FR-8, A3 | pending |
| `comment` verb handler | verb | Append attributed/timestamped comment | Vault adapter (Backend SPI), `comments` tracker kind | ready-claim-hooks | FR-9, A2 | pending |

## Ops layer (hooks / onboarding)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| Session stop-hook | hook | Warn on session end if claimed ticket has no subsequent update | `claim` verb handler (claimed_at), `audit.py` | ready-claim-hooks | FR-10 | pending |
| `console setup <editor>` command | CLI | Write MCP client config (stdio or HTTP) + `AGENTS.md` snippet, idempotent | MCP Streamable HTTP transport (for HTTP-capable editor config) | ready-claim-hooks | FR-11 | pending |

---

## Dependency graph

```
ticket.toml schema ext ───────────┐
                                   ├─▶ claim verb handler ──▶ Session stop-hook
comments tracker kind ─────────┐  │
                                ├──┼─▶ comment verb handler
Backend SPI interface ─▶ Vault adapter ─▶ ready verb handler
                                          │
workspace.toml schema ─▶ find_repo_root resolution   (independent chain)

kanban.py --json audit            (independent, root+leaf)
Ticket-creation path collapse     (independent, root+leaf)

MCP resources capability ─▶ MCP Streamable HTTP transport ─▶ console setup <editor>
```

---

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data | 3 | 0 | 0 | 3 |
| Backend (SPI) | 2 | 1 | 0 | 1 |
| Protocol | 8 | 5 | 0 | 3 |
| Ops | 2 | 2 | 0 | 0 |
| **Total** | **15** | **8** | **0** | **7** |

Phase 1 (this row's "done" entries) is complete; the remaining "pending" rows
(Vault adapter, MCP Streamable HTTP transport, `find_repo_root` resolution,
`ready`/`claim`/`comment` verb handlers, Session stop-hook, `console setup`)
are Phases 2–4, not yet started.

## Links
- [[T-017-summary]] · [[T-017-requirements]] · [[T-017-plan]] · [[T-017-components]] · [[T-017-task-breakdown]] · [[T-017-implementation-plan]]
