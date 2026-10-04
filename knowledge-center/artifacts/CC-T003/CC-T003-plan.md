---
ticket: "CC-T003"
artifact: plan
---

# Plan: CC-T003

## Approach

Phase 2 — an agent backend that talks to an HTTP API instead of driving a CLI, so the
console can run any model OpenRouter serves.

The gap is structural, not config. Every backend today is a subprocess: `LiveSession` holds
one process with stdin open, `TurnSession` runs one process per turn. OpenRouter is HTTP and
SSE, so it needs a fourth transport and a session class that owns its own agent loop.

**Owning the loop is the point, not a cost.** A CLI backend brings its own harness — its own
tools, its own permission model, its own idea of what a skill is. An API backend has none of
that, which means the loop can be *ours*: the same approval gate, the same telemetry, and —
the part that matters — the console's own verbs as first-class tools. The agent that comes
out of this is the one that reads a ticket with one `context` call because that call is a
tool it holds, not a convention it has to remember.

Two things it must NOT do differently:

- **Emit different events.** It produces the same normalized event stream the chat UI,
  transcripts and telemetry already consume. A second event shape means a second renderer.
- **Gate differently.** `agent_approvals.REGISTRY` is already transport-agnostic — it takes a
  `publish` callable and blocks. In-process, that is a *better* gate than the CLI's hook: no
  hook process, no HTTP round trip, same "Permission needed" card.

Constraint carried forward: **zero new runtime dependencies.** SSE over `urllib` is stdlib.

**The key is the user's, and so is the spend.** Nothing here reads a key at import time,
nothing hardcodes a model, and `pricing.toml` still ships empty. Live verification needs a
key and costs real money, so it is the user's call, not mine — see the note at the end.

## Tasks

### [x] CC-T003-01 — Tool surface for API agents (4 h)

- [x] `console/server/agent_tools.py` — the tools an API-driven agent holds: file reads and
      writes, glob, grep, shell, plus **every console verb**, schema-generated from the
      registry exactly as the MCP server does it
- [x] One definition per tool, shared with the MCP schema generator — a tool defined twice
      is a tool that will describe itself two ways
- [x] Path confinement: no read or write escapes the workspace root
- **Done-criteria:** the tool list contains the 8 shipped verbs plus the file/shell tools;
  a path traversal attempt is refused; every tool has a schema a model can call from.
- **Basis:** dossier §2 item #1 (the loop is where the gates live) + #7 (verbs as tools)
- **Depends on:** —

### [x] CC-T003-02 — OpenRouter chat client (3 h)

- [x] `console/server/openai_client.py` — streaming chat completions over `urllib`, SSE
      parsed incrementally; OpenAI-compatible, so it serves any compatible base URL
- [x] Assembles streamed `tool_calls` deltas into whole calls (they arrive fragmented, by
      index, with arguments split across chunks)
- [x] Errors carry the provider's message; a key that is missing, refused or rate-limited
      must say which
- **Done-criteria:** a fixture SSE stream yields text deltas, a complete tool call, and a
  usage record; a 401 and a 429 each produce a distinguishable, readable error.
- **Basis:** dossier §2 item #1, option A
- **Depends on:** —

### [x] CC-T003-03 — `ApiSession` transport (5 h)

- [x] Fourth transport `openai_api`; `ApiSession(BaseSession)` running the tool loop
- [x] Emits the existing normalized events (`text.delta`, `tool.start`, `usage`, `turn.end`)
- [x] Gated tools go through `agent_approvals.REGISTRY` — same card, no hook process
- [x] Telemetry per turn, via the path CC-T001 already built
- **Done-criteria:** a scripted fake provider drives a full turn — text, a gated tool call
  awaiting approval, a denial the model can read, and a `turn.end` carrying token counts —
  with no real network.
- **Basis:** dossier §2 item #1
- **Depends on:** CC-T003-01, CC-T003-02

### [x] CC-T003-04 — Skill and persona injection (3 h)

- [x] `console/server/prompt_build.py` — system prompt from the harness core, the selected
      persona's agent file, and the selected skill's SKILL.md
- [x] An API agent has no slash-command system, so a skill is *injected*, not referenced;
      this is what makes roadmap item #2 a hard dependency of item #1
- [x] Budgeted, with what was included stated — never a silent truncation
- **Done-criteria:** choosing persona `builder` and skill `plan` produces a system prompt
  containing both files plus the always-on core, under a stated budget.
- **Basis:** dossier §2 item #1, "non-obvious dependency"
- **Depends on:** —

### [x] CC-T003-05 — Config, model catalogue and wiring (2 h)

- [x] `agents.toml` row for OpenRouter: base URL, `api_key_env`, models, gated tools
- [x] Backend reports `installed` from key presence, not from PATH — the existing check is
      meaningless for an API backend and would claim it is unavailable
- [x] The composer's model picker and custom-id box work unchanged
- **Done-criteria:** with no key set the backend lists as not installed and says why; with
  one set it lists as ready; adding a model is a config edit.
- **Basis:** dossier §2 item #9
- **Depends on:** CC-T003-03

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T003-01 — Tool surface | 4 h | file/shell tools + verb bridge + confinement |
| CC-T003-02 — OpenRouter client | 3 h | SSE parse + tool-call assembly + errors |
| CC-T003-03 — ApiSession | 5 h | the agent loop, gates, events, telemetry |
| CC-T003-04 — Prompt building | 3 h | assembly + budget |
| CC-T003-05 — Config and wiring | 2 h | one row + an installed-check that means something |
| **Total** | **17 h** | flat-mode estimate |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
| --- | --- |
| Any OpenRouter model can be run from the console | CC-T003-02, CC-T003-05 |
| The console's own verbs are tools the agent holds | CC-T003-01 |
| Gated tools ask the same way they already do | CC-T003-03 |
| Skills reach a backend with no slash commands | CC-T003-04 |
| Cost and tokens are recorded like any other backend | CC-T003-03 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Shell and write tools in a loop we own is the largest blast radius in this repo | High | High | Path confinement on every file tool; shell and writes gated by default in config; the gate is the same one a human already answers | Builder |
| An API key leaks into a transcript or telemetry record | Med | High | Key read from env at call time, never stored on the session, never in an event; telemetry records model and counts only | Builder |
| SSE parsing is subtly wrong and truncates replies | Med | High | Fixture streams covering split chunks, fragmented tool arguments, and `[DONE]`; no live network in tests | Builder |
| Provider response shapes drift | Med | Med | Parse defensively, keep the provider's own error text, never assert a shape the tests do not cover | Builder |
| Loop runs away and spends money | Med | High | Hard cap on tool-call rounds per turn, stated in the turn's end event | Builder |

## Dependencies

- Blocks: Phase 3 (remote dispatch runs these sessions unattended)
- Blocked by: CC-T002 (closed) — the verbs this backend holds as tools

## Note on live verification

Everything here is verifiable without a key: a scripted fake provider drives the loop,
including a gated tool call and a denial. What cannot be proven without the user is a real
request to OpenRouter — that needs their key and spends their money. It is left as a stated
gap in verification rather than quietly ticked, exactly as CC-T001's live-telemetry gap was.

## Links
- [[CC-T003-summary]] · [[CC-T003-analysis]] · [[CC-T003-requirements]] · [[CC-T003-decision-log]] · [[CC-T003-plan]] · [[CC-T003-progress]] · [[CC-T003-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]] · Prior phase: [[CC-T002-summary]]
