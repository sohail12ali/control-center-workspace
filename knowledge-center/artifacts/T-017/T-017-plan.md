---
ticket: "T-017"
artifact: plan
---

# Plan: T-017

## Approach

Multi-layer structure — 5 scope items (one-api, mcp-first-class, tracker-spi, workspace-contract, ready-claim-hooks), 11 FRs, 15 components across 4 layers, and a real dependency chain (Backend SPI interface → vault adapter → claim verb → stop-hook; MCP resources → HTTP transport → editor setup), well past the single-layer threshold (≤6 tasks, no cross-ticket chain). Approach follows the ticket's own decision-log directly rather than re-litigating: build the Backend SPI as its own module distinct from `plugins/registry.py` and `trackers.py` (decision a4), extend `trackers.py`'s `VALID_KINDS` with a 4th `comments` kind (a2), keep `workspace.toml` resolution additive/optional ahead of the existing sibling-folder fallback (a7), and target MCP's already-declared `2025-06-18` protocol version for Streamable HTTP with no version bump (a5). No new tech-select decisions were needed — every technology/architecture choice this ticket implies (interface pattern, TOML tracker shape, MCP transport version) was already resolved in `decision-log.md` a1-a8 during CLARIFY.

Chain run: `requirements stories` → [[T-017-user-stories]] (8 stories, US-1..US-8, covering all 11 FRs) → `analyze-components` → [[T-017-components]] (15 components, 4 layers) → `estimate(mode=upfront)` → [[T-017-effort-estimate]] (140h dev / 235.2h Final-Complete envelope) → `breakdown-tasks` → [[T-017-task-breakdown]] (56 tasks, 4 phases, 124.5h) + [[T-017-implementation-plan]] (synthesis, build order, critical path) → `challenge-plan` below.

## Slices

Slices map 1:1 to the ticket's 5 scope items, sequenced into 4 build phases by dependency (full detail: [[T-017-implementation-plan]]):

- **Phase 1 — Foundations** (parallel): one-api (JSON audit + ticket-creation collapse), tracker-spi interface, workspace-contract schema, ready-claim-hooks data schema, mcp-first-class resources.
- **Phase 2 — Adapters & transport**: mcp-first-class HTTP transport, tracker-spi vault adapter, workspace-contract resolution.
- **Phase 3 — Verbs**: ready-claim-hooks verb handlers (`ready`/`claim`/`comment`).
- **Phase 4 — Ops**: ready-claim-hooks stop-hook + `console setup <editor>`.

## Tasks

Full atomic task list (56 tasks, effort, acceptance criteria, dependencies) lives in [[T-017-task-breakdown]] — not duplicated here per SIMPLIFY (one canonical location for task detail). Task IDs follow `{phase}-{slice}-{task}` (e.g. `2b-3`).

## Effort

| Slice | Estimate | Basis |
|-------|---------:|-------|
| 1a — one-api | 9.5 h | [[T-017-task-breakdown]] Phase 1 |
| 1b — tracker-spi interface | 8 h | [[T-017-task-breakdown]] Phase 1 |
| 1c — workspace-contract schema | 5 h | [[T-017-task-breakdown]] Phase 1 |
| 1d — ready-claim-hooks data schema | 8 h | [[T-017-task-breakdown]] Phase 1 |
| 1e — mcp-first-class resources | 17 h | [[T-017-task-breakdown]] Phase 1 |
| 2a — mcp-first-class HTTP transport | 16 h | [[T-017-task-breakdown]] Phase 2 |
| 2b — tracker-spi vault adapter | 17 h | [[T-017-task-breakdown]] Phase 2 |
| 2c — workspace-contract resolution | 8 h | [[T-017-task-breakdown]] Phase 2 |
| 3a — ready-claim-hooks verb handlers | 18 h | [[T-017-task-breakdown]] Phase 3 |
| 4a — ready-claim-hooks stop-hook + setup | 12 h | [[T-017-task-breakdown]] Phase 4 |
| **Total (dev)** | **126.5 h** | Sum of [[T-017-task-breakdown]] Effort summary (revised +2h post `challenge-plan` CR-1 — see [[T-017-critique-report]]); reconciled against [[T-017-effort-estimate]]'s 140h upfront most-likely (within range, no over-upper-bound flag) |

QC + risk reserve (not task-level, per [[T-017-effort-estimate]]): +73.8h QC, +21.4h reserve → **235.2h Final/Complete envelope**.

### Acceptance criterion coverage

11/11 FRs mapped to ≥1 task; full table in [[T-017-implementation-plan]] § Acceptance criterion coverage. Summary:

| FR | Covered by |
|----|-----------|
| FR-1 | Slice 1a (1a-1..1a-3) |
| FR-2 | Slice 1a (1a-4..1a-6) |
| FR-3 | Slice 1e (1e-1..1e-6) |
| FR-4 | Slice 2a (2a-1..2a-5) |
| FR-5 | Slices 1b + 2b |
| FR-6 | Slices 1c + 2c |
| FR-7 | Slice 3a (3a-1..3a-3) |
| FR-8 | Slices 1d + 3a (3a-4..3a-8) |
| FR-9 | Slices 1d + 3a (3a-9..3a-11) |
| FR-10 | Slice 4a (4a-1..4a-3) |
| FR-11 | Slice 4a (4a-4..4a-8) |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| `claim` race condition corrupts `ticket.toml` under concurrent calls | Med | High | Atomic write/replace guard (task 3a-5), dedicated concurrent-claim test (3a-8); reuses the same file-write safety `tickets.py`/`trackers.py` already need | Builder | requirements.md AC8, Edge Case §8; FR-8 |
| MCP resource change-notification "Bus" is wholly new — no existing mechanism (analysis F5) | Med | Med | Scoped narrowly to MCP resource subscribers only, not the UI board (a8); flagged as highest-uncertainty task (1e-4) with the largest estimate range; consider a timebox/spike if it exceeds ~30h during build | Builder | T-017-analysis.md F5; decision-log a8 |
| PowerShell dependency becomes load-bearing for every ticket-creation entry point post-FR-2 collapse | Med | Med | Accepted, documented constraint (a1) — pre-existing, not introduced by this ticket; `PowerShellUnavailable` must surface honestly from every entry point (task 1a-6) | Builder | decision-log a1; requirements NFR-3 |
| MCP HTTP transport has no new auth scheme | Low | Med | Accepted — same trust boundary as today's unauthenticated local `serve`; explicitly deferred, non-blocking (a5, NFR §5) | Builder/Ops | requirements NFR §5; decision-log a5 |
| Backend SPI naming collision with `console/server/trackers.py` confuses an implementer | Low | Med | Resolved via a4 — "Backend SPI" used throughout tasks/components/stories; docstring cites the rationale (task 1b-2) | Planner/Builder | decision-log a4; analysis F2/F3 |
| Ticket-creation path collapse changes behavior for any external script calling the old bare-TOML-only path | Low | Med | Regression test (1a-5) + changelog note called out in requirements §9 interactions | Builder | requirements-draft.md §9 |

High×High risks: **none** — the one Med×High risk (claim race condition) has an explicit mitigation already tasked, satisfying the gate.

## Dependencies
- Blocks: T-018 (worktree-per-Run, ticket-id-in-branch, PR linkage — depends on this ticket's `claim`/`ready` verb contracts and `claimed_by` field being stable)
- Blocked by: —

## Links
- [[T-017-summary]] · [[T-017-analysis]] · [[T-017-requirements]] · [[T-017-decision-log]] · [[T-017-plan]] · [[T-017-progress]] · [[T-017-verification]]
