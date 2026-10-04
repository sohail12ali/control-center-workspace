---
ticket: "T-018"
artifact: context-snapshot
status: draft
created: "2026-09-16"
last_updated: "2026-09-16"
scope: codebase + history
---

# Context Snapshot: T-018

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-018 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Ticket-git-Run: default worktree isolation per Run, ticket id encoded in branch/PR, lane hints surfaced from PR open/merge (human still closes), and a Run inspector diffstat — building on T-017's Run object and Backend SPI, not re-deriving them.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Git worktree add/remove/prune/list | `console/server/worktrees.py` | git porcelain shell-out, CLI wiring | Reuse `add`/`path_for`/`branch_for`/`_find` directly for per-Run isolation; `branch_for` already implements "ticket id in branch name" via `agent/{ticket}` pattern | worktrees.py:37-38, 92-93, 148-176 |
| Worktree CLI commands | `console/kanban.py` `worktree add/remove/prune/list` | CLI only — no MCP verb, no UI | No MCP/UI surface exists yet for worktrees | kanban.py:301-318, 973-992 (no `worktree` entry in `console/config/verbs.toml`) |
| Run object (tagged union chat/job/cursor) | `console/server/runs.py` | durable per-run JSON record | `create()`/`get()`/`set_state()` already the shape to extend with git fields, or leave untouched and put fields on the ticket instead (see decision-log a1) | runs.py:45-104 |
| `launch_role` — starts a harness persona as a chat + Run | `console/server/verb_handlers.py:301-334` | verb handler → `agent_manager.create` → `runs_mod.create` | Calls `agent_manager.create(repo_root, ...)` with **no `cwd` override** — the chat's cwd is `repo_root` itself, i.e. the shared tree, confirmed at the call site | verb_handlers.py:324-327 |
| Chat cwd = shared tree | `console/server/agent_manager.py` | session/backend layer | `create(repo_root, backend_id, prompt, ...)` passes `repo_root` straight through as `agent_session.build`'s `cwd` positional arg; `send()`'s own docstring states outright **"`sess.cwd` IS the workspace root (chats run there — see `create`)"** | agent_manager.py:64, 83, 113-114 (build call), 328 (docstring statement) |
| `claimed_by`/`claimed_at` schema extension pattern | `console/server/tickets.py` | ticket.toml schema | Direct precedent for adding new ticket-scoped fields (`branch`, `pr_url`, `pr_state`) the same way: `create()` seeds the field, `load()` defaults it for old tickets, a dedicated setter mutates it under a lock | tickets.py:38-79 (create), 82-95 (load), 207-240 (`set_claim`, race-safe pattern) |
| Run inspector (Agents tab) | `console/static/agents.js` | UI — run row + click-through | `runRow()`/`openRun()` today show `executor/backend/executor_id` and click through to the chat; they do **not** show worktree path, diffstat, "open in IDE", or cost/tokens — this is the extension point, not a new tab, matching T-016's "the Agents tab becomes that inspector" scope note | agents.js:226-258; T-016-summary.md:26 |
| Telemetry (cost/tokens) | `console/server/telemetry.py` | per-turn JSONL, aggregation | `record()`/aggregation already carry `input_tokens`/`output_tokens`/`cost_usd` keyed by session/ticket — reusable for the Run inspector's cost/tokens panel without new plumbing | telemetry.py:57, 121-150, 229-257 |
| Lane ids | `console/config/boards/tickets.toml` | board config | Lanes are `open`, `in-progress`, `blocked`, `verify`, `done` (`done` is `terminal=true`) — "lane hints" target `verify` (PR opened) and `done` (PR merged) | boards/tickets.toml:9-27 |
| GitHub hosting confirmed | `.github/workflows/`, `git remote -v` | CI / repo host | This workspace's own repo is hosted on GitHub (`origin` = `github.com/sohail12ali/control-center-workspace`) and already runs GitHub Actions — the `gh` CLI is the natural, dependency-free way to read PR state, consistent with `worktrees.py`'s stated philosophy of shelling out to porcelain commands rather than writing a wrapper library | `.github/workflows` (dir listing), `git remote -v` output, worktrees.py:23-27 |
| No PR/GitHub API integration exists today | workspace-wide grep | — | No `gh pr`, `GITHUB_TOKEN`, GitHub REST/GraphQL client, or webhook receiver exists anywhere in `console/` | grep for `github|pr_url|pull.request` across console/ — only unrelated hits (`.github` dir-visibility constant in tickets.py:110, README mentions) |

### Existing patterns to reuse
- Shell out to an already-installed CLI rather than build an API client — `worktrees.py`'s `_git()` helper (worktrees.py:57-65) is the precedent for a `_gh()` equivalent.
- Schema extension via `setdefault` for backward compatibility — tickets.py:91-93.
- Race-safe field mutation via `tomlio.atomic_update` — introduced in T-017 for `claim` (decision-log T-017 a3, code path `tickets.set_claim`).
- Change-notification publish on mutation — `verb_handlers.ticket_move` publishes to the MCP bus after every ticket mutation (verb_handlers.py:359-361); any new `pr-set`/`worktree` verb should do the same for consistency.

### Naming and architectural conventions in play
- One mutation API — CLI, MCP, HTTP are adapters over the same verb handlers (`console/server/verb_handlers.py`), per CLAUDE.md "Console sync" and T-017's FR-1.
- Ticket-scoped fields live on `ticket.toml`, mutated only via `console/kanban.py` / the verb layer — never hand-edited (CLAUDE.md "Layout" section; tickets.py's own field-setter pattern).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| [[T-017-summary]] | One-API, MCP resources/HTTP, tracker SPI, workspace.toml, `ready`/`claim`/`comment` verbs, `claimed_by`/`claimed_at` on ticket.toml | Closed 2026-09-16, 11/11 AC pass | T-018 depends on this ticket's Run/ready-claim work and Backend SPI; do not re-derive — reuse `Backend` ABC, `VaultBackend`, the verb registry, and the `claimed_by`/`claimed_at` schema-extension pattern (decision-log a3) directly |
| [[T-016-summary]] | Run object (`runs.py`), `launch_role`, Agents tab as inspector, Assistant-as-home | In Verify, 10/10 tasks done, not yet closed | Read-only reference per task instructions — do not modify T-016 artifacts/code. Its Run object and Agents-tab inspector are the extension points for T-018, not a parallel structure |

### Relevant commits / PRs
- `4931696` "Ship T-017: Delivery Console core…" — most recent commit, matches T-017's closed state.

### Known incidents / regressions in this area
- None specific to worktrees/git/PR flow — this is greenfield functionality; the worktree *commands* exist and are tested (T-016/T-017 scope did not touch them beyond wiring), but nothing consumes them for Run isolation yet.

## 4. External Systems in the Loop

- **GitHub** — PR open/merge state, read via the `gh` CLI (already implied available given this repo's own GitHub Actions/remote). No token/API-client work is proposed; `gh` handles its own auth via the developer's existing login, matching `worktrees.py`'s "not a git wrapper, shells to porcelain" philosophy.
- **The local git worktree machinery** — `console/server/worktrees.py`, already built, requires the repo to be a real git repository (`_require_git_repo`).

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- Worktrees are keyed by a single `name` (`path_for`/`branch_for` take one `name` string, worktrees.py:78-93) — today's callers pass a ticket id. Multiple Runs against the same ticket (e.g. analyst then builder, each via `launch_role`) would collide on `worktrees.add()`'s "never create over an existing path" rule (worktrees.py:152-155) unless Run creation reuses an existing managed worktree for that ticket rather than always creating one.
- `agent_manager.create` has no `ticket`-less-chat exception path today for cwd — a majority of live Assistant chats have `ticket=""` (agent_manager.py:66 default) and cannot be keyed to a per-ticket worktree; defaulting *unconditionally* to worktree isolation would break every ticketless chat.
- `gh` CLI availability is assumed, not verified in this codebase — no existing code path checks for or shells to `gh` anywhere today.
- No existing UI surface renders `git diff --stat` output or a worktree path — `agents.js`'s run row is metadata-only (agents.js:226-244).

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. Convert to open questions via `clarify` if any would change the draft.

- `gh` CLI is installed and authenticated on any machine that runs the console and wants PR-state lane hints — inferred from this repo's own GitHub hosting and Actions usage, not confirmed by reading a CI config or asking the user directly.

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-16 | Bash | `console/kanban.py context T-018` | trace-context baseline |
| 2026-09-16 | Read | `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` | source-of-truth scope doc for T-018 |
| 2026-09-16 | Read | `console/server/agent_manager.py` | verify "sess.cwd IS the workspace root" claim |
| 2026-09-16 | Read | `console/server/runs.py` | current Run object shape |
| 2026-09-16 | Read | `console/server/worktrees.py` | existing worktree command surface |
| 2026-09-16 | Grep | `launch_role` across `console/` | locate real definition (verb_handlers.py, not agents.py) |
| 2026-09-16 | Read | `console/server/verb_handlers.py:270-370` | confirm `launch_role` passes no cwd override |
| 2026-09-16 | Read | `console/server/agent_session.py` (grep) | confirm `build(sid, backend, cwd, ...)` signature |
| 2026-09-16 | Grep | `worktree` in `kanban.py`, `verbs.toml` | confirm CLI-only, no MCP verb |
| 2026-09-16 | Read | `console/server/tickets.py:38-137` | ticket.toml schema + `claimed_by`/`claimed_at` precedent |
| 2026-09-16 | Read | `knowledge-center/artifacts/T-017/T-017-summary.md`, `T-017-decision-log.md` | shipped T-017 shape, decisions a1-a9 |
| 2026-09-16 | Read | `knowledge-center/artifacts/T-016/T-016-summary.md` | Run/inspector scope, read-only |
| 2026-09-16 | Grep | `run_show/inspector/backend` in `agents.js` | confirm Run inspector's current UI shape |
| 2026-09-16 | Read | `console/static/agents.js:200-270` | run row/openRun implementation |
| 2026-09-16 | Grep | `pr_url/pull.request/github` across `console/` | confirm no existing GitHub/PR integration |
| 2026-09-16 | Grep | `cost_usd/num_turns/tokens` in `telemetry.py` | confirm telemetry fields for inspector's cost/tokens panel |
| 2026-09-16 | Bash | `cat console/config/boards/tickets.toml` | lane ids for lane-hint targets |
| 2026-09-16 | Bash | `git remote -v`, `ls .github` | confirm GitHub hosting for the `gh` CLI decision |

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements-draft]] · [[T-018-context-snapshot]] · [[T-018-gap-analysis]] · [[T-018-iteration-log]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
