---
ticket: "T-041"
artifact: requirements
status: frozen
freeze_status: frozen
frozen_on: "2026-10-06"
iteration: 1
---

# Requirements: T-041

**Nightly link checker.** A deterministic, read-only checker over the vault's signposts (artifact-map rows and every ticket's `## Links` block, plus prose wikilinks), exposed as one CLI command and one verb, scheduled as a parked routine. Grounded in [[T-041-analysis]] and [[T-041-context-snapshot]]; decisions in [[T-041-decision-log]]; critique history in [[T-041-critique-report]]. Post-freeze changes go through `evolve`.

Terms. **Vault** = `paths.vault_dir(repo_root)` (`console/server/paths.py:136-147`), `knowledge-center/` by default. **Ticket artifact** = a `{T}-*.md` file directly in a ticket directory (a directory under the configured `data_root` that holds `ticket.toml`; `_`-prefixed directories are not tickets). **Links block** = the `## Links` heading line and the text after it up to the next heading of level 1 or 2, or end of file. **Sibling** = another ticket artifact in the same ticket directory. Severity: ERROR or WARN (FR-9).

## Functional Requirements

### Scan and parsing
1. **FR-1 Scan scope.** The checker reads `.md` files under the vault (skipping dot-directories; not following symlinks) and `ticket.toml` through `tickets.list_tickets` (`console/server/tickets.py:127-146`). Links-block, sibling and map rules apply to ticket artifacts only. `_template/`, `_shared/`, `ticket-scripts/` and files outside `{T}-*.md` are exempt from those rules. `_template/` files are not checked for links at all (they hold `{ID}` placeholders) but are in the resolution index. Investigations, wiki, docs and logs get link resolution only (FR-7); they need no Links block and no sibling rule.
2. **FR-2 Link extraction.** A link is `[[target]]`, `[[target|alias]]`, `[[target#heading]]` or `[[target#heading|alias]]`; the target is the text before the first `|` or `#`, trimmed. `[[#heading]]` (same-file anchor) is not checked. A `[[` with no `]]` on the same line is not a link and never swallows following lines. Text inside fenced code blocks (backtick or tilde fences) and inline code spans is ignored. Headings (`#heading`) are not verified.
3. **FR-3 Resolution.** A target resolves iff it equals, case-sensitively, the basename without extension of at least one `.md` file in the vault (the rule `vault.build_graph` applies at `console/server/vault.py:117-147`, restricted to `.md` per `consolidate/SKILL.md:51`). Case-sensitivity holds on case-insensitive filesystems (the index is built from directory listings, never from `os.path.exists`). Non-canonical forms resolve leniently by their last path segment with a trailing `.md` removed, and raise WARN `link-form`: a `.md` suffix, a folder prefix. A target ending in a non-`.md` extension (e.g. `.toml`) or containing `..` is unresolved. When a case-insensitive match exists the dangling message says the names differ only in case.
4. **FR-4 Artifact-map rows.** In `artifact-map.md` (in the vault) every bullet beginning `- [[` is a row and must match `- [[{T}-summary]] — {title} — {status} — {owner} — {date}` (em dash separators, ISO date); otherwise WARN `map-row-format`. Other bullets are ignored. If `artifact-map.md` does not exist the checker reports one ERROR `map-missing` and skips the other map rules. A row target that does not resolve is ERROR `map-dangling`; one that resolves but is not `{T}-summary` of an existing ticket is ERROR `map-unknown-ticket`. The row's section is the nearest preceding `## ` heading.
5. **FR-5 Map versus tickets.** Against `ticket.toml` (tickets of kind `tickets`): a ticket with no row is ERROR `map-missing-row`; a ticket with two or more rows is ERROR `map-duplicate-row`. For rows not under `## Archived`: stage to (section, status label) is open to Active/Open, in-progress to Active/In Progress, verify to Active/Verify, blocked to Blocked/Blocked, done to Completed/Complete. A label mismatch is ERROR `map-status-drift` (message names row label and stage); a section mismatch is ERROR `map-section-drift`; a title different from `ticket.toml` `title` is ERROR `map-title-drift`. A stage not in the table is skipped. The `blocked` row (section and label) is an assumption: no ticket is blocked today, so it is unverified against a real row. Owner and date are not compared.

### Ticket artifact rules
6. **FR-6 Links block form.** Each ticket artifact must carry exactly one Links block as its last section. No block is ERROR `links-missing`. Two or more `## Links` headings are ERROR `links-duplicate`. A line that starts `##` and `Links` but is not exactly `## Links` (trailing spaces tolerated), or a `## Links` occurring after other text on a line (outside code), is ERROR `links-malformed` (the fused case). A level 1 or 2 heading after the block is WARN `links-not-last`.
7. **FR-7 Link targets resolve.** Every link target inside the Links block of any scanned file (ticket artifact, dossier, wiki, docs) that does not resolve is ERROR `links-dangling`, reported with file and line. Unresolved links elsewhere (prose bodies of any scanned file, including `[[…]]` placeholders) are WARN `body-dangling`. Frozen files are not exempt: a dangling Links entry in a frozen artifact is still reported, and the fix is a Links-block-only edit (precedent `T-036-progress.md:36`).
8. **FR-8 Sibling links.** For each ordered pair of siblings (A, B): if A's Links block contains B and B's does not contain A, WARN `one-way-link` at B naming A. Per file, if the block omits one or more siblings, one WARN `links-incomplete` listing them (consolidate: "every sibling", `consolidate/SKILL.md:50`). A link to itself is ignored. Links between different tickets need not be reciprocal and are never reported. A sibling with no Links block counts as linking nothing.

### Output and entry points
9. **FR-9 Severity and exit codes.** ERROR codes: `map-missing`, `links-missing`, `links-duplicate`, `links-malformed`, `links-dangling`, `map-dangling`, `map-unknown-ticket`, `map-missing-row`, `map-duplicate-row`, `map-status-drift`, `map-section-drift`, `map-title-drift`. WARN codes: `one-way-link`, `links-incomplete`, `links-not-last`, `body-dangling`, `link-form`, `ambiguous-basename`, `misplaced-artifact`, `map-row-format`. Exit 0 when there are no errors (warnings alone pass); exit 1 on any error, or on any warning when `--strict`; exit 2 when the check could not run (vault directory missing or unreadable, or `--ticket` names a ticket that does not exist). The set of codes lives in one constant so tests can enumerate it.
10. **FR-10 Output.** Text output lists errors then warnings, each as level, code, path:line and a one-sentence message that states the fix; ends with one summary line (`N tickets, M files | E error(s), W warning(s)`). Text output is ASCII only and, by default, shows at most 20 warnings per code followed by `+K more (use --all)`; `--all` lists every one; errors are never capped. `--json` prints `{"summary": {...}, "findings": [{"level","code","path","line","message"}]}` with every finding (no cap), same top-level shape as `harness lint --json` (`console/kanban.py:365-368`). Paths are vault-relative with `/`. Ordering is by (level, path, line, code).
11. **FR-11 CLI.** `python console/kanban.py vault links [--json] [--strict] [--all] [--ticket T-NNN]`, added to the existing `vault` group (`console/kanban.py:826-838`).
12. **FR-12 Verb.** A `link-check` verb in `console/config/verbs.toml` (`needs_confirm` false, `needs_ticket` false) with handler `verb_handlers.link_check_verb(repo_root, ticket=None, strict="")` that returns `{"ok": bool, "summary": {...}, "findings": [...]}` and never raises because of findings (the verb's findings are never capped; the string `1/true/yes/on` is accepted for `strict`, as `evals_replay` does for `changed`). `ok` is true when the CLI would exit 0 under the same flags. With `ticket` set, only findings for that ticket's artifacts and its map row are returned; global checks (other tickets' rows, vault-wide prose links) are skipped. The verb is exposed to HTTP, MCP and agent tools by the registry with no further code (`mcp.py:11-15`, `agent_tools.py:339-358`).
13. **FR-13 One home, deterministic subset.** Two basenames-level checks stand in for "every fact has one home": two or more `.md` files in the vault with the same basename is WARN `ambiguous-basename` once per name listing all paths (filenames must be globally unique, `consolidate/SKILL.md:47`); a ticket artifact whose filename does not start with `{directory name}-` is WARN `misplaced-artifact`. No check compares prose, headings or file contents for duplication, and none is planned.
14. **FR-14 Documentation.** `console/README.md` (near `harness lint`, line 116 and section at 533) and `.claude/skills/console/SKILL.md` (line 28) document the command, severities and exit codes. `validate-artifacts` is left as is; one sentence in the README states the split: this checker is the automatic subset (dangling, missing block, one-way, map drift); requirement-to-task-to-code traceability stays manual.
15. **FR-15 Schedule.** `console/config/schedules.toml` gains a row `id = "link-check-nightly"`, `label = "Nightly link check"`, `expr = "30 2 * * *"`, `verb = "link-check"`, `enabled = false`, with a comment saying why it is parked (the repair pass in [[T-041-decision-log]] D-9 comes first) and that the console must be running at that time. No `confirm`. It is not wired into CI.

## Non-Functional Requirements
1. **NFR-1 Stdlib only.** Python standard library plus existing `console/server` modules; no new dependency (so `tech-select` is not needed). No syntax newer than the console's CI interpreter (3.13).
2. **NFR-2 Read-only.** The checker never creates, modifies, renames or deletes any file, including caches. It opens files only for reading.
3. **NFR-3 Deterministic.** The same tree gives byte-identical text and JSON; no clock, no randomness, no environment dependence in findings; directory listings sorted.
4. **NFR-4 Performance.** Each file is read once. Budget: the real vault (about 650 `.md` files; prototype 0.2 to 0.6 s) completes in under 5 s on a developer machine; a synthetic 2,000-file vault under 10 s in CI.
5. **NFR-5 Cross-platform text.** CRLF, LF, mixed endings, a lone CR and a UTF-8 BOM (8, 7 and 1 files today) must give the same findings as the LF equivalent; first-line links are not hidden by a BOM; output paths use `/`; no dependence on filesystem case sensitivity or path separator; the working tree being CRLF while the index is LF changes nothing.
6. **NFR-6 Contained.** Reads only files discovered under the vault root (and the ticket directories the console config names). Does not follow symlinks or junctions; a link target is never turned into a path to open.
7. **NFR-7 Testable.** Pure functions over text and a file index, plus a thin walker, so each rule is testable with `repo` tmp-workspace fixtures (`console/tests/conftest.py:129-138`). Every code in FR-9 has a test that makes it fire and the clean fixture yields no findings (`console/tests/test_harness_lint.py:1-9` pattern).
8. **NFR-8 No UI.** Adds no static asset, tab or API route of its own; static export is unaffected (`console/server/export.py` has no verb or schedule reference); ES5 rules do not apply.
9. **NFR-9 Robust.** An unreadable or non-UTF-8 file is read with replacement characters (as `harness_lint._read`, `harness_lint.py:74-76`) and never aborts the run; the run always reaches the summary unless exit 2 applies.
10. **NFR-10 Console-safe output.** ASCII only in text mode (`harness_lint.py:341-343`).

## Acceptance Criteria
Tags: `[PY]` automated in `console/tests/test_link_check.py` unless a file is named; `[MANUAL]` needs a human or a live console.

Parsing and resolution
- [ ] AC-1 `[PY]` (FR-1) In a tmp workspace with two tickets, `_template/`, `_shared/` and a `ticket-scripts/README.md`, only `{T}-*.md` files at ticket roots get Links-block findings; `{ID}` placeholders in `_template/` produce none.
- [ ] AC-2 `[PY]` (FR-1, NFR-6) With a `workspace.toml` that relocates the vault, the scan covers the relocated vault, not `knowledge-center/`.
- [ ] AC-3 `[PY]` (FR-2) The same unresolved link inside a ``` fence, a ~~~ fence and an inline code span yields no finding; outside code it yields one.
- [ ] AC-4 `[PY]` (FR-2, FR-3) `[[x|alias]]`, `[[x#h]]`, `[[x#h|alias]]` resolve against `x`; `[[#h]]` is ignored; an unclosed `[[x` followed by a line with a real dangling link does not hide or merge it.
- [ ] AC-5 `[PY]` (FR-3) `[[t-041-summary]]` is dangling when only `T-041-summary.md` exists, with a message noting the case difference.
- [ ] AC-6 `[PY]` (FR-3) `[[x.md]]` and `[[artifacts/T-1/x]]` resolve and raise `link-form`; `[[x.toml]]` and `[[../../CLAUDE.md]]` are dangling and no file outside the vault is opened (open is mocked or the file is a trip-wire).
- [ ] AC-7 `[PY]` (FR-13, FR-3) Two `.md` files with one basename in different folders give one `ambiguous-basename` naming both paths; a link to that name resolves.
- [ ] AC-8 `[PY]` (FR-3) Drift guard: on a fixture with only `.md` files and no code spans, the resolved (source, target) pairs, self-links excluded, equal the `wikilink` edges of `vault.build_graph` for the same tree.

Artifact map
- [ ] AC-9 `[PY]` (FR-4) A well-formed row yields no finding; a row missing the date yields `map-row-format`; non-row bullets are ignored.
- [ ] AC-10 `[PY]` (FR-4) A workspace with no `artifact-map.md` yields one `map-missing` and no other map finding; a row whose target is absent yields `map-dangling`; a row pointing at a real file that is not `{T}-summary` of an existing ticket yields `map-unknown-ticket`.
- [ ] AC-11 `[PY]` (FR-5) A ticket without a row yields `map-missing-row`; a ticket with two rows yields `map-duplicate-row`.
- [ ] AC-12 `[PY]` (FR-5) Stage `verify` with a row reading "Open" yields `map-status-drift`; stage `done` under Active yields `map-section-drift`; a differing title yields `map-title-drift`; consistent rows, rows under Archived and unknown stages yield none.

Ticket artifacts
- [ ] AC-13 `[PY]` (FR-6) No Links block yields `links-missing`; two yield `links-duplicate`; `## Links- [[x]]`, `## Links text` and `...text ## Links` (outside code) yield `links-malformed`; trailing spaces on the heading are accepted; a heading after the block yields `links-not-last`.
- [ ] AC-14 `[PY]` (FR-7) A dangling target in a ticket artifact's Links block is an ERROR with the right file and line; the same target in prose is a WARN `body-dangling`; `[[…]]` in prose is a WARN; a dangling target in a dossier's Links block is an ERROR.
- [ ] AC-15 `[PY]` (FR-7) A file with frontmatter `freeze_status: frozen` and a dangling Links entry is still reported.
- [ ] AC-16 `[PY]` (FR-8) A lists B and B does not list A yields one `one-way-link` at B; mutual links yield none; a self link yields none; a link to another ticket's artifact with no back link yields none; a sibling with no Links block counts as linking nothing.
- [ ] AC-17 `[PY]` (FR-8) A block omitting a sibling yields exactly one `links-incomplete` for that file listing the missing names.
- [ ] AC-18 `[PY]` (FR-13) `T-002-notes.md` inside `T-001/` yields `misplaced-artifact`.

Contract and output
- [ ] AC-19 `[PY]` (FR-9) Exit codes: clean 0; warnings only 0; warnings with `--strict` 1; any error 1; missing vault directory 2 with a message; `--ticket T-999` (no such ticket) 2.
- [ ] AC-20 `[PY]` (FR-9, NFR-7) A test enumerates the code constant and asserts each of the 20 codes has a firing fixture and none fires on the clean fixture.
- [ ] AC-21 `[PY]` (FR-10) `--json` parses, `summary` counts equal the findings, every finding has level, code, path, line, message; two runs are byte-identical.
- [ ] AC-22 `[PY]` (FR-10, NFR-10) Text output encodes as ASCII, lists errors before warnings, caps warnings at 20 per code with a `+K more` line, `--all` lists all, errors are never capped, and the last line is the summary.
- [ ] AC-23 `[PY]` (FR-11) `vault links` runs through `kanban.main` (or a subprocess) and propagates the exit code; `--ticket T-001` limits output to that ticket and its map row.
- [ ] AC-24 `[PY]` (FR-12) `link-check` is in the verb registry with `needs_confirm` false; `verbs.run(repo, "link-check")` returns `ok`, `summary` and `findings` and does not raise when errors exist; `strict="true"` flips `ok` for a warnings-only tree; `ticket="T-001"` scopes the findings.
- [ ] AC-25 `[PY]` (FR-12) The MCP tool list (as `console/tests/test_mcp.py:375`) and the agent tool list (as `test_agent_tools.py:202`) include the new verb.
- [ ] AC-26 `[PY]` (FR-15) `schedules.toml` has `link-check-nightly`, verb `link-check`, `enabled = false`, parses through `schedules.registry`, its verb exists in `verbs.toml`, and `TestShippedConfig` still passes.

Constraints
- [ ] AC-27 `[PY]` (NFR-1) An AST scan of `console/server/link_check.py` finds only stdlib and `server.*` imports.
- [ ] AC-28 `[PY]` (NFR-2) The fixture tree (paths, sizes, mtimes, bytes) is identical before and after a run; an AST scan finds no write-mode `open`, `os.remove`, `os.rename`, `os.makedirs` or `shutil` call.
- [ ] AC-29 `[PY]` (NFR-3) Two runs on one tree give identical text and JSON; findings follow the FR-10 ordering.
- [ ] AC-30 `[PY]` (NFR-4) A synthetic vault of 2,000 `.md` files scans in under 10 s; a smoke run on the real repo completes in under 5 s and reports counts without asserting their values.
- [ ] AC-31 `[PY]` (NFR-5) Files written as CRLF, LF, mixed endings, lone CR and with a UTF-8 BOM give findings identical to the LF baseline, including a link on the first line after a BOM.
- [ ] AC-32 `[PY]` (NFR-6) A symlink or junction to a directory outside the vault is not followed (skipped with a stated reason if the OS cannot create one).
- [ ] AC-33 `[PY]` (NFR-9) A file with invalid UTF-8 bytes does not abort the run.
- [ ] AC-34 `[MANUAL]` (FR-10) On the real vault in a Windows terminal the first screen shows the ERROR lines, each with a path and a fix hint a person can act on.
- [ ] AC-35 `[MANUAL]` (FR-15) On a throwaway console (own port, not the user's running app) with the row temporarily enabled, one tick produces a job `submitted_by schedule:link-check-nightly` that finishes `done` with `result.ok` present.
- [ ] AC-36 `[MANUAL]` (FR-14) README, console SKILL and the validate-artifacts split sentence read correctly; `git diff` shows no change under `console/static/` or `console/server/export.py` (NFR-8).

## Traceability
| FR | Acceptance criteria |
|---|---|
| FR-1 | AC-1, AC-2 |
| FR-2 | AC-3, AC-4 |
| FR-3 | AC-4, AC-5, AC-6, AC-7, AC-8 |
| FR-4 | AC-9, AC-10 |
| FR-5 | AC-11, AC-12 |
| FR-6 | AC-13 |
| FR-7 | AC-14, AC-15 |
| FR-8 | AC-16, AC-17 |
| FR-9 | AC-19, AC-20 |
| FR-10 | AC-21, AC-22, AC-34 |
| FR-11 | AC-23 |
| FR-12 | AC-24, AC-25 |
| FR-13 | AC-7, AC-18 |
| FR-14 | AC-36 |
| FR-15 | AC-26, AC-35 |
| NFR-1..10 | AC-27 (1), AC-28 (2), AC-29 (3), AC-30 (4), AC-31 (5), AC-32 (6), AC-20 (7), AC-36 (8), AC-33 (9), AC-22 (10) |

## Out of Scope
- The Needs-you panel ([[T-039-summary]]), the routines board ([[T-040-summary]]), brain views ([[T-038-summary]]). A future view may read the verb's JSON; this ticket adds no UI, route or static file.
- Detecting duplicated prose, headings or paragraphs ("one home" beyond FR-13): no deterministic form exists; no heuristics.
- Repairing any file (checker is read-only). The repair pass and template symmetrization are follow-ups (todos TD-1, TD-2).
- Verifying that a `#heading` anchor exists; requirement-to-task-to-code traceability (stays `validate-artifacts`); relative markdown links `[x](path)` (none are the vault's convention); `.toml` or non-md link targets.
- Adding the check to CI, notifying on a failed nightly, and auto-unparking the schedule.
- Checking `_template/` files themselves; owner and date columns of map rows.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Related: [[T-039-summary]] · [[T-040-summary]] · [[T-038-summary]] · [[INV-2026-10-06-maps-os-ui-adoption-dossier]]
