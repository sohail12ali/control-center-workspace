---
ticket: "T-016"
artifact: requirements-draft
status: frozen
freeze_status: frozen
frozen_at: "2026-09-11"
frozen_iteration: 1
iteration: 1
created: "2026-09-11"
last_updated: "2026-09-11"
---

# Requirements Draft: T-016

> Working requirements document. **Not frozen.** Expect revisions each iteration until `requirements T-016 freeze` passes.

**Command reference:**
- **Created by:** `requirements T-016 draft`
- **Grounded by:** `analyze T-016` → writes [[T-016-context-snapshot]]
- **Gaps surfaced by:** `challenge-requirements T-016 (gaps dimension)`
- **Challenged by:** `challenge-requirements T-016` (adds ⚠ markers below)
- **Enriched by:** `requirements T-016 enrich [source]`
- **Cross-checked by:** `challenge-requirements T-016 (overlap/conflict/reuse dimension)`
- **Iterated by:** `requirements T-016 iterate "feedback"`
- **Frozen by:** `requirements T-016 freeze` → produces `T-016-requirements.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** The desktop Assistant is the home screen, and every piece of work is a Run you can watch.

**Business driver:** Agents and the Assistant already use the console as a backend; the window is still a human kanban app. That mismatch is why talk, board "Start agent", Cursor, and `console_delegate` feel like four products.

**Raw intent verbatim:**
> I want to rethink the delivery console to work better with agents and assistant.

**Interpretation:** Invert IA in the native shell (Assistant is a new first tab when `in-shell`); introduce a Run as a tagged-union record; complete four mutation verbs; launch harness roles as console `cursor-agent` chats with `@persona` ([[T-016-decision-log]]).

## 2. Context Summary

(Condensed from [[T-016-context-snapshot]])

- **Similar existing features:** Agents tab + `agent_manager` chats ([[T-011-summary]] resume); Assistant `/api/assistant` ([[T-004-summary]]); `console_delegate` ([[T-014-summary]]); verb registry + MCP ([[CC-T002-summary]]); job queue for verbs (`jobs.py`); ticket/tracker CLI writers (`tickets.py`, `kanban.py`); Tauri `in-shell` (`main.rs:115-122`).
- **Affected code areas:** `console/server/features/{shell,assistant,agents}_feature.py`, `console/static/{board,agents,app}.js`, `console/config/verbs.toml`, `console/server/{mcp,agent_tools,jobs,tickets,trackers,verb_handlers}.py`, `desktop/src-tauri/src/main.rs`, `knowledge-center/wiki/desktop-assistant.md`.
- **Known risks from history:** wiki tray=Agents lock vs tray→`/api/assistant/say`; T-015 still open on latency/tray — isolate.

## 3. Scope

### In scope
- Native-shell home: new Assistant **tab**, first in `NAV_ORDER` when `html.in-shell`; other tabs stay in the strip ([[#in-shell-home-is-first-tab]]).
- Amend [[desktop-assistant]] so the tray remotes the Assistant, not “the live Agents session”.
- Durable Run object the Assistant, board, schedule, and MCP can start and the UI can watch.
- Agents tab becomes the Run inspector / transcript history, not a parallel product.
- Board “Start agent” becomes ask-the-Assistant or create-a-named-Run (`board.js:448-462` today).
- Console launches a named harness role as a Run by spawning a `cursor-agent` CLI chat with that persona ([[#harness-via-cursor-agent-cli]]).
- Verbs for `ticket move`, `ticket set`, `tracker add`, `tracker update` only.

### Out of scope (explicit)
- T-015 remaining verify (latency, tray honesty, overlay) — separate ticket.
- Deleting tabs.
- In-console GROUND→VERIFY loop / new harness agents.
- New model backends, new desktop capture/voice features.
- Agents hand-editing `ticket.toml` or tracker TOML.
- Changing `kanban.py serve` browser-first nav (assistant-as-home impact: browser may keep existing nav).
- Full-bypass of gated tools.

### Assumptions
- Plugin + verb registry remain the extension points. Confirmed by convention (`plugins.toml`, `verbs.toml`).
- `cursor-agent` may be missing on a machine — launch fails honestly, no silent fallback to `claude` ([[#harness-via-cursor-agent-cli]]).

## 4. Functional Requirements

### FR-1: Native shell opens on the Assistant
**Description:** When the Tauri shell shows the main window (`html.in-shell`), a new Assistant tab is first in the nav: talk, live runs, ticket strip. Other console tabs remain in the strip. Plain `kanban.py serve` in a browser keeps today’s nav (Overview first).

**Actor:** Person using the desktop shell

**Trigger:** Open/show the main window, or a tray action that shows the window

**Preconditions:**
- Desktop shell is running and the console sidecar is up (`main.rs:218-222`).

**Flow:**
1. Shell loads the loopback console with `in-shell` class (`main.rs:115-122`).
2. Home view is the Assistant tab, registered via `register_tab`, sorted first only when `in-shell` ([[#in-shell-home-is-first-tab]]).
3. Person can open a drawer (Tickets, Agents inspector, Work, …) and return home without losing the Assistant session pointer (`assistant/session.json`).

**Postconditions / observable outcomes:**
- First painted main surface in-shell is Assistant home.
- Browser without `in-shell` is unchanged.

**Acceptance criteria (testable):**
- [ ] A test or in-shell check: `document.documentElement.classList.contains("in-shell")` shows Assistant home as the default view; without the class, `NAV_ORDER` behaviour is unchanged (`shell_feature.py:17-30`).
- [ ] Overview, boards, Agents, Work, Analytics, Todos, Vault, Settings remain reachable (not deleted).
- [ ] Reused Assistant chat is the same session the tray `POST /api/assistant/say` uses (`console_api.rs:41`, `assistant_feature.py:198-210`).

**Business rules invoked:** BR-2, BR-4

### FR-2: Every piece of work is a Run you can watch
**Description:** Starting work from the Assistant, the board, a schedule, or MCP creates (or points at) a Run record under `console/.cache/runs/` that points at a chat id and/or job id and/or cursor-pointer ([[#run-is-tagged-union]]). The Assistant tab can list live/recent Runs.

**Actor:** Person, Assistant talk model, MCP client

**Trigger:** Delegate, named launch, board start-run, or `console_delegate`

**Preconditions:**
- Console server running if the Run needs an approval card (`verb_handlers.py:184-189`).

**Flow:**
1. Caller creates a Run (tagged union; usually `chat` for delegate and harness launch).
2. State is one of at least: queued, running, needs-approval, done, failed, interrupted (jobs already distinguish interrupted vs error — `jobs.py:20-27`).
3. Assistant home and the inspector show that state. Approvals still use the existing card.

**Postconditions / observable outcomes:**
- A Run id exists that `console context` or a new verb can return.
- `console_delegate` either creates a Run or is wrapped so the work chat is watchable as one.

**Acceptance criteria (testable):**
- [ ] After `console_delegate`, the Assistant can name the work’s id and state without the person switching tabs.
- [ ] Restarting the console does not silently invent a second identity for an in-flight Run (durable record; contrast `agent_manager.py:1-6` process-memory sessions).
- [ ] Two starters (Assistant delegate and board create-run) produce the same record type.

**Business rules invoked:** BR-1, BR-5, BR-6

### FR-3: Board starts a Run or asks the Assistant
**Description:** The ticket drawer no longer dumps a prompt into the Agents composer (`board.js:448-462`). It asks the Assistant or creates a named Run for that ticket.

**Actor:** Person on the board

**Trigger:** Click the primary ticket action currently labelled “Start agent”

**Preconditions:** Ticket exists.

**Flow:**
1. Person opens a ticket drawer.
2. Primary action creates a Run for that ticket and/or sends a `say` to the Assistant naming the ticket.
3. Window stays on Assistant home in-shell (or focuses Assistant); it does not `go("agents")` as the success path.

**Acceptance criteria (testable):**
- [ ] `startAgentFor` no longer calls `ConsoleAgents.compose` + `go("agents")` as the only path.
- [ ] The action is ticket-scoped (Run.ticket or Assistant turn cites the id).
- [ ] Agents tab still exists as inspector if the Run has a console transcript.

**Business rules invoked:** BR-2

### FR-4: Agents tab is the Run inspector
**Description:** The Agents tab lists Runs (and still shows console chat transcripts for Runs that are chats). Composer “new chat” is “new Run”, not a second product with a different lifecycle.

**Actor:** Person inspecting work

**Trigger:** Open Agents drawer/tab

**Acceptance criteria (testable):**
- [ ] A Run created by `console_delegate` appears in that list with the same id the Assistant named.
- [ ] Harness personas remain selectable only as a Run role, not as a silent `@persona` that creates an untracked chat (`agents.py:138-141` today).
- [ ] Existing chat resume (T-011) still works for chat-backed Runs.

**Business rules invoked:** BR-5

### FR-5: Pipeline mutations are verbs
**Description:** `ticket move`, `ticket set`, `tracker add`, and `tracker update` become `verbs.toml` rows that call the existing `tickets`/`trackers` functions. MCP and `openai_api` tools appear automatically. Same `needs_confirm` / lane validation as the CLI. progress-append, close-work, and log-work are **not** in this ticket ([[#verbs-this-ticket]]).

**Actor:** MCP client, Assistant/API agent, palette

**Trigger:** Tool/verb call

**Preconditions:** Ticket id valid; stage valid for move (`tickets.py:157-165`).

**Flow:**
1. New verb rows; handlers are one-liners to existing writers (`verb_handlers.py` convention).
2. `needs_confirm=true` on mutating rows (`verbs.toml:25-30`).
3. CLI `kanban.py ticket move` remains and shares the writer.

**Acceptance criteria (testable):**
- [ ] `python console/mcp_server.py` `tools/list` includes `console_ticket_move` (or the `console_` + id name from `agent_tools.verb_tool_name`) and tracker add/update.
- [ ] Invalid lane fails with the same error class as `tickets.move` (`tickets.py:163-165`).
- [ ] No test or docs instruct hand-editing `ticket.toml`.
- [ ] Pytest covers the new handlers (stdlib console tests).

**Business rules invoked:** BR-1

### FR-6: Launch a harness role as a named Run (hybrid)
**Description:** The console creates a Run whose role is analyst, planner, builder, verifier, fixer, harness, or deployer for a ticket by starting a `cursor-agent` CLI chat with that persona (`agents.toml` id `cursor-agent`, transport `resume`). No in-console GROUND→VERIFY loop. If the backend is not installed, fail and name it; do not fall through to `claude`.

**Actor:** Person or Assistant

**Trigger:** “Run analyst on T-016” (fast command, verb, or Assistant tool)

**Acceptance criteria (testable):**
- [ ] Creating the Run starts `agent_manager.create` with backend `cursor-agent` and persona set to the role (catalog id from `agents.py:138-141`).
- [ ] The Run record’s executor is that chat id (tagged union `chat`).
- [ ] Missing `cursor-agent` → error naming the backend; `claude` is not started.
- [ ] `.claude/agents/` remains seven files; no eighth harness agent.
- [ ] No new Python pipeline that runs GROUND→VERIFY inside the console process.

**Business rules invoked:** BR-3, BR-5

### FR-7: Wiki lock matches shipping Assistant
**Description:** [[desktop-assistant]] stops saying the tray remotes the live Agents session (wiki L12, L240-241). It states: tray remotes the Assistant; work is Runs; no second orchestrator still holds.

**Actor:** Maintainer / future tickets

**Acceptance criteria (testable):**
- [ ] Grep of `desktop-assistant.md` has no “live Agents session” tray lock.
- [ ] The page wikilinks [[T-016-summary]] and the three kickoff decisions.

**Business rules invoked:** BR-2

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | Assistant home must not add a network probe on window show | Zero new sockets on first paint of home; reuse T-015 `settings_get` no-probe | Grounded in T-015 defect |
| Scalability | Concurrent chat-backed Runs | Same as today: one subprocess per chat (`agent_manager`); do not reuse `[jobs] max_concurrent` for chats ([[#run-is-tagged-union]]) | Jobs stay verb-only |
| Security / Auth | No new auth; loopback + `X-Console-Request`; gated tools stay gated | Unchanged | `console.toml` |
| Auditability | Run start/end and ticket/tracker verb calls are audit events | Same `[audit]` log as chats/verbs | `audit.py` |
| Availability | Browser `serve` without shell keeps working | No shell-only Python imports in console kernel | stdlib-only |
| Usability | Spoken Assistant replies still lead with the answer | Existing `assistant.md` reply contract | Do not rewrite persona except Run-watch instructions |
| Compliance | N/A — local workspace tool | N/A — rationale: no regulated data store added | |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Run | new | id, ticket, role, executor tagged union (chat_id / job_id / cursor_pointer), state, created, updated, spend? | create → running → needs-approval? → done/failed/interrupted | plan-to-create `console/.cache/runs/` gitignored |
| ticket.toml | exists | stage/owner/… via new verbs | unchanged schema | `tickets.py` |
| tracker items | exists | questions/bugs/todos | add/update via new verbs | `trackers.py` |
| Assistant session pointer | exists | sid, backend, model | unchanged | `console/.cache/assistant/session.json` |

### Data flows
Person/Assistant/MCP → verb or `say` → Run record → executor (chat / Cursor / job) → state updates → Assistant home + inspector.

### Retention / archival
Gitignored under `console/.cache/` like chats and jobs (`agent_manager.py:8-12`, `jobs.py:48`). Not vault artifacts unless a future ticket says otherwise.

## 7. Business Rules

- **BR-1:** Ticket and tracker TOML mutate only through console writers (CLI, HTTP, verbs). Never hand-edit.
- **BR-2:** Do not add a second orchestrator (no LangGraph/CrewAI; wiki L79). Assistant talks and creates Runs; it does not become harness.
- **BR-3:** Exactly seven role agents in `.claude/agents/`. Assistant stays `console/config/assistant.md`.
- **BR-4:** `kanban.py serve` without `in-shell` keeps current nav.
- **BR-5:** A Run record points at a chat, a job, and/or a cursor-pointer. Harness launch in T-016 uses the chat arm (`cursor-agent`). ([[#run-is-tagged-union]], [[#harness-via-cursor-agent-cli]])
- **BR-6:** `needs_confirm` is the stray-click guard; `gated_tools` is the human card. New verbs follow that split (`verbs.toml:25-30`).
- **BR-7:** T-015 paths are not in this ticket’s done criteria.

## 8. Edge Cases

- Console down: tray `say` already fails honestly; new Run verbs fail the same way.
- Delegate with no work backend: keep current refuse-on-talk-model (`verb_handlers.py:168-172`).
- Invalid ticket lane on `ticket-move`: reject, do not coerce.
- Two people/starters on one ticket: two Runs allowed; do not silently merge.
- CLI backend without MCP: new verbs exist but that CLI will not hold them unless MCP loaded — UI/docs must say so (`agent_tools.py:3-4`).
- Job orphan vs chat death: Run state `interrupted`, not `done` (`jobs.py:20-27`).
- Missing `cursor-agent`: launch fails with the backend id named; no silent `claude` fallback.

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[T-004-summary]] Assistant chat | reuse | low | extend home view; keep `say` |
| [[T-014-summary]] `console_delegate` | overlap | med | wrap as Run; do not fork a second delegate |
| [[T-011-summary]] resume | reuse | low | chat-backed Runs resume as today |
| [[CC-T002-summary]] verbs/MCP/jobs | reuse | med | add rows; do not invent a parallel tool table |
| Agents tab composer | overlap | high | become inspector; avoid two lifecycles |
| Board `startAgentFor` | conflict | high | replace (FR-3) — would violate Assistant-as-home if left |
| [[desktop-assistant]] tray=Agents | conflict | high | amend wiki (FR-7) |
| [[T-015-summary]] tray/HUD/fast talk | isolate | med | do not retouch except nav/home |
| `jobs.py` verb queue | isolate | low | Q2 — do not extend to chats |
| `.claude/agents` @persona | overlap | med | FR-4/FR-6 — role on a Run, not untracked prefix |

## 10. External Dependencies

- Cursor IDE — not required for harness launch in T-016 (Q1b). `cursor-agent` CLI on PATH is required for FR-6.
- Existing backends in `agents.toml` — unchanged rows.
- PowerShell 5.1 — template render only if kickoff-like verbs added; not required for ticket-move.
- Telegram — no new event types required; reuse approval/turn_end.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Product / user | Irshad | Home IA, hybrid Cursor, freeze | yes |
| Implementer | Sohail Ali | Storage, verbs, shell nav | no |
| Future agents | MCP/Cursor | Verb completeness | no |

## 12. Open Questions (mirrored)

- Q1: How does the console launch a harness role if Cursor IDE has no inbound start API? — status: answered — `cursor-agent` CLI chat
- Q2: What is a Run in storage? — status: answered — tagged union
- Q3: Extra verbs this ticket? — status: answered — defer
- Q4: in-shell home IA? — status: answered — new first tab

## 13. Challenge Findings (⚠)

- ⚠ [unstated-assumption] §3 Assumptions: “Cursor” = IDE not `cursor-agent` CLI — resolution: resolved: requirements iterate 2026-09-11 Q1b
- ⚠ [untestable] §FR-6: launch AC cannot be observed until Q1 picks a mechanism — resolution: resolved: FR-6 AC now names `cursor-agent` + persona
- ⚠ [contradiction] §FR-2 vs `jobs.py:5`: jobs claim to be how work is tracked but only run verbs — resolution: resolved: Q2 tagged union; jobs stay verb-only
- ⚠ [ambiguity] §FR-1: “drawers” vs tabs not specified (Q4) — resolution: resolved: new first tab
- ⚠ [scope-creep] §FR-5: Q3 verbs (progress/close-work/log-work) are not in the locked In list — resolution: resolved: deferred
- ⚠ [spof] §10: hybrid Run that only works if Cursor is already open — resolution: accepted: `cursor-agent` missing is an honest fail, not a Cursor-IDE SPOF
- ⚠ [nfr-unmeasurable] §5 Scalability: Run cap “if jobs reused” — resolution: resolved: chats not under jobs cap

## 14. Draft History

See [[T-016-iteration-log]] for per-iteration diff + rationale.

Current iteration: **1**

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred
- [x] Out-of-scope list is non-empty
- [x] Every FR has at least one testable acceptance criterion
- [x] All ⚠ findings resolved or explicitly accepted with rationale
- [x] All blocker open questions answered (Q1–Q4 answered 2026-09-11)
- [x] Every NFR has a concrete target or documented reason for absence
- [x] Every new/changed entity has a canonical reference or creation plan (`console/.cache/runs/`)
- [x] Stakeholder sign-off recorded (Irshad Q1–Q4 + full stack, 2026-09-11)
- [x] `T-016-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements-draft]] · [[T-016-context-snapshot]] · [[T-016-gap-analysis]] · [[T-016-iteration-log]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
