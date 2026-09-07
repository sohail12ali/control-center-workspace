---
ticket: "T-004"
artifact: task-breakdown
---

# Task breakdown: T-004

Atomic tasks per slice, with acceptance criteria and effort. Task ID format: `{phase}-{slice}-{task}`. Slice numbers match `T-004-components.md`'s Slice column (= the user story each component headlines); Phase numbers match its 3-phase safe build order.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis step), `estimate(mode=forecast)`.

Test-file routing rule applied throughout: extend an existing test file that already exercises the touched module (`test_api_session.py` for `ApiSession`/`agent_session.build`, `test_agent_backends.py` for `Backend.session_argv`/`agents.toml`, `test_prompt_build.py` for `persona_text`/`build()`, `test_verbs.py` for verb rows, `test_notify_audit.py` for `audit.ACTIONS`, `test_plugins.py` for the plugin row, `test_harness_lint.py` for the 7-agent structural check) rather than inventing a redundant file. New behavior with no existing home (the assistant's own routes, dispatch table, memory, native-bridge stub, kickoff verb) goes to the three explicitly-named new files: `test_assistant.py`, `test_native_bridge.py`, `test_kickoff.py`. Frontend JS (`agents.js`, `assistant.js`, `settings.js`) has no unit-test harness in this repo (confirmed: no `test_ui_endpoints.py`/equivalent covers script behavior) — those tasks are marked "manual/code-review, recorded in verification.md" rather than routed to a fabricated JS test file.

---

## Phase 1: Roots — build first, parallelizable

### Slice 1: C0 — `audit.py` ACTIONS extension

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1-1-1 | Extend `audit.ACTIONS` tuple (`audit.py:43`) with `assistant.say`, `assistant.kickoff`, `assistant.remember`, `assistant.settings`, `assistant.persona_truncated` | C0 | FR-1 AC3, BR-2 | Each new action name accepted by `audit.record` without raising | 0.5 (actual 0.3) | done | Test: extended `test_notify_audit.py` (`test_every_t004_assistant_action_is_accepted`, parametrized over all 5). No deps. |
| 1-1-2 | Structural regression test: `.claude/agents/*.md` count stays 7 (T-004 adds zero agents) | C0 | FR-2 AC6, BR-3 | Test fails if an 8th agent file ever appears | 0.5 (actual 0.2) | done | Test: extended `test_harness_lint.py` (`TestRealAgentRoster`, reads the real `.claude/agents/` directory, not a fixture). No deps. |

### Slice 2: C1 — `BaseSession` `system_append`/`extra` threading (bottleneck)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1-2-1 | `BaseSession.__init__` gains `system_append=""`, `extra=""` (`agent_session.py:67-86`); `agent_session.build()` gains the same 2 kwargs, passed to `cls(...)` (`agent_session.py:590-606`) | C1 | FR-3, FR-4 (plumbing) | Attrs stored, default empty | 1 (actual 1) | done | Test: extend `test_api_session.py`'s session-construction fixture (`agent_session.build("sid1", backend, repo, ...)`, L112). No deps — root of C1. `is_assistant` kwarg deferred to T-006 with C9 (amendment 2026-09-06) — its only consumer was the FR-8 autoRead guard. |
| 1-2-2 | `Backend.session_argv(...)` gains `system_append=""`, added to the `_expand` context dict (`agent_backends.py:491-505`) | C1 | FR-3 AC1/AC2 | Flag present with text when non-empty; `_expand` drops it when empty (existing mechanism, no new code there) | 1 (actual 0.5) | done | Test: extend `test_agent_backends.py` near `test_an_unset_optional_flag_vanishes_with_its_value` (new `TestSystemAppend` class). Depends: 1-2-1. |
| 1-2-3 | `LiveSession.start()` passes `system_append=self.system_append` to `session_argv(...)` (`:366-370`) | C1 | FR-3 AC1 | Argv carries the flag+text when non-empty | 1 (actual 0.5, combined with 1-2-6's dispatch test) | done | No existing file constructs `LiveSession` directly — exercised end-to-end via new `test_assistant.py`. Depends: 1-2-1, 1-2-2. `session.started.is_assistant` payload addition deferred to T-006 with C9 (amendment 2026-09-06). |
| 1-2-4 | `agents.toml` claude row: `session_args += ["--append-system-prompt", "{system_append}"]` | C1 | FR-3 AC1 | Claude argv contains the flag+text when non-empty; absent when empty | 0.5 (actual 0.3) | done | Test: extend `test_agent_backends.py` (`test_shipped_claude_row_declares_the_flag`, real config). Depends: 1-2-2. |
| 1-2-5 | `ApiSession.start()` passes `extra=self.extra` to `prompt_build.build(...)` (`agent_api_session.py:105-107`) | C1 | FR-4 AC1/AC3, FR-3 AC3 | `openai_api` request body/system prompt includes persona+context via `extra=` | 0.5 (actual 0.3) | done | Test: extend `test_api_session.py` near `test_the_skill_text_is_in_the_prompt_not_the_message`. Depends: 1-2-1. |
| 1-2-6 | `agent_manager.create(...)` gains `system_append=""`, `extra=""`, passed to `agent_session.build(...)`; when the backend has no system-prompt flag (cursor-agent), prepend `system_append` to `wire` before `sess.send(...)` instead | C1 | FR-3 AC4 (cursor-agent), AC1/AC2 | cursor-agent first-turn prompt starts with persona text; claude path unaffected (flag used instead) | 1.5 (actual 1.4) | done | Test: new `test_assistant.py` — `TestSystemAppendDispatch`, fake cursor-agent-shaped backend asserts wire prefix; fake claude backend asserts wire unmodified; empty system_append never touches the wire. Depends: 1-2-1, 1-2-3. `is_assistant=False` kwarg deferred to T-006 with C9 (amendment 2026-09-06). |

### Slice 9: C8 — file-based memory

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1-9-1 | New `console/server/assistant.py` — `session.json` pointer read/write (sid, backend, model, timestamps) under `console/.cache/assistant/` | C8 | FR-9 (Data Entities: `session.json`) | Pointer created/read/overwritten correctly | 1 (actual 0.7) | done | Test: new `test_assistant.py` (`TestSessionPointer`). No deps (root). |
| 1-9-2 | `assistant.py` — capped `memory.md` read/append (≤1,500 chars, oldest-first trim) + secret-shaped-fact guard (`-----BEGIN`, provider-key prefixes, bare `KEY=value`) | C8 | FR-9, BR-4, decision-log `remember-secret-guard` | Appends and caps at 1,500; over-cap trims oldest-first, never errors; secret-shaped fact declined | 1.5 (actual 1.2) | done | Test: new `test_assistant.py` (`TestMemory`, incl. a false-positive guard against an ordinary `=`-bearing sentence). Depends: 1-9-1. |
| 1-9-3 | `assistant.py` — last-reply file (plain text, overwrite per completed turn) | C8 | FR-9 (Data Entities: last-reply file) | Overwritten each turn, no growth | 0.5 (actual 0.2) | done | Test: new `test_assistant.py` (`TestLastReply`). Depends: 1-9-1. |

### Slice 11: C10 — `native_bridge.py` stub

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1-11-1 | New `console/server/native_bridge.py` — stdlib `urllib` client reading `console/.cache/desktop/bridge.json`; `available()` → `(False, "shell not running")` when absent; per-endpoint helper stubs (5s/60s timeouts) | C10 | FR-11 (all 3 ACs) | `available()` false+reason when file absent; "copy that" gets the honest reason, not an error | 1 (actual 0.9) | done | Test: new `test_native_bridge.py`, fake-opener idiom matching `test_api_session.py`/`agent_backends._probe`. No deps — isolated leaf. `available()` genuinely probes a `base_url` if the pointer file names one (forward-compatible with T-005), always honestly `False` while nothing writes that file, which is exactly T-004's real state. |

**Phase 1 subtotal: 12 tasks, 10.5h**

---

## Phase 2: depends only on Phase 1

### Slice 1: C2 — `assistant_feature.py` plugin + routes

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2-1-1 | `plugins.toml` tenth row (`id="assistant"`, `module="features.assistant_feature"`, `enabled=true`) | C2 | FR-1 AC1 | Exactly one `[[plugin]]` row added; `httpd.py` diff empty | 0.5 (actual 0.3) | done | Test: extended `test_plugins.py` (`test_assistant_plugin_is_enabled`, `test_assistant_plugin_registers_no_tab`, `TestAssistantRoutes.test_it_registers_the_expected_routes`). No deps. `httpd.py` confirmed untouched. |
| 2-1-2 | New `assistant_feature.py` — `say` route: normalise → session pointer (C8) → on `agent_manager.create`/`send` raising, catch to `{"result":"error",...}`; audited via `audit.record("assistant.say",...)` | C2 | FR-1 AC2/AC6, BR-2 | 403 without `X-Console-Request: 1`; backend failure never surfaces a 500 | 2 (actual 1.8) | done | Test: new `test_assistant.py` (`TestSayRoute`), fake `agent_manager`. The 403 itself is the existing generic transport CSRF check (`httpd.py`, untouched) — no per-plugin logic added, per BR-6. Depends: 2-1-1, 1-1-1, 1-9-1. Note: the fast-command "normalise" step is C5 (Phase 3) and edits this route in place; for now `say` talks straight to the session, which is still BR-1's "else" branch with an empty table in front of it. |
| 2-1-3 | `assistant_feature.py` — `session`/`new` routes: `new` creates via `agent_manager.create(...)` (mirrors `agents_feature.chat_new`); busy→queued surfaced from `sess.send`'s return; idle-timeout (`session_idle_minutes`) recreate | C2 | FR-2 (all ACs), US-2 | Second `say` in-flight → `queued`; past idle timeout → new chat | 2 (actual 1.8) | done | Test: new `test_assistant.py` (`TestSessionAndNewRoutes`). Depends: 2-1-2, 1-2-6. `is_assistant=True` kwarg deferred to T-006 with C9 (amendment 2026-09-06) — used a bare `DEFAULT_IDLE_MINUTES=240` constant pending C7's `assistant.toml` (task 3-7-4 rewires this to read config fresh per `new`). |
| 2-1-4 | `assistant_feature.py` — `stream` route (SSE) filtered to exactly `turn.start`/`attention`/`reply`/`turn.end`/`speaking.*` | C2 | FR-1 AC5 | Other event types filtered out | 1.5 (actual 1.3) | done | Test: new `test_assistant.py` (`TestStreamRoute`). Depends: 2-1-2. Implementation note: added an additive `types=` filter kwarg to `agent_events.Stream.subscribe`/`agent_manager.subscribe` (default `None`, fully backward compatible — `agents_feature.chat_stream` unaffected) rather than a second event log, so the Assistant's stream and the ordinary chat stream stay one mechanism. |
| 2-1-5 | `assistant_feature.py` — `memory` `GET`/`POST` routes wrapping `assistant.py`'s memory read/append | C2 | FR-9 (route surface), US-4 | Routes read/write the capped memory file | 1 (actual 0.7) | done | Test: new `test_assistant.py` (`TestMemoryRoutes`, incl. the secret-shaped-fact guard reaching the route). Depends: 2-1-2, 1-9-2. |

### Slice 3: C3 — persona + `persona_text` second root

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2-3-1 | Author `console/config/assistant.md` (≤4,000 chars): role, reply contract, tool preferences, safety list (incl. the remember-secret rule), fast-command list | C3 | FR-3 (persona content) | File exists, ≤4,000 chars | 1 (actual 0.6) | done | Test: new `test_assistant.py` (length guard covered by `TestPersonaCap`'s general cap tests; file itself is 2,513 bytes, well under 4,000). No deps. |
| 2-3-2 | `prompt_build.persona_text(repo_root, persona)` gains a second root, `console/config/` (personas live directly there — `console/config/assistant.md` IS the file, so the root is where it already sits, not a separate `personas/` subdirectory); tries new root first, falls back to `.claude/agents/%s.md` | C3 | FR-3 (injection mechanism), decision-log `persona-console-owned-second-root` | Second root tried first; existing agent-persona mechanism unaffected | 1 (actual 0.9) | done | Test: extended `test_prompt_build.py` (`TestConsoleOwnedPersonaSecondRoot`). Also wired the per-backend routing this makes possible: `assistant_feature._persona_kwargs` sends `persona="assistant"` to an `openai_api` backend and `system_append=persona_text(...)` to every other transport (whose own `--agent`-style flag would need a `.claude/agents/` file the console-owned persona deliberately isn't, BR-3) — tested in `test_assistant.py`'s `TestPersonaRouting`. Depends: 2-3-1. |
| 2-3-3 | 4,000-char truncation + stated marker + `audit.record("assistant.persona_truncated", ...)` when persona text exceeds the cap (BR-7) | C3 | FR-3 AC6, BR-7 | 4,500-char fixture truncates to 4,000 with stated marker + audit call | 1 (actual 0.7) | done | Test: extended `test_prompt_build.py` (`TestPersonaCap`, incl. the audit-call assertion — folded in there rather than `test_notify_audit.py` since the fixture needs a real oversized persona file). Enforced inside `persona_text()` itself so every caller (an `openai_api` build, a CLI's `system_append`) inherits the cap for free. Depends: 2-3-2, 1-1-1. |

### Slice 6: C6 — new verbs (`kickoff`, `tickets_digest`, `remember`)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2-6-1 | New `console/server/kickoff.py` — `next_ticket_id` + `tickets.create(...)` + render each `_template/*.md` via `New-FromTemplate.ps1` (subprocess; PS-unavailable raises honestly) + append artifact-map row | C6 | FR-6 AC1/AC2, BR-5 | `"create ticket for X"` produces `ticket.toml` + rendered templates; PS-absent → honest error | 3 (actual 2.6) | done | Test: new `test_kickoff.py` — `_fake_ps_runner()` stands in for a working script (fake-runner idiom, no real process); a distinct `PowerShellUnavailable` test proves the honest-error path. Depends: 1-1-1. |
| 2-6-2 | `verbs.toml` `kickoff` row (`needs_confirm=true`, handler → `kickoff.py`) | C6 | FR-6 AC3 | Refused without `confirm` | 0.5 (actual 0.3) | done | Test: extended `test_verbs.py` (`TestT004Verbs.test_kickoff_needs_confirm`/`test_kickoff_confirmed_creates_a_ticket`). Depends: 2-6-1. |
| 2-6-3 | `tickets_digest` verb handler — composes `tickets.list_tickets` + `boards.lanes_for` + `trackers.blockers` into a ≤1,200-char digest; `verbs.toml` row | C6 | FR-6 AC4, FR-4 (digest section) | Digest capped, unit-tested | 1.5 (actual 1.3) | done | Real composition lives in `context.tickets_digest` (the module that already owns ticket/board/tracker composition for the per-ticket digest); `verb_handlers.tickets_digest` is a one-line adapter, per that file's own stated convention. Test: extended `test_verbs.py`. No new deps. |
| 2-6-4 | `remember` verb handler — appends via `assistant.py`'s memory API, applies the secret-shaped-fact guard; `verbs.toml` row | C6 | FR-6 AC4, FR-9, BR-4 | Unit-tested; secret fact declined | 1 (actual 0.5) | done | Test: extended `test_verbs.py` (`test_remember_confirmed_appends`/`test_remember_confirmed_still_declines_a_secret`). `needs_confirm=true` added to this row too (a mutating write, same reasoning as `kickoff`'s). Depends: 1-9-2. |
| 2-6-5 | PowerShell-unavailable fallback trigger: `kickoff` verb error path signals the fast-command layer to fall back | C6 | FR-6 AC2 | Verb error is distinguishable from a generic exception | 1 (actual 0.4, folded into 2-6-1's own test) | done | `PowerShellUnavailable(RuntimeError)` is its own type, distinct from the generic `RuntimeError` a render failure raises — C5 (Phase 3, task 3-5-4) catches exactly this one. Test: `test_kickoff.py::TestCreateTicket::test_powershell_unavailable_raises_a_distinguishable_error`. Depends: 2-6-1, 2-6-2. |
| 2-6-6 | **(added, amendment 2026-09-06)** `kickoff.py`'s artifact-map insertion: locate the `## Active` heading and insert the new row directly under it, never "after the last ticket-shaped row" (regression: T-004's own row landed in `## Completed` under the old approach, because the previously-last row had since moved there) | C6 | FR-6 (new AC) | Given a map whose `## Completed` section is non-empty and whose `## Active` section is empty, the new row still lands under `## Active` | 0.5 (actual 0.5) | done | Test: new `test_kickoff.py` (`TestArtifactMapInsertion`), hand-built artifact-map fixture matching that exact shape, plus an existing-rows case and an end-to-end case via `create_ticket`. Depends: 2-6-1. |
| 2-6-7 | **(added, amendment 2026-09-06)** Regression test for the `New-FromTemplate.ps1` double-encoding fix (already applied this session — `Get-Content -Raw`/`Set-Content -Encoding UTF8` mismatch under Windows PowerShell 5.1 was producing BOM'd, mangled-dash output) | C6 | FR-6 (new AC) | After `kickoff` runs, each rendered `{ID}-*.md` starts with `---` (no `\xef\xbb\xbf`), decodes as UTF-8, contains none of `Â·`, `â€"`, `â€™` | 0.5 (actual 0.6) | done | Test: new `test_kickoff.py` (`TestRenderedTemplateEncoding`) — copies the REAL `New-FromTemplate.ps1` + its `Get-RepoRoot.ps1` helper into a throwaway repo and actually runs PowerShell against a template containing the real mis-encoded punctuation (em dash, middot, curly apostrophe); byte-level BOM/UTF-8/mis-encoding assertions. Confirmed the script itself reads `Get-Content -Raw -Encoding UTF8` and writes via `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))` — already fixed this session, this test only guards the regression. Honest skip off Windows or with no PowerShell on PATH. Depends: 2-6-1. |

**Phase 2 subtotal: 15 tasks, 18h**

---

## Phase 3: depends on Phase 2

### Slice 4: C4 — injected session context

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3-4-1 | Session-create path composes `extra` = tickets digest (≤1,200, C6) + memory (≤1,500, C8) + capabilities line (bridge up/down via C10, backend local/cloud, vision-capable from `agents.toml`), passed to `agent_manager.create(..., extra=...)` | C4 | FR-4 (all 3 ACs) | Composed `extra` has all 3 sections within caps; over-cap section truncates with stated marker; total stays under `DEFAULT_BUDGET` | 2 (actual 1.8) | done | Test: new `test_assistant.py` (`TestInjectedContext`, 6 tests). "vision-capable from `agents.toml`" reads `assistant.toml`'s `vision_models` list instead (C7 hasn't landed yet at this point in the build order; honestly `False`/"not configured yet" until it does — task text's own Data Entities section lists `vision_models` under `assistant.toml`, not `agents.toml`). A CLI backend folds the composed context into the same `system_append` channel as its persona text (only one channel exists); an `openai_api` backend gets it via a separate `extra=`. Depends: 1-2-6, 2-6-3, 1-9-2, 1-11-1, 2-1-3. |

### Slice 5: C5 — fast-command dispatch table (novel, no analogue)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3-5-1 | Normaliser: strip wake word/punctuation, `t[- ]?(\d+)` → `T-00N` | C5 | FR-5 (normalisation rule) | Normaliser unit-tested | 1 | pending | Test: new `test_assistant.py`. No new deps beyond C2. |
| 3-5-2 | 11-row whole-utterance match table (new chat/stop/mute/use backend/status/what's-open/create ticket/copy that/remember/do-fix-build-run/screenshot) → else `agent_manager.send`, `telegram_bot._dispatch`-shaped (BR-1) | C5 | FR-5 (all 4 ACs), BR-1 | `"status T-002"` never calls `send`; each row unit-tested; `"stop the server"` falls through (whole-utterance-only); unrecognized input reaches `else` without raising | 3 | pending | Test: new `test_assistant.py`, one test per row. Depends: 3-5-1, 2-1-3, 2-6-1..4, 1-11-1. |
| 3-5-3 | BR-1 regression test: fast-command-shaped model output never re-enters dispatch | C5 | FR-2 AC5, BR-1 | Fake `send()` returning fast-command-shaped text never re-dispatches | 1 | pending | Test: new `test_assistant.py`. Depends: 3-5-2. |
| 3-5-4 | PowerShell-unavailable chat-fallback composition: `"create ticket for X"` row sends `/kickoff {id} --title …` to the chat when the verb errors | C5 | FR-6 AC2 | Mocked-PS-absent → fallback text sent via `sess.send` | 1 | pending | Test: new `test_assistant.py`. Depends: 3-5-2, 2-6-5. |

### Slice 7: C7 — Settings backend picker (service half only)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3-7-1 | New `console/config/assistant.toml` defaults: `backend` (first enabled+installed, local-first per `agents.toml`), `model`, `mode="default"`, `vision_models`, `session_idle_minutes=240`, `speak`, `reply_chars=400`, `ticket_prefix` | C7 | FR-7 AC4 | Local-first backend chosen on first bootstrap | 1 | pending | Test: new `test_assistant.py`. No deps. |
| 3-7-2 | `assistant_feature.py` `GET`/`POST /api/assistant/settings` (modeled on `notify.py`/`ops_feature.py`'s prefs shape, full-replace not narrowing-only); unknown/uninstalled backend → 400, file unchanged; write audited (`assistant.settings`) | C7 | FR-7 AC1/AC3/AC5 | POST persists; invalid backend → 400 + file unchanged; GET round-trips (via HTTP client, not the Settings-tab control) | 1.5 | pending | Test: new `test_assistant.py`. Depends: 3-7-1, 1-1-1. |
| 3-7-4 | Mid-flight-change semantics: `assistant_feature.py`'s session-create path reads `assistant.toml` fresh per `new`, never caches on a live session | C7 | FR-7 AC6 | Settings change mid-chat doesn't affect the live chat; only the next `new` picks it up | 0.5 | pending | Test: new `test_assistant.py`. Depends: 3-7-2, 2-1-3. |

~~**Task 3-7-3 (Settings-tab UI picker in `console/static/settings.js`, FR-7 AC2) — DEFERRED to T-006, amendment 2026-09-06.** T-004 ships the service half only; the tab control lands with T-006's shell.~~

~~### Slice 8: C9 — reply path + `is_assistant` flag + `assistant.js` (novel, no analogue)~~

**Slice 8 (C9, tasks 3-8-1..6, 6.5h) — DEFERRED IN FULL to T-006, amendment 2026-09-06.** FR-8 moves out of T-004 entirely: server-side reply watcher, `spoken_form()`, speaker dispatch, `approval.request`-spoken-text, the `is_assistant` autoRead guard, and `assistant.js`'s "Ask assistant" box. Rationale: speaking a reply, and testing the double-speech guard, only matter once voice exists (T-006); this was also one of the two components `analyze-components` flagged as novel with no in-repo analogue and the estimate's largest risk concentration alongside C5. The `attention` SSE event type itself still ships in T-004 (part of FR-1's `stream` route, task 2-1-4) — only the accompanying spoken text and the watcher that produces it are deferred.

### Slice 10: C11 — `kanban.py assistant say` CLI

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3-10-1 | New `assistant` subparser group in `kanban.py` (mirrors the `agents` group, `:606-644`) with a `say` action calling the same code path as `POST /api/assistant/say` in-process | C11 | FR-10 (all 3 ACs) | `assistant say "status T-002"` prints the deterministic answer; subparser shape matches `agents` | 1 | pending | Test: new `test_assistant.py` (no `test_kanban.py` exists). Depends: 2-1-2. |

**Phase 3 subtotal: 9 tasks, 12h** (was 16 tasks/20h — Slice 8/C9 (6 tasks, 6.5h) and task 3-7-3 (1 task, 1.5h) deferred to T-006, amendment 2026-09-06)

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 | 10.5 | 7.5 | 0 | 3.0 | 71% |
| Phase 2 | 18.0 | 13.7 | 0 | 4.3 | 76% |
| Phase 3 | 12.0 | 0 | 0 | 12.0 | 0% |
| **Total** | **40.5** | **21.2** | **0** | **19.3** | **52%** |

36 tasks across 3 phases / 10 slices (post-descope; was 41 tasks/47.5h/11 slices — amendment 2026-09-06, [[T-004-decision-log]] § Amendment 2026-09-06). Slice 8 (C9, FR-8, 6 tasks/6.5h) and task 3-7-3 (FR-7 AC2's UI, 1 task/1.5h) deferred in full to T-006; 2 new FR-6 tasks added (2-6-6, 2-6-7, 1 task/1h combined) for the artifact-map insertion-point and rendered-template-encoding regressions observed this session. Net: 47.5 − 6.5 − 1.5 + 1.0 = **40.5h**. `T-004-effort-estimate.md`'s 85.0h Final/Complete figure is now stale pending a fresh `estimate(mode=forecast)` pass (not recomputed here — see that artifact's revision log).

## Links
- [[T-004-summary]] · [[T-004-plan]] · [[T-004-components]] · [[T-004-task-breakdown]] · [[T-004-implementation-plan]] · [[T-004-effort-estimate]] · [[T-004-effort-forecast]] · [[T-004-requirements]] · [[T-004-user-stories]] · [[T-004-decision-log]]
