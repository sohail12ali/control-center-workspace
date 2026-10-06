---
ticket: "T-041"
artifact: decision-log
---

# Decisions: T-041

Dated 2026-10-06, taken by the analyst. "User-adjustable" means a default the user may override at any time, before or after build; none blocks the freeze. Open questions are tracked in `T-041-questions.toml` (Q1, Q2).

## D-1 where-it-lives
**Decision:** New module `console/server/link_check.py`, shaped like `harness_lint.py` (`Finding` imported from it, or the same four fields; `check(repo_root, ticket=None)` returning `(findings, summary)`; `format_report`). Verb `link-check` in `console/config/verbs.toml`, handler `verb_handlers.link_check_verb`. CLI `kanban vault links`, in the existing `vault` group.
**Rationale:** the harness-lint pattern already gives CLI, HTTP, MCP and agent-tool exposure from one registry row (`mcp.py:11-15`, `agent_tools.py:339-358`). `vault` is where the other vault commands live (`kanban.py:826-838`).
**Impact:** FR-11, FR-12. `vault.py` is not edited (T-038 may touch it).

## D-2 link-forms-that-count
**Decision:** Obsidian wikilinks only: `[[x]]`, `[[x|alias]]`, `[[x#h]]`, `[[x#h|alias]]`. Relative markdown links `[t](path)` are not checked.
**Rationale:** `consolidate/SKILL.md:46-51` makes the wikilink the convention and the vault graph only reads wikilinks (`vault.py:17`). No markdown-path convention exists to check against.
**Impact:** FR-2, Out of Scope.

## D-3 resolution-rule
**Decision:** Own extractor and resolver in `link_check.py`: bare basename without extension, case-sensitive, against `.md` files across the whole vault. Lenient with `.md` suffix and folder prefix (WARN `link-form`); `.toml` and `..` targets unresolved. A drift-guard test compares the pairs with `vault.build_graph` edges.
**Rationale:** the vault regex is not reusable as the summary assumed (strips no code, no dangling report, text-extension index, `vault.py:17, 74-75, 117-147`). Copying 3 lines of rule plus a guard test is cheaper than refactoring `vault.py`.
**Impact:** FR-2, FR-3, AC-8.

## D-4 severity-split (user-adjustable, Q1)
**Decision:** ERROR for broken signposts (dangling Links or map targets, missing or malformed Links block, map-versus-ticket drift). WARN for hygiene (one-way, incomplete sibling list, prose links, link form, ambiguous basename, misplaced file, row format). One-way pairs are WARN by default.
**Rationale:** spike: 1,344 one-way pairs and 3,578 omitted sibling edges across 39 of 47 tickets, partly because fresh templates are one-way by construction (`_template/summary.md:19-20` vs `context-snapshot.md:79-80`). As an ERROR the nightly is red on day one for reasons nobody can fix in a night, and the errors that matter get lost, the failure mode `harness_lint.py:9-18` warns about. The user's literal ask ("no sibling link may be one-way", non-zero on any problem) is met by `--strict`, and by flipping the code to ERROR once TD-1 and TD-2 are done.
**Impact:** FR-8, FR-9. Rejected: baseline file of known debt (a second file to maintain, hides regressions in old tickets); scoping the rule to non-done tickets (fresh scaffolds still fail).

## D-5 exit-code-contract
**Decision:** 0 no errors; 1 any error, or any warning with `--strict`; 2 could not run. Same as `kanban harness lint` plus the exit 2 for a missing vault.
**Rationale:** `kanban.py:372-375`; a check that silently passes because the vault moved is worse than none.
**Impact:** FR-9, AC-19.

## D-6 output-format
**Decision:** Text like `harness_lint.format_report` (errors then warnings, one summary line, ASCII), warnings capped at 20 per code with `--all`; `--json` as `{summary, findings}` with an added `line` field (cheap, so included).
**Rationale:** 1,344 warnings would bury the 32 errors in a terminal. JSON is uncapped for tools.
**Impact:** FR-10.

## D-7 artifact-map-vs-ticket-toml-in-scope
**Decision:** In scope, ERROR: missing row, duplicate row, stage-versus-status label, stage-versus-section, title drift. Owner and date not compared.
**Rationale:** deterministic from `ticket.toml`, the machine truth; hit today (T-019, T-036, T-037 read "Open" while in `verify`, spike) and earlier ([[T-032-verification]] line 87). The nightly runs when work is quiescent, so in-flight lag is rare.
**Impact:** FR-4, FR-5. The `blocked` row label is an unverified assumption.

## D-8 exemptions
**Decision:** Code fences and spans ignored. `_template/` not link-checked (placeholders), but in the resolution index. `_shared/` and `ticket-scripts/` exempt from Links and sibling rules (`consolidate/SKILL.md:30-33`). Frozen files not exempt: the fix is a Links-block-only edit, which has precedent (`T-036-progress.md:36`). Investigations, wiki, docs and logs: link resolution only (Links-block dangling is ERROR, prose dangling is WARN); no Links-block or sibling rule.
**Rationale:** frozen artifacts carry most of the debt, so exempting them would hide it; a nightly check cannot know which prose placeholder is intentional, so prose is WARN.
**Impact:** FR-1, FR-2, FR-7.

## D-9 schedule-and-parked (user-adjustable, Q2)
**Decision:** Row `link-check-nightly`, `30 2 * * *` local, `enabled = false`, no `confirm`. Not added to CI. Unpark after the repair pass (TD-1: about 32 errors) so the first red night means something new.
**Rationale:** template convention for useful read-only jobs (`schedules.toml:21-23`); the console is the clock and skips missed firings, so a 02:30 run only happens if the console is up overnight (`schedules.py:1-17`). CI runs `harness lint` (`.github/workflows` line 69) but a link check would fail day one.
**Impact:** FR-15, AC-26.

## D-10 one-home-check
**Decision:** Only the deterministic subset: unique basenames (`ambiguous-basename`) and artifact filename prefix equals its folder (`misplaced-artifact`). No prose, heading or content duplication detection.
**Rationale:** the ticket allows it only if deterministic; today both checks find 0 (spike), so they are guards, not clean-up work.
**Impact:** FR-13.

## D-11 verb-result-not-failure
**Decision:** The verb returns `{ok, summary, findings}` and does not raise on findings. A nightly with errors is a `done` job whose result has `ok: false`; no push notification. Scheduled runs leave a job record, not an audit line (HTTP runs do audit).
**Rationale:** `jobs.py:268-297` notifies only on an exception, and raising would drop the findings from the result. Surfacing `ok` on the routines board is T-040's job.
**Impact:** FR-12, AC-24, AC-35. Risk R-2 in the critique report.

## D-12 performance-and-export
**Decision:** Budget under 5 s on the real vault (prototype 0.2 to 0.6 s), under 10 s for 2,000 files. No static-export impact (`export.py` has no verb or schedule reference; no UI).
**Impact:** NFR-4, NFR-8.

## D-13 ticket-scoping
**Decision:** Optional `ticket` argument (verb) and `--ticket` (CLI) limit findings to one ticket's artifacts and its map row, so a verifier can run it per ticket as `validate-artifacts` does.
**Rationale:** the verb handler already receives `ticket`; a few lines of filtering.
**Impact:** FR-11, FR-12, AC-23, AC-24.

## Links
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
- Cross-ticket: [[T-032-verification]]
