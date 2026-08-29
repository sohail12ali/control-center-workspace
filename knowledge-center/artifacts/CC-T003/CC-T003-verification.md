---
ticket: "CC-T003"
artifact: verification
---

# Verification: CC-T003

**Verified:** 2026-08-29 · **Result:** PASS with one stated gap (live request — needs the user's key and spend).

## Evidence

| Command | Result |
| --- | --- |
| `python -m pytest` | **386 passed, 1 skipped** (symlink test, not permitted here) |
| `python console/kanban.py harness lint` | `39 skills, 7 agents \| 0 error(s), 0 warning(s)` |
| `node --check console/static/agents.js` | parses |
| `python console/kanban.py agents backends` | claude + cursor-agent; `openrouter` correctly absent (`enabled = false`) |

Tests added by this ticket: agent_tools 39 (1 skipped) · openai_client 28 ·
api_session 25 · prompt_build 15 — **107 new**, 386 total.

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Any OpenRouter model can be run from the console | **Met, unproven live** | Full loop drives against a scripted provider; model id is passed verbatim and the composer keeps a custom-id box. See the gap. |
| The console's own verbs are tools the agent holds | **Met** | `console_context` in the offered tool list; a tool call runs the verb and the result returns to the model |
| Gated tools ask the same way they already do | **Met** | A `write_file` call parks on `agent_approvals.REGISTRY`; allow writes the file, deny reaches the model as text, silence denies |
| Skills reach a backend with no slash commands | **Met** | Skill text appears in the system message; the user message stays exactly what was typed |
| Cost and tokens recorded like any other backend | **Met** | A turn writes a telemetry record with ticket, backend and token counts; usage accumulates across tool rounds |

## The gap

**No live request has been made.** Everything is driven by a scripted provider — including a
tool call, a gated call awaiting a human, a denial, an API error, and the runaway cap. What
has *not* happened is one real HTTPS request to OpenRouter, because that needs the user's key
and spends the user's money. Ticking it on my own judgement is exactly the kind of claim
`BE HONEST` exists to prevent.

To close it: set `OPENROUTER_API_KEY`, flip `enabled = true` on the `openrouter` row in
`console/config/agents.toml`, and start a chat. Everything else is already wired.

## Security posture — stated plainly

This ticket puts a shell and a file writer inside a loop the console owns. That is the
largest blast radius in the repo, so the boundaries are worth stating rather than assuming:

| Control | What it does | What it does not do |
| --- | --- | --- |
| Path confinement | Every file path is `realpath`-resolved and must sit under the workspace root — a symlink cannot step out | Nothing for `run_command` |
| Credential refusal | `.env`, `*.pem`, `*.key`, `credentials.json` are unreadable through the tools and skipped by search | Not a substitute for not having secrets in the tree |
| Approval gate | `write_file`, `edit_file`, `run_command` park on a human, fail-closed on silence | Read-only verbs are deliberately ungated |
| Round cap | Ends a runaway turn with a visible notice | Does not cap spend directly |
| Key handling | Read from env per request; never on the session, in an event, in a transcript, or in telemetry | Nothing reads a `.env` file, by design |

The deliberate non-control: read-only `console_*` verbs do not ask. Approving "look up this
ticket's lane" trains a person to click allow without reading, which is precisely how a gate
stops working for the calls that matter.

## Defect found and fixed

**A job worker could die on a failed record write, taking the queue with it.** A rare
`PytestUnhandledThreadExceptionWarning` appeared once and would not reproduce across five
further runs. Rather than dismiss it, I traced the only unguarded path that fits: `_write`
ran outside any `try`, so an `OSError` there escaped the worker thread — and since the worker
loop is the only thing pulling the queue, every job behind it would have stopped with nothing
saying why. `_write` now reports failure instead of raising, and the worker has a last-resort
guard. Two tests cover it.

Being precise about what was proven: the fix is verified, the original warning is **not**
confirmed to have had this cause. It did not recur, and I did not reproduce it.

## Effort

Estimated 17 h, actual ~12 h.

## Links
- [[CC-T003-summary]] · [[CC-T003-analysis]] · [[CC-T003-requirements]] · [[CC-T003-decision-log]] · [[CC-T003-plan]] · [[CC-T003-progress]] · [[CC-T003-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T002-summary]]
