---
ticket: "T-041"
artifact: analysis
---

# Analysis: T-041

## Context

The MAPS video ([[INV-2026-10-06-maps-os-ui-adoption-dossier]], dossier lines 37 and 54) asks for a nightly check that flags signposts pointing at files that moved, and the rule "every fact has one home". Scope is in [[T-041-summary]]. All code claims below were re-read in the tree on 2026-10-06 (HEAD 2040634) and cited file:line. The spike numbers come from a read-only script (stdlib only, nothing written to the repo) run over the real `knowledge-center/`.

## Current State

- **No link check exists.** `harness_lint.py` scans only `.claude/skills` and `.claude/agents` (`console/server/harness_lint.py:33-34, 251-308`). `workspace_check.py` is about secret paths and template state. `schedules.toml` has two parked rows, `harness-lint-weekday` and `skill-usage-weekly` (`console/config/schedules.toml:25-37`).
- **Template to copy.** `harness_lint` defines `Finding` (level, code, path, message; `:56-71`), `lint()` returning `(findings, summary)` (`:251-308`) and an ASCII-only `format_report` (`:334-346`). It is exposed three ways: CLI `kanban harness lint [--json] [--strict]` (`console/kanban.py:363-375, 1075-1081`), verb `harness-lint` (`console/config/verbs.toml:66-70`, handler `console/server/verb_handlers.py:75-77`) and, automatically, MCP and agent tools (`console/server/mcp.py:11-15`, `console/server/agent_tools.py:339-358`). Errors fail, warnings fail only with `--strict` (`kanban.py:372-375`); CI runs it (`.github/workflows` line 69).
- **Scheduler.** Ticker runs `queue.submit(verb, ticket, confirm=schedule.confirm, args, submitted_by="schedule:<id>")` once a minute; nothing fires while the console is down and missed runs are skipped (`console/server/schedules.py:1-17, 207-233`). `confirm` only matters for a verb with `needs_confirm` (`console/server/verbs.py:146-149`); a read-only verb needs none. The shipped-config test requires every row to be parked (`console/tests/test_schedules.py:245-256`).
- **A job whose verb returns findings still ends `done`.** `jobs._run_one` marks ERROR only when the handler raises, and pushes a notification only then (`console/server/jobs.py:268-297`). So a nightly that finds errors is invisible unless the result is read.
- **Audit.** HTTP `verb.run` and `verb.submit` write audit lines (`console/server/features/verbs_feature.py:41-47, 62`). The ticker path (`schedules.py:223-227`) and `jobs.py` call no `audit.record` (grep of both files), so a scheduled run leaves a job JSON under `console/.cache/jobs` (`jobs.py:49, 107-122`) and no audit line.

## Key Findings

- **Dossier/summary claim "reuse `vault._extract_wikilinks` and the basename match" is only half true.** The extractor is a bare regex `\[\[([^\]|#]+)` (`console/server/vault.py:17, 74-75`): it does not strip code (119 of 7,319 matches sit in code spans or fences), ignores `[[#heading]]`, and can run across lines. The basename match is inline in `build_graph` (`vault.py:117-147`), indexes every text extension (so a `.toml` basename resolves, against `consolidate/SKILL.md:51`), is case-sensitive, caps at 5,000 files (`:109, 117`) and silently drops unresolved links (`:142-144`). There is nothing reusable that reports a dangling link. Recommendation: a new module with its own extractor and resolver, plus a drift-guard test against `build_graph`.
- **Dossier line numbers drifted slightly** (`build_graph` is `vault.py:109-167`, not 100-167); the structure it describes (nodes, edges, cap, `truncated`) is accurate (`vault.py:121, 158-165`).
- **Vault location is configurable** (`console/server/paths.py:136-147`, `workspace.toml`), and ticket dirs come from `console.toml` `data_root` (`paths.py:179-184`, `tickets.py:127-146`). The checker must not hardcode `knowledge-center/`.
- **Spike, real vault today** (656 `.md` of 879 files, 47 ticket dirs, all with `ticket.toml`):
  - Wikilinks: 7,335 raw, 7,200 outside code. Forms: 1 alias, 16 anchors, 1 path, 1 `.md` suffix. Ambiguous `.md` basenames: 0. Filenames are globally unique today.
  - Rule used: bare basename, case-sensitive, against `.md` files across the vault. Case-only mismatches: 0.
  - Unresolved (excluding `_template`, which holds `{ID}` placeholders: 107): 60 in 47 files. By place: **28 in `## Links` blocks across 16 files** (CC-T004/5/6 link `-analysis`/`-requirements` that do not exist; T-004 and T-017 link `-effort-forecast` ghosts; three dossiers link `[[CLAUDE]]`, `[[console]]`, `[[harness-standards]]`, which are repo files outside the vault; one docs file, one wiki path-form), and **32 in prose bodies** (25 are the `[[…]]` placeholder left in requirements drafts).
  - Ticket artifacts missing a `## Links` block: 1 (`T-016-critique-report.md`). Links not the last section: 1 (`T-002-verification.md`). A `## Links` fused mid-line: 0 in the current tree (the known cases were repaired, see `T-036-progress.md:292`).
  - **One-way sibling pairs: 1,344** of 4,630 directed sibling edges, across 38 of 47 tickets. 39 of 47 tickets have at least one sibling omitted from some Links block (3,578 omitted edges); only 8 tickets are fully mutual (CC-T001 to CC-T006, T-001, T-031). T-036 was repaired to zero one-way pairs but still omits siblings. Cause is partly structural: core templates list 7 siblings, working-set templates list 10 (`_template/summary.md:19-20` vs `_template/context-snapshot.md:79-80`), so a fresh scaffold is one-way by construction (T-038..T-041 show 33 each).
  - Files: 8 carry a UTF-8 BOM, 7 have mixed line endings, 1 has a lone CR, 485 are CRLF and 171 LF-only; none is non-UTF-8.
  - **Artifact map:** 47 rows, all parse as `- [[T-NNN-summary]] — title — status — owner — date`; 4 convention bullets are not rows. Every ticket has exactly one row, every row target resolves, titles and owners all match `ticket.toml`. **Three rows are stale:** T-019, T-036, T-037 read "Open" while `ticket.toml` stage is `verify`. Stage mapping that fits all 47 rows: open to Active/Open, in-progress to Active/In Progress, verify to Active/Verify, done to Completed/Complete (blocked to Blocked/Blocked is [unverified]: no blocked ticket today).
  - **Speed:** a full scan in a throwaway Python script takes 0.2 to 0.6 s.
- **Day-one outlook with the proposed severities:** about 32 errors (28 dangling Links targets, 1 missing block, 3 stale map rows), about 1,400 warnings. Unparking before a repair pass would make every night red.

## Research

None needed; stdlib only, existing patterns. `tech-select` is not triggered: no new dependency or unmade technology choice.

## Recommended Path

1. New `console/server/link_check.py` (shape of `harness_lint.py`), verb `link-check`, CLI `kanban vault links`, parked schedule row `link-check-nightly` (see [[T-041-requirements]]).
2. Two severities. Errors for broken signposts; warnings for hygiene (one-way, incomplete, prose links, form). One-way is WARN by default only because of the 1,344-pair day-one debt; a user decision ([[T-041-decision-log]] D-4, tracker Q1).
3. Artifact-map vs `ticket.toml` drift is in scope and an error (deterministic, and a real defect we hit).
4. One-home: only the deterministic subset (unique basenames, artifact prefix equals its folder). Prose duplication is out.
5. Repair pass and template symmetrization are separate follow-ups (todos TD-1, TD-2) before unparking.

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]]
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
