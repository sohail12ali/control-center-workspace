---
ticket: "T-017"
artifact: context-snapshot
status: draft
created: "2026-09-16"
last_updated: "2026-09-16"
scope: codebase + history
---

# Context Snapshot: T-017

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-017 all`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

One uniform API surface (CLI/MCP/HTTP) for the Delivery Console, MCP resources + streamable HTTP, a shape-only tracker backend SPI (vault-only adapter), `workspace.toml` to decouple console from sibling-folder layout, and `ready`/`claim`/`comment` verbs with agent identity, a stop-hook, and `console setup <editor>`.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Verb registry (deterministic, config-driven) | `console/config/verbs.toml` + `console/server/verbs.py` + `console/server/verb_handlers.py` | CLI (`kanban.py verb run`), MCP (`mcp.py` derives tools from the registry), HTTP (`features/verbs_feature.py`) | `ready`/`claim`/`comment` should be added as new `[[verb]]` rows + handlers — this is exactly the "one API, many adapters" pattern the plan wants, already proven for `ticket-move`/`tracker-add`/`kickoff` | `console/config/verbs.toml:1-237`, `console/server/mcp.py:92-103` (schema derivation) |
| Plugin loader (feature modules, topological `requires`) | `console/config/plugins.toml` + `console/server/plugins/registry.py` + `console/server/plugins/base.py` | HTTP routes / UI tabs | Pattern to *mirror* (not reuse directly — see Analysis F3) for the tracker backend SPI: an interface class + one row per adapter | `console/server/plugins/registry.py:1-107` |
| Ticket CRUD | `console/server/tickets.py` (`create`, `move`, `set_field`) | CLI, verbs, HTTP | `claim` can extend `set_field`-style mutation but needs a distinct field, not reuse of `owner` | `console/server/tickets.py:38,157,177` |
| Tracker (sub-ticket) CRUD | `console/server/trackers.py` (`VALID_KINDS = questions/bugs/todos`) | CLI, verbs, HTTP | `comment` needs either a 4th kind here or a separate mechanism — no reuse without a schema change | `console/server/trackers.py:19` |
| Repo-root resolution | `console/server/paths.py` (`find_repo_root`, `_is_repo_root`) | Every module that needs `repo_root` | Must gain a `workspace.toml`-first lookup, falling back to today's sibling check for backward compatibility | `console/server/paths.py:15-43` |
| MCP tool surface (schema-from-signature) | `console/server/mcp.py` | stdio only | Extend `capabilities`, add `resources/list`/`resources/read`, keep the "derive from registry" principle for any resource list too | `console/server/mcp.py:54-103,162-170` |
| Ticket-creation (fuller path, PowerShell-backed) | `console/server/kickoff.py` (`create_ticket`, `_render_templates`) | CLI (`kickoff` verb), used by `kickoff` skill | Target of the one-api collapse; carries a PowerShell dependency (`_powershell_exe`, `PowerShellUnavailable`) that becomes universal once `cmd_ticket_create` is retired | `console/server/kickoff.py:42-80` |
| Run object (T-016, read-only context) | `console/server/runs.py` | Assistant, board | Not modified by T-017; `claim`/`ready` verbs are ticket-level, independent of Runs | `console/server/runs.py:1-60` |

### Existing patterns to reuse
- Config-driven verb rows resolved to handler functions at registry load (fail fast on typo) — `console/config/verbs.toml:9-13`.
- `needs_confirm` as the stray-click/hallucination guard, separate from the human-approval gate in `agents.toml` — `console/config/verbs.toml:25-30,148-157`.
- MCP tool schema derived from a handler's own Python signature rather than hand-maintained — `console/server/mcp.py:54-89`.
- Two independent enable switches (committed `plugins.toml` vs. per-user Settings toggle) kept deliberately separate — `console/server/plugins/registry.py:1-13`.

### Naming and architectural conventions in play
- "Tracker" is already a taken name in this codebase for the questions/bugs/todos sub-log per ticket (`console/server/trackers.py`). The plan's "Tracker SPI" means the ticket-backend abstraction (vault vs. a future Jira/Azure adapter) — a naming collision that requirements must resolve with distinct terminology (e.g. call the new interface a "Backend"/"Ticket Store" SPI in code, even if the ticket title keeps "tracker-spi" as the plan's shorthand).
- CANONICAL rule (`CLAUDE.md`): one fact, one file; ticket/tracker TOML is CLI-mutated only, never hand-edited.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-016 | Added the unified Run object (chat/job/cursor tagged union) and `launch-role`/`run-list`/`run-show` verbs | Verify stage (open) | T-017 must not modify `runs.py`; `ready`/`claim` are ticket-scoped, not Run-scoped |
| T-018 (proposed, depends on T-017) | Worktree-per-Run, branch/PR linkage, lane hints from git | Not started | Confirms `ready-claim-hooks` in T-017 must produce a stable verb/field contract (e.g. `claimed_by`) that T-018 can build on without another schema change |

### Relevant commits / PRs
- No commit history search was needed beyond the plan doc itself; the plan doc (dated 2026, present in `.cursor/plans/`) is the freshest and most authoritative source for this split, superseding any older single-ticket framing.

### Known incidents / regressions in this area
- None found specific to MCP/CLI/tracker-SPI in `knowledge-center/logs/` during this pass (not exhaustively searched beyond the required grounding files; see Open Confirmations).

## 4. External Systems in the Loop

- None for T-017 itself — explicitly no real Jira/Azure/Linear/GitHub Issues integration (plan lines 49, 88, 111, 175, 229). Editors (Cursor, Claude Code, VS Code) are MCP *clients*, not external systems the console calls out to.

## 5. Preliminary Risks Spotted

- Collapsing kickoff paths makes bare CLI ticket creation depend on PowerShell being installed — a Windows-first assumption already latent in `kickoff.py`, now made universal (Analysis F1).
- Streamable HTTP MCP + change notifications require a "change bus" the plan's mermaid diagram names (`Bus`) but that does not exist in code yet — new component, not a wire-up of something existing.
- `workspace.toml` changes `find_repo_root`'s search semantics; must stay backward compatible with the current template (`CLAUDE.md`'s own layout) so existing skills/agents that call `find_repo_root()` with no workspace.toml present keep working unchanged.

## 6. Open Confirmations

- `knowledge-center/logs/` was not exhaustively searched for every past incident touching MCP/CLI — only the GROUND-required files were read in full. If a future iteration needs prior-incident evidence beyond what's cited here, re-run `analyze T-017 history`.
- Whether any other skill or script outside `console/` shells directly to `python console/kanban.py ticket create` (rather than the `kickoff` skill/verb) was not exhaustively grepped across `.claude/skills/`; assumed low-risk since `CLAUDE.md` already mandates `kickoff` as the only sanctioned entry point for new tickets.

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-16 | Read | `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` | Canonical scope source |
| 2026-09-16 | Read | `console/server/mcp.py` | Verify mcp-first-class claims |
| 2026-09-16 | Read | `console/server/paths.py` | Verify workspace-contract claims |
| 2026-09-16 | Read | `console/kanban.py` | Verify one-api / dual-kickoff claims |
| 2026-09-16 | Read | `console/config/verbs.toml` | Verify ready/claim/comment absence |
| 2026-09-16 | Read | `console/server/plugins/registry.py` | Verify tracker-spi / plugin-shape claims |
| 2026-09-16 | Read | `console/server/vault.py` (partial) | Verify hardcoded `VAULT_SUBDIR` claim |
| 2026-09-16 | Read | `console/config/plugins.toml` | Confirm plugin rows are UI/HTTP features, not tracker backends |
| 2026-09-16 | Grep | `console/server/agent_manager.py` (`cwd`) | Verify "sess.cwd IS workspace root" claim |
| 2026-09-16 | Read | `console/server/kickoff.py` (partial) | Verify kickoff-path behavior + find PowerShell coupling |
| 2026-09-16 | Read | `console/server/runs.py` (partial) | Read-only T-016 context, confirm no modification needed |
| 2026-09-16 | Grep | `console/server/trackers.py` (`VALID_KINDS`, `comment`) | Find comment-storage gap |
| 2026-09-16 | Grep | `console/server/tickets.py` (`move`, `set_field`, `create`) | Confirm ticket.toml mutation surface for claim |
| 2026-09-16 | Read | `knowledge-center/artifacts/T-017/ticket.toml` | Confirm existing ticket.toml fields (no claim/agent field) |
| 2026-09-16 | Glob | `knowledge-center/artifacts/T-017/*` | Enumerate existing (empty) artifacts |

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements-draft]] · [[T-017-context-snapshot]] · [[T-017-gap-analysis]] · [[T-017-iteration-log]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
