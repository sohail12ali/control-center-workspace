---
ticket: "T-017"
artifact: requirements-draft
status: drafting
freeze_status: open
iteration: 2
created: "2026-09-16"
last_updated: "2026-09-16"
---

# Requirements Draft: T-017

> Working requirements document. **Not frozen.** Expect revisions each iteration until `requirements T-017 freeze` passes.

**Command reference:**
- **Created by:** `requirements T-017 draft`
- **Grounded by:** `analyze T-017` → [[T-017-context-snapshot]]
- **Gaps surfaced by:** `challenge-requirements T-017` (gaps dimension)
- **Challenged by:** `challenge-requirements T-017` (adds ⚠ markers below)
- **Enriched by:** `requirements T-017 enrich`
- **Cross-checked by:** `challenge-requirements T-017` (overlap/conflict/reuse dimension)
- **Iterated by:** `requirements T-017 iterate`
- **Frozen by:** `requirements T-017 freeze` → [[T-017-requirements]]

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Make the Delivery Console one product regardless of which surface (CLI, MCP, HTTP/UI) drives it, extensible via a real tracker-backend plugin shape, portable to a split vault/console/project layout, and pull-friendly for agents (ready/claim/comment) with a safety net (stop-hook) so ticket state never silently drifts.

**Business driver:** Today CLI/MCP/HTTP drift (dual kickoff path, MCP lacks resources/HTTP), the console cannot run unless `knowledge-center/` and `console/` are siblings, and agents have no first-class way to pull and claim work or leave a paper trail before exiting a session.

**Raw intent verbatim:**
> "Delivery Console core: one API, MCP resources/HTTP, tracker SPI, workspace.toml, ready/claim/comment verbs" — ticket title, sourced from `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` §"How the improved console works (T-017 scope)".

## 2. Context Summary

(Condensed from [[T-017-context-snapshot]])

- **Similar existing features:** the verb registry (`console/config/verbs.toml` + `verb_handlers.py`) already proves the "one handler, many adapters (CLI/MCP/HTTP)" shape `ready`/`claim`/`comment` should follow. The UI-plugin loader (`console/server/plugins/registry.py`) proves the interface+registration pattern the tracker-backend SPI should mirror, though it cannot be reused directly (different concern — UI features, not ticket-storage backends).
- **Affected code areas:** `console/kanban.py`, `console/server/mcp.py`, `console/server/paths.py`, `console/server/vault.py`, `console/server/kickoff.py`, `console/server/tickets.py`, `console/server/trackers.py`, `console/config/verbs.toml`, `console/server/verb_handlers.py`; new modules for the tracker-backend SPI and `workspace.toml` loading.
- **Known risks from history:** T-016's Run object (`console/server/runs.py`) and `launch-role`/`run-list`/`run-show` verbs are read-only context — not modified. T-018 depends on `claimed_by`/verb contracts this ticket defines, so those contracts should be stable, not throwaway.

## 3. Scope

### In scope
- Uniform `--json` contract across every `console/kanban.py` subcommand (FR-1).
- Collapsing the dual ticket-creation path into one (FR-2).
- MCP `resources` capability + change notifications, additive to the existing stdio tool surface (FR-3).
- MCP streamable HTTP transport mounted on the existing `serve` command; stdio remains available (FR-4).
- Tracker **backend** SPI (interface shape only) with vault as the sole real adapter (FR-5).
- `workspace.toml` support in repo-root resolution, replacing the hard sibling-folder requirement while staying backward compatible (FR-6).
- `ready`, `claim`, `comment` verbs, each exposed identically via CLI/MCP/HTTP (FR-7, FR-8, FR-9).
- Session stop-hook reminding an agent to update its claimed ticket before exiting (FR-10).
- `console setup cursor|claude|vscode` command (FR-11).

### Out of scope (explicit)
- Any real Jira/Azure Boards/Linear/GitHub Issues tracker-backend adapter — SPI shape only, per plan lines 12, 49, 88, 111, 175, 229.
- The 39→12 skill harness-kernel collapse — separate future ticket (plan line 49, 230).
- Voice/barge-in/VAD work — T-015's territory (plan line 231).
- Worktree-per-Run, ticket-id-in-branch, PR linkage, lane-hints-from-git, Run-inspector diffstat — all T-018, which depends on this ticket (plan lines 20-21, 48, 196-205, 220-221).
- Any modification to T-015 or T-016 artifacts or to `console/server/runs.py` — read-only reference only.
- A change bus / SSE UI live-sync beyond what MCP resource-change-notification requires for editor clients — the plan's mermaid diagram shows `Bus → HTTP` for UI EventSource too (plan line 153), but the ticket title and explicit scope list (plan lines 5-19) do not name a UI-side EventSource requirement; treated as a `⚠` — see §13.
- Real-time WebSocket UI updates — not named in the 5-item scope list; same `⚠` as above.

### Assumptions
- **A1 (resolves F1, analysis):** Collapsing `cmd_ticket_create` into `kickoff.py`'s `create_ticket` path is accepted, including its existing PowerShell dependency on Windows; this is documented as a known constraint (NFR, §5) rather than escalated as a blocker, because it is a pre-existing limitation of the fuller path, not a new one introduced by this ticket. A non-Windows fallback is out of scope for T-017 unless already planned elsewhere (none found).
- **A2 (resolves F4, analysis):** `comment` is stored as a new `comments` kind added to `console/server/trackers.py`'s `VALID_KINDS`, reusing the existing questions/bugs/todos CRUD shape (`add`/`list`/`update`) rather than a new file format. Comments never block release (mirrors `todos`' `_IS_BLOCKER` predicate returning `False`).
- **A3:** Agent-claim identity is stored as new `ticket.toml` fields (`claimed_by`, `claimed_at`), distinct from the existing human `owner` field, mutated only via the new `claim` verb (never hand-edited, consistent with CANONICAL rule).
- **A4:** "Tracker SPI" in the plan means a **ticket-storage backend** abstraction (vault vs. a hypothetical future Jira/Azure/etc.), not `console/server/trackers.py`'s questions/bugs/todos CRUD. Code introduced for this requirement is named to avoid the collision (e.g. a `console/server/backends/` or `console/server/store/` package with a `Tracker` interface class), and this requirements document uses "Backend SPI" when precision matters, "tracker-spi" only as the plan's scope-item label.
- **A5:** MCP streamable HTTP transport targets the same protocol version already declared (`2025-06-18`, `console/server/mcp.py:42`), which defines Streamable HTTP; no protocol-version bump is required.
- **A6:** `ready` means "tickets with no blocking open questions/bugs and no `claimed_by`, filterable by stage" — reusing the existing blocker predicate in `console/server/trackers.py` (`_IS_BLOCKER`) and `console/server/verb_handlers.py`'s `ticket_blockers`. Not a new blocking-logic engine.
- **A7:** `workspace.toml` is optional. Its absence must not change behavior for any existing single-repo checkout (the template `CLAUDE.md` layout) — `find_repo_root` tries `workspace.toml` resolution first, then falls back unchanged to today's sibling-folder check.

## 4. Functional Requirements

### FR-1: Uniform `--json` contract on every `console/kanban.py` subcommand
**Description:** Every subcommand under `kanban.py` must support (or unconditionally emit) machine-readable JSON on stdout, with a documented, consistent shape (top-level object or array, no mixed prose+JSON on one stream).

**Actor:** Any CLI caller — human, skill, agent, or CI script.

**Trigger:** Any `python console/kanban.py <group> <action> [--json]` invocation.

**Preconditions:**
- Repo root resolvable (`find_repo_root`, extended per FR-6).

**Flow:**
1. Caller runs a subcommand, with or without `--json` where the flag exists today.
2. Command handler prints exactly one JSON value to stdout on `--json`/JSON-only commands; errors go to stderr via `_die` (`kanban.py:26-28`), unchanged.

**Postconditions / observable outcomes:**
- Every subcommand's `--help` and behavior confirm JSON support; commands that today print human-formatted text only (if any remain after this audit) either gain `--json` or are documented as intentionally interactive-only (e.g. `reset`'s confirmation prompt).

**Acceptance criteria (testable):**
- [ ] A scripted audit of `build_parser()` shows every leaf subcommand either always emits JSON or accepts `--json` (cite the resulting list in the implementation plan).
- [ ] `console/tests/` gains at least one test per subcommand group asserting `--json` output parses as valid JSON.
- [ ] No subcommand's `--json` output is contaminated by a stray `print()` on the same stream.

**Business rules invoked:** BR-1, BR-2

### FR-2: One ticket-creation path
**Description:** `cmd_ticket_create` in `kanban.py` (`kanban.py:41-46`) is removed or rewritten to call the same `create_ticket` flow as the `kickoff` verb (`console/server/kickoff.py`), so `console ticket create` and `console verb run kickoff` produce identical artifacts (ticket.toml, rendered templates, artifact-map row).

**Actor:** CLI caller, MCP client, HTTP client, `kickoff` skill.

**Trigger:** `console ticket create ...` / `kickoff` verb call from any adapter.

**Preconditions:** PowerShell available on PATH (inherited constraint, A1).

**Flow:**
1. Caller invokes ticket creation from any of CLI/MCP/HTTP.
2. Single code path performs id generation, template render, artifact-map row append.
3. Same result shape returned regardless of entry point.

**Postconditions / observable outcomes:** Exactly one function in the codebase creates a ticket; `tickets.create()` (bare TOML) is no longer reachable as a top-level "ticket create" user action (it may remain as an internal helper called by the unified path).

**Acceptance criteria (testable):**
- [ ] `console/kanban.py ticket create` and `console/kanban.py verb run kickoff` produce the same three artifacts for equivalent inputs.
- [ ] A regression test asserts `cmd_ticket_create`'s old bare-TOML-only behavior no longer exists as a public path.
- [ ] `PowerShellUnavailable` surfaces as a clear, honest CLI error (not a traceback) when PowerShell is missing, on whichever entry point is used.

**Business rules invoked:** BR-1, BR-2

### FR-3: MCP resources capability + change notifications
**Description:** `console/server/mcp.py` gains `resources/list`, `resources/read`, and (if the client subscribes) `resources/subscribe` / `notifications/resources/updated`, declared in `initialize`'s `capabilities` (`mcp.py:162-170`) only once implemented.

**Actor:** MCP client (Cursor, Claude Code, VS Code) over stdio or HTTP.

**Trigger:** Client calls `resources/list` or `resources/read`, or a console-side mutation changes a resource a client has subscribed to.

**Preconditions:** Session `initialize`d (`mcp.py:172-192`).

**Flow:**
1. Client lists resources (e.g. one resource per ticket, or a `context` digest resource).
2. Client reads a resource by URI.
3. On a mutation (verb run) affecting a subscribed resource, server sends `notifications/resources/updated`.

**Postconditions / observable outcomes:** A client can read ticket state without polling `tools/call`, and is notified when it changes.

**Acceptance criteria (testable):**
- [ ] `initialize` response declares `resources` capability once implemented; today's response (tools-only) does not regress for clients that ignore resources.
- [ ] `resources/list` returns at least ticket-context resources; `resources/read` returns the same data `context` verb already produces (`verb_handlers.ticket_context`).
- [ ] A test simulates a verb mutation and asserts a change notification is emitted to a subscribed session.

**Business rules invoked:** BR-1

### FR-4: MCP streamable HTTP transport on `serve`
**Description:** The already-running HTTP process started by `console/kanban.py serve` (`kanban.py:557-560`, `server/httpd.py`) additionally exposes the MCP Streamable HTTP transport (POST for requests/responses, GET+SSE for server-initiated messages), so multiple editor clients share one running console instance. stdio (`console/mcp_server.py`) remains available for offline/single-client use.

**Actor:** Editor MCP clients configured for HTTP transport; `console setup <editor>` (FR-11) writes this configuration.

**Trigger:** `console/kanban.py serve` is running; a client connects over HTTP instead of spawning a stdio subprocess.

**Preconditions:** `serve` process reachable on its configured host/port.

**Flow:**
1. Operator runs `console/kanban.py serve`.
2. Editor client, configured via `console setup <editor>`, connects to the MCP HTTP endpoint on the same host/port as the UI.
3. Same `verbs.registry()`-derived tool set and new resources are available as over stdio.

**Postconditions / observable outcomes:** One running `serve` process answers CLI-equivalent MCP calls for every connected editor; killing one editor's connection doesn't affect others.

**Acceptance criteria (testable):**
- [ ] `serve` exposes an MCP-over-HTTP endpoint alongside existing UI/API routes, without a separate process or port.
- [ ] The same `tools/list`/`tools/call` results are returned over HTTP as over stdio for an equivalent request.
- [ ] `console setup <editor>` (FR-11)-generated config points at the HTTP endpoint when the editor supports it.

**Business rules invoked:** BR-1

**NFR note:** the HTTP MCP endpoint runs on a local/dev host by default (no new auth scheme is specified by the plan); see §5 Security row and §13 challenge finding.

### FR-5: Tracker backend SPI (shape only), vault-only adapter
**Description:** Introduce a `Tracker`-shaped interface (per plan: `list` / `show` / `create` / `move` / `set` / `comment` / `ready` / `claim`) as a small Python interface (e.g. abstract base class or protocol) under a new module distinct from `console/server/trackers.py` (see A4), with exactly one registered implementation: the existing vault-backed logic (`tickets.py`, `trackers.py`, `vault.py` wrapped/adapted to the interface, not rewritten).

**Actor:** Console core (CLI/MCP/HTTP handlers) — calls the interface, not vault functions directly, wherever the plan's verb list (`context`, `ready`, `claim`, `ticket-move`, `tracker-add`, `run-show`) touches ticket state.

**Trigger:** Any verb/handler that mutates or reads ticket state.

**Preconditions:** None beyond the vault adapter being registered as the (only) implementation at startup.

**Flow:**
1. Core resolves "the tracker backend" (vault, today's only registration).
2. Core calls interface methods; the vault adapter delegates to existing `tickets.py`/`trackers.py` functions.

**Postconditions / observable outcomes:** A future adapter (Jira/etc., out of scope here) could be added by implementing the same interface and registering it, without changing core call sites — demonstrated by the interface existing and the vault path passing through it, not by a second adapter actually shipping.

**Acceptance criteria (testable):**
- [ ] The interface is defined once, documents each of the 8 named operations, and is imported by at least the `ready`/`claim`/`comment`/`ticket-move` handlers (FR-7/8/9 and existing `ticket-move`).
- [ ] No Jira/Azure/Linear/GitHub Issues code exists anywhere in the diff.
- [ ] Vault remains canonical: a design note states a future non-vault adapter would sync identity/status/comments, not replace the vault lane, per plan line 176.

**Business rules invoked:** BR-4

### FR-6: `workspace.toml` support in repo-root resolution
**Description:** `console/server/paths.py`'s `find_repo_root` first looks upward for a `workspace.toml` (schema per plan: `name`, `vault`, `console`, `projects`); if found, resolves `console`/vault roots from it. If not found, falls back unchanged to today's `_is_repo_root` sibling-folder check (A7).

**Actor:** Every module calling `find_repo_root()` (effectively the whole CLI/MCP/HTTP surface).

**Trigger:** Any console entry point starting up.

**Preconditions:** None — this is the first resolution step.

**Flow:**
1. Search upward from `start`/cwd/package location for `workspace.toml`.
2. If found, read `vault`/`console`/`projects` paths (relative to the toml's directory) and use them as the resolved roots.
3. Else, run today's `_is_repo_root` sibling search unchanged.

**Postconditions / observable outcomes:** A console checkout with `knowledge-center/` in a separate repo, bound via `workspace.toml`, works identically to today's single-repo layout from every existing call site.

**Acceptance criteria (testable):**
- [ ] Existing single-repo checkouts (no `workspace.toml`) behave identically — a regression test pins today's `find_repo_root` behavior unchanged.
- [ ] A test fixture with `console/` and `knowledge-center/` in separate directories, bound by a `workspace.toml`, resolves correctly.
- [ ] `RepoRootError`'s message is updated to mention `workspace.toml` as an alternative when neither resolution succeeds.

**Business rules invoked:** BR-5

### FR-7: `ready` verb
**Description:** A new read-only verb listing tickets that are unblocked (no open critical questions/bugs per existing `_IS_BLOCKER` logic, A6) and unclaimed (`claimed_by` empty), optionally filtered by stage/kind.

**Actor:** Agent or human looking for pullable work.

**Trigger:** `console verb run ready` / MCP tool `ready` / HTTP equivalent.

**Preconditions:** None (read-only).

**Flow:**
1. Caller invokes `ready`, optionally with a stage/kind filter.
2. Handler lists tickets, applies blocker + unclaimed filters via the Backend SPI (FR-5).
3. Returns the filtered list, JSON by default (FR-1).

**Postconditions / observable outcomes:** Caller sees only tickets with no blocking open critical items and no current claim.

**Acceptance criteria (testable):**
- [ ] `ready` excludes any ticket with an open critical question or unverified critical bug (reusing `_IS_BLOCKER`).
- [ ] `ready` excludes any ticket with a non-empty `claimed_by`.
- [ ] Available identically via CLI (`kanban.py verb run ready`), MCP tool, and HTTP.

**Business rules invoked:** BR-1

### FR-8: `claim` verb with agent identity
**Description:** A new mutating verb (`needs_confirm = true`, per existing convention) that sets `claimed_by`/`claimed_at` on a ticket (A3), refusing if already claimed by a different identity (no silent double-claim).

**Actor:** Agent or human claiming a ticket to work on.

**Trigger:** `console verb run claim --ticket T-xxx --set agent=<id> --confirm` / MCP tool `claim` / HTTP equivalent.

**Preconditions:** Ticket exists; ticket not already claimed by a different agent identity.

**Flow:**
1. Caller invokes `claim` with a ticket id and an agent identity string.
2. Handler checks current `claimed_by`; if empty or equal to the caller's identity, sets `claimed_by`/`claimed_at` (via the Backend SPI, never hand-editing ticket.toml).
3. If claimed by someone else, the verb fails with a clear error naming the current claimant.

**Postconditions / observable outcomes:** `ticket.toml` (or its Backend-SPI equivalent) records who is working the ticket and when they started.

**Acceptance criteria (testable):**
- [ ] Two concurrent `claim` calls for the same ticket by different identities: exactly one succeeds, the other gets a clear "already claimed by X" error (no corrupted TOML from a race — see Edge Cases §8).
- [ ] `claim` is logged in `console/server/audit.py`'s audit trail (consistent with other mutating verbs).
- [ ] Re-claiming by the same identity is idempotent (no error, refreshes `claimed_at` or is a no-op — pick one and document it).

**Business rules invoked:** BR-1, BR-2, BR-3

### FR-9: `comment` verb
**Description:** A new mutating verb appending a timestamped, attributed comment to a ticket, stored via a new `comments` tracker kind (A2), visible to humans and agents on the same thread (plan line 81).

**Actor:** Agent or human leaving a note on a ticket.

**Trigger:** `console verb run comment --ticket T-xxx --set text=... --set author=... --confirm` / MCP tool `comment` / HTTP equivalent.

**Preconditions:** Ticket exists.

**Flow:**
1. Caller invokes `comment` with ticket id, text, and author/identity.
2. Handler calls `trackers.add(repo_root, ticket_id, "comments", text, author=...)` (extending `VALID_KINDS`).
3. Comment is listed via the existing `tracker list` path (`kanban.py tracker list <id> comments`) once `comments` is a valid kind.

**Postconditions / observable outcomes:** A per-ticket, append-only, attributed comment log exists, readable the same way questions/bugs/todos are.

**Acceptance criteria (testable):**
- [ ] `comments` appears in `trackers.VALID_KINDS` and behaves like `todos` for blocking purposes (never blocks release — A2).
- [ ] A comment is attributed (author field) and timestamped.
- [ ] `console/kanban.py tracker list <id> comments` returns the full thread.

**Business rules invoked:** BR-1, BR-2

### FR-10: Session stop-hook
**Description:** A hook that fires when an agent session ends, checking whether the session's claimed ticket(s) were moved/commented/released, and if not, emits a reminder (best-effort — cannot force an already-exited process to act, but must warn on the next opportunity, e.g. via console startup or a dashboard flag).

**Actor:** The harness (session lifecycle), on behalf of any agent that called `claim`.

**Trigger:** Session-stop event (mirrors existing `refresh --quiet` session hooks per `CLAUDE.md`'s "Console sync" section).

**Preconditions:** At least one ticket claimed by the exiting session's identity with no subsequent move/comment/release in that session.

**Flow:**
1. Session ends.
2. Hook checks claimed tickets for that session identity against the audit log / claim timestamp.
3. If no ticket-state update happened since claim, hook surfaces a reminder (console-side flag, log line, or next-session prompt — mechanism to be finalized in planning, not requirements).

**Postconditions / observable outcomes:** An agent that claims a ticket and exits without updating it is flagged, not silently forgotten.

**Acceptance criteria (testable):**
- [ ] A test simulates claim → session end with no update → reminder recorded/surfaced.
- [ ] A test simulates claim → move/comment → session end → no reminder.
- [ ] Hook failure never crashes the session end sequence (mirrors `cmd_refresh`'s own "hooks must never crash a session" guard, `kanban.py:589-598`).

**Business rules invoked:** BR-1

### FR-11: `console setup <editor>` command
**Description:** New `console setup cursor|claude|vscode` subcommand writing MCP client configuration (pointing at stdio or the new HTTP transport, FR-4) plus a short `AGENTS.md` snippet instructing the agent to use these tools and never hand-edit `ticket.toml`/tracker TOML.

**Actor:** Human onboarding an editor to a workspace.

**Trigger:** `console/kanban.py setup <editor>`.

**Preconditions:** Repo root resolvable (FR-6).

**Flow:**
1. Operator runs `console setup cursor` (or `claude`/`vscode`).
2. Command writes/updates the editor's MCP config file (location per-editor convention, e.g. `.cursor/mcp.json`, `.mcp.json`, VS Code's MCP settings) and appends/creates a short `AGENTS.md` snippet.
3. Command reports what it wrote, idempotently (safe to re-run).

**Postconditions / observable outcomes:** The named editor is wired to this console's MCP surface without manual JSON editing.

**Acceptance criteria (testable):**
- [ ] Running `console setup cursor` twice produces the same result the second time (idempotent), not a duplicated block.
- [ ] Each of the three editor targets writes to its own documented config location.
- [ ] The `AGENTS.md` snippet explicitly says never to hand-edit `ticket.toml`/tracker TOML.

**Business rules invoked:** BR-2

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | `--json` uniformity adds no material CLI latency | No perceptible regression vs. current commands | Pure formatting-path change, not new computation |
| Compatibility | `find_repo_root` behaves identically for checkouts without `workspace.toml` | 100% of existing tests pass unchanged | A7 |
| Compatibility | Ticket creation still fails honestly (not a traceback) when PowerShell is absent | `PowerShellUnavailable` surfaced from every entry point that now shares FR-2's path | A1 — inherited constraint, documented not silently fixed |
| Security / Auth | MCP HTTP transport access control | 〈TBD — no auth scheme specified by the plan; assumed same trust boundary as today's local `serve` (no new auth) unless the operator's environment already fronts it〉 | See §13 ⚠ — flagged, not blocking, since `serve` today has no auth either |
| Auditability | `claim`/`comment`/`ready`(read)/kickoff-collapse mutations are all recorded | Every mutating verb call appears in `console/server/audit.py`'s log, consistent with existing mutating verbs | FR-8, FR-9 |
| Concurrency | `claim` race safety | No two concurrent claims by different identities both succeed | FR-8 edge case |
| Usability | `console setup <editor>` output is self-explanatory | A first-time user completes editor wiring without reading source | FR-11 |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `ticket.toml` (changed) | exists | + `claimed_by`, `claimed_at` | set by `claim`, cleared by `ticket-move`-to-done or an explicit release action (mechanism `⚠`, see §13) | `knowledge-center/artifacts/T-017/ticket.toml` |
| `{T}-comments.toml` (new) | new, mirrors `{T}-questions.toml`/`{T}-bugs.toml`/`{T}-todos.toml` shape | id, text, author, created, status | create on first comment; append-only | `console/server/trackers.py` pattern |
| `workspace.toml` (new) | new | `name`, `vault`, `console`, `projects` | created manually by an operator (not console-generated in T-017 scope) | plan lines 182-188 |
| Backend SPI interface (new, code not data) | new | `list`/`show`/`create`/`move`/`set`/`comment`/`ready`/`claim` methods | one registration (vault) at startup | plan lines 174-177 |

### Data flows
- CLI/MCP/HTTP → verb handler → Backend SPI (vault adapter) → `tickets.py`/`trackers.py` → TOML files under `knowledge-center/artifacts/{T}/`.
- `workspace.toml` (if present) → `find_repo_root` → resolved `console`/`vault` roots → every downstream path computation.

### Retention / archival
- Comments and claim fields follow the ticket's own lifecycle (archived with the ticket per `close-work`); no separate retention policy introduced.

## 7. Business Rules

- **BR-1:** No write path to ticket/tracker state exists outside the Backend SPI; CLI, MCP, and HTTP are adapters over the same core functions (plan line 161).
- **BR-2:** `ticket.toml` and tracker `.toml` files are CLI-mutated only, never hand-edited (CANONICAL rule, `CLAUDE.md`).
- **BR-3:** Every new mutating verb (`claim`, `comment`) requires `confirm=true`, consistent with every existing mutating verb in `verbs.toml`.
- **BR-4:** Vault is the sole registered Backend SPI implementation in T-017; no other adapter ships (plan lines 12, 175).
- **BR-5:** `workspace.toml` is optional; its absence must not change resolution behavior for existing checkouts (A7).

## 8. Edge Cases

- `workspace.toml` present but its `vault`/`console` paths don't exist on disk → `find_repo_root` (or the caller) raises a clear error naming the missing path, not a generic `FileNotFoundError` deep in an unrelated module.
- Two agents call `claim` on the same unclaimed ticket at nearly the same time → exactly one wins; the loser gets a named "already claimed by X" error, not a corrupted `ticket.toml` (requires the same file-write safety `tickets.py`/`trackers.py` already use, e.g. atomic write/replace).
- `ready` called when every ticket is either blocked or claimed → returns an empty list, not an error.
- `comment` called on a ticket with no prior `{T}-comments.toml` → file is created on first use, mirroring how `{T}-questions.toml` etc. are scaffolded by `kickoff`.
- MCP HTTP client sends a request without a prior `initialize` → server responds per JSON-RPC/MCP error semantics already used for unknown methods (`mcp.py:212-214`), not a crash.
- `console setup <editor>` run in a repo with an existing hand-written MCP config for that editor → command must not silently overwrite unrelated existing entries; merges or clearly reports what would change.
- PowerShell unavailable during ticket creation (any entry point, post-FR-2) → `PowerShellUnavailable` surfaces as a clean CLI/MCP/HTTP error (A1), not a stack trace.

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[T-016-summary]] Run object / `launch-role` | none — `claim`/`ready` are ticket-scoped, Runs are session-scoped | low | isolate (read-only reference only) |
| `console/server/trackers.py` (questions/bugs/todos) | `comment` extends `VALID_KINDS` in the same module | low | modify — additive, mirrors existing kinds |
| `console/server/plugins/registry.py` (UI plugins) | Backend SPI is a parallel, distinct mechanism, not an extension of this registry | medium (naming confusion) | isolate — new module, distinct name (A4) |
| `console/server/kickoff.py` / `kanban.py cmd_ticket_create` | FR-2 removes one of the two current paths | medium (behavior change for any external script calling `ticket create` expecting bare-TOML-only, fast behavior) | modify, with a clear changelog note — see §13 ⚠ |
| `console/server/paths.py` `find_repo_root` | FR-6 adds a new first resolution step | low (additive, backward compatible per A7) | modify |
| Existing `agents.toml` gated-tools / approval-card mechanism | `claim`/`comment`'s `needs_confirm` is the stray-click guard only; human-approval gating (if wanted for `claim`) would be a separate `agents.toml` row | low | reuse existing pattern, no new gate mechanism needed unless a stakeholder asks |

## 10. External Dependencies

- PowerShell 5.1 on PATH — inherited from `kickoff.py`, now load-bearing for every ticket-creation entry point post-FR-2 (A1).
- None else — no external tracker systems, no new third-party services (explicitly excluded).

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Ticket owner | Sohail Ali | Overall scope/direction per the plan doc | yes |
| Future T-018 implementer | 〈unassigned〉 | Stable `claim`/`ready` verb contracts and `claimed_by` field to build worktree-per-Run on | no (informational — T-018 not started) |
| Editor integrators (Cursor/Claude/VS Code users) | 〈n/a — this workspace's own agents〉 | `console setup <editor>` must work for all three named editors | no |

## 12. Open Questions (mirrored)

Mirrored from `{T-017}-questions.toml`. None raised as blocking — all judgment calls were resolvable from GROUND-stage evidence and recorded as Assumptions (§3) per Auto Mode guidance. See [[T-017-decision-log]] for the reasoning behind each.

- (none open)

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements T-017`. Each must be resolved or explicitly accepted before freeze.)

- ⚠ The plan's mermaid diagram (plan lines 117-157) shows `Bus → HTTP` feeding a UI `EventSource`, implying live UI sync is part of "one API" — but the 5-item scope list (plan lines 5-19, todos frontmatter) does not name a UI EventSource/live-sync deliverable. **Resolution:** treated as illustrative architecture, not a committed FR, since the explicit scope list and "Out of scope" list are the two canonical scope statements per the task instructions, and neither names it. Excluded from FR-1..FR-11; flagged here so `challenge-requirements`/the user can override if UI live-sync was intended as in-scope. **Accepted as out-of-scope pending user confirmation** — not blocking (low-risk, additive if added later).
- ⚠ FR-8's claim-release mechanism (what clears `claimed_by`) is not pinned down by the plan. **Resolution:** default to "cleared automatically when the ticket moves to `done` via `close-work`, or explicitly by a `claim --release` variant" — documented as an implementation-planning decision, not re-opened as a blocking requirements question, since either choice is reversible and low-risk.
- ⚠ FR-4's HTTP MCP transport security model is unspecified by the plan (no auth scheme named). **Resolution:** accepted as "same trust boundary as today's unauthenticated local `serve`" (NFR §5) since the plan does not ask for new auth and this console is explicitly a local/dev tool per its own framing (plan line 28, "not a new product"). Not blocking.
- ⚠ Terminology collision between "Tracker SPI" (plan's ticket-backend abstraction) and `console/server/trackers.py` (questions/bugs/todos CRUD) risked requirements ambiguity. **Resolution:** resolved via A4 — this document uses "Backend SPI" for the new interface throughout FR-5/7/8/9's descriptions; freeze does not block on this since it's an internal naming decision, not a stakeholder-facing one.

## 14. Draft History

See [[T-017-iteration-log]] for per-iteration diff + rationale.

Current iteration: **2**

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred (one remains in §5 Security row, explicitly deferred with rationale — see NFR notes)
- [x] All ⚠ findings resolved or explicitly accepted with rationale (§13)
- [x] All blocker open questions answered (none raised — §12)
- [x] Every FR has at least one testable acceptance criterion
- [x] Every NFR has a concrete target or documented reason for absence
- [x] Every new/changed entity has a canonical reference or creation plan (§6)
- [x] Out-of-scope list is non-empty (§3)
- [x] Stakeholder sign-off recorded — ticket owner is also the requesting user for this GROUND/CLARIFY pass; explicit approval still requested in the handback (see report)
- [x] `T-017-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements-draft]] · [[T-017-context-snapshot]] · [[T-017-gap-analysis]] · [[T-017-iteration-log]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
