---
tags: [active]
status: Done
ticket: "T-012"
---

# T-012: Provider switching: Ollama, LM Studio, custom OpenAI-compatible URLs

**Status:** Done
**Stage:** VERIFY
**Owner:** Sohail Ali
**Created:** 2026-09-07
**Due:**

## Overview

Point the console at whatever model you like. Settings → **Model providers**
lists every OpenAI-compatible provider — OpenRouter, Ollama, LM Studio — with a
switch, and **Add a provider** takes any other endpoint that speaks that API:
a vLLM box, llama.cpp, a hosted gateway. `kanban agents provider` does the same
from a terminal.

Most of the machinery was already here: `agents.toml` shipped complete `ollama`
and `lm-studio` rows, and `openai_client` drives them unchanged. What was
missing was a way to turn one on that did not involve hand-editing a committed
file — which is also why the Settings panel had always refused to touch it:
`agents.toml` is a document, and a TOML round-trip would delete its two hundred
lines of comments.

So your choices live beside it, in a gitignored
`console/.cache/agents/providers.json`. Whether you run Ollama is a fact about
your laptop, not about the template.

A key is **named, never pasted**: you give the name of an environment variable
and the value stays in `.env`. Pasting a key into that field is refused with a
sentence saying what the field is for.

## Current State

Shipped and verified live against a real Ollama server: switched on, probed
while stopped and while running, catalogue fetched, a chat started on it, a
custom URL added, tested before saving, used, and removed.

One thing is honestly untested: whether a *local* model actually calls the
console's tools. On this machine the tool-capable model did not fit in free
memory and the one that fit reports no tool support — both in Ollama's own
words, shown in the chat. See [[T-012-verification]].

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
