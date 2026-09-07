---
ticket: "T-004"
artifact: analysis
---

# Analysis: T-004

## Context

T-004 makes the future voice assistant testable by typing, before any microphone
exists: one ordinary Agents chat ("Assistant"), a deterministic fast-command
table, a console-owned persona, a Settings backend picker, and file-based
memory. Binding source of truth: `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md`
§ "T-004 — Assistant brain (typed first, voice later)" (lines 143-182), plus
§ "Architecture (one voice turn)" (37-53), § "Decisions taken" (30-35), and
§ "Platform strategy" (55-76). T-003 (shell hygiene, `procs.py`/`logger.rs`/PE
subsystem fix) is the stated dependency and its artifacts (`console/.cache/desktop/{host,serve}.log`,
`console/server/procs.py`, `console/tests/test_procs.py`) already exist in the
working tree, so the dependency is satisfied even though T-003 is not yet
`close-work`'d (git status shows it staged as modified/untracked, not this
ticket's concern). No T-004 code exists yet — kickoff produced only the 13
placeholder artifacts and the two placeholder plan tasks (`T-004-plan.md`,
ignored here — planner owns it).

## Current State

**Plugin/route pattern (net-new module to add):**
- `console/server/features/verbs_feature.py:1-102` is the literal template the
  plan names: thin `apply(ctx)`, handlers close over `repo_root`, routes via
  `ctx.get`/`ctx.post`, every mutating call wrapped in `audit.record(...)`
  (success and failure both recorded — verbs_feature.py:34-46).
- `console/server/features/agents_feature.py:100-123` (`chat_new`) is the
  create-session pattern to copy for the Assistant session: resolve backend →
  `agent_manager.create(...)` → `audit.record(repo_root, "chat.start", ...)`.
  `chat_send` (:138-139) and `chat_interrupt` (:141-142) are the thin wrappers
  around `agent_manager.send`/`interrupt` the fast-command table will call.
- `console/config/plugins.toml:22-86` — 9 enabled rows, each `id` +
  `module = "features.{name}_feature"` + `enabled = true`. A tenth
  `[[plugin]] id = "assistant" module = "features.assistant_feature"` is a
  pure addition; nothing else in this file changes.
- CSRF is already handled at the transport layer: `console/server/httpd.py:181-182`
  rejects any POST lacking `X-Console-Request: 1` with 403. `assistant_feature.py`
  needs no bespoke CSRF logic — only its callers (`assistant.js`, the
  `kanban.py assistant say` CLI's local HTTP call if it goes over HTTP rather
  than in-process) must send the header.

**Session/chat model:**
- `agent_manager.create` (`console/server/agent_manager.py:41-87`) already
  does exactly what the plan's session model needs: backend-installed check,
  `agent_session.build`, `sess.start()`, `sess.send(...)`, `sess.snapshot()`.
  No new primitive is needed — the Assistant session is an ordinary call into
  this with a persisted pointer (`console/.cache/assistant/session.json`, a
  new file) tracking its `sid`, read/written by the new `assistant_feature.py`.
- `agent_manager.send` (`:179-193`) and `agent_manager.get`/`require`
  (`:90-101`) give "reuse while alive" and "busy → queued" (the queued
  semantics live inside `sess.send`, not visible at this layer — confirmed
  the manager itself has no busy/queued branching, so "busy → queued, spoken
  'Still working — queued'" is a response the fast-command handler composes
  from `sess.send`'s return value, not new manager code).
- `.cache/agent-chats/` already holds two live-looking chats
  (`7762c925c1f8`, `8fe6c5410e62`) with `.settings.json`/`.log`/`.events.jsonl`
  siblings — confirms the on-disk shape `_paths()` (`agent_manager.py:36-38`)
  produces, which the Assistant chat will also use (it is an ordinary chat,
  visible in the Agents tab, per the plan).
- No `console/.cache/assistant/` directory exists yet — fully net-new.

**Persona + prompt plumbing:**
- `console/server/prompt_build.py:56-60` `persona_text` reads exactly one
  root, `.claude/agents/%s.md`. Adding a second root
  (`console/config/personas/`, which also does not exist yet) is a small,
  additive change: try the new root first (or merge), fall back/combine with
  the existing one — exact merge strategy is a planner/builder decision, not
  an open requirements question, since the plan already names the two things
  that must combine (the persona text `console/config/assistant.md`, ≤4,000
  chars per the plan, plus the existing agent-file mechanism for CLI
  personas). No `console/config/assistant.md` exists yet.
- `prompt_build.build` (`:100-154`) already has a generic `extra` parameter
  (`:100-101`) that gets appended as its own section (`:119-120`) and is
  budget-accounted like every other section (`DEFAULT_BUDGET = 24_000` chars,
  `:32`). This is exactly the passthrough the plan's "Injected `extra` per new
  session" (tickets digest + memory + capabilities line) needs — no change to
  `prompt_build.py` itself is required for the `extra=` path; `ApiSession.start`
  (`agent_api_session.py:103-108`) already calls `prompt_build.build(..., ticket=self.ticket)`
  with no `extra=` passed today, so wiring the Assistant's session creation to
  pass `extra=` down through `BaseSession`/`ApiSession.__init__` is the actual
  gap (currently there is no `extra` field on `BaseSession`/`ApiSession` to
  carry it from `agent_manager.create` through to `start()`).
- `agent_backends.py:491-505` `Backend.session_argv(...)` builds the
  `stream_json` argv from `session_args` templates and has no `system_append`
  parameter today. `agents.toml`'s claude row (`:52-63`) has no
  `--append-system-prompt` entry. Both need one additive line each — confirmed
  `_expand` (`agent_backends.py:205-239`) already drops a flag whose
  placeholder resolves to empty (`:213-219`, `:233-237`), so
  `"--append-system-prompt", "{system_append}"` behaves exactly as the plan
  requires (flag vanishes when the persona is empty) with **no new code** in
  `_expand` itself.
- `agent_session.py:368-370` is the one call site of `session_argv` for a
  `stream_json` LiveSession — it will need a `system_append=` kwarg threaded
  from `BaseSession.__init__` (`:67-82`, which does not currently store one).
- cursor-agent's row (`agents.toml:143-179`) has no system-prompt flag
  (confirmed against the plan's claim); prepending persona text to the first
  turn's prompt is a `compose_prompt`/call-site change, not a config row.

**Fast commands:**
- `console/server/telegram_bot.py:295-307` `_dispatch` is precisely the shape
  named in the task ("study ~line 295") — a `dict.get(word, handler)` lookup
  with a fallback to a free-text handler (`_say`, `:370-378`). The assistant's
  fast-command table is the same shape (normalise → exact/whole-utterance
  match → handler, else `agent_manager.send`), confirming BR-1 is
  structurally enforceable: exactly one regex/table match OR one `send`, never
  both, mirroring `_dispatch`'s own one-branch-or-the-other structure.
  `telegram_bot.py`'s commands are prefix-based (`/status`, `/new ...`)
  while the plan's fast commands are natural-language whole-utterance matches
  (`"status T-002"`, `"what's open"`) — a different regex table, same
  dispatch shape.
- No existing normalisation helper for "strip wake word/punctuation" or
  `t[- ]?(\d+) -> T-00N` exists in the repo (grepped; net-new, small,
  ticket-id patterns already used elsewhere in `verb_handlers`/`tickets.py`
  for validation, not normalisation from speech).
- `agent_backends.py:526-542` `compose_prompt` is the existing
  skill-composition path the plan's "do|fix|build|run {rest}" row reuses
  (`compose_prompt(rest, skill="do")`); confirmed it exists with the
  slash/inline/none dispatch by `prompt_prefix_style`.

**Verbs:**
- `console/config/verbs.toml` currently has 8 read-only verbs
  (`context`, `blockers`, `plan-status`, `artifacts`, `todos`, `harness-lint`,
  `telemetry`, `skill-usage`, `agent-models`), each a `[[verb]]` row +
  `verb_handlers.<fn>` — this file's own comment (`:25-27`) states "every verb
  below is READ-ONLY... the first mutating verb should set [`needs_confirm`],
  and the tests already cover the gate." **`kickoff` is that first mutating
  verb.** `console/server/verbs.py:145` already enforces `needs_confirm` at
  dispatch (`if verb.needs_confirm and not confirm: refuse`), so the gate
  exists and only a new verb row + handler are needed.
- `tickets.create` (`console/server/tickets.py:38-73`) writes `ticket.toml` +
  calls `trackers_mod.ensure_all` — it does **not** render `_template/*.md`
  artifacts or touch `artifact-map.md`. The `kickoff` skill
  (`.claude/skills/kickoff/SKILL.md:15-20`) does both of those as separate
  steps, invoking `New-FromTemplate.ps1` per template file. A new
  `console/server/kickoff.py` verb handler therefore has real work to do
  beyond calling `tickets.create`: compute `next_ticket_id`, call
  `tickets.create`, shell out to `New-FromTemplate.ps1` once per
  `_template/*.md` file, and append the artifact-map row — i.e. it is a
  Python-orchestrated re-implementation of the kickoff skill's steps 1-2-5,
  calling the *same* PowerShell script rather than reimplementing template
  substitution (the plan explicitly rejects a Python port as "second
  implementation").
- `.claude/skills/template/scripts/New-FromTemplate.ps1:65,88` already has the
  PS 5.1 fix stated in the task brief: `Get-Content -Raw -Encoding UTF8` read
  (`:65`) and `[System.IO.File]::WriteAllText(..., UTF8Encoding($false))`
  BOM-less write (`:88`) — confirmed in place, no further PS work needed here.
- **Settings-write gap (new finding, not explicit in the plan text):** the
  existing Settings tab (`console/static/settings.js`) has exactly one
  server-side-persisted panel — Telegram prefs — via
  `console/server/notify.py:61-102` (`prefs_path`/`load_prefs`/`apply_prefs`,
  a committed-config + gitignored-overlay pattern) and
  `console/server/features/ops_feature.py:78-89` (`POST /api/notify/prefs`).
  Every other Settings panel (`agentBackends`, `composer`, `tabVisibility`) is
  **browser-local only** (`localStorage` via `C.prefs`). The plan's "Settings
  backend picker" needs the assistant's default backend to be known
  **server-side** (it drives which backend a new server-spawned Assistant
  session uses, independent of any browser), so it cannot be `localStorage`
  like the existing `agentBackends` panel — it must follow the
  `notify.py`/`ops_feature.py` shape: a committed `console/config/assistant.toml`
  with defaults, no gitignored overlay is named in the plan (unlike notify),
  so the simplest reading consistent with "Settings backend picker" is a
  `GET`/`POST` pair under `/api/assistant/...` that reads/writes
  `assistant.toml` directly (analogous to `notify.config`/`apply_prefs` but
  without the narrowing-only asymmetry notify.py needs, since there is no
  Telegram-style widen/narrow security concern for a backend/model choice).
  This endpoint is not named among the plan's explicit route list
  (`say`/`session`/`new`/`stream`/`memory`) — flagged for
  challenge-requirements as a real gap to close with a testable AC, not a
  blocking question (the shape is unambiguous by analogy).

**Reply path / no double-speech:**
- `console/static/agents.js:839-846` is the exact autoRead handler named in
  the brief: `store.on("patch", ...)` speaks any finished, not-yet-spoken
  assistant text when `Voice.prefs().autoRead` is on, for **whatever chat
  store is open** — this fires for the Assistant chat too if a user happens
  to have it open in the Agents tab with autoRead on, which is the double-
  speech risk the plan calls out. The store has no concept of "this chat is
  the assistant's own" today; a guard (e.g. `store.chatId !== assistantChatId`,
  or a `meta` flag on the session) is net-new and belongs to
  `assistant.js`/`agents.js`, not to this analysis (challenge-requirements
  territory: needs a named mechanism, currently unspecified in the plan text
  beyond "must not double-speak").
- `console/server/agent_manager.py` has no `sess.stream.subscribe`-based
  server-side watcher today; `agent_events.py:153-181` `subscribe` is
  consumer-side (SSE for the browser) — the plan's "server-side reply
  watcher" is a new consumer of the same `stream.subscribe` API, one per
  Assistant session, net-new code in `assistant.py`/`assistant_feature.py`.

**Native bridge:**
- `console/server/native_bridge.py` does not exist (confirmed via glob) —
  100% net-new, matching the plan ("Always reports unavailable in T-004 (no
  bridge yet)"). `console/.cache/desktop/bridge.json` does not exist either
  (only `serve.log`/`host.log` are present from T-003), so `available()` has
  nothing to read and must return `False` with a stated reason — this is the
  literal, trivially-testable AC ("shell not running").

**Memory:**
- `console/.cache/` has `agent-chats/` and `audit/` and `desktop/` today; no
  `assistant/` subdirectory. `.gitignore:67` (`console/.cache/`) already
  covers anything written under it — no `.gitignore` edit needed for the new
  `console/.cache/assistant/` path.

**CLI:**
- `console/kanban.py:499-792` builds one `argparse` subparser group per
  domain (`ticket`, `tracker`, `work`, `vault`, `agents` (`:607`), `verb`,
  `notify`, `schedule`, `job`, `worktree`, `telemetry`, `harness`) — no
  `assistant` group exists yet. A new `assistant` subparser with a `say`
  action (`python console/kanban.py assistant say "..."`) is a pure addition
  in the same pattern as the existing `agents` group.

**Baseline:**
- `python -m pytest` from repo root exits 0 (all green) as of this session;
  this repo's conftest emits a custom per-file collection report rather than
  pytest's default "`N passed`" summary line, so the exact current total was
  not machine-read here — the ticket brief's stated baseline (783 passed) is
  taken as given and unchanged, since no test files were touched during this
  GROUND pass. One pre-existing, unrelated flaky `PytestUnhandledThreadExceptionWarning`
  fires from `test_tomlio.py::test_concurrent_writers_do_not_corrupt` (a
  Windows file-lock race in a concurrency stress test) — a warning, not a
  failure, and outside T-004's scope.
- Roster confirmed: exactly 7 files under `.claude/agents/` (analyst, builder,
  deployer, fixer, harness, planner, verifier) and 41 entries under
  `.claude/skills/` (39 first-party + `template` counted + one more; exact
  count is the skills catalog's own concern, not restated here). T-004 adds
  **zero** new agents — confirmed no 8th "assistant" agent file is implied by
  any of the 11 delivery points; the assistant is a chat + a dispatch table,
  consistent with the hard rule.

## Key Findings

- **Every one of the 11 delivery points is net-new code, but 9 of them extend
  an existing, already-proven pattern** (plugin/route, session-create,
  verb-with-`needs_confirm`, prompt-budget `extra=`, CSRF-at-transport,
  gitignored `.cache` scratch dir, argparse subgroup): the implementation risk
  is concentrated in the 2 places with no existing analogue — the
  natural-language fast-command normaliser/table, and the no-double-speech
  guard between `agents.js`'s per-chat autoRead and the new server-side
  reply watcher. Significance: plan/estimate effort here, not in the
  plumbing.
- **`tickets.create` alone does not satisfy the plan's `kickoff` verb** — it
  skips template rendering and the artifact-map row, both of which the
  existing `kickoff` *skill* already does via `New-FromTemplate.ps1`. The verb
  handler must orchestrate the same three steps the skill does (ticket.toml +
  trackers, template render via the same PS1, artifact-map append), not just
  call `tickets.create`. Significance: undersizing this task would produce a
  `kickoff` verb that creates a ticket with no rendered artifacts —
  functionally broken against the plan's own acceptance criterion (line 181:
  "produces `ticket.toml` only through `tickets.create` + template render").
- **No server-side-writable assistant settings endpoint is named in the
  plan's explicit route list**, yet "Settings backend picker" requires one
  (browser-local `localStorage`, the pattern every other Settings picker
  uses, cannot drive a server-spawned session's default backend). The
  `notify.py`/`ops_feature.py` prefs pattern is a directly reusable template.
  Significance: a testable AC for this must be added during
  `challenge-requirements` rather than left implicit, or an agent
  implementing from requirements alone could ship the backend picker as
  browser-local-only, which would not work.
- **The double-speech guard has no named mechanism yet** — the plan states
  the invariant ("must not double-speak with existing autoRead handler") but
  not the mechanism. `agents.js`'s `store` has no chat-identity check today.
  Significance: needs a concrete, testable AC (e.g. "the assistant's own
  chat's `autoRead` is force-disabled" or "`assistant.js` and `agents.js`
  coordinate via a shared flag") before build, or the two speaking paths will
  race in an ambiguous way that unit tests can't pin down.
- **BR-1 ("no second orchestrator") is structurally supported by the existing
  `telegram_bot._dispatch` shape** — a single `if/dict.get(...)` branch with
  one fallback path is the same shape the fast-command table needs, so BR-1
  is enforceable by code review/structure rather than needing new
  infrastructure. Significance: lowers implementation risk on the item the
  plan calls out as the single most important invariant.
- **T-003's deliverables are already present in the working tree**
  (`procs.py`, `logger.rs`, install scripts, `.cache/desktop/*.log`) even
  though `ticket.toml` for T-003 was not inspected here (out of scope) —
  T-004's stated dependency is satisfied in substance. Significance: no
  GROUND blocker from the dependency chain.

## Research

- Plan file (binding): `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md`,
  lines 143-231 (T-004 + T-005 sections, read for the seams between them —
  e.g. `native_bridge.py` and desktop verbs are T-005's job, T-004 only needs
  the always-unavailable stub).
- `console/server/features/verbs_feature.py`, `agents_feature.py` (full read).
- `console/server/telegram_bot.py` (full read) — `_dispatch` at :295,
  `Poller._loop`/`_handle` for the "one malformed input must not kill the
  loop" pattern, reusable as a design note for the fast-command handler.
- `console/server/prompt_build.py` (full read) — budget/truncation-honesty
  mechanism.
- `console/config/agents.toml`, `console/config/verbs.toml`,
  `console/config/plugins.toml` (full read).
- `console/server/agent_manager.py:1-230`, `console/server/agent_backends.py:190-530`,
  `console/server/agent_session.py` (grepped for `session_argv`/`system_append`/`build(`),
  `console/server/agent_api_session.py:60-129`.
- `console/server/audit.py:40-94` (`ACTIONS` tuple — confirms `chat.start`
  exists already; `assistant.say`/`kickoff` are not yet in the tuple and must
  be added for `audit.record` to accept them without silently mis-recording).
- `console/server/tickets.py:1-95` (`create`, `load`).
- `console/server/verbs.py` (grepped for `run`/`list_verbs`/`needs_confirm`).
- `.claude/skills/kickoff/SKILL.md`,
  `.claude/skills/template/scripts/New-FromTemplate.ps1` (full read).
- `console/tests/test_api_session.py:1-90` (fake-opener/`Provider` style for
  the `openai_api` transport — the pattern `test_assistant.py` and
  `test_native_bridge.py` should follow).
- `console/tests/test_telegram_bot.py` (grepped for fake-opener style —
  confirmed a `Fake` class at :33, same idiom).
- `console/static/agents.js:833-862` (autoRead / announce handlers),
  `console/static/settings.js` (full read — Settings tab panel patterns).
- `console/server/notify.py:55-153`, `console/server/features/ops_feature.py`
  (full read — the prefs read/write pattern proposed for assistant settings).
- `console/server/httpd.py` (grepped for CSRF — :181-182).
- `console/kanban.py` (grepped for subparser groups — no `assistant` group
  exists).
- `.gitignore:65-67` (`console/.cache/` already ignored).
- Glob checks (no matches, confirming net-new): `console/server/native_bridge.py`,
  `console/config/personas/**`, `console/config/assistant.*`.
- `python -m pytest` run from repo root, this session: exit code 0.
- `.claude/agents/` (7 files), `.claude/skills/` (41 entries) — roster counts.

## Recommended Path

Build T-004 as ten small, independently testable slices that each extend an
already-proven pattern rather than one large plugin: (1) `assistant_feature.py`
+ `plugins.toml` row + session pointer file, copying `agents_feature.py`'s
create/send/interrupt calls exactly; (2) thread `system_append`/`extra` through
`BaseSession` → `ApiSession.start`/`LiveSession` argv (two small, additive
parameter threads, not a redesign); (3) `console/config/assistant.md` +
`persona_text`'s second root; (4) the fast-command table as one
`telegram_bot._dispatch`-shaped module, unit-testable with no live backend;
(5) the `kickoff`/`tickets_digest`/`remember` verbs, with `kickoff` explicitly
re-using `New-FromTemplate.ps1` rather than porting it; (6)
`console/config/assistant.toml` + a small `GET`/`POST /api/assistant/settings`
pair modeled on `notify.py`/`ops_feature.py`, since the plan implies but does
not name this route — call this out explicitly in
`challenge-requirements`/the frozen requirements so build doesn't ship a
browser-local-only picker; (7) the reply watcher + `spoken_form()` +
`assistant.js`, with an explicit, named double-speech guard (also to be
pinned down as a testable AC, not left to the plan's prose); (8)
`native_bridge.py` as a stub that is honestly always-unavailable; (9) memory
file read/write under `console/.cache/assistant/`, capped and gitignored by
the existing blanket rule; (10) `kanban.py assistant say`. Each slice's tests
follow `test_api_session.py`'s fake-opener/no-network idiom. No change is
needed to `httpd.py`, `app.js`, or `.claude/agents/`, consistent with the
plan's explicit "untouched" list.

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
