---
ticket: "T-041"
artifact: verification
---

# Verification: T-041

Verifier run, 2026-10-06, branch `development`, HEAD `2040634` plus an uncommitted working tree (T-041 and T-039 changes). Scope: all (unit, integration, review, ready), by a verifier who did not write the code. Result: **33/33 [PY] acceptance criteria PASS, 3 [MANUAL] pending (owner: parent session), 0 FAIL, 0 critical or major defects, 2 low findings.** Disposition: ready_to_close is blocked only by the 3 MANUAL ACs and the open task T-041-07 (both expected, not defects).

Static-only: none. Every [PY] AC was run (whole test file 142 passed) and the named tests were read; the 3 MANUAL ACs were not executed. This verifies the checker, its CLI and its verb on tmp workspaces plus a read-only run on the real vault. It does not verify the nightly schedule firing in a live console (AC-35). Test file below is `console/tests/test_link_check.py` (line numbers are its own); `link_check.py` is `console/server/link_check.py`.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Only `{T}-*.md` at ticket roots get Links-block findings; `_template`, `_shared`, `ticket-scripts` exempt | PASS | `TestScanScope::test_only_ticket_artifacts_get_links_block_rules` (:232), `test_clean_tree_has_no_findings_and_counts` (:225); read and run |
| AC-2 | Relocated vault scanned, not `knowledge-center/` | PASS | `TestScanScope::test_relocated_vault_is_scanned_not_the_default_folder` (:241) with a decoy in the default folder; `scan` calls `paths.vault_dir` (`link_check.py:569`); read and run |
| AC-3 | Same unresolved link in ``` fence, ~~~ fence, inline span ignored | PASS | `TestExtract::test_code_is_ignored_outside_it_counts` (:50) asserts only the outside link survives; read and run |
| AC-4 | Alias and anchor forms resolve; `[[#h]]` ignored; unclosed `[[x` does not swallow | PASS | `TestExtract` :45, :68; `TestDangling::test_unclosed_bracket_does_not_hide_a_real_dangling_link` (:374); read and run |
| AC-5 | `[[t-041-summary]]` dangling with a case note | PASS | `TestResolve::test_case_difference_is_dangling_with_a_note` (:101), `TestDangling::test_case_only_difference_is_named` (:357); read and run |
| AC-6 | `.md` and folder prefix resolve with `link-form`; `.toml` and `..` dangling; no outside file opened | PASS | `TestResolve` :107, :113; `TestDangling` :362, :369; `TestContained` (:1036, `builtins.open` spied, trip-wire `CLAUDE.md`); read and run |
| AC-7 | Duplicate basename: one `ambiguous-basename` naming both; link still resolves | PASS | `TestOneHome::test_same_basename_twice_is_one_finding_naming_both_and_still_resolves` (:454); read and run |
| AC-8 | Drift guard against `vault.build_graph` | PASS | `TestDriftGuardAgainstTheVaultGraph` (:141): builds `vault.build_graph(repo)`, compares (source, target) pairs with self-links excluded, asserts at least 6 edges; fixture has a duplicate basename and no code spans. `git diff -- console/server/vault.py` is empty. Read and run |
| AC-9 | Well-formed row clean; missing date `map-row-format`; non-row bullets ignored | PASS | `TestMapRows` (:468-507); run; firing fixture read (`_plant` :644) |
| AC-10 | No map file: one `map-missing`, nothing else; absent target `map-dangling`; non-summary target `map-unknown-ticket` | PASS | `TestMapAgainstTheFiles` (:509-538); run; code read (`map_findings`, `link_check.py:499-526`) |
| AC-11 | No row `map-missing-row`; two rows `map-duplicate-row` | PASS | `TestMapAgainstTheFiles::test_ticket_without_a_row_and_ticket_with_two_rows` (:531); run; code read (`link_check.py:527-539`) |
| AC-12 | verify/Open status drift; done under Active section drift; title drift; consistent, Archived and unknown stages none | PASS | `TestMapDrift` (:547-595); run; `STAGE_MAP` and the drift code read (`link_check.py:63-69`, `540-558`). The `blocked` row shape is still the documented assumption |
| AC-13 | links-missing / duplicate / malformed (3 shapes) / trailing spaces / not-last | PASS | `TestLinksBlock` (:269-326), malformed shapes parametrized at :289; read and run |
| AC-14 | Block dangling ERROR with file:line; prose WARN; `[[...]]` WARN; dossier block ERROR | PASS | `TestDangling` :331, :338, :345; read and run |
| AC-15 | Frozen file with a dangling Links entry still reported | PASS | `TestDangling::test_frozen_files_are_not_exempt` (:351); read and run |
| AC-16 | one-way at B; mutual none; self none; other ticket none; no-block sibling links nothing | PASS | `TestSiblings` (:394-441); read and run |
| AC-17 | Block omitting a sibling: exactly one `links-incomplete` naming the missing | PASS | `TestSiblings::test_incomplete_block_lists_the_missing_siblings_once` (:423); read and run |
| AC-18 | `T-002-notes.md` in `T-001/` is `misplaced-artifact` | PASS | `TestOneHome::test_artifact_with_another_tickets_prefix_is_misplaced` (:446); read and run |
| AC-19 | Exit codes 0 / 0 / 1 strict / 1 error / 2 missing vault / 2 unknown ticket | PASS | `TestExitCodes` (:718), `TestCheck` :685, :691, `TestCli` :1188, :1223. Independent real run: `--ticket T-999` exit 2, stderr `vault links: no such ticket: T-999` |
| AC-20 | Enumeration test: 20 codes, each fires, none on clean | PASS | `TestCodes` (:650-673) parametrized over `link_check.ALL_CODES`; `_plant` (:598) has a fixture per code; 12 ERROR + 8 WARN asserted; read and run |
| AC-21 | `--json` parses; counts equal findings; fields; byte-identical | PASS | `TestJson` (:821), `TestCheck::test_two_runs_are_identical_in_text_and_json` (:706). Independent: real `--json` parses, summary 34/1860 = 1,894 findings |
| AC-22 | ASCII, errors first, 20 per code + `+K more`, `--all`, errors never capped, summary last | PASS | `TestFormat` (:779-817). Independent real runs: 0 non-ASCII bytes in text, json, `--all`, `--ticket`, `--strict`; default output has `+K more (use --all)`, `--all` does not |
| AC-23 | `vault links` through kanban, exit code propagates; `--ticket` limits | PASS | `TestCli` (:1173-1252) incl. a cp1252 subprocess; `cmd_vault_links` read (`console/kanban.py:175`). Independent real CLI exits 1, 1, 1, 1, 2 (table below) |
| AC-24 | `link-check` verb: registry, `ok/summary/findings`, no raise on errors, `strict`, `ticket` | PASS | `TestVerb` (:1085-1146); `link_check_verb` read (`console/server/verb_handlers.py:81`); `verbs.toml` row has no `needs_confirm`. Independent: `verb run link-check` exit 0, `ok: false`, 34/1860 |
| AC-25 | MCP and agent tool lists include the verb | PASS | `TestToolSurfaces` (:1149); regression set including `test_mcp.py` and `test_agent_tools.py`: 223 passed |
| AC-26 | `link-check-nightly` parked, parses via registry, verb exists, `TestShippedConfig` passes | PASS | `TestSchedule` (:1157); `git diff -- console/config/schedules.toml`: `expr = "30 2 * * *"`, `verb = "link-check"`, `enabled = false`, no `confirm`; `test_schedules.py` 46 passed alone |
| AC-27 | AST scan: stdlib and `server.*` imports only | PASS | `TestStdlibOnly` (:852); independent grep of imports in `link_check.py`: `os`, `re`, `from . import boards, paths, tickets`; `console/requirements-dev.txt` has no diff |
| AC-28 | Tree identical before and after; AST: no write-mode open, no remove/rename/makedirs/shutil | PASS | `TestReadonlyCode` (:867), `TestReadonlyRun` (:910); read and run. Independent: file list with sizes and mtimes of all 881 files under `knowledge-center/`, an md5 over every `.md`, and `git status --short` identical before and after 7 real CLI runs |
| AC-29 | Two runs identical; FR-10 ordering | PASS | `TestCheck` :695, :706; `sort_key` plus message (`link_check.py:103`, `658`) |
| AC-30 | 2,000-file vault under 10 s; real repo under 5 s | PASS | `TestPerf` (:922-957). Independent: real vault CLI 0.67 to 0.77 s per run including interpreter start, 645 files. Caveat: the synthetic test reads every file once before timing (OS first-read cost, comment at :934), so it times the checker warm |
| AC-31 | CRLF, LF, mixed, lone CR, BOM equal the LF baseline incl. first-line link | PASS | `TestEndings` (:960-988), `TestLinksBlock` :316, `TestExtract` :75, :78; read and run |
| AC-32 | Symlink or junction out of the vault not followed | PASS | `TestSymlinkNotFollowed` (:1007) parametrized symlink and junction; both ran here (file shows 142 passed, 0 skipped). `_is_reparse_dir` and `walk_md` read (`link_check.py:280-321`) |
| AC-33 | Invalid UTF-8 does not abort | PASS | `TestUtf8` (:1027), `TestDangling` :380; `_read` uses `errors="replace"` (`link_check.py:324`) |
| AC-34 | `[MANUAL]` Real vault in a Windows terminal: first screen shows ERROR lines with path and fix hint | pending: owner (parent session) | Not run by the verifier. Supporting fact only: text output is ASCII, and the first lines are the 5 `map-status-drift` ERRORs, each with path, line and a fix sentence |
| AC-35 | `[MANUAL]` Throwaway console, row enabled, one tick makes job `schedule:link-check-nightly` that ends `done` with `result.ok` | pending: owner (parent session) | Not run. The console on :8790 predates the verb and does not list `link-check` until restarted (not touched) |
| AC-36 | `[MANUAL]` README, console SKILL and split sentence read correctly; no T-041 change under `console/static/` or `export.py` | pending: owner (parent session) | Prose not read by the verifier. Facts: `git diff -- console/server/export.py console/server/vault.py console/server/harness_lint.py console/requirements-dev.txt` is empty; the `console/static/` diff lists T-039's five files (about, app, core, overview, styles), which the builder attributes to T-039; I did not diff their content |

Counts: 33 PASS, 3 pending manual, 0 FAIL.

## Test Results

Independent runs (`PYTHONUTF8=1`), not copied from the builder.

| Command | Result |
|---------|--------|
| `pytest console/tests/test_link_check.py -o addopts="" -q` | 142 passed in 27.07 s (builder: 142+, about 40 s) |
| Regression set: `test_verbs test_plugins test_mcp test_agent_tools test_schedules test_desktop_verbs test_evals_verb test_cli_json test_cli_encoding` | 223 passed in 11.65 s (matches the builder's 223) |
| `test_schedules.py` alone | 46 passed |
| Full suite `pytest console/tests -o addopts="" -q -p no:cacheprovider` | **1 failed, 3024 passed, 1 skipped in 190.66 s** (3026 collected). The one failure is the known `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`), not this ticket's and not touched. The voice-assets timing flake did not fail |
| Builder-reported full suite | `1 failed, 3065 passed, 1 skipped`. My passed count is 41 lower and I did not find the cause. `--collect-only` after the run still gives 3026, so it is not a skip. Likely cause, unconfirmed: test files in the working tree changed between the runs (T-039 has concurrent edits and untracked `test_fresh_core.py` and `test_fresh_source.py`). Not T-041's files |

Real CLI against the real vault, read-only (times include interpreter start):

| Command | Exit | Time | Output |
|---------|------|------|--------|
| `vault links` | 1 | 0.72 s | last line `47 tickets, 645 files, 34 error(s), 1860 warning(s)`; warnings capped, `+K more (use --all)` present |
| `vault links --json` | 1 | 0.67 s | 1,894 findings: 1303 one-way-link, 527 links-incomplete, 29 body-dangling, 28 links-dangling, 5 map-status-drift, 1 links-missing, 1 links-not-last |
| `vault links --strict` | 1 | 0.67 s | same counts (errors exist, so strict is not distinguishable on this vault) |
| `vault links --all` | 1 | 0.77 s | 3,790 lines, no `+K more` |
| `vault links --ticket T-041` | 1 | 0.68 s | `1 tickets, 14 files, 1 error(s), 0 warning(s)`; the error is `map-status-drift artifact-map.md:26` (row reads Open, stage is in-progress) |
| `vault links --ticket T-999` | 2 | 0.67 s | stderr `vault links: no such ticket: T-999`, stdout empty |
| `verb run link-check` | 0 | n/a | JSON `ok: false`, same summary 34/1860 (findings are a result; the verb did not raise) |

Bytes above 127 across all of these outputs: 0. Read-only: the sorted list of every file under `knowledge-center/` with mtime and size, an md5 over all `.md` contents and `git status --short` were identical before and after the 7 CLI runs. No stray process left by me.

Other independent checks:
- Line endings: `git ls-files --eol` for the 6 touched tracked files (`SKILL.md`, `README.md`, `schedules.toml`, `verbs.toml`, `kanban.py`, `verb_handlers.py`): `i/lf w/crlf` (index LF, tree CRLF, as the rest of the repo). New files: `link_check.py` 30,009 bytes, 706 CRLF = 706 LF, 0 lone CR, no BOM; `test_link_check.py` 60,814 bytes, 1,252 CRLF = 1,252 LF, 0 lone CR, no BOM. Pure CRLF as found.
- No new dependency: imports of `link_check.py` are `os`, `re` and `from . import boards, paths, tickets`; `console/requirements-dev.txt` has no diff.
- `git diff` of `console/server/vault.py`, `export.py`, `harness_lint.py`: empty.
- Schedule row: `link-check-nightly`, `30 2 * * *`, `link-check`, `enabled = false`, parked comment, no `confirm`.

## Reviewed against the frozen requirements (by reading `link_check.py`)

- Extractor: `normalize` strips the BOM and splits CRLF/CR/LF without `splitlines`; `mask_code` blanks backtick and tilde fences (indented, longer-fence rule, unclosed runs to EOF) and inline spans; `_LINK_RE` is single-line; `_target` cuts at the first `|` or `#`; empty targets dropped. Matches FR-2 and NFR-5.
- Resolver: exact case-sensitive basename from an index built from the walker (no `os.path.exists`); `..` dangling; `.md` suffix or folder prefix gives "form"; other extensions dangling; case-only hint. Matches FR-3. A target is never turned into a path.
- 20 codes: `ERROR_CODES` 12 and `WARN_CODES` 8 (`link_check.py:46-56`), identical to FR-9.
- Exemptions: `classify` returns "template" (indexed, skipped in the scan loop, `link_check.py:582`), "artifact" only for `{T}-*.md` at the ticket root, "other" for `_shared`, `ticket-scripts`, wiki and the like. Frozen files get no exemption.
- Map rules: only `- [[` bullets are rows; `STAGE_MAP` matches the FR-5 table; Archived skipped; owner and date not compared; `map-missing` short-circuits.
- Read-only: only `open(path, "r", ...)` and `os.scandir`; the AST test enforces it. Uses `paths.vault_dir` (`:569`, `:640`), no hardcoded path. The walker skips dot entries, symlinks and reparse points.
- `LinkCheckError` for an unreadable vault, an unknown ticket and a missing console config; the verb lets it propagate so a job ends `error`; findings never raise.
- `--ticket` is a post-filter on a full run (`_scope`); exit codes 0/1/2 and `--strict` in `exit_code` and `cmd_vault_links`; cap 20 per code in `format_report`, `--all` lifts it.

## challenge-implementation

0 critical, 0 major, 2 low, 3 informational. Nothing blocks.
- L1 (low, FR-12 / AC-23 scoping): `map-row-format` findings carry no `refs` (`link_check.py:510`), so `--ticket T-NNN` and the verb's `ticket` do not return a malformed map row of that ticket, although FR-12 says the ticket's map row is returned. Reproduced with `map_findings` on a malformed T-1 row: `[('map-row-format', ())]`. A malformed row also skips the drift checks (fields are None), so a ticket with a bad row is silent when scoped. The real vault has no such row, so no live impact. Fix: pass the ticket as `refs` when the row target resolves to a ticket.
- L2 (low, cosmetic): the `_is_fused` docstring (`link_check.py:245`) reads "A  that follows other text" with a missing word.
- I1: the 2,000-file perf test warms the cache before timing (disclosed in the test). The real-vault CLI runs (0.7 s) are the stronger evidence.
- I2: `parse_map` runs on unmasked lines, so a `- [[` bullet inside a code fence in `artifact-map.md` would count as a row. Negligible.
- I3: the `blocked` stage row shape is an assumption (no blocked ticket exists), already stated in FR-5 and `STAGE_MAP`.

## Edge Cases Probed
- Empty text and a 50,000-fold `[[` string: no links, no exception (probe on `extract_links`).
- Double-backtick span, indented fence, `[[a|b#c]]`, `[[ ]]`, `[[#h]]` in one text: returned only `z` (line 5) and `a` (line 6), as intended.
- Malformed map row under `--ticket` scoping: L1 above.
- Missing vault, unknown ticket, missing console config, invalid UTF-8, lone CR, BOM, junction, symlink, `..` targets: covered by tests that ran and passed (AC-19, 31, 32, 33, 6).
- Concurrent load: another verifier's suite ran alongside mine; no interference seen, no write to the vault.

## Notes

Drift and open items for the parent. The verifier fixed none of these; this file is the only one written.
1. `T-041-summary.md` is stale: Status `Open`, Stage `TEMPLATE - slice 1 (T-041-01..03) building`, Current State says "No code written; lane still open ... Next: @builder on T-041-01". Code, tests, docs and the lane `in-progress` say otherwise.
2. `T-041-progress.md` Status Summary reads `Stage: TEMPLATE - building slice 1 (T-041-01..03)`; its log shows tasks 01 to 06 done and 07 partly done.
3. Artifact-map row for T-041 (`knowledge-center/artifact-map.md:26`) reads `Open`; `ticket.toml` stage is `in-progress`. The checker reports it (`map-status-drift`, artifact-map.md:26). The same drift exists for T-019, T-036, T-037 (verify) and T-039 (in-progress): outside this ticket.
4. `T-041-plan.md`: T-041-07 stays `[ ]` (expected: it owns AC-34/35/36). AC checkboxes in the frozen requirements are unticked (not touched).
5. `T-041-release.md` is a placeholder: `Shipped 2026-10-06` and `Verify gate ... (ready)` with empty sub-project fields, though nothing has shipped and no deployer ran. Needs the deployer or a revert to the template before close.
6. `ticket.toml` `review_rounds = 0`: no `review-round` recorded yet; the parent or harness records the outcome (the verifier does not hand-edit TOML).
7. The full-suite passed count differs from the builder's by 41 (see Test Results); cause not found.

Open owner questions (non-blocking, defaults in force): Q1 one-way sibling links are WARN, not ERROR (needs the TD-1 repair pass and TD-2 template symmetry first); Q2 nightly time `30 2 * * *` local, parked. Both are still `open` in `T-041-questions.toml`. TD-1 and TD-2 are open todos and follow-ups, not part of this build.

The console server on :8790 predates the `link-check` verb and does not list it until restarted; not touched, as instructed.

## Manual criteria run by the parent session (2026-10-06)

The three [MANUAL] acceptance criteria, run after the verifier's pass. **Not covered: a run at the real 02:30 time on the user's running console, and any check inside the desktop app.**

- **AC-34 PASS.** `python console/kanban.py vault links` on the real vault: the first screen is the ERROR lines, each with `path:line` and a plain fix hint, for example `ERROR map-status-drift artifact-map.md:8 / T-019 reads 'Open' but ticket.toml stage 'verify' means 'Verify'; update the row` and `ERROR links-dangling artifacts/CC-T004/CC-T004-decision-log.md:14 / [[CC-T004-analysis]] does not resolve to any .md file in the vault; fix the name or remove the link`. Run from a bash shell on Windows, not a native cmd window.
- **AC-35 PASS.** On a throwaway console (own port 18793, a scratch COPY of `console/` and `knowledge-center/` without `console/.cache`, never the user's running app on 8790), the `link-check-nightly` row was enabled with cron `* * * * *` in the copy only. After the ticker ran, `/api/jobs` showed a job with `submitted_by: schedule:link-check-nightly`, state `done`, started and finished within one second, and `result.ok` present (`false`) with `summary` {tickets 47, files 645, errors 34, warnings 1860} and the findings list. A first look made too early showed no job yet (the ticker interval is 30 s). The throwaway process was stopped and the copy deleted; the real `console/config/schedules.toml` row is still `enabled = false`, `30 2 * * *`.
- **AC-36 PASS.** `console/README.md` (section near line 544, split sentence near line 565 naming `validate-artifacts`) and `.claude/skills/console/SKILL.md:29` read correctly. `git diff` is empty for `console/server/export.py` and `console/server/vault.py`; the `console/static` files that differ (`about.js`, `app.js`, `core.js`, `overview.js`, `styles.css`) are T-039's, not T-041's (the criterion's literal "no change under `console/static/`" cannot hold in a tree with T-039's work; the check that holds is that T-041 added nothing there). `validate-artifacts` and `consolidate` skills are untouched.
- **Still open for the owner:** Q1 (one-way sibling links stay WARN) and Q2 (nightly time 02:30, parked); repairs TD-1 and TD-2 before unparking; the live console on :8790 must be restarted to list the `link-check` verb.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
