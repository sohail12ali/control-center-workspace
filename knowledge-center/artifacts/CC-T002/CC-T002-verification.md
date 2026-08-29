---
ticket: "CC-T002"
artifact: verification
---

# Verification: CC-T002

**Verified:** 2026-08-29 · **Result:** PASS. No gaps.

## Evidence

| Command | Result |
| --- | --- |
| `python -m pytest` | **278 passed** |
| `python console/kanban.py harness lint` | `39 skills, 7 agents \| 0 error(s), 0 warning(s)` — exit 0 |
| `python console/kanban.py verb list --ticket CC-T001` | 8 verbs, availability and reason per row |
| `python console/kanban.py context CC-T001` | full digest, **1,676 bytes** |
| `python console/kanban.py job submit blockers --ticket CC-T002` | `state: done`, result inline |
| `python console/kanban.py worktree list` | main worktree, branch `development` |
| `mcp_server.py` via subprocess: `initialize` + `tools/list` | 8 tools, clean stdout |
| `mcp_server.py` via subprocess: `tools/call context` | markdown digest for CC-T002 |

Test counts added by this ticket: verbs 24 · context 18 · worktrees 22 · jobs 23 · mcp 25
(112 new; 278 total).

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Deterministic work is declarable without code | **Met** | 8 verbs exist only as `verbs.toml` rows; a test adds a 9th at runtime and it appears as an MCP tool with no code change |
| A turn can ground itself in one call | **Met** | `context` measured at 1,676 B vs 26,938 B of artifacts — **16.1x**; `trace-context` v2.0 makes the call |
| Parallel runs cannot corrupt each other | **Met** | Two worktrees for two tickets verified independent; a file created in one is absent from the other |
| Work is tracked and survives a restart | **Met** | Queued jobs re-run after a fresh `JobQueue`; finished jobs read back unchanged; ordering survives via `seq` |
| Every MCP client gets the same tools | **Met** | Tools derived from the registry; schemas derived from handler signatures; verified in a real subprocess |

## The headline number

| | Bytes | ~Tokens |
| --- | --- | --- |
| Reading CC-T001's artifacts | 26,938 | 6,734 |
| `console context CC-T001` | 1,676 | 419 |
| **Saving per turn** | **16.1x** | **~6,300 tokens** |

This is the measurement roadmap item #2 was unfalsifiable without, and it is banked rather
than theoretical: `trace-context` — which runs at the start of *every* agent turn — now
makes the one call.

## Defects found and fixed while building

**1. Broad `except TypeError` masked handler crashes.** Wrapping the handler call meant a
`TypeError` raised *inside* a handler was relabelled "bad arguments", pointing the reader at
the call site instead of the fault. Replaced with `inspect.signature().bind()` before the
call. A regression test asserts a genuine crash still propagates as itself.

**2. `**kwargs` on handlers swallowed argument typos.** `by=modle` would have been ignored
and answered with a default-grouped result that looks correct. Catch-alls removed; the
registry now rejects the typo by name.

**3. Job ordering was undefined within a second.** `submitted` is second-granularity and the
queue routinely accepts several jobs per second, so the job list reshuffled itself. Added a
monotonic `seq`, floored from existing records so it survives a restart.

**4. `static/agents.js` contained a literal NUL byte** (carried over from CC-T001's
follow-up work) making the file read as binary to grep and every text tool. Replaced with
the escape sequence; `node --check` passes and semantics are identical.

## Design decisions worth restating

- **The digest composes, it does not reimplement.** Lane, blockers and spend come from the
  modules that own those facts. A digest with its own route to them becomes a second source
  of truth and eventually disagrees with the board about something that matters.
- **Gates are checked at submission, not at run.** A doomed job is refused while the caller
  is still there to be told.
- **`interrupted` is its own state.** An orphaned job is not `done` (a lie) and not `error`
  (a guess).
- **Unparseable is not empty.** "No open tasks" and "I could not read the plan" are
  different facts, and an agent told the first about the second acts confidently wrong.

Full rationale: [[CC-T002-decision-log]].

## Effort

Estimated 19 h, actual ~14 h. Under because every task composed existing readers rather
than adding storage, and the MCP server needed no SDK.

## Links
- [[CC-T002-summary]] · [[CC-T002-analysis]] · [[CC-T002-requirements]] · [[CC-T002-decision-log]] · [[CC-T002-plan]] · [[CC-T002-progress]] · [[CC-T002-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T001-summary]]
