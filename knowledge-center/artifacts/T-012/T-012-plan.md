---
ticket: "T-012"
artifact: plan
---

# Plan: T-012

## Approach

Copy the two-layer pattern `assistant_config` already uses, merge it where the
config is loaded, and give the existing panel the controls it deliberately
lacked.

## Tasks

### [x] T-012-01 — The per-machine layer (2 h)
- [x] `provider_overrides.py`: load/save/apply/validate/update
- [x] Custom-row defaults mirroring the shipped `ollama` row
- **Done-criteria:** every refusal has a sentence; nothing writes agents.toml
- **Depends on:** —

### [x] T-012-02 — Merge and invalidate (1 h)
- [x] `load_config` applies overrides; `committed_rows`; `forget_config()`
- [x] `provider_list` including switched-off rows; public `probe`
- **Done-criteria:** enabling takes effect on the next request
- **Depends on:** T-012-01

### [x] T-012-03 — Routes (1 h)
- [x] `GET`/`POST /api/agents/providers`, `POST .../probe`, audited
- [x] `model_catalog.peek` for a URL that is not a backend yet
- **Depends on:** T-012-02

### [x] T-012-04 — The panel (2 h)
- [x] Switch per provider, Add a provider, Test, Remove, Refresh models kept
- **Depends on:** T-012-03

### [x] T-012-05 — CLI parity and docs (1 h)
- [x] `kanban agents provider list|enable|disable|add|remove`
- [x] `agents doctor`'s disabled row says how to turn it on
- [x] README, and a comment in `agents.toml` pointing at the new way
- **Depends on:** T-012-03

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-012-01 — Per-machine layer | 2 h | mirrors assistant_config |
| T-012-02 — Merge and invalidate | 1 h | two functions and a cache |
| T-012-03 — Routes | 1 h | beside the existing agents routes |
| T-012-04 — The panel | 2 h | a rewrite of one panel |
| T-012-05 — CLI and docs | 1 h | one subcommand |
| **Total** | **7 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1, 8 | T-012-02 |
| 2 | T-012-01, T-012-02 |
| 3 | T-012-04 |
| 4 | T-012-01 |
| 5 | T-012-03 |
| 6, 7 | T-012-01 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| A UI write destroys agents.toml's comments | Med | High | The panel never writes it; a test asserts the file is untouched | Builder |
| Someone pastes a key into the env-var field | High | High | Refused, with a message saying what the field is for | Builder |
| A custom provider runs ungated | Med | High | Inherits the shipped local rows' `gated_tools` | Builder |
| A newly enabled provider needs a restart | Med | Med | `forget_config()` drops the parsed config and the probe cache | Builder |

## Dependencies
- Blocks: —
- Blocked by: —

## Links
- [[T-012-summary]] · [[T-012-analysis]] · [[T-012-requirements]] · [[T-012-decision-log]] · [[T-012-plan]] · [[T-012-progress]] · [[T-012-verification]]
