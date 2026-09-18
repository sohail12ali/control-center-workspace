---
ticket: "T-016"
artifact: implementation-plan
---

# Implementation plan: T-016

Master synthesis of frozen requirements, plan slices, components, and tasks. Effort total **22 h** matches [[T-016-task-breakdown]].

## Ticket summary

Invert the native-shell IA so the Assistant is home; give work a durable Run; expose ticket/tracker mutations as verbs; launch harness roles as `cursor-agent` chats. T-015 isolated.

## Phase 1 — Kernel verbs (4 h)

Slice 1a. Files: `console/config/verbs.toml`, `console/server/verb_handlers.py`, `console/tests/test_verbs.py` (or new `test_ticket_verbs.py`). Call `tickets.move` / `set_field` / `trackers.add` / `trackers.update` only — no second writer.

Tasks: 1-1-1, 1-1-2. Requirements: FR-5. Can start immediately.

## Phase 2 — Runs (8 h)

Slice 2a. Files: new `console/server/runs.py`, tests, `verb_handlers.delegate` wrap, new launch verb. Storage `console/.cache/runs/` (ensure gitignore already covers `.cache/`). Do not modify `jobs.py` chat tracking.

Tasks: 2-1-1 → 2-1-2, 2-1-3. Requirements: FR-2, FR-6.

## Phase 3 — Home (4.5 h)

Slice 3a. Files: `assistant_feature.py` `register_tab`, new `console/static/assistant.js` (or extend existing), `app.js` / shell tab boot to sort when `document.documentElement.classList.contains("in-shell")`. Do not change Tauri init script unless a bug is found.

Tasks: 3-1-1 → 3-1-2. Requirements: FR-1.

## Phase 4 — Board and inspector (4.5 h)

Slice 4a. Files: `console/static/board.js` `startAgentFor`; `console/static/agents.js` list. Prefer POST to a Run/Assistant route over duplicating compose.

Tasks: 4-1-1, 4-1-2. Requirements: FR-3, FR-4.

## Phase 5 — Docs (1 h)

`knowledge-center/wiki/desktop-assistant.md`, `console/config/assistant.md`.

Task: 5-1-1. Requirement: FR-7.

## Build order

1-1-1 ∥ 1-1-2 ∥ 5-1-1 → 2-1-1 → (2-1-2 ∥ 2-1-3 ∥ 3-1-1) → 3-1-2 → (4-1-1 ∥ 4-1-2)

## Links
- [[T-016-requirements]] · [[T-016-plan]] · [[T-016-components]] · [[T-016-task-breakdown]] · [[T-016-implementation-plan]]
