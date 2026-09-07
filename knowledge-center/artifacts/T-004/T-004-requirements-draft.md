---
ticket: "T-004"
artifact: requirements-draft
status: frozen
freeze_status: frozen
frozen_at: "2026-09-06"
frozen_iteration: 0
iteration: 0
created: "2026-09-06"
last_updated: "2026-09-06"
---

# Requirements Draft: T-004

> **FROZEN** at iteration 0, 2026-09-06. See [[T-004-requirements]] for the canonical finalized artifact consumed by planning. This draft is retained as the working history; further changes must go through `evolve`, never a silent rewrite.

**Command reference:**
- **Created by:** `requirements T-004 draft`
- **Grounded by:** `analyze T-004` → writes `T-004-context-snapshot.md`
- **Gaps surfaced by:** `challenge-requirements T-004 (gaps dimension)`
- **Challenged by:** `challenge-requirements T-004` (adds ⚠ markers below)
- **Enriched by:** `requirements T-004 enrich [source]`
- **Cross-checked by:** `challenge-requirements T-004 (overlap/conflict/reuse dimension)`
- **Iterated by:** `requirements T-004 iterate "feedback"`
- **Frozen by:** `requirements T-004 freeze` → produces `T-004-requirements-summary.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Sohail Ali wants the future voice assistant testable by typing today — persona, dispatch, memory, and a backend picker — with no microphone and no native bridge required yet.

**Business driver:** T-005 (native bridge) and T-006 (voice/mic) carry the highest architectural risk in the desktop-assistant programme; proving the brain (session model, persona injection, fast-command dispatch, memory) via ordinary typed chat first de-risks that work before audio exists, and unblocks T-005/T-006 which both depend on T-004 (plan programme table, plan.md:83-85).

**Raw intent verbatim:**
> "T-004 — Assistant brain: persona, `/api/assistant`, fast commands, Settings backend picker, memory (typed, no mic)" — plan.md:83 (programme table), expanded at plan.md § "T-004 — Assistant brain (typed first, voice later)", lines 143-182.

## 2. Context Summary

(Condensed from [[T-004-context-snapshot]])

- **Similar existing features:** [[T-004-context-snapshot|verb registry]] (`console/config/verbs.toml` → `verbs.py` → `verb_handlers.py`, context-snapshot.md:36) · live agent chat lifecycle (`agent_manager.create/send/interrupt`, context-snapshot.md:37) · inbound dispatch shape (`telegram_bot.py:_dispatch`, context-snapshot.md:38) · budgeted prompt assembly (`prompt_build.py`, context-snapshot.md:39) · committed-config + HTTP settings pattern (`notify.py`/`ops_feature.py`, context-snapshot.md:40) · per-chat autoRead (`agents.js:839-846`, context-snapshot.md:41) · kickoff artifact scaffolding (`kickoff` skill + `New-FromTemplate.ps1`, context-snapshot.md:42).
- **Affected code areas:** `console/server/features/` (new `assistant_feature.py`), `console/server/` (new `assistant.py`, `native_bridge.py`, `kickoff.py`; modified `prompt_build.py`, `agent_backends.py`, `agent_session.py`, `agent_manager.py`, `agent_api_session.py`, `audit.py`), `console/config/` (new `assistant.md`, `assistant.toml`; modified `plugins.toml`, `verbs.toml`, `agents.toml`), `console/static/` (new `assistant.js`; modified `agents.js:841`, `index.html`), `console/kanban.py` (new `assistant` subparser group) — full file list at analysis.md:326-348 and plan.md:179.
- **Known risks from history:** T-001/T-002 shell↔server IPC is `eval`/DOM-event only, no Tauri commands yet (relevant only if T-004 code assumed shell access, which it does not — native bridge stays a stub) — context-snapshot.md:62; T-003 is fully **Complete/closed** (pytest 758→783 passed), so the stated dependency is satisfied in substance, not merely "artifacts present" — context-snapshot.md:64.

## 3. Scope

### In scope
- `assistant_feature.py` plugin + `plugins.toml` row + routes: `say`/`session`/`new`/`stream`/`memory` (plan.md:145).
- Session model: one reused "Assistant" chat, pointer file, busy→queued semantics, no second orchestrator (plan.md:147).
- Console-owned persona (`assistant.md`) injected per-backend, including the cursor-agent prepend path (plan.md:149-151).
- Injected `extra` context per new session: tickets digest, memory, capabilities line, stated budget (plan.md:152).
- Deterministic fast-command table: normalise → whole-utterance match → handler, else send (plan.md:154-169).
- Three new verbs: `kickoff`, `tickets_digest`, `remember` (plan.md:171).
- Settings backend picker, server-side (`assistant.toml` + a settings route) — plan names the picker but not its route; closed as its own FR per analysis.md:254-262.
- Reply path: server-side reply watcher, `spoken_form()`, native-bridge-else-webview speak, double-speech guard, `attention` on approval (plan.md:175).
- File-based memory under `console/.cache/assistant/`, capped, gitignored, no vault writes (plan.md:177).
- CLI: `kanban.py assistant say "…"` (plan.md:145, 179).
- `native_bridge.py` stub: always-unavailable, honest reason (plan.md:179, 199-200; analysis.md:194-200).

### Out of scope (explicit)
- T-005 native bridge real implementation — tray states, screenshot/OCR/clipboard/TTS over the bridge — deferred; T-004 ships only the always-unavailable stub (plan.md:185, programme table plan.md:84).
- T-006 voice/mic capture, VAD, hotkey, listen modes — deferred; T-004 is typed-only (plan.md:234-249, programme table plan.md:85).
- T-007 multimodal `/send` (image parts, region crop) — deferred (plan.md:253-255, programme table plan.md:86).
- Telegram routing of `/api/assistant/say` behind `telegram_bot._dispatch` — listed under "Suggestions beyond the ask," explicitly "not required for this ticket's ACs" (plan.md:263; context-snapshot.md:79).
- Tray icon states / listening-mode icons — T-005's `tray_state.rs` (plan.md:205-222).
- OS actuation (UIA invoke/click, app launch) — backlog T-009 (plan.md:267, 269-274).
- An 8th "assistant" agent under `.claude/agents/` — explicitly rejected; the assistant is a chat + dispatch table (CLAUDE.md "Exactly 7 agents"; analysis.md:230-232).

### Assumptions
- T-003's dependency is satisfied: it is closed (status Complete, pytest 758→783 passed) — context-snapshot.md:64. No re-verification needed here.
- The Windows dev machine has PowerShell 5.1 available for the `kickoff` verb's template render in the common case; the honest-fallback path (FR-6) covers its absence — plan.md:171.
- `console/config/personas/` (persona_text's second root) holds one file (`assistant.md`) for T-004; it is a directory so future non-CLI personas could be added later without another `prompt_build.py` change — context-snapshot.md:97 (Open Confirmation, not blocking).
- `httpd.py`, `console/static/app.js`, and `.claude/agents/` are untouched by this ticket, per the plan's explicit list (plan.md:179).

## 4. Functional Requirements

Number each `FR-{n}`. Each must be independently verifiable.

### FR-1: `assistant_feature.py` plugin + routes
**Description:** A new plugin module `console/server/features/assistant_feature.py`, registered as a tenth row in `console/config/plugins.toml`, exposes `POST /api/assistant/say`, `GET /api/assistant/session`, `POST /api/assistant/new`, `GET /api/assistant/stream`, and `GET`/`POST /api/assistant/memory`, following the existing plugin contract (module + `plugins.toml` row; `httpd.py` untouched).

**Actor:** Any HTTP caller — the future `assistant.js` palette box, `kanban.py assistant say` (FR-10), and (in T-005) the Rust bridge.

**Trigger:** An HTTP request to any `/api/assistant/*` route.

**Preconditions:**
- `plugins.toml` has `[[plugin]] id = "assistant" module = "features.assistant_feature" enabled = true` (plan.md:145; pattern: `plugins.toml:22-86`).
- Server running via `python console/kanban.py serve`.

**Flow:**
1. Route dispatch via `ctx.get`/`ctx.post`, mirroring `verbs_feature.py:1-102`.
2. `say` first checks the fast-command table (FR-5); on no match, falls through to `agent_manager.send` against the Assistant session (FR-2).
3. Every mutating call (`say`, `new`, `memory` POST) is wrapped in `audit.record(...)`, success and failure both (`verbs_feature.py:34-46`).

**Postconditions / observable outcomes:**
- `say` responds `{chat, result: handled|sent|queued|error, spoken, reply?}` — `error` is a new fourth variant (see Edge Cases §8 "`say` backend-failure result") added at enrich to close a documented gap (plan.md:145 named only `handled|sent|queued`; no AC covered `agent_manager.create`/`send` itself raising).
- `GET /api/assistant/stream` is an SSE stream filtered to exactly five event names (plan.md:145): `turn.start`, `turn.end` (both already published today, unchanged shape — `agent_session.py:381-385`), and three net-new types with no existing publish call site (confirmed by grep of `agent_events.py`/`agent_session.py`/`agent_api_session.py`/`agent_normalize.py`/`agent_approvals.py`): `attention` (`{type:"attention", reason:"approval"|"error", text}` — emitted by FR-8's reply watcher on `approval.request`), `reply` (`{type:"reply", text, spoken}` — emitted alongside `turn.end` carrying `spoken_form()`'s output for `assistant.js` to speak without re-deriving it), `speaking.*` (`speaking.start`/`speaking.stop`, `{type:"speaking.start"|"speaking.stop"}` — emitted by `assistant.js` client-side around its `ConsoleVoice.speak` call, relayed to the stream via `POST /api/assistant/memory`'s sibling route or a small speaking-state field on `GET /api/assistant/session`; exact relay path is a builder wiring decision, not a new route, since no additional POST route is named in plan.md:145). See §6 Data Requirements for the per-event field table.

**Acceptance criteria (testable):**
- [ ] `plugins.toml` diff adds exactly one `[[plugin]]` row; `git diff` on `httpd.py` is empty (plan.md:179).
- [ ] `POST /api/assistant/say` without `X-Console-Request: 1` returns 403, with no bespoke CSRF code in `assistant_feature.py` (`httpd.py:181-182`; BR-6).
- [ ] `audit.py`'s `ACTIONS` tuple is extended with `assistant.say` and any other new mutating actions before they are recorded (`audit.py:43-54`, currently absent).
- [ ] Each route has a unit test using a fake `agent_manager` (no live backend), asserting the documented response shape.
- [ ] `GET /api/assistant/stream` (pytest, fake session emitting each of the 5 event names) yields only `turn.start`/`attention`/`reply`/`turn.end`/`speaking.*` frames — any other event type on the underlying `sess.stream` is filtered out, not forwarded.
- [ ] When `agent_manager.create`/`send` raises (backend fails to spawn, cloud network error), `say` returns `{chat: "", result: "error", spoken: "<stated reason>", reply: null}` with HTTP 400 for a malformed request body and HTTP 200-with-`result:"error"` for a downstream backend failure — never an unhandled 500/stack trace to the caller (pytest, fake manager raising `ValueError`/`RuntimeError`).

**Business rules invoked:** BR-1, BR-2, BR-6

### FR-2: Session model — one reused Assistant chat
**Description:** The system maintains exactly one "Assistant" chat per running server process. A pointer file (`console/.cache/assistant/session.json`) tracks its chat id; a new `say` reuses the live chat if alive and used within `session_idle_minutes` (240), otherwise creates a fresh one via `agent_manager.create`.

**Actor:** `assistant_feature.py` (server-side), on behalf of any caller.

**Trigger:** Any `say`/`new` call.

**Preconditions:**
- `agent_manager.create`/`send`/`get`/`require` exist and are unchanged in shape (`agent_manager.py:41-101,179-193`).

**Flow:**
1. Read `console/.cache/assistant/session.json`; if it names a live, non-idle chat, reuse it.
2. Else call `agent_manager.create(...)` + `audit.record("chat.start", ...)` (pattern: `agents_feature.py:100-123`), write the new pointer.
3. `sess.send(...)`; if the session is busy, compose `result: "queued"`, `spoken: "Still working — queued"` from `sess.send`'s return value (the manager itself has no busy/queued branching — analysis.md:57-59).

**Postconditions / observable outcomes:**
- The Assistant chat is an ordinary chat, visible in the Agents tab; approvals on it are answered there like any other chat (plan.md:147).
- **BR-1** holds: `say` is exactly one fast-command match OR one `send`, never both, and no output is inspected to pick a next action.

**Acceptance criteria (testable):**
- [ ] A second `say` while the first turn is in flight reuses the same chat id and returns `result: "queued"` (pytest, fake manager) — plan.md:181.
- [ ] After `session_idle_minutes` elapses, the next `say` creates a new chat, not the stale one (pytest, monkeypatched clock).
- [ ] The Assistant chat is listed by the ordinary Agents-tab chat list (no filtering/hiding) — manual or existing-endpoint assertion.
- [ ] Code review: the fast-command handler contains exactly one branch point (match → handler, else → `send`); no code path inspects a model reply to decide what to do next.
- [ ] **Regression test for BR-1** (closes BR-GAP-2): a fake `agent_manager` whose `send()` returns text shaped like a fast-command match (e.g. the literal string `"status T-002"`) is asserted, via a second `say` call against that reply, to never re-enter the fast-command dispatcher — the dispatcher runs exactly once per inbound `say` call, on the caller's raw text only, never on a prior turn's model output (pytest).
- [ ] **Structural test for BR-3** (closes BR-GAP-1): a pytest asserts `len(glob.glob(".claude/agents/*.md")) == 7` post-diff — the same count confirmed at GROUND (analysis.md's roster note) — so a future accidental 8th agent file fails CI, mirroring FR-9's diff-grep pattern for BR-4.

**Business rules invoked:** BR-1, BR-3

### FR-3: Console-owned persona injected per backend
**Description:** `console/config/assistant.md` (≤4,000 chars) is the assistant's persona text. `prompt_build.persona_text` gains a second root, `console/config/personas/`, so this file is found and combined with the existing `.claude/agents/%s.md` mechanism. The persona is injected per-backend: `stream_json` (claude) via `--append-system-prompt`, `openai_api` (ollama/lm-studio/openrouter) via `prompt_build.build`'s existing `extra=` passthrough, and `cursor-agent` via prepending the persona text to the first turn's prompt (no system-prompt flag exists for it).

**Actor:** `assistant_feature.py` at session-create time; `prompt_build.py`/`agent_backends.py`/`agent_session.py` at session-start time.

**Trigger:** Assistant session creation (FR-2).

**Preconditions:**
- `prompt_build.persona_text` currently reads only `.claude/agents/%s.md` (`prompt_build.py:56-60`) — second root is net-new.
- `agent_backends.Backend.session_argv` has no `system_append` parameter today (`agent_backends.py:491-505`); `agents.toml`'s claude row has no `--append-system-prompt` entry (`agents.toml:52-63`).
- `_expand` already drops any flag whose placeholder resolves empty (`agent_backends.py:205-239, 213-219, 233-237`) — reused as-is, no new logic there.

**Flow:**
1. `assistant_feature.py` reads `console/config/assistant.md`; if its length exceeds 4,000 chars, it is truncated to 4,000 chars before use — same "truncate + stated marker, never silent" pattern `prompt_build.build` already applies (`prompt_build.py:137-150`: cut text gets an appended `_[This section was cut here...]_` marker and a `report["truncated"]` entry). The truncation (if any) is recorded via `audit.record("assistant.persona_truncated", ...)` so it is visible in the audit log, not merely a code comment. The resulting `system_append` value threaded into claude's argv is asserted ≤8,000 chars (BR-7) — enforced by this same truncation, not a separate argv-length check, since 4,000 persona chars plus the fixed `--append-system-prompt` flag text is always well under 8,000.
2. `assistant_feature.py` threads `system_append` through `BaseSession.__init__` → `LiveSession`'s call to `session_argv` (`agent_session.py:368-370`).
3. `agents.toml` claude row gains `session_args += ["--append-system-prompt", "{system_append}"]`.
4. `ApiSession.start` passes `extra=` through to `prompt_build.build` (`agent_api_session.py:103-108`, currently no `extra=` passed).
5. For cursor-agent, the persona text is prepended to the composed first-turn prompt (a call-site change, not a config row — `agents.toml:143-179` confirmed no system-prompt flag exists).

**Postconditions / observable outcomes:**
- Every backend's first turn carries the persona, via the mechanism appropriate to its transport.
- `assistant.md`'s ≤4,000-char cap is enforced at read time (step 1 above), not merely documented — closes EDGE-GAP-1.

**Acceptance criteria (testable):**
- [ ] Claude session argv contains `--append-system-prompt` followed by the persona text when `assistant.md` is non-empty (pytest on `session_argv`) — plan.md:181.
- [ ] Claude session argv omits the flag entirely when persona text is empty (pytest on `_expand`'s existing empty-drop behavior) — BR-7, Edge Cases.
- [ ] `openai_api` backends' request body includes the persona inside the `extra=`-derived prompt section (pytest, fake HTTP opener per `test_api_session.py`).
- [ ] cursor-agent's first-turn prompt string starts with the persona text (pytest on the compose call site).
- [ ] `agent_api_session.py`/`agent_session.py` diffs touch only the `system_append`/`extra` threading, nothing else (diff review — plan.md:181).
- [ ] **Closes EDGE-GAP-1:** a 4,500-char `assistant.md` fixture is read, truncated to exactly 4,000 chars with a stated marker (pytest, mirroring `prompt_build.py:137-141`'s existing truncation test shape), and `audit.record("assistant.persona_truncated", ...)` is called — never a silent cut, never a raised exception.

**Business rules invoked:** BR-7

### FR-4: Injected context per new session
**Description:** Each new Assistant session's `extra` prompt section carries an open-tickets digest (≤1,200 chars), the memory file (≤1,500 chars), and a one-line capabilities summary (bridge up/down, backend local/cloud, vision-capable), composed within `prompt_build.py`'s existing `DEFAULT_BUDGET` (24,000 chars) accounting.

**Actor:** `assistant_feature.py` (composes `extra`) at session-create time.

**Trigger:** New Assistant session creation (FR-2, no pointer or expired pointer).

**Preconditions:**
- `prompt_build.build`'s `extra` parameter already exists and is budget-accounted (`prompt_build.py:100-101,119-120`); no change needed inside `prompt_build.py` itself.
- Tickets digest is sourced from `tickets.list_tickets` + `boards.lanes_for` + `trackers.blockers` (plan.md:152) — the same data the `tickets_digest` verb (FR-6) exposes.

**Flow:**
1. On session create, gather digest + memory + capabilities line.
2. Concatenate as one `extra` string, pass to `agent_manager.create` → `prompt_build.build(..., extra=...)`.
3. Total budget stays ≈9.7k of the 24k default (plan.md:152); if any section would be truncated, `prompt_build.py`'s existing truncation-honesty behavior applies (stated, not silent).

**Postconditions / observable outcomes:**
- New sessions can answer "what's open" or ticket-status questions without an extra tool round-trip, and know whether native/cloud capabilities are available.

**Acceptance criteria (testable):**
- [ ] A new session's composed `extra` string contains a tickets-digest section ≤1,200 chars, a memory section ≤1,500 chars, and a one-line capabilities string (pytest, string-length assertions on the composed `extra`).
- [ ] If a section would exceed its cap, it is truncated with a stated marker, not silently cut (pytest against `prompt_build.py`'s existing truncation behavior).
- [ ] Total prompt length assertion stays under `DEFAULT_BUDGET` (pytest).

**Business rules invoked:** BR-4

### FR-5: Deterministic fast-command table
**Description:** Before any model call, `say`'s input text is normalised (strip wake word/punctuation; `t[- ]?(\d+)` → `T-00N`) and matched whole-utterance against a fixed table (plan.md:154-169: `new chat`/`start over`, `stop`/`cancel`/`interrupt`, `mute`/`unmute`, `use {backend}`, `status (of) T-00N`, `what's open`/`standup`, `create ticket (for) {title}`, `copy that`/`put the last reply on the clipboard`, `remember {fact}`, `do|fix|build|run {rest}`, `screenshot (of X)`, else → `agent_manager.send`).

**Actor:** `assistant_feature.py`'s dispatch function.

**Trigger:** Every `say` call.

**Preconditions:**
- No existing normalisation helper for wake-word-strip or ticket-id normalisation exists in the repo (analysis.md:116-119, net-new).
- `telegram_bot.py:_dispatch` (`:295-378`) is the structural template: one `dict.get`/regex lookup, one fallback (analysis.md:105-115).

**Flow:**
1. Normalise input text.
2. Attempt whole-utterance match against each named row, in the order given (plan.md's table).
3. On match, call the row's action (a verb, `agent_manager.interrupt`, a pref write, `compose_prompt`, etc.) and return without ever calling `agent_manager.send`.
4. On no match, `agent_manager.send` the raw (or normalised) text.

**Postconditions / observable outcomes:**
- "status T-002" never triggers a model call; it is answered purely by `verbs.run("context", ticket)` (plan.md:162, 181).

**Acceptance criteria (testable):**
- [ ] `say "status T-002"` returns lane/stage data with zero calls into `agent_manager.send` (pytest, fake manager asserting `send` not called) — plan.md:181.
- [ ] Each named row in the table has its own unit test (11 rows minimum, per plan.md:158-169).
- [ ] "stop the server" (a whole-utterance non-match for the `stop` row, which only matches exact "stop"/"cancel"/"interrupt") falls through to `send`, not to `interrupt` — confirms whole-utterance-only matching (plan.md:154, "so 'stop the server' is not an interrupt").
- [ ] An unrecognized or partially-matched utterance never raises; it reaches the `else` branch (Edge Cases; mirrors `telegram_bot.py`'s one-bad-input-doesn't-kill-the-loop pattern).

**Business rules invoked:** BR-1

### FR-6: New verbs — `kickoff`, `tickets_digest`, `remember`
**Description:** Three new rows in `console/config/verbs.toml` with handlers in `console/server/kickoff.py` (and existing verb-handler module for the other two). `kickoff` computes `next_ticket_id`, calls `tickets.create` (writes `ticket.toml` + trackers), renders every `_template/*.md` file via the existing `New-FromTemplate.ps1` (never a Python port), and appends the artifact-map row — mirroring the `kickoff` skill's steps, not merely wrapping `tickets.create`.

**Actor:** Fast-command handler (`create ticket for X`) or direct verb invocation.

**Trigger:** `create ticket (for) {title}` fast command, or `verbs.run("kickoff", ...)`.

**Preconditions:**
- `verbs.py:145` already enforces `needs_confirm` at dispatch — `kickoff` is registered `needs_confirm = true` (context-snapshot.md:36; verbs.toml's own comment states the first mutating verb sets this).
- `tickets.create` (`tickets.py:38-73`) does **not** render templates or touch `artifact-map.md` on its own (analysis.md:135-147) — the verb handler must do both extra steps itself, calling the same PS1 script the `kickoff` skill uses.
- `New-FromTemplate.ps1`'s PS 5.1 fixes (`:65,88`) are already in place (analysis.md:148-151).

**Flow:**
1. `kickoff` verb: compute next ticket id → `tickets.create` → for each `_template/*.md`, invoke `New-FromTemplate.ps1` → append artifact-map row.
2. If PowerShell is unavailable, the verb call fails with a clear error (no partial ticket dir silently left with only `ticket.toml`); the fast command instead sends `/kickoff {id} --title …` to the chat as an honest fallback (plan.md:171). **Framing note (closes EDGE-GAP-2):** the platform strategy's Build-prerequisites row (plan.md:74) lists MSVC/Xcode CLT/apt packages per OS with no `pwsh` entry for macOS/Linux — so on 2 of the 3 target OSes, this fallback branch is the *routine* path for `create ticket for X`, not a rare failure; on Windows (where PS 5.1 ships by default) the render branch is routine instead. Both branches already have their own AC below; this is a labeling correction, no new AC.
3. `tickets_digest` verb: read open tickets + lanes + blockers, return the same digest FR-4 injects.
4. `remember` verb: append the given fact to `console/.cache/assistant/memory.md`, respecting the 1,500-char cap (FR-9).

**Postconditions / observable outcomes:**
- `say "create ticket for X"` produces a ticket dir with rendered `.md` artifacts and an artifact-map row, not just `ticket.toml` (plan.md:181, the ticket's own stated AC).

**Acceptance criteria (testable):**
- [ ] `say "create ticket for X"` produces `ticket.toml` **and** rendered `_template/*.md` artifacts, verified via the CLI path in a pytest (plan.md:181).
- [ ] With PowerShell mocked unavailable, the `kickoff` verb returns an error (not a partial success), and the fast-command handler sends `/kickoff {id} --title …` to the chat instead (pytest, Edge Cases).
- [ ] `kickoff` verb row has `needs_confirm = true` and is refused without `confirm` (pytest against `verbs.py:145`'s existing gate).
- [ ] `tickets_digest` and `remember` verbs each have a unit test for their documented behavior.

**Business rules invoked:** BR-5

### FR-7: Settings backend picker — server-side
**Description:** A new committed `console/config/assistant.toml` holds the assistant's default backend/model/mode plus `vision_models`, `session_idle_minutes`, `speak`, `reply_chars` (400), `ticket_prefix` (plan.md:173). A new `GET`/`POST /api/assistant/settings` route (modeled on `notify.py`'s `load_prefs`/`apply_prefs` + `ops_feature.py`'s `POST /api/notify/prefs`, since every other Settings panel is browser-`localStorage`-only and cannot drive a server-spawned session) reads/writes this file. The Settings tab gains a corresponding picker row. This route is not named in the plan's explicit list (`say`/`session`/`new`/`stream`/`memory`) — flagged in analysis.md:254-262 as a real gap; closed here as its own FR with a testable AC, per this ticket's instruction.

**Actor:** User via the Settings tab; `assistant_feature.py`/`assistant.py` server-side on read.

**Trigger:** User opens Settings → Assistant backend picker; saves a change. Or: any server-spawned Assistant session reads the current default at create time.

**Preconditions:**
- Every existing Settings panel except Telegram prefs is `localStorage`-only (`settings.js`; analysis.md:152-163) — insufficient here because a headless `kanban.py assistant say` invocation has no browser.
- `notify.py:61-102` / `ops_feature.py:78-89` is the directly reusable committed-config + HTTP read/write shape (context-snapshot.md:40).

**Flow:**
1. `GET /api/assistant/settings` returns the current `assistant.toml` contents.
2. `POST /api/assistant/settings` validates and writes back (audited). **Validation rule (closes BR-GAP-3):** a submitted `backend` value must name a backend that is both installed and enabled per `agent_backends.get(...).installed` (the same check `agent_manager.create` already runs and raises on, `agent_manager.py:44-51`) — an unknown/uninstalled backend is rejected with 400 and never persisted, so `assistant.toml` can never hold a backend the system cannot actually spawn.
3. `agent_manager.create` (FR-2) reads `assistant.toml`'s `backend`/`model`/`mode` as the default when no backend is explicitly given, but **only at the moment a brand-new Assistant chat is created** (no live-pointer chat, or the idle pointer expired — FR-2 step 1-2). **Mid-flight note (closes EDGE-GAP-4):** a Settings/`use {backend}` write while the pointer still names a live, non-idle chat (FR-2) does not affect that chat — the live chat keeps whatever backend it was created with; the new default is read only by the next `new` (also see Edge Cases §8).
4. The `use {backend}` fast command (FR-5) also writes this file, keeping the "backend for next session" state in one place (CANONICAL gate: one fact, one file — context-snapshot.md:55).

**Postconditions / observable outcomes:**
- A backend change made in Settings (or via the `use X` fast command) is visible to the very next **newly created** Assistant chat, with no browser involved; it never retroactively changes an already-live chat's backend.

**Acceptance criteria (testable):**
- [ ] `POST /api/assistant/settings {backend: "ollama"}` persists to `console/config/assistant.toml`; a subsequent headless `kanban.py assistant say` (no browser session) creates its next new chat against `ollama` (pytest, no browser/localStorage involved) — closes analysis.md's flagged gap.
- [ ] `GET /api/assistant/settings` and the Settings-tab picker round-trip the same value (pytest + code review of `settings.js`'s new panel, confirming it is not `localStorage`-backed).
- [ ] The write is wrapped in `audit.record(...)` (BR-2).
- [ ] Initial default (no prior write) is "first enabled + installed backend, local-first" per the recorded decision (plan.md:34; `agents.toml` local-first order).
- [ ] **Closes BR-GAP-3:** `POST /api/assistant/settings {backend: "not-a-real-backend"}` returns 400 and `assistant.toml` is unchanged on disk (pytest, fake `agent_backends.get` reporting not-installed).
- [ ] **Closes EDGE-GAP-4:** with a live, non-idle Assistant chat pointed at `claude`, a `POST /api/assistant/settings {backend: "ollama"}` followed immediately by a `say` (same pointer, still alive) still dispatches to the existing `claude` chat; only a subsequent `new`/expired-pointer `say` creates a chat against `ollama` (pytest, fake manager + clock).

**Business rules invoked:** BR-8, BR-2

### FR-8: Reply path — watcher, spoken form, no double-speech
**Description:** A server-side reply watcher, one per Assistant session, subscribes to `sess.stream.subscribe` (`agent_events.py:153-181`). On `turn.end`, it takes the last `text.done` text, computes `spoken_form()` (first paragraph ≤ `reply_chars`, markdown stripped — a Python port of `voice.js:152-158`), and speaks it: via the native bridge if available (always false in T-004, FR-11), else via the webview's `ConsoleVoice.speak` triggered by `assistant.js` listening on the SSE stream. `agents.js`'s existing `autoRead` handler (`:839-846`) must not also speak the same reply if a user happens to have the Assistant chat open in the Agents tab.

**Actor:** Server-side watcher (new); `assistant.js` (new, browser); `agents.js` (existing, modified at line 841).

**Trigger:** `turn.end` event on the Assistant session's stream; `approval.request` event.

**Preconditions:**
- No `sess.stream.subscribe`-based server-side watcher exists today; `agent_events.py:subscribe` is currently consumer-side only, for browser SSE (analysis.md:188-192).
- `agents.js:839-846`'s `store` has no concept of "this chat is the assistant's own" today (analysis.md:176-187) — a guard is net-new.

**Flow:**
1. Watcher consumes the Assistant session's own event stream server-side.
2. On `turn.end`: compute `spoken_form()`; speak via bridge-else-webview.
3. **Double-speech guard mechanism (closes CROSS-GAP-1; design decision — see [[T-004-decision-log]] "assistant-chat-identity-flag"):** `agent_manager.create` gains a keyword `is_assistant=False`, threaded into `agent_session.build` and stored on the session object; `LiveSession.start`/`ApiSession.start`'s existing `session.started` event payload (`agent_session.py:380-385,494`) gains one field, `"is_assistant": self.is_assistant`. This event already populates every session's `meta` dict consumed both server-side (`agent_manager.py:140-145`'s `_meta_from_transcript`/snapshot reconstruction) and client-side (`agents.js:835`'s existing `store.on("meta", st.repaintChat)` subscription) — no new event type or transport is added. `assistant_feature.py` is the only caller that ever passes `is_assistant=True`. `agents.js`'s `autoRead` handler (`:838-846`) gains one guard line before its `Voice.speak(item.text)` call: `if ((store.state.meta || {}).is_assistant) return;` — the per-chat `autoRead` preference is left untouched (still checkable/toggleable in Settings), but it becomes a no-op specifically for the assistant's own chat, because the server-side watcher (step 2) already owns speaking for that chat.
4. On `approval.request`: emit an `attention` event and a spoken "Permission needed for …" (mirrors `agents.js:859-860`); the shell shows the window on `attention` (T-005 concern for the actual window-show; T-004 only emits the event honestly).
5. **Palette UI contract (closes UX-GAP-1; scoped down, not fully out-of-scope — `assistant.js` and its palette box remain in scope per plan.md:145):** `assistant.js` renders exactly one always-visible "Ask assistant" input + send action (no history pane, no attachments, no separate composer chrome) that `POST`s to `/api/assistant/say`; replies are visible through the ordinary Assistant chat already rendered by the existing Agents-tab chat view (it is an ordinary chat, FR-2), so `assistant.js` itself only needs to (a) accept typed input from that one box and (b) listen to `GET /api/assistant/stream` to trigger `ConsoleVoice.speak` (step 2/3) and an `attention` visual cue (step 4). Exact placement/keybinding/styling of the input box is a builder implementation choice, not a spec requirement — the plan's own manual end-to-end AC (plan.md:181) is exercised by typing directly in the Agents tab, not through the palette, so no additional testable AC is needed beyond "the box exists and posts to `/api/assistant/say`" (covered by FR-1's route ACs).

**Postconditions / observable outcomes:**
- A finished Assistant reply is spoken exactly once, regardless of whether the Assistant chat is also open in the Agents tab with `autoRead` on.

**Acceptance criteria (testable):**
- [ ] **Closes CROSS-GAP-1:** with the Assistant chat open in the Agents tab, `autoRead` on, and `store.state.meta.is_assistant === true`, a finished reply is spoken exactly once — by the server-side watcher's path, never by `agents.js`'s `autoRead` handler (unit test on the guard condition; integration test simulating both paths reacting to the same `turn.end`).
- [ ] A non-assistant chat's `session.started` event has no `is_assistant` field (or `false`), and its `autoRead` behavior is completely unchanged (regression test — the guard must not affect any existing chat).
- [ ] `spoken_form()` truncates to `reply_chars` (400 default) and strips markdown, matching `voice.js:152-158`'s existing behavior (pytest, parity test against known inputs).
- [ ] `approval.request` produces an `attention` SSE event with spoken text "Permission needed for …" (pytest against the event stream).
- [ ] With the native bridge unavailable (always true in T-004), the webview path is used with no error surfaced to the user (pytest).
- [ ] `assistant.js`'s input box exists, is always visible, and its `POST` reaches `/api/assistant/say` (pytest/DOM-level check) — closes UX-GAP-1's minimal contract.

**Business rules invoked:** BR-1 (n/a to speech, listed for completeness — none directly)

### FR-9: File-based memory
**Description:** The Assistant's conversation history is the chat itself (no duplicate store). A session pointer, a capped `memory.md` (≤1,500 chars, written by the `remember` fast command/verb), and a last-reply file live under `console/.cache/assistant/` — already covered by the blanket `.gitignore` rule, no vault writes.

**Actor:** `assistant_feature.py`/`assistant.py`.

**Trigger:** `remember {fact}` fast command; every completed reply (last-reply file update).

**Preconditions:**
- `console/.cache/` has no `assistant/` subdirectory yet (analysis.md:202-206, net-new).
- `.gitignore:65-67` already covers `console/.cache/` — no `.gitignore` edit needed (context-snapshot.md:50).

**Flow:**
1. **Secret guard (closes COMP-GAP-1; design decision — see [[T-004-decision-log]] "remember-secret-guard"):** before appending, `remember`'s handler checks the fact text against a small set of secret-shaped patterns (`-----BEGIN`, `sk-`/`AKIA`-style provider-key prefixes, a bare `KEY=value`/`.env`-looking line); on a match it declines and responds with a stated reason ("that looks like a secret — I won't remember it") instead of appending. This extends `assistant.md`'s existing persona safety list (plan.md:150: "name the destination before a cloud screenshot; never read the clipboard unasked; never claim to have seen pixels when OCR text was used") with one more line to the same effect, since `memory.md` is plaintext and re-injected into every future session's `extra` (FR-4).
2. `remember {fact}` (non-secret) appends to `console/.cache/assistant/memory.md`; if the result would exceed 1,500 chars, the oldest content is dropped first (exact trim strategy is a builder decision, not specified further by the plan — marked as an assumption in §3).
3. Every completed turn overwrites `console/.cache/assistant/last-reply` (consumed by "copy that" once the native bridge exists in T-005; unavailable honestly in T-004).
4. No code path in this ticket writes to `knowledge-center/` (the Obsidian vault).

**Postconditions / observable outcomes:**
- Memory survives server restarts (file-based) but is never versioned/vault-visible.
- A `remember` request whose fact text matches a secret-shaped pattern is declined, never appended (closes COMP-GAP-1).

**Acceptance criteria (testable):**
- [ ] `remember "the sky is blue"` appends to `console/.cache/assistant/memory.md`, capped at 1,500 chars (pytest).
- [ ] After the cap is exceeded, the file is truncated (oldest-first) rather than growing unbounded or erroring (pytest).
- [ ] Grep of the diff confirms no write call targets any path under `knowledge-center/` (code review / static check).
- [ ] `console/.cache/assistant/` requires no new `.gitignore` entry (verified: already covered).
- [ ] **Closes COMP-GAP-1:** `remember "sk-abcdef1234567890"` (and a `-----BEGIN PRIVATE KEY-----` fixture) is declined with a stated reason and never appears in `memory.md` afterward (pytest, secret-pattern fixtures).

**Business rules invoked:** BR-4

### FR-10: CLI — `kanban.py assistant say`
**Description:** A new `assistant` subparser group in `console/kanban.py`, with a `say` action, lets any user run `python console/kanban.py assistant say "…"` for shell-less testing — the same pattern as the existing `agents` subparser group.

**Actor:** Developer/user at a terminal.

**Trigger:** `python console/kanban.py assistant say "..."`.

**Preconditions:**
- No `assistant` subparser group exists in `kanban.py` today (`kanban.py:499-792`, analysis.md:208-214).

**Flow:**
1. CLI parses the `say` action and its text argument.
2. Calls the same code path as `POST /api/assistant/say` (in-process call, or a local HTTP call carrying `X-Console-Request: 1` if it goes over HTTP — either way, no bespoke CSRF bypass).
3. Prints the response (`result`, `spoken`, `reply` if present).

**Postconditions / observable outcomes:**
- Full assistant behavior (fast commands, session reuse, persona) is exercisable with no browser and no shell running.

**Acceptance criteria (testable):**
- [ ] `python console/kanban.py assistant say "status T-002"` prints the deterministic lane/stage answer, matching FR-5's AC (pytest, CLI invocation).
- [ ] The CLI path sends `X-Console-Request: 1` if it goes over HTTP (code review / pytest, per BR-6 — no bespoke bypass).
- [ ] `kanban.py`'s new subparser group follows the same `argparse` shape as the existing `agents` group (code review).

**Business rules invoked:** BR-6

### FR-11: `native_bridge.py` — honest always-unavailable stub
**Description:** `console/server/native_bridge.py` (100% new) provides the client shape T-005 will fill in, but in T-004 it always reports unavailable with a stated reason ("shell not running"), since neither `console/server/native_bridge.py` nor `console/.cache/desktop/bridge.json` exist as a working pair yet.

**Actor:** `assistant_feature.py` (calls `native_bridge.available()`); the `copy that` fast command and FR-8's reply-speak path.

**Trigger:** Any code path that would use the native bridge (clipboard write, native speak) in T-004.

**Preconditions:**
- `console/server/native_bridge.py` does not exist (confirmed via glob, analysis.md:194-200).
- `console/.cache/desktop/bridge.json` does not exist (only `serve.log`/`host.log` from T-003 are present) — `available()` has nothing to read.

**Flow:**
1. `available()` checks for `console/.cache/desktop/bridge.json`; absent → returns `False` with reason `"shell not running"`.
2. Any caller (e.g. `copy that`) receives the honest unavailable result and reports it to the user, rather than hanging or silently no-op'ing.

**Postconditions / observable outcomes:**
- Every native-bridge-dependent fast command degrades honestly in T-004, matching the cross-platform-honesty pattern already used by `voice.js` and the plan's platform strategy.

**Acceptance criteria (testable):**
- [ ] `native_bridge.available()` returns `False` with reason `"shell not running"` when `bridge.json` is absent (pytest, this is the literal trivially-testable AC per analysis.md:200).
- [ ] `say "copy that"` responds with a message naming the shell as not running, not an error/exception (pytest) — plan.md:165, 199-200.
- [ ] `test_native_bridge.py` follows the fake-opener/no-network idiom of `test_api_session.py` (code review of test style).

**Business rules invoked:** (none directly — honesty is enforced by structure, not a numbered BR)

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | Prompt budget stays within existing accounting | Tickets digest ≤1,200 chars; memory ≤1,500 chars; persona ≤4,000 chars; total `extra` ≈9.7k of `DEFAULT_BUDGET` 24k | `prompt_build.py:32,100-120`; truncation always stated, never silent (FR-4) |
| Scalability | Single Assistant chat per server process | One chat, reused; no concurrency design needed beyond existing `agent_manager` busy/queued handling | plan.md:147; not a multi-tenant concern in T-004 |
| Security / Auth | CSRF reuse, no bespoke plugin logic | All mutating routes rejected without `X-Console-Request: 1` | `httpd.py:181-182`; BR-6 |
| Auditability | Every mutating call recorded | `audit.record(...)` called for `assistant.say`, `kickoff`, `remember`, settings writes; `ACTIONS` tuple updated first | `audit.py:43-54`; BR-2 |
| Availability | Malformed/edge input never crashes dispatch | Fast-command table falls through cleanly on no match; PowerShell absence degrades to an honest error, not a partial ticket | Edge Cases §8; mirrors `telegram_bot.py`'s one-bad-input-doesn't-kill-the-loop pattern |
| Usability | Spoken-first reply contract | First paragraph ≤ `reply_chars` (400 default) is what is spoken; details after | plan.md:150,173 |
| Compliance | `remember`/`memory.md` must not persist secrets | Fact text matching a secret-shaped pattern is declined, never appended (FR-9) | Single-user local tool, so low severity, but a concrete rule, not "none identified" — closes COMP-GAP-1 |
| Concurrency | Single-writer-per-process for `console/.cache/assistant/*` plain files | `session.json`/`memory.md`/last-reply have exactly one writer at a time by construction: the pointer is read-then-written inline within one HTTP request handler (no background writer thread), and `remember`/the reply watcher never run concurrently against the same file because both are driven by the same single-process request/event-loop model already used for `agent_manager`'s existing session dict (`agent_manager.py:26-27`'s `_lock`) — no file-locking library is added; if a future change adds a second writer process, it must gain the same kind of lock `tomlio` already proves works (`test_tomlio.py::test_concurrent_writers_do_not_corrupt`, analysis.md's baseline note) | Closes NFR-GAP-2 |
| Cross-platform honesty | Native-bridge stub reports unavailable identically on all 3 target OSes | `native_bridge.available() == False, reason="shell not running"` regardless of host OS | plan.md § Platform strategy; FR-11 |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `session.json` | new | chat id (`sid`), backend, model, created/last-used timestamps | create on first `say`; update on reuse; overwritten (never archived) | `console/.cache/assistant/session.json`, plan.md:147 |
| `memory.md` | new | free-text facts appended by `remember`, cap 1,500 chars | create on first `remember`; update (append, oldest-first trim past cap) | `console/.cache/assistant/memory.md`, plan.md:166,177 |
| last-reply file | new | plain text of the most recent spoken reply | create/overwrite on every completed turn | `console/.cache/assistant/`, plan.md:177; consumed by "copy that" once T-005 lands |
| `assistant.toml` | new | `backend`, `model`, `mode`, `vision_models`, `session_idle_minutes`, `speak`, `reply_chars`, `ticket_prefix` | create at kickoff (defaults committed); update via FR-7's settings route | `console/config/assistant.toml`, plan.md:173 |
| `assistant.md` | new | persona text, ≤4,000 chars | create once; update by direct file edit (not via API in T-004) | `console/config/assistant.md`, plan.md:149-150 |
| `/api/assistant/stream` events | new | 5 event types, each read-only over SSE: `turn.start {type,at}` / `turn.end {type,at,cost_usd,num_turns}` (existing shape, unchanged, `agent_session.py:380-385`); `attention {type,reason:"approval"\|"error",text}` (net-new); `reply {type,text,spoken}` (net-new); `speaking.start`/`speaking.stop {type}` (net-new, client-relayed) | emitted per turn/approval; never persisted beyond the existing per-session `.events.jsonl` transcript | plan.md:145; closes DATA-GAP-1/NFR-GAP-1 (FR-1) |

**`assistant.toml` forward-compatibility (closes DATA-GAP-2):** unknown keys are ignored on load and every read goes through `.get(key, default)` (same additive-config rule `notify.py` already uses for its own committed prefs, e.g. `notify.py:90-99`'s `cfg.get("channel", "telegram")`/`cfg.get("timeout", DEFAULT_TIMEOUT)` pattern) — so T-005/T-006 adding their own keys to this same file (e.g. per-OS voice/listen settings) cannot break a T-004-era reader, and an older config missing a T-005-added key still loads with that key's coded default.

### Data flows
User utterance → `say` → normaliser (FR-5) → **match:** verb/handler call, zero model calls → response; **no match:** `agent_manager.send` with `extra=` (tickets digest + memory + capabilities line, FR-4) injected → backend reply → reply watcher (FR-8) → `spoken_form()` → speak (webview, native bridge always unavailable in T-004, FR-11) → last-reply file updated (FR-9).

### Retention / archival
All new files live under `console/.cache/assistant/`, already covered by the blanket `.gitignore` rule (`.gitignore:65-67`) — no retention policy beyond process/checkout lifetime; no vault writes, no archival step. `memory.md` self-caps at 1,500 chars (oldest-first trim, exact trim mechanics a builder decision per §3 Assumptions).

## 7. Business Rules

Number each `BR-{n}`. Each is atomic.

- **BR-1:** Fast-command dispatch on a `say` call resolves to exactly one whole-utterance table match OR exactly one `agent_manager.send` call — never both — and no code path inspects a model's output to choose the next action ("no second orchestrator"). Structurally mirrors `telegram_bot.py:_dispatch`'s one-branch shape (`:295-378`). — plan.md:53,147; analysis.md:104-115.
- **BR-2:** Every mutating call under `/api/assistant/*` (including verb writes) is wrapped in `audit.record(...)`, on both success and failure, and its action name is added to `audit.py`'s `ACTIONS` tuple before first use. — `verbs_feature.py:34-46`; `audit.py:43-54`.
- **BR-3:** T-004 adds zero new agents; the assistant is one ordinary chat plus a dispatch table, never an 8th file under `.claude/agents/`. — CLAUDE.md "Exactly 7 agents"; analysis.md:226-232.
- **BR-4:** Assistant memory (`memory.md`, session pointer, last-reply) is written only under `console/.cache/assistant/`, never to the Obsidian vault (`knowledge-center/`). — plan.md:177.
- **BR-5:** The `kickoff` verb must produce the same three artifacts the `kickoff` *skill* produces — `ticket.toml` + trackers via `tickets.create`, rendered `_template/*.md` files via `New-FromTemplate.ps1`, and an artifact-map row — never merely a thin wrapper around `tickets.create` alone. — plan.md:171,181; `tickets.py:38-73`; `.claude/skills/kickoff/SKILL.md:15-20`.
- **BR-6:** CSRF is enforced once, at the transport layer (`X-Console-Request: 1`, `httpd.py:181-182`); `assistant_feature.py` and its callers (`assistant.js`, `kanban.py assistant say`) rely on that check and add no bespoke per-plugin CSRF logic.
- **BR-7:** Persona text is capped at ≤4,000 chars, enforced by `assistant_feature.py` truncating `assistant.md` at read time (never merely documented) using `prompt_build.build`'s existing truncate-plus-stated-marker pattern (`prompt_build.py:137-150`), logged via `audit.record("assistant.persona_truncated", ...)`; the resulting claude argv stays ≤8,000 chars, safely under the Windows ~32k argv limit. When persona text is empty, `--append-system-prompt` is dropped entirely from argv, never sent as an empty value. — plan.md:151-152; `agent_backends.py:205-239` (FR-3).
- **BR-8:** The assistant's default/session backend selection is stored server-side in `console/config/assistant.toml`, readable by any server-spawned session including a headless `kanban.py assistant say` call — never in browser `localStorage` alone, unlike every other Settings picker. — analysis.md:152-174; `notify.py:61-102`.
- **BR-9** (closes INT-GAP-2): The 3 new verb rows (`kickoff`, `tickets_digest`, `remember`) are exposed identically to every existing chat and to the MCP tool list, not scoped to the Assistant alone — because `verbs.toml` is a generic registry (`agent_tools.py:9-11,321`: "every row in `verbs.toml` becomes a tool," prefixed `console_`), consistent with T-004 adding no bespoke assistant-only tool-exposure mechanism. This is intentional, not a defect: the persona doc's own "tool preferences" list (plan.md:151, e.g. `console_tickets_digest` for "what's open") already presumes these are ordinary `console_`-prefixed tools any chat/persona can be told to prefer. — `agent_tools.py:9-11,321`; plan.md:151.

## 8. Edge Cases

- **Busy session, queued:** a second `say` while a turn is in flight reuses the pointer and returns `result: "queued"`, spoken "Still working — queued," without erroring or opening a second chat. — plan.md:147; analysis.md:57-59 (FR-2).
- **PowerShell unavailable (closes EDGE-GAP-2 — reframed):** the `kickoff` verb fails honestly rather than leaving a partial ticket dir (only `ticket.toml`, no rendered artifacts); the `create ticket for X` fast command falls back to sending `/kickoff {id} --title …` to the chat instead. On Windows (PS 5.1 ships by default) this is the rare branch; on macOS/Linux (no `pwsh` in plan.md:74's Build-prerequisites row) this fallback is the routine path, not an edge case there — both branches carry their own AC already (FR-6). — plan.md:74,171 (FR-6).
- **Empty persona:** `assistant.md` empty or missing → `system_append` resolves to empty → `--append-system-prompt` is dropped entirely from argv, reusing `_expand`'s existing empty-placeholder-drop behavior, not a new assertion. — `agent_backends.py:205-239` (FR-3, BR-7).
- **autoRead double-speech (closes CROSS-GAP-1):** a user with the Assistant chat open in the Agents tab with `autoRead` on must hear a finished reply exactly once — enforced by the `session.started` event's new `is_assistant` flag, checked by `agents.js`'s `autoRead` handler before it speaks (FR-8; design decision in [[T-004-decision-log]]).
- **Backend uninstalled/not enabled:** the `use {backend}` fast command for a backend that is not installed/enabled must report failure honestly (reusing `agent_manager.create`'s existing backend-installed check, `agent_manager.py:41-87`), never silently falling back to a different backend (FR-5).
- **Windows argv cap exceeded (closes EDGE-GAP-1):** `assistant.md`/`system_append` is truncated to 4,000 chars at read time with a stated marker (never silently, never a raised exception, never an OS-truncated argv) — the same "truncate + stated marker" pattern `prompt_build.build` already uses (`prompt_build.py:137-150`); the resulting argv addition stays ≤8,000 chars, safely under the ~32k Windows limit (FR-3, BR-7).
- **Malformed fast-command input:** an unrecognized or partially-matched utterance must fall through cleanly to the `else: agent_manager.send` branch and never raise or crash the dispatcher — mirrors `telegram_bot.py`'s "one bad input doesn't kill the loop" pattern (`:295-378`) (FR-5).
- **Native bridge always unavailable in T-004:** any fast command depending on it (e.g. `copy that`) returns a clear "unavailable: shell not running" message, never hangs or raises an opaque error (plan.md:165,199-200) (FR-11).
- **`say` backend-failure result (closes EDGE-GAP-3):** if `agent_manager.create`/`send` itself raises (backend fails to spawn, cloud network error), `say` returns `result: "error"` with a stated reason, never an unhandled 500/crash (FR-1).
- **Mid-flight backend change (closes EDGE-GAP-4):** changing the Settings backend picker (or `use {backend}`) while an Assistant session is already live does not affect that live session — it is read only by the next brand-new session (FR-7).

## 9. Interactions with Existing Features

(Condensed from [[T-004-context-snapshot]] §2; expanded by `challenge-requirements T-004 (overlap/conflict/reuse dimension)`)

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| Verb registry (`verbs.toml`/`verbs.py`/`verb_handlers.py`) | reuse — `kickoff`/`tickets_digest`/`remember` are new rows in this exact registry, `needs_confirm` gating already implemented and tested | low | modify (additive rows only) |
| Live agent chat lifecycle (`agent_manager.py`) | reuse — the Assistant chat is an ordinary `agent_manager.create`/`send` call, no new session primitive | low | modify (thread `system_append`/`extra` params) |
| Inbound dispatch shape (`telegram_bot.py:_dispatch`) | reuse (structural template only, not shared code) — same one-match-or-fallback shape proves BR-1 is enforceable | low | isolate (new module, same shape) |
| Prompt assembly / budget (`prompt_build.py`) | reuse — `extra=` param already exists and is budget-accounted; only call-site plumbing is missing | low | modify (thread `extra=`/`system_append` through `BaseSession`→`ApiSession`/`LiveSession`) |
| Settings prefs pattern (`notify.py`/`ops_feature.py`) | reuse — direct template for the new server-side-writable `assistant.toml` + settings route; every *other* Settings panel is `localStorage`-only and cannot drive a server-spawned session | medium (if not followed, ships a broken picker) | modify (new file/route, same pattern) |
| Per-chat autoRead (`agents.js:839-846`) | conflict, resolved — no chat-identity awareness today; guarded by the new `session.started`/`meta.is_assistant` flag (FR-8) so the server-side reply watcher never double-speaks with it | medium | modify (one guard line + one event field) |
| Kickoff skill (`kickoff/SKILL.md` + `New-FromTemplate.ps1`) | reuse — the `kickoff` verb must mirror the skill's 3 steps (ticket.toml+trackers, template render, artifact-map append), calling the same PS1 rather than reimplementing it | medium (undersizing ships a broken verb) | modify (verb orchestrates same steps, same script) |
| PS 5.1-safe template rendering (`New-FromTemplate.ps1:65,88`) | reuse (closes INT-GAP-1) — the `kickoff` verb calls this exact script, whose PS 5.1 fixes are already in place; listed as its own row since context-snapshot.md §2 tracks it separately from the "Kickoff skill" row (8 similar-feature rows there vs. 7 here before this pass) | low | isolate (called as-is, no script changes) |
| Verb→tool generic exposure (`agent_tools.py:9-11,321`) | reuse, ripple noted (closes INT-GAP-2) — `kickoff`/`tickets_digest`/`remember` automatically become `console_`-prefixed tools callable by every existing chat and the MCP tool list, not only the Assistant's own dispatch table; intentional per BR-9 and the persona doc's own "tool preferences" framing (plan.md:151) | low (additive, no existing chat behavior changes unless a chat is told to call these tools) | none — confirmed intended, no code change beyond the additive `verbs.toml` rows already planned (FR-6) |

## 10. External Dependencies

- **Claude CLI (`claude`)** — `--append-system-prompt <text>` flag, verified present (plan.md:26). Needed for FR-3's persona injection on the `stream_json` transport.
- **cursor-agent CLI** — no system-prompt flag exists (confirmed, `agents.toml:143-179`); FR-3's persona injection for this backend is a prompt-prepend, not a config flag.
- **OpenRouter / Ollama / LM Studio (`openai_api` transport)** — persona/context reach these via `prompt_build.build`'s existing `extra=` passthrough (FR-3, FR-4); no new external dependency, just wiring.
- **Windows PowerShell 5.1** — the `kickoff` verb's template render (FR-6) depends on it; an honest fallback exists for its absence (Edge Cases §8).
- **`New-FromTemplate.ps1`** (existing script, `.claude/skills/template/scripts/`) — the `kickoff` verb calls this script as-is; no new script is written (FR-6).

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner / approver | Sohail Ali | Wants the assistant brain testable by typing before voice/native-bridge work begins; owns the binding plan (`our-project-is-in-optimized-treasure.md`) | yes |
| Future implementer (closes STAKE-1) | Sohail Ali (forward-compat hat, T-005/T-006) | `native_bridge.py`'s always-unavailable stub shape (FR-11) and the reply-watcher/`attention`-event contract (FR-8) must be extensible without rework once T-005's real bridge and T-006's voice loop land — plan.md:84-85 makes both tickets depend on T-004 | no (same person as owner; concern noted, not a separate sign-off gate) |

## 12. Open Questions (mirrored)

Mirrored from `T-004-questions.toml` (`console/kanban.py tracker list T-004 questions`). Blocker questions must be resolved before freeze.

- Q{n}: _text_ — status: open | answered | resolved

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements T-004`. Each must be resolved or explicitly accepted before freeze. Find-don't-fix: resolutions land in the next `requirements enrich`/`iterate` pass, not here.)

- ⚠ **BR-1 is proven only by code review, not by a regression test.** FR-2's sole AC for BR-1 is "Code review: the fast-command handler contains exactly one branch point... no code path inspects a model reply to decide what to do next" (requirements-draft.md FR-2 AC). That proves the *current* code's shape once, but nothing catches a future change that lets a model's reply steer a second dispatch. No AC uses a fake `agent_manager` whose `send()` returns text that happens to match a fast-command pattern (e.g. a reply containing the literal words "status T-002") to assert the dispatcher never re-fires on it. — **resolution:** FR-2 gained a new AC: a fake `agent_manager.send()` returning fast-command-shaped text (`"status T-002"`) is asserted to never re-enter the dispatcher on the next `say` — the dispatcher only ever inspects the caller's raw inbound text, never a prior model reply.

- ⚠ **FR-8's double-speech guard still has no named mechanism.** FR-8's own AC text says "the specific guard mechanism is named at challenge-requirements" (requirements-draft.md FR-8) — i.e. the draft deferred this exact decision to this pass, and after this pass it remains unnamed (which flag, which file, which side — `assistant.js` vs `agents.js` vs a server-side session field — enforces it). analysis.md:263-269 flagged the same gap at GROUND; it is still open. — **resolution:** FR-8 now names the mechanism: a new `is_assistant` boolean threaded through `agent_manager.create` → the `session.started` event payload → the existing `meta` object already consumed by `agents.js:835`'s `store.on("meta", ...)`. `agents.js`'s `autoRead` handler (`:838-846`) gains one guard line (`if ((store.state.meta||{}).is_assistant) return;`) before speaking. Recorded as a design decision in [[T-004-decision-log]] ("assistant-chat-identity-flag").

- ⚠ **Windows argv-cap-exceeded behavior is an undecided OR, and `assistant.md`'s own ≤4,000-char cap is never enforced.** Edge Cases §8 states "`session_argv` must fail loudly or truncate with a stated reason" — two different behaviors, no chosen one, so no single testable AC exists for this path. Separately, `assistant.md` is "update[d] by direct file edit (not via API in T-004)" (§6 Data Requirements) — no code path in any FR reads the file and checks its length against the ≤4,000-char cap FR-3 describes, so the cap is documentation only today, not enforced. The ticket's own established pattern elsewhere ("truncate + stated marker, never silent" — FR-4) is a candidate default but was not applied here. — **resolution:** FR-3 now enforces the ≤4,000-char cap at read time: `assistant_feature.py` truncates `assistant.md` using `prompt_build.build`'s existing truncate-plus-stated-marker pattern (`prompt_build.py:137-150`) and logs it via `audit.record("assistant.persona_truncated", ...)` — never silent, never a raised exception, and the resulting argv addition stays well under the 8,000-char/32k-Windows-limit bound (BR-7 updated to match).

- ⚠ **BR-3 ("zero new agents, never an 8th file under `.claude/agents/`") has no testable acceptance criterion anywhere in the draft.** BR-3 is invoked by FR-2 ("Business rules invoked: BR-1, BR-3"), but none of FR-2's four ACs test it — contrast with BR-4 (vault writes), which FR-9 tests directly via "Grep of the diff confirms no write call targets any path under `knowledge-center/`." No equivalent "`.claude/agents/` file count is unchanged (7)" assertion exists for BR-3, and a repo grep found no existing structural test enforcing the agent count either. — **resolution:** FR-2 gained a testable AC for BR-3: a pytest asserting `len(glob.glob(".claude/agents/*.md")) == 7` post-diff, mirroring FR-9's diff-grep pattern for BR-4.

- ⚠ **PS-unavailable is framed as an edge case but may be the routine path on 2 of 3 target OSes.** Platform strategy (plan.md:55-76) names Windows/macOS/Linux as the 3 target OSes and lists no PowerShell prerequisite for macOS/Linux builds (plan.md:74, Build-prerequisites row has entries for MSVC/Xcode CLT/apt packages, none for pwsh). §8 Edge Cases frames "PowerShell unavailable" as an edge case for the `kickoff` fast command, but on a macOS/Linux dev or deploy machine without `pwsh` installed, the fallback branch (send `/kickoff {id} --title …` to chat instead) may be the *normal* outcome, not a rare one. Both branches are individually testable already (FR-6 ACs), so this is a framing/labeling gap, not a missing test. — **resolution:** FR-6's flow and the Edge Cases §8 bullet now state the expected frequency per OS explicitly (routine on macOS/Linux, rare on Windows, citing plan.md:74's Build-prerequisites row) — no new AC, both branches were already tested.

- ⚠ **FR-7's "validates" step names no validation rule.** FR-7 Flow step 2: "`POST /api/assistant/settings` validates and writes back (audited)" — no AC states what "validates" checks (e.g. rejecting a `backend` value that is not installed/enabled, mirroring `agent_manager.create`'s existing check per context-snapshot.md's "Existing patterns to reuse"). Without this, a malformed POST could persist a backend the system can never actually spawn, discovered only at the next `say`. — **resolution:** FR-7's flow now names the rule: an unknown/uninstalled `backend` value (checked via `agent_backends.get(...).installed`, the same check `agent_manager.create` already runs) is rejected with 400 and never persisted; a new AC covers it.

- ⚠ **`/api/assistant/stream`'s event vocabulary is undocumented and (mostly) unimplemented anywhere in the repo.** plan.md:145 names the exact SSE filter (`turn.start`, `attention`, `reply`, `turn.end`, `speaking.*`), but FR-1's own description/ACs don't restate it, and a repo grep of `agent_events.py`/`agent_session.py`/`agent_api_session.py`/`agent_normalize.py`/`agent_approvals.py` finds only `turn.start`, `turn.end`, `turn.steer`, `turn.interrupt`, `text.start/delta/done`, `approval.request`, `approval.decided` — **no `attention`, `reply`, or `speaking.*` publish call site exists anywhere today.** §6 Data Requirements lists 5 file-based entities but no event-schema entity for these three net-new types, and FR-1 AC #4 ("asserting the documented response shape") has nothing documented for the `stream` route specifically. A builder cannot implement this route from the draft alone. — **resolution:** FR-1 now enumerates all 5 event names with field shapes (`turn.start`/`turn.end` existing and unchanged; `attention`/`reply`/`speaking.*` net-new), and §6 Data Requirements gained a matching entity row — a builder can now implement `GET /api/assistant/stream` from the draft alone.

- ⚠ **§9 Interactions (7 rows) undercounts context-snapshot.md §2's "Similar / adjacent features" table (8 rows).** Missing: "PS 5.1-safe template rendering (`New-FromTemplate.ps1:65,88`)" as its own interaction row (context-snapshot.md row 8). It's functionally subsumed by the "Kickoff skill" row (same script, called as-is), so risk is low, but a reader trusting the "7 interactions" summary count undercounts the actual reused surface by one. — **resolution:** §9 gained its own row for "PS 5.1-safe template rendering (`New-FromTemplate.ps1:65,88`)" — now 9 rows (7 original + this + the verb→tool exposure row below), matching context-snapshot.md §2's full reused-surface count.

- ⚠ **§9 Interactions has no row for the verb registry's generic tool exposure.** `console/server/agent_tools.py:9-11` states "Every row in `verbs.toml` becomes a tool" (prefixed `console_`, `agent_tools.py:321`) — meaning the 3 new verb rows (`kickoff`, `tickets_digest`, `remember`) automatically become callable tools (`console_kickoff`, `console_tickets_digest`, `console_remember`) for **every existing agent chat and the MCP tool list**, not only the Assistant's own fast-command table. This is plan-consistent (the persona doc itself lists these as "tool preferences" — plan.md:151), but it is a real ripple onto every pre-existing chat that §9 never names or cross-checks for conflict. — **resolution:** §9 gained a "Verb→tool generic exposure" row confirming the exposure is intentional and identical for every chat (consistent with the persona doc's "tool preferences" framing); a new BR-9 states the same rule as a numbered business rule.

- ⚠ **No NFR covers concurrent-write safety for `console/.cache/assistant/*` plain files.** `session.json`, `memory.md`, and the last-reply file have no stated atomic-write/locking guarantee, unlike the repo's proven TOML writer (referenced in analysis.md:216-225's baseline note, `test_tomlio.py::test_concurrent_writers_do_not_corrupt`). At least two independent write paths exist that could race on `memory.md`/last-reply (the `remember` fast command and the reply watcher's per-turn update). — **resolution:** §5 NFR table gained a "Concurrency" row: single-writer-per-process by construction (one request/event-loop model, no background writer thread), so no file-locking library is needed; if a second writer process is ever added, it must gain a lock like `tomlio`'s proven one (`test_tomlio.py::test_concurrent_writers_do_not_corrupt`).

- ⚠ **FR-1 defines no `error` result for `say`.** The postcondition lists `result: handled|sent|queued` only (plan.md:145; FR-1). No AC anywhere covers the case where `agent_manager.create`/`send` itself throws (backend process fails to spawn, network error to a cloud backend) — every current AC assumes success or the busy/queued branch. — **resolution:** FR-1's postcondition now names a fourth `result: "error"` variant (with a new AC) for when `agent_manager.create`/`send` itself raises — a stated reason, HTTP 400 for malformed requests, never an unhandled 500/crash; also added as an Edge Cases §8 bullet.

- ⚠ **Backend changed via Settings while the reused live Assistant chat is still active is unspecified.** FR-7's postcondition says a change "is visible to the very next `kanban.py assistant say` call" — but FR-2 reuses the live chat "if alive and used within `session_idle_minutes`," so it is only implied, never stated, that a mid-flight `use {backend}`/Settings change affects the *next new session* and not the currently-reused one. — **resolution:** FR-7's flow now states this explicitly (a Settings/`use` write only affects the next brand-new Assistant chat, never a live/reused one), with a new AC and a matching Edge Cases §8 bullet.

- ⚠ **No FR describes the "Ask assistant" palette box's own UI contract.** `console/static/assistant.js` is new and in-scope (plan.md:145, §3 In scope), and the plan's own manual AC ("typed end-to-end in the Agents tab... manual, recorded" — plan.md ACs) presumes a working palette exists to type into, but no FR states its visibility trigger, keybinding/placement, or where a reply renders — FR-8 only covers assistant.js's role in *speaking* a finished reply, not the input surface itself. — **resolution:** FR-8 gained a minimal UI-contract flow step: `assistant.js` renders exactly one always-visible input + send action posting to `/api/assistant/say`, with replies visible via the ordinary Agents-tab chat render (FR-2); exact placement/keybinding is left to the builder since the plan's own manual e2e AC is exercised via the Agents tab, not the palette. The palette itself stays in scope per plan.md:145 — this is a scoped-down UI contract, not an out-of-scope declaration.

- ⚠ **No compliance note for `remember`-ing secrets.** `remember {fact}` (FR-6/FR-9) has no guard against a user "remembering" a secret (API key, password) into a plaintext, unencrypted `memory.md` that is then re-injected into every future session's `extra` context (FR-4). Low severity given this is a single-user local tool (§11 Stakeholders: one owner), but the NFR table's Compliance row currently says "None identified... revisit if challenge-requirements finds one" (§5) — this is that revisit. — **resolution:** FR-9 gained a secret-guard flow step: `remember` declines a fact matching a secret-shaped pattern (`-----BEGIN`, provider-key prefixes, `KEY=value`) with a stated reason, never appending it; extends `assistant.md`'s existing persona safety list (plan.md:150). §5's Compliance row updated from "none identified" to this rule. Design decision recorded in [[T-004-decision-log]] ("remember-secret-guard").

- ⚠ **`assistant.toml`'s forward-compatibility is unstated.** T-005/T-006 are both expected to add keys to this same file (`vision_models` already present for T-007-era use; per-OS voice/listen settings are T-006's), but §6 Data Requirements states only the current field list, with no "unknown keys ignored, new keys additive" statement — a future ticket's evolve could silently break this ticket's reader if the assumption isn't pinned now. — **resolution:** §6 Data Requirements gained an explicit forward-compat note: unknown keys are ignored, every read goes through `.get(key, default)`, mirroring `notify.py`'s own additive-config pattern (`notify.py:90-99`).

- ⚠ **No stakeholder row for the future T-005/T-006 implementer.** §11 lists only Sohail Ali as owner/approver. The plan explicitly makes T-005/T-006 depend on T-004 (plan.md:84-85 programme table), and this draft's own §1 Business driver says T-004 exists to de-risk that work — but no stakeholder row captures the concern that `native_bridge.py`'s always-unavailable stub shape and the reply-watcher/`attention`-event contract (FR-8, FR-11) must be extensible without rework once T-005 lands. — **resolution:** §11 gained a "Future implementer" stakeholder row (same person, forward-compat hat) naming this concern explicitly.

## 14. Draft History

See [[T-004-iteration-log]] for per-iteration diff + rationale.

Current iteration: **0** (v0 draft, not yet iterated)

---

## Freeze Checklist (run by `requirements freeze`) — result: PASS (2026-09-06, iteration 0)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred — none remain (verified by grep)
- [x] All ⚠ findings resolved or explicitly accepted with rationale — all 16 §13 findings carry a resolution
- [x] All blocker open questions answered — `T-004-questions.toml` has 0 entries (`console/kanban.py tracker list T-004 questions`)
- [x] Every FR has at least one testable acceptance criterion — FR-1..FR-11 each have ≥1 checklist AC
- [x] Every NFR has a concrete target or documented reason for absence — §5 table, 8/8 rows
- [x] Every new/changed entity has a canonical reference or creation plan — §6 table, 6/6 entities
- [x] Out-of-scope list is non-empty — §3, 7 items
- [x] Stakeholder sign-off recorded — §11, Sohail Ali, "yes"
- [x] `T-004-requirements.md` finalized for `requirements stories` consumption (see [[T-004-requirements]])

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements-draft]] · [[T-004-context-snapshot]] · [[T-004-gap-analysis]] · [[T-004-iteration-log]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
