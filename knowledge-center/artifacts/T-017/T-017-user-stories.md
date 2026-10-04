---
ticket: "T-017"
artifact: user-stories
created: "2026-09-16"
---

# User Stories: T-017

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-017 stories` · **Validated by:** `validate-artifacts T-017 links` · **Verified by:** `validate-artifacts T-017 links`

Source: [[T-017-requirements]] (frozen, iteration 2, 11 FRs). Full FR detail: [[T-017-requirements-draft]] §4.

## Stories

### US-1: Uniform `--json` contract on every CLI subcommand

**As a** CLI caller (human, skill, agent, or CI script)
**I want to** get consistent, valid JSON from every `console/kanban.py` subcommand
**So that** scripts and agents never need special-case parsing for text-vs-JSON output

**Acceptance Criteria:**
- [ ] A scripted audit of `build_parser()` shows every leaf subcommand either always emits JSON or accepts `--json`
- [ ] `console/tests/` gains ≥1 test per subcommand group asserting `--json` output parses as valid JSON
- [ ] No subcommand's `--json` output is contaminated by a stray `print()` on the same stream

**Business Rules:** BR-1, BR-2

**Edge Cases:**
- Interactive-only commands (e.g. `reset`'s confirmation prompt) documented as intentionally non-JSON, not silently left inconsistent

**Related Components:** CLI (console/kanban.py)
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** Medium
**Story Points:** 3

---

### US-2: One ticket-creation path

**As an** agent, skill, or CI script creating a ticket
**I want to** have `ticket create` (CLI) and `kickoff` (verb) produce identical artifacts
**So that** ticket creation behaves the same regardless of entry point, with no bare-TOML shortcut left reachable

**Acceptance Criteria:**
- [ ] `console/kanban.py ticket create` and `console/kanban.py verb run kickoff` produce the same three artifacts (ticket.toml, rendered templates, artifact-map row) for equivalent inputs
- [ ] Regression test asserts `cmd_ticket_create`'s old bare-TOML-only path is no longer reachable as a public action
- [ ] `PowerShellUnavailable` surfaces as a clean CLI/MCP/HTTP error (not a traceback) when PowerShell is missing, from every entry point

**Business Rules:** BR-1, BR-2

**Edge Cases:**
- PowerShell unavailable during ticket creation, any entry point post-collapse (A1)

**Related Components:** CLI (console/kanban.py), server/kickoff.py
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** High
**Story Points:** 5

---

### US-3: MCP resources capability + change notifications

**As an** MCP client (Cursor, Claude Code, VS Code)
**I want to** list and read ticket-context resources and be notified when they change
**So that** I can track ticket state without polling `tools/call`

**Acceptance Criteria:**
- [ ] `initialize` declares `resources` capability once implemented; today's tools-only response does not regress
- [ ] `resources/list` returns ≥ ticket-context resources; `resources/read` returns the same data the `context` verb produces
- [ ] A test simulates a verb mutation and asserts a change notification is emitted to a subscribed session

**Business Rules:** BR-1

**Edge Cases:**
- MCP client sends a request without a prior `initialize` → server responds per existing JSON-RPC/MCP error semantics, not a crash

**Related Components:** MCP server (console/server/mcp.py)
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-4: MCP Streamable HTTP transport on `serve`

**As an** editor MCP client
**I want to** connect to a running `console serve` process over HTTP instead of spawning a stdio subprocess
**So that** multiple editors can share one running console instance

**Acceptance Criteria:**
- [ ] `serve` exposes an MCP-over-HTTP endpoint alongside existing UI/API routes, without a separate process or port
- [ ] Same `tools/list`/`tools/call` results returned over HTTP as over stdio for an equivalent request
- [ ] `console setup <editor>` (US-8)-generated config points at the HTTP endpoint when the editor supports it

**Business Rules:** BR-1

**Edge Cases:**
- No new auth scheme (NFR, deferred — same trust boundary as today's unauthenticated local `serve`, per a5/§13)

**Related Components:** MCP server (console/server/mcp.py), CLI serve (console/kanban.py)
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-5: Tracker Backend SPI (shape only), vault-only adapter

**As** console core (CLI/MCP/HTTP handlers)
**I want to** call ticket-state operations through one Backend SPI interface instead of vault functions directly
**So that** a future non-vault adapter could be added later without changing call sites, while today only vault is registered

**Acceptance Criteria:**
- [ ] Interface defined once (list/show/create/move/set/comment/ready/claim), imported by ≥ `ready`/`claim`/`comment`/`ticket-move` handlers
- [ ] Zero Jira/Azure/Linear/GitHub Issues code exists anywhere in the diff
- [ ] Vault remains canonical; a design note states a future non-vault adapter would sync, not replace, the vault lane

**Business Rules:** BR-4

**Edge Cases:**
- Named distinctly ("Backend SPI") from `console/server/trackers.py`'s questions/bugs/todos CRUD to avoid the terminology collision (a4/F2)

**Related Components:** New Backend SPI module (console/server/backends/), tickets.py, trackers.py, vault.py
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-6: `workspace.toml` support in repo-root resolution

**As an** operator running a split vault/console/project layout
**I want to** `find_repo_root` resolve roots from a `workspace.toml` when present
**So that** the console works without `knowledge-center/` and `console/` being sibling folders, with zero behavior change when no `workspace.toml` exists

**Acceptance Criteria:**
- [ ] Existing single-repo checkouts (no `workspace.toml`) behave identically — regression test pins today's `find_repo_root` behavior unchanged
- [ ] A test fixture with `console/`/`knowledge-center/` in separate directories, bound by a `workspace.toml`, resolves correctly
- [ ] `RepoRootError`'s message mentions `workspace.toml` as an alternative when neither resolution succeeds

**Business Rules:** BR-5

**Edge Cases:**
- `workspace.toml` present but its `vault`/`console` paths don't exist on disk → clear named error, not a generic `FileNotFoundError`

**Related Components:** console/server/paths.py
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** Medium
**Story Points:** 5

---

### US-7: `ready` and `claim` verbs for pulling work

**As an** agent or human looking for pullable work
**I want to** list unblocked, unclaimed tickets and claim one under my identity
**So that** two agents never silently collide on the same ticket

**Acceptance Criteria:**
- [ ] `ready` excludes any ticket with an open critical question/bug (`_IS_BLOCKER`) and any ticket with non-empty `claimed_by`; identical via CLI/MCP/HTTP
- [ ] `claim` sets `claimed_by`/`claimed_at`; two concurrent claims by different identities → exactly one succeeds, the other gets a named "already claimed by X" error, no corrupted TOML
- [ ] `claim` is audited (`console/server/audit.py`); re-claiming by the same identity is idempotent (documented behavior)

**Business Rules:** BR-1, BR-2, BR-3

**Edge Cases:**
- `ready` called when every ticket is blocked or claimed → empty list, not an error
- Two agents call `claim` on the same ticket near-simultaneously → race-safe via atomic write/replace

**Related Components:** verb_handlers.py, verbs.toml, Backend SPI, ticket.toml schema
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** High
**Story Points:** 8

---

### US-8: `comment` verb, stop-hook, and editor setup

**As an** agent or human leaving a note on a ticket, or onboarding an editor
**I want to** append attributed comments, be reminded if I exit without updating a claimed ticket, and wire my editor's MCP config in one command
**So that** ticket state never silently drifts and editor onboarding needs no manual JSON editing

**Acceptance Criteria:**
- [ ] `comments` appears in `trackers.VALID_KINDS`, never blocks release (mirrors `todos`); comment is attributed + timestamped; readable via `tracker list <id> comments`
- [ ] Stop-hook: claim → no update → session end → reminder recorded; claim → update → session end → no reminder; hook never crashes session end
- [ ] `console setup cursor|claude|vscode` is idempotent, writes to each editor's documented config location, includes an `AGENTS.md` snippet warning against hand-editing ticket/tracker TOML

**Business Rules:** BR-1, BR-2

**Edge Cases:**
- `comment` on a ticket with no prior `{T}-comments.toml` → file created on first use, mirroring existing tracker scaffolding
- `console setup <editor>` run where a hand-written config already exists for that editor → merges, doesn't silently overwrite unrelated entries

**Related Components:** trackers.py, verb_handlers.py, verbs.toml, session hooks, kanban.py (setup subcommand)
**Related Tasks:** _filled by breakdown-tasks_

**Priority:** Medium
**Story Points:** 8

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Uniform `--json` contract | Pending | Medium | 3 | — |
| US-2 | One ticket-creation path | Pending | High | 5 | — |
| US-3 | MCP resources + change notifications | Pending | High | 8 | — |
| US-4 | MCP Streamable HTTP transport | Pending | High | 8 | — |
| US-5 | Tracker Backend SPI | Pending | High | 8 | — |
| US-6 | `workspace.toml` resolution | Pending | Medium | 5 | — |
| US-7 | `ready`/`claim` verbs | Pending | High | 8 | — |
| US-8 | `comment` verb, stop-hook, editor setup | Pending | Medium | 8 | — |

## Traceability Matrix

| Story | FRs | Components | Tasks |
|-------|-----|-----------|-------|
| US-1 | FR-1 | CLI (kanban.py) | — |
| US-2 | FR-2 | CLI, server/kickoff.py | — |
| US-3 | FR-3 | MCP server (mcp.py) | — |
| US-4 | FR-4 | MCP server, CLI serve | — |
| US-5 | FR-5 | Backend SPI (new), tickets.py, trackers.py, vault.py | — |
| US-6 | FR-6 | server/paths.py | — |
| US-7 | FR-7, FR-8 | verb_handlers.py, verbs.toml, Backend SPI, ticket.toml | — |
| US-8 | FR-9, FR-10, FR-11 | trackers.py, verb_handlers.py, verbs.toml, hooks, kanban.py | — |

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-requirements-draft]] · [[T-017-user-stories]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
