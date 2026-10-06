---
ticket: "T-041"
artifact: gap-analysis
status: resolved
created: "2026-10-06"
last_updated: "2026-10-06"
---

# Gap Analysis: T-041

**Sources:** [[T-041-requirements-draft]] · [[T-041-context-snapshot]]

Legend: red = blocks freeze unless resolved, yellow = should be resolved, green = note. Every gap below is resolved in the frozen [[T-041-requirements]]; none is open.

## Summary

| Category        | Red | Yellow | Green | Total |
|-----------------|-----|--------|-------|-------|
| Stakeholders    | 0   | 1      | 0     | 1     |
| Business rules  | 1   | 1      | 1     | 3     |
| Edge cases      | 1   | 3      | 0     | 4     |
| NFRs            | 0   | 1      | 0     | 1     |
| Data / entities | 0   | 1      | 0     | 1     |
| Integrations    | 1   | 1      | 0     | 2     |
| UX / UI         | 0   | 1      | 0     | 1     |
| Compliance      | 0   | 0      | 1     | 1     |
| Cross-cutting   | 0   | 1      | 0     | 1     |
| **Total**       | **3** | **10** | **2** | **15** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-06 | all | Initial pass from `challenge-requirements` (gaps) on draft v0 | analyst |
| 2026-10-06 | G-2, G-5, G-11 | Resolved in iteration 1: severity split (D-4), NFR-5, FR-12 | analyst |
| 2026-10-06 | G-1, G-3, G-6..G-10, G-12, G-13, G-15 | Resolved in iteration 1 (FR/NFR cited per row) | analyst |
| 2026-10-06 | G-4, G-14 | Accepted as notes (stated in FR-5 and D-11) | analyst |

---

## Stakeholders
- **G-1 (yellow)** The routines board ([[T-040-summary]]) will show the nightly's last-run status; it can only do that if the verb result says pass or fail. Resolved: FR-12 `ok` and `summary` in the result.

## Business rules
- **G-2 (red)** "No sibling link may be one-way" plus "non-zero on any problem" contradicts the spike: 1,344 one-way pairs, 39 of 47 tickets with omitted siblings, and templates that create them (`_template/summary.md:19-20` vs `context-snapshot.md:79-80`). Resolved: D-4 and FR-8/FR-9 (WARN by default, `--strict`, Q1), follow-ups TD-1/TD-2.
- **G-3 (yellow)** Are frozen files exempt? They hold most of the debt and post-freeze edits go through `evolve`. Resolved: FR-7 not exempt, Links-block-only fix (precedent `T-036-progress.md:36`).
- **G-4 (green)** The `blocked` map label and section are assumed, not observed (no blocked ticket). Noted in FR-5.

## Edge cases
- **G-5 (red)** Byte-level: 8 BOM files, 7 mixed endings, 1 lone CR, CRLF working tree over LF index (spike). A `^## Links$` regex without normalization misses them. Resolved: NFR-5, AC-31.
- **G-6 (yellow)** Links in code spans or fences (119 of 7,319 matches) and unclosed `[[`. Resolved: FR-2, AC-3, AC-4.
- **G-7 (yellow)** Case-insensitive filesystems accept `[[t-041-summary]]` in Windows but Obsidian on Linux does not. Resolved: FR-3 case-sensitive, message names case difference, AC-5.
- **G-8 (yellow)** Symlinks or junctions leading outside the vault; `[[../../CLAUDE.md]]`. Resolved: NFR-6, FR-3, AC-6, AC-32.

## Non-functional requirements
- **G-9 (yellow)** No stated performance budget. Resolved: NFR-4 (prototype 0.2 to 0.6 s on 656 files).

## Data / entities
- **G-10 (yellow)** `artifact-map.md` holds 4 convention bullets that look like rows to a loose parser. Resolved: a row is a bullet starting `- [[` (FR-4), AC-9.

## Integrations
- **G-11 (red)** A verb that returns findings still ends the job `done` and pushes nothing (`console/server/jobs.py:268-297`); the nightly would look green. Resolved: result carries `ok` (FR-12, D-11); surfacing it is T-040.
- **G-12 (yellow)** The vault can be relocated by `workspace.toml` (`console/server/paths.py:136-147`). Resolved: FR-1, AC-2.

## UX / UI
- **G-13 (yellow)** Around 1,400 day-one warnings would bury about 32 errors. Resolved: FR-10 cap and `--all`, errors never capped, AC-22.

## Compliance / audit
- **G-14 (green)** Scheduled runs write a job record but no audit line (`schedules.py:223-227`, `jobs.py`); HTTP runs audit (`features/verbs_feature.py:41-47`). Accepted; read-only verb.

## Cross-cutting
- **G-15 (yellow)** `harness lint` runs in CI (`.github/workflows` line 69); the link check would fail day one. Resolved: D-9, not in CI.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Related: [[T-040-summary]]
