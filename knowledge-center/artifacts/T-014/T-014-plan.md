---
ticket: "T-014"
artifact: plan
---

# Plan: T-014

## Approach

Settings first, then the facts the picker needs, then the ability itself, then
the UI. Prove it by delegating a real task and watching the answer return.

## Tasks

### [x] T-014-01 — The second slot and per-machine addresses (2 h)
- [x] `work_backend` / `work_model`, validated like the talk pair
- [x] `where` overrides in `provider_overrides`, address and key name only
- **Done-criteria:** a shipped row reachable at a LAN address, committed file
  untouched
- **Depends on:** —

### [x] T-014-02 — Residency and capabilities (2 h)
- [x] `model_catalog.loaded()` with LM Studio and Ollama adapters; `None` for
      "cannot say"
- [x] `capabilities()` for tool training, vision, params, context
- [x] Both surfaced on `GET /api/agents/models?backend=`
- **Depends on:** T-014-01

### [x] T-014-03 — Delegation (3 h)
- [x] The `delegate` verb and its handler; refusals for no task, no work
      backend, an unusable backend, and no server to answer the card
- [x] `console_delegate` gated on every API-backed row
- [x] `assistant_reply.watch_delegate` reporting on turn end
- [x] Persona guidance on what to hand over
- **Depends on:** T-014-01

### [x] T-014-04 — The Settings page (2 h)
- [x] Talk and Work rows, each a backend select plus a real model dropdown
- [x] Loaded / not loaded / unknown, tool-training marks, and one confirm
      before an unloaded model
- **Depends on:** T-014-02

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-014-01 — Slot and addresses | 2 h | mirrors the T-012 override layer |
| T-014-02 — Residency | 2 h | two adapters and a route field |
| T-014-03 — Delegation | 3 h | a verb, a gate and a watcher |
| T-014-04 — Settings | 2 h | one panel rewrite |
| **Total** | **9 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1, 2, 3 | T-014-01 |
| 4, 5 | T-014-02 |
| 6, 7, 8, 9 | T-014-03 |
| the picker | T-014-04 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| The talk model attempts work it cannot do | High | High | `delegate` refuses to fall back; the persona says what to hand over | Builder |
| A local model spends money unprompted | Med | High | `console_delegate` is gated on every API-backed row | Builder |
| A sleeping box reads as "nothing loaded" | High | Med | `None` is a third state, carried to the UI | Builder |
| An override quietly widens a tool gate | Low | High | Only the address and key name can be overridden | Builder |

## Dependencies
- Blocks: —
- Blocked by: T-012 (providers), T-013's assistant fixes (mode/model reaching
  the chat)

## Links
- [[T-014-summary]] · [[T-014-analysis]] · [[T-014-requirements]] · [[T-014-decision-log]] · [[T-014-plan]] · [[T-014-progress]] · [[T-014-verification]]
