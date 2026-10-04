---
ticket: "T-016"
artifact: decision-log
---

# Decisions: T-016

Locked with Irshad at kickoff, 2026-09-11, before GROUND analysis. These are product
locks, not implementation picks.

## assistant-as-home
**Decision:** The desktop shell's default view is the Assistant — talk, live runs, and a
ticket strip. Boards, Work, Analytics, Vault, Settings, and the rest remain, as drawers.
The browser-only `kanban.py serve` path may still boot the existing nav; the native shell
is what inverts.

**Rationale:** A person talking to this workspace should not have to pick a tab, a
backend, or a skill to ask what is open or to start work. The current ten-tab IA is a
human kanban app. Voice, tray, and `/api/assistant` already assume a single conversation.
Making that conversation the home matches how the product is used, not how the first
board was drawn.

*Amended 2026-09-11:* “drawers” means other tabs stay reachable, not a hidden
strip. Home is a new first tab when `in-shell` — see [[#in-shell-home-is-first-tab]].
“Cursor work” under hybrid is superseded for launch by
[[#harness-via-cursor-agent-cli]].

## hybrid-harness-runs
**Decision:** The console can launch a named harness role (analyst, planner, builder,
verifier, fixer, harness, deployer) as a Run. Those roles still do their work in Cursor
(or Claude Code). The console does not grow an in-process GROUND→VERIFY loop.

*Superseded in part, same day:* launch is a console `cursor-agent` chat — see
[[#harness-via-cursor-agent-cli]]. The “no in-console GROUND→VERIFY loop” half
still holds.

**Rationale:** The seven agents and 39 skills already live in `.claude/` and are invoked
from the IDE. Duplicating that loop inside the console would be a second orchestrator,
which [[desktop-assistant]] already rejected. What is missing is visibility and a single
starter: the board cannot show "analyst is on T-015", and the Assistant cannot launch
that role as something you can watch.

**Impact:** A Run record must be able to mean "this work is happening in Cursor", not
only "this is a console chat". MCP `delegate` / a future launch verb starts or points at
that work; the transcript may live in the IDE. Do not require the work backend to be a
console-owned CLI session for harness roles.

## ticket-not-wiki-only
**Decision:** This rethink is T-016, a delivery ticket, not only a wiki amendment.
T-015 stays in Verify and closes on its own evidence.

**Rationale:** The change spans product lock, a Run object, verb completeness, and
shell IA. That is multi-session and needs an audit trail. Folding it into T-015 would
mix "make the current Assistant honest" with "change what the console is".

**Impact:** Wiki amendments ([[desktop-assistant]] and any new page) happen on this
ticket, during GROUND/CLARIFY, not instead of the ticket.

## harness-via-cursor-agent-cli
**Decision:** Launching a harness role starts a **console-owned `cursor-agent` CLI
chat** with that persona (`@analyst` etc.). The Run’s executor is the chat id.
This **amends** [[#hybrid-harness-runs]]: work is not the Cursor IDE. There is still
no in-console GROUND→VERIFY loop — the seven agent files stay prompt personas on
that CLI.

**Rationale:** Q1 answered 2026-09-11 option (b). Cursor IDE has no inbound start
API in this repo. The `cursor-agent` backend already exists
(`console/config/agents.toml` id `cursor-agent`, transport `resume`). A console
chat is something the Run inspector can watch.

**Impact:** If `cursor-agent` is not installed, launch fails honestly (same class
as any missing backend). Do not silently fall through to `claude`. Tagged-union
Runs (Q2) will usually be `chat` for harness launches. Prompt-package and
MCP-claim options are out of T-016.

## run-is-tagged-union
**Decision:** A Run is a small new record that **points at** an existing chat id
and/or job id and/or cursor-pointer. It is not an extension of `jobs.py` (verb-only)
and not chat ids alone.

**Rationale:** Q2, 2026-09-11. `jobs.py:5` already says agent subprocesses are
untracked; stuffing chats into jobs would lie. A wrapper-only-chats store would
drop any future pointer. A tagged union reuses stores.

**Impact:** New module/files under `console/.cache/runs/` (gitignored, like chats).
Schema is a planning detail; the union is the lock.

## verbs-this-ticket
**Decision:** T-016 adds verbs for `ticket move`, `ticket set`, `tracker add`,
`tracker update` only. progress-append, close-work, and log-work are deferred.

**Rationale:** Q3. Locked In list already named move/set/tracker. Extra verbs are
scope-creep (CR-5).

**Impact:** MCP/API agents still cannot append progress.md through a verb after
this ticket. That stays a later ticket or file tools.

## in-shell-home-is-first-tab
**Decision:** Assistant-as-home is a **new first tab** (`register_tab`), placed first
in `NAV_ORDER` when `html.in-shell`. Other tabs stay in the strip. Browser without
`in-shell` keeps current order (Overview first).

**Rationale:** Q4. Matches the plugin contract; less new chrome than hiding the
strip. Amends the metaphor “drawers” in [[#assistant-as-home]] to “other tabs
remain visible”.

**Impact:** `shell_feature.py` NAV_ORDER becomes context-sensitive, or the Assistant
plugin registers a tab the shell sorts first only when in-shell. Tests must cover
both classes.

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]]
- [[desktop-assistant]] · [[T-015-summary]]
