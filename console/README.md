# Delivery Console

A local web app + CLI for ticket/investigation boards plus a handful of
supporting tabs (Overview, Agents, Work, Analytics, Todos, Vault, About,
Settings), backed by TOML files under `knowledge-center/artifacts/` and the
existing `knowledge-center/logs/` daily log files. Stdlib-only Python (no
pip install, no build step for the frontend) — drop this folder into any
workspace that has a `knowledge-center/` sibling and it works.

Not implemented (by explicit choice, not oversight): **Migrations**/**Releases**
boards (present in config, disabled by default — see Config below) and
**Projects**/**Files** tabs (not built at all in this template).

## Onboarding

`python console/kanban.py onboard` (and the "Getting started" card on
Overview) answer the question a new workspace actually raises: *how do I get
from an empty vault to a ticket with agreed requirements?* Six steps —
identity, project name, boards, agent CLI, first ticket, then **product
requirements**, which is the point of the list rather than an afterthought.
The last step tracks each ticket as `missing → stub → drafted → frozen` and
names the pre-freeze skill chain, whose order is the part people forget.

Nothing in it writes. Every step reports state and offers the command or tab
that changes it — the remaining work is decisions (what is this called, which
boards, what are the requirements), and a wizard that guesses at those just
produces a workspace someone has to un-guess. Turn the whole thing off with
the `onboarding` row in `console/config/plugins.toml` once it stops earning
its place.

## Quick start

```bash
python console/kanban.py ticket create T001 --title "My first ticket"
python console/kanban.py serve
# open http://127.0.0.1:8790
```

## CLI

```text
ticket create ID --title T [--kind K] [--owner O] [--priority low|medium|high|critical] [--url URL]
ticket list [--kind K] [--stage S] [--owner O]
ticket show ID
ticket move ID STAGE
ticket set ID FIELD VALUE

tracker add ID {questions|bugs|todos} "text" [--set key=value ...]
tracker list ID {questions|bugs|todos} [--status S]
tracker update ID {questions|bugs|todos} ITEM_ID [--set key=value ...]
tracker blockers ID

onboard [--json]        first-run setup steps, ending at the requirements pipeline
serve [--host H] [--port N]
export --out DIR
refresh [--quiet]

overview
todos [--status S] [--owner O]
work day [--date D] [--author A]
work range [--start D] [--end D] [--author A]
analytics [--window N] [--author A]

vault tree [--path P]
vault file --path P
vault graph

agents backends
agents catalog
agents launch BACKEND "prompt" [--cwd DIR]
agents jobs
agents show JOB_ID
agents stop JOB_ID

telemetry [--by ticket|model|skill|persona|backend|day] [--ticket T]
          [--skill S] [--since D] [--until D] [--json]
telemetry skills [--json]

harness lint [--strict] [--json]

context TICKET [--json]

verb list [--ticket T] [--json]
verb run VERB [--ticket T] [--confirm] [--set KEY=VALUE ...]

schedule list [--json]
schedule due [--json]

audit [--limit N] [--action A] [--since D] [--json]
notify status
notify chat-id [--json]
notify test [--text "..."]

job submit VERB [--ticket T] [--confirm] [--set K=V] [--detach] [--timeout N]
job list [--state S] [--ticket T] [--json]
job show JOB_ID
job cancel JOB_ID

worktree list [--json]
worktree add NAME [--base REF] [--branch NAME]
worktree remove NAME [--force]
worktree prune
```

`context` is the one-call ticket digest: lane, blockers, unchecked plan tasks,
open trackers, artifacts, recent progress and spend, already reduced. On a
mid-sized ticket it is ~1.7 KB against ~27 KB of raw artifacts — a 16x
reduction, per turn. Every cap it applies is stated in the output, so silence
means the picture is complete. `trace-context` calls this instead of opening
eight files.

`verb` runs deterministic jobs declared in `config/verbs.toml` — no model
involved. Each verb declares its own gates (`needs_ticket`, `needs_confirm`,
board `kinds`/`lanes`), so the CLI, the queue and the MCP server all enforce the
same rules without reimplementing any of them. Handler paths resolve at registry
load, so a typo is a startup error rather than a surprise mid-run.

`job` is the durable queue those verbs run on: records on disk are the source of
truth, the concurrency cap comes from `[jobs] max_concurrent`, and a job
orphaned by a dead process is reported as `interrupted` — not `done` (a lie) and
not `error` (a guess).

`schedule` is cron-driven verbs, and **the running console is the clock** — there
is no daemon to install, and nothing fires while `serve` is not running. That
trade is stated rather than hidden: on startup the server prints either the
enabled schedules and their next run, or `scheduler: idle (N schedule(s), all
parked)`. Missed firings are **skipped, not replayed**; catching up after a
weekend would run every job dozens of times at once, and these submit real work.
A schedule whose verb needs confirmation must be granted it in the file, because
a scheduled job runs with nobody watching. `schedule due` is a dry run.

The cron subset is `*`, `N`, `A-B`, `*/S`, `A-B/S` and comma lists. Nicknames
(`@daily`), `L`, `W` and `#` are **rejected at load with the schedule id** rather
than silently treated as `*` — a schedule firing every minute because its
expression was not understood is the worst outcome available here. Day-of-month
and day-of-week together mean AND, not real cron's OR.

`worktree` gives a run its own checkout. It refuses to reuse a path, refuses to
remove uncommitted work without `--force`, and names what would be lost when it
refuses.

`telemetry` reports token and cost totals per turn. A cost the backend did not
report and that `config/pricing.toml` cannot price is shown as **unpriced** and
excluded from the total, marked with `*` — never as zero, because a total that
quietly treats unknown as free is wrong in the direction that matters.
`telemetry skills` partitions the skill roster into fired and never-fired; a
skill invoked by hand in a terminal leaves no record, so never-fired is a
candidate for review rather than a verdict.

### Where these appear in the UI

Everything above is also readable from the browser, placed **inside the tab
that already answers the same question** rather than on an operations tab of
its own. A tab you have to navigate to is a tab you check after it mattered.

| What | Where | Can act? |
| ---- | ----- | -------- |
| Verbs | Command palette, "Run" group | Runs it; result opens in the drawer |
| Jobs | Overview → **Jobs** | Cancels a *queued* job |
| Schedules | Overview → **Scheduled** | Read-only |
| Token and cost totals | Analytics → **Agent spend** | Read-only |
| Audit trail | Work → **Console activity** | Read-only, collapsed by default |
| Worktrees, notification health | Settings → **This machine** | Read-only |

Two rules run through that table.

**The panels remove themselves when they have nothing to say.** A workspace
that uses no schedules does not get a permanently empty box on its landing
page; the empty state is a panel that is not there. The exception is a panel
reporting a *problem* — a cron expression that failed to parse is shown, because
hiding it means discovering it on the morning the job did not run.

**Reads move to the UI; writes stay in the CLI.** Adding a worktree checks out
a branch, editing a schedule changes what fires while nobody is watching, and
this server has no authentication of its own — see below. Those belong in a
terminal that shows you the error. Cancelling a queued job is the one exception,
and it refuses a *running* job rather than pretending: stopping work mid-flight
needs the worker's cooperation, and reporting "cancelled" while it carries on
would be worse than saying no.

The spend panel never treats an unpriced turn as free. A model with no row in
`config/pricing.toml` contributes tokens but no cost, and every total drawn
from such a window carries a `*` and a count of the turns it excluded. A
dashboard that quietly under-reports spend is worse than one that reports
nothing, because it gets believed.

### Secrets: `.env` at the workspace root

Create `<workspace root>/.env` — beside `CLAUDE.md`, **not** inside `console/`:

```dotenv
OPENROUTER_API_KEY=sk-or-v1-...
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

It is gitignored (`.gitignore` line 38, `.env`), and every entry point loads it —
`kanban` for the CLI, `serve` for the web UI, `mcp_server.py` for MCP clients. So
a key in this file reaches the Agents tab, the CLI and Cursor without exporting
anything. There are no dependencies to install; the parser is forty lines of
stdlib in `server/dotenv.py`.

Three rules worth knowing:

- **An exported variable always wins.** A stale value in `.env` will never
  silently shadow one you set in your shell, because the resulting confusion is
  unbounded: the key you can see is not the key in use, and nothing says so.
- **Only names are ever printed.** On startup the console lists the variable
  names it found (`.env: OPENROUTER_API_KEY`) and never a value, so you can
  confirm the file was read without putting a credential in your scrollback, a
  screenshot, or a CI log.
- **Agents cannot read it.** `.env` and `.env.*` are in the workspace tools'
  refused-paths list and are skipped by the search tool — an agent
  authenticating with a key cannot read that key back.

To use OpenRouter after setting the key, flip `enabled = true` on the
`openrouter` row in `config/agents.toml`. The model picker ships empty on
purpose: availability and pricing move, and a stale hardcoded list is worse than
a paste box. `kanban agents backends` will show `installed: true` once the key
is found.

If a key does get committed, rotate it. Removing the commit does not un-publish
it.

### Telegram: making a parked approval reach you

Without this, a remote run stalls at its first gated write and denies 300
seconds later with nothing to tell you it happened. Four steps:

1. **Make the bot.** In Telegram, message [@BotFather](https://t.me/BotFather),
   send `/newbot`, and answer the two prompts. It replies with a token that
   looks like `1234567890:AA...`. That token *is* the bot — treat it like a
   password.
2. **Put it in `.env`** as `TELEGRAM_BOT_TOKEN=`.
3. **Find your chat id.** Telegram never tells you your own; you have to read it
   out of an update. Send your new bot any message (for a group, add the bot to
   it first and post there), then run:

   ```bash
   python console/kanban.py notify chat-id
   ```

   It prints one row per chat that has spoken to the bot — id, type, name — and
   nothing else. Copy the id into `.env` as `TELEGRAM_CHAT_ID=`. Group ids are
   negative; keep the minus sign, or you get an id that looks plausible and
   silently delivers nowhere.

   The documented alternative is pasting `getUpdates` into a browser with the
   token in the URL, which writes a live credential into your history, your
   address bar, and any screenshot of either. This command makes the same call
   from the process that already holds the token.
4. **Turn it on** — `enabled = true` under `[notify]` in `config/console.toml` —
   then prove it end to end:

   ```bash
   python console/kanban.py notify test
   ```

   That sends a real message and exits non-zero if it did not arrive. A
   notification path you have not tested is one you discover at the moment it
   is least useful to discover.

`notify status` answers "why didn't my phone buzz?" by reporting whether each
piece is *present* — never its value.

`events` is `["approval"]` by default, and widening it is a real trade: a phone
that buzzes for every turn gets muted, and then it buzzes for nothing. The other
kinds are `turn_end` and `job_error`.

Two properties hold regardless: a send that fails **never** blocks, delays, or
fails the run it describes — the approval still appears in the browser and still
times out exactly as before, you are simply not told. And a bot token is a
credential in a URL, so the failure path reports the status code and never the
URL it called.

### Reaching the console from elsewhere

The console has **no authentication of its own**, and that is a decision rather
than an omission. The supported way to reach it remotely is a private network —
Tailscale or equivalent — that authenticates before traffic ever arrives. Adding
a second, weaker authentication layer beside a working one would add risk
without adding safety.

That only holds while it is *known*, so set `[general] host` to the tailnet
address (or `0.0.0.0` if the machine is only on the tailnet) and the server
prints a warning at **every** start. A console listening beyond this machine
must never be a fact you forgot configuring. Never expose the port to the
internet.

`[notify]` pushes a parked approval to a phone. This is what makes remote
running work rather than a decoration on top of it: without it, a run started
from anywhere but this desk stalls at its first gated tool and dies on the
300-second timeout with nothing said about it. Telegram today; the seam is one
function in `server/notify.py`. Credentials come from the environment, are read
per send, and never reach an event, a transcript, an audit record or a log
line — the failure path reports a status code and not the URL it called,
because the URL contains the bot token.

Delivery is best-effort and off the request thread. If the provider is
unreachable the approval still appears in the browser and still denies on the
same timeout — you are simply not told, which is no worse than not having it
configured. Check with `notify status`, and prove it with `notify test`: a
notification path you have not tested is one you find out about at the moment
it matters.

`audit` records what *starts work or changes state* — a chat started, a verb run
or queued, an approval answered, with the client address. Not reads: a log that
records every board poll is one nobody scrolls through. Local and gitignored,
because those lines are a fact about your network rather than about the project.

### Reviewing before approving

A gated tool call parks on a "Permission needed" card. That card used to show the tool's
arguments as JSON — for a file write, a wall of escaped text with an escaped newline between
every line. Nobody reads that, so it got approved unread, which makes the gate a speed bump
with a log rather than a gate.

`server/tool_preview.py` now computes what the call would actually do and sends it with the
request: a unified diff with `+N/-M` for a write or an edit, the command and working
directory for a shell call. Computed server-side, so the CLI hook path and the in-process API
loop get it from one implementation and cannot drift.

It is honest about its limits. An edit whose target text is not in the file says the call
will fail — before you approve it. An ambiguous edit says how many occurrences exist and
which one wins. A shell command is shown, never predicted. And a preview that fails to build
never stops the question being asked: a gated tool must not run unreviewed because a diff
crashed.

### Command palette

`Ctrl`/`Cmd`-`K`. Every tab, ticket, verb and skill, filtered by subsequence — `hl` finds
"harness lint". Sourced from the tab manifest, the boards, the verb registry and the skill
catalogue, so anything that exists anywhere else appears here without this file changing. A
verb that needs a ticket is greyed with the reason rather than offered and then failed.

### The `openai_api` transport

Three of the four transports spawn somebody else's agent and inherit its tools,
its permission model, and its idea of what a skill is. `openai_api` has no
process: the console talks to an OpenAI-compatible endpoint and runs the loop
itself.

That is the point rather than the cost. Because the loop is ours:

- the agent holds **the console's own verbs as tools** (`console_context`,
  `console_blockers`, …) alongside file and shell tools, so reading a ticket is
  one call it *has* rather than a convention it has to remember;
- gated calls raise the **same "Permission needed" card** — in-process, with no
  hook subprocess and no HTTP round trip;
- tokens and cost are recorded through the same telemetry path as every other
  backend.

A model with no slash-command system cannot resolve `/plan`, so choosing a skill
here **injects its text** into the system prompt (`server/prompt_build.py`).
That is why the roadmap's token work had to come first: every skill is now paid
for, in tokens, on every turn that selects it. If a section does not fit the
budget, the prompt says so — a silently truncated skill is the worst failure
available, because the agent follows the half it received and the transcript
gives no sign.

To enable it: set `OPENROUTER_API_KEY` in the shell that starts the console and
flip `enabled = true` on the `openrouter` row in `config/agents.toml`. It ships
disabled because this template has no key and cannot verify one. `installed` for
an API backend means "the key is set", not "a binary is on PATH" — asking PATH
would report it missing and grey out something that would have worked.

The key is read per request, never stored on the session, and never written to
an event, a transcript, or a telemetry record.

Safety, honestly stated: file tools are confined to the workspace (resolved
paths, so a symlink cannot step out) and refuse credential-shaped files; writes
and shell are gated by a human. Read-only `console_*` verbs are deliberately
**not** gated — asking someone to approve "look up this ticket's lane" trains
them to click allow without reading, which is how a gate stops working for the
calls that matter. A tool-call round cap ends a runaway turn with a visible
notice rather than silently.

### MCP

`python console/mcp_server.py` serves the same verbs to any MCP client over
stdio — Claude Code, Cursor, and the OpenRouter backend Phase 2 adds all get an
identical tool set from one implementation instead of three integrations that
drift. `.mcp.json` at the repo root wires it up.

There is no tool table in the server: `tools/list` walks the verb registry and
derives each schema from its handler's signature, so a new row in `verbs.toml`
becomes a new tool with no code change. A failed gate comes back as a tool error
with the reason, not a JSON-RPC error code, so the model can correct itself.

`harness lint` type-checks `.claude/` config that nothing else validates:
frontmatter names against their directory/filename, `.claude/...` paths against
what exists, orphan skills, and the roster counts CLAUDE.md states. Exits
non-zero on errors; warnings need `--strict` to fail. Run in CI by
`.github/workflows/verify.yml` and, for harness-touching commits only, by
`.githooks/pre-commit`.

`questions`/`bugs`/`todos` skill docs (`.claude/skills/{questions,bugs,todos}/SKILL.md`)
describe their own verbs (`answer`, `fix`, `verify`, `close`, `doing`, `done`,
`drop`, `snooze`, ...) as `tracker update` calls with specific `--set` fields —
that keeps this CLI's surface small while each tracker keeps its existing
vocabulary.

## Config

- `config/console.toml` — `data_root`, `id_pattern` (ticket-id regex — no
  prefix is hardcoded in code), `host`, `port`, `enabled_boards`.
- `config/boards/{kind}.toml` — lanes and label for one board kind.
  `tickets`/`investigations` ship enabled; `migrations`/`releases` ship with
  `enabled = false` and placeholder lanes — flip the flag and edit lanes to
  turn either on, no code changes needed.

- `config/console.toml`'s `[agents.backends.*]` — one table per launchable
  CLI for the Agents tab (`command` + `args`, with `{prompt}` substituted).
  Ships with `claude` (`--permission-mode plan` by default — safe/read-only
  until you change it) and `cursor-agent`. Add more the same way; nothing is
  hardcoded to a specific CLI.
- `config/plugins.toml` — which **features** load. This, not `console.toml`,
  is what decides the non-board tabs. See Plugin architecture below.

### Two different off switches — don't conflate them

| Question | `config/plugins.toml` | Settings tab |
| --- | --- | --- |
| Scope | The deployment — everyone who pulls the checkout | One person's browser |
| Stored in | A committed file | `localStorage` |
| Effect | Module never imported, routes don't exist, tab absent from `/api/config` | Tab hidden from the nav |
| Use it to say | "This deployment does not do that" | "I don't use that tab" |

Hiding the Agents tab in Settings does **not** disable the launch endpoint.
Setting its `plugins.toml` row to `enabled = false` does. The Settings tab
shows the server's actual loaded routes next to its own switches so the
difference is visible rather than assumed.

## Data model

- `{TICKET}/ticket.toml` — id, title, kind, stage, status, owner, priority,
  dates, tags, links, optional `scripts_dir`, optional `url`.

  `priority` is one of `low|medium|high|critical` — anything else normalises
  to `medium` rather than producing a card that can't render. `url` links the
  ticket to whatever external tracker the team uses (Jira, Linear, GitHub, an
  internal tool); empty means "not tracked elsewhere" and the card simply
  omits the link. Nothing here is specific to any one tracker.
- `{TICKET}/{TICKET}-{questions,bugs,todos}.toml` — `[meta]` + `[[items]]`.

All of the above are **CLI-mutated only** (this CLI or the HTTP API, which
share the same `server/` code) — never hand-edited. See
`.claude/skills/consolidate/SKILL.md` for how these fit the rest of the
ticket-artifact convention.

The **Work** tab does not introduce a second storage format — it reads the
per-author daily log files `/log-work` already writes
(`knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{slug}.md`), and implements
as real code the hour-allocation algorithm `log-work/SKILL.md` (mode summary) already
specifies in prose (explicit `~{h}` hints stand; everything else splits the
remaining hours toward an 8h/day floor, rounded to 0.25h). Adding a work
entry still goes through `/log-work`, not this console — that skill's
author-resolution and idempotency logic isn't duplicated here.

The **Vault** tab's graph is wikilink + folder-containment edges only — no
typed knowledge-graph schema. Its canvas is an overview drawn from a one-shot
force layout (a ring layout past 400 nodes, which the UI says out loud); the
focusable node list beside it, sorted most-linked-first, is the part that
actually reaches files and the part that works by keyboard. The **Agents**
tab launches a real subprocess for whichever backend you pick; see its own
section below.

## Why no external TOML library

Reads and writes go through `server/tomlio.py`, a small hand-rolled
reader/writer scoped to exactly the shapes above (flat tables, one level of
array-of-tables, scalar values). That keeps the console at zero pip
dependencies and with no Python-version floor — the whole point of this
being a drop-in-anywhere template. It is **not** a general TOML parser; don't
point it at hand-authored TOML using features outside that subset. Arrays are
split on top-level commas only, so a quoted element may contain a comma
(`args = ["-c", "import time,sys"]`) and round-trips through `dumps`/`loads`
intact.

## Architecture

```text
kanban.py         CLI entrypoint (argparse -> server/*)
server/
  tomlio.py       TOML read/write + atomic write/lock
  paths.py        workspace-root resolution
  boards.py       board-kind config loading
  tickets.py      ticket.toml CRUD
  trackers.py     questions/bugs/todos CRUD
  render.py       board/ticket view-models (shared by httpd.py and export.py)
  overview.py     Overview tab aggregation
  worklog.py      Work tab: parses log-work's existing markdown files
  analytics.py    Analytics tab: pure functions over board + worklog data
  todos_agg.py    Todos tab: cross-vault todos aggregation
  vault.py        Vault tab: file tree, read-only file viewer, wikilink graph
  agents.py       Agents tab: subprocess launcher + job tracking
  plugins/
    base.py       Plugin / Route / Router / PluginContext contracts
    registry.py   reads config/plugins.toml, topo-sorts by each plugin's
                  own `requires`, raises on cycles and missing deps
  features/
    *_feature.py  one module per feature: PLUGIN = Plugin(..., apply=...)
  httpd.py        transport ONLY (sockets, headers, CSRF, static files).
                  Knows no feature; asks the router.
  export.py       static snapshot, read-only (needs_live tabs excluded —
                  see "Static export" below)
static/           vanilla HTML/JS/CSS frontend, no build step, one file per
                  tab (core.js has the shared tab-registry/fetch helpers)
```

## Plugin architecture

A feature is one server module plus one client file, and adding one edits no
existing code. That is the property to preserve when extending this.

**Server side.** `server/features/<name>_feature.py` exposes
`PLUGIN = Plugin(id=..., apply=..., requires=(), summary=...)`. `apply(ctx)`
runs once at boot and uses only `PluginContext`:

```python
def apply(ctx):
    ctx.register_tab("widgets", label="Widgets", short="Wid",
                     icon="list", group="main", needs_live=False)
    ctx.get(r"^/api/widgets/?$", lambda req: {"items": []}, "widgets.list")

PLUGIN = Plugin(id="widgets", apply=apply, summary="Example feature.")
```

Then add a row to `config/plugins.toml`:

```toml
[[plugin]]
id = "widgets"
module = "features.widgets_feature"
enabled = true
```

That is the whole registration. `httpd.py` is never edited — it resolves
requests through the router, which only holds what the loaded plugins put
there. Load order comes from each plugin's own `requires`, not from row order
in the config, because a module's dependencies are a property of the code and
not of a deployment's on/off choices. Cross-plugin access goes through
`ctx.provide(name, obj)` / `ctx.provider(name)` so a consumer depends on a
name rather than an import — that is why disabling `work` makes Analytics
return `worklog: null` and render a "plugin disabled" panel instead of
crashing or drawing an empty chart.

**Client side.** `static/<name>.js` calls
`Console.tab("widgets", { render(host, api), onSearch?(q), onLeave?() })` and
gets a `<script>` tag in `index.html`. The router (`app.js`) intersects the
server manifest with whatever registered client-side, so a tab appears only
when *both* halves exist — which is what makes `enabled = false` a complete
off switch rather than a dead nav entry that 404s. Board tabs all share one
implementation registered as `"board"`, parameterised by `api.tab.kind`, so
any number of boards needs no extra JS.

Set `needs_live = True` on a tab whose data a frozen snapshot would
misrepresent; the exporter drops it and the frontend hides it.

`GET /api/routes` reports what actually loaded — the first thing to check
when a tab 404s. The Settings tab renders it.

## Static export

`kanban.py export --out DIR` writes a self-contained folder that opens
directly from a `file://` URL — no server, no network, no external assets.

It contains Boards (with each card's drawer data), Overview, Todos, About and
Settings. **Tabs flagged `needs_live` are excluded**: Agents (launches real
subprocesses), Work and Analytics (date/window pickers), and Vault (per-path
tree and file reads). The frontend hides them automatically, and About says
why rather than implying the feature is disabled.

The page reads its data from `data.js` (`window.__CONSOLE_DATA__`), loaded by
a plain `<script>` tag — **not** by fetching `data/*.json`. That is a hard
requirement, not a style choice: a page opened from `file://` has a null
origin and Chromium blocks `fetch()` against it outright, so a
fetch-backed snapshot cannot boot at all without a web server. The
`data/*.json` files are still written alongside it for anything that wants to
consume the export as data.

Writes are refused in a snapshot with a clear message rather than failing
silently, and the connection pill reads `snapshot`.

## Agents tab — what it does and doesn't do

Launches a configured backend (`console/config/console.toml`'s
`[agents.backends.*]`) as a **headless one-shot subprocess** — `subprocess.Popen`
with an argv list (never a shell string, so prompt content can't inject
shell syntax), output captured in the background and polled by the UI.

Deliberately smaller than a full agent-orchestration UI:
- **No live steering.** You can watch a run and stop it, not talk to it mid-turn.
- **No worktree isolation.** Every run executes directly in the workspace
  root (or a `cwd` you pass, still inside the workspace). Don't launch two
  runs against the same ticket/repo concurrently.
- **Approval gate on live chats only.** In a live chat, tools listed under
  `gated_tools` in `console/config/agents.toml` are held by a PreToolUse hook:
  a "Permission needed" card appears in the transcript (Allow once / Allow for
  this chat / Deny) and silence denies fail-closed after `approval_timeout`
  seconds. In acceptEdits mode the file-edit tools are auto-allowed so the
  mode means what it says. One-shot CLI runs (`agents launch`) have no gate —
  their default `claude` backend uses `--permission-mode plan` specifically so
  a launch can't take actions by default.

Job records live in process memory plus a best-effort JSON snapshot under
`console/.cache/agent-runs/` (gitignored) written when a job finishes — a
server restart mid-run loses live tracking of that job (the OS process
itself is unaffected).

## Security notes

- Binds `127.0.0.1` only — not reachable from the network.
- Every POST requires an `X-Console-Request: 1` header, which a same-origin
  browser won't let a cross-site page attach without CORS — a lightweight
  CSRF mitigation given there's no other auth.
- No secrets or credentials ever belong in a tracker item's text.
- The Vault tab's file viewer is read-only and path-checked against escaping
  `knowledge-center/` — it cannot read or write anything outside the vault.
- The Agents tab can launch real processes on your machine. Treat backend
  config changes with the same care as any other command you'd run locally.
