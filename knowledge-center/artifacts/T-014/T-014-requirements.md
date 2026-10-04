---
ticket: "T-014"
artifact: requirements
---

# Requirements: T-014

## Functional Requirements
1. The Assistant has a talk pair and a work pair, both chosen in Settings.
2. The talk model hands code-shaped work to the work model rather than
   attempting it.
3. A delegated task's result is reported back into the Assistant chat.
4. A shipped provider can be re-pointed at another host, per machine.
5. The model picker shows which models are resident and what each claims to be
   able to do.
6. Choosing a model that is not resident asks once, naming the cost.

## Non-Functional Requirements
1. `agents.toml` is never machine-written; only the address and the key's
   env-var NAME are overridable.
2. "Cannot say" and "not loaded" are different answers and never merge.
3. Delegating raises the human approval card on an API-backed talk model.
4. Nothing is ever loaded silently.

## Acceptance Criteria
- [x] 1. `work_backend`/`work_model` validate and round-trip.
- [x] 2. A re-pointed provider is reachable; the committed row is unchanged.
- [x] 3. Overriding anything but the address or key name is refused.
- [x] 4. Residency reports ids, empty, or `None` — the last for an unreachable
      or silent provider.
- [x] 5. The models route carries `loaded`, `tool_use`, `params`, `context`.
- [x] 6. `delegate` refuses with no work backend and says it did not run the
      task itself.
- [x] 7. `delegate` refuses when no console server can answer its approval.
- [x] 8. A finished delegated TURN posts a notice into the Assistant chat.
- [x] 9. Every API-backed row gates `console_delegate`.

## Out of Scope
- Loading or unloading a model on the user's behalf: LM Studio's JIT load does
  it on first use, and no load endpoint was confirmed.
- Routing by keyword. The model decides, guided by its persona.

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
