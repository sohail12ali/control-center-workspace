---
ticket: "T-017"
artifact: critique-report
---

# Critique report: T-017

Adversarial critique findings across lifecycle stages. One `CR-{n}` ID sequence, never reused. Format/severity per `.claude/skills/challenge-standards/rules.md`.

## Plan critique

**Last run:** 2026-09-16 · `challenge-plan T-017` · after `breakdown-tasks`, before build.

**Artifacts walked:** `T-017-requirements.md`, `T-017-plan.md`, `T-017-components.md`, `T-017-task-breakdown.md`, `T-017-implementation-plan.md`, `T-017-effort-estimate.md`.

### Summary

| Severity | Count |
|----------|------:|
| Critical | 0 |
| Major | 2 |
| Minor | 3 |
| **Total** | **5** |

Gate: **clear** — zero unresolved critical findings. Both major findings were fixed in place (planner + critic are the same pass here; corrections applied directly to task-breakdown/implementation-plan/plan, not deferred to a separate `replan`, since neither required a scope or requirements decision).

### Findings

| CR-{n} | Severity | Kind | Pointer | Issue | Resolution |
|--------|----------|------|---------|-------|-----------|
| CR-1 | major | traceability | T-017-task-breakdown.md Slice 1a (ticket-creation collapse), Slice 3a (comment verb) | NFR-5 requires `claim`/`comment`/kickoff-collapse mutations all recorded in `audit.py`, but only the `claim` verb (3a-7) had an explicit audit-wiring task — the ticket-creation collapse and `comment` verb had none | resolved: task-breakdown.md 2026-09-16 — added task 1a-7 (ticket-creation collapse → audit.py) and task 3a-12 (comment → audit.py); implementation-plan.md and plan.md effort totals updated 126.5h |
| CR-2 | minor | effort-unrealistic | T-017-task-breakdown.md Effort summary vs. T-017-effort-estimate.md | Task-level dev total was 124.5h, ~11% under the upfront components-basis most-likely (140h), just past the 10% divergence threshold (though well within the full [98-176h] range) | accepted: task-level decomposition is naturally tighter than T-shirt sizing; documented in both task-breakdown.md and plan.md Effort sections; no upper-bound breach, no `replan` trigger. Revised total (126.5h, post CR-1) narrows the gap to ~9.6% |
| CR-3 | major | critical-path | T-017-implementation-plan.md § Build order / Critical path | Critical-path hours were approximated from whole-slice-effort sums (~38h for Backend SPI → vault adapter → claim → stop-hook) rather than the true task-dependency-weighted longest path; this understated that the MCP chain (resources → HTTP transport → editor setup) is comparably long (~32h) and wasn't called out as a second near-critical path | resolved: implementation-plan.md 2026-09-16 — recomputed both chains from task-level dependency weights (32h each, near-tied); build-order section now documents both explicitly and recommends `estimate(mode=forecast)` tracking on whichever slips first |
| CR-4 | minor | layer-violation | T-017-task-breakdown.md 1e-3 (`resources/read` delegates to `verb_handlers.ticket_context`) | BR-1 ("no write path to ticket/tracker state exists outside the Backend SPI") is satisfied for the 4 handlers requirements.md's AC names (`ready`/`claim`/`comment`/`ticket-move`), but the new MCP `resources/read` path delegates to the pre-existing `ticket_context` function, which reads vault state without going through the new Backend SPI | accepted: FR-5's AC explicitly scopes the SPI requirement to `ready`/`claim`/`comment`/`ticket-move`; `resources/read` is a read-only path, not one of the named handlers, and BR-1 concerns write paths — no requirements violation, flagged for future-adapter completeness awareness only |
| CR-5 | minor | traceability | T-017-components.md header note | Component count (15) exceeds `analyze-components`' 5-12 default guidance | accepted: already self-disclosed in components.md; count tracks the ticket's own frozen 5 scope items / 11 FRs at natural grain, not scope creep — no rescoping warranted |

### Not found (checked, no issue)

- **scope-drift:** every task traces to a frozen FR/AC; no orphan work found.
- **contradiction:** plan.md Approach, components.md, task-breakdown.md, and implementation-plan.md effort figures are mutually consistent (126.5h dev, post-CR-1).
- **sequencing-risk:** Phase 3 (verbs) correctly scheduled after Phase 1/2 dependencies (vault adapter, data schema); Phase 4 (ops) correctly scheduled after `claim`/audit (Phase 3) and HTTP transport (Phase 2). No consumer-before-dependency found.
- **untestable:** every task's acceptance criteria are observable (test-simulatable); FR-10's mechanism (deferred to planning per requirements §13) is finalized as a console-side flag/log line in task 4a-2.
- **rollback-gap:** all schema changes (`ticket.toml` fields, `comments` tracker kind, `workspace.toml`) are additive and optional per A2/A3/A7 — no migration-down path needed, confirmed backward-compatible by design, not merely by omission.
- **circular dependency:** none detected in the components.md dependency graph or the task-breakdown's task-level dependency notes.

## Implementation critique

**Last run:** 2026-09-16 · `challenge-implementation T-017` · VERIFY stage, all 4 build phases complete, independent of builder's own per-phase `simplify` passes.

**Artifacts walked:** `T-017-requirements.md`, `T-017-implementation-plan.md`, `T-017-progress.md`, `T-017-decision-log.md`; code read directly (not diffed against a base branch — nothing is committed yet): `console/server/paths.py`, `workspace_config.py`, `tickets.py`, `tomlio.py`, `backends/base.py`, `backends/vault_backend.py`, `mcp.py`, `mcp_http_feature.py`, `verb_handlers.py`, `stop_hook.py`, `setup_editor.py`, `kanban.py`, `trackers.py`; `console/static/` (out-of-scope boundary check).

### Summary

| Severity | Count |
|----------|------:|
| Critical | 0 |
| Major | 0 |
| Minor | 1 |
| **Total** | **1** |

Gate: **clear** — 0 critical findings. Ready for `verify ready` / `validate-artifacts` (already run this session, see `T-017-verification.md`).

### Findings

| CR-{n} | Severity | Kind | Pointer | Issue | Resolution |
|--------|----------|------|---------|-------|-----------|
| CR-6 | minor | traceability | `T-017-effort-estimate.md`, `T-017-task-breakdown.md` | Both wikilink `[[T-017-effort-forecast]]`, which does not exist (`estimate(mode=forecast)` was never run — no re-forecast was needed since actuals came in under estimate throughout). Dangling link, pre-existing from the planning stage, not introduced during build. | accepted: non-blocking — `mode=forecast` is optional per the `estimate` skill and was never triggered by a variance flag; the link is a forward-reference to an artifact that correctly doesn't exist yet. No action needed unless a future `evolve`/re-plan produces one. |

### Not found (checked, no issue)

- **plan-drift:** all 58 tasks' actual implementation matches their stated AC in task-breakdown.md — spot-checked FR-6 (workspace.toml), FR-8 (claim race-safety), FR-5 (Backend SPI), FR-3/4 (MCP resources/HTTP) against the real code, not just progress.md's narrative.
- **incomplete-slice:** no task marked done with missing files — every file progress.md names for each slice exists and contains the described logic (verified by direct read, not just `ls`).
- **spec-gap:** none found against the 11 frozen ACs; see `T-017-verification.md`'s full AC-by-AC evidence table.
- **error-handling:** `ClaimConflictError`, `WorkspaceConfigError`, `RepoRootError`, `PowerShellUnavailable` all confirmed as named exceptions surfaced cleanly (not bare tracebacks) at their respective call sites, by direct code read.
- **test-gap:** 0 of 11 ACs lack test coverage — see newly-written `T-017-test-cases.md` traceability matrix (100% mapped).
- **security-risk:** none found; NFR-4's deferred-auth decision for MCP HTTP is documented, not silently shipped as if secure.
- **operational-risk:** `claim`'s race-safety re-derived independently (not trusted from narrative) — single-lock read-check-write in `tomlio.atomic_update`, confirmed genuinely race-safe by code read + 3x-repeated concurrency test run with no flake. Decision-log a7's `workspace.toml` backward-compatibility claim confirmed via `test_paths.py::test_the_real_checkout_still_resolves` (pins this actual repo's own resolution).
- **out-of-scope leakage:** checked explicitly (Jira/Azure/Linear/GitHub adapter code, UI EventSource/WebSocket, T-018 worktree/branch/PR machinery, T-015/T-016/`runs.py` modification) — none found in any of the four categories. Full evidence in `T-017-verification.md` § Out-of-scope boundary check.

## Links
- [[T-017-summary]] · [[T-017-plan]] · [[T-017-critique-report]] · [[T-017-plan-iteration-log]] · [[T-017-verification]]
