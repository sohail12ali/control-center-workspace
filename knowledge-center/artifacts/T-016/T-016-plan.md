---
ticket: "T-016"
artifact: plan
---

# Plan: T-016

## Approach

Ship the **kernel verbs first** (FR-5): wrapping `tickets.move` / `set_field` and tracker add/update as `verbs.toml` rows immediately gives MCP and `openai_api` the same tools, with no UI. Then a **small Run record** (`console/.cache/runs/`, tagged union — [[T-016-decision-log]] run-is-tagged-union) so `console_delegate` and harness launch share an id. Harness launch is `agent_manager.create` on `cursor-agent` with `@persona` ([[#harness-via-cursor-agent-cli]]). Last, **in-shell IA**: the Assistant plugin grows a tab; the *frontend* sorts it first when `html.in-shell` (the CSS class is client-only — `main.rs:115-122` — so `NAV_ORDER` on the server cannot see it). Board `startAgentFor` and the Agents list then consume Runs. Wiki last (FR-7). Do not extend `jobs.py` to chats. Do not touch T-015 tray/HUD/latency paths.

Structure: **multi-layer** — service verbs, new data, UI tab, board, inspector, wiki (9 components, 10 tasks).

## Slices

### Slice 1 — Mutation verbs (FR-5)
### Slice 2 — Run store + wrap delegate + harness launch (FR-2, FR-6)
### Slice 3 — Assistant tab + in-shell sort (FR-1)
### Slice 4 — Board + inspector (FR-3, FR-4)
### Slice 5 — Wiki lock (FR-7)

## Tasks

Flat index; canonical IDs live in [[T-016-task-breakdown]].

### [x] T-016-01 — ticket move/set verbs (2 h)
- **Done-criteria:** MCP lists `console_ticket_move` and `console_ticket_set`; invalid lane fails like `tickets.move`; pytest.
- **Basis:** thin adapters over `tickets.py:157-188`
- **Depends on:** —

### [x] T-016-02 — tracker add/update verbs (2 h)
- **Done-criteria:** MCP lists add/update; `needs_confirm`; pytest; no TOML hand-edit.
- **Depends on:** —

### [x] T-016-03 — Run store (3 h)
- **Done-criteria:** create/get/list JSON under `console/.cache/runs/`; states include interrupted; tests.
- **Depends on:** —

### [x] T-016-04 — Wrap `console_delegate` as a Run (2 h)
- **Done-criteria:** After delegate, a Run exists with chat executor; Assistant can read it via a verb or session extra.
- **Depends on:** T-016-03

### [x] T-016-05 — Harness launch verb (3 h)
- **Done-criteria:** `cursor-agent` + persona; missing binary named fail; no claude fallback; pytest.
- **Depends on:** T-016-03

### [x] T-016-06 — Assistant tab (3 h)
- **Done-criteria:** Plugin `register_tab`; home shows talk + run list + ticket strip; still `/api/assistant/say`.
- **Depends on:** T-016-03

### [x] T-016-07 — in-shell tab sort (1.5 h)
- **Done-criteria:** `html.in-shell` → Assistant first and default; browser unchanged.
- **Depends on:** T-016-06

### [x] T-016-08 — Board start-run (1.5 h)
- **Done-criteria:** Primary action is not compose+`go("agents")` only; ticket-scoped.
- **Depends on:** T-016-03, T-016-06

### [x] T-016-09 — Agents inspector lists Runs (3 h)
- **Done-criteria:** Delegated/harness Run ids appear; chat resume still works.
- **Depends on:** T-016-03, T-016-04

### [x] T-016-10 — Wiki + assistant.md (1 h)
- **Done-criteria:** No “live Agents session” tray lock; T-016 wikilinks; persona mentions Runs.
- **Depends on:** —

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-016-01 ticket verbs | 2 h | existing writers |
| T-016-02 tracker verbs | 2 h | existing writers |
| T-016-03 Run store | 3 h | new module + tests |
| T-016-04 wrap delegate | 2 h | one call site |
| T-016-05 harness launch | 3 h | create + fail path |
| T-016-06 Assistant tab | 3 h | new JS + routes |
| T-016-07 in-shell sort | 1.5 h | frontend sort |
| T-016-08 board | 1.5 h | `startAgentFor` |
| T-016-09 inspector | 3 h | agents.js list |
| T-016-10 wiki | 1 h | two markdown files |
| **Total** | **22 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| FR-1 in-shell home / browser unchanged / same session | T-016-06, T-016-07 |
| FR-2 Run id, watch, durable | T-016-03, T-016-04 |
| FR-3 board action | T-016-08 |
| FR-4 inspector + resume | T-016-09 |
| FR-5 four verbs + tests | T-016-01, T-016-02 |
| FR-6 cursor-agent launch | T-016-05 |
| FR-7 wiki | T-016-10 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| `html.in-shell` is client-only; server NAV_ORDER cannot branch | High | Med | Sort tabs in JS; tests for both classes | Builder | analysis; `main.rs:115-122` |
| `cursor-agent` missing on the machine | Med | High | Honest fail, no claude fallback (FR-6) | Builder | decision harness-via-cursor-agent-cli |
| Agents tab + Assistant tab duplicate chat UI | Med | Med | Inspector reuses chat render; Assistant is talk+runs | Builder | FR-4 isolate |
| T-015 still open; overlapping files | Med | Med | Do not edit tray/HUD/settings-get probe paths | Builder | BR-7 |
| CLI backends still lack new verbs without MCP | High | Low | Document in About/assistant extra; don’t pretend | Builder | `agent_tools.py:3-4` |

No high×high. All top risks have mitigation.

## Dependencies
- Blocks: —
- Blocked by: T-015 only if a file conflict appears (not expected)

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-components]] · [[T-016-task-breakdown]] · [[T-016-implementation-plan]] · [[T-016-progress]] · [[T-016-verification]] · [[T-016-test-cases]]
