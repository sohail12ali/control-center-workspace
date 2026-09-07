---
ticket: "T-012"
artifact: progress
---

# Progress: T-012

## Status Summary
Stage: VERIFY — driven live against a real Ollama server. See
[[T-012-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-012-01 `provider_overrides.py` — the per-machine layer, its merge rules
    and its refusals, including a pasted key in the env-var field.
  - T-012-02 `load_config` merges overrides; `provider_list` reports the
    switched-off rows too; `forget_config()` makes a change take effect now.
  - T-012-03 `GET`/`POST /api/agents/providers` and a probe route, audited as
    `providers.change`; `model_catalog.peek` for a not-yet-a-backend URL.
  - T-012-04 The Settings panel gained switches, Add a provider, Test and
    Remove.
  - T-012-05 `kanban agents provider …`, the doctor's message, README and a
    pointer comment in `agents.toml`.
- Verified live: Ollama switched on while stopped (reason names the address),
  started, catalogue fetched (`deepseek-coder:latest`, `qwen3:8b`), a chat run
  on it, a custom URL added through the UI, tested before saving, used, and
  removed. `agents.toml` untouched throughout.
- Not verified, deliberately: a local model completing a tool-calling turn —
  qwen3:8b needs 5.5 GiB against 1.76 GiB free, and deepseek-coder reports no
  tool support. Both are Ollama's own words, shown in the chat.
- Blocked: —
- Next: —

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
