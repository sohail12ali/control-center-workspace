---
ticket: "T-012"
artifact: analysis
---

# Analysis: T-012

## Context

"Add an option to use LM Studio or Ollama... like we have OpenRouter for a
provider. We can switch the provider to Ollama or LM Studio or any custom URL
where we can use the OpenAI API style."

## Current State

- `agents.toml` already ships **complete** `ollama` and `lm-studio` rows:
  `transport = "openai_api"`, `auth = "none"`, the right base URLs, gated
  tools, and context caps tuned for a local model. Both sit at
  `enabled = false`.
- `assistant_config.LOCAL_FIRST` already prefers `ollama`, then `lm-studio`,
  over the hosted backends.
- `registry()` filters on the row's `enabled`, and nothing overrides it.
- The Settings "Model providers" panel is read-only, and says why in a
  comment: writing `agents.toml` would destroy its comments.

## Key Findings

- **The feature was three quarters built and unreachable.** The gap was not
  the transport or the client; it was that turning a provider on meant editing
  a committed file by hand.
- **That file cannot be machine-written.** `tomlio.dumps()` round-trips TOML
  into bare key-value pairs. `agents.toml` is mostly prose — why a local model
  needs tool support, what "loaded" means in LM Studio — and all of it would
  go. The panel's existing refusal to write it is correct and had to be kept.
- **The precedent already exists.** `assistant_config` solved the same problem
  for the Assistant's settings: committed defaults, per-machine overrides in a
  gitignored file, merged on read.
- **A custom provider is a small amount of data and a large amount of
  defaulting.** A base URL and a label; everything else — transport, gates,
  context caps — should come from the shipped local rows rather than being
  asked for or, worse, left off.
- **The keys question is already answered.** `openai_client` reads
  `os.environ[api_key_env]` at use time. Naming a variable keeps that intact;
  storing a value would make this the first file in the project to hold a
  secret.

## Research

Read `agent_backends.py` (`load_config`, `registry`, `Backend`, the probe),
`model_catalog.py` (`summary`, `fetch`), `openai_client.py`,
`agent_api_session.py`, `assistant_config.py` as the pattern to copy, the
providers panel in `settings.js`, and the `ollama` / `lm-studio` rows in
`agents.toml` including their comments.

## Recommended Path

Add the per-machine layer, merge it in `load_config`, expose a provider list
that includes the switched-off rows, and give the panel a switch, an add form
and a Test button. Then prove it against the Ollama that is actually installed
on this machine.

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
