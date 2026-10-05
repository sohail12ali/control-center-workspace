---
ticket: "T-022"
artifact: critique-report
---

# Critique report: T-022

## Requirements critique

**Last run:** 2026-10-01 · `challenge-requirements` (gaps + redteam), iteration 1 re-check

| Severity | Count |
|---|---|
| critical | 0 |
| major | 0 unresolved (6 resolved, 2 accepted) |
| minor | 0 unresolved (3 resolved, 1 accepted) |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | major | ambiguity | draft §4 FR-4 | MCP argument serialization for the canonical call string undefined | resolved: requirements iterate 2026-10-01 (exact `json.dumps` form; edit paths normalized to `/`) |
| CR-2 | major | contradiction | draft §4 FR-1 vs FR-9 | exit 2 on "nothing selected" vs exit 0 on `--changed` with nothing to gate | resolved: requirements iterate 2026-10-01 (FR-1 exit codes restated, AC added) |
| CR-3 | major | unstated-assumption | draft §4 FR-3 | fixture shapes and tool input keys assumed to match the CLI | resolved: enrich 2026-10-01 verified the input keys and `mcp__console__<verb-id>` naming from persisted logs; envelope stays an Open Confirmation, covered by de-duplication |
| CR-4 | major | ambiguity | draft §7 BR-8 / FR-8 | "usable completed turn" undefined | resolved: requirements iterate 2026-10-01 (FR-8 definition) |
| CR-5 | major | nfr-unmeasurable | draft §5, FR-6 | performance, budget, timeout, tool-cap numbers missing | resolved: enrich proposals confirmed under delegated authority (≤ 5 s; 0.50 USD, 180 s, 25 calls) |
| CR-6 | major | untestable | draft §4 FR-6 | live ACs unobservable until a login exists (Q9) | accepted: fake-spawn tests cover the logic; the real smoke run is a manual AC recorded NOT RUN until Q9 |
| CR-7 | minor | contradiction | draft §7 BR-7 vs FR-15 | audit record vs "never records" wording | resolved: requirements iterate 2026-10-01 (BR-7 names the audit exception) |
| CR-8 | minor | scope-creep | draft §4 FR-2 | `skill` field unused by the starter set | resolved: requirements iterate 2026-10-01 (scenario 10 `evolve-logs-before-editing` exercises it) |
| CR-9 | major | unstated-assumption | draft §3, FR-6 | `plan` mode may emit no tool call | accepted: `text scope=any/all` counts plan text and call strings; prompt wording, not the checker, is tuned at the smoke; replay unaffected |
| CR-10 | minor | spof | draft §10 | live depends on one CLI and one login | accepted: replay, tests and CI need neither |
| CR-11 | minor | unstated-assumption | draft §4 FR-11 | quotes assume single-line, newline-insensitive reads | resolved: requirements iterate 2026-10-01 (single-line quotes, text-mode read, loader rejects newlines) |
| CR-12 | major | ambiguity | draft §4 FR-10 | per-scenario checks unspecified, so fail_checks is unreviewable | resolved: requirements iterate 2026-10-01 (Appendix A: every check kind and regex; all 20 quotes and 13 sample regexes verified against the repo) |

Gate: **clear** (0 critical, 0 unresolved; 3 accepted with rationale).

## Plan critique

**Last run:** 2026-10-01 · `challenge-plan` (flat mode, 13 tasks) · artifacts walked: requirements, plan; components, task-breakdown, implementation-plan, effort-estimate: missing, skipped (flat structure by design, see [[T-022-plan]] Approach).

| Severity | Count |
|---|---|
| critical | 0 |
| major | 0 unresolved (5 resolved, 2 accepted) |
| minor | 0 unresolved (3 resolved, 1 accepted, 1 noted) |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-13 | major | contradiction | plan T-022-06 vs requirements FR-5 AC1 / FR-15 | Replay must spawn no process, yet the results record needs `git_head`, which the first draft read with `git rev-parse` | resolved in plan: `git_head` is read from `.git/HEAD`, loose refs and `packed-refs` without a process; tests named in task 06; `--changed` (which needs git) is the one documented exception |
| CR-14 | major | traceability | NFR Security, NFR Maintainability | No task covered "never read `.env`" or "3 modules, no new dependency" | resolved in plan: two guard tests added to task 11 |
| CR-15 | major | untestable | NFR Portability | Local Python is 3.14, CI is 3.11/3.13; a 3.12-only construct would pass locally and fail CI | resolved in plan: task 13 greps for 3.12-only syntax, py3.11 result reported PENDING until CI; risk R19 |
| CR-16 | major | effort-unrealistic | plan T-022-10 | Thread reader, teardown, audit, persistence and 15 tests in one 3 h session | resolved in plan: explicit checkpoint, half (b) can become T-022-10b with the suite green at both boundaries |
| CR-17 | major | sequencing-risk | plan T-022-13 (CI step) | A CI step running `evals replay` before any scenario exists exits 2 and turns CI red | resolved in plan: the step lands in task 13, after the real scenarios; `console/README.md` pointer also last (collision with T-021 doc-drift audit) |
| CR-18 | major | critical-path | plan T-022-12, T-022-13 | T-022 cannot close before T-020 and T-021 ship; a slip in either blocks tasks 12-13 | accepted: tasks 01-11 (about 21.5 h of 30.5 h) are independent; the orchestrator chooses wait or build-early-and-re-pin (R20) |
| CR-19 | major | contradiction | requirements FR-14 and Interactions table vs build order | The requirements say T-020 and T-021 run `evals replay --changed` in their verify step, but T-022 is built after both, so that cannot happen | accepted for build (README wording generalised, tasks 12-13 are the retroactive check); OPEN for the orchestrator: amend FR-14 through `evolve` if the build order stands (R14). Not critical, no question mirrored |
| CR-20 | minor | rollback-gap | plan Approach | FR-15 names the rollback in one sentence; the plan had no concrete revert list | resolved in plan: Rollback paragraph lists every file and hunk |
| CR-21 | minor | untestable | plan T-022-08 | ASCII-only output was untested when an evidence excerpt contains non-ASCII; parser wiring untested without `kanban.main` | resolved in plan: two tests added to task 08 |
| CR-22 | minor | scope-drift | plan T-022-10, T-022-13 | Four plan choices go beyond the frozen text: `stderr` merged into stdout, adopting `procs.kill_tree`/`clean_env` when T-020 provides them, the CI step, the `console/README.md` pointer | noted: the first two keep the live driver consistent with `LiveSession` after T-020; the CI step is optional and flagged for deletion if strict FR-13 is preferred; the pointer is required by FR-14 |
| CR-23 | minor | effort-unrealistic | plan Effort | Estimates have no history; four tasks sit at 3 h | accepted: ranges stated (25-38 h total), re-forecast after task 04 (R18) |
| CR-24 | minor | traceability | plan AC map | The FR-6 manual smoke AC cannot be executed here | resolved: mapped to task 13, which records NOT RUN; verifier repeats it in verification |

Gate: **clear** (0 critical, 0 unresolved). Plan changed in place after the pass (single-layer path): CR-13, 14, 15, 16, 17, 20, 21, 24 edited into [[T-022-plan]]; CR-18, 19, 22, 23 accepted or noted.

## Links
- [[T-022-summary]] · [[T-022-requirements-draft]] · [[T-022-gap-analysis]] · [[T-022-iteration-log]] · [[T-022-plan-iteration-log]] · [[T-022-plan]] · [[T-022-decision-log]]
