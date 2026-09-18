---
tags: [completed]
status: Complete
closed_date: 2026-08-29
ticket: "CC-T003"
---

# CC-T003: Phase 2 - OpenRouter backend: API transport, tool loop, skill injection, model routing

**Status:** Complete  
**Stage:** Closed  
**Owner:**  
**Created:** 2026-08-29  
**Due:**  

## Overview

Phase 2 — an agent backend with no CLI behind it. The console talks to an OpenAI-compatible
endpoint and runs the loop itself, which is what lets that loop hold the console's own verbs
as tools, gate through the same "Permission needed" card, and record telemetry the same way
every other backend does.

A model with no slash-command system cannot resolve `/plan`, so choosing a skill here injects
its text into the system prompt — which is why the token work of Phase 0 and 1 had to come
first.

## Current State

Closed 2026-08-29. 386 tests passing, harness lint clean.

**Not yet proven live.** No real request has been made to OpenRouter: that needs the user's
key and spends the user's money. To finish: set `OPENROUTER_API_KEY`, flip `enabled = true`
on the `openrouter` row in `console/config/agents.toml`, start a chat.

## Links
- [[CC-T003-summary]] · [[CC-T003-analysis]] · [[CC-T003-requirements]] · [[CC-T003-decision-log]] · [[CC-T003-plan]] · [[CC-T003-progress]] · [[CC-T003-verification]]

