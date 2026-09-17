---
ticket: "T-016"
artifact: analysis
---

# Analysis: T-016

## Context

The Delivery Console was built as a human kanban board (`console/`), then grew
an Agents tab, an MCP verb layer (CC-T002), an Assistant persona (T-004), talk
vs work (T-014), and a Tauri shell whose tray posts to `/api/assistant/say`
(T-001–T-015). Irshad asked to rethink that stack so it works as a workspace
OS for agents and the Assistant. Three product locks are already in
[[T-016-decision-log]]: Assistant is home in the native shell; harness roles
are launched as Runs but still *work* in Cursor; this is a ticket, not a wiki
note. T-015 remains in Verify and is out of scope.

## Current State

**Nav is board-first; the Assistant has no tab.**
`shell_feature.py` `NAV_ORDER` lists overview, two-to-four boards, then
`agents`, work, analytics, todos, vault, about, settings
(`console/server/features/shell_feature.py:17-30`). The assistant plugin is
enabled and has HTTP routes, but `assistant_feature.py:647-651` registers no
tab. `plugins.toml:81-88` still says “No tab of its own yet”. The desktop
shell loads that same loopback UI as the main webview
(`desktop/src-tauri/src/main.rs:218-222`) and only adds `html.in-shell`
(`main.rs:115-122`). Tray speech goes to `POST /api/assistant/say`
(`desktop/src-tauri/src/console_api.rs:6,41`), not to the Agents composer.

**Five starters, no shared run object.**
1. Board “Start agent” builds a prompt naming the ticket folder and calls
   `ConsoleAgents.compose` then `go("agents")` (`console/static/board.js:448-462`).
2. Assistant `say` reuses one chat pointed at by
   `console/.cache/assistant/session.json` (`assistant_feature.py:1-10,198-210`).
3. Agents tab is a coding IDE chat: backend, `/skill`, `@persona` read from
   the opening message (`console/static/agents.js:1-38`). Personas are the
   seven files under `.claude/agents/*.md` (`console/server/agents.py:121-143`).
4. Cursor / Claude Code speak MCP tools generated from `verbs.toml`
   (`console/server/mcp.py:11-16`; `.mcp.json` at repo root).
5. Schedules / `job submit` run **verbs**, not chats (`console/server/jobs.py:5-10,183-201`).

`console_delegate` starts a *chat* via `agent_manager.create` and optionally
watches it back into the Assistant session (`verb_handlers.py:191-208`). It
does not create a job record. `jobs.py:5` states the gap in one sentence:
“an agent run is a subprocess nobody is tracking.”

**Chats are not Runs.** `agent_manager.py:1-12` — sessions are process-memory;
transcripts on disk under `console/.cache/agent-chats/` are gitignored and
replay-only after restart unless the backend can resume (T-011). There is no
first-class `{id, role, ticket, backend, state, spend}` object spanning
Assistant, Agents, MCP, and Cursor.

**Verbs are the agent API and they are read-heavy.** `verbs.toml` ships
context, blockers, plan-status, artifacts, todos, harness-lint, telemetry,
skill-usage, agent-models, delegate, kickoff, tickets-digest, remember, and
desktop-* (19 rows). MCP `tools/list` walks that registry only
(`mcp.py:13-16`). `openai_api` agents hold the same verbs as `console_*`
tools plus workspace file/shell tools (`agent_tools.py:8-18,321-360`). CLI
backends “bring [their] own tools” (`agent_tools.py:3-4`).

The CLI can `ticket move` / `ticket set` and `tracker add|list|update`
(`kanban.py:629-665`; writers `tickets.py:157-188`). Those writers are **not**
verbs. An MCP agent that needs to change a lane today shells `kanban.py` or
edits files — the second is forbidden by harness rules.

**Wiki and shipping product disagree.** [[desktop-assistant]] still locks
“tray is a remote control of the live Agents chat” (wiki L12, L240-241) and
“Do not invent a second orchestrator” (L79). Shipping code is a second
conversation (Assistant) plus `console_delegate` plus the IDE harness.
T-004–T-015 already took the Assistant path; the wiki sentence is stale.

**Hybrid harness has no inbound Cursor API in this repo.** `.claude/agents/`
are prompt files. Console can `@persona` them onto a console chat
(`agents.py:138-141`) — that is a console-owned CLI/API session, which the
hybrid lock says is *not* where those roles work. Cursor IDE has MCP *into*
the console; the console has no cited way to start a Cursor Agent IDE chat
from the outside. How “launch a named Run that Cursor executes” is done is
an open confirmation, not a coded feature.

## Key Findings

- **Finding:** The product the human actually talks to (Assistant + tray) is
  a plugin without a home surface, while the default window is still the
  ten-tab board. **Significance:** “Assistant as home” is an IA change in the
  shell (`in-shell`), not a new backend.

- **Finding:** `console_delegate` and `jobs.JobQueue` are two incomplete Run
  shapes — one is a chat, one is a verb. **Significance:** a Run object is
  new data, not a rename. Overloading `jobs.py` without changing its
  “verb-only” contract would lie about agent work.

- **Finding:** Adding `ticket-move`, `ticket-set`, `tracker-add`,
  `tracker-update` as verbs automatically gives MCP and `openai_api` the same
  tools (`mcp.py` + `agent_tools.tool_definitions`). **Significance:** verb
  completeness is the cheapest agent-console win and matches CANONICAL (one
  mutation API). Gates already exist: `needs_confirm` vs `gated_tools`.

- **Finding:** Board `startAgentFor` bypasses the Assistant. **Significance:**
  if Assistant is home, that button is a product bug relative to the new
  intent, not a missing API.

- **Finding:** Hybrid “launch in Cursor” is unspecified in code.
  **Significance:** freeze-blocking. Pretending `agents launch cursor-agent`
  *is* Cursor would contradict [[T-016-decision-log]] hybrid-harness-runs.

- **Finding:** T-015 owns latency/tray/overlay honesty. **Significance:** do
  not retouch those paths except where Assistant-as-home requires a nav
  change.

## Research

- [[desktop-assistant]] — original shell architecture; tray=Agents lock now
  stale vs T-004.
- [[T-004-summary]] — Assistant brain, one reused chat, verbs kickoff /
  remember / tickets-digest.
- [[T-014-summary]] — talk vs work, `console_delegate`.
- [[T-011-summary]] — chat resume (CLI session id), not a Run.
- [[CC-T002-summary]] — verbs, context, jobs, MCP.
- Commits (subjects only): `7f9a672` agent body; `c601099` assistant you can
  talk to; `8cb29e4` Tauri shell; `2d66192` two models; `37d1aef` stop
  answering through a coding CLI.

## Recommended Path

Keep the kernel (tickets, verbs, gates, plugins). Do not add an agent
framework. Four slices, order forced by dependency: **C verb completeness**
can ship without UI and unblocks every agent immediately; **B Run object**
needs a storage decision (new records vs tagged union of chat-id / job-id /
cursor-pointer) before UI; **A wiki lock** is a same-day amend of
[[desktop-assistant]] once B’s shape is named; **D Assistant as home** is
`in-shell` nav + replace `startAgentFor`, after B so “live runs” have
something to show. Freeze must not proceed until the Cursor-launch question
is answered; everything else is enrichable from this survey.

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
- [[T-016-context-snapshot]] · [[desktop-assistant]] · [[T-015-summary]] · [[T-004-summary]] · [[T-014-summary]] · [[CC-T002-summary]]
