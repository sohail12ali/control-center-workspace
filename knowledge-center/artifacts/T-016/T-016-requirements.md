---
ticket: "T-016"
artifact: requirements
status: frozen
freeze_status: frozen
frozen_at: "2026-09-11"
frozen_iteration: 1
---

# Requirements: T-016

Frozen 2026-09-11 from [[T-016-requirements-draft]] iteration 1. Intent and AC live here; narrative and challenge history stay on the draft.

## Intent

Make the Assistant the home, and every piece of work a Run you can watch.

Raw: “I want to rethink the delivery console to work better with agents and assistant.”

## In scope

- New Assistant tab, first in nav when `html.in-shell`; browser nav unchanged.
- Amend [[desktop-assistant]] tray lock (Assistant, not Agents session).
- Run records under `console/.cache/runs/` (tagged union: chat / job / cursor-pointer).
- Agents tab is the Run inspector; board “Start agent” creates a Run / asks Assistant.
- Harness role launch = `cursor-agent` CLI chat + persona; no in-console pipeline.
- Verbs: ticket move, ticket set, tracker add, tracker update.

## Out of scope

- T-015 verify work; deleting tabs; in-console GROUND→VERIFY; new backends/agents/desktop capture; hand-editing ticket/tracker TOML; browser nav invert; progress-append / close-work / log-work verbs; prompt-package or MCP-claim launch.

## Functional requirements

### FR-1 Native shell opens on the Assistant tab
AC: `in-shell` default view is the new Assistant tab; without the class, `NAV_ORDER` unchanged; tray `say` still uses the same Assistant session; other tabs remain.

### FR-2 Work is a Run you can watch
AC: `console_delegate` and board create-run share one record type; Assistant can name id+state without switching tabs; record survives console restart (not process-memory only).

### FR-3 Board starts a Run or asks the Assistant
AC: `startAgentFor` is not `compose` + `go("agents")` as the only path; action is ticket-scoped.

### FR-4 Agents tab is the Run inspector
AC: delegated Run appears under the same id; `@persona` without a Run is not the success path for harness launch; T-011 resume still works for chat-backed Runs.

### FR-5 Pipeline mutations are verbs
AC: MCP `tools/list` includes the four verbs (`console_*` names); invalid lane fails like `tickets.move`; pytest on handlers; no hand-edit of TOML.

### FR-6 Launch harness role via cursor-agent chat
AC: `agent_manager.create` backend `cursor-agent` + persona; Run executor is that chat id; missing binary fails named, no `claude` fallback; still seven `.claude/agents/` files.

### FR-7 Wiki matches shipping Assistant
AC: `desktop-assistant.md` has no “live Agents session” tray lock; wikilinks T-016 decisions.

## Non-functional

| Category | Target |
|---|---|
| Performance | No new sockets on first paint of Assistant home (T-015 no-probe) |
| Scalability | Chat-backed Runs = one subprocess per chat; do not put chats on `[jobs] max_concurrent` |
| Security | Unchanged loopback + CSRF header + gated tools |
| Audit | Run start/end and new verbs are audit events |
| Availability | `kanban.py serve` without shell keeps working; stdlib-only console |
| Usability | `assistant.md` reply contract stays; add Run-watch guidance only |
| Compliance | N/A — local workspace |

## Data

- **Run** (new): `console/.cache/runs/` gitignored. Fields: id, ticket, role, executor union, state, timestamps, optional spend.
- ticket.toml / trackers: existing writers, now also verbs.
- Assistant session pointer: unchanged.

## Business rules

BR-1 TOML via writers only. BR-2 no second orchestrator. BR-3 seven role agents + console Assistant persona. BR-4 browser nav unchanged. BR-5 tagged-union Run; harness launch uses chat/`cursor-agent`. BR-6 `needs_confirm` vs `gated_tools`. BR-7 T-015 not done-criteria.

## Edge cases

Missing `cursor-agent` named fail; invalid lane reject; two Runs per ticket allowed; CLI without MCP will not hold new verbs; orphaned chat → Run `interrupted`; no work backend still refuses to run on talk model.

## Sign-off

Irshad, 2026-09-11: Q1b `cursor-agent` CLI, Q2 tagged union, Q3 defer extra verbs, Q4 first tab, plus `/kickoff T-016 full stack`.

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-requirements-draft]] · [[T-016-iteration-log]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
