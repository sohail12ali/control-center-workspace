---
ticket: "T-004"
artifact: context-snapshot
status: draft
created: "2026-09-06"
last_updated: "2026-09-06"
scope: codebase + history
---

# Context Snapshot: T-004

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-004 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Make the future voice assistant testable by typing today: a console-owned
persona injected into every backend's system prompt, one `/api/assistant`
surface routing to a single reused "Assistant" chat, a deterministic
fast-command table that intercepts whole-utterance patterns before any model
call, a Settings-tab backend picker, and capped file-based memory — all with
no microphone and no native bridge (T-005) required.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Deterministic job registry (verbs) | `console/config/verbs.toml` → `console/server/verbs.py` → `console/server/verb_handlers.py` | config row, HTTP route (`verbs_feature.py`), CLI, MCP | `kickoff`/`tickets_digest`/`remember` are new rows in this exact registry; `needs_confirm` gating already implemented and tested | `console/server/verbs.py:145`, `console/config/verbs.toml:1-27` |
| Live agent chat session lifecycle | `console/server/agent_manager.py` (`create`/`send`/`interrupt`/`stop`) | HTTP (`agents_feature.py`), session process (`agent_session.py`/`agent_api_session.py`), audit | The Assistant chat is an ordinary call into `agent_manager.create`; no new session primitive needed | `console/server/agent_manager.py:41-87,179-198` |
| Inbound free-text command dispatch | `console/server/telegram_bot.py:_dispatch` | polling loop → prefix/dict lookup → handler, else free-text fallback | Exact dispatch shape (one match OR one fallback `send`) the fast-command table needs — structural proof BR-1 is enforceable | `console/server/telegram_bot.py:295-378` |
| Prompt assembly with stated budget/truncation | `console/server/prompt_build.py` | orientation + core + persona + skill + `extra` sections, char-budgeted | `extra=` param already exists and is budget-accounted; only the call-site plumbing to pass it from `agent_manager.create` down to `ApiSession.start`/`LiveSession` argv is missing | `console/server/prompt_build.py:100-154` |
| Committed-config + gitignored-overlay settings, HTTP read/write | `console/server/notify.py` (`load_prefs`/`apply_prefs`) + `console/server/features/ops_feature.py` (`POST /api/notify/prefs`) | config file, HTTP, Settings-tab JS panel | Direct template for a server-side-writable `console/config/assistant.toml` + `/api/assistant/...` settings route (backend/model/mode picker) — every OTHER Settings panel is browser-`localStorage`-only and cannot drive a server-spawned session | `console/server/notify.py:61-102`, `console/server/features/ops_feature.py:78-89` |
| Per-chat auto-read-aloud on the browser side | `console/static/agents.js:839-846` (`store.on("patch", ...)`) | any open chat store in the Agents tab | The exact place a double-speech guard must be added for the Assistant's own chat | `console/static/agents.js:833-862` |
| Kickoff artifact scaffolding (skill, not verb) | `.claude/skills/kickoff/SKILL.md` + `.claude/skills/template/scripts/New-FromTemplate.ps1` | ticket dir creation, template render, artifact-map append, `tickets.create` | The `kickoff` verb handler must orchestrate the same 3 steps (not just call `tickets.create`, which only writes `ticket.toml` + trackers) | `.claude/skills/kickoff/SKILL.md:15-20`, `console/server/tickets.py:38-73` |
| PS 5.1-safe template rendering | `New-FromTemplate.ps1:65,88` | `-Encoding UTF8` read, BOM-less `WriteAllText` write | Already fixed this session; the `kickoff` verb calls this script as-is | `.claude/skills/template/scripts/New-FromTemplate.ps1` |

### Existing patterns to reuse
- Plugin = module + `plugins.toml` row, never touch `httpd.py` — `console/server/features/verbs_feature.py:1-102,96-101`.
- CSRF enforced once at the transport layer (`X-Console-Request: 1`), not per-plugin — `console/server/httpd.py:181-182`.
- Every mutating HTTP call wrapped in `audit.record(...)`, success and failure both — `console/server/features/verbs_feature.py:34-46`; `ACTIONS` tuple must list a new action before `audit.record` treats it as expected — `console/server/audit.py:43-54` (does not yet contain `assistant.say`/`kickoff`).
- Backend argv templates drop an optional flag whose placeholder resolves empty, already generalised in `_expand` — `console/server/agent_backends.py:205-239` — so `"--append-system-prompt", "{system_append}"` needs no new logic there, only a new template row plus a value to feed it.
- `.cache/` is a single blanket-gitignored tree; `console/.cache/assistant/` needs no new `.gitignore` entry — `.gitignore:65-67`.

### Naming and architectural conventions in play
- `CLAUDE.md` § Rules: "Ticket + tracker state lives in TOML under the ticket dir, mutated only via `console/kanban.py`" — the new `assistant` CLI group follows the existing `argparse` subparser-per-domain shape (`console/kanban.py:499-792`, e.g. `agents_cmd` at `:607`).
- `CLAUDE.md` § Order: "Exactly 7 agents — no additions without explicit user intent" — confirmed still true (`.claude/agents/` has exactly 7 files); the assistant is explicitly not an 8th agent per the binding plan (line 33, 179).
- Harness core.md CANONICAL gate ("every fact lives in exactly one file") — the backend-picker default must live in `console/config/assistant.toml`, not duplicated into `agents.toml` or browser `localStorage`.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-001 | Native Tauri shell spike around the console (`desktop/`) | Complete (all 8 ACs PASS, closed in T-003's VERIFY pass) | Shell↔server IPC today is only `eval`/a `desktop-session` DOM event, no Tauri commands/plugins yet — relevant if T-004 ever needs the shell to call `/api/assistant` directly (T-005's concern, not T-004's) — `knowledge-center/artifacts/T-003/T-003-summary.md:26` |
| T-002 | Tray remote (Show/New chat/Mute/Interrupt/Quit) | 9 PASS / 4 PENDING / 1 PARTIAL; not fully closed (manual click-through pending) | Tray icon states / listening modes are T-005/T-006 work, out of scope here | `knowledge-center/artifacts/T-003/T-003-summary.md:26` |
| T-003 | Shell hygiene: stray-console fix, `procs.py`, per-OS launch, CI matrix, close T-001/T-002 | **Complete**, closed 2026-09-06 — `python -m pytest` went 758→783 passed, 0 regressions | T-004's stated dependency is fully satisfied, not merely "artifacts present" as first read from git status; the ticket itself is closed | `knowledge-center/artifacts/T-003/T-003-summary.md` (frontmatter `status: Complete`) |

### Relevant commits / PRs
- `8cb29e4` "Add a native Tauri shell and tray remote for the Delivery Console" — T-001/T-002 landing.
- `f8ffbc2` "Two kinds of agent, inline / @ # references, and a foldable chat list" — prior Agents-tab composer work (the `#`/`@`/`/` picker `settings.js` toggles reference).
- `447aa25` "Fix the composer clipped to 4px, and mark references that resolve" — recent Agents-tab UI polish, unrelated to T-004 directly but same file family (`agents.js`).

### Known incidents / regressions in this area
- None specific to the assistant surface (it does not exist yet). T-003's own dossier (`knowledge-center/memory/stray-terminal-root-cause.md` per user memory index) covers the stray-console defect, already fixed and out of scope here.

## 4. External Systems in the Loop

- **Claude CLI** (`claude`) — `--append-system-prompt` flag, verified present (plan line 26); the persona-injection mechanism for the `stream_json` transport.
- **cursor-agent CLI** — no system-prompt flag; persona must be prepended to the first turn's prompt instead (plan line 151; confirmed no such row in `agents.toml:142-179`).
- **OpenRouter / Ollama / LM Studio** (`openai_api` transport) — persona reaches these via `prompt_build.build`'s existing `extra=`/persona/skill sections, no CLI-flag concern.
- **Telegram** (existing inbound bot, `telegram_bot.py`) — the plan's "Suggestions beyond the ask" section proposes routing the same `/api/assistant/say` behind `_dispatch`'s free-text fallback later; not in T-004's explicit route list and not required for this ticket's ACs.
- **Windows PowerShell 5.1** — `kickoff` verb's template render depends on it; plan states an honest fallback (verb errors, fast command sends `/kickoff {id} --title` to chat) when PowerShell is unavailable (cross-platform honesty requirement).

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- **Windows argv length cap (~32k)** — `--append-system-prompt` carries the full persona text; the plan caps it at ≤8k chars but the actual `session_argv` build (`agent_backends.py:491-505`) has no length assertion today. Would bite if a future edit to `assistant.md` grows past the cap silently.
- **No server-side-writable Settings route named for the backend picker** — if build ships only a `localStorage`-backed picker (copying `agentBackends` in `settings.js`), the Assistant's server-spawned session cannot read the user's choice at all. Would bite the moment two people share a checkout, or the composer's browser prefs differ from what a headless `kanban.py assistant say` invocation should use.
- **Double-speech mechanism unnamed** — `agents.js:839-846`'s `autoRead` has no chat-identity awareness; the new server-side reply watcher has no negotiation with it yet. Would bite as soon as a user opens the Assistant chat in the Agents tab with autoRead on while also using voice/typed `say`.
- **`agent_manager.send`'s busy/queued semantics live inside `sess.send`, not the manager** — the fast-command handler must inspect `sess.send`'s return shape correctly to render "Still working — queued" instead of assuming a manager-level flag exists. Would bite as a silently wrong reply.
- **`tickets.create` alone under-delivers the `kickoff` verb's stated AC** (line 181: "produces `ticket.toml` only through `tickets.create` + template render") — building the verb as a thin wrapper around `tickets.create` (as `agents_feature.chat_new` wraps `agent_manager.create`) would ship a ticket with no rendered markdown artifacts. Would bite as a `kickoff` fast command that "succeeds" but leaves a ticket dir with only `ticket.toml`.

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. Convert to open questions via `clarify` if any would change the draft.

- Whether `agent_manager.send`'s "queued" branch already exists inside `sess.send` with the exact wording "Still working — queued" or whether that is user-facing copy the fast-command handler must compose itself — not traced into `agent_session.py`'s queue internals during this GROUND pass (out of the explicitly-named files list). Would change an AC's exact wording, not the requirement itself; not blocking.
- Whether `console/config/personas/` (the plan's second `persona_text` root) is meant to hold *only* `assistant.md`-equivalent files or is a general multi-persona directory for future non-CLI personas — the plan names one file (`assistant.md`) but a directory-root design. Treated as: the directory exists so a second file could be added later without another `prompt_build.py` change; not blocking since T-004 only needs one file in it.

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-06 | Read | `our-project-is-in-optimized-treasure.md` (full) | Binding source of truth for all 11 delivery points |
| 2026-09-06 | Read | `console/server/features/verbs_feature.py`, `agents_feature.py` | Plugin/route template + session-create template |
| 2026-09-06 | Read | `console/server/telegram_bot.py` (full) | Fast-command dispatch shape (`_dispatch` ~line 295) |
| 2026-09-06 | Read | `console/server/prompt_build.py` (full) | Persona/skill/budget/`extra=` mechanism |
| 2026-09-06 | Read | `console/config/agents.toml`, `verbs.toml`, `plugins.toml` (full) | Current backend rows, verb registry shape, plugin registry shape |
| 2026-09-06 | Grep+Read | `console/server/agent_manager.py`, `agent_backends.py:190-530`, `agent_session.py`, `agent_api_session.py:60-129` | Session lifecycle, `session_argv`/`_expand`, `ApiSession.start` |
| 2026-09-06 | Grep | `console/server/audit.py:40-94` | `ACTIONS` tuple — confirms `assistant.say`/`kickoff` not yet listed |
| 2026-09-06 | Read | `console/server/tickets.py:1-95` | `create`'s actual scope (no template render, no artifact-map row) |
| 2026-09-06 | Grep | `console/server/verbs.py` | `needs_confirm` gate already enforced |
| 2026-09-06 | Read | `.claude/skills/kickoff/SKILL.md`, `New-FromTemplate.ps1` (full) | Kickoff-skill steps the verb must mirror; PS 5.1 fix confirmed in place |
| 2026-09-06 | Read | `console/tests/test_api_session.py:1-90` | Fake-opener/no-network test idiom for `openai_api` transport |
| 2026-09-06 | Grep | `console/tests/test_telegram_bot.py` | Confirms a `Fake` class idiom, same style |
| 2026-09-06 | Grep+Read | `console/static/agents.js:833-862`, `settings.js` (full) | autoRead handler; every Settings panel's persistence mechanism |
| 2026-09-06 | Read | `console/server/notify.py:55-153`, `features/ops_feature.py` (full) | Committed-config + overlay + HTTP prefs pattern to copy for assistant settings |
| 2026-09-06 | Grep | `console/server/httpd.py` | CSRF already enforced at transport layer |
| 2026-09-06 | Grep | `console/kanban.py:499-792` | No `assistant` subparser group exists yet |
| 2026-09-06 | Glob | `console/server/native_bridge.py`, `console/config/personas/**`, `console/config/assistant.*` | Confirmed net-new (no matches) |
| 2026-09-06 | Bash | `python -m pytest` (repo root) | Exit code 0 — baseline green |
| 2026-09-06 | Bash | `git log --oneline --grep="assistant\|voice\|tray\|persona" -i` | 4 relevant commits, all T-001/T-002/composer work |
| 2026-09-06 | Read | `knowledge-center/wiki/desktop-assistant.md` (full) | Durable design doc predating the plan — architecture, safety rules, non-goals still binding |
| 2026-09-06 | Read | `knowledge-center/artifacts/T-003/T-003-summary.md` | T-003 is Complete/closed, not merely artifacts-present |
| 2026-09-06 | Bash | `ls .claude/agents/`, `ls .claude/skills/` | 7 agents, 41 skill entries confirmed |
| 2026-09-06 | Grep+Read | `console/server/agent_events.py`, `agent_manager.py:100-151`, `agent_session.py:355-404` | `requirements enrich` pass: confirmed which of `turn.start`/`attention`/`reply`/`turn.end`/`speaking.*` already publish, and the `session.started`→`meta` plumbing used for FR-8's `is_assistant` guard |
| 2026-09-06 | Read | `console/server/prompt_build.py:95-154` | `requirements enrich` pass: exact truncate-plus-stated-marker text for FR-3/FR-4's shared pattern |
| 2026-09-06 | Read | `console/static/agents.js:825-868` | `requirements enrich` pass: exact `autoRead` handler lines guarded by FR-8's new mechanism |
| 2026-09-06 | Grep | `console/server/notify.py:60-99`, `audit.py:40-54` | `requirements enrich` pass: additive-config `.get(key, default)` pattern (DATA-GAP-2) and current `ACTIONS` tuple |
| 2026-09-06 | Bash | `grep -n "T-004" our-project-is-in-optimized-treasure.md` (full section) | `requirements enrich` pass: re-confirmed plan.md:74 (no pwsh prerequisite off-Windows) and plan.md:145 (exact 5-event SSE filter) |

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements-draft]] · [[T-004-context-snapshot]] · [[T-004-gap-analysis]] · [[T-004-iteration-log]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
