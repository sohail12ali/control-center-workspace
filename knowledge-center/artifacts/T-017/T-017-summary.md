---
tags: [completed]
status: Complete
ticket: "T-017"
closed_date: "2026-09-16"
---

# T-017: Delivery Console core: one API, MCP resources/HTTP, tracker SPI, workspace.toml, ready/claim/comment verbs

**Status:** Complete  
**Stage:** CLOSED  
**Owner:** Sohail Ali  
**Created:** 2026-09-16  
**Due:**  
**Closed:** 2026-09-16

## Overview

Console core scope from `.cursor/plans/split-repo_delivery_os_4060c023.plan.md` (T-017 section): a uniform `--json` CLI contract with one kickoff path, MCP resources + change notifications + streamable HTTP transport on `serve`, a tracker SPI (vault-only adapter, no Jira/Azure/Linear/GitHub code), `workspace.toml` replacing the sibling-folder root requirement, and `ready`/`claim`/`comment` verbs with a session stop-hook plus `console setup <editor>`. Independent of T-018 (ticket-git-Run), which depends on this ticket's Run/ready-claim work.

## Current State

GROUND + CLARIFY complete. GROUND-stage read of `mcp.py`, `paths.py`, `kanban.py`, `verbs.toml`, `plugins/registry.py`, `vault.py`, `agent_manager.py`, `kickoff.py`, `runs.py` (read-only), and `plugins.toml` confirmed 4 of 5 plan claims exactly, and surfaced 2 discrepancies the plan doesn't state: (1) collapsing the dual kickoff path onto `server/kickoff.py` inherits its PowerShell dependency for every ticket-creation entry point; (2) no storage target exists today for a `comment` verb (`trackers.py`'s `VALID_KINDS` has no `comments` kind). `challenge-requirements` found 6 gaps (0 blockers) and 4 ⚠ findings, all resolved as documented assumptions (see [[T-017-decision-log]]) rather than escalated — none required a human decision. Requirements frozen at iteration 2, 11 FRs (FR-1..FR-11) covering all 5 scope items with the T-018/tracker-adapter/voice/harness-collapse exclusions preserved. Next: hand off to planner (`requirements stories`).

**Artifacts:** [[T-017-analysis]] · [[T-017-context-snapshot]] · [[T-017-requirements-draft]] · [[T-017-gap-analysis]] · [[T-017-decision-log]] · [[T-017-iteration-log]] · [[T-017-requirements]] (frozen) · [[T-017-user-stories]] · [[T-017-components]] · [[T-017-effort-estimate]] · [[T-017-task-breakdown]] · [[T-017-implementation-plan]] · [[T-017-plan]] · [[T-017-critique-report]] · [[T-017-plan-iteration-log]]

## Planning Complete (CANONICAL)

Multi-layer plan: 15 components / 4 layers, 58 tasks / 4 phases, 126.5h dev (upfront envelope 140h dev / 235.2h Final-Complete with QC+reserve). `challenge-plan` gate clear (0 critical findings; 2 major fixed in place — NFR-5 audit-coverage gap, critical-path recomputation; 3 minor accepted). Two near-tied ~32h critical-path chains (Backend SPI → vault adapter → claim → stop-hook; MCP resources → HTTP transport → editor setup), both parallelizable against the one-api and workspace-contract chains.

## Build Progress (TEMPLATE)

**Phase 1 — Foundations: complete.** All 5 slices done — 1a one-api (`--json` audit + ticket-creation collapse onto `kickoff.create_ticket` + audit wiring), 1b tracker-spi interface (`Backend` ABC), 1c workspace-contract schema (`workspace_config.py`), 1d ready-claim-hooks data schema (`claimed_by`/`claimed_at`, `comments` tracker kind), 1e mcp-first-class resources (`resources/list`/`read`/`subscribe`, new change-notification `bus.py`). 32h actual vs 55.5h estimated. Full suite green: `pytest -o addopts="" console/tests -q` → 1270 passed.

**Phase 2 — Adapters & transport: complete.** All 3 slices done — 2c workspace-contract resolution (`find_repo_root`'s `workspace.toml` branch, scope gap flagged for a renamed vault/console pair), 2b tracker-spi vault adapter (`VaultBackend`, `ticket_move` rewired through the Backend SPI), 2a mcp-first-class HTTP transport (`mcp_http_feature.py`, `POST /api/mcp` + SSE, one shared `Server.handle()` for stdio and HTTP; a real session-id bug found and fixed along the way). 16.5h actual vs 41h estimated. Full suite green: 1298 passed.

**Phase 3 — Verbs: complete.** Slice 3a done — `ready`/`claim`/`comment` verb handlers (FR-7/8/9), reached identically via CLI/MCP/HTTP through the existing verb registry (no per-surface code needed). `claim`'s race-safety (3a-5, the slice's core requirement) is a new `tomlio.atomic_update` primitive reusing the existing lock-file mechanism, closing a TOCTOU gap the prior `load()`+`_save()` pair left open; a conflicting claim now raises a named `tickets.ClaimConflictError` instead of silently overwriting. A real Windows lock-acquire bug (`PermissionError` not retried alongside `FileExistsError`) was found and fixed via the concurrency test written for this task. Both `claim` and `comment` are audited (NFR-5) and publish to the MCP change-notification bus. 6.5h actual vs 18h estimated. Full suite green: `pytest -o addopts="" console/tests -q` → 1328 passed.

**Phase 4 — Ops: complete. All 4 phases done — 58/58 tasks.** Slice 4a — session stop-hook (`console/server/stop_hook.py` + `.claude/hooks/console-stop-reminder.sh`, extending the existing `.claude/settings.json` Stop-hook mechanism alongside `console-refresh.sh`, never blocking session end) and `console setup cursor|claude|vscode` (`console/server/setup_editor.py`, idempotent MCP-config + `AGENTS.md`-snippet writes modeled on this repo's own root `.mcp.json`). 4h actual vs 12h estimated. Full suite green: `pytest -o addopts="" console/tests -q` → **1357 passed** (+120 across the whole ticket, from 1237 at Phase 1's mid-point). Total actuals: 59h vs 126.5h estimated (53% under). One flagged, non-silent scope gap (2c's `workspace.toml` support originally only resolving exactly-named `console`/`knowledge-center` dirs sharing a parent, not an arbitrary renamed vault/console pair) was found at the initial VERIFY pass and **closed by a subsequent fixer pass** (decision-log a9: `paths.vault_dir`/`console_dir`/`resolve_rel` now resolve a genuinely renamed pair end-to-end, proven via `vault.py`/`runs.py`) — independently re-verified by the verifier as a full PASS. See [[T-017-progress]] for full per-slice evidence and [[T-017-task-breakdown]] for per-task actuals. VERIFY complete: 11/11 acceptance criteria PASS.

## Closed (2026-09-16)

Ticket closed by `close-work` after VERIFY passed 11/11 acceptance criteria (AC-6 re-verified full PASS after the AC-6 fixer pass — see [[T-017-verification]]). Full suite: `pytest -o addopts="" console/tests -q` → 1365 passed, 0 failed. `validate-artifacts` structure/links clean (one pre-existing, non-blocking dangling `[[T-017-effort-forecast]]` link noted — optional artifact never generated since no `estimate(mode=forecast)`/replan was triggered). Board lane synced to `done` via `console/kanban.py ticket move T-017 done`. Not deploying — deployer is a separate, explicitly ASK-gated step.

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-test-cases]] · [[T-017-verification]]
