---
ticket: "T-039"
artifact: critique-report
---

# Critique report: T-039

Scaffolded on first use per `.claude/skills/challenge-standards/rules.md` (no `_template/critique-report.md` exists; [[T-037-critique-report]] was the shape reference).

## Requirements critique

**Last run:** 2026-10-06 · `challenge-requirements` pass 2 (after iteration 1): 0 new material findings. Pass 1 raised CR-1..CR-16 on draft v0 (closed in iteration 1; CR-16 accepted). Pass 2 re-read the frozen text for traceability (every FR has an AC, every AC cites a tag), cross-reference accuracy (ids, counts, line numbers) and contradictions; it found one wording fix, applied inline and logged in [[T-039-iteration-log]] (FR-7 "byte-identical" changed to "structurally identical" to match AC-7.1). No pass 3 needed.

| Severity | Count |
|---|---|
| critical | 0 |
| major | 9 |
| minor | 7 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | major | unstated-assumption | draft FR-3 / G4 | The existing cap of 8 would hide a human-only item (9 open questions today) | resolved: FR-3 cap 50, D-7 |
| CR-2 | major | unrealistic-constraint | draft FR-12 / G5 | A tick driven by the heartbeat never runs while the server is down (`app.js:439-441`) | resolved: own 30 s clock, D-8, AC-8.4 |
| CR-3 | major | unstated-assumption | draft FR-7 / G6 | A footer mark disappears when the panel is collapsed (`styles.css:522`) | resolved: chip in header, D-12, AC-7.3 |
| CR-4 | major | untestable | draft FR-2 / G3 | "The agent never marks an item done" cannot be proved system-wide (CLI can set a status) | resolved: scoped to the Overview, AC-2.1..2.4, limit in D-15 |
| CR-5 | major | contradiction | draft FR-5 / G13 | `test_splitter.py:1118-1160` pins six `ov.*` ids, 18 overall and the `attnPanel` handler | resolved: D-16, NFR-8, AC-5.1 |
| CR-6 | major | overlap | draft FR-1 / G2 | A `review_escalated` entry would list one wait three times (question, approval, flag) | resolved: no review kind, D-2 |
| CR-7 | major | contradiction | draft FR-1 vs summary / G2 | Summary lists "answered" questions as human-only; the status model says the person already answered | resolved: D-3, Q1 raised (non-blocking) |
| CR-8 | major | unstated-assumption | draft FR-1 / G12,G14 | Changing keys breaks `assistant.js:123`, the export and the CLI | resolved: additive payload, D-6, AC-1.4 |
| CR-9 | major | untestable | draft FR-14 / G11 | No viewport or measurement for mobile | resolved: AC-14.1 at 400 px with scrollWidth check |
| CR-10 | minor | ambiguity | draft FR-7 / G9 | "STALE" already names ticket idleness | resolved: D-9 distinct element and title |
| CR-11 | minor | unstated-assumption | draft FR-6 | Badge stops lighting for repair-only items | accepted: D-5, Q2 raised (non-blocking) |
| CR-12 | minor | unstated-assumption | draft FR-8 / G8 | Client fetch time would read "just now" in an old export | resolved: server `generated_at`, D-10, FR-11 |
| CR-13 | minor | ambiguity | draft FR-7 / G8 | Future or unparsable `asOf` | resolved: clamp 0; unparsable is stale; AC-7.2 |
| CR-14 | minor | ambiguity | draft FR-13 / G10 | Per-tick text rewrite causes screen-reader chatter | resolved: rewrite only on change, constant-text status chip |
| CR-15 | minor | untestable | draft AC split | No JS runner: freshness math not [PY]-testable | resolved: source checks [PY] plus optional skip-if-absent node test; rest [BROWSER] (stated) |
| CR-16 | minor | scope-creep | draft FR-1 | Run state `needs-approval` (`runs.py:20`, `run_sync.py:184`) is not emitted | accepted: the approval card already covers it; out of scope, noted as a lead |

## Plan critique

**Last run:** 2026-10-06 · `challenge-plan` two passes: 10 findings (PC-1 critical, 4 major, 5 minor), all fixed in [[T-039-plan]]; pass 2 found nothing new. Detail and resolutions are in the plan's "Plan critique" section. Open for the parent: PC-1 (`evolve` the NFR-8 exception for `test_prefs_client_source.py:202`) and PC-2 (AC-5.1 wording).

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
