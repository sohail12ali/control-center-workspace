---
ticket: "T-041"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
created: "2026-10-06"
last_updated: "2026-10-06"
---

# Requirements Draft: T-041

> Working document, now **frozen** into [[T-041-requirements]] (the canonical text of every FR, NFR and AC). This draft keeps the working context and does not repeat the requirement wording; change requirements only through `evolve` on the frozen file.

**Command reference:** created by `requirements draft`; grounded by [[T-041-context-snapshot]]; gaps in [[T-041-gap-analysis]]; challenged in [[T-041-critique-report]]; history in [[T-041-iteration-log]]; decisions in [[T-041-decision-log]].

**Legend:** a warning marker means a challenge finding; each is resolved below.

---

## 1. Intent

**Stakeholder (one line):** Sohail Ali wants signposts that cannot silently go stale.

**Business driver:** the MAPS video's "the map can't go stale" and "every fact has one home", and real drift found while building T-031..T-037 (stale map rows, one-way and fused Links blocks).

**Raw intent verbatim:**
> A link/signpost checker over `knowledge-center/artifact-map.md` rows and every ticket's `## Links` block: each wikilink must resolve to a file, each artifact must have a Links block, and no sibling link may be one-way. One command, non-zero exit on any problem, human-readable output. ... Register it as a routine in `console/config/schedules.toml`, parked until the user unparks it (like the existing `harness-lint` entry). ... A one-home check is only in scope if it can be made deterministic. ([[T-041-summary]])

## 2. Context Summary

(Condensed from [[T-041-context-snapshot]])

- **Similar existing features:** `harness lint` (`console/server/harness_lint.py`), `workspace check`, the Vault graph (`console/server/vault.py`), the `validate-artifacts` skill.
- **Affected code areas:** new `console/server/link_check.py`; one row each in `console/config/verbs.toml` and `schedules.toml`; a handler in `console/server/verb_handlers.py`; a command in `console/kanban.py`; README and console SKILL docs.
- **Known risks from history:** stale map rows today (T-019, T-036, T-037); an Edit anchored on the Links heading fused progress entries (`T-036-progress.md:292`).

## 3. Scope

### In scope
- Resolution of links, Links-block form and sibling reciprocity per ticket; artifact-map rows against `ticket.toml`; deterministic one-home subset; CLI, verb, parked schedule row, docs.

### Out of scope (explicit)
- See the Out of Scope section of [[T-041-requirements]] (UI and other tickets, prose duplication, repair, anchors, CI, notifications).

### Assumptions
- The nightly only runs while the console is up (`console/server/schedules.py:1-17`): accepted, stated, Q2.
- One-way pairs are WARN by default until the vault and templates are repaired: Q1, user-adjustable.

## 4. Functional Requirements

Canonical text: FR-1 to FR-15 in [[T-041-requirements]]. Index:

| FR | Subject | Key rule |
|---|---|---|
| FR-1 | Scan scope | `.md` under the vault; ticket rules for `{T}-*.md` only; templates, `_shared`, `ticket-scripts` exempt |
| FR-2 | Extraction | `[[x]]`, alias, anchor; code ignored; no cross-line swallow |
| FR-3 | Resolution | basename, case-sensitive, `.md` only, lenient forms warn |
| FR-4 | Map rows | row format, dangling or unknown target, missing map |
| FR-5 | Map vs `ticket.toml` | missing, duplicate, status, section, title |
| FR-6 | Links block form | missing, duplicate, malformed (fused), not last |
| FR-7 | Link targets | Links-block dangling ERROR, prose dangling WARN, frozen not exempt |
| FR-8 | Siblings | one-way, incomplete (WARN) |
| FR-9 | Severity and exit | 12 ERROR and 8 WARN codes; exit 0, 1, 2 |
| FR-10 | Output | text capped warnings, `--json`, ASCII, ordering |
| FR-11 | CLI | `vault links` |
| FR-12 | Verb | `link-check`, `ok`, `--ticket` scope |
| FR-13 | One home | unique basenames, artifact prefix equals folder |
| FR-14 | Docs | README, console SKILL, validate-artifacts split |
| FR-15 | Schedule | `link-check-nightly`, parked |

## 5. Non-Functional Requirements

Canonical text: NFR-1 to NFR-10 in [[T-041-requirements]]: stdlib only, read-only, deterministic, under 5 s on the real vault, CRLF/LF/BOM safe, contained to the vault, testable with tmp workspaces, no UI or static-export impact, robust to bad files, ASCII output.

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Finding | new, in memory | level, code, path, line, message | per run, never stored | shape of `harness_lint.Finding` (`harness_lint.py:56-71`) |
| Schedule row `link-check-nightly` | new | id, label, expr, verb, enabled | static config | `console/config/schedules.toml:25-37` |
| Verb `link-check` | new | id, label, hint, handler | static config | `console/config/verbs.toml:66-70` |

### Data flows
Vault files and `ticket.toml` (read) to findings (memory) to text, JSON or verb result. Nothing is written.

### Retention / archival
None. A scheduled run's result lives in the job record (`console/.cache/jobs`, `jobs.py:49`), owned by the job queue.

## 7. Business Rules

- **BR-1:** a signpost is a wikilink in an artifact-map row or a Links block; it must resolve, or the file is broken.
- **BR-2:** `ticket.toml` is the truth; `artifact-map.md` is derived and must agree with it.
- **BR-3:** filenames are globally unique and carry their ticket prefix (`consolidate/SKILL.md:47`).
- **BR-4:** every ticket artifact ends with a Links block listing its siblings (`consolidate/SKILL.md:50`); a sibling link is reciprocal.
- **BR-5:** the checker reports; it never repairs.

## 8. Edge Cases

- Links in code, `[[#h]]`, unclosed `[[`, aliases: FR-2. Case differences: FR-3. BOM, mixed endings, lone CR: NFR-5. Missing map: FR-4. Unknown `--ticket`: FR-9. Symlinks: NFR-6. Relocated vault: FR-1.

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| `harness lint` ([[T-041-analysis]]) | reuse shape | low | copy the pattern, import `Finding` |
| `vault.build_graph` | overlap (basename rule) | med | drift-guard test AC-8, do not edit `vault.py` |
| `validate-artifacts` skill | overlap | low | document the split (FR-14) |
| CI harness-lint step | conflict if added | med | not in CI (D-9) |
| Job queue and notifications | integration | med | result `ok` (FR-12, D-11) |
| [[T-040-summary]] routines board | consumer | low | shows the new row and last-run automatically |
| [[T-039-summary]] Needs-you panel, [[T-038-summary]] brain views | none | low | out of scope |

## 10. External Dependencies

- None. No network, no new package.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner and sole user | Sohail Ali | a trustworthy nightly signal, no day-one noise | yes (APPROVED at the freeze gate, pending) |
| Agents (verifier, fixer) | harness roles | run per ticket, read `ok` | no |

## 12. Open Questions (mirrored)

Mirrored from `T-041-questions.toml`. Neither blocks the freeze (priority low, defaults taken).

- Q1: one-way pairs ERROR from the start, or WARN by default? Default WARN (D-4). Status: open.
- Q2: nightly time. Default `30 2 * * *`, parked (D-9). Status: open.

## 13. Challenge Findings

19 findings across three passes, all resolved or accepted (CR-13, CR-14 accepted); see [[T-041-critique-report]].

## 14. Draft History

See [[T-041-iteration-log]]. Current iteration: **1**. Frozen 2026-10-06.

---

## Freeze Checklist (run by `requirements freeze`)
- [x] All placeholders replaced (no TBD left)
- [x] All challenge findings resolved or accepted with rationale (CR-1 to CR-19)
- [x] No blocker open question (Q1, Q2 are low-priority defaults)
- [x] Every FR has at least one testable acceptance criterion (traceability table in [[T-041-requirements]])
- [x] Every NFR has a concrete target or maps to an AC
- [x] New entities have a reference (section 6)
- [x] Out-of-scope list is non-empty
- [ ] Stakeholder sign-off recorded: not yet; the freeze was requested by the launching agent, the user's APPROVED is pending
- [ ] `T-041-requirements-summary.md`: not generated; [[T-041-requirements]] is the single canonical text and `requirements stories` reads it directly (deferred, noted in [[T-041-iteration-log]])

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Related: [[T-040-summary]] · [[T-039-summary]] · [[T-038-summary]]
