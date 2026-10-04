---
ticket: "T-012"
artifact: verification
---

# Verification: T-012

Verified 2026-09-07. **pytest 1133 passed** (1100 before this ticket's tests),
harness lint clean, and the whole path driven live against a real Ollama server
with real pulled models.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | A shipped-but-off provider can be switched on without editing a committed file | PASS | `kanban agents provider enable ollama` → `ollama yes ready local`; the stored file is `{"enabled": {"ollama": true}}` |
| 2 | `agents.toml` is never written by the feature | PASS | `git diff console/config/agents.toml` stayed empty across every enable, add and remove. (The 4-line comment in this ticket's diff is hand-written, and says how to switch a provider on) |
| 3 | An unreachable provider says what is wrong | PASS | With the server stopped: `nothing is listening on 127.0.0.1:11434 — is the server running? Start it with 'ollama serve'.` — not "unusable" |
| 4 | Its catalogue can be fetched | PASS | `agents models ollama --refresh` listed `deepseek-coder:latest` and `qwen3:8b` from the running server |
| 5 | The panel lists switched-OFF providers too | PASS | Settings shows Ollama, OpenRouter and LM Studio with switches; a panel that listed only what is already on could not be where you turn one on |
| 6 | A custom OpenAI-compatible URL can be added | PASS | Added `local-copy` through the UI; it appears in `/api/agents/backends`, so the composer and the Assistant's picker both offer it |
| 7 | Test probes before saving | PASS | Test on `http://127.0.0.1:11434/v1` answered `answering — 2 models: deepseek-coder:latest, qwen3:8b` **before** the row existed |
| 8 | A custom provider is a real backend | PASS | A chat started on it ran under `agent: local-copy, model: deepseek-coder:latest` and reached Ollama |
| 9 | Only your own providers can be removed | PASS | Removing `local-copy` from the UI left the three shipped rows; `remove ollama` is refused with "only ones you added here can be removed" |
| 10 | A key is named, never stored | PASS | `api_key_env` takes an env var NAME; a pasted key is refused with a sentence saying what the field is for. A test asserts no key VALUE appears anywhere in the provider listing |
| 11 | A newly enabled provider works without a restart | PASS | `forget_config()` drops the parsed config and the probe cache; the enable → ready → refresh → chat sequence above happened in one server run |
| 12 | A local model completes a tool-calling turn | **NOT TESTED** | See below — the honest answer on this machine today |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1133 passed
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

33 new tests: the merge (each precedence rule), custom-row defaults, every
refusal (bad id, id collision, non-http URL, a **pasted key** in the env-var
field, unknown field, unknown patch key, removing a shipped row), atomic
persistence, a corrupt override file, and that the committed file is never
written.

## What is NOT verified, and why

**A local model actually using the console's tools.** The `ollama` row's own
comment warns that local tool support is uneven, and this machine could not
settle it either way today:

```
qwen3:8b                 model requires more system memory (5.5 GiB) than is available (4.7 GiB)
deepseek-coder:latest    registry.ollama.ai/library/deepseek-coder:latest does not support tools
```

Both of those are **Ollama's own words, surfaced in the chat** — which is
itself the evidence that the wiring is right: the console reached the provider,
sent a real request, and showed the answer rather than a generic failure. What
is unproven is the next step: that a tool-capable local model, given room to
load, calls `console_context` rather than merely talking. Pulling a smaller
tool-capable model (qwen3:1.7b) would settle it; that was offered and
deliberately deferred.

**LM Studio.** Not installed here. Its row is exercised only through the
enable/probe path — the same code as Ollama's, but nothing on this machine has
run a turn against it.

## Notes

### Why the override file exists at all

`agents.toml` is a document: two hundred lines explaining why the ollama row
needs a tool-capable model, what LM Studio means by "loaded", why a local
context cap is lower. `tomlio.dumps()` would round-trip that into bare
key-value pairs and delete every word — which is exactly why the Settings panel
already refused to write it. So the panel writes a machine-local JSON file
instead, and the committed file stays the thing you can read.

### Edge cases probed

- A custom row whose id collides with a shipped one never shadows it, at the
  merge as well as at validation — the committed row is the one with the
  review.
- Removing a provider forgets its enable flag too, so re-adding the same id
  does not inherit a stale "off".
- A half-wrong patch stores nothing: an earlier choice survives a later bad
  request.
- An id is normalised (`  My-LLM  ` → `my-llm`) rather than refused; case is a
  typing accident, not a mistake worth an error.

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
