---
ticket: "T-016"
artifact: context-snapshot
status: draft
created: "2026-09-11"
last_updated: "2026-09-11"
scope: codebase + history
---

# Context Snapshot: T-016

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-016 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Make the Assistant the home, and every piece of work a Run you can watch — native shell opens on talk + live runs + ticket strip; agents mutate the vault through verbs; harness roles still execute in Cursor.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Agents tab + chats | `/api/agents/*`, `agents.js` | plugin, `agent_manager`, four transports | Inspector / transcript host for Runs that *are* chats | `agents_feature.py:22-37`, `agent_manager.py:1-12` |
| Assistant one-chat | `/api/assistant/say` | plugin, `assistant_commands`, persona | Human face; already tray-wired | `assistant_feature.py:1-20,180-210`, `plugins.toml:81-88` |
| `console_delegate` | verb `delegate` | verb + `agent_manager.create` | Starting work from talk; not a Run record | `verb_handlers.py:132-214`, `verbs.toml:103-108` |
| Verb registry + MCP | `verbs.toml`, `mcp_server.py` | config → CLI / HTTP / MCP / API tools | Adding a row adds the agent tool | `mcp.py:11-16`, `agent_tools.py:338-360` |
| Job queue | `jobs.JobQueue.submit` | durable JSON under `.cache/jobs` | Durability pattern; **verb-only** today | `jobs.py:1-10,183-201` |
| Ticket/tracker writers | `kanban.py ticket|tracker` | `tickets.py`, `trackers.py` | Wrap as verbs; do not duplicate | `kanban.py:629-665`, `tickets.py:157-188` |
| Desktop shell | Tauri main webview | `desktop/src-tauri` | `in-shell` class for home IA; tray already → Assistant | `main.rs:115-122,218-222`, `console_api.rs:6,41` |
| Harness personas | `.claude/agents/*.md` | glob into Agents catalog | `@persona` on a console chat; **not** Cursor IDE launch | `agents.py:121-143` |
| Fast commands | `assistant_commands` | pure match table | Keep; home view still uses `say` | `assistant_feature.py:12-21` |

### Existing patterns to reuse
- Plugin + `register_tab` + `plugins.toml` row — never edit `httpd.py` (`plugins.toml:1-9`, `console` skill).
- Verbs: one handler signature `(repo_root, ticket=None, **args)`, `needs_confirm` vs `gated_tools` (`verbs.toml:21-30`).
- Tool names for verbs: `console_` + id with hyphens to underscores (`agent_tools.py:321-325`).
- Approval cards already interrupt Assistant (T-015 `POST /api/assistant/approve` — do not rework).
- `html.in-shell` is the existing fork between browser and native chrome (`main.rs:115-122`).

### Naming and architectural conventions in play
- Ticket/tracker TOML is CLI-mutated only (`CLAUDE.md` / `consolidate`).
- Stdlib-only `console/` — no pip (`console/README.md`).
- Assistant is not an 8th `.claude/agents/` file (`assistant.md`, `assistant_feature.py:151-157`).
- Four transports; only `openai_api` holds console verbs as tools (`agent_tools.py:3-4`).
- Jobs track verbs; chats are a different store (`jobs.py:5-10` vs `agent_manager.py:8-12`).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| [[CC-T002-summary]] | verbs, `context`, worktrees, job queue, MCP | Complete | Agent API = verb registry |
| [[CC-T003-summary]] | `openai_api` loop, skill injection | Complete | API backends get verbs; CLIs do not unless MCP |
| [[T-001-summary]] | Tauri shell wrapping console | Complete | Shell loads the *same* web UI |
| [[T-004-summary]] | Assistant brain, `/api/assistant`, memory | Complete | Second conversation, no tab |
| [[T-011-summary]] | Resume CLI chats | Complete | Resume ≠ Run lifecycle |
| [[T-014-summary]] | Talk vs work, `console_delegate` | Complete | Work is a second chat, notice back |
| [[T-015-summary]] | Fast talk, honest tray, dismissible HUD | Verify (open) | Out of scope; do not absorb |

### Relevant commits / PRs
- `7f9a672` CC-T002 Phase 1 - agent body: verbs, one-call context, worktrees, job queue, MCP
- `c601099` Teach the console to be an assistant you can talk to
- `8cb29e4` Add a native Tauri shell and tray remote for the Delivery Console
- `2d66192` Give the Assistant two models, and a way to hand work over
- `37d1aef` Stop answering "what's open?" through a coding CLI
- `d2840ed` Let a conversation outlive the process that was having it

### Known incidents / regressions in this area
- T-015: talk pinned to Claude CLI because local models failed preflight; settings GET probed the network (2026-09-10). Not this ticket.
- Wiki vs code: tray remotes Agents session ([[desktop-assistant]] L12, L240) vs tray posts `/api/assistant/say` (`console_api.rs:41`). Product contradiction T-016 must resolve in the wiki, not by reverting the Assistant.

## 4. External Systems in the Loop

- Cursor IDE (this workspace) — MCP client of `console/mcp_server.py`; no inbound “start Task” API found in-repo.
- Claude Code CLI / Cursor Agent CLI — backends in `agents.toml`; optional MCP if those CLIs load `.mcp.json`.
- OpenRouter / Ollama / LM Studio — `openai_api` talk/work models.
- Telegram — approval/turn_end notify (`console.toml` `[notify]`); must not grow new approval classes here (wiki privacy).
- Native shell sidecar — already owns mic/pixels; T-016 is IA + kernel, not capture.

## 5. Preliminary Risks Spotted

- Hybrid launch: naming a Run “for Cursor” with no start mechanism → dead UI (“watch” nothing).
- Treating `jobs.py` as the Run store without extending it past verbs → agent work invisible again (`jobs.py:5`).
- Verb `ticket-move` without the same lane validation as `tickets.move` → corrupt `ticket.toml`.
- Shell home that also changes `kanban.py serve` browser nav → contradicts assistant-as-home impact (“browser may keep existing nav”).
- Scope bleed into T-015 tray/overlay/latency paths.
- CLI backends still won’t hold new verbs unless MCP is loaded — documenting that is required or agents will look broken.

## 6. Open Confirmations

- How the console *starts* work inside Cursor IDE (no in-repo inbound API). → question, critical.
- Whether a Run is a new record type, a wrapper of chat ids, an extended job, or a tagged union. → question, high.
- Whether progress-append / close-work / log-work become verbs in T-016. → question, high.
- Whether `in-shell` home is a new first tab or chrome that hides the tab strip. → question, medium.

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-11 | `kanban.py context T-016 --json` | ticket digest | trace-context |
| 2026-09-11 | Read | `shell_feature.py`, `plugins.toml`, `assistant_feature.py`, `board.js`, `agents.js`, `agents.py`, `agent_manager.py`, `agent_tools.py`, `mcp.py`, `verbs.toml`, `verb_handlers.py`, `tickets.py`, `kanban.py`, `jobs.py`, `desktop-assistant.md`, `main.rs`, `console_api.rs`, `T-016-summary.md`, `T-016-decision-log.md` | survey |
| 2026-09-11 | Grep | `register_tab`, `/api/assistant/say`, `list_catalog`, `def move`, tracker parsers | confirm absences/presences |
| 2026-09-11 | `git log --oneline` | console/assistant/wiki paths | history |

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements-draft]] · [[T-016-context-snapshot]] · [[T-016-gap-analysis]] · [[T-016-iteration-log]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
