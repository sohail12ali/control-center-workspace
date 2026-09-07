---
ticket: "T-004"
artifact: implementation-plan
---

# Implementation plan: T-004

Master build plan — synthesizes [[T-004-requirements]] (scope, 11 FRs, 9 BRs), [[T-004-plan]] (approach), [[T-004-components]] (12 components, dependency graph, 3-phase build order) and [[T-004-task-breakdown]] (41 atomic tasks) into one navigable document. Components and tasks are inputs, not duplicated here beyond what's needed for phase/slice narrative.

**Produced by:** `breakdown-tasks` (synthesis step). **Ready for:** `challenge-plan`.

## Ticket summary

T-004 makes the future voice assistant testable by typing, before any microphone exists: one reused "Assistant" chat, a console-owned persona injected per-backend, injected per-session context (tickets digest + memory + capabilities), a deterministic fast-command table, three new verbs (`kickoff`/`tickets_digest`/`remember`), a server-side Settings backend picker (service half — see below), file-based capped memory, a CLI parity command, and an honestly-always-unavailable `native_bridge.py` stub (T-005 builds the real bridge). 9 of the 12 components extend an already-proven in-repo pattern (plugin/route, session-create, verb-with-`needs_confirm`, prompt-budget `extra=`, CSRF-at-transport, gitignored `.cache` scratch dir, argparse subgroup); C5's fast-command normaliser/table has no in-repo analogue and carries T-004's remaining implementation risk.

**Amendment 2026-09-06 ([[T-004-decision-log]] § Amendment 2026-09-06):** C9 (reply path, `is_assistant` flag, `assistant.js`, FR-8 in full) is deferred in full to T-006 — the estimate's other novel/no-analogue risk concentration, now out of T-004's build. C7's UI half (Settings-tab picker, FR-7 AC2, task 3-7-3) is also deferred to T-006; C7's service half ships in T-004. Two new FR-6 tasks were added for observed defects (artifact-map `## Active` insertion point, rendered-template-encoding regression guard).

Total: **36 tasks, 40.5h Dev** ([[T-004-task-breakdown]] Effort summary; was 41 tasks/47.5h before the amendment). The prior 85.0h Final/Complete figure ([[T-004-effort-estimate]]) is stale pending a fresh `estimate(mode=forecast)` pass — not recomputed here to avoid fabricating a number.

## Dependency graph (from T-004-components.md, restated for build order)

```
C0 (audit ACTIONS) ──┬─> C2 (routes) ──┬─> C5 (fast-command table)
C1 (session/extra    │                  ├─> C7 (settings picker, service half)
     threading)  ─────┼─> C2 ────────────┴─> C11 (CLI)
     [BOTTLENECK]      │
                       ├─> C3 (persona)
                       └─> C4 (context) <── C6 (verbs) <── C0, C8
C8 (memory) ──┬─> C4
              └─> C6 ──> C4, C5
C10 (native_bridge) — isolated, any time

C9 (reply path/is_assistant) — DEFERRED IN FULL to T-006, amendment 2026-09-06
```

No circular dependencies (verified in `T-004-components.md`). C1 is the bottleneck: 7 of the other 11 components sit behind it, directly or transitively.

---

## Phase 1 — Roots (parallelizable)

Foundation plumbing with no dependencies on anything else in this ticket. C1 is the priority within this phase — everything in Phase 2 stalls until it lands.

### Slice 1 — C0: `audit.py` ACTIONS extension
Add the 5 new action names T-004 needs (`assistant.say`, `assistant.kickoff`, `assistant.remember`, `assistant.settings`, `assistant.persona_truncated`) before anything calls `audit.record` with them, plus a structural regression guard that T-004 never grows an 8th agent file.
- Tasks: 1-1-1, 1-1-2 (1h)
- Files: `console/server/audit.py`, `console/tests/test_notify_audit.py`, `console/tests/test_harness_lint.py`
- Satisfies: FR-1 AC3, FR-2 AC6, BR-2, BR-3

### Slice 2 — C1: `BaseSession` `system_append`/`extra` threading (bottleneck)
Six additive kwarg threads: `BaseSession` itself, `Backend.session_argv`, the two session-transport call sites (`LiveSession`/`TurnSession`), the `agents.toml` claude row, `ApiSession.start`'s `extra=` passthrough, and `agent_manager.create`'s cursor-agent first-turn-prepend path.
- Tasks: 1-2-1 … 1-2-6 (5.5h)
- Files: `console/server/agent_session.py`, `console/server/agent_backends.py`, `console/config/agents.toml`, `console/server/agent_api_session.py`, `console/server/agent_manager.py`
- Satisfies: FR-3 (all ACs), FR-4 AC1/AC3, decision-log `assistant-chat-identity-flag`

### Slice 9 — C8: file-based memory
`console/server/assistant.py`'s three data primitives: session pointer, capped fact store with the secret-shaped-fact guard, last-reply file. All under `console/.cache/assistant/` (already gitignored).
- Tasks: 1-9-1 … 1-9-3 (3h)
- Files: `console/server/assistant.py` (new), `console/tests/test_assistant.py` (new)
- Satisfies: FR-9 (all ACs), BR-4, decision-log `memory-location-and-caps`, `remember-secret-guard`

### Slice 11 — C10: `native_bridge.py` stub
Fully isolated leaf — build any time.
- Tasks: 1-11-1 (1h)
- Files: `console/server/native_bridge.py` (new), `console/tests/test_native_bridge.py` (new)
- Satisfies: FR-11 (all ACs)

**Phase 1 total: 12 tasks, 10.5h.**

---

## Phase 2 — depends only on Phase 1

### Slice 1 — C2: `assistant_feature.py` plugin + routes
The tenth `plugins.toml` row and the 5 routes (`say`/`session`/`new`/`stream`/`memory`), built on C0+C1.
- Tasks: 2-1-1 … 2-1-5 (7h)
- Files: `console/config/plugins.toml`, `console/server/features/assistant_feature.py` (new), `console/tests/test_plugins.py`, `console/tests/test_assistant.py`
- Satisfies: FR-1 (all ACs), FR-2 (all ACs), FR-9 (route surface), US-1, US-2

### Slice 3 — C3: persona + `persona_text` second root
`console/config/assistant.md` plus the second-root read path and the 4,000-char truncation/audit guard.
- Tasks: 2-3-1 … 2-3-3 (3h)
- Files: `console/config/assistant.md` (new), `console/server/prompt_build.py`, `console/tests/test_prompt_build.py`
- Satisfies: FR-3 AC6, BR-7, decision-log `persona-console-owned-second-root`

### Slice 6 — C6: new verbs (`kickoff`, `tickets_digest`, `remember`)
`kickoff.py` is the real work here (3 of the slice's 8h) — it must mirror the kickoff *skill*'s 3 steps via `New-FromTemplate.ps1`, never a thin `tickets.create` wrapper. **Amendment 2026-09-06:** 2 tasks added for defects observed this session — the artifact-map row must insert directly under `## Active`, never "after the last ticket-shaped row" (T-004's own row landed in `## Completed` under the old approach); and a regression guard for the `New-FromTemplate.ps1` double-encoding fix (BOM + mangled dashes under Windows PowerShell 5.1, already fixed and re-encoded this session).
- Tasks: 2-6-1 … 2-6-7 (8h)
- Files: `console/server/kickoff.py` (new), `console/config/verbs.toml`, `console/tests/test_kickoff.py` (new), `console/tests/test_verbs.py`
- Satisfies: FR-6 (all ACs, incl. the 2 added at amendment 2026-09-06), BR-5, BR-9

**Phase 2 total: 15 tasks, 18h.**

---

## Phase 3 — depends on Phase 2

### Slice 4 — C4: injected session context
Assembly-only: compose the 3 `extra` sections from C6/C8/C10/agents.toml within the existing `DEFAULT_BUDGET`.
- Tasks: 3-4-1 (2h)
- Files: `console/server/features/assistant_feature.py`, `console/tests/test_assistant.py`
- Satisfies: FR-4 (all ACs)

### Slice 5 — C5: fast-command dispatch table (novel — risk concentration #1)
Normaliser + the 11-row whole-utterance table + BR-1 regression + the PowerShell-fallback composition.
- Tasks: 3-5-1 … 3-5-4 (6h)
- Files: `console/server/features/assistant_feature.py` (or a new `assistant_dispatch` module if the table outgrows the feature file — builder's call, SIMPLIFY), `console/tests/test_assistant.py`
- Satisfies: FR-5 (all ACs), FR-2 AC5, FR-6 AC2, BR-1

### Slice 7 — C7: Settings backend picker (service half only)
`assistant.toml` defaults and the `GET`/`POST /api/assistant/settings` pair (notify.py/ops_feature.py-shaped). **Amendment 2026-09-06:** task 3-7-3 (Settings-tab UI picker in `console/static/settings.js`, FR-7 AC2) deferred to T-006 — verified via HTTP client in T-004, not the tab control.
- Tasks: 3-7-1, 3-7-2, 3-7-4 (3h)
- Files: `console/config/assistant.toml` (new), `console/server/features/assistant_feature.py`, `console/tests/test_assistant.py`
- Satisfies: FR-7 AC1/AC3/AC4/AC5/AC6, BR-8, decision-log `settings-backend-picker-local-first-default`

~~### Slice 8 — C9: reply path + `is_assistant` flag + `assistant.js` (novel — risk concentration #2)~~
**DEFERRED IN FULL to T-006, amendment 2026-09-06.** Server-side reply watcher, `spoken_form()`, speaker dispatch, the `agents.js` autoRead guard, and the new `assistant.js` widget all move to T-006 with FR-8 — speaking a reply and testing the double-speech guard only matter once voice exists. The `attention` SSE event type itself still ships in T-004 (Slice 1/C2's `stream` route, task 2-1-4); only the spoken-text watcher that would accompany it is deferred.

### Slice 10 — C11: `kanban.py assistant say` CLI
- Tasks: 3-10-1 (1h)
- Files: `console/kanban.py`, `console/tests/test_assistant.py`
- Satisfies: FR-10 (all ACs), BR-6

**Phase 3 total: 9 tasks, 12h.** (was 16 tasks/20h — Slice 8/C9 and task 3-7-3 deferred to T-006, amendment 2026-09-06)

---

## Effort reconciliation

**Post-amendment (2026-09-06):** implementation-plan phase totals (10.5 + 18 + 12 = **40.5h**) equal `T-004-task-breakdown.md`'s Effort summary total exactly — no drift. `T-004-effort-estimate.md`'s prior 85.0h Final/Complete figure (built on the pre-amendment 47.5h Dev) is now stale — flagged in that artifact's revision log, not recomputed here to avoid fabricating a number without re-running `estimate(mode=forecast)`.

**Pre-amendment history (for the record):** the original 47.5h Dev / 85.0h Final/Complete diverged materially from the source plan's pre-decomposition "M · 3 d" (24h) sizing. That divergence, concentrated in C5 and C9 (both novel, no in-repo analogue, ×1.8 QC penalty), is what prompted the user's descope decision — see [[T-004-decision-log]] § Amendment 2026-09-06.

## Acceptance criterion coverage

All FRs' remaining in-scope ACs and all 9 BRs trace to ≥1 task in `T-004-task-breakdown.md` (see that file's per-task Requirement/AC column). Summary by FR: FR-1→2-1-1..5, 1-1-1; FR-2→2-1-3, 1-1-2, 3-5-3; FR-3→1-2-1..6, 2-3-1..3; FR-4→3-4-1, 1-2-5; FR-5→3-5-1..2; FR-6→2-6-1..7 (incl. the 2 amendment tasks), 3-5-4; FR-7→3-7-1, 3-7-2, 3-7-4 (AC2/UI deferred to T-006); ~~FR-8→3-8-1..6~~ (deferred in full to T-006, amendment 2026-09-06 — no tasks in T-004); FR-9→1-9-1..3, 2-1-5, 2-6-4; FR-10→3-10-1; FR-11→1-11-1. Full bidirectional Requirement ↔ Task trace available via `validate-artifacts T-004 links`.

## Links
- [[T-004-summary]] · [[T-004-requirements]] · [[T-004-user-stories]] · [[T-004-plan]] · [[T-004-components]] · [[T-004-task-breakdown]] · [[T-004-effort-estimate]] · [[T-004-decision-log]] · [[T-004-progress]] · [[T-004-verification]]
