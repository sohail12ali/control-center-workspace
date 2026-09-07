---
ticket: "T-012"
artifact: requirements
---

# Requirements: T-012

## Functional Requirements
1. Any OpenAI-compatible provider can be switched on or off from Settings and
   from the CLI.
2. A provider that ships switched off (Ollama, LM Studio) appears in the panel
   so it can be switched on there.
3. Any number of custom providers can be added by base URL.
4. An endpoint can be tested before it is saved.
5. A custom provider can be removed; a shipped one cannot.
6. An enabled provider is immediately usable — composer, Assistant picker,
   model catalogue — without restarting the console.

## Non-Functional Requirements
1. `console/config/agents.toml` is never machine-written.
2. Choices are per-machine and gitignored.
3. An API key is referenced by environment-variable NAME; no key value is ever
   stored, returned by the API, or logged.
4. A custom provider inherits the shipped local rows' tool gates and context
   caps rather than being an unreviewed special case.

## Acceptance Criteria
- [x] 1. `provider enable ollama` makes it usable; `agents.toml` unchanged.
- [x] 2. A stopped local server produces a reason naming the address, not
      "unusable".
- [x] 3. The panel lists switched-off providers with a working switch.
- [x] 4. A custom URL becomes a real backend, offered in the composer.
- [x] 5. Test reports what an endpoint serves before it is saved.
- [x] 6. Refusals: bad id, id collision with a shipped row, non-http URL, a
      pasted key, unknown field, removing a shipped provider.
- [x] 7. No key value appears in any response (asserted by a test).
- [x] 8. Enabling takes effect without a restart.

## Out of Scope
- Pulling or loading models for you: that is Ollama's and LM Studio's job, and
  `Refresh models` reports what they have.
- Making a local model tool-capable. The console can only report what the
  provider says.

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
