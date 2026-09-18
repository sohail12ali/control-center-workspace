---
ticket: "T-012"
artifact: decision-log
---

# Decisions: T-012

## per-machine-overrides-not-a-rewritten-agents-toml
**Decision:** Choices go to `console/.cache/agents/providers.json`; the
committed `agents.toml` is never written.
**Rationale:** Two reasons, and the second decides it. Whether you run Ollama
is a fact about your laptop. And `agents.toml` is a document — the ollama row
alone carries a paragraph on why a tool-capable model matters — which
`tomlio.dumps()` would silently delete. The Settings panel already refused to
write it for exactly this reason.
**Impact:** `load_config` merges; `provider_overrides` owns the rules.

## a-custom-provider-inherits-the-local-rows-defaults
**Decision:** A custom row supplies a URL and a label; transport, gates,
approval timeout and context caps come from `DEFAULTS_FOR_CUSTOM`, which
mirrors the shipped `ollama` row.
**Rationale:** The alternative is asking someone to specify a tool gate in a
form, which they will not, and getting an ungated provider by default.
**Impact:** A provider added in ten seconds has the same gate as one that
shipped: writes and shell ask a human in the chat.

## keys-are-named-never-stored
**Decision:** `api_key_env` holds the NAME of an environment variable, and a
value-shaped entry is refused with a message explaining the field.
**Rationale:** `openai_client` already reads the environment at use time. No
file in this project has ever held a secret, and a gitignored file is not a
good enough reason to make this the first.
**Impact:** A test asserts no key value can appear in the provider listing.

## the-panel-lists-what-is-OFF
**Decision:** `provider_list` is a separate function from `registry`, because
it deliberately includes disabled rows.
**Rationale:** `registry()` answers "what can I run", which is the wrong
question for the screen where you turn something on.
**Impact:** A disabled provider is not probed — scanning every configured port
on every repaint would be work done for nobody.

## test-before-save
**Decision:** `POST /api/agents/providers/probe` takes a URL that is not yet a
backend.
**Rationale:** Otherwise a typo in a port number is discovered on the first
turn, several minutes and one confusing error later.
**Impact:** The same probe and the same sentences as a configured provider —
what you see before saving is what the console will see after.

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
