---
ticket: "T-011"
artifact: analysis
---

# Analysis: T-011

## Context

"We should be able to resume the sessions again. As you know, the CLIs give a
session ID to continue."

## Current State

- `agent_manager.list_chats` lists chats from a previous run as `orphaned`,
  and the UI shows a `past` chip meaning replay-only.
- `agent_session` captures `native_session_id` from the CLI's events and
  already uses it to continue `resume`-transport backends BETWEEN TURNS.
- The Assistant keeps a pointer to its one chat; when that chat is dead,
  `_ensure_session` creates a new one without saying so.

## Key Findings

- **Everything needed was already on disk.** `session.started` records cwd,
  model, mode, agent and title; every later event carries the CLI's session
  id. What was missing was a way back in, not the data.
- **The transcript is append-mode.** A new session with the same id appends to
  the same file — but the `Stream` restarts its sequence at 1, and two events
  numbered 1 in one file would break the client's catch-up after a reconnect.
- **`transcript()` preferred the in-memory ring.** For a resumed chat that
  holds only what happened after the resume, so opening one would have shown
  two events and no history. Found by opening one.
- **Not every backend can do this.** claude and cursor-agent take a resume
  flag; qwen's row says its flags are unverified. Reading the capability off
  the config row keeps that honest and keeps `agents.toml` the place where a
  claim about a CLI lives.
- **The Assistant has the same hole, and it costs more.** Its whole value is
  continuity — memory, the ticket it was looking at — and a restart silently
  reset it.

## Research

Read `agent_manager.py`, `agent_session.py`, `agent_events.py`,
`agent_backends.py`, `features/agents_feature.py`,
`features/assistant_feature.py`, `agents.toml`, and `agents.js`'s chat rail
and dead-composer banner.

## Recommended Path

Recover the identity from the transcript, add a resume template to the backend
row, rebuild the session in place with the same id and a continued sequence,
and expose it as one button plus one route. Then prove it by asking a resumed
model something only the previous process could know.

## Links
- [[T-011-summary]] · [[T-011-analysis]] · [[T-011-requirements]] · [[T-011-decision-log]] · [[T-011-plan]] · [[T-011-progress]] · [[T-011-verification]]
