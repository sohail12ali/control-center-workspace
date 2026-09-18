---
ticket: "CC-T002"
artifact: plan
---

# Plan: CC-T002

## Approach

Phase 1 of the v3 roadmap — give the agent a **program body**. The thesis: everything the
console can compute, the console should compute, so the model spends tokens on judgement
instead of arithmetic.

Three layers, built bottom-up:

1. **Verbs** — named, deterministic, no-LLM jobs, declared in config and dispatched by id.
   This is the vocabulary everything above speaks.
2. **Isolation and scheduling** — worktrees so parallel runs cannot corrupt each other, and
   a job queue so a verb or agent run is a tracked, resumable thing rather than a fire-and-forget
   subprocess.
3. **MCP server** — the verbs exposed over one protocol, so Claude Code, Cursor, and the
   future OpenRouter backend all get identical native tools from one implementation.

`context` is the first and most valuable verb: `trace-context` currently has the model read
roughly eight artifact files at the start of every turn. One call returning one digest
replaces that, and it is the single largest per-turn saving available.

Constraint carried forward: **zero new runtime dependencies.** The MCP server is JSON-RPC
over stdio, which is stdlib.

## Tasks

### [x] CC-T002-01 — Verb registry (4 h)

- [x] `console/config/verbs.toml` — id, label, hint, handler, and the gates a verb declares
      for itself (`needs_ticket`, `needs_confirm`, `kinds`, `lanes`)
- [x] `console/server/verbs.py` — registry, argument validation, dispatch to a handler
      resolved by dotted path; unknown verb and failed gate are errors, not warnings
- [x] `kanban verb list` and `kanban verb run {id} [--ticket T] [--confirm] [--json]`
- **Done-criteria:** a verb declared in config and nowhere else is listable and runnable;
  a `needs_confirm` verb refuses without `--confirm`; an unknown handler path fails at
  registry load, not at run time.
- **Basis:** dossier §2 items #2 and #7; ports the fork's `verbs.toml` idea generically
- **Depends on:** —

### [x] CC-T002-02 — `context` verb (3 h)

- [x] One call returning a ticket's full state as one compact structure: ticket fields,
      lane, artifact inventory with per-artifact headings, open trackers, blockers,
      unchecked plan tasks, recent progress entries, and telemetry to date
- [x] `kanban context {T} [--json|--md]`; markdown form is what an agent pastes into context
- [x] Budget-aware: caps per section, with an explicit note when something was truncated
      rather than silent elision
- **Done-criteria:** for CC-T001, one call returns lane, all 7 artifacts, 4 open todos,
  0 blockers, and 6/6 completed tasks — in under ~2 KB of markdown.
- **Basis:** dossier §2 item #2, lever 2 — the largest single-turn saving in the pipeline
- **Depends on:** CC-T002-01

### [x] CC-T002-03 — Worktree isolation (3 h)

- [x] `console/server/worktrees.py` — create/list/remove a git worktree per run under a
      configured root; branch naming from config, never hardcoded
- [x] Refuse to create one for a dirty target, and refuse to remove one with uncommitted
      work unless forced
- [x] `kanban worktree list|add|remove`
- **Done-criteria:** two worktrees for the same ticket cannot collide; removing one with
  uncommitted changes requires `--force` and says what would be lost.
- **Basis:** dossier §2 item #4, step 1 — the prerequisite for everything remote
- **Depends on:** —

### [x] CC-T002-04 — Job queue (4 h)

- [x] Durable job records (queued → running → done/error/cancelled) with a concurrency cap
- [x] Runs verbs today; the same queue is what agent runs move onto in Phase 3
- [x] `kanban job list|show|cancel`; survives a server restart by reading records back
- **Done-criteria:** submitting more jobs than the cap leaves the excess queued; a restart
  re-reads records and marks orphaned `running` jobs as interrupted rather than lying.
- **Basis:** dossier §2 item #4, step 2
- **Depends on:** CC-T002-01

### [x] CC-T002-05 — MCP server (5 h)

- [x] `console/mcp_server.py` — JSON-RPC 2.0 over stdio, stdlib only: `initialize`,
      `tools/list`, `tools/call`
- [x] Tools generated from the verb registry plus `context`, so adding a verb adds a tool
      with no MCP code change
- [x] `.mcp.json` wiring documented for Claude Code and Cursor
- **Done-criteria:** a handshake plus `tools/list` returns every enabled verb with a JSON
  schema; `tools/call` on `context` returns the same digest as the CLI.
- **Basis:** dossier §3 addition #2 — the real form of roadmap item #7
- **Depends on:** CC-T002-01, CC-T002-02

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T002-01 — Verb registry | 4 h | config + dispatch + CLI + gates |
| CC-T002-02 — `context` verb | 3 h | aggregates 5 existing readers |
| CC-T002-03 — Worktrees | 3 h | git plumbing + safety rules |
| CC-T002-04 — Job queue | 4 h | durable records + concurrency + restart |
| CC-T002-05 — MCP server | 5 h | protocol + schema generation + wiring |
| **Total** | **19 h** | flat-mode estimate |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
| --- | --- |
| Deterministic work is declarable without code | CC-T002-01 |
| A turn can ground itself in one call | CC-T002-02 |
| Parallel runs cannot corrupt each other | CC-T002-03 |
| Work is tracked and survives a restart | CC-T002-04 |
| Every MCP client gets the same tools | CC-T002-05 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Verb handlers become a plugin system nobody asked for | Med | Med | Handlers are dotted paths into existing console modules; no new lifecycle, no new base class | Builder |
| `context` grows into a second renderer that drifts from the board | Med | High | It composes the existing readers (tickets, trackers, telemetry) rather than reimplementing them; tests assert agreement | Builder |
| Worktree code assumes a branch model | High | Med | Branch pattern comes from config with a documented default; never hardcode a branch name | Builder |
| MCP protocol version drift | Med | Low | Pin the protocol version reported in `initialize`; the surface used is the stable core three methods | Builder |
| Job queue in-process only, lost on restart | Med | Med | Records on disk are the source of truth; an orphaned `running` job is reported as interrupted, never as done | Builder |

## Dependencies

- Blocks: Phase 2 (OpenRouter backend consumes the MCP tools), Phase 3 (remote uses the queue and worktrees)
- Blocked by: CC-T001 (closed)

## Links
- [[CC-T002-summary]] · [[CC-T002-analysis]] · [[CC-T002-requirements]] · [[CC-T002-decision-log]] · [[CC-T002-plan]] · [[CC-T002-progress]] · [[CC-T002-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T001-summary]]
