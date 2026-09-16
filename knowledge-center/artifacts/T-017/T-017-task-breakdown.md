---
ticket: "T-017"
artifact: task-breakdown
---

# Task breakdown: T-017

Atomic tasks per slice, with acceptance criteria and effort. Task ID format: `{phase}-{slice}-{task}`.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis step), `estimate(mode=forecast)`.

Build order rationale (from [[T-017-components]] dependency graph): Phase 1 builds every root component in parallel (no cross-component dependency within the phase); Phase 2 builds everything that depends only on Phase 1; Phase 3 (verb handlers) depends on the Backend SPI/vault adapter and data-schema work landing in Phases 1-2; Phase 4 (ops) depends on `claim` (Phase 3) and the HTTP transport (Phase 2).

---

## Phase 1: Foundations (parallel — no intra-phase dependencies)

### Slice 1a: one-api

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1a-1 | Audit `build_parser()` for JSON coverage gaps; list every subcommand's current JSON/text behavior | kanban.py --json audit | FR-1, AC1 | Audit list committed to task/implementation-plan notes, cites every leaf subcommand | 2 (1 actual) | done | Audit found the plan's named "mixed subcommands" (`verb-list`, `audit`, `context`, `telemetry`, `schedule-list`, `job-list`, `worktree-list`, `harness-lint`, `agents-*`) already had `--json` in current code; the real gap was 3 subcommands with **no** JSON path at all — see `test_cli_json.py` module docstring for the full audit |
| 1a-2 | Add/normalize `--json` across mixed subcommands (`verb-list`, `audit`, `context`, `telemetry`, `schedule-list`, `job-list`, `worktree-list`, `harness-lint`, `agents-*`) | kanban.py --json audit | FR-1, AC1 | Every named subcommand emits valid JSON on `--json`; no stray `print()` on stdout stream | 3 (1.5 actual) | done | depends on 1a-1 — deviation: those named subcommands needed no change (already correct); added `--json` to `export`, `reset`, `notify who` instead, the 3 that were actually plain-text-only |
| 1a-3 | Add test coverage per subcommand group asserting `--json` output parses as valid JSON | kanban.py --json audit | FR-1, AC1 | ≥1 test per subcommand group passes | 3 (1.5 actual) | done | depends on 1a-2 — `console/tests/test_cli_json.py`, 7 cases covering `export`/`reset`/`notify who` |
| 1a-4 | Rewire `cmd_ticket_create` to call `kickoff.py`'s `create_ticket` | Ticket-creation path collapse | FR-2, AC2 | `ticket create` and `verb run kickoff` produce identical artifacts for equivalent inputs | 3 (2 actual) | done | `kickoff.create_ticket` gained an optional `ticket_id`/`priority`/`url` so the CLI's explicit-id form and the verb's allocated-id form share one function |
| 1a-5 | Remove/deprecate bare-TOML-only path as a public action (may remain as internal helper) | Ticket-creation path collapse | FR-2, AC2 | Regression test confirms old path unreachable as a public action | 2 (0.5 actual — folded into 1a-4) | done | depends on 1a-4 — `tickets.create` remains as the internal helper `kickoff.create_ticket` itself calls; no CLI path reaches it directly any more |
| 1a-6 | Add `PowerShellUnavailable` honest-error test from every entry point (CLI/MCP/HTTP) post-collapse | Ticket-creation path collapse | FR-2, NFR-3, A1 | Clean named error, not a traceback, on all entry points | 1.5 (1 actual) | done | depends on 1a-4 — CLI: `kanban.py main()` now catches `kickoff.PowerShellUnavailable`; MCP/HTTP already had generic catch-alls (`mcp.call_tool`, `httpd._dispatch`) that pre-date this ticket and needed no change — verified by reading, not modified |
| 1a-7 | Wire the collapsed ticket-creation path into `console/server/audit.py`'s existing audit log | Ticket-creation path collapse | FR-2, NFR-5 | Ticket creation appears in the audit trail | 1 (1 actual) | done | depends on 1a-4 — `audit.record("ticket.create", ...)` called once inside `kickoff.create_ticket` itself (not duplicated per caller), new `"ticket.create"` row in `audit.ACTIONS` — closes NFR-5 gap (CR-1) |

### Slice 1b: tracker-spi (interface)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1b-1 | Design & write Backend SPI interface module (e.g. `console/server/backends/base.py`) defining `list`/`show`/`create`/`move`/`set`/`comment`/`ready`/`claim` | Backend SPI interface | FR-5, AC5, A4 | Interface defined once, documents all 8 operations | 3 (2 actual) | done | `abc.ABC` + `abstractmethod` |
| 1b-2 | Document interface contract + naming rationale (distinct from `trackers.py`, per a4) in module docstring | Backend SPI interface | FR-5, A4 | Docstring cites a4; no ambiguity with `console/server/trackers.py` | 1 (0 actual — folded into 1b-1) | done | depends on 1b-1 |
| 1b-3 | Wire interface import stubs into `verb_handlers.py` call sites that will use it (`ready`/`claim`/`comment`/`ticket-move`) | Backend SPI interface | FR-5, AC5 | Stub wiring compiles; no behavior change yet (adapter lands Phase 2) | 2 (0.5 actual) | done | depends on 1b-1 — import added, `ticket_move`/etc. still call `tickets_mod`/`trackers_mod` directly until 2b-4 |
| 1b-4 | Interface contract test: cannot be instantiated without implementing all 8 methods | Backend SPI interface | FR-5, AC5 | Test fails on an incomplete stub implementation | 2 (1.5 actual) | done | depends on 1b-1 — `console/tests/test_backends.py` |

### Slice 1c: workspace-contract (schema)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1c-1 | Define `workspace.toml` schema (`name`/`vault`/`console`/`projects`) + parser | workspace.toml schema | FR-6, AC6, A7 | Parser reads a valid `workspace.toml` fixture correctly | 2 (2 actual) | done | new `console/server/workspace_config.py` |
| 1c-2 | Validation: missing/invalid `vault`/`console` paths raise a clear named error, not `FileNotFoundError` deep in an unrelated module | workspace.toml schema | FR-6, Edge Case §8 | Error names the missing path | 1.5 (1 actual) | done | depends on 1c-1 — `WorkspaceConfigError` |
| 1c-3 | Unit test: parser round-trips valid + invalid fixtures | workspace.toml schema | FR-6 | Both fixture cases pass | 1.5 (2 actual) | done | depends on 1c-1 — `console/tests/test_workspace_config.py`, 10 cases |

### Slice 1d: ready-claim-hooks (data schema)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1d-1 | Add `claimed_by`/`claimed_at` fields + `tickets.py` mutator (`set_claim`), distinct from `owner` | ticket.toml schema extension | FR-8, A3 | Mutator sets/reads fields; `owner` untouched | 2 (1.5 actual) | done | |
| 1d-2 | Unit test: claim-field mutator correctness | ticket.toml schema extension | FR-8, A3 | Fields set/read correctly, isolated from `owner` | 1 (0.5 actual) | done | depends on 1d-1 |
| 1d-3 | Update `ticket.toml` template/docs for new fields | ticket.toml schema extension | FR-8 | Template scaffolds fields; docs mention them | 1 (0.5 actual) | done | depends on 1d-1 — no `_template/ticket.toml` file exists (ticket.toml is CLI-scaffolded via `tickets.create`, not template-rendered); updated `console/README.md` data-model + CLI sections instead |
| 1d-4 | Add `comments` to `trackers.py` `VALID_KINDS` + `_DEFAULT_STATUS`/`_IS_BLOCKER` entries | `comments` tracker kind | FR-9, A2 | `comments` behaves like `todos` for blocking (never blocks) | 2 (1.5 actual) | done | |
| 1d-5 | Scaffold `{T}-comments.toml` creation in the `kickoff` path | `comments` tracker kind | FR-9, A2, Edge Case §8 | New ticket scaffolds an empty `{T}-comments.toml`, mirroring questions/bugs/todos | 1 (0 actual — folded into 1d-4) | done | depends on 1d-4 — `tickets.ensure_all()` already loops `VALID_KINDS`, so adding `comments` there was sufficient; no separate scaffolding code needed |
| 1d-6 | Unit test: comments CRUD (`add`/`list`/`update`) + `_IS_BLOCKER` returns `False` | `comments` tracker kind | FR-9, A2 | Test passes | 1 (1 actual) | done | depends on 1d-4 |

### Slice 1e: mcp-first-class (resources)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1e-1 | Extend `initialize` response to declare `resources` capability (additive; tools-only clients unaffected) | MCP resources capability | FR-3, AC3 | `initialize` gains `resources`; existing tools-only behavior unchanged | 1 (0.5 actual) | done | `{"subscribe": true, "listChanged": false}` |
| 1e-2 | Implement `resources/list` (ticket-context resource enumeration) | MCP resources capability | FR-3, AC3 | Returns ≥ ticket-context resources | 3 (1.5 actual) | done | depends on 1e-1 — one `ticket://{ID}` resource per ticket |
| 1e-3 | Implement `resources/read` (delegates to `verb_handlers.ticket_context`) | MCP resources capability | FR-3, AC3 | Returns the same data the `context` verb produces | 2 (1 actual) | done | depends on 1e-2 — delegates to `context.build`/`format_markdown`, same content as the `context` tool, verified byte-for-byte in tests |
| 1e-4 | Design + implement a minimal change-notification bus scoped to MCP resource subscribers only (not the UI board — a8) | MCP resources capability | FR-3, A5, a8 | Bus delivers a mutation event to a subscribed session; explicitly does not touch UI EventSource/WebSocket (out of scope, a8) | 4 (3 actual) | done | greenfield — new `console/server/bus.py`; pull-not-push design (subscribe/publish/drain), process-local singleton; came in under estimate — the uncertainty was more in "what shape" than "how much code" |
| 1e-5 | Implement `resources/subscribe` + `notifications/resources/updated` | MCP resources capability | FR-3, AC3 | Subscribed session receives the notification | 3 (2 actual) | done | depends on 1e-4 — also added symmetric `resources/unsubscribe` (small addition, standard MCP shape); notifications flush at the end of every `handle()` turn |
| 1e-6 | Test: a verb mutation triggers a change notification to a subscribed session | MCP resources capability | FR-3, AC3 | Test passes | 4 (2 actual) | done | depends on 1e-5 — wired into the existing `ticket_move` verb handler (the only pre-existing mutating verb in this phase; `ready`/`claim`/`comment` publish the same way once they land in Phase 3); `console/tests/test_mcp.py::TestResourcesSubscribeAndNotify`, 5 cases |

---

## Phase 2: Adapters & transport (depends on Phase 1)

### Slice 2a: mcp-first-class (HTTP transport)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2a-1 | Add MCP Streamable HTTP endpoint (POST for request/response) mounted on the existing `serve` process | MCP Streamable HTTP transport | FR-4, AC4, A5 | Endpoint answers MCP calls on the same running process/port | 4 (2.5 actual) | done | new `console/server/features/mcp_http_feature.py`, registered in `console/config/plugins.toml`; `POST /api/mcp` |
| 2a-2 | Add GET+SSE endpoint for server-initiated messages | MCP Streamable HTTP transport | FR-4, AC4 | SSE stream delivers server-initiated messages | 3 (1.5 actual) | done | depends on 2a-1 — `GET /api/mcp/sse`, reuses `httpd.EventSource` |
| 2a-3 | Share `verbs_mod`/`context_mod` logic between stdio and HTTP paths (no duplicated handler logic) | MCP Streamable HTTP transport | FR-4, AC4 | One shared call path for both transports | 3 (1 actual) | done | depends on 2a-1 — the HTTP handler builds one `mcp.Server` per session and calls its exact `handle()` (stdio's own method) against an in-memory `io.StringIO`; no second `initialize`/`tools/call`/`resources/*` implementation. Found and fixed a real bug in the process: `mcp.Server.__init__` always set `session_id = id(self)`, so the HTTP transport's own session id and the bus's subscription key were two different values until `Server` gained an optional `session_id=` param — see progress.md |
| 2a-4 | Test: identical `tools/list`/`tools/call` results over HTTP vs. stdio for an equivalent request | MCP Streamable HTTP transport | FR-4, AC4 | Test passes | 3 (1 actual) | done | depends on 2a-3 — `console/tests/test_mcp_http.py::TestPostRequestResponse` |
| 2a-5 | Test: multiple concurrent HTTP clients isolated (killing one connection doesn't affect others) | MCP Streamable HTTP transport | FR-4, AC4 | Test passes | 3 (1 actual) | done | depends on 2a-2 — `TestConcurrentSessionsIsolated`: two sessions subscribed to different tickets, only the mutated one's subscriber sees a notification; closing one session's SSE stream doesn't disturb the other's registry entry or queue |

### Slice 2b: tracker-spi (vault adapter)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2b-1 | Implement `VaultBackend` satisfying the Backend SPI interface, delegating `list`/`show`/`create`/`move`/`set` to `tickets.py`/`trackers.py` | Vault adapter | FR-5, AC5 | Delegation only, no logic duplication | 4 (1.5 actual) | done | new `console/server/backends/vault_backend.py` |
| 2b-2 | Implement `comment`/`ready`/`claim` methods on `VaultBackend` (thin delegation) | Vault adapter | FR-5, AC5 | Same as above for the 3 new operations | 3 (1.5 actual) | done | depends on 2b-1, 1d-1, 1d-4 — `ready`'s unblocked+unclaimed filter and `claim`'s field-set are real (if simple) logic written now since Phase 3's verb handlers have nothing to call otherwise; `claim`'s race-safety guard is still Phase 3's 3a-5, deliberately last-write-wins here |
| 2b-3 | Register `VaultBackend` as the sole startup registration | Vault adapter | FR-5, BR-4 | Exactly one adapter registered at startup | 1 (0.5 actual) | done | depends on 2b-1 — module-level singleton `backends.default_backend()`, mirrors `bus.default()`'s shape |
| 2b-4 | Wire the existing `ticket-move` handler through the Backend SPI instead of direct calls | Vault adapter | FR-5, AC5 | `ticket-move` uses the interface, not direct vault calls | 3 (0.5 actual) | done | depends on 2b-1 — `verb_handlers.ticket_move` now calls `backends_mod.default_backend().move(...)` |
| 2b-5 | Test: `VaultBackend` round-trips against real vault fixtures for all 8 methods | Vault adapter | FR-5, AC5 | All 8 methods pass fixture round-trip | 4 (1.5 actual) | done | depends on 2b-2, 2b-4 — `console/tests/test_vault_backend.py`, 13 cases against the `repo` fixture |
| 2b-6 | Verify zero Jira/Azure/Linear/GitHub Issues code exists in the diff (grep-based check, documented as a test or CI note) | Vault adapter | FR-5, AC5, Out-of-Scope | Check passes / documented in PR notes | 1 (0.5 actual) | done | `test_vault_backend.py::TestNoOtherAdapterExists` — checks for a forbidden adapter *class*, not the docstrings' own mentions of them as future-only possibilities |
| 2b-7 | Design note: a future non-vault adapter would sync identity/status/comments, not replace the vault lane (plan line 176) | Vault adapter | FR-5, AC5 | Note added to Backend SPI module docs | 1 (0.5 actual) | done | in `vault_backend.py`'s module docstring |

### Slice 2c: workspace-contract (resolution)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2c-1 | Add `workspace.toml` upward-search branch to `find_repo_root`, resolving `vault`/`console` roots when found | `find_repo_root` workspace.toml resolution | FR-6, AC6, A7 | `find_repo_root` returns resolved roots from a valid `workspace.toml` | 3 (1 actual, +~2 actual in the fixer pass below) | done | **Fixer pass (a9) closed the renamed-pair gap this row originally flagged**: `find_repo_root` now returns a stable anchor for an unreducible (renamed) pair instead of raising; new `paths.vault_dir`/`console_dir`/`resolve_rel` re-resolve the real directories from it, and all ~25 real call sites across the package that used to join `repo_root + "console/..."`/`"knowledge-center/..."` literally were migrated to go through them. See decision-log a9 for the full file list and rationale. |
| 2c-2 | Fallback path: unchanged sibling-folder check when `workspace.toml` absent | `find_repo_root` workspace.toml resolution | FR-6, A7 | No `workspace.toml` → identical behavior to today | 1 (0.5 actual) | done | `workspace_config.resolve()` returns `None` (never raises) when absent, so the pre-existing sibling walk is untouched code, reached unconditionally |
| 2c-3 | Regression test: existing single-repo checkouts unaffected | `find_repo_root` workspace.toml resolution | FR-6, AC6 | All existing `find_repo_root` tests pass unchanged | 2 (0.5 actual) | done | `console/tests/test_paths.py::TestSiblingFallbackUnchanged` (3 cases, incl. a live check against this repo's own real checkout, which has no `workspace.toml`); full suite still 1270 passed before this slice's new tests were added |
| 2c-4 | New fixture test: split-repo layout bound by `workspace.toml` resolves correctly | `find_repo_root` workspace.toml resolution | FR-6, AC6 | Fixture test passes | 2 (1 actual) | done | `console/tests/test_paths.py::TestWorkspaceTomlFirstBranch` (3 cases: resolves a valid split layout found above where the walk starts, raises named error on an unreducible layout, raises `WorkspaceConfigError` on a broken path) |

---

## Phase 3: Verbs (depends on Phase 1 + Phase 2)

### Slice 3a: ready-claim-hooks (verb handlers)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3a-1 | Implement `ready` verb handler using Backend SPI + existing `_IS_BLOCKER`, filtering claimed tickets | `ready` verb handler | FR-7, AC7, A6 | Excludes blocked and claimed tickets | 2 (0.5 actual) | done | `verb_handlers.ticket_ready` calls `backends.default_backend().ready(...)` (2b-2's real logic) |
| 3a-2 | Register `ready` in `verbs.toml` (CLI/MCP/HTTP identical) | `ready` verb handler | FR-7, AC7 | Available identically across all three surfaces | 1 (0.25 actual) | done | one `[[verb]]` row — CLI (`verb run`), MCP (`tools/call`/`tools/list`), and HTTP (`/api/verbs/{id}/run`) all dispatch through `verbs.run`'s shared registry already, confirmed by reading `mcp.call_tool`/`verbs_feature.py`/`kanban.cmd_verb_run` — no per-surface code needed (one-api, Phase 1's 1a/1b) |
| 3a-3 | Test: `ready` excludes blocked+claimed; empty list (not error) when none available | `ready` verb handler | FR-7, AC7, Edge Case §8 | Test passes | 1 (0.5 actual) | done | `console/tests/test_ready_claim_comment_verbs.py::TestReady` |
| 3a-4 | Implement `claim` verb: set `claimed_by`/`claimed_at` via Backend SPI, `confirm=true` | `claim` verb handler | FR-8, AC8, A3 | Fields set correctly on success | 2 (0.5 actual) | done | `verb_handlers.ticket_claim`; generic `--set agent=<id>` (existing CLI/MCP/HTTP arg-passing) stands in for a dedicated `--agent` flag — no new per-surface plumbing needed |
| 3a-5 | Race-safety: atomic write/replace guard, refuse a conflicting claim with a named "already claimed by X" error | `claim` verb handler | FR-8, AC8, Edge Case §8 | Concurrent-claim scenario never corrupts `ticket.toml` | 3 (2 actual) | done | New `tomlio.atomic_update(path, mutate)` — a read-modify-write under the *same* lock file `atomic_write` already uses (reused, not reinvented, per this task's own instruction and Phase 2's note about `test_tomlio.py`'s concurrent-writer test). `tickets.set_claim` now runs its whole read-check-write inside one `atomic_update` call instead of a plain `load()`+`_save()` pair, and raises the new `tickets.ClaimConflictError` on a conflicting claim. Found and fixed a real pre-existing Windows lock-acquire bug in the process: `os.open(..., O_CREAT\|O_EXCL)` on a lock file another thread is mid delete-and-recreate on can raise `PermissionError` instead of `FileExistsError` on NTFS — `_acquire_lock` only retried on the latter, so 8-way contention (this task's own test) intermittently crashed a claim instead of just queuing it. Now retries on both. |
| 3a-6 | Idempotent re-claim by the same identity (documented behavior: no-op or refresh `claimed_at` — pick one) | `claim` verb handler | FR-8, AC8 | Re-claim by same identity does not error | 1 (0.25 actual) | done | Chose refresh — same identity re-claiming updates `claimed_at`, folded into 3a-5's `set_claim` mutate function (no separate code path) |
| 3a-7 | Wire `claim` mutation into `audit.py`'s existing audit log | `claim` verb handler | FR-8, AC8, NFR-5 | Claim appears in audit trail | 1 (0.25 actual) | done | `audit.record(repo_root, "ticket.claim", ...)` on both success and refusal (a refused claim is exactly the kind of thing worth a line, matching `verb.run`'s own refused-run pattern) |
| 3a-8 | Test: two concurrent `claim` calls by different identities — exactly one succeeds | `claim` verb handler | FR-8, AC8 | Test passes deterministically | 2 (0.75 actual) | done | Tested at two layers: `test_tickets.py::TestClaim::test_concurrent_claims_by_different_identities_exactly_one_succeeds` (8 threads, `tickets.set_claim` directly) and `test_ready_claim_comment_verbs.py::TestClaim::test_concurrent_claims_by_different_agents_exactly_one_succeeds` (6 threads, through the verb). Both green across repeated runs after the 3a-5 Windows lock fix. |
| 3a-9 | Implement `comment` verb: append to `comments` tracker kind via Backend SPI, `confirm=true` | `comment` verb handler | FR-9, AC9, A2 | Comment appended, attributed + timestamped | 2 (0.5 actual) | done | `verb_handlers.ticket_comment` calls `backends.default_backend().comment(...)` → `trackers.add(..., "comments", ...)`, which already stamps `author`/`posted_on` (1d-4) |
| 3a-10 | Test: comment attribution/timestamp; readable via `tracker list <id> comments` | `comment` verb handler | FR-9, AC9 | Test passes | 1 (0.5 actual) | done | `console/tests/test_ready_claim_comment_verbs.py::TestComment` |
| 3a-11 | Register `comment` in `verbs.toml` (CLI/MCP/HTTP identical) | `comment` verb handler | FR-9, AC9 | Available identically across all three surfaces | 1 (0.25 actual) | done | Same one-api reasoning as 3a-2 |
| 3a-12 | Wire `comment` mutation into `audit.py`'s existing audit log | `comment` verb handler | FR-9, NFR-5 | Comment appears in audit trail | 1 (0.25 actual) | done | `audit.record(repo_root, "ticket.comment", ...)` — closes NFR-5 gap (CR-1) |

---

## Phase 4: Ops (depends on Phase 2 + Phase 3)

### Slice 4a: ready-claim-hooks (stop-hook + editor setup)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4a-1 | Implement session stop-hook: check claimed tickets for the exiting identity with no update since claim | Session stop-hook | FR-10, AC10 | Detects stale claims correctly | 2 (0.75 actual) | done | new `server/stop_hook.py`: `stale_claims`/`_has_update_since_claim` — reuses `log-work`'s existing `author.local` slug as the identity source (no second identity convention invented); "no update" = ticket `updated` and every `comments` item's `posted_on` still ≤ `claimed_at` |
| 4a-2 | Emit reminder (console-side flag/log line); hook never crashes session end (mirrors `cmd_refresh`'s guard) | Session stop-hook | FR-10, AC10 | Hook failure never crashes session end | 1 (0.5 actual) | done | `kanban.py stop-hook check` (new subcommand) catches any exception and reports it (JSON) or swallows it (plain), same contract as `cmd_refresh`; `.claude/hooks/console-stop-reminder.sh` wraps the call in `\|\| true` and registers in `.claude/settings.json`'s Stop hooks list alongside `console-refresh.sh` |
| 4a-3 | Test: claim→no update→reminder recorded; claim→update→no reminder; hook never crashes | Session stop-hook | FR-10, AC10 | All three scenarios pass | 1 (0.5 actual) | done | `console/tests/test_stop_hook.py` (16 cases: identity resolution, stale/not-stale via comment or move, cross-agent isolation, CLI `--json`/plain modes, never-crashes-on-exception, parser wiring) |
| 4a-4 | Implement `console setup cursor` — write `.cursor/mcp.json` + `AGENTS.md` snippet | `console setup <editor>` command | FR-11, AC11 | Config + snippet written at documented location | 2 (0.75 actual) | done | new `server/setup_editor.py`: `setup_editor(repo_root, "cursor")` writes `.cursor/mcp.json`'s `mcpServers.console` (same shape as this repo's own root `.mcp.json`) |
| 4a-5 | Implement `console setup claude` — write Claude Code's documented MCP config location | `console setup <editor>` command | FR-11, AC11 | Config written at documented location | 1.5 (0.25 actual) | done | Claude Code's project MCP config is the repo-root `.mcp.json` that already exists — `setup_editor(..., "claude")` merges into it rather than writing a second file |
| 4a-6 | Implement `console setup vscode` — write VS Code's documented MCP settings location | `console setup <editor>` command | FR-11, AC11 | Config written at documented location | 1.5 (0.25 actual) | done | `.vscode/mcp.json`'s `servers.console`, with the extra `"type": "stdio"` field VS Code's schema names |
| 4a-7 | Idempotency + merge-not-overwrite handling for pre-existing editor configs | `console setup <editor>` command | FR-11, AC11, Edge Case §8 | Re-run is a no-op; existing unrelated entries preserved | 1.5 (0.5 actual) | done | `_merge_mcp_json` sets only the `"console"` key under each format's servers dict — a pre-existing sibling server or unrelated top-level key survives untouched; `_write_agents_snippet` replaces content between two HTML-comment markers in place rather than appending again |
| 4a-8 | Test: idempotent re-run for all 3 editors; `AGENTS.md` snippet warns against hand-editing ticket/tracker TOML | `console setup <editor>` command | FR-11, AC11 | Test passes | 1.5 (0.5 actual) | done | `console/tests/test_setup_editor.py` (13 cases: per-editor config shape, second-run no-op, unrelated-server preservation, AGENTS.md create/append/no-duplicate-on-rerun, unknown-editor rejection, CLI `--json`/plain, parser wiring incl. `choices` rejection) |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 — Foundations | 55.5 | 32 | 0 | 23.5 | 100% tasks done (32h actual vs 55.5h estimated) |
| Phase 2 — Adapters & transport | 41 | 16.5 | 0 | 24.5 | 100% tasks done (16.5h actual vs 41h estimated) |
| Phase 3 — Verbs | 18 | 6.5 | 0 | 11.5 | 100% tasks done (6.5h actual vs 18h estimated) |
| Phase 4 — Ops | 12 | 4 | 0 | 8 | 100% tasks done (4h actual vs 12h estimated) |
| **Total** | **126.5** | **55** | **0** | **71.5** | **73.7% of tasks done, 43.5% of effort spent** |

Phase 1 actuals by slice: 1a 8.5h, 1b 4h, 1c 5h, 1d 6h, 1e 8.5h = 32h actual vs 55.5h estimated (42% under — several tasks folded together or were smaller than sized once the real code was read; see per-task Notes above for each deviation).

Phase 2 actuals by slice: 2c 3h, 2b 6.5h, 2a 7h = 16.5h actual vs 41h estimated (60% under — see progress.md for the 2c scope note and the 2a session-id bug found+fixed along the way).

Phase 3 actuals: 6.5h actual vs 18h estimated (64% under — the schema/interface work Phases 1-2 already did for `claimed_by`/`claimed_at`, the `comments` kind, and the `ready`/`claim` Backend SPI methods left this phase mostly wiring: one `atomic_update` primitive for 3a-5's race-safety, three verb handlers, three `verbs.toml` rows, two `audit.ACTIONS` entries. One real bug found and fixed in 3a-5's own concurrency test: a Windows-specific lock-acquire race (see task-breakdown Notes and progress.md).

**Reconciliation vs. [[T-017-effort-estimate]]:** task-level sum (126.5h dev) is ~9.6% under the upfront components-basis "most likely" Dev total (140h) and well within the upfront range [98h-176h]. No `replan` trigger (the reconciliation rule only fires >10% **over** the upper bound, 176h) — task-level granularity is naturally tighter than T-shirt sizing; no drift concern, noted for the record. (Revised from an initial 124.5h after `challenge-plan` CR-1 added tasks 1a-7 and 3a-12 to close an NFR-5 audit-coverage gap — see [[T-017-critique-report]].)

---

## Conventions

**Status:** pending · in-progress · done · blocked (see Notes for why).
**Effort:** 0.5 / 1 / 1.5 / 2 / 3h buckets — no micro- or mega-tasks (a few 4h tasks retained where a component's atomic unit of work — e.g. concurrent-claim testing, the MCP change-bus — doesn't split further without becoming artificial; flagged, not hidden).
**Dependencies:** noted in Notes column.

## Links
- [[T-017-summary]] · [[T-017-plan]] · [[T-017-components]] · [[T-017-task-breakdown]] · [[T-017-implementation-plan]] · [[T-017-effort-estimate]] · [[T-017-effort-forecast]]
