---
ticket: "T-021"
artifact: decision-log
---

# Decisions: T-021

> Every decision below was **decided under delegated authority 2026-10-01, reversible**: the owner said "go wild, do end to end", so the analyst chose the safest minimal default. No user answer is implied or invented. Each links to its tracker question (`T-021-questions.toml`). Reverting one means a `requirements` evolve, not a silent edit.

## a1-liveness-is-a-ticket-state-check (Q1)
**Decision:** Item 7 is a separate module (`ticket_liveness.py`) and read-only verb `ticket-liveness`, surfaced as a `ticket_liveness` line in `console context`. It is not a harness lint rule.
**Context:** `harness_lint.py:1-25` scopes lint to static harness files; CI is a shallow checkout with no `console/.cache/runs/` (`.gitignore:66`); pre-commit only runs on `.claude/(skills|agents)/` or `CLAUDE.md` paths (`.githooks/pre-commit:16-18`); claim staleness needs a clock.
**Alternatives:** a lint rule (rejected: every Run-linked claim reads `run_missing` in CI); a Stop hook (rejected: holder-side only, already exists as `stop_hook`).
**Impact:** FR-6.

## a2-lanes-covered (Q2)
**Decision:** `kind=tickets` only; `open` and terminal lanes exempt; `in-progress` and `verify` need one path; `blocked` has its own rule. The human `owner` is not a path.
**Rationale:** Paperclip's `backlog`/`todo` carry no execution expectation (`execution-semantics.md:36-50`); Paperclip counts a human owner as a path, but every ticket here has one, so the check would be vacuous. Today's vault: T-015, T-016, T-019 sit in `verify` with no path, which is exactly what the check should surface.
**Impact:** FR-6, BR-4, BR-5.

## a3-severity-and-rejection-point (Q3)
**Decision:** Scan findings are WARN-level, report-only. Prose-only `blocked` is refused at the transition into `blocked` (verb and CLI), prospective only. No override for `blocked`.
**Rationale:** Paperclip's rule applies to transitions after rollout and leaves already-blocked issues untouched (`execution-semantics.md:83`; `routable-blocked.ts:3, 18-21`). The vault has 0 blocked tickets, so nothing existing is affected. The remedy (add a question) is always available, so an override would only add a bypass.
**Impact:** FR-6, FR-7, BR-1, BR-7.

## a4-definitions (Q4)
**Decision:** Pending question = status `open` or `answered`, any priority (`clarify/question-templates.md` lifecycle). A `blocked` ticket is routable iff it has a pending question or an open critical bug (`trackers.blockers`) and an owner (claim holder if held, else the ticket `owner`, standing in for Paperclip's board owner). The action is the item's text.
**Limit:** the owner half is nearly always satisfied; todo TD-2 proposes a named-responder field.
**Impact:** FR-6, FR-7, BR-4, BR-8.

## a5-evidence-classes (Q5)
**Decision:** `close-check` blocks on: no verification table, a non-pass row, a pass row with empty evidence, a pass row whose refs are all phantom, open critical questions or bugs, a stale claim, an escalated review, unchecked plan tasks. It warns on prose-only and partial evidence, descoped rows and a held claim. `accepted` means the file, test name or Run exists, never that the claim is true.
**Context (measured, prototype in the session scratchpad over 24 historical verification files):** 212 PASS rows; 177 (84 %) prose or measurement; 34 (16 %) cite a resolvable path or test node; 0 empty; 1 only-phantom. 14 of 24 tickets cite no resolvable ref at all. `plan_open` would have refused 3 of 22 historical closes.
**Alternatives:** at least one resolvable ref per row (rejected: refuses almost every close and trains rubber-stamped overrides); empty-evidence only (rejected: bites nothing); re-running tests from the check (rejected: a 22-minute suite, and a subprocess in a deterministic gate).
**Impact:** FR-8, BR-3, NFR-2.

## a6-gate-in-wrapper-not-in-writer (Q6)
**Decision:** `ticket-move` (verb) and CLI `ticket move` consult `close-check` for a terminal-lane target of a `tickets`-kind ticket; `tickets.move` stays the raw writer. Human override is a separate verb `close-override` (confirm, reason of at least 10 characters, audit row, comment). Board drag stays ungated.
**Alternatives:** gate inside `tickets.move` (rejected: 3 existing tests use it as fixture setup and the board drag would need UI work); an `override` argument on `ticket-move` (rejected: cannot be gated by tool name); gate the HTTP board route advisory-only (deferred, todo TD-3).
**Limit:** agents can still reach `tickets.move` via a hand edit or the board HTTP route; BR-11.
**Impact:** FR-9, FR-10, BR-2, BR-6, BR-11.

## a7-skill-lint (Q7)
**Decision:** `description-too-long` at 300 chars, WARN only; the 20 offenders are not edited; use-when/not-when stays a convention; agents out of scope; todo TD-1 to trim after T-022 and then raise to ERROR.
**Context:** 39 descriptions, min 86, median 316, max 658; 20 over 300; 2,550 of 12,137 chars excess. Paperclip tests length only. Dossier § 3: evals before shrinking skills.
**Consequence:** `harness lint` will show 20 warnings and 0 errors after this ticket.
**Impact:** FR-1, BR-7.

## a8-doc-drift (Q8)
**Decision:** Fix the verifiably stale docs now (FR-3). Mechanism: roster-count check extended to README.md (FR-4) plus one config-agreement test. No SHA cursor, claim registry, dated-snapshot rule or new skill.
**Rationale:** Paperclip's audit is an LLM-run skill with a cursor file; a cursor in CI (shallow clone) or a commit-diff rule would fire on every commit. A phrase registry overfits today's four findings. Only one dated doc exists in `knowledge-center/docs`.
**Impact:** FR-3, FR-4, NFR-8.

## a9-persona-cap (Q9)
**Decision:** Trim `assistant.md` to fit `PERSONA_CAP = 4000` with the clause inside `## Safety`; the cap is unchanged and asserted.
**Context:** 4,725 chars today, so `persona_text` cuts it mid-bullet in Safety; the "do not approve your own tool calls" bullet and "Known fast commands" are never delivered. Raising the cap would spend tokens on every Assistant turn on small local models and move a budget owned by T-004's BR-7.
**Impact:** FR-5, BR-10, NFR-7.

## a10-ordering (Q10)
**Decision:** Slice A (FR-1..FR-5) has no T-020 dependency. Slice B (FR-6..FR-11) is built after T-020, consuming `runs.ACTIVE`, `tickets.claim_status`, `review_escalated` and the FR-23 digest pattern.
**Context:** `runs.set_state` has no caller outside tests; before T-020 every Run stays `running`.
**Impact:** slice plan; [[T-021-analysis]] § 4.

## a11-human-gate-for-override (Q11, open, non-blocking)
**Decision:** Not decided; needs the user. Adding `mcp__console__close-override` (and `console_close_override` for API rows) to `gated_tools` in `agents.toml` would raise an approval card. `agents.toml` is protected config (comments dropped by `tomlio`), so this ticket does not write it.
**Works without:** separate verb, `confirm`, reason, audit row, comment, protocol text forbidding agents from calling it.

## a12-who-closes (Q12)
**Decision:** The verifier reports a `Disposition` and stops at `close-check`; the harness or the user runs `close-work`. `CLAUDE.md`'s verifier row, `verifier.md` step 10, `harness.md` and `close-work` are edited to say so.
**Context:** `verifier.md` step 10 runs `close-work` while its own contract asks the user to approve it; `harness.md` also says "self → close-work".
**Impact:** FR-11, BR-2.

## a13-task-boundary-text (no question)
**Decision:** The rule is defined once in `plan/SKILL.md`; `breakdown-tasks` points to it and its "ideally one component per task" becomes conditional. Existing size caps (flat 1-4 h, breakdown ≤ 3 h) still bound a merged task.
**Impact:** FR-2, BR-9.

## a14-naming (no question)
**Decision:** Ticket-level key and module are `ticket_liveness`; verb `ticket-liveness`. T-020's per-Run `liveness` and `stop_hook`'s "stale" keep their meanings.
**Impact:** FR-6.

## a15-critique-report-has-no-template
**Decision:** `T-021-critique-report.md` was scaffolded from `challenge-standards/rules.md` and the T-020 precedent because `_template/` has no `critique-report.md`. The gap is flagged, not fixed here (no template additions in scope).

## a16-builder-claims (no question)
**Decision:** `builder.md` gains a claim step so that FR-6's remedy for `in-progress` exists. 0 of 28 tickets are claimed today.
**Limit:** whether builders follow it is a behaviour question for T-022.
**Impact:** FR-11.

## c1-contradictions-with-the-dossier (verified, recorded)
1. **Item 8.** Paperclip's default completion is claim-policy (`agent_claim_policy`): a `done` claim is accepted when the model claims every criterion satisfied; durable evidence is the strong path; unknown refs "remain diagnostic information" (`native-status-arbitration.md:108-124, 305-310`; `status-arbiter.ts:279-309`). The dossier's "accepts only refs that resolve" describes the strong path. Adopted: pure arbiter, four-way classification, claims are not proof, gates beat `done`.
2. **Item 10.** Paperclip tests length only; use-when/not-when is untested authoring guidance (`shipped-catalog.test.ts:30, 95-110`; `create-paperclip-bundled-skill/SKILL.md:177-179`). The dossier's line `:30` is real (re-read).
3. **Item 7.** "Lands in `harness_lint.py`" fails on CI and pre-commit facts (a1); Paperclip's contract counts a human owner as a path and applies prospectively (a2, a3).
4. **Item 12.** Paperclip's audit is an LLM-run skill with a cursor file, not a lint (a8).
5. **Item 13.** Confirmed as the dossier's own inference (Paperclip's analogue is `skills/slack/SKILL.md`); the hidden persona-cap trap was not in the dossier (a9).
6. **Stale docs.** "console/README.md and agents.py say no worktree isolation" is only partly stale: the README text is scoped to the one-shot launcher and true there; the `agents.py` parenthetical about live chats is false. The OpenRouter "ships disabled" claim is not in the dossier but is stale in three places.

## Open, non-blocking (needs the user; design works without)
- **Q11** human approval card for `close-override`: needs a hand edit of `agents.toml` `gated_tools`.

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-requirements-draft]] · [[T-021-decision-log]] · `T-021-questions.toml` · [[T-021-critique-report]] · [[T-021-gap-analysis]] · [[T-021-iteration-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
