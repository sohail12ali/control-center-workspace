---
ticket: "T-017"
artifact: implementation-plan
---

# Implementation plan: T-017

Master synthesis of frozen requirements ([[T-017-requirements]]), plan slices ([[T-017-plan]]), components ([[T-017-components]]), and tasks ([[T-017-task-breakdown]]). Effort total **126.5 h** dev matches [[T-017-task-breakdown]]'s Effort summary; see [[T-017-effort-estimate]] for the upfront Dev/QC/reserve envelope (140h dev most-likely, 235.2h Final/Complete including QC + reserve). Total revised from an initial 124.5h by `challenge-plan` CR-1 (see [[T-017-critique-report]]) — added audit-log wiring tasks (1a-7, 3a-12) to fully satisfy NFR-5's "claim/comment/kickoff-collapse mutations are all recorded" requirement.

## Ticket summary

Make the Delivery Console one product regardless of surface (CLI/MCP/HTTP): a uniform `--json` CLI contract with one ticket-creation path, MCP `resources` + change notifications + Streamable HTTP transport on `serve`, a Backend SPI (ticket-storage abstraction, vault-only adapter, no real Jira/Azure/Linear/GitHub code), `workspace.toml` as an optional, backward-compatible alternative to the sibling-folder repo-root requirement, and `ready`/`claim`/`comment` verbs plus a session stop-hook and `console setup <editor>`. T-018 (worktree-per-Run, branch/PR linkage) depends on this ticket's `claim`/`ready` contracts and is explicitly out of scope here. T-015 (voice) and T-016 (Run object) are read-only context, not modified.

## Phase 1 — Foundations (55.5 h, parallel — no intra-phase dependencies)

### Slice 1a — one-api (9.5 h)
Files: `console/kanban.py` (`build_parser`, `cmd_ticket_create`), `console/server/kickoff.py`, `console/server/audit.py`, `console/tests/`.
Tasks: 1a-1 → 1a-2 → 1a-3 (JSON audit); 1a-4 → 1a-5 → 1a-6 → 1a-7 (ticket-creation collapse + audit wiring). Requirements: FR-1, FR-2, NFR-5.

### Slice 1b — tracker-spi interface (8 h)
Files: new `console/server/backends/base.py` (or equivalent), `console/server/verb_handlers.py` (stub wiring), `console/tests/`.
Tasks: 1b-1 → 1b-2, 1b-3, 1b-4. Requirements: FR-5.

### Slice 1c — workspace-contract schema (5 h)
Files: new `console/server/workspace_config.py` (or similar — schema/parser module), fixtures under `console/tests/fixtures/`.
Tasks: 1c-1 → 1c-2, 1c-3. Requirements: FR-6.

### Slice 1d — ready-claim-hooks data schema (8 h)
Files: `knowledge-center/artifacts/_template/ticket.toml`, `console/server/tickets.py`, `console/server/trackers.py`, `console/tests/`.
Tasks: 1d-1 → 1d-2, 1d-3 (ticket.toml fields); 1d-4 → 1d-5, 1d-6 (comments kind). Requirements: FR-8, FR-9.

### Slice 1e — mcp-first-class resources (17 h)
Files: `console/server/mcp.py`, new change-notification bus module (name TBD at build time, e.g. `console/server/bus.py`), `console/tests/`.
Tasks: 1e-1 → 1e-2 → 1e-3 → 1e-4 → 1e-5 → 1e-6. Requirements: FR-3. **Highest-uncertainty task: 1e-4** (no prior change-bus mechanism exists — see Risks).

## Phase 2 — Adapters & transport (41 h, depends on Phase 1)

### Slice 2a — mcp-first-class HTTP transport (16 h)
Files: `console/kanban.py` (`cmd_serve`), `console/server/httpd.py`, `console/server/mcp.py`, `console/tests/`.
Tasks: 2a-1 → 2a-2, 2a-3 → 2a-4, 2a-5. Requirements: FR-4. Depends on: 1e-1..1e-3.

### Slice 2b — tracker-spi vault adapter (17 h)
Files: new `console/server/backends/vault_backend.py` (or similar), `console/server/verb_handlers.py` (`ticket-move`), `console/tests/`.
Tasks: 2b-1 → 2b-2 → 2b-3, 2b-4 → 2b-5, 2b-6, 2b-7. Requirements: FR-5. Depends on: 1b-1..1b-4, 1d-1, 1d-4.

### Slice 2c — workspace-contract resolution (8 h)
Files: `console/server/paths.py` (`find_repo_root`), `console/tests/`.
Tasks: 2c-1 → 2c-2 → 2c-3, 2c-4. Requirements: FR-6. Depends on: 1c-1.

## Phase 3 — Verbs (18 h, depends on Phase 1 + Phase 2)

### Slice 3a — ready-claim-hooks verb handlers (18 h)
Files: `console/config/verbs.toml`, `console/server/verb_handlers.py`, `console/server/audit.py`, `console/tests/`.
Tasks: 3a-1 → 3a-2, 3a-3 (ready); 3a-4 → 3a-5 → 3a-6, 3a-7 → 3a-8 (claim); 3a-9 → 3a-10, 3a-11, 3a-12 (comment + audit wiring). Requirements: FR-7, FR-8, FR-9, NFR-5. Depends on: 2b-5 (vault adapter), 1d-1 (ticket.toml fields), 1d-4 (comments kind).

## Phase 4 — Ops (12 h, depends on Phase 2 + Phase 3) — done, 4h actual

### Slice 4a — ready-claim-hooks stop-hook + editor setup (12 h)
Files: session-hook config (`.claude/`/equivalent), `console/kanban.py` (new `setup` subcommand), `console/tests/`.
Tasks: 4a-1 → 4a-2 → 4a-3 (stop-hook); 4a-4, 4a-5, 4a-6 → 4a-7 → 4a-8 (editor setup). Requirements: FR-10, FR-11. Depends on: 3a-7 (claim/audit), 2a-1 (HTTP transport, for HTTP-capable editor configs).

## Build order

```
Phase 1 (parallel):
  1a-1→1a-2→1a-3   ∥   1a-4→1a-5→1a-6→1a-7   ∥   1b-1→(1b-2 ∥ 1b-3 ∥ 1b-4)
  ∥ 1c-1→(1c-2 ∥ 1c-3)   ∥   1d-1→(1d-2 ∥ 1d-3)   ∥   1d-4→(1d-5 ∥ 1d-6)
  ∥ 1e-1→1e-2→1e-3→1e-4→1e-5→1e-6

Phase 2 (after relevant Phase 1 slices):
  (needs 1e-1..1e-3) 2a-1→(2a-2 ∥ 2a-3)→(2a-4 ∥ 2a-5)
  (needs 1b-*, 1d-1, 1d-4) 2b-1→2b-2→(2b-3 ∥ 2b-4)→2b-5→(2b-6 ∥ 2b-7)
  (needs 1c-1) 2c-1→2c-2→(2c-3 ∥ 2c-4)

Phase 3 (after 2b-5, 1d-1, 1d-4):
  3a-1→(3a-2 ∥ 3a-3)
  3a-4→3a-5→(3a-6 ∥ 3a-7)→3a-8
  3a-9→(3a-10 ∥ 3a-11 ∥ 3a-12)

Phase 4 (after 3a-7, 2a-1):
  4a-1→4a-2→4a-3
  (4a-4 ∥ 4a-5 ∥ 4a-6)→4a-7→4a-8
```

Critical path (recomputed as the true task-dependency-weighted longest chain, not a whole-slice-hour sum — corrects `challenge-plan` CR-3, see [[T-017-critique-report]]): two chains are near-tied, both ≈32h of task-hours if built serially with no parallelism across chains:

- **Backend SPI chain:** 1b-1→(1b-2‖1b-3‖1b-4) [5h] → 2b-1→2b-2→(2b-3‖2b-4)→2b-5→(2b-6‖2b-7) [15h] → 3a-4→3a-5→(3a-6‖3a-7)→3a-8 [8h] → 4a-1→4a-2→4a-3 [4h] = **32h**
- **MCP chain:** 1e-1→1e-2→1e-3→1e-4→1e-5→1e-6 [17h] → 2a-1→(2a-2‖2a-3)→(2a-4‖2a-5) [10h] → 4a-4→4a-7→4a-8 [5h] = **32h**

Both chains are independent of each other and of the one-api/workspace-contract chains, so they can build in parallel; neither is a single bottleneck on its own, but a slip in **either** chain (most likely 1e-4, the greenfield change-bus task — see Risks) delays the ticket equally. Recommend tracking both via `estimate(mode=forecast)` once tasks in either chain have actuals, rather than treating only the Backend-SPI chain as "the" critical path.

## Acceptance criterion coverage

Every FR/AC in [[T-017-requirements]] is covered by ≥1 task above:

| AC (requirements.md) | Covered by tasks |
|---|---|
| FR-1 `--json` audit + tests | 1a-1, 1a-2, 1a-3 |
| FR-2 one ticket-creation path | 1a-4, 1a-5, 1a-6, 1a-7 (NFR-5 audit) |
| FR-3 MCP resources + notifications | 1e-1..1e-6 |
| FR-4 MCP Streamable HTTP transport | 2a-1..2a-5 |
| FR-5 Backend SPI (shape only, vault-only) | 1b-1..1b-4, 2b-1..2b-7 |
| FR-6 `workspace.toml` resolution | 1c-1..1c-3, 2c-1..2c-4 |
| FR-7 `ready` verb | 3a-1, 3a-2, 3a-3 |
| FR-8 `claim` verb (race-safe, audited) | 1d-1, 1d-2, 1d-3, 3a-4..3a-8 |
| FR-9 `comment` verb | 1d-4, 1d-5, 1d-6, 3a-9, 3a-10, 3a-11, 3a-12 (NFR-5 audit) |
| FR-10 session stop-hook | 4a-1, 4a-2, 4a-3 |
| FR-11 `console setup <editor>` | 4a-4..4a-8 |

## Links
- [[T-017-summary]] · [[T-017-requirements]] · [[T-017-plan]] · [[T-017-components]] · [[T-017-task-breakdown]] · [[T-017-implementation-plan]] · [[T-017-effort-estimate]]
