---
ticket: "T-004"
artifact: user-stories
created: "2026-09-06"
---

# User Stories: T-004

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-004 stories` · **Validated by:** `validate-artifacts T-004 links` · **Verified by:** `validate-artifacts T-004 links`

> 11 stories, one per frozen FR — deliberately outside the skill's usual 3-8 range because T-004 spans 9+ real layers (planner's `analyze-components` call); merging FRs here would hide the dependency seams the components map needs. Related Tasks left blank — task IDs don't exist until `breakdown-tasks`.

## Stories

### US-1: HTTP entry point for the assistant

**As a** developer building the typed-first assistant
**I want to** a new `assistant_feature.py` plugin exposing `say`/`session`/`new`/`stream`/`memory` routes as a tenth `plugins.toml` row
**So that** every caller (CLI, future Rust bridge, webview palette box) has one entry point, with `httpd.py` untouched

**Acceptance Criteria:**
- [ ] Exactly one `[[plugin]]` row added; `httpd.py` diff empty
- [ ] `say` without `X-Console-Request: 1` → 403
- [ ] `audit.py` `ACTIONS` extended before first use
- [ ] Each route unit-tested against a fake `agent_manager`
- [ ] `stream` yields only the 5 named event types, others filtered
- [ ] `agent_manager.create`/`send` raising → `result:"error"`, never an unhandled 500

**Business Rules:** BR-2 (audit-wrapped), BR-6 (CSRF at transport only)
**Edge Cases:** `say` backend failure never surfaces a 500

**Related Components:** assistant_feature.py plugin+routes (C2), audit.py ACTIONS extension (C0)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** High
**Story Points:** 5

---

### US-2: One reused Assistant chat session

**As a** user typing to the assistant repeatedly
**I want to** the assistant to reuse one "Assistant" chat (busy→queued, idle-timeout recreates)
**So that** I don't accumulate duplicate chats or lose context between turns

**Acceptance Criteria:**
- [ ] Second `say` in-flight reuses chat, returns `queued`
- [ ] Past `session_idle_minutes`, next `say` creates a new chat
- [ ] Assistant chat visible in ordinary Agents-tab chat list
- [ ] Code review: exactly one branch point (match → handler, else → send)
- [ ] Regression test: fast-command-shaped model output never re-enters dispatch (BR-1)
- [ ] Structural test: `.claude/agents/*.md` count stays 7 (BR-3)

**Business Rules:** BR-1 (one match or one send, never both), BR-3 (zero new agents)
**Edge Cases:** Busy → `queued`, no error, no second chat

**Related Components:** assistant_feature.py plugin+routes (C2), BaseSession system_append/extra threading (C1)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** High
**Story Points:** 3

---

### US-3: Console-owned persona injected per backend

**As a** the assistant's owner/user
**I want to** a persona (`console/config/assistant.md`, ≤4,000 chars) injected into every backend (claude/openai_api/cursor-agent) without an 8th agent file
**So that** the assistant's role, safety list, and tool preferences are consistent regardless of which backend is selected

**Acceptance Criteria:**
- [ ] Claude argv contains the flag+text when non-empty
- [ ] Flag omitted entirely when persona empty
- [ ] `openai_api` request body includes persona via `extra=`
- [ ] cursor-agent first-turn prompt starts with persona text
- [ ] Diff touches only `system_append`/`extra` threading
- [ ] 4,500-char fixture truncates to 4,000 with stated marker + `audit.record("assistant.persona_truncated", ...)`

**Business Rules:** BR-3 (never an 8th agent file), BR-7 (4,000-char cap, empty drops flag)
**Edge Cases:** Empty persona → flag dropped entirely; persona/argv over cap → truncate + stated marker

**Related Components:** persona + persona_text second root (C3), BaseSession system_append/extra threading (C1)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** High
**Story Points:** 5

---

### US-4: Injected per-session context (tickets, memory, capabilities)

**As a** user asking the assistant about current work
**I want to** every new Assistant session pre-loaded with a tickets digest, prior memory, and a capabilities line
**So that** I don't have to re-explain ticket state or capabilities each turn, within the existing prompt budget

**Acceptance Criteria:**
- [ ] Composed `extra` has all 3 sections within their caps
- [ ] Over-cap section truncates with stated marker
- [ ] Total prompt length stays under budget

**Business Rules:** (NFR: Digest ≤1,200 · memory ≤1,500 · persona ≤4,000 · total ≈9.7k of 24k `DEFAULT_BUDGET`)
**Edge Cases:** Over-cap section truncates, never silently drops

**Related Components:** injected session context (C4), BaseSession system_append/extra threading (C1), new verbs (C6), file-based memory (C8)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** Medium
**Story Points:** 3

---

### US-5: Deterministic fast-command dispatch

**As a** user typing a short command ("status T-002", "stop the server")
**I want to** a deterministic normalise-then-whole-utterance-match table of 11 rows handle it before any model call, else fall through to `send`
**So that** common commands are instant and reliable, and BR-1's "no second orchestrator" invariant holds

**Acceptance Criteria:**
- [ ] `"status T-002"` never calls `send`
- [ ] Each of the 11 rows has its own unit test
- [ ] `"stop the server"` falls through to `send`, not `interrupt` (whole-utterance only)
- [ ] Unrecognized input never raises; reaches `else`

**Business Rules:** BR-1 (exactly one match or one send)
**Edge Cases:** Malformed fast-command input falls through to `send`, never raises

**Related Components:** fast-command dispatch table (C5) — **novel, no existing analogue beyond `telegram_bot._dispatch`'s structural shape**
**Related Tasks:** _pending breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-6: New verbs — kickoff, tickets_digest, remember

**As a** user issuing "create ticket for X" or "remember {fact}"
**I want to** three new verbs that mirror the `kickoff` skill's real 3 steps (never a thin `tickets.create` wrapper), with an honest PowerShell-unavailable fallback
**So that** ticket creation, ticket-state summaries, and fact retention work identically whether driven by a human, a chat, or the CLI

**Acceptance Criteria:**
- [ ] `"create ticket for X"` produces `ticket.toml` + rendered templates
- [ ] PowerShell mocked unavailable → verb errors, fast command sends `/kickoff …` fallback
- [ ] `kickoff` row has `needs_confirm=true`, refused without `confirm`
- [ ] `tickets_digest`/`remember` each unit-tested

**Business Rules:** BR-2 (audit-wrapped), BR-5 (kickoff mirrors the skill's 3 steps), BR-9 (verb rows generic, not assistant-scoped)
**Edge Cases:** PowerShell unavailable → honest verb failure + chat fallback

**Related Components:** new verbs (C6), file-based memory (C8), audit.py ACTIONS extension (C0)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-7: Settings backend picker (server-side)

**As a** user choosing which backend the assistant talks to
**I want to** a server-persisted `assistant.toml` + `GET`/`POST /api/assistant/settings`, validated against enabled+installed backends
**So that** the choice is honored by headless callers too, not just the browser, and an invalid choice is rejected rather than silently accepted

**Acceptance Criteria:**
- [ ] POST persists; next headless `say` creates its next new chat against the new backend
- [ ] ~~GET + Settings-tab picker round-trip the same value, not `localStorage`~~ **DEFERRED to T-006, amendment 2026-09-06** — GET round-trips via HTTP client in T-004; the tab control ships with T-006
- [ ] Write wrapped in `audit.record(...)`
- [ ] Initial default = first enabled+installed backend, local-first order
- [ ] Invalid backend → 400, file unchanged
- [ ] Mid-flight change doesn't affect an already-live chat

**Business Rules:** BR-8 (server-side, never `localStorage`-only), BR-2 (audit-wrapped)
**Edge Cases:** Uninstalled/disabled backend → honest failure, no silent fallback; mid-flight change affects only the next brand-new session

**Related Components:** settings backend picker (C7), assistant_feature.py plugin+routes (C2), audit.py ACTIONS extension (C0) — **zero risk, direct copy of `notify.py`/`ops_feature.py` pattern**
**Related Tasks:** _pending breakdown-tasks_

**Priority:** Medium
**Story Points:** 3

---

### US-8: Spoken reply path with no double-speech — DEFERRED IN FULL to T-006 (amendment 2026-09-06)

**As a** user who has the Agents tab open with autoRead on
**I want to** the assistant's reply spoken exactly once (server-side watcher owns it), and a minimal always-visible "Ask assistant" box
**So that** I never hear the same reply twice and can always type to the assistant regardless of which tab is showing

Speaking a reply, and testing the no-double-speech guard, only make sense once voice/mic exists (T-006). None of this story's build work ships in T-004; the `attention` SSE event type itself still flows through T-004's `stream` route (FR-1) unfiltered.

**Acceptance Criteria (all deferred to T-006):**
- ~~Reply spoken exactly once even with the chat open + `autoRead` on~~
- ~~Non-assistant chat's `autoRead` behavior unchanged (regression)~~
- ~~`spoken_form()` truncates to `reply_chars`, strips markdown~~
- ~~`approval.request` → `attention` SSE + spoken text~~ (SSE event ships in T-004; spoken text deferred)
- ~~Bridge unavailable → webview path, no error surfaced~~
- ~~`assistant.js` input box exists, always visible, posts to `/api/assistant/say`~~

**Business Rules:** (NFR: spoken-first reply, first paragraph ≤`reply_chars`)
**Edge Cases:** `autoRead` double-speech guard deferred to T-006 with the `is_assistant` flag

**Related Components:** reply path + is_assistant flag + assistant.js (C9) — **DEFERRED IN FULL to T-006**, was novel/no-existing-analogue, the ticket's other flagged high-risk item
**Related Tasks:** none in T-004 — see T-006

**Priority:** High (T-006)
**Story Points:** 8 (moves to T-006)

---

### US-9: File-based capped memory

**As a** user asking the assistant to remember a fact
**I want to** the fact appended to a capped, oldest-first-trimmed `memory.md` under `console/.cache/assistant/`, with secret-shaped facts declined
**So that** the assistant has durable-enough working memory without ever leaking into the vault or storing credentials in plaintext

**Acceptance Criteria:**
- [ ] `remember` appends, capped at 1,500 chars
- [ ] Over-cap truncates oldest-first, never errors/grows unbounded
- [ ] Diff grep: no write targets `knowledge-center/`
- [ ] No new `.gitignore` entry needed (already covered)
- [ ] Secret-shaped fact (API key / private-key fixture) declined, never appended

**Business Rules:** BR-4 (memory only under `console/.cache/assistant/`, never the vault)
**Edge Cases:** Secret-shaped fact text declined, never appended

**Related Components:** file-based memory (C8) — **zero risk, gitignored `.cache` scratch-dir pattern already exists**
**Related Tasks:** _pending breakdown-tasks_

**Priority:** Medium
**Story Points:** 3

---

### US-10: CLI parity for `assistant say`

**As a** user or script driving the assistant headlessly
**I want to** `python console/kanban.py assistant say "..."` to use the exact same code path as `POST /api/assistant/say`
**So that** there is no bespoke CSRF bypass or second implementation to keep in sync

**Acceptance Criteria:**
- [ ] `assistant say "status T-002"` prints the deterministic answer
- [ ] HTTP path (if any) sends `X-Console-Request: 1`
- [ ] Subparser shape matches the existing `agents` group

**Business Rules:** BR-6 (CSRF enforced once at transport, no bespoke logic)
**Edge Cases:** none beyond the shared route's own

**Related Components:** kanban.py assistant say CLI (C11), assistant_feature.py plugin+routes (C2)
**Related Tasks:** _pending breakdown-tasks_

**Priority:** Low
**Story Points:** 2

---

### US-11: Honest native-bridge stub

**As a** the future T-005 implementer
**I want to** `native_bridge.py` always report unavailable ("shell not running") in T-004, on all 3 OSes
**So that** T-004 never pretends a native bridge exists before T-005 builds one, and T-005 has a stable, forward-compatible contract to extend

**Acceptance Criteria:**
- [ ] `available()` → `False, "shell not running"` when `bridge.json` absent
- [ ] `"copy that"` responds with the honest reason, not an error
- [ ] Test style matches `test_api_session.py`'s fake-opener idiom

**Business Rules:** (Cross-platform honesty NFR: identical stub behavior on all 3 OSes)
**Edge Cases:** Native bridge always unavailable in T-004 → honest "shell not running" message

**Related Components:** native_bridge.py stub (C10) — **zero risk, fully isolated leaf, no dependency on any other T-004 component**
**Related Tasks:** _pending breakdown-tasks_

**Priority:** Low
**Story Points:** 1

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | HTTP entry point for the assistant | Pending | High | 5 | |
| US-2 | One reused Assistant chat session | Pending | High | 3 | |
| US-3 | Console-owned persona injected per backend | Pending | High | 5 | |
| US-4 | Injected per-session context | Pending | Medium | 3 | |
| US-5 | Deterministic fast-command dispatch | Pending | High | 8 | |
| US-6 | New verbs — kickoff, tickets_digest, remember | Pending | High | 8 | |
| US-7 | Settings backend picker (server-side only; UI half deferred to T-006) | Pending | Medium | 3 | |
| US-8 | Spoken reply path with no double-speech | **Deferred to T-006** (amendment 2026-09-06) | High | 8 | |
| US-9 | File-based capped memory | Pending | Medium | 3 | |
| US-10 | CLI parity for `assistant say` | Pending | Low | 2 | |
| US-11 | Honest native-bridge stub | Pending | Low | 1 | |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | C2 assistant_feature.py routes, C0 audit ACTIONS | |
| US-2 | C2 assistant_feature.py routes, C1 BaseSession threading | |
| US-3 | C3 persona + second root, C1 BaseSession threading | |
| US-4 | C4 injected context, C1, C6, C8 | |
| US-5 | C5 fast-command dispatch table | |
| US-6 | C6 new verbs, C8 memory, C0 audit ACTIONS | |
| US-7 | C7 settings picker, C2, C0 | |
| US-8 | C9 reply path + is_assistant flag | |
| US-9 | C8 file-based memory | |
| US-10 | C11 CLI, C2 | |
| US-11 | C10 native_bridge stub | |

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements]] · [[T-004-requirements-draft]] · [[T-004-user-stories]] · [[T-004-components]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
