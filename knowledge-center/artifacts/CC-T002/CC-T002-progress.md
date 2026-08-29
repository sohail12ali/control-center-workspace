---
ticket: "CC-T002"
artifact: progress
---

# Progress: CC-T002

## Status Summary
Stage: VERIFY — all five plan tasks built and tested.

## Dated Log

### 2026-08-29

**CC-T002-01 — verb registry — done (3 h vs 4 h est).**

- `console/config/verbs.toml` + `server/verbs.py` + `server/verb_handlers.py`;
  `kanban verb list|run`. Eight verbs shipped, all read-only.
- Handlers resolve at **registry load**, so a typo in a handler path is a startup error
  naming the verb, not a surprise the first time someone runs it. Four tests cover the
  four ways a handler path can be wrong.
- Gates (`needs_ticket`, `needs_confirm`, `kinds`, `lanes`) travel with the definition, so
  the CLI, the job queue and the MCP server enforce identical rules without any of them
  reimplementing the rules.
- **Two design corrections the tests forced:**
  - `except TypeError` around the handler call also swallowed a `TypeError` raised *inside*
    a handler and relabelled a genuine crash as "bad arguments" — pointing the reader at
    the call site instead of the fault. Replaced with `inspect.signature().bind()` before
    the call.
  - Handlers originally took `**_`, which meant `by=modle` would be silently ignored and
    answered with a default-grouped result that looks correct. Removed the catch-all so the
    registry rejects the typo by name.

**CC-T002-02 — `context` verb — done (2 h vs 3 h est).**

- `server/context.py` + `kanban context {T} [--json]`. Composes the existing readers
  (tickets, trackers, telemetry, boards) rather than deriving lane or blocker state a
  second way — a digest with its own route to those facts becomes a second source of truth
  and eventually disagrees with the board.
- Two narrow parsers for what nothing else reads: plan task headings and dated progress
  entries. Both report what they could not parse — "no open tasks" and "I could not read
  the plan" are different facts, and an agent told the first about the second acts
  confidently wrong.
- **Measured on CC-T001: 1,676 bytes (~419 tokens) against 26,938 bytes (~6,734 tokens) of
  raw artifacts — a 16x reduction, per turn.** Every cap is stated in the output, so
  silence means the picture is complete.
- `trace-context` rewritten (v2.0) to make the one call instead of opening eight files,
  with the measurement in the skill and a documented fallback when `console/` is absent.
  This is the change that actually banks roadmap item #2.

**CC-T002-03 — worktrees — done (2.5 h vs 3 h est).**

- `server/worktrees.py` + `kanban worktree list|add|remove|prune`. Tests run against a real
  git repository built in `tmp_path` — mocking git here would test the mock.
- Refusals are the substance: never create over an existing path, never remove uncommitted
  work without force (and name what would be lost), never touch a worktree it did not
  create, and never accept a name that could escape the root — that name arrives from a CLI
  argument or an agent tool call.
- Branch pattern comes from config; nothing hardcodes a branch name.

**CC-T002-04 — job queue — done (3 h vs 4 h est).**

- `server/jobs.py` + `kanban job submit|list|show|cancel`. Records on disk are the source of
  truth; memory is a cache.
- Gates are checked at **submission**, while the caller is still there to be told, rather
  than accepting a doomed job that fails later with nobody watching.
- A job orphaned by a dead process becomes `interrupted` — not `done` (a lie), not `error`
  (a guess). Nobody knows how far it got, and the state name has to say so.
- **Ordering flaw found by a test:** `submitted` is an ISO timestamp at second granularity
  and this queue routinely takes several jobs per second, so sorting by it left their order
  undefined and the job list reshuffled itself. Added a monotonic `seq`, floored from
  existing records so it survives a restart.

**CC-T002-05 — MCP server — done (3.5 h vs 5 h est).**

- `server/mcp.py` + `console/mcp_server.py` + root `.mcp.json`. JSON-RPC 2.0 over
  newline-delimited stdio, stdlib only — no SDK, no install step.
- **No tool table.** `tools/list` walks the verb registry and derives each schema from its
  handler's signature, so a new row in `verbs.toml` is a new tool with no code change here.
  A test asserts exactly that.
- A failed gate returns a tool error carrying the reason, not a JSON-RPC error code — the
  model can correct itself from the former and not from the latter.
- Notifications are never answered (a protocol violation some clients treat as fatal), and
  only implemented capabilities are declared.
- Verified in a **real subprocess**, because the failure this design is most exposed to is
  something printing to stdout and corrupting the stream, which only shows up in a real
  process.

- Done: all five tasks. **278 tests passing; harness lint clean.**
- Blocked: nothing.
- Next: verification, then Phase 2 (OpenRouter backend) — which consumes these MCP tools.

## Links
- [[CC-T002-summary]] · [[CC-T002-analysis]] · [[CC-T002-requirements]] · [[CC-T002-decision-log]] · [[CC-T002-plan]] · [[CC-T002-progress]] · [[CC-T002-verification]]

