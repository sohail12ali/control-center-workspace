---
ticket: "T-004"
artifact: requirements
status: frozen
frozen_at: "2026-09-06"
frozen_iteration: 0
---

# Requirements: T-004 (frozen, iteration 0, 2026-09-06)

> Canonical, frozen requirements for planning/build/verify. Full rationale, flows, and challenge history live in [[T-004-requirements-draft]] (retained, not superseded) and [[T-004-iteration-log]]. Any post-freeze change goes through `evolve`, never a silent edit here.

## Intent

Sohail Ali wants the future voice assistant testable by typing today — persona, dispatch, memory, and a backend picker — with no microphone and no native bridge required yet. De-risks T-005 (native bridge) and T-006 (voice/mic), both of which depend on T-004 (plan.md:83-85, 143-182).

## Scope

**In:** `assistant_feature.py` plugin + 5 routes (`say`/`session`/`new`/`stream`/`memory`, `stream`'s `attention` event included) · one reused "Assistant" chat session model · console-owned persona injected per-backend · injected per-session context (tickets digest, memory, capabilities) · deterministic fast-command table · 3 new verbs (`kickoff`, `tickets_digest`, `remember`) · server-side Settings backend picker (service half only — see Out) · file-based capped memory · `kanban.py assistant say` CLI · `native_bridge.py` honest always-unavailable stub.

**Out:** T-005 native bridge real implementation · **T-006: reply-path speaking (FR-8 in full — server-side watcher, `spoken_form()`, `is_assistant` double-speech guard, `assistant.js` "Ask assistant" box) — deferred, amendment 2026-09-06** · **T-006: Settings-tab UI picker (FR-7 AC2 only) — deferred, amendment 2026-09-06** · T-006 voice/mic capture · T-007 multimodal `/send` · Telegram routing of `/api/assistant/say` · tray icon states · OS actuation (backlog T-009) · an 8th `.claude/agents/` file (explicitly rejected).

## Functional Requirements

1. **FR-1 — `assistant_feature.py` plugin + routes.** New plugin, tenth `plugins.toml` row, routes `say`/`session`/`new`/`stream`/`memory`; `httpd.py` untouched.
   - [ ] Exactly one `[[plugin]]` row added; `httpd.py` diff empty
   - [ ] `say` without `X-Console-Request: 1` → 403
   - [ ] `audit.py` `ACTIONS` extended before first use
   - [ ] Each route unit-tested against a fake `agent_manager`
   - [ ] `stream` yields only the 5 named event types, others filtered
   - [ ] `agent_manager.create`/`send` raising → `result:"error"`, never an unhandled 500

2. **FR-2 — Session model.** One reused "Assistant" chat; pointer file; busy→queued; idle timeout recreates.
   - [ ] Second `say` in-flight reuses chat, returns `queued`
   - [ ] Past `session_idle_minutes`, next `say` creates a new chat
   - [ ] Assistant chat visible in ordinary Agents-tab chat list
   - [ ] Code review: exactly one branch point (match → handler, else → send)
   - [ ] Regression test: fast-command-shaped model output never re-enters dispatch (BR-1)
   - [ ] Structural test: `.claude/agents/*.md` count stays 7 (BR-3)

3. **FR-3 — Persona injected per backend.** `assistant.md` (≤4,000 chars, truncated+stated if over) via `persona_text`'s second root; claude via `--append-system-prompt`; `openai_api` via `extra=`; cursor-agent via prompt-prepend.
   - [ ] Claude argv contains the flag+text when non-empty
   - [ ] Flag omitted entirely when persona empty
   - [ ] `openai_api` request body includes persona via `extra=`
   - [ ] cursor-agent first-turn prompt starts with persona text
   - [ ] Diff touches only `system_append`/`extra` threading
   - [ ] 4,500-char fixture truncates to 4,000 with stated marker + `audit.record("assistant.persona_truncated", ...)`

4. **FR-4 — Injected session context.** `extra` = tickets digest (≤1,200) + memory (≤1,500) + capabilities line, within `DEFAULT_BUDGET` 24k.
   - [ ] Composed `extra` has all 3 sections within their caps
   - [ ] Over-cap section truncates with stated marker
   - [ ] Total prompt length stays under budget

5. **FR-5 — Deterministic fast-command table.** Normalise → whole-utterance match (11 rows) → handler, else `send`.
   - [ ] `"status T-002"` never calls `send`
   - [ ] Each of the 11 rows has its own unit test
   - [ ] `"stop the server"` falls through to `send`, not `interrupt` (whole-utterance only)
   - [ ] Unrecognized input never raises; reaches `else`

6. **FR-6 — New verbs (`kickoff`, `tickets_digest`, `remember`).** `kickoff` mirrors the `kickoff` skill's 3 steps (never a thin `tickets.create` wrapper); PS-unavailable fails honestly with a chat fallback.
   - [ ] `"create ticket for X"` produces `ticket.toml` + rendered templates
   - [ ] PowerShell mocked unavailable → verb errors, fast command sends `/kickoff …` fallback
   - [ ] `kickoff` row has `needs_confirm=true`, refused without `confirm`
   - [ ] `tickets_digest`/`remember` each unit-tested
   - [ ] **(added, amendment 2026-09-06)** Given an artifact-map whose `## Completed` section is non-empty and whose `## Active` section is empty, the new row still lands directly under `## Active` — insertion is heading-relative, never "after the last ticket-shaped row"
   - [ ] **(added, amendment 2026-09-06)** After the verb runs, each rendered `{ID}-*.md` starts with `---` (no `\xef\xbb\xbf` BOM), decodes as UTF-8, and contains none of `Â·`, `â€"`, `â€™` — regression guard for the `New-FromTemplate.ps1` double-encoding fix (ANSI `Get-Content -Raw` + BOM `Set-Content -Encoding UTF8` under Windows PowerShell 5.1)

7. **FR-7 — Settings backend picker (server-side).** `assistant.toml` + `GET`/`POST /api/assistant/settings`; unknown/uninstalled backend rejected (400), never persisted; only a brand-new session reads the default.
   - [ ] POST persists; next headless `say` creates its next new chat against the new backend
   - [ ] ~~GET + Settings-tab picker round-trip the same value, not `localStorage`~~ **DEFERRED to T-006, amendment 2026-09-06** (service half only in T-004: `GET`/`POST /api/assistant/settings` exists and is tested via HTTP client, not the Settings-tab control)
   - [ ] Write wrapped in `audit.record(...)`
   - [ ] Initial default = first enabled+installed backend, local-first order
   - [ ] Invalid backend → 400, file unchanged
   - [ ] Mid-flight change doesn't affect an already-live chat

8. **FR-8 — Reply path. DEFERRED IN FULL to T-006, amendment 2026-09-06.** Speaking a reply, and testing the no-double-speech guard, only make sense once voice/mic exists (T-006). None of this FR's ACs are in T-004's build scope; `assistant_feature.py`'s `stream` route (FR-1) still emits the `attention` event type unfiltered — only the *speaking* watcher, `spoken_form()`, the `is_assistant` guard, and `assistant.js` move to T-006.
   - ~~Reply spoken exactly once even with the chat open + `autoRead` on~~
   - ~~Non-assistant chat's `autoRead` behavior unchanged (regression)~~
   - ~~`spoken_form()` truncates to `reply_chars`, strips markdown~~
   - ~~`approval.request` → `attention` SSE + spoken text~~ (the SSE event itself ships in T-004 via FR-1's `stream` route; only the accompanying spoken text is deferred)
   - ~~Bridge unavailable → webview path, no error surfaced~~
   - ~~`assistant.js` input box exists, always visible, posts to `/api/assistant/say`~~

9. **FR-9 — File-based memory.** `session.json`/`memory.md` (≤1,500, oldest-first trim)/last-reply under `console/.cache/assistant/`; secret-shaped facts declined; no vault writes.
   - [ ] `remember` appends, capped at 1,500 chars
   - [ ] Over-cap truncates oldest-first, never errors/grows unbounded
   - [ ] Diff grep: no write targets `knowledge-center/`
   - [ ] No new `.gitignore` entry needed (already covered)
   - [ ] Secret-shaped fact (API key / private-key fixture) declined, never appended

10. **FR-10 — CLI `kanban.py assistant say`.** Same code path as `POST /api/assistant/say`, no bespoke CSRF bypass.
    - [ ] `assistant say "status T-002"` prints the deterministic answer
    - [ ] HTTP path (if any) sends `X-Console-Request: 1`
    - [ ] Subparser shape matches the existing `agents` group

11. **FR-11 — `native_bridge.py` honest stub.** Always reports unavailable ("shell not running") in T-004.
    - [ ] `available()` → `False, "shell not running"` when `bridge.json` absent
    - [ ] `"copy that"` responds with the honest reason, not an error
    - [ ] Test style matches `test_api_session.py`'s fake-opener idiom

## Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | Prompt budget | Digest ≤1,200 · memory ≤1,500 · persona ≤4,000 · total ≈9.7k of 24k `DEFAULT_BUDGET` |
| Scalability | Single Assistant chat/process | No multi-tenant concurrency design needed |
| Security/Auth | CSRF reuse only | All mutating routes need `X-Console-Request: 1`, no bespoke logic |
| Auditability | Every mutating call audited | `audit.record(...)` for `assistant.say`/`kickoff`/`remember`/settings writes |
| Availability | Malformed input never crashes dispatch | Fast-command table falls through cleanly; PS absence degrades honestly |
| Usability | Spoken-first reply | First paragraph ≤ `reply_chars` (400 default) is spoken |
| Compliance | No secrets in `memory.md` | Secret-shaped fact text declined, never appended |
| Concurrency | Single-writer-per-process for `.cache/assistant/*` | No locking library added; one request/event-loop model |
| Cross-platform honesty | Bridge stub identical on all 3 OSes | `available()==False, reason="shell not running"` everywhere |

## Data Entities

| Entity | Fields | Lifecycle |
|---|---|---|
| `session.json` | `sid`, backend, model, timestamps | create/reuse/overwrite |
| `memory.md` | free-text facts, cap 1,500 | create/append, oldest-first trim |
| last-reply file | plain text | overwrite per completed turn |
| `assistant.toml` | backend, model, mode, vision_models, session_idle_minutes, speak, reply_chars, ticket_prefix | create at kickoff; update via FR-7; unknown keys ignored (forward-compat) |
| `assistant.md` | persona text ≤4,000 chars | create once; direct file edit in T-004 |
| `/api/assistant/stream` events | `turn.start`/`turn.end` (existing shape) · `attention {reason,text}` · `reply {text,spoken}` · ~~`speaking.start`/`speaking.stop`~~ (deferred to T-006 with FR-8, amendment 2026-09-06 — filter passes the type through but nothing emits it in T-004) | per-turn/approval; not persisted beyond existing transcript |

## Business Rules

- **BR-1:** `say` resolves to exactly one fast-command match OR one `agent_manager.send` — never both; no code path inspects model output to choose the next action.
- **BR-2:** Every mutating `/api/assistant/*` call is `audit.record`-wrapped, success and failure, action name added to `ACTIONS` first.
- **BR-3:** Zero new agents; assistant is one chat + dispatch table, never an 8th `.claude/agents/` file.
- **BR-4:** Assistant memory lives only under `console/.cache/assistant/`, never the vault.
- **BR-5:** `kickoff` verb produces the same 3 artifacts as the `kickoff` skill (ticket.toml+trackers, rendered templates, artifact-map row) — never a thin `tickets.create` wrapper.
- **BR-6:** CSRF enforced once at transport (`X-Console-Request: 1`); no bespoke per-plugin CSRF logic.
- **BR-7:** Persona ≤4,000 chars, truncated+stated (never silent); resulting argv ≤8,000 chars; empty persona drops the flag entirely.
- **BR-8:** Backend selection stored server-side in `assistant.toml`, readable by headless callers — never `localStorage`-only.
- **BR-9:** New verb rows are exposed identically to every chat and the MCP tool list (generic `verbs.toml`→tool mechanism), not scoped to the Assistant alone — intentional.

## Edge Cases

- Busy session → `queued`, no error, no second chat.
- PowerShell unavailable → honest verb failure + chat fallback (routine on macOS/Linux, rare on Windows).
- Empty persona → flag dropped entirely, no new assertion needed.
- ~~`autoRead` double-speech → guarded by `is_assistant` flag on `session.started`/`meta`.~~ **DEFERRED to T-006 with FR-8, amendment 2026-09-06** — no `is_assistant` flag ships in T-004.
- Uninstalled/disabled backend via `use {backend}` → honest failure, no silent fallback.
- Persona/argv over cap → truncate + stated marker, never silent, never raised.
- Malformed fast-command input → falls through to `send`, never raises.
- Native bridge always unavailable in T-004 → honest "shell not running" message.
- `say` backend failure (`create`/`send` raises) → `result:"error"` with stated reason, never an unhandled 500.
- Mid-flight backend change → affects only the next brand-new session, never a live one.

## Interactions with Existing Features

Verb registry (reuse, additive rows) · live agent chat lifecycle (reuse, thread `system_append`/`extra`) · `telegram_bot._dispatch` (structural template only) · `prompt_build.py` (reuse, plumbing only) · `notify.py`/`ops_feature.py` settings pattern (reuse, direct template) · per-chat `autoRead` (deferred to T-006 with FR-8, amendment 2026-09-06 — no conflict to resolve in T-004, nothing speaks yet) · `kickoff` skill + `New-FromTemplate.ps1` (reuse, verb mirrors skill's 3 steps, calls script as-is) · verb→tool generic exposure (reuse, ripple confirmed intentional per BR-9). Full detail: [[T-004-requirements-draft]] §9.

## Stakeholders

Sohail Ali — owner/approver, sign-off: **yes**. Also the future T-005/T-006 implementer (forward-compat concern on `native_bridge.py`'s stub shape and the `attention`/reply-watcher contract staying extensible).

## Out of Scope

T-005 native bridge (real impl, tray states, screenshot/OCR/clipboard/TTS) · **T-006 voice/mic/VAD/hotkey, plus (deferred from T-004, amendment 2026-09-06) FR-8 in full — reply-speaking watcher, `spoken_form()`, `is_assistant` autoRead guard, `assistant.js` — and FR-7 AC2, the Settings-tab UI picker** · T-007 multimodal `/send` · Telegram routing of `/api/assistant/say` · tray icon states (T-005's `tray_state.rs`) · OS actuation (backlog T-009) · an 8th `.claude/agents/` file.

## Freeze Record

- Iteration: 0 · Frozen: 2026-09-06
- Challenge findings: 16/16 resolved (§13 of the draft) · Gap analysis: 17/17 rows closed ([[T-004-gap-analysis]])
- Open questions at freeze: 0 (`T-004-questions.toml`)
- Decisions grounding this freeze: [[T-004-decision-log]] — entry-point plugin shape, console-owned persona + second root, kickoff-as-verb (rejected: agent turn, Python template port), fast-command table scope (BR-1), Settings backend picker local-first default, memory location + caps, plus the two challenge-resolution decisions (assistant-chat-identity-flag, remember-secret-guard).
- **Amendment 2026-09-06** (post-freeze, iteration unchanged — see [[T-004-decision-log]] § Amendment 2026-09-06): FR-8 deferred in full to T-006; FR-7 AC2 deferred to T-006; FR-6 gained 2 new ACs (artifact-map `## Active` insertion point, rendered-template encoding regression guard).

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements-draft]] · [[T-004-context-snapshot]] · [[T-004-gap-analysis]] · [[T-004-iteration-log]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]] · [[T-004-user-stories]]
