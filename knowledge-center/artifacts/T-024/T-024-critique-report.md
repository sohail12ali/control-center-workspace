---
ticket: "T-024"
artifact: critique-report
---

# Critique report: T-024

Shared `CR-{n}` sequence across stages (format and severity: `.claude/skills/challenge-standards/rules.md`). Find, don't fix.

## Plan critique

### Summary

| Severity | Count |
|----------|-------|
| critical | 0 |
| major | 3 |
| minor | 3 |
| **Total** | **6** |

Last run: 2026-10-04 (plan stage, initial). Artifacts walked: `requirements.md`, `plan.md`, `user-stories.md`, `decision-log.md`, `analysis.md`. Missing, skipped: `components.md`, `task-breakdown.md`, `implementation-plan.md`, `effort-estimate.md` (single-layer plan; none produced by design). Gate: **clear** (zero unresolved critical).

### Findings

| CR | Severity | Kind | Pointer | Issue | Resolution |
|----|----------|------|---------|-------|------------|
| CR-1 | major | sequencing-risk | plan T-024-02; NFR Regression | After FR-1 every agent-spawned process (including a builder running pytest inside a console agent session) carries `CONSOLE_REPO_ROOT`, which re-points `find_repo_root()` and can change unrelated tests that rely on cwd | resolved: plan T-024-02 adds an autouse `delenv` in `console/tests/conftest.py` (2026-10-04) |
| CR-2 | major | untestable | plan T-024-01; NFR Regression | The baseline (plan said ~1867) is unmeasured; the planner had no shell in this run, and the tree is dirty with other tickets' edits (`console/kanban.py`, `server/verb_handlers.py`, `tests/test_ui_endpoints.py`), so a later count can drift | resolved: plan T-024-01 measures the exact count first with `git status` snapshot; T-024-06 compares names, not only totals (2026-10-04). Number itself still unknown until the builder runs it |
| CR-3 | major | traceability | `console/server/features/agents_feature.py:278`; [[T-024-analysis]] Key Findings | Analysis says only the API session calls `REGISTRY.request`; `hook_pretooluse` (the Claude CLI approval hook) also does, passing main `repo_root`, so a worktree Claude chat previews the main file, not the worktree file it edits. No FR/AC covers it | 〈TBD〉 owner decision: `evolve` to pass `preview_root=sess.cwd` there (one line, backward compatible) or defer. Plan leaves it unchanged by default (BR-5), risk R10 |
| CR-4 | minor | untestable | AC-3d; plan T-024-06 | AC-3d is a manual live smoke and needs `.mcp.json` committed before a fresh worktree can carry it; commit is an ASK-gate | accepted: recorded as evidence in [[T-024-verification]]; failure routes to `evolve` (D3) |
| CR-5 | minor | traceability | AC-4a, 4c, 5a, 5b | These ACs are written red/guard in T-024-01 but made green in 04/05, so one-task coverage is ambiguous | resolved: coverage table lists both tasks (2026-10-04) |
| CR-6 | minor | contradiction | AC-2b, 3c, 5g vs. new tests | "unmodified" tests vs. adding tests could be read as editing `test_paths.py`/`test_setup_editor.py` | resolved: plan puts new tests in new files; only the `test_api_session.py:608` fake is edited (2026-10-04) |

Categories with no findings: scope-drift, effort-unrealistic (12.5 h, no envelope exists), layer-violation, rollback-gap (no schema/API break; additive defaulted arguments), critical-path (single component; FR-5 is the largest task at 3 h and is acknowledged in R4/R8).

## Links
- [[T-024-summary]] · [[T-024-plan]] · [[T-024-requirements]] · [[T-024-plan-iteration-log]]
