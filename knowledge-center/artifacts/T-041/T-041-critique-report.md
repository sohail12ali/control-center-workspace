---
ticket: "T-041"
artifact: critique-report
---

# Critique report: T-041

Run by the analyst as `challenge-requirements` (red-team plus gaps plus overlap/conflict/reuse), three passes. Pass 1 on draft v0, pass 2 on draft v2 after iteration 1, pass 3 on the freeze candidate. Gap detail is in [[T-041-gap-analysis]]; fixes are logged in [[T-041-iteration-log]].

## Requirements critique

**Last run:** 2026-10-06 (pass 3). Result: 0 critical, 0 major open; freeze gate clear.

| Pass | Critical | Major | Minor | Outcome |
|---|---|---|---|---|
| 1 (draft v0) | 2 | 5 | 7 | iterate |
| 2 (draft v2) | 0 | 0 | 5 | fixed inline |
| 3 (freeze candidate) | 0 | 0 | 0 | freeze |

### Pass 1

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | critical | contradiction | summary scope 1 vs spike | "No sibling link may be one-way" and "non-zero on any problem" make the nightly red on day one: 1,344 one-way pairs, 39 of 47 tickets incomplete, and templates create them (`_template/summary.md:19-20` vs `context-snapshot.md:79-80`) | resolved: severity split (D-4), `--strict`, TD-1, TD-2, Q1 |
| CR-2 | critical | gap (integration) | FR schedule | A verb that returns findings ends the job `done` and sends no notification (`console/server/jobs.py:268-297`), so a red nightly looks green | resolved: result carries `ok` (FR-12, D-11); surfacing it is [[T-040-summary]] |
| CR-3 | major | unstated-assumption | summary "reuse `_extract_wikilinks`" | Not reusable: bare regex, no code stripping (119 of 7,319 matches in code), ignores `[[#h]]`, no dangling report, text-extension index, inline in `build_graph` (`console/server/vault.py:17, 74-75, 117-147`) | resolved: own resolver (D-3), drift-guard AC-8 |
| CR-4 | major | ambiguity | "each wikilink must resolve" | Of 7,200 links, 32 prose links are dangling and 25 of those are the `[[…]]` template placeholder; failing the nightly on them is noise | resolved: Links blocks ERROR, prose WARN (FR-7) |
| CR-5 | major | untestable | known case "fused Links lines" | 0 fused headings in the current tree (repaired, `T-036-progress.md:292`); no real sample to test against | resolved: FR-6 defines the shapes, AC-13 uses planted fixtures; stated as fixture-only |
| CR-6 | major | gap (edge) | line endings | 8 BOM, 7 mixed, 1 lone CR files; a `$`-anchored heading regex misses them | resolved: NFR-5, AC-31 |
| CR-7 | major | gap (edge) | location | Vault is relocatable by `workspace.toml` (`console/server/paths.py:136-147`) | resolved: FR-1, AC-2 |
| CR-8 | minor | overlap | `validate-artifacts` | Manual skill covers the same rule plus traceability | resolved: split sentence in FR-14 |
| CR-9 | minor | conflict | CI | `harness lint` is a CI step; a link check would fail the template day one | resolved: not in CI (D-9) |
| CR-10 | minor | ambiguity | frozen files | Post-freeze edits go through `evolve`; frozen files hold most debt | resolved: not exempt, Links-only fix (D-8, FR-7) |
| CR-11 | minor | scope | artifact-map status drift | Is it in scope? | resolved: yes, ERROR (D-7, FR-5) |
| CR-12 | minor | gap (UX) | output volume | About 1,400 warnings bury 32 errors | resolved: cap and `--all` (FR-10) |
| CR-13 | minor | gap (compliance) | audit | Scheduled runs leave no audit line | accepted: read-only verb (D-11) |
| CR-14 | minor | spof | schedule | Console not running overnight means no run (`console/server/schedules.py:1-17`) | accepted: stated in FR-15 comment, Q2 |

### Pass 2

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-15 | minor | inconsistency | FR-1 vs FR-7 | FR-1 said prose-only for dossiers/wiki while FR-7 made their Links blocks errors | resolved: FR-1 reworded, FR-7 generalized to any scanned file |
| CR-16 | minor | untestable | AC-8 | `build_graph` skips self-links and indexes `.toml` | resolved: AC-8 limited to `.md`-only fixtures, self-links excluded |
| CR-17 | minor | ambiguity | FR-5 | Which tickets: any kind in `data_root` | resolved: kind `tickets` |
| CR-18 | minor | gap (edge) | FR-4 | `artifact-map.md` absent (post-`reset` state) was undefined | resolved: ERROR `map-missing` (20 codes) |
| CR-19 | minor | gap (edge) | FR-9 | `--ticket` for an unknown ticket was undefined | resolved: exit 2 |

### Pass 3
Re-read the frozen file end to end: every FR has at least one AC (traceability table), every NFR maps to an AC, codes in FR-9 (12 ERROR, 8 WARN) match AC-20, no contradiction between FR-1/FR-7/FR-8, no requirement invented beyond the summary scope and the caller's brief. No findings.

## Existing-feature interactions
- Overlap: 3 (`validate-artifacts` structure and links scopes; `vault.build_graph` basename edges; `harness_lint` shape).
- Conflict: 1 (CI day-one failure, avoided by D-9).
- Reuse: 5 (`Finding`/report shape, verb registry, `vault` CLI group, `tickets.list_tickets`/`paths.vault_dir`, `repo` fixture).

## Plan critique

**Last run:** 2026-10-06 (planner, 2 passes). Result: 0 critical, 0 major open; gate clear. Counts: 8 findings (0 critical, 1 major fixed, 7 minor: 5 fixed, 2 accepted). Rows CR-20 to CR-27 are in [[T-041-plan]] § Plan critique (kept in one place there); in short: AC-3 to AC-6 needed finding-level coverage in task 02 (fixed), critical path stated, `files` and the AC-35 tick defined, eol claim corrected, FR-14 versus the brief's `validate-artifacts` and `consolidate` text left to the parent (needs `evolve`), verb raises on exit-2 conditions (plan choice P-2).

## Residual risks (not blocking)
- R-1: day-one debt of about 32 errors and 1,344 warnings until TD-1/TD-2 are done.
- R-2: the nightly's red/green is only visible if the result is read (T-040) or the CLI is run.
- R-3: the `blocked` map row shape is unverified.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Related: [[T-040-summary]]
