---
ticket: "T-017"
artifact: analysis
---

# Analysis: T-017

## Context

T-017 is the first of two tickets split from `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` ("Improve the Delivery Console"). Scope: one CLI/MCP/HTTP API surface, MCP resources + streamable HTTP, a Tracker plugin SPI (vault-only adapter), `workspace.toml` (drop the sibling-folder requirement), and `ready`/`claim`/`comment` verbs + stop-hook + `console setup <editor>`. T-018 (worktree-per-Run, branch/PR linkage) depends on this ticket and is explicitly out of scope here. T-015 (voice) and T-016 (Run object, Verify stage) are read-only context, not touched.

## Current State

**one-api** (plan lines 5-6, 65, 159-166)
- `console/kanban.py:41-46` `cmd_ticket_create` calls `tickets.create()` directly — bare `ticket.toml` + tracker TOMLs only, no template render, no artifact-map row.
- `console/server/kickoff.py:1-16` + `console/server/verb_handlers.py:125-130` — the `kickoff` verb's `create_ticket` does the full flow: id gen (`kickoff.py:49-61`), template render via `New-FromTemplate.ps1` (PowerShell-only, `kickoff.py:64-80`), artifact-map row.
- **Confirmed dual path**, exactly as the plan states. **New finding not in the plan:** the "fuller" path (`kickoff.py`) shells to PowerShell (`kickoff.py:64-65`, `_powershell_exe`) and fails honestly with `PowerShellUnavailable` when it's missing (`kickoff.py:42-46`). Collapsing `cmd_ticket_create` into this path — the natural direction, since it's the one with real behavior — means **every** ticket-creation entry point (CLI, MCP, HTTP) becomes PowerShell-dependent, not just the `kickoff` verb. That's an existing constraint inherited, not created, by this ticket; flagged as a risk (see requirements NFR/edge cases).
- JSON claim: `kanban.py` commands here already print `json.dumps(...)` unconditionally (e.g. `cmd_ticket_create`, `cmd_ticket_list`, `cmd_tracker_add`, `cmd_context` with `--json` flag). A handful use a `--json` flag with a formatted-text default (`cmd_verb_list:146-148`, `cmd_audit:157-160`, `cmd_context:300-303`, `cmd_telemetry`, `cmd_schedule_list`, `cmd_job_list`, `cmd_worktree_list`, `cmd_harness_lint`, `cmd_agents_models`, `cmd_agents_provider`, `cmd_agents_doctor`). Confirms the plan's "JSON already exists on most commands, closing the remaining gaps" framing (plan line 65) rather than "add JSON from scratch."

**mcp-first-class** (plan lines 8-9, 57)
- `console/server/mcp.py:1-234` is stdio-only (`serve_forever` reads `self.stdin`, line 222-234) and implements exactly `initialize`, `notifications/initialized`, `ping`, `tools/list`, `tools/call`, `shutdown`/`exit` (`handle`, lines 172-220). Declared capabilities: `{"tools": {"listChanged": False}}` only (line 168) — no `resources`, no change notifications. **Plan claim confirmed exactly**, including the specific method list.
- `console/kanban.py:557-560` `cmd_serve` starts `server.httpd.serve(...)` — an existing HTTP server process that would need to host the new streamable-HTTP MCP transport per the plan (line 162).

**tracker-spi** (plan lines 11-13, 61, 172-177)
- **Important discrepancy from the plan's wording.** `console/config/plugins.toml` and `console/server/plugins/registry.py` are a real plugin *loader* — but they gate **UI/HTTP feature modules** (`boards`, `overview`, `agents`, `vault`, `assistant`, `shell`, etc., each with an `apply(ctx)` and a `requires` list; `registry.py:1-107`), not a tracker abstraction. There is no existing "Tracker" interface or SPI-shaped seam anywhere in the codebase today — `tracker-spi` is wholly new design work, not an extension of `plugins.toml`. The plan's phrase "Plugins cannot extend the console" (line 59) is about this same UI-plugin system, so the plan is *not* wrong, but a reader could mistakenly assume the tracker SPI slots into `plugins.toml`'s existing shape — it doesn't; it needs its own interface module (e.g. `console/server/trackers/base.py` mirroring the shape of `console/server/plugins/base.py`).
- `console/server/vault.py:12` `VAULT_SUBDIR = "knowledge-center"` — confirmed hardcoded constant, no adapter indirection.
- `console/server/trackers.py:19` `VALID_KINDS = ("questions", "bugs", "todos")` — the *tracker* here is the questions/bugs/todos sub-trackers per ticket, a different (and unrelated) use of the word "tracker" from the plan's "Tracker SPI" (which means the ticket-management backend — vault vs. Jira/Azure/etc.). This naming collision is worth a one-line disambiguation in requirements so `tracker-spi` (ticket backend abstraction) isn't confused with `console/server/trackers.py` (questions/bugs/todos CRUD, unaffected by this ticket).

**workspace-contract** (plan lines 14-16, 57, 180-192)
- `console/server/paths.py:15-18` `_is_repo_root` requires **both** `knowledge-center/` and `console/` as immediate children; `find_repo_root:21-43` walks upward from cwd (or the console package's own location) and raises `RepoRootError` if neither is found. **Plan claim confirmed exactly** (docstring at `paths.py:1-6` states the same constraint in its own words).
- No `workspace.toml` file or loader exists anywhere in `console/` today (`Glob` for `workspace.toml` and grep for `"workspace.toml"` in `console/` returned nothing beyond the plan doc itself) — this is new, not a rename of an existing mechanism.

**ready-claim-hooks** (plan lines 17-19, 63-65, 159-169)
- Confirmed absent: no `ready`, `claim`, or `comment` verb in `console/config/verbs.toml` (verbs present: `context`, `blockers`, `plan-status`, `artifacts`, `todos`, `harness-lint`, `telemetry`, `skill-usage`, `agent-models`, `launch-role`, `run-list`, `run-show`, `ticket-move`, `ticket-set`, `tracker-add`, `tracker-update`, `delegate`, `kickoff`, `tickets-digest`, `remember`, plus 7 `desktop-*` verbs) and no matching handler in `console/server/verb_handlers.py`.
- **New finding not covered by the plan:** there is nowhere to put a "comment" today. `console/server/trackers.py:19` `VALID_KINDS = ("questions", "bugs", "todos")` — no `comments` kind exists, and its own header (`trackers.py:7-9`) says `gaps`/`critique` are "reserved names, promoted only once questions/bugs/todos are proven" — i.e. this file's kind list is deliberately conservative about growing. A `comment` verb needs an explicit storage decision (new tracker kind vs. a ticket-level append log vs. reusing an existing kind) — see Recommended Path and requirements §3 Assumptions.
- Agent identity for `claim`: `ticket.toml` (`knowledge-center/artifacts/T-017/ticket.toml:7`) has `owner` (human, free text) but no field for "which agent/session claimed this." Needs a new field, not a repurposed one — humans and claiming agents are different concerns.
- No session stop-hook exists yet (nothing under `.claude/hooks/` or equivalent references a ticket-update reminder — out of this analysis's direct grounding scope but consistent with the plan's "does not exist today" framing).
- `console setup cursor|claude|vscode` does not exist as a kanban subcommand (`build_parser` in `kanban.py:603-927` has no `setup` subparser).

## Key Findings

- **F1 — Dual kickoff path confirmed, plus a PowerShell coupling the plan doesn't mention:** collapsing onto `kickoff.py`'s path is right, but it makes CLI-only ticket creation (today PowerShell-independent) inherit the PowerShell dependency. Significance: must be stated as an accepted risk/NFR, not silently absorbed.
- **F2 — "Tracker SPI" and `console/server/trackers.py` are different things with the same word.** Significance: requirements must name the new interface distinctly (e.g. "Ticket Tracker SPI" or "Backend SPI") to avoid an implementer wiring it into the wrong module.
- **F3 — No existing plugin shape fits a tracker backend.** `plugins/registry.py` plugins are UI/HTTP feature modules with `apply(ctx)`; the tracker SPI needs its own small interface (list/show/create/move/set/comment/ready/claim per the plan) with vault as the only registered implementation. Significance: this is new architecture, not a config addition — plan correctly scopes it as "shape only" but requirements must be explicit that no generic plugin-loading mechanism is being reused as-is.
- **F4 — `comment` has no storage target today.** Significance: genuine design gap; needs either a new `comments` tracker kind (extending `VALID_KINDS`) or a ticket-level append-only log. Resolved as an assumption below (see requirements §3), not escalated to a blocking question, since it's a reasonable, reversible, low-risk implementation choice.
- **F5 — MCP capability negotiation already correctly says "only what's implemented"** (`mcp.py:166-170`) — adding resources support is additive: extend `capabilities`, add `resources/list`/`resources/read` (+ optionally `resources/subscribe`) methods, wire change notifications through whatever change-bus mechanism `Bus` in the plan's mermaid diagram implies (no such bus exists yet either — also new).
- **F6 — `workspace.toml` and its sibling-folder replacement is fully new**, not a modification of a half-built feature. `find_repo_root` needs a new first step (look for `workspace.toml` upward, use its `console`/`vault` keys) before falling back to today's sibling check, to stay backward compatible with the current single-repo template layout (CLAUDE.md's own default).

## Research

- Plan doc: `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` (full read, lines 1-242) — canonical scope source per task instructions.
- MCP spec version already targeted: `2025-06-18` (`mcp.py:42`), which is the spec version that defines the Streamable HTTP transport and resource change notifications — no version bump needed, only capability additions.

## Recommended Path

Ground truth matches the plan closely on 4 of 5 items (one-api, mcp-first-class, workspace-contract, ready-claim-hooks framing), with two things the plan doesn't spell out that requirements must cover explicitly: (1) the PowerShell coupling inherited by collapsing kickoff paths, and (2) the missing storage target for `comment` and for agent-claim identity. Treat `tracker-spi` as genuinely greenfield (no existing plugin shape to extend) and name it distinctly from `console/server/trackers.py` throughout. Proceed to `requirements draft` grounded in this analysis; resolve F1/F4 as documented assumptions rather than blocking questions, since both are reversible, scoped implementation decisions with no missing stakeholder input.

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
