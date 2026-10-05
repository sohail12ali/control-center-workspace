---
ticket: "T-022"
artifact: decision-log
---

# Decisions: T-022

All decisions below were **decided under delegated authority 2026-10-01, reversible**: the user said "go wild, do end to end" and delegated the open design choices. Each picks the safest minimal default. None is a user answer; none was invented on the user's behalf. Questions Q9 and Q10 need something only the user can supply and stay open (non-blocking).

## scenario-format-home-cli-verb (Q1)
**Decision:** Scenarios are one TOML file each (`console/evals/scenarios/{id}.toml`) parsed by `tomlio`; code in `console/evals/` (`scenario.py`, `grade.py`, `runner.py`); CLI `kanban.py evals {list,replay,live}`; ONE read-only verb `evals-replay`; no live verb.
**Alternatives:** JSON (no comments, same backslash problem, unreadable for review); markdown frontmatter (`harness_lint._frontmatter` is flat key:value only, cannot hold a list of checks); code in `console/server/` (no gain; the ticket proposes `console/evals/`); a live verb (a hallucinated `confirm=true` would spend money: `needs_confirm` is a stray-call guard, not a human gate, `verbs.toml:25-30`).
**Rationale:** `tomlio` nests `[[scenario.check]]` and skips own-line comments (probed 2026-10-01), so a human can annotate; the subset's limits (trailing `# comment` silently corrupts a value, single-line strings, doubled backslashes) are enforced by the loader and documented, not worked around. The replay verb is deterministic, free and has one right answer, which is the stated test for a verb (`verbs.toml:1-6`).
**Impact:** FR-1, FR-2, FR-12, FR-14; `verbs.toml` +1 row, `verb_handlers.py` +1 adapter, `kanban.py` +1 block.

## deterministic-graders-no-judge (Q2)
**Decision:** v1 has no LLM judge. Five deterministic check kinds (`call`, `first_call`, `order`, `text`, `end`), a closed set, no plugin system.
**Alternatives:** judge-scored (the v3 dossier, `...v3-dossier.md:151`); promptfoo-style `contains` over free text (Paperclip `core.yaml`).
**Rationale:** a judge is a second unmeasured model, costs tokens per grade, and cannot run in CI without a credential (`OPENROUTER_API_KEY` is empty). Substring-over-prose checks pass on empty output and grade what a model says it would do, not what it did; tool-call checks grade actions. The v3 "judge-scored nightly" item is superseded, recorded as the one document-level conflict.
**Impact:** FR-4, BR-1; scheduler never runs live evals.

## raw-transcript-fixtures (Q3)
**Decision:** Fixtures are raw stream-json lines (what the CLI prints), fed through the existing `Normalizer`. Graders use only tool calls (de-duplicated by `id`), text and `turn.end`; usage is read from the raw `result` object. The Normalizer quirks are NOT fixed here.
**Alternatives:** normalized `.events.jsonl` (usage already collapsed to 0: `agent_normalize.py:313-323`, so "UNKNOWN never zero" would be impossible; and hand-authoring bypasses the real reader); a second private wire parser (violates one-fact-one-file).
**Rationale:** the same code path serves fixture and live stdout. Changing the Normalizer would alter the live UI and is T-020/UI territory; the eval view is robust to it by construction. A todo is filed to confirm the quirks against a real stream.
**Impact:** FR-3, FR-7; todo on T-022.

## live-mode-safety-and-spend (Q4)
**Decision:** `live` is opt-in per invocation: `--confirm` required; refused when `CI` is set; needs a selector or `--all`; `--max-budget-usd` default 0.50 per scenario (overridable); wall-clock timeout 180 s; tool-call cap 25; permission mode `plan` only (the backend's read-only rung, `agents.toml:103-104,142`); one attempt per scenario, no retries; backend `claude` with transport `stream_json` only; no side effects (BR-7).
**Alternatives:** scheduled nightly runs (unattended spend, expired login, empty price table); `acceptEdits` mode in a temp copy (heavier, writes real files); auto-retry (turns a behaviour failure into a pass by luck, `doc/evals.md:271-275`).
**Rationale:** smallest blast radius that still observes tool-call behaviour. The 0.50 and the caps are proposals with no price data behind them (`pricing.toml` is empty); the first run is one scenario.
**Impact:** FR-6, BR-3, BR-7, BR-8, NFR Cost.

## failure-taxonomy-rules (Q5)
**Decision:** Four classes, mechanical, one primary per non-pass, precedence grading > infra > product > model. grading = harness/definition/transcript defects and suite self-test failures; infra = could not produce usable evidence (spawn, auth, rate limit, timeout, no result, budget cap, empty turn); product = a committed prompt no longer carries the rule a scenario encodes or a subject file is gone (preflight, spends nothing); model = a usable completed live turn that fails behaviour checks, `error_max_turns`, or the tool-call cap. Infra rules are a small private classifier, replaced by T-020's when it exists.
**Alternatives:** analyst-assigned classes only (not testable); treat a quote mismatch as grading (hides the prompt edit it exists to catch).
**Rationale:** follows `doc/evals.md:137-165` ("a usable completed behaviour failure is not infrastructure"; "fix the grader before interpreting the score") while keeping every class assignable by code.
**Impact:** FR-8, BR-11.

## prompt-edit-gating-and-provenance (Q6)
**Decision:** Scenarios declare `subjects` (`agent:<name>`, `skill:<id>`, `core`); `--changed` maps edited files (git diff plus status) to scenarios; every scenario carries `[[source]]` quotes verified verbatim against the cited files (preflight, no bypass flag). A selector matching nothing exits 2; `--changed` with changed gated files and zero covering scenarios exits 2; partial coverage is reported as UNCOVERED, not failed.
**Alternatives:** gate by filename convention (breaks on rename); no quote check (a deleted rule would keep a green scenario); fail on any uncovered file (unusable while 6 of 39 skills have a scenario).
**Rationale:** the stated purpose is to gate prompt edits and later skill shrinking; a quote check is ~15 lines and makes "grounded in a real rule" mechanical. Honest coverage: 7/7 agents, 6/39 skills as primary subjects.
**Impact:** FR-9, FR-11; sequencing note for T-021.

## starter-set-and-deferred-claim-scenarios (Q7)
**Decision:** Ten scenarios (Appendix A of the requirements), synthetic ticket `EV-001`. Paperclip's "checkout before work" becomes trace-context-first; "stop on 409" becomes stop-on-a-refused-handoff-gate; "blocked needs a reason" becomes blocker-carries-evidence; "no-work exit" becomes builder-with-no-unchecked-tasks. Claim-before-work and stop-on-claim-conflict are deferred.
**Alternatives:** write the claim scenarios anyway (they would test a rule no prompt states; every model would "fail" as a product defect by design).
**Rationale:** `grep claim .claude/` finds no role or skill instruction; only the verb (`verbs.toml:134-140`) and a stop-hook reminder exist. BR-9: grade prompts that exist. The deferral is listed in the README so it is not lost; T-020 item 5 is the natural moment to add the rule and the scenario.
**Impact:** FR-10, BR-9.

## retention-telemetry-side-effects (Q8)
**Decision:** Results and live transcripts go only to `console/.cache/evals/{run_id}/` (gitignored); nothing is committed except scenarios and fixtures; no telemetry record, no notification, no chat entry, no worktree or Run; one audit record per live invocation. Live transcripts are promoted to fixtures only by hand after scrubbing; a pytest scan rejects absolute user paths and key-like strings in committed fixtures.
**Alternatives:** drive `agent_manager.create`/`LiveSession` (it notifies a phone per turn and writes telemetry, `agent_session.py:308-360`, and would put eval chats in the Agents tab); commit results (transcripts can hold anything the agent read, `agent_manager.py:8-9`).
**Rationale:** evals must not skew per-ticket cost, skill-usage counts or spam a phone.
**Impact:** FR-6, FR-13, FR-15, BR-7.

## open-needs-the-user (Q9, Q10)
**Decision:** none taken. Q9 (a working Claude login on this machine and the go-ahead to spend) and Q10 (verified price rows) stay open, priority low, non-blocking.
**Rationale:** only the user can supply a credential, consent to spend, or verified prices. The design works without them: replay, the tests and CI need none; live ACs are verified with a fake spawn and the one real smoke run is recorded NOT RUN until authorised; cost reads UNKNOWN without a table row.
**Impact:** FR-6 (manual smoke NOT RUN), FR-7.

## Amendment 2026-10-01 — FR-13 and FR-14 (post-freeze, via evolve)
**Trigger:** discovery during planning ([[T-022-plan]], challenge-plan CR-13..CR-24): the build order T-020 → T-021 → T-022 makes two sentences in the frozen requirements impossible or self-defeating. Decided under delegated authority 2026-10-01, reversible.
**FR-14 before:** "…the rule that a `[[source]]` quote is updated in the same change that edits the cited rule (T-020/T-021 run `evals replay --changed` in their verify step)…"
**FR-14 after:** same rule, but "T-020 and T-021 predate the suite and cannot run it in their verify step; T-022 tasks 12-13 re-pin every quote to the then-current text and are the retroactive check. From T-022 onward, any ticket that edits a quoted rule runs `evals replay --changed` in its verify step."
**FR-13 before:** "CI needs no workflow change (the existing `pytest` job collects them)."
**FR-13 after:** "CI gains one replay-only step in the existing harness job (free: no network, no `claude`), added in the LAST task so it never runs before scenarios exist; the pytest job still collects the `test_evals_*` modules." Reason: replay is the only mode that is both free and a true regression gate; a gate nobody runs is not a gate.
**Alternative rejected:** leave FR-14 as written and note the gap (rejected: a requirement that states something false cannot be verified honestly).
**Cascade:** plan tasks 11 (README stays generic), 12-13 (re-pin quotes; task 13 adds the `verify.yml` step) already encode this; verification must test the `verify.yml` step, not only the module tests.

## Amendment 2026-10-01 (2) — lint criterion
T-021's skill-length rule adds about 20 harness-lint WARNINGS (20 of 39 descriptions exceed 300 chars; warn-only so CI stays green). T-022 builds after T-021, so FR-13 AC3 and the plan's closing gate now read "0 errors and no new warnings vs the pre-T-022 baseline". Decided under delegated authority, reversible. T-020 builds before T-021, so its "0 warnings" criteria stay correct.

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements-draft]] · [[T-022-requirements]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
