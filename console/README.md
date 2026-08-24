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
```

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
