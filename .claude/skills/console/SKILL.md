---
name: console
description: The Delivery Console — a local Tickets/Investigations board plus Overview/Agents/Work/Analytics/Todos/Vault/About/Settings tabs (Migrations/Releases boards and Projects/Files tabs intentionally not built), served from console/ and backed by TOML files under knowledge-center/artifacts/ and the existing knowledge-center/logs/ daily logs. Use to view board state, serve/export the UI, launch an agent run, or as the CLI other skills (questions/bugs/todos, kickoff) shell out to for ticket and tracker mutations.
---

# /console

**Usage:**
```
/console serve [--host H] [--port N]     # local web UI (default 127.0.0.1:8790)
/console export --out DIR                # static snapshot for file:// (needs_live tabs excluded)
/console ticket create {T} --title "..." [--kind tickets|investigations] [--owner O]
/console ticket list [--kind K] [--stage S] [--owner O]
/console ticket show {T}
/console ticket move {T} {stage}         # lanes: open | in-progress | blocked | verify | done
/console ticket set {T} {field} {value}
/console refresh                          # cheap re-index (session hooks)
/console agents launch {backend} "prompt" [--cwd DIR]   # headless one-shot run
```
Also: `overview`, `todos`, `work day|range`, `analytics`, `vault tree|file|graph`, `agents backends|catalog|jobs|show|stop`, `onboard`. Full CLI + architecture: [console/README.md](../../../console/README.md).

**When:** A visual board beats grepping `artifact-map.md`, or a skill needs to mutate ticket/tracker state.

## Stage → lane sync

Pipeline events map to board lanes via `ticket move`: `kickoff` → `open` (create default) · first build task → `in-progress` · blocker logged → `blocked` · verification running → `verify` · `close-work` → `done`. `close-work` owns the final move; agents move lanes when their stage starts.

## What backs this

- `console/kanban.py` — CLI entrypoint. `serve`/`export` render through shared `console/server/render.py`, so live UI and static export never drift.
- `console/config/console.toml` — `id_pattern`, `host`, `port`, `enabled_boards`, legacy `[agents.backends.*]` for the CLI launch path.
- `console/config/agents.toml` — the web Agents tab's backend registry (transport, session args, modes, models + labels/hints, `gated_tools` + `approval_timeout` for the PreToolUse approval gate). Live chats park gated tool calls on a "Permission needed" card (Allow once / Allow for this chat / Deny; silence denies fail-closed); voice can read replies aloud and announce turn-end/permission-needed.
- `console/config/boards/{kind}.toml` — one file per board kind; `migrations`/`releases` ship `enabled = false` (a fork flips the flag, no code change).
- `console/config/plugins.toml` — which feature modules load; `enabled = false` removes routes + tab entirely (server-side, committed — distinct from Settings' per-browser tab hiding). New feature = `console/server/features/*_feature.py` + `console/static/*.js` + a row here; `httpd.py` is never edited.
- Data lives in ticket folders: `{T}/ticket.toml` + `{T}/{T}-{questions,bugs,todos}.toml` — **CLI-mutated only**, the one exception to "artifacts are hand-edited markdown" (see `consolidate/SKILL.md`).
- **Work** tab reads `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{slug}.md` (written by `log-work` — no second storage format).
- **Agents** tab launches configured backends as subprocesses (argv list, never a shell string). Limitations list: `console/server/agents.py` docstring = the UI table, kept in step deliberately.

## Who calls this

`kickoff` (ticket create), `questions`/`bugs`/`todos` (tracker verbs), `close-work` (ticket move → done), `deployer` (ticket show), session hooks (`.claude/hooks/console-refresh.sh` → `refresh --quiet`, best-effort, never blocks a session).

## Rules

- Never hand-edit `ticket.toml` or any `{T}-{questions,bugs,todos}.toml` — always via this CLI.
- `{T}-gaps.toml`/`{T}-critique.toml` are reserved, not wired — the `challenge-*` critique passes stay markdown.
- Don't enable `migrations`/`releases` speculatively.
- Server binds `127.0.0.1` only; writes require the `X-Console-Request` header — don't weaken either.
- Never launch a second Agents run against a ticket/repo with one running (no worktree isolation yet).
- `about` tab content stays derived from live board config, never hardcoded.
- New features via plugin + `Console.tab(...)` — never by editing `httpd.py`/`app.js`. Don't conflate `plugins.toml` (removes routes) with Settings tab-hiding (cosmetic).
- Charts use `--cat-*` tokens, never `--accent`/`--info`/`--run`; every chart keeps a table twin.

**Delegates to:** none (owns storage/CLI). **Called by:** `kickoff`, `questions`, `bugs`, `todos`, `close-work`, `deployer`, session hooks.

**Version:** 1.3 — lean rewrite; stage→lane sync map | **Updated:** 2026-08-23
