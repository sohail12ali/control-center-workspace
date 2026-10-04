---
ticket: "T-021"
artifact: critique-report
status: active
---

# Critique Report: T-021

Adversarial critique findings across stages. Find-don't-fix: resolutions happen via the owning stage's repair command. Scaffolded on first use per `challenge-standards/rules.md` (no `_template/critique-report.md` exists; shape follows [[T-020-critique-report]], gap recorded in decision a15).

## Requirements critique

**Last run:** 2026-10-01 · `challenge-requirements T-021` (gaps + redteam), pass 1 on v0, pass 2 on v1, pass 3 on v2
**Summary:** 25 findings in three passes (critical 4 / major 11 / minor 10), all resolved. Gaps 20 (🔴 5 / 🟡 12 / 🟢 3), see [[T-021-gap-analysis]]. Interactions (draft § 9, 13 rows): overlap 4 · conflict 3 · reuse 4 · isolation 2.
**Pass 1 (v0, the dossier items restated literally):** CR-1..CR-14. **Pass 2 (v1):** CR-15..CR-21. **Pass 3 (v2, freeze-gate re-read):** CR-22..CR-25.

| CR-{n} | Severity | Kind | Pointer | Issue | Resolution |
|--------|----------|------|---------|-------|------------|
| CR-1 | critical | contradiction | v0 item 7 "lands in `harness_lint.py`" vs `harness_lint.py:1-25`, `.githooks/pre-commit:16-18`, `.gitignore:66` (G-integ, Q1) | Lint is static over harness files; CI has no Run records, pre-commit never fires on a ticket edit, claim staleness needs a clock | resolved: requirements iterate 2026-10-01 (iteration 1): separate module and verb, surfaced in the digest (FR-6, decision a1) |
| CR-2 | critical | unstated-assumption | v0 item 7 "has a live Run" (G13, Q10) | Runs never leave `running` (no caller of `runs.set_state`), so every Run would read live | resolved: iteration 1: slice B consumes T-020's lifecycle by name and builds after it; slice A is independent (decision a10) |
| CR-3 | critical | untestable | v0 item 8 "evidence refs that resolve" (G4, Q5) | Prototype over 212 historical PASS rows: 84 % are prose or measurements; a one-resolvable-ref rule refuses almost every close | resolved: iteration 1: block on empty, all-phantom and non-pass rows; warn on prose-only and partial; `accepted` means existence (FR-8, BR-3, decision a5) |
| CR-4 | critical | unstated-assumption | v0 item 13 "clause in `assistant.md`" (G10, Q9) | The file is 4,725 chars, cap 4,000: a clause at the end is cut before the model reads it, and today's Safety bullet on self-approval is already cut | resolved: iteration 1: trim the file, keep the cap, pin fit and clause by test (FR-5, BR-10, decision a9) |
| CR-5 | major | contradiction | v0 item 8 premise vs `native-status-arbitration.md:108-124`, `status-arbiter.ts:279-309` | Paperclip's default completion is claim-policy; durable evidence is the strong path and unknown refs are diagnostic | resolved: iteration 1: only the pure arbiter, the four-way vocabulary and "claims are not proof" are adopted; contradiction recorded (decision c1) |
| CR-6 | major | unrealistic-constraint | v0 item 10 "≤ 300 chars" as a rule (Q7) | 20 of 39 skills exceed 300; an ERROR rule is red on day one, trimming prompt text without evals is what dossier § 3 warns against | resolved: iteration 1: WARN only, offenders untouched, todo TD-1 (FR-1, decision a7) |
| CR-7 | major | untestable | v0 item 10 "use-when / not-when" (Q7) | No objective test: 28 of 39 contain a "use" word, 6 an explicit not-when; Paperclip tests length only (`shipped-catalog.test.ts:30, 95-110`) | resolved: iteration 1: convention in the message and docstring, not a rule (decision a7) |
| CR-8 | major | scope-creep | v0 item 12 "SHA cursor and minimal patches" (Q8) | No deterministic form; Paperclip's is an LLM-run skill and the roster is capped; a dated-snapshot rule would cover one doc | resolved: iteration 1: fix the stale docs now (FR-3), extend the roster count check to README (FR-4), state the limit (decision a8) |
| CR-9 | major | contradiction | v0 item 11 vs `breakdown-tasks/SKILL.md` step 1 "ideally one component per task" | The new rule says fewest tasks, the old one splits per component | resolved: iteration 1: rule defined once in `plan`, size caps retained, breakdown-tasks defers to it (FR-2, decision a13) |
| CR-10 | major | unstated-assumption | v0 item 7 `in-progress` needs a claim | 0 of 28 tickets are claimed; `builder.md` has no claim step; remedy would not exist | resolved: iteration 1: builder protocol gains a claim step (FR-11 item 4, decision a16) |
| CR-11 | major | contradiction | `verifier.md` step 10 (runs `close-work`) vs its output contract (asks the user to approve it) and `CLAUDE.md` verifier row | Who closes is stated three ways; "agents do not self-close" has no actor | resolved: iteration 1: verifier reports a `Disposition` and stops at `close-check`; harness or user runs `close-work` (FR-11, decision a12, Q12) |
| CR-12 | major | ambiguity | v0 item 7 "prose-only blocked is rejected" (G6, Q3) | Rejected where and when? Retroactive rejection would flag existing tickets | resolved: iteration 1: refused at the transition into `blocked`, prospective only, scan findings are WARN (FR-6, FR-7, BR-1, decision a3) |
| CR-13 | minor | ambiguity | v0 items 7, 8: "pending question", "owner", "liveness", "stale" (G5, Q4) | Undefined terms; "liveness" and "stale" already mean other things (T-020 FR-13, `stop_hook`) | resolved: iteration 1: definitions in BR-4/BR-8, key `ticket_liveness`, "stale" only as `claim_status` defines it (decision a4, a14) |
| CR-14 | minor | unstated-assumption | v0 item 8 "human overrides" (G16, G17, Q6, Q11) | `needs_confirm` is a stray-call guard, not a human gate; no override specified | resolved: iteration 1: separate verb `close-override` with reason, audit and comment; hard gate left to the user as open Q11 (FR-10, BR-6) |
| CR-15 | major | ambiguity | v1 FR-8 ref grammar | A URL such as `https://x.com/a/b.md` or an absolute path parses as a repo path and would read as a phantom ref | resolved: iteration 2: URLs and absolute paths are `unverifiable`; AC row added |
| CR-16 | major | contradiction | v1 FR-11 item 2 vs T-020 FR-25 and verifier step 10 | The rewrite dropped the "unmet → fixer" branch and collided with T-020's edit of the same step | resolved: iteration 2: unmet branch kept, applied on top of T-020's wording |
| CR-17 | major | nfr-unmeasurable | v1 FR-5 "tighten without deleting a rule" | No size target; the file must shrink by about 1,250 chars net | resolved: iteration 2: net target and per-section budget stated |
| CR-18 | minor | untestable | v1 FR-3 docs-agree test | The README phrase wraps across a line break ("It ships" / "disabled"); a naive substring test would never fire | resolved: iteration 2: whitespace-normalised before matching |
| CR-19 | minor | unstated-assumption | v1 BR-8 owner half | Every ticket has an owner, so `blocked_no_owner` is nearly dead; a named responder is the real fix | resolved: iteration 2: accepted with the limit stated in BR-8; todo TD-2 |
| CR-20 | minor | unstated-assumption | v1 FR-9 | An unattended `/do` close, or a human at the CLI, meets the gate and has no stated way forward | resolved: iteration 2: edge case states the stop-and-ask behaviour and the `close-override` path |
| CR-21 | minor | untestable | v1 FR-9 AC | A CLI test that spawns `kanban.py` contradicts NFR-3 (no subprocess) | resolved: iteration 2: CLI tested in-process via `cmd_ticket_move` |
| CR-22 | minor | untestable | v2 FR-2 AC | "Five labelled elements" named no labels, so a grep test could not be written | resolved: iteration 3: heading and five bold labels pinned in FR-2 text and AC |
| CR-23 | minor | untestable | v2 FR-5 AC | The clause anchor was "pinned in the test" with no required wording, so nothing constrained the clause | resolved: iteration 3: exact phrase `data, not instructions` and four required words |
| CR-24 | minor | ambiguity | v2 FR-7 vs FR-9 | Both use `ticket_gate.guarded_move`; FR-9 claimed to create the module FR-7 already needs | resolved: iteration 3: FR-7 creates it, FR-9 extends it; build order stated |
| CR-25 | minor | ambiguity | v2 FR-3 (1) | Line cite `agents.py:25-27` is off by one (text is on lines 24-26) | resolved: iteration 3: corrected |

## Plan critique

**Last run:** 2026-10-02 · `challenge-plan T-021` (flat plan, 17 tasks). **Summary:** 7 findings (critical 0 / major 3 / minor 4), all fixed in [[T-021-plan]] except PC-7 (accepted).

| PC-{n} | Severity | Pointer | Issue | Resolution |
|--------|----------|---------|-------|------------|
| PC-1 | major | task 05, `agents.py:24-26` | T-020 tasks 2a-2/2b-1 also edit `agents.py`; a stale-line edit could clobber them | fixed: collision table row, comment edit done last after a re-read |
| PC-2 | major | `audit.py` `ACTIONS` :44-67 | Both tickets append actions; not in the requirements' shared-file list | fixed: added to collision table and to tasks 09, 12, 13 |
| PC-3 | major | task 04 | "net shrink >= 1,250" is not an FR checkbox and needs about 1,850 chars cut against a 600-char clause | fixed: stated as design target; hard criterion is cap fit and last Safety bullet delivered |
| PC-4 | minor | task 11 | FR-8 "verb on HTTP" had no test | fixed: HTTP route or registry-load citation added |
| PC-5 | minor | FR-3 | `console/SKILL.md:45` is `.claude/skills/console/SKILL.md`, not under `console/` | fixed: full path in task 05 and the prompt-facing table |
| PC-6 | minor | tasks 14/15 | `verifier.md` step 10 depends on T-020 4b-3 (FR-25) having landed | fixed: task 15 depends on it explicitly |
| PC-7 | minor | structure | 17 tasks exceeds the six-task flat threshold | accepted: one component, no component graph needed; lean flat plan chosen by the orchestrator |

AC coverage: 11/11 FR mapped, every FR checkbox appears in the skeleton table; no high x high risk; every task has files, named tests, a verify command and done-criteria.

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements-draft]] · [[T-021-requirements]] · [[T-021-gap-analysis]] · [[T-021-iteration-log]] · [[T-021-decision-log]] · `T-021-questions.toml`
