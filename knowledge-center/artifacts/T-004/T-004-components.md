---
ticket: "T-004"
artifact: components
---

# Components: T-004

Tracks every component this ticket touches, its dependencies, and its build status. Layers renamed from the template's data/service/UI to match what T-004 actually is: a plumbing/foundation layer, an HTTP+dispatch layer, and a config/frontend layer — no traditional DB migration exists in this ticket.

**Produced by:** `analyze-components` (which also builds the dependency graph below in the same pass). **Consumed by:** `breakdown-tasks` (tasks + implementation-plan synthesis).

---

## Foundation layer (plumbing + isolated stubs)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C0: audit.py ACTIONS extension | config/constant | Add `assistant.say`/`kickoff`/`remember`/settings-write action names before first use | none (root) | 1 | FR-1 AC3, BR-2 | done — `console/server/audit.py`; tests in `test_notify_audit.py`, `test_harness_lint.py` |
| C1: BaseSession `system_append`/`extra` threading | service/plumbing | Thread persona text + injected context through `agent_manager.create` → `agent_session.py`/`agent_api_session.py` → `Backend.session_argv` | none (root) | 2 | FR-3, FR-4 | done — `console/server/agent_session.py`, `agent_backends.py`, `console/config/agents.toml`, `agent_api_session.py`, `agent_manager.py`; tests in `test_api_session.py`, `test_agent_backends.py`, new `test_assistant.py` |
| C8: File-based memory | data/state | `session.json` pointer, capped `memory.md` (≤1,500, oldest-first trim), last-reply file under `console/.cache/assistant/` | none (root) | 9 | FR-9, BR-4 | done — `console/server/assistant.py`; tests in `test_assistant.py` |
| C10: `native_bridge.py` stub | module/stub | Always-unavailable honest stub (`available() → False, "shell not running"`) | none (isolated leaf — no deps in or out) | 11 | FR-11 | done — `console/server/native_bridge.py`; tests in `test_native_bridge.py` |

## HTTP + dispatch layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C2: `assistant_feature.py` plugin + routes | endpoint | `say`/`session`/`new`/`stream`/`memory` routes, tenth `plugins.toml` row, session pointer file | C0, C1 | 1 | FR-1 | done — `console/server/features/assistant_feature.py`, `console/config/plugins.toml`, additive `types=` filter on `agent_events.Stream.subscribe`/`agent_manager.subscribe`; tests in `test_plugins.py`, `test_assistant.py` |
| C6: New verbs (`kickoff`, `tickets_digest`, `remember`) | service/verb-handler | `kickoff` mirrors the kickoff skill's 3 steps via `New-FromTemplate.ps1`; `tickets_digest`/`remember` read/write memory | C0, C8 | 6 | FR-6, BR-5, BR-9 | done — `console/server/kickoff.py`, `console/server/context.py` (`tickets_digest`), `console/server/verb_handlers.py`, `console/config/verbs.toml`; tests in `test_kickoff.py`, `test_verbs.py` |
| C5: Fast-command dispatch table | service | Normalise → whole-utterance match (11 rows) → handler, else `agent_manager.send` | C2, C6 | 5 | FR-5, BR-1 | pending |

## Config + frontend layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C3: Persona + `persona_text` second root | config/plumbing | `console/config/assistant.md` (≤4,000 chars) + `prompt_build.py` second root; per-backend injection | C1 | 3 | FR-3, BR-3, BR-7 | done — `console/config/assistant.md`, `console/server/prompt_build.py`, `console/server/features/assistant_feature.py` (`_persona_kwargs`); tests in `test_prompt_build.py`, `test_assistant.py` |
| C4: Injected session context (`extra`) | service/composition | Compose `extra` = tickets digest (≤1,200) + memory (≤1,500) + capabilities line, within `DEFAULT_BUDGET` | C1, C6, C8 | 4 | FR-4 | pending |
| C7: Settings backend picker | config/endpoint | `assistant.toml` + `GET`/`POST /api/assistant/settings`, validated against enabled+installed backends. **Service half only — the Settings-tab UI control (FR-7 AC2) is deferred to T-006, amendment 2026-09-06.** | C0, C2 | 7 | FR-7, BR-8 | pending |
| C9: Reply path + `is_assistant` flag + `assistant.js` | service/UI | ~~Server-side watcher speaks `spoken_form()`; `is_assistant` guards `agents.js` autoRead; "Ask assistant" input box~~ **DEFERRED IN FULL to T-006, amendment 2026-09-06** — FR-8 moves out of T-004 entirely; speaking a reply only matters once voice exists | C1, C2 | 8 | FR-8 (deferred) | deferred |
| C11: `kanban.py assistant say` CLI | CLI subcommand | Same code path as `POST /api/assistant/say`, no bespoke CSRF bypass | C2 | 10 | FR-10, BR-6 | pending |

---

## Dependency graph

```
C0 (audit ACTIONS) ──┬─> C2 (assistant_feature.py routes) ──┬─> C5 (fast-command table)
C1 (session/extra    │                                       ├─> C7 (settings picker)
     threading) ──────┼─> C2 ─────────────────────────────────┼─> C9 (reply path/is_assistant)
     [BOTTLENECK]      │                                       └─> C11 (CLI)
                       ├─> C3 (persona, second root)
                       └─> C4 (injected context) <── C6 (verbs) <── C0, C8
C8 (memory) ──┬─> C4 (injected context)
              └─> C6 (verbs, remember) ──> C4, C5

C10 (native_bridge stub) — fully isolated, no in/out edges, can build any time in parallel
```

Root (no deps): C0, C1, C8, C10 (C10 additionally has nothing depending on it — isolated).
Leaf (nothing depends on them): C3, C4, C5, C7, C9, C10, C11.
Middle (has deps and is depended upon): C2, C6.

---

## Dependency graph analysis

- **Circular dependencies:** none — the graph is a clean DAG (verified by hand-tracing every edge; no back-edges).
- **Bottleneck: C1 (BaseSession `system_append`/`extra` threading).** Directly blocks C2, C3, C4, C9 (4 direct dependents); transitively blocks C5, C7, C9, C11 through C2 as well — 7 of the other 11 components sit behind this one plumbing change. This matches the task brief's flag exactly: it is what makes persona injection (C3), the context digest (C4), the settings picker mattering at all (C7, via C2's session-create reading `assistant.toml`), and the reply-path wiring (C9) all possible. Build this first and in isolation — it is small (additive kwargs through 3-4 files) but everything else stalls until it lands.
- **Critical path (longest chain, 3 components deep):** `C1 → C2 → {C5, C9}` — the bottleneck plumbing, then the HTTP surface, fanning out to the two components flagged as genuinely novel (no existing in-repo analogue beyond `telegram_bot._dispatch`'s structural shape for C5, and no analogue at all for C9's double-speech guard). An equally-long alternate chain, `C0 → C6 → C4`, is lower-risk (all three are pattern-reuse, not novel).
- **Zero-risk / pure pattern-reuse components** (per `analysis.md`'s Key Findings — extend an already-proven pattern): C0 (mirrors existing `ACTIONS` tuple additions), C2 (`verbs_feature.py`/`agents_feature.py` template), C6's `tickets_digest`/`remember` handlers (verb-with-`needs_confirm` pattern already gated in `verbs.py:145`), C7 (direct copy of `notify.py`/`ops_feature.py` prefs pattern), C8 (gitignored `.cache` scratch-dir pattern already exists), C10 (trivial stub), C11 (argparse subgroup pattern).
- **Novel / no existing analogue — the two real risk concentrations:** C5 (fast-command normaliser/table — closest analogue is `telegram_bot._dispatch`'s dispatch *shape*, but the natural-language whole-utterance matching and normalisation rule are net-new) and C9 (the `is_assistant` double-speech guard between the new server-side watcher and `agents.js`'s existing per-chat autoRead — no prior mechanism in the repo distinguishes "this chat" from "the assistant's own chat"). Plan/estimate effort here, not in the plumbing.
- **Safe build order** (topological, 3 phases):
  1. **Phase 1 — roots, build first, can parallelize:** C0 (audit ACTIONS), C1 (session/extra threading — the bottleneck, prioritize within this phase), C8 (memory), C10 (native_bridge stub — fully independent, assign anytime).
  2. **Phase 2 — depends only on Phase 1:** C2 (assistant_feature.py routes — needs C0, C1), C3 (persona — needs C1), C6 (new verbs — needs C0, C8).
  3. **Phase 3 — depends on Phase 2:** C4 (injected context — needs C1, C6, C8), C5 (fast-command table — needs C2, C6), C7 (settings picker, service half — needs C0, C2), C11 (CLI — needs C2). ~~C9 (reply path — needs C1, C2)~~ **deferred in full to T-006, amendment 2026-09-06.**

---

## Status summary

| Layer | Total | Pending | Deferred (T-006) | In-progress | Done |
|-------|------:|--------:|------------------:|------------:|-----:|
| Foundation | 4 | 4 | 0 | 0 | 0 |
| HTTP + dispatch | 3 | 3 | 0 | 0 | 0 |
| Config + frontend | 5 | 4 | 1 (C9) | 0 | 0 |
| **Total** | 12 | 11 | 1 | 0 | 0 |

C9 deferred in full to T-006 (amendment 2026-09-06); C7 stays "pending" but scoped to its service half only (FR-7 AC2's UI control also deferred).

## Links
- [[T-004-summary]] · [[T-004-requirements]] · [[T-004-user-stories]] · [[T-004-plan]] · [[T-004-components]] · [[T-004-task-breakdown]] · [[T-004-implementation-plan]] · [[T-004-decision-log]] · [[T-004-analysis]]
