---
ticket: "T-014"
artifact: analysis
---

# Analysis: T-014

## Context

"A local model for communicating with users' basic needs, and the coding part
by the CLI or the OpenRouter models. The URL and API key can be different for
each system, so make it configurable. And before loading, ask — show which
models are already loaded."

## Current State

- The Assistant has ONE `backend`/`model` pair.
- Its 19 verbs and workspace tools contain nothing that starts an agent on
  another backend.
- `model_catalog` caches `/v1/models`, which does not say what is resident.
- Per-machine provider overrides (T-012) cover `enabled` only, so the shipped
  `lm-studio` row is stuck on `127.0.0.1`.

## Key Findings

- **The local box is genuinely good at the talking half.** Measured through
  the exact request shape the console sends: `qwen/qwen3.5-9b` calls tools
  correctly and answers in 1.4 s once resident.
- **Residency is the thing the UI has to show.** LM Studio keeps one model
  loaded and swaps on demand, so the cold numbers (6-25 s) are model loads,
  not inference. A dropdown that hides that invites a 25-second surprise.
- **The server already reports what a picker needs.** `/api/v1/models` carries
  `loaded_instances`, `trained_for_tool_use`, `vision`, context length and
  parameter count per model.
- **A capability flag is a hint, not a contract.** `meta/muse-glimmer`
  declares `trained_for_tool_use: false` and called a tool correctly anyway.
- **A verb is the cheapest way to give the Assistant a new ability.** The verb
  registry turns one config row into an Assistant tool, an MCP tool and a CLI
  command with no glue — and `agents.toml`'s `gated_tools` is where the human
  gate for it belongs.
- **`assistant_reply` already had the return channel.** It publishes `notice`
  events into a chat's stream, which the Assistant UI relays and the voice path
  speaks.

## Research

Probed the LM Studio server directly (models, capabilities, residency, and a
tool call per model); read `agent_tools.tool_definitions`, `verbs.toml`'s own
contract, `agent_manager.create`, `assistant_reply`, `provider_overrides`,
`model_catalog`, and the Assistant panel in `settings.js`.

## Recommended Path

Add the second slot, teach the override file to re-point a row, read residency
and capabilities from whatever the base URL answers, and give the Assistant one
gated verb to hand work over — then prove the loop by delegating a real task
and watching the answer come back.

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
