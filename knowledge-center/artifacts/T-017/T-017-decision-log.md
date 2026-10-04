---
ticket: "T-017"
artifact: decision-log
---

# Decisions: T-017

## a1-collapse-kickoff-onto-powershell-path
**Decision:** Collapse `kanban.py cmd_ticket_create` into `server/kickoff.py`'s `create_ticket` (FR-2), accepting that this makes the existing PowerShell dependency (`kickoff.py:64-80`, `PowerShellUnavailable`) load-bearing for every ticket-creation entry point, not just the `kickoff` verb.
**Rationale:** The alternative — keeping two paths, or reimplementing template rendering without PowerShell — is out of scope for this ticket (no cross-platform template-render rewrite was asked for) and the "fuller" path is already the one skills/agents are told to use per `CLAUDE.md`. The constraint is pre-existing, not introduced by T-017.
**Impact:** Documented as NFR (§5) and edge case (§8) in requirements. A non-Windows checkout without PowerShell already cannot use `kickoff` today; this decision doesn't make things worse, just more visible.

## a2-comment-as-fourth-tracker-kind
**Decision:** Store `comment` verb output as a new `comments` kind in `console/server/trackers.py`'s `VALID_KINDS` (currently `questions`, `bugs`, `todos`), reusing the existing `add`/`list`/`update` CRUD shape, never blocking release (mirrors `todos`' `_IS_BLOCKER` returning `False`).
**Rationale:** `trackers.py`'s own header (lines 7-9) reserves `gaps`/`critique` as future kinds but doesn't forbid adding others; reusing the proven CRUD/TOML shape is the smallest correct extension rather than inventing a new file format for comments.
**Impact:** `trackers.py` gains one line (`VALID_KINDS` tuple) plus `_DEFAULT_STATUS`/`_IS_BLOCKER` entries for `comments`; `{T}-comments.toml` scaffolding follows the same pattern `kickoff` already uses for questions/bugs/todos.

## a3-claim-fields-distinct-from-owner
**Decision:** Add `claimed_by` and `claimed_at` as new `ticket.toml` fields, kept distinct from the existing `owner` field (human, set at ticket creation).
**Rationale:** `owner` and "who currently has this claimed" are different concerns — an owner doesn't change when an agent picks up a claimed ticket, and a claim needs a timestamp for the stop-hook (FR-10) and for T-018's future worktree/branch linkage to reference.
**Impact:** `ticket.toml` schema gains two fields; `tickets.set_field` (or a dedicated `claim`/`release` path) is the only mutator, per BR-2.

## a4-backend-spi-not-plugins-toml
**Decision:** Name the new ticket-backend abstraction "Backend SPI" in requirements/design language, distinct from both `plugins.toml`'s UI-feature plugin loader and `console/server/trackers.py`'s questions/bugs/todos CRUD. Implement it as its own small interface module, not an extension of `plugins/registry.py`.
**Rationale:** GROUND-stage reading of `plugins/registry.py` (UI/HTTP feature modules with `apply(ctx)`) and `trackers.py` (questions/bugs/todos CRUD) confirmed neither is the plan's intended "Tracker SPI" (ticket-storage backend abstraction: vault vs. a hypothetical Jira/Azure adapter). Reusing either existing name/mechanism would either wire the SPI into the wrong system or create a naming collision an implementer could trip on.
**Impact:** New module (e.g. `console/server/backends/base.py` mirroring `plugins/base.py`'s shape) with exactly one registered adapter (vault). No change to `plugins.toml` or `trackers.py`'s own CRUD role.

## a5-mcp-http-no-protocol-bump
**Decision:** Target the MCP Streamable HTTP transport under the protocol version already declared in `console/server/mcp.py:42` (`2025-06-18`).
**Rationale:** That version already defines the Streamable HTTP transport; no version negotiation change is needed, only additive capability declarations and new method handling.
**Impact:** `initialize`'s `capabilities` gains `resources` (FR-3); a new HTTP-serving code path is added alongside stdio, sharing `verbs_mod`/`context_mod` logic already used by `Server`.

## a6-ready-reuses-existing-blocker-logic
**Decision:** `ready` (FR-7) reuses `console/server/trackers.py`'s existing `_IS_BLOCKER` predicate and `verb_handlers.ticket_blockers` rather than introducing new blocking-logic rules.
**Rationale:** A second, parallel definition of "blocked" would drift from the one `blockers` verb already exposes; one predicate, two callers, is the CANONICAL-consistent choice.
**Impact:** `ready`'s filter is: not blocked (existing predicate) AND `claimed_by` empty.

## a7-workspace-toml-optional-backward-compatible
**Decision:** `workspace.toml` resolution in `find_repo_root` (FR-6) is tried first but is fully optional; its absence must reproduce today's `_is_repo_root` sibling-folder behavior exactly.
**Rationale:** `CLAUDE.md`'s own documented layout is the sibling-folder shape; breaking that default for every existing checkout to support a new, opt-in split-repo layout would violate SIMPLIFY (no unnecessary behavior change) and CANONICAL (one documented layout becoming two undocumented ones).
**Impact:** `find_repo_root` gains a new first branch (workspace.toml search) with a fallback to the existing implementation, unit-testable independently.

## a8-ui-eventsource-confirmed-out-of-scope
**Decision:** UI live sync (EventSource/WebSocket push to the console board UI) is confirmed **out of scope** for T-017. The plan's mermaid diagram shows a `Bus → HTTP` edge implying UI push, but the plan's literal 5-item scope list (one-api, mcp-first-class, tracker-spi, workspace-contract, ready-claim-hooks) never names it. FR-3/FR-4 ship MCP resource-change notifications and MCP-over-HTTP for editor clients only; the console board UI's own live-refresh mechanism is unchanged by this ticket.
**Rationale:** Flagged as a `⚠` in `challenge-requirements` (draft §13) since the diagram and scope list disagreed; escalated to the user rather than assumed. User confirmed out-of-scope, matching the literal scope list over the diagram's broader illustration.
**Impact:** No change bus → UI SSE/WebSocket work in T-017's plan or acceptance criteria. A future ticket can pick up UI EventSource push once wanted; T-017's `Bus` (if any change-notification plumbing is introduced for FR-3) only needs to reach MCP resource subscribers, not the board UI.

## a9-workspace-toml-renamed-pair-resolves-end-to-end
**Decision:** Close the narrowing a7 accepted for the 2c slice: a `workspace.toml` naming a genuinely renamed/relocated vault or console directory (the plan's own illustrative `vault = "../noble-knowledge"`) now resolves end-to-end, instead of `find_repo_root` raising `RepoRootError` for any pair that doesn't reduce to a literal `knowledge-center`/`console` shared-parent shape.
**Rationale:** AC-6 (verification) found the a7 narrowing to be a real gap, not an acceptable deferral — a `workspace.toml` that can *only* rename the pair when the rename doesn't actually rename anything defeats the feature's own stated purpose. Fixing it does not touch FR-6's AC ("passes existing tests with no `workspace.toml`, and a new split-repo fixture test with one present") or widen scope: it is the same FR-6, resolved completely rather than partially.
**Impact:** `paths.find_repo_root` no longer raises for an unreducible pair — it returns the `workspace.toml`'s own directory as a stable anchor instead. Two new resolvers, `paths.vault_dir(repo_root)`/`paths.console_dir(repo_root)`, re-resolve the real (possibly renamed) directories from that anchor via `workspace_config.resolve`, falling back to the literal `repo_root/knowledge-center` and `repo_root/console` when no `workspace.toml` governs `repo_root` (a true no-op for every pre-T-017 checkout). A third helper, `paths.resolve_rel(repo_root, rel)`, lets every call site that used to join a `"console/..."`/`"knowledge-center/..."`-shaped relative path directly onto `repo_root` do so through the renamed-aware resolvers with a one-line change. All ~25 real call sites across the package (agents.py, agent_manager.py, agent_backends.py, assistant.py, assistant_config.py, audit.py, boards.py, jobs.py, kickoff.py, model_catalog.py, multimodal.py, native_bridge.py, notify.py, onboarding.py, plugins/registry.py, prompt_build.py, provider_overrides.py, reset.py, runs.py, schedules.py, stop_hook.py, telemetry.py, tickets.py, verbs.py, vault.py, worklog.py) were migrated; `.claude/skills`/`.claude/agents`/`CLAUDE.md` paths (harness_lint.py, kickoff.py's `RENDER_SCRIPT_REL`, agents.py's `.claude` globs) were left untouched — they are the harness's own source-config location, not a vault/console data path a `workspace.toml` renames. `test_paths.py`'s `test_a_layout_workspace_toml_cannot_reduce_to_one_root_raises` (which pinned the exact narrowing being removed) was replaced with `test_a_renamed_layout_resolves_via_the_workspace_toml_anchor`; every other pre-existing test is unchanged and passing (1357 -> 1365 total, all green; 8 new tests added).

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
