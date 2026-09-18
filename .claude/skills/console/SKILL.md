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
/console context {T}                       # ONE-CALL ticket digest (~16x cheaper than reading artifacts)
/console verb list|run {id} [--ticket {T}] [--confirm]   # deterministic jobs, no model
/console job submit|list|show|cancel       # durable queue for verb runs
/console schedule list|due                 # cron verbs; the running console is the clock
/console audit [--action A]                # who started work or changed state, and from where
/console notify status|test                # can a parked approval reach your phone
/console worktree list|add|remove|prune    # isolated checkout per run
/console telemetry [--by ticket|model|skill|backend|day] [--ticket {T}]   # token + cost totals
/console telemetry skills                  # per-skill invocation counts; what never fired
/console harness lint [--strict]           # frontmatter, dead .claude paths, orphan skills
```

Also: `overview`, `todos`, `work day|range`, `analytics`, `vault tree|file|graph`, `agents backends|catalog|jobs|show|stop`, `onboard`. Full CLI + architecture: [console/README.md](../../../console/README.md).

**When:** A visual board beats grepping `artifact-map.md`, or a skill needs to mutate ticket/tracker state.

## Stage → lane sync

Pipeline events map to board lanes via `ticket move`: `kickoff` → `open` (create default) · first build task → `in-progress` · blocker logged → `blocked` · verification running → `verify` · `close-work` → `done`. `close-work` owns the final move; agents move lanes when their stage starts.

## What backs this

- `console/kanban.py` — CLI entrypoint. `serve`/`export` render through shared `console/server/render.py`, so live UI and static export never drift.
- `console/config/console.toml` — `id_pattern`, `host`, `port`, `enabled_boards`, optional `[telemetry] dir`. Backends are **not** here: `agents.toml` is the single registry for both the tab and the `agents launch` CLI path.
- **Secrets** live in `<workspace root>/.env` (gitignored, loaded by every entry point via `console/server/dotenv.py`). `OPENROUTER_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`. An exported shell variable always wins; only variable NAMES are ever printed; agents cannot read the file.
- `console/config/pricing.toml` — per-model rates for backends that report tokens but no cost. A model with no row is reported **unpriced**, never as zero.
- **Backends** come in four transports: `stream_json` / `resume` / `oneshot` drive a CLI; **`openai_api`** has no process — the console runs the loop, so the agent holds the console's verbs as tools, gates in-process, and has its skill **injected** into the system prompt (no slash commands exist for it). `installed` for an API backend means the key env var is set. OpenRouter row ships `enabled = false`.
- `console/config/schedules.toml` — cron rows fired by `serve` itself (no daemon). Nothing fires while the console is down and missed firings are **skipped, not replayed**. Unsupported cron syntax is rejected at load, never treated as `*`.
- `console/config/verbs.toml` — deterministic no-model jobs. Handlers resolve at registry load (a typo fails at startup); each row declares its own gates, so CLI, queue and MCP enforce them identically.
- `console/mcp_server.py` + root `.mcp.json` — the verbs as MCP tools for Claude Code, Cursor, and any other MCP client. Tools are generated from the registry, so adding a verb adds a tool with no code change.
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
- Server binds `127.0.0.1` by default and has **no auth of its own**. Remote access is via a private network (Tailscale) that authenticates first — any non-loopback `host` prints a warning at every start. Never expose the port to the internet. Writes still require the `X-Console-Request` header (CSRF defence, not authentication) — don't weaken it.
- `[notify]` (Telegram) is what stops a remote run stalling silently at its first gated tool. Best-effort and fail-soft; a failed send never blocks the run. `[audit]` records only state-changing actions, local and gitignored.
- Concurrent runs against one repo need isolation: `worktree add {T}` first. Live chats and `agents launch` still run in the shared tree, so two of those on one ticket will interleave their edits.
- `about` tab content stays derived from live board config, never hardcoded.
- New features via plugin + `Console.tab(...)` — never by editing `httpd.py`/`app.js`. Don't conflate `plugins.toml` (removes routes) with Settings tab-hiding (cosmetic).
- Charts use `--cat-*` tokens, never `--accent`/`--info`/`--run`; every chart keeps a table twin.

**Delegates to:** none (owns storage/CLI). **Called by:** `kickoff`, `questions`, `bugs`, `todos`, `close-work`, `deployer`, session hooks.

**Version:** 2.0 — verbs, one-call context, jobs, worktrees, schedules, MCP, `openai_api` transport, telemetry | **Updated:** 2026-08-29
