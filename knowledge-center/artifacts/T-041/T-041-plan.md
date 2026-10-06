---
ticket: "T-041"
artifact: plan
---

# Plan: T-041

## Approach

Flat plan, by the caller's direction: one new stdlib module `console/server/link_check.py` shaped like `console/server/harness_lint.py` ([[T-041-decision-log]] D-1), a verb row, a CLI subcommand, a parked schedule row, tests and docs. The dependency chain is linear, so `analyze-components` would add nothing. Honest note: 7 tasks exceed the flat default of 6; kept flat because every split below has a named reason and the chain is one module.

Build order is inside-out: pure functions first (extractor, resolver, with the drift guard against `vault.build_graph`, decision D-3), then the rules (artifact rules, map rules), then assembly and output, then the entry points (verb, CLI, schedule), then docs and verification. The module is read-only and has no new dependency (NFR-1, NFR-2), so `tech-select` is not triggered.

Defaults taken (analyst's, user-adjustable, non-blocking): one-way sibling rule is WARN, ERROR via `--strict` or a later flip of one constant (Q1, D-4); nightly time `30 2 * * *`, parked (Q2, D-9). The repairs TD-1 and TD-2 are follow-ups (R1 to R3 below), not part of this build.

Plan-level design choices the requirements leave open. Each is pinned by a test in the named task; if the user disagrees, change the test and the one-line rule.
- **P-1 Finding type.** `link_check.Finding` has `level, code, path, line, message` (own class; `harness_lint.Finding` has no line, `harness_lint.py:56-71`; `harness_lint.py` is not edited). Task 02.
- **P-2 Could-not-run in the verb.** `check()` raises `LinkCheckError` for the exit-2 conditions (vault dir missing or unreadable; `--ticket` not a ticket). CLI prints the message to stderr and exits 2. The verb lets it propagate, so a scheduled job ends `error` and notifies (`console/server/jobs.py:272-299`) instead of looking green; findings never raise (FR-12, D-11). Through `verbs.run`, an unknown `ticket` is refused earlier by the gate (`console/server/verbs.py:154-159`, `VerbError`); the handler's own check covers direct calls. Task 04, 06.
- **P-3 Malformed heading.** A `links-malformed` line is not a block: the file gets `links-malformed` and not also `links-missing` (one cause, one finding), and counts as linking nothing for the sibling rules. Task 02.
- **P-4 Several blocks.** With `links-duplicate`, sibling rules use the union of all `## Links` blocks; `links-not-last` looks at the last block. Task 02.
- **P-5 `--ticket` scoping** is a post-filter on a full run (resolution needs the whole index anyway): keep findings whose path is inside that ticket's directory, plus map findings whose row target is `{T}-summary` (and `map-missing-row`/`map-duplicate-row` for it), plus `ambiguous-basename` when one path is in that directory. Summary counts are of the filtered set; `tickets` is 1. Task 04.
- **P-6 Line numbers.** Lines break on CRLF, LF or a lone CR (each one break), 1-based, counted after the BOM is stripped. Not `str.splitlines()` (it also breaks on U+2028 and others). Task 01.
- **P-7 Ticket directory** = any directory directly under the `data_root` with a `ticket.toml`, of any kind (Links rules apply to all kinds); map rules use kind `tickets` only (FR-5, `tickets.list_tickets(kind="tickets")`, `console/server/tickets.py:127-148`). Task 02, 03.
- **P-8 ASCII output.** Paths, targets and titles that contain non-ASCII are written with backslash escapes in text mode (map titles hold em dashes and arrows); JSON keeps its default escaping. Task 04.
- **P-9 Junctions.** The walker uses `os.scandir`, skips an entry that is a symlink or a Windows reparse point (`os.path.isjunction` where present, else `st_file_attributes & 0x400`), and never calls `os.path.exists` for name matching (NFR-6, FR-3). Task 02.

## Slices

### Slice A — Engine (tasks 01 to 03)
Pure extractor and resolver, then the artifact rules and the map rules. 03 can run beside 02 once 01 is done.

### Slice B — Contract (tasks 04 and 05)
Assembly, ordering, scoping, exit codes, text and JSON output, then the hardening tests that prove the non-functional requirements.

### Slice C — Surfaces (tasks 06 and 07)
Verb, CLI and parked schedule; then docs, full-suite verification, and the real-vault run plus the manual criteria.

### Follow-ups, not in this build (repairs of existing artifacts)
R1 to R3 at the end of Tasks. They change existing vault files or a shipped config row, so they are separate tickets of work (todos TD-1, TD-2) and must land before the schedule is unparked.

## Tasks

Conventions. Python source in this repo is CRLF in the working tree and LF in the index; `console/kanban.py`, `console/server/verb_handlers.py`, `console/config/verbs.toml`, `console/config/schedules.toml`, `console/README.md` and `.claude/skills/console/SKILL.md` showed CR LF line endings in this stage's count (kanban.py 1,113 lines, verb_handlers.py 761, verbs.toml 350, schedules.toml 37, test_schedules.py 253; README and SKILL counted CRLF too, totals not compared). `git ls-files --eol` could not be run in the planning stage (no shell), so the builder confirms each file. Builders edit those with anchored single edits (never a whole-file rewrite), write the two new files with CRLF to match, and confirm with `git ls-files --eol` before and after (`i/lf w/crlf` is the expected pattern). Tests run as `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q` unless a task says otherwise. Do not touch `console/static/`, `console/server/overview.py`, `console/server/vault.py` or `console/server/export.py` (T-039 works there concurrently; NFR-8).

### [x] T-041-01 — Pure extractor, resolver and drift guard (3 h)
- [ ] Create `console/server/link_check.py`: module docstring (what is ERROR and what is WARN, in the style of `harness_lint.py:9-18`); constants `ERROR`, `WARN`, `ERROR_CODES`, `WARN_CODES`, `ALL_CODES` (the 12 and 8 codes of FR-9, one place); `normalize(text)` (strip a leading BOM, split on CRLF/CR/LF per P-6); `mask_code(lines)` (fenced backtick and tilde blocks and inline code spans); `extract_links(text)` returning `(target, line)` pairs per FR-2; `build_index(md_paths)` (basename-without-extension, case-sensitive, from directory listings only) and `resolve(index, target)` returning resolved / dangling (with a "differs only in case" note) / `link-form` (`.md` suffix, folder prefix; non-`.md` extension or `..` is dangling) per FR-3.
- [ ] Create `console/tests/test_link_check.py` with the first test classes (parsing, resolution, drift guard).
- **Split because:** self-contained deliverable and the hard dependency of every other task (everything calls the extractor and resolver).
- **Done-criteria:** AC-3, AC-4, AC-5, AC-6 (resolver never turns a target into a path: asserted with a trip-wire, and again end to end in 05), AC-8 (drift guard: on a `.md`-only, code-free fixture the resolved (source, target) pairs, self-links excluded, equal the `wikilink` edges of `vault.build_graph`, `console/server/vault.py:109-147`). `[[#h]]` ignored; an unclosed `[[x` does not swallow the next line; first-line link after a BOM is found; CR-only text gives the same line numbers as LF.
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "extract or resolve or drift"`
- **Basis:** `harness_lint.py` is 346 lines with a 300-line test file as the comparison; extractor plus resolver is about a quarter of the module, and the drift guard needs a fixture. Estimate, plus or minus 30 percent.
- **Depends on:** — (requirements frozen)

### [x] T-041-02 — Scan, Links-block rules, dangling and sibling rules (4 h)
- [ ] In `link_check.py`: junction-safe walker (P-9) under `paths.vault_dir(repo_root)` (`console/server/paths.py:136-147`, never a hardcoded folder; skips dot-directories); `_read` as `harness_lint._read` (`harness_lint.py:74-76`, replacement characters, never aborts); ticket directories from the console config data root (P-7); Links-block parser (heading exactly `## Links` with trailing spaces tolerated; malformed shapes `## Links- [[x]]`, `## Links text`, `... text ## Links`; P-3, P-4); `links-missing`, `links-duplicate`, `links-malformed`, `links-not-last`; `links-dangling` (inside any scanned file's block, with line) and `body-dangling` (prose, including `[[...]]` placeholders; frozen files are not exempt); `one-way-link` and `links-incomplete` (sibling rules, WARN per D-4; severity of `one-way-link` held in one constant so the Q1 flip is one line); `misplaced-artifact`; `ambiguous-basename` (once per name, all paths listed). `_template/` is indexed but not checked; `_shared/`, `ticket-scripts/` and non-`{T}-*.md` files are exempt from Links and sibling rules.
- [ ] Tests (tmp workspace via the `repo` fixture, `console/tests/conftest.py:128-138`; tickets via `tickets.create`; files written with `encoding="utf-8"`).
- **Split because:** an independently reviewed piece (all rules that read ticket artifacts), parallel with 03 after 01.
- **Done-criteria:** AC-1, AC-2 (relocating `workspace.toml` fixture), AC-7, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18; each of these codes has a firing fixture and the clean fixture has no finding: `links-missing`, `links-duplicate`, `links-malformed`, `links-not-last`, `links-dangling`, `body-dangling`, `one-way-link`, `links-incomplete`, `misplaced-artifact`, `ambiguous-basename`, `link-form`.
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "scan or block or dangling or sibling or misplaced or ambiguous"`
- **Basis:** the rules with the most shapes (six Links-block shapes, five sibling cases) and the largest fixture set; judgement, plus or minus 30 percent. At the 4 h cap on purpose.
- **Depends on:** T-041-01

### [x] T-041-03 — Artifact-map rules against `ticket.toml` (3 h)
- [ ] In `link_check.py`: parse `artifact-map.md` rows (bullet beginning `- [[`; `{T}-summary`, then title, status, owner, date split on em dash with the last three fields taken from the right, so a title may itself hold a dash); `map-row-format`, `map-missing` (one finding and skip the rest), `map-dangling`, `map-unknown-ticket`, `map-missing-row`, `map-duplicate-row`, `map-status-drift`, `map-section-drift`, `map-title-drift`. The stage-to-(section, label) table is one constant: open to Active/Open, in-progress to Active/In Progress, verify to Active/Verify, blocked to Blocked/Blocked (unverified, [[T-041-critique-report]] R-3), done to Completed/Complete; unknown stage skipped; rows under `## Archived` skipped for drift; the section is the nearest preceding `## ` heading; owner and date not compared.
- [ ] Tests, using `tickets.create` and `tickets.move` (`console/server/tickets.py:189`) for stages.
- **Split because:** self-contained deliverable (depends only on 01's resolver and the ticket list), can run in parallel with 02.
- **Done-criteria:** AC-9, AC-10, AC-11, AC-12; firing fixtures for `map-row-format`, `map-missing`, `map-dangling`, `map-unknown-ticket`, `map-missing-row`, `map-duplicate-row`, `map-status-drift`, `map-section-drift`, `map-title-drift`; consistent rows, Archived rows and unknown stages yield nothing; the four non-row convention bullets of the real map are ignored.
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "map"`
- **Basis:** nine codes but each is a few lines over one parsed table; the spike found all 47 real rows parse ([[T-041-analysis]] Key Findings); judgement, plus or minus 30 percent.
- **Depends on:** T-041-01

### [x] T-041-04 — Assembly, scoping, exit codes and output (4 h)
- [ ] In `link_check.py`: `check(repo_root, ticket=None)` returning `(findings, summary)` with `summary = {"tickets", "files", "errors", "warnings"}` (`files` = `.md` files read for links, `_template/` excluded; the `harness_lint.lint` shape, `harness_lint.py:302-308`), ordering by (level, path, line, code), P-5 scoping, `LinkCheckError` for exit 2 (P-2); `exit_code(summary, strict)`; `format_report(findings, summary, show_all=False)` (errors then warnings, `LEVEL code path:line` plus a one-sentence message that states the fix, summary line `N tickets, M files | E error(s), W warning(s)`, ASCII only with P-8, at most 20 warnings per code then `+K more (use --all)`, errors never capped); `as_json(findings, summary)` giving `{"summary", "findings": [{level, code, path, line, message}]}` uncapped, vault-relative `/` paths.
- [ ] Tests.
- **Split because:** an independently reviewed piece: the output and exit contract that CLI, verb and schedule all consume, and the point where the 20-code enumeration test becomes possible.
- **Done-criteria:** AC-19 (function level: clean 0; warnings only 0; warnings with strict 1; any error 1; missing vault raises with a message; `--ticket T-999` raises), AC-20 (a test enumerates `ALL_CODES`, asserts exactly the 20 codes of FR-9, each has a firing fixture, none fires on the clean fixture), AC-21, AC-22, AC-29 (ordering; two runs identical in text and JSON).
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "check or exit or format or json or order or codes or scope"`
- **Basis:** formatting and capping are the harder part (`harness_lint.format_report` is 13 lines and has no cap); the enumeration test reuses fixtures from 02 and 03; judgement, plus or minus 30 percent. At the 4 h cap.
- **Depends on:** T-041-02, T-041-03

### [x] T-041-05 — Hardening tests for the non-functional requirements (2.5 h)
- [ ] Add tests (and the fixes they force in `link_check.py`): AST scan for imports (only stdlib and `server.*`) and for write-mode `open`, `os.remove`, `os.rename`, `os.makedirs`, `shutil`; before and after snapshot (paths, sizes, mtimes, bytes) of a fixture tree; 2,000-file synthetic vault timed; smoke run on the real repo timed without asserting counts; one file in each of CRLF, LF, mixed, lone CR, UTF-8 BOM (first-line link) giving findings identical to the LF baseline; a symlink or junction to a directory outside the vault, skipped with a stated reason where the OS cannot create one (`pytest.skip` with the reason); a file with invalid UTF-8 bytes; `[[../../CLAUDE.md]]` with `open` mocked (a trip-wire for NFR-6, end to end).
- **Split because:** an independently reviewed piece (proof of constraints, not behavior) that may force fixes in 02 to 04, so it is reviewed on its own.
- **Done-criteria:** AC-27, AC-28, AC-29 (second half: same tree, same bytes), AC-30, AC-31, AC-32, AC-33, and AC-6 end to end; real-repo smoke under 5 s, 2,000-file vault under 10 s.
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "stdlib or readonly or perf or endings or symlink or utf8 or contained"`
- **Basis:** mostly fixtures; the symlink test and the timing test are the fiddly ones; judgement, plus or minus 30 percent.
- **Depends on:** T-041-04

### [x] T-041-06 — Verb, CLI and parked schedule (4 h)
- [ ] `console/server/verb_handlers.py`: add `from . import link_check` (alphabetical among the imports at lines 16-36) and `link_check_verb(repo_root, ticket=None, strict="")` next to `harness_lint_verb` (`verb_handlers.py:75-77`); returns `{"ok", "summary", "findings"}` (uncapped); `strict` accepts `1/true/yes/on` as `evals_replay` does (`verb_handlers.py:86`); `ok` equals "CLI would exit 0 under the same flags".
- [ ] `console/config/verbs.toml`: a row `id = "link-check"` (`needs_confirm` false, `needs_ticket` false) after `harness-lint` (`verbs.toml:66-70`), with a hint that says it is read-only.
- [ ] `console/kanban.py`: add `link_check` to the `from server import ...` line (`kanban.py:19`), `cmd_vault_links(args, repo_root)` beside `cmd_vault_graph` (`kanban.py:171-172`) mirroring `cmd_harness_lint` (`kanban.py:363-375`) and printing `LinkCheckError` to stderr with exit 2, and the parser entry `vault links [--json] [--strict] [--all] [--ticket T-NNN]` in the `vault` group (`kanban.py:826-838`).
- [ ] `console/config/schedules.toml`: a row `link-check-nightly`, label `Nightly link check`, `expr = "30 2 * * *"`, `verb = "link-check"`, `enabled = false`, no `confirm`, a comment saying why it is parked (repair pass first, R1 and R2, [[T-041-decision-log]] D-9) and that the console must be running at that time (`console/server/schedules.py:1-17`). Not wired into CI.
- [ ] Tests. They use the shipped registry the way `console/tests/test_evals_verb.py:54-69` does (`verbs.registry(ROOT, force=True)`, `mcp.tool_list(ROOT)`), and the CLI the way `test_cli_json.py` and `test_cli_encoding.py` do: call `kanban.cmd_vault_links(ns, repo)` for output and exit codes (`kanban.main` is avoided: it calls `find_repo_root` and loads `.env`), plus one subprocess run with `CONSOLE_REPO_ROOT=repo` under `PYTHONIOENCODING=cp1252` (`test_cli_encoding.py:47-54`) for exit-code propagation and ASCII output.
- **Split because:** a hard handoff: the registry, MCP, agent-tool and scheduler surfaces consume the module only through these rows, and each surface is a reviewable seam.
- **Done-criteria:** AC-23, AC-24 (verb listed with `needs_confirm` false; `verbs.run(repo, "link-check")` returns `ok`, `summary`, `findings`, does not raise when errors exist; `strict="true"` flips `ok` on a warnings-only tree; `ticket="T-001"` scopes), AC-25 (shipped `mcp.tool_list` and `agent_tools.tool_definitions` include `link-check` and `console_link_check`), AC-26 (`schedules.registry` parses the row, verb exists, `enabled` false, `TestShippedConfig` at `console/tests/test_schedules.py:245-253` still passes), `kanban vault links --help` parses all four flags. No existing test pins the verb list (checked: `test_verbs.py:73` and `test_agent_tools.py:15-26` use local fixture configs; `test_plugins.py:139` and `test_desktop_verbs.py:317` compare to the live registry; `test_mcp.py:375` and `test_agent_tools.py:202` are subset checks), so none needs editing. Re-run them anyway: `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_verbs.py console/tests/test_plugins.py console/tests/test_mcp.py console/tests/test_agent_tools.py console/tests/test_schedules.py console/tests/test_desktop_verbs.py console/tests/test_evals_verb.py console/tests/test_cli_json.py -q`.
- **Test:** `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_link_check.py -q -k "verb or cli or mcp or tool or schedule"` and the regression command above.
- **Basis:** four small edits in four files, each anchored; most of the time is the CLI and registry tests; judgement, plus or minus 30 percent. At the 4 h cap.
- **Depends on:** T-041-04 (T-041-05 may run beside it)

### [ ] T-041-07 — Docs, full verification, real-vault run, manual criteria (3 h)
- [x] `console/README.md`: the command in the CLI block after `harness lint` (`README.md:116`), a paragraph near the `harness lint` section (`README.md:533`) with severities and exit codes 0/1/2, the `--all` and `--ticket` flags, that it is not in CI and the schedule is parked, and the one-sentence split with `validate-artifacts` (automatic subset: dangling, missing block, one-way, map drift; requirement-to-task-to-code traceability stays manual). `.claude/skills/console/SKILL.md`: a line after `harness lint` (line 28) and `vault links` in the "Also" line (line 31). `validate-artifacts` is left as is (FR-14).
- [x] Full suite: `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests -q` (record pass/fail counts from the tree, not from a subagent's report), then `python console/kanban.py harness lint` still clean, then `git diff --stat` shows no change under `console/static/`, `console/server/export.py`, `console/server/vault.py`, `console/server/harness_lint.py`.
- [x] Real-vault read-only run: `python console/kanban.py vault links` and `--json`, record the numbers in `T-041-progress.md` beside the spike (about 32 errors, about 1,400 warnings expected; explain any difference).
- [ ] [MANUAL] owner for AC-34, AC-35, AC-36 (below).
- **Split because:** an independently reviewed piece (verification and the manual acceptance), and the only task that touches human or live-console steps.
- **Done-criteria:** AC-34 (real vault in a Windows terminal: the first screen shows the ERROR lines, each with a path and a fix hint a person can act on; the cap hides the warning flood), AC-35 (throwaway console on its own port, row temporarily enabled with `expr = "* * * * *"` in a scratch copy of the workspace, not the user's running app and not the committed file: one tick makes a job `submitted_by schedule:link-check-nightly` that ends `done` with `result.ok` present), AC-36 (README, console SKILL and the split sentence read correctly; `git diff` empty under `console/static/` and `console/server/export.py`). Full suite green, or each failure named and owned.
- **Test:** the full-suite command above; manual steps recorded with evidence in `T-041-verification.md`.
- **Basis:** two doc edits, one suite run and a manual console tick; judgement, plus or minus 30 percent.
- **Depends on:** T-041-05, T-041-06

### Follow-ups before unparking (repairs of existing artifacts; NOT part of this build, nothing here is performed by the plan stage)
- [ ] **T-041-R1 — Repair the day-one errors (todo TD-1).** About 32 findings: 28 dangling Links targets (CC-T004/5/6 `-analysis`/`-requirements`, T-004 and T-017 `-effort-forecast`, T-031, three dossiers that link `[[CLAUDE]]`, `[[console]]`, `[[harness-standards]]`, one docs file, one wiki path-form), 1 missing Links block (`T-016-critique-report.md`), 3 stale map rows (T-019, T-036, T-037 read "Open" while in `verify`) and 1 `links-not-last` (`T-002-verification.md`, a warning). Frozen files get Links-block-only edits (precedent `T-036-progress.md:36`). Owner fixer, via `fix`, `progress-tracker`; done when `vault links` exits 0. Effort not estimated here: scope is the exact list the first real-vault run prints (T-041-07).
- [ ] **T-041-R2 — Symmetrize `_template/` Links (todo TD-2).** Core templates list 7 siblings, working-set templates 10 (`_template/summary.md:19-20` against `_template/context-snapshot.md:79-80`), and `_template/release.md:34-35` lists 3. A fresh scaffold must have no one-way pair; prerequisite for flipping one-way to ERROR. Owner fixer; kickoff and `consolidate` read the templates, so check `kickoff` output after the change.
- [ ] **T-041-R3 — Unpark the schedule (user decision, after R1).** Set `enabled = true` on `link-check-nightly` and pick the time (Q2). This breaks `TestShippedConfig` (`console/tests/test_schedules.py:252-253` requires every shipped row parked), so the same change must deliberately adjust that test. Optional in the same step: flip `one-way-link` to ERROR (Q1) once R2 is done and the one-way count is zero.

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-041-01 — Extractor, resolver, drift guard | 3 h | comparison with `harness_lint.py` and its tests; judgement |
| T-041-02 — Scan, Links-block, dangling, sibling rules | 4 h | most shapes and fixtures; judgement |
| T-041-03 — Artifact-map rules | 3 h | nine codes over one table; real rows all parse (spike) |
| T-041-04 — Assembly, scoping, exit codes, output | 4 h | cap, ASCII and enumeration test; judgement |
| T-041-05 — Hardening tests | 2.5 h | fixtures; symlink and timing tests are fiddly |
| T-041-06 — Verb, CLI, parked schedule | 4 h | four anchored edits plus registry and CLI tests |
| T-041-07 — Docs, verification, real run, manual | 3 h | one suite run plus a manual console tick |
| **Total (build)** | **23.5 h** | sum; each row plus or minus 30 percent, so about 16 to 31 h. R1 to R3 not included |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| AC-1, AC-2 | T-041-02 |
| AC-8 | T-041-01 |
| AC-3, AC-4, AC-5 | T-041-01 (extractor and resolver level), T-041-02 (finding level: one finding or none, with file and line) |
| AC-6 | T-041-01 (resolver flags the form), T-041-02 (`link-form` finding), T-041-05 (no file opened, end to end) |
| AC-7, AC-13, AC-14, AC-15, AC-16, AC-17, AC-18 | T-041-02 |
| AC-9, AC-10, AC-11, AC-12 | T-041-03 |
| AC-19, AC-20, AC-21, AC-22 | T-041-04 (AC-19 CLI propagation also in T-041-06) |
| AC-23, AC-24, AC-25, AC-26 | T-041-06 |
| AC-27, AC-28, AC-30, AC-31, AC-32, AC-33 | T-041-05 |
| AC-29 | T-041-04 (ordering, identical text and JSON), T-041-05 (same bytes) |
| AC-34, AC-35, AC-36 `[MANUAL]` | T-041-07 (final owner) |

Result: 36 of 36 acceptance criteria are mapped (33 `[PY]` to tasks 01 to 06, 3 `[MANUAL]` to task 07).

| Requirement | Covered by |
|-------------|-----------|
| FR-1 | T-041-02 |
| FR-2, FR-3 | T-041-01 |
| FR-4, FR-5 | T-041-03 |
| FR-6, FR-7, FR-8, FR-13 | T-041-02 |
| FR-9, FR-10 | T-041-04 |
| FR-11, FR-12, FR-15 | T-041-06 |
| FR-14 | T-041-07 |
| NFR-1, NFR-2, NFR-4, NFR-5, NFR-6, NFR-9 | T-041-05 (design in 01, 02) |
| NFR-3 | T-041-04, T-041-05 |
| NFR-7, NFR-10 | T-041-04 |
| NFR-8 | T-041-07 (no static, export or route change; `git diff` check) |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| Day-one debt makes every night red (about 32 errors, about 1,400 warnings) | High | Med | Schedule parked; R1 and R2 are prerequisites to R3; one-way is WARN; output capped | Planner, then fixer | CR-1, [[T-041-analysis]] Key Findings |
| A scheduled run with errors ends `done` and looks green | Med | Med | Result carries `ok` (task 06); could-not-run raises so it does notify (P-2); surfacing `ok` is [[T-040-summary]]'s | Builder | CR-2, `console/server/jobs.py:268-299` |
| Walker follows a Windows junction out of the vault | Med | High | Own `scandir` walker, reparse-point test, AC-32 (task 02, 05); skip with reason if the OS cannot create one | Builder | NFR-6, G-8 |
| Real-vault numbers differ from the spike (code masking, `### Links`, P-3 choices) | Med | Med | Task 07 records both and explains each difference; a surprising error class goes back to a plan-level choice, not a silent tweak | Builder | [[T-041-analysis]] spike |
| Rewriting a CRLF file as LF (or mixing endings) in an edit | Med | Low | Anchored edits only; `git ls-files --eol` before and after; new files CRLF | Builder | caller's brief |
| Non-ASCII in a title or filename breaks a Windows console | Med | Low | P-8 escaping; cp1252 subprocess test (task 06) | Builder | NFR-10 |
| Unparking breaks `TestShippedConfig` | Low | Low | Called out in R3 so the test is changed on purpose | Fixer | `test_schedules.py:252-253` |
| `blocked` map row shape is a guess | Low | Low | One constant; no blocked ticket exists to disagree; revisit when one does | Builder | CR R-3 |
| Concurrent T-039 work edits shared files (`kanban.py`, shared tests) | Low | Med | T-039 is scoped to `console/static` and `overview.py`; builder uses anchored edits and re-reads before each | Builder | caller's brief |
| High by High | none | | | | |

Rated 9 risks, 9 with mitigation, 0 high by high.

## Plan critique

Run by the planner as `challenge-plan`, 2 passes, 2026-10-06. Full rows are also in [[T-041-critique-report]] § Plan critique. Result: 0 critical, 0 major open, gate clear.

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-20 | major | traceability | AC-3 to AC-6 vs T-041-01 | The ACs speak of findings (`link-form`, one finding, file and line), but 01 builds only the extractor and resolver, so 01 alone could not satisfy them | fixed: coverage table maps them to 01 plus 02 (finding level), AC-6 also to 05 |
| CR-21 | minor | critical-path | Dependencies | Critical path was not stated | fixed: 01, 02, 04, 06, 07 = 18 h; 03 and 05 run beside the chain |
| CR-22 | minor | untestable | T-041-04 | `files` in the summary was undefined, so the summary line could not be asserted | fixed: defined as `.md` files read, `_template/` excluded |
| CR-23 | minor | untestable | AC-35 in T-041-07 | A nightly row never ticks inside a test minute | fixed: scratch copy uses `* * * * *` |
| CR-24 | minor | contradiction | Conventions | Plan claimed every file fully CRLF without counting totals, and `git ls-files --eol` was not runnable here | fixed: states what was counted, hands the eol check to the builder |
| CR-25 | minor | scope-drift | caller's brief vs FR-14 | The brief suggests `validate-artifacts` and `consolidate` text; frozen FR-14 says `validate-artifacts` stays as is and names only README and the console SKILL | not changed: frozen requirements win; adding a sentence to `consolidate` or `validate-artifacts` needs `evolve` first (open for the parent) |
| CR-26 | minor | rollback-gap | whole plan | Checker is read-only and adds a verb row, a CLI entry and a parked row; rollback is a revert of those edits, no data to migrate | accepted: noted |
| CR-27 | minor | sequencing-risk | P-2 | The requirements do not say what the verb does on an exit-2 condition; raising ends a scheduled job in `error` with a notification, which is the safer reading | accepted as plan choice P-2, pinned by a test in 04 and 06 |

Pass 2 re-read the whole plan after the fixes: every AC and FR/NFR is mapped, every task has files, done-criteria with AC ids, a test command, effort with basis, a dependency and a "Split because"; no dependency cycle; effort sums to 23.5 h; no new findings. Not done in this stage and stated plainly: no `plan-iteration-log` was scaffolded, no kanban command or `git ls-files --eol` was run (this session had no shell), and `T-041-questions.toml` got no new items (no critical finding needs a user decision).

## Dependencies
- Blocks: unparking `link-check-nightly` (R3) is blocked by R1 and R2; [[T-040-summary]] may later read the verb's `ok`.
- Blocked by: nothing; requirements frozen 2026-10-06.
- Critical path: 01, 02, 04, 06, 07 = 18 h of the 23.5 h; 03 runs beside 02, 05 beside 06.
- Parallel work: [[T-039-summary]] (UI, `console/static`, `overview.py`) shares no file with this plan.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
