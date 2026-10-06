---
ticket: "T-041"
artifact: context-snapshot
status: final
created: "2026-10-06"
last_updated: "2026-10-06"
scope: codebase + history
---

# Context Snapshot: T-041

> Descriptive only. Facts with file:line; interpretation lives in [[T-041-analysis]]. Numbers marked "spike" come from a read-only stdlib script over the real vault on 2026-10-06 (HEAD 2040634).

---

## 1. Intent (echo)

A deterministic nightly check that flags artifact-map rows and ticket `## Links` entries that point at files that moved or never existed, plus the rule "every fact has exactly one home" where it can be made deterministic ([[T-041-summary]], dossier lines 37, 54).

## 2. Codebase Findings

### Similar / adjacent features already built
- `console/server/harness_lint.py:56-71, 251-346`: `Finding`, `lint()` returning `(findings, summary)`, ASCII `format_report`. Errors fail, warnings only with `--strict` (`console/kanban.py:372-375`).
- `console/server/workspace_check.py:30-75`: read-only report with an `ok` flag (`kanban.py:666-680`).
- `console/server/vault.py:17, 74-75` (`_extract_wikilinks`), `:109-167` (`build_graph`, basename edges at `:142-147`, silently drops unresolved at `:143-144`).
- `.claude/skills/validate-artifacts/SKILL.md` (scope structure item 4, scope links): the manual rule this automates in part; report-only.
- `.claude/skills/consolidate/SKILL.md:46-55`: bare basename, no `.md`, no folder prefix, `.toml` never wikilinked, every artifact ends with a `## Links` block listing every sibling, map row shape.

### Existing patterns to reuse
- Verb registration: `[[verb]]` row in `console/config/verbs.toml:66-70`, handler `(repo_root, ticket=None, **args)` in `console/server/verb_handlers.py:75-77`; arguments arrive as strings from MCP (`verb_handlers.py:80-97`, `evals_replay` parses `changed`). MCP, agent tools and HTTP derive from the registry (`console/server/mcp.py:11-15`, `agent_tools.py:339-358`, `features/verbs_feature.py:30-47`).
- CLI group `vault` already exists (`console/kanban.py:826-838`).
- Schedule row schema and parked rows: `console/config/schedules.toml:1-37`; ticker `console/server/schedules.py:207-233`; parked-config guard test `console/tests/test_schedules.py:245-256`.
- Vault/ticket location helpers: `paths.vault_dir` (`console/server/paths.py:136-147`), `paths.artifacts_dir`, `tickets.list_tickets` (`tickets.py:127-146`).
- Test fixtures: `repo` tmp workspace in `console/tests/conftest.py:129-138`; lint test style (every check proved to fire and to stay quiet) `console/tests/test_harness_lint.py:1-60`.

### Naming and architectural conventions in play
- Stdlib-only console (`console/server/tomlio.py:1-11`); ASCII output for CI and Windows consoles (`harness_lint.py:341-343`); artifacts flat `{T}-{artifact}.md`.

## 3. Historical Findings

### Prior tickets touching the same area
- T-036 repaired one-way links by hand: 37 links added across 13 files, one-way pairs 29 to 0 (`T-036-progress.md:305`); an Edit anchored on `## Links` had fused progress entries (`T-036-progress.md:292`, `T-037-verification.md` F-5). The wiki handoff warns not to anchor on that string (`knowledge-center/wiki/handoff-2026-10-06-pending-work.md:101`).
- T-003 verification removed one dangling `[[T-003-effort-forecast]]` by hand (`T-003-verification.md:78`).

### Relevant commits / PRs
- None specific; the tree is at `2040634` (T-032).

### Known incidents / regressions in this area
- Stale artifact-map rows today: T-019, T-036, T-037 read "Open", `ticket.toml` stage is `verify` (spike). T-032 verification also noted a stale row ([[T-032-verification]] line 87).

## 4. External Systems in the Loop

- None. No network, no third-party service. The console ticker is the only clock (`schedules.py:1-17`).

## 5. Preliminary Risks Spotted

- Day-one flood: 1,344 one-way pairs and about 32 errors (spike); unparking before a repair pass gives a permanently red nightly.
- Console not running overnight: a nightly row silently does not fire (`schedules.py:1-17`).
- A returning verb never fails the job (`jobs.py:268-297`); the result must carry `ok`.
- Line endings: working tree CRLF, index LF; 8 BOM files, 7 mixed, 1 lone CR (spike).

## 6. Open Confirmations

- Q1 (tracker): one-way severity default WARN, user may want ERROR.
- Q2 (tracker): nightly time default `30 2 * * *`.

---

## Source Log

| Source | What was read | Date |
|---|---|---|
| console/server/harness_lint.py, vault.py, schedules.py, jobs.py, verbs.py, verb_handlers.py, paths.py, tickets.py, audit.py | structure, contracts | 2026-10-06 |
| console/config/schedules.toml, verbs.toml, boards/tickets.toml | schedule and verb schema, lanes | 2026-10-06 |
| console/kanban.py, console/tests/conftest.py, test_harness_lint.py, test_schedules.py | CLI wiring, fixtures | 2026-10-06 |
| knowledge-center artifact-map, 47 ticket dirs, `_template/` | spike | 2026-10-06 |
| .claude/skills/validate-artifacts, consolidate | canonical link rules | 2026-10-06 |

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Cross-ticket: [[T-032-verification]] · [[INV-2026-10-06-maps-os-ui-adoption-dossier]]
