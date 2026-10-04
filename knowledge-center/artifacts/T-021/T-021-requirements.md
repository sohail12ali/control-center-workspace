---
ticket: "T-021"
artifact: requirements
status: frozen
frozen_date: "2026-10-01"
frozen_iteration: 3
---

# Requirements: T-021

> Frozen summary for `requirements stories`/planner consumption. Full wording (flows, grammar, edge cases, interaction table) is in [[T-021-requirements-draft]] (frozen v3). Decisions: [[T-021-decision-log]] (all "decided under delegated authority 2026-10-01, reversible"). Frozen 2026-10-01 at iteration 3: 11 FR / 8 NFR / 11 BR, 0 open challenge findings (25 resolved), 0 blocker questions (Q11 open, non-blocking).

## Intent

Turn the honesty gates into checks: a ticket-liveness check, an evidence-gated close with an audited human override, a skill-description length lint, a task-boundary rule, doc-drift fixes and a roster check, and an untrusted-content clause for the Assistant. Dossier items 7, 8, 10-13 of [[INV-2026-10-01-paperclip-adoption-dossier]]. GROUND changed four of the dossier's mechanisms (see Contradictions): the design is calibrated to measurements, not to the dossier's literal wording.

## Scope

### In scope
- **Slice A (no T-020 dependency, any order):** FR-1 skill-length lint, FR-2 task-boundary text, FR-3 stale docs, FR-4 README roster check, FR-5 Assistant clause.
- **Slice B (built after T-020):** FR-6 liveness + digest, FR-7 blocked guard, FR-8 `close-check`, FR-9 guarded move, FR-10 `close-override`, FR-11 protocol text. Order inside: FR-6 before FR-7; FR-7 and FR-9 share `ticket_gate.py`; FR-8 before FR-9/FR-10; FR-11 last.

### Out of scope
UI (board drag stays ungated, TD-3); budgets; new agents or skills (7 and 39 stay); the T-020 items; agent evals (T-022); editing existing skill descriptions (TD-1); linting use-when/not-when or agent descriptions; any `ticket.toml` field or tracker kind; any config TOML except three rows in `verbs.toml`; `agents.toml`; a SHA-cursor or claim-registry doc audit; truth-checking evidence, re-running tests or reading git from `close-check`; touching any existing ticket.

## What T-021 consumes from T-020 (so the planner can order the builds)

| T-020 item (frozen [[T-020-requirements]]) | Used by | How |
|---|---|---|
| `runs.ACTIVE` / `TERMINAL`, locked terminal states (FR-1, FR-2) | FR-6 | live Run = Run on the ticket with `state in runs.ACTIVE` (includes `scheduled_retry`) |
| `tickets.claim_status(repo, ticket, now)` → `{state free/held/stale, holder, basis}` (FR-20) | FR-6, FR-8 | `held` is a path; `stale` is not and blocks close |
| `review_escalated` on `ticket.toml` (FR-24) | FR-8 | block `review_escalated` |
| Escalation question (critical) (FR-24) | FR-8 | reported by `trackers.blockers`, no new code |
| `context.build` additive digest keys (FR-23) | FR-6 | `ticket_liveness` key, same pattern |
| Verb-row and handler pattern (FR-18/22/24) | FR-6, FR-8, FR-10 | three `verbs.toml` rows |

Files both tickets edit: `console/server/context.py`, `console/server/verb_handlers.py`, `console/config/verbs.toml`, `.claude/agents/verifier.md`. T-020 builds first. T-021 adds no `ticket.toml` field, so it cannot collide with T-020's schema. Without T-020 every Run stays `running` forever (no caller of `runs.set_state`), so slice B must not be built first. If a T-020 name differs at slice B start, adapt and log the delta.

## Prompt-facing files this ticket edits (T-022 pins quotes after T-020 and T-021 are built)

`.claude/skills/plan/SKILL.md` (FR-2) · `.claude/skills/breakdown-tasks/SKILL.md` (FR-2) · `.claude/skills/close-work/SKILL.md` (FR-11) · `.claude/skills/console/SKILL.md`, one sentence (FR-3) · `.claude/agents/verifier.md` (FR-11; T-020 FR-25 too) · `.claude/agents/harness.md` (FR-11, ≤ +378 chars) · `.claude/agents/builder.md` (FR-11) · `CLAUDE.md` verifier row (FR-11) · `console/config/assistant.md` (FR-5). Their `description:` lines stay byte-identical. Scenarios worth pinning in T-022: injected instruction in clipboard text is not obeyed (FR-5); verifier stops at `close-check` and does not run `close-work` (FR-11); builder claims on its first task (FR-11).

## Functional Requirements

### Slice A

#### FR-1: Skill-description length rule
`harness_lint.lint` emits `description-too-long` (WARN, never ERROR) for skills whose `description` exceeds `MAX_DESCRIPTION_CHARS = 300`; skills only; existing offenders untouched (20 of 39 at 2026-10-01).
- [ ] 300 chars: no finding; 301: one `warn` finding, `errors == 0`.
- [ ] 400-char agent description: no finding; empty skill description: `missing-description` only.
- [ ] Existing `test_harness_lint.py` tests unchanged and green.
- [ ] Real tree: all such findings `warn`, `harness lint` exits 0, finding set equals the files' own over-300 set.
- [ ] Diff touches `harness_lint.py` and its test only.

#### FR-2: Task-boundary rule text
Defined once in `plan/SKILL.md` under `Task boundary rule` with bold labels **Fewest tasks**, **Qualifying boundaries**, **Reason per task**, **Merge-back pass**, **Re-read before done**; size caps (1-4 h flat, ≤ 3 h breakdown) kept; `breakdown-tasks` points to it by path and drops the unconditional "ideally one component per task".
- [ ] A test finds the heading, the five labels, `1-4h` and `0.5/1/1.5/2/3h` in `plan/SKILL.md`.
- [ ] `breakdown-tasks/SKILL.md` contains `.claude/skills/plan/SKILL.md` and not "ideally one component per task".
- [ ] `harness lint` 0 errors, `39 skills, 7 agents`; both `description:` lines byte-identical.
- [ ] Diff touches only those two SKILL.md files plus the test.

#### FR-3: Verifiably stale docs fixed
Edits: `agents.py:24-26` (drop "True of the live chats too", ticketed live chats isolate since T-018); `console/README.md:738-740` (scope the limit to the one-shot launcher); `console/README.md:243, 480-481` and `console/SKILL.md:45` (OpenRouter row ships `enabled = true`, `installed = false` until the key is set); `desktop/README.md:8-10` (tray remotes the Assistant; menu from `features.toml`); `console-feature-comparison.md` (worktree, schedules, verbs rows, size line, "next ports").
- [ ] Greps: the stale phrases are gone; comparison rows no longer start `❌`; README tray paragraph says Assistant.
- [ ] `test_docs_agree_with_config`: OpenRouter `enabled = true` and no whitespace-normalised "ships disabled"/"enabled = false" in `console/README.md` or `console/SKILL.md`.
- [ ] `import server.agents` works; `pytest -k agents` shows no new failure.
- [ ] The `console/SKILL.md` edit is one sentence; its `description:` is unchanged.

#### FR-4: Roster-count check covers README.md
`_check_declared_counts` also reads `README.md`; docstring states that semantic drift is not detectable deterministically.
- [ ] README "9 skills" with 2 on disk: WARN `stale-count`, path `README.md`; accurate: quiet; absent: quiet.
- [ ] Real tree: no `stale-count`.
- [ ] Existing `TestDeclaredCounts` unchanged and green.

#### FR-5: Untrusted-content clause for the Assistant
Clause (≤ 600 chars) inside `## Safety` of `assistant.md` containing `data, not instructions` and the words clipboard, OCR, screenshot, web; dossier's own inference (Paperclip analogue: `skills/slack/SKILL.md`). File shrinks by ≥ 1,250 chars net (remove `## Known fast commands`, tighten two sections, no rule deleted); `PERSONA_CAP` stays 4000.
- [ ] `len(persona_text(real, "assistant")) <= PERSONA_CAP`, no "Persona text cut here".
- [ ] Delivered text contains the phrase, the four words and every Safety bullet, including "You do not approve your own tool calls" (cut off today).
- [ ] `PERSONA_CAP == 4000`.
- [ ] All seven agent personas ≤ cap (headroom: harness 378).
- [ ] No test calls a model.

### Slice B

#### FR-6: Ticket liveness check (read-only)
`console/server/ticket_liveness.py`: `evaluate(repo, ticket, now)`, `scan(repo, now)`; verb `ticket-liveness`. Applies to `kind=tickets`, lanes `in-progress`/`verify`/`blocked` (not `open`, not terminal). Paths: live Run, held claim, pending question (`open`/`answered`); stale claim, terminal Run, resolved question, human `owner` are not. `in-progress`/`verify`: `no_action_path` or `claim_stale`; `blocked`: `blocked_prose_only` / `blocked_no_owner`. All WARN. Digest key `ticket_liveness` and one `Liveness:` line only when there is a finding.
- [ ] Table test (17 rows listed in the draft) with fixtures and injected `now` returns the expected code or ok for each.
- [ ] Corrupt tracker yields `check_error` warn; `scan` continues.
- [ ] Digest line and JSON key for an in-progress ticket without a path; none for done/healthy tickets (existing `test_context.py` unchanged).
- [ ] Verb needs no `confirm`; MCP list has `ticket-liveness`.
- [ ] No writes (bytes and mtimes identical); `scan` of 100 tickets < 2 s.
- [ ] Informational: real-vault scan recorded in `T-021-verification.md`.

#### FR-7: Prose-only `blocked` refused at the transition
Through `ticket_gate.guarded_move` for verb `ticket-move` and CLI `ticket move`; prospective only; refusal `{ok: False, refused, message, hint}`, no write, audit `ticket.block`; no override.
- [ ] No question or critical bug: refused, lane unchanged, one audit row with `refused:`.
- [ ] After `tracker-add` of a question: move succeeds, `stage == "blocked"`.
- [ ] Empty owner and no claim: `blocked_no_owner`.
- [ ] Other moves and moves out of `blocked` unevaluated; existing `TestTicketMoveSet` green.
- [ ] CLI and verb return the same refusal; other kinds never refused.

#### FR-8: `close-check` (read-only evidence verdict)
`console/server/close_check.py`, verb `close-check`. Blocks: `no_verification`, `criterion_not_pass`, `evidence_empty`, `evidence_phantom`, `critical_question_open`, `critical_bug_unverified`, `claim_stale`, `review_escalated`, `plan_open`, `check_error`. Warnings: `evidence_prose_only`, `evidence_partial`, `criterion_descoped`, `claim_held`. Evidence refs: path with `/` (or ticket artifact name) with optional `:N[-M]`, `::name`; `run:<12hex>` (Run must be `done`); everything else `unverifiable`; `accepted` = exists, not truth; `basis: "existence"`.
- [ ] Each block code fires on a planted fixture and not on the clean one; clean fixture returns `ok: true` with exact counts.
- [ ] Ref table: nonexistent path, line beyond EOF, absent test name, unknown run, `running` run → missing; bare `tray.rs`, `pytest 1406 passed`, timings, backslash path, `/tmp/x.py`, URL → unverifiable.
- [ ] Row policy: accepted + missing → partial warn; only missing → `evidence_phantom`; all-prose table → ok with warnings.
- [ ] T-020 consumption: stale claim blocks, held warns, `review_escalated` blocks, critical question blocks.
- [ ] Read-only and total: no writes; corrupt file and injected exception return blocks, never raise.
- [ ] Calibration over the 22 done tickets recorded in `T-021-verification.md`: expect 0 `evidence_empty`, ≤ 3 `evidence_phantom` of 212 pass rows, ~84 % prose-only; > 10 % blocked means a parser defect.
- [ ] Verb on CLI, MCP, HTTP; shown by `kanban verb list`.

#### FR-9: A close goes through `close-check`
`ticket_gate.guarded_move` for `ticket-move` and CLI `ticket move` to a terminal lane of a `tickets` ticket that is not already terminal: blocks → `{ok: False, blocked: True, blocks, hint}`, no write, audit `ticket.close` `refused:`; ok → `tickets.move` + audit with evidence counts; exception → `check_error` block. `tickets.move` unchanged.
- [ ] Open critical question: refused with `critical_question_open`, lane unchanged, audit row.
- [ ] Clean ticket moves; audit carries counts.
- [ ] Injected exception: lane unchanged, `check_error`.
- [ ] CLI (in-process `cmd_ticket_move`, `SystemExit(1)`) and verb agree.
- [ ] Direct `tickets.move` still works: `test_agents_catalog`, `test_context`, `test_pr_check_verb` unchanged.
- [ ] Non-terminal targets, reopening, other kinds: no check.

#### FR-10: `close-override`
Mutating verb (`needs_ticket`, `needs_confirm`), reason ≥ 10 chars; moves to the first terminal lane regardless of blocks; audit `ticket.close.override` (reason, codes, counts); comment by `close-override`; bus publish; separate from `ticket-move` so it is gate-able by name.
- [ ] Reason empty or 9 chars: `{ok: false}`, no change, no override audit row.
- [ ] Valid reason on a blocked fixture: lane done, one override audit row with reason and codes, one comment.
- [ ] No `confirm`: `VerbError`; tool listed on CLI and MCP.
- [ ] Already-done and non-`tickets` tickets refused.

#### FR-11: Protocol text: disposition, no self-close
Edits: `close-work` (first step runs `close-check`; Gate forbids editing `verification.md` to satisfy it and forbids an agent calling `close-override` or inventing a reason); `verifier.md` step 10 (clean: report `Disposition`, run `close-check`, hand over, do not run `close-work`; unmet branch kept; layered on T-020 FR-25) and contract line `Disposition: ready_to_close | needs_fix | blocked | needs_human`; `harness.md` row; `builder.md` claim step; `CLAUDE.md` verifier row.
- [ ] Greps find the phrases in the five files as listed; `verifier.md` step 10 does not instruct `close-work`.
- [ ] Contract headers (`── Verifier ──`, `── Builder ──`, `── Harness ──`) and fields intact; every persona ≤ cap; `harness.md` growth ≤ 378 chars.
- [ ] `harness lint`: 0 errors, no new `stale-count`, `39 skills, 7 agents`; edited `description:` lines unchanged.
- [ ] Diff touches only the five files plus tests; no new file under `.claude/agents` or `.claude/skills`.

## Non-Functional Requirements

| ID | Category | Requirement | Target |
|---|---|---|---|
| NFR-1 | Constraints | Stdlib only; JS untouched; 7 agents / 39 skills; no `ticket.toml` field or tracker kind; only `verbs.toml` gains exactly 3 rows | 0 new third-party imports; no `console/static`, `agents.toml` or new skill dir in the diff |
| NFR-2 | Reliability | Fail closed and honest: errors block, unknown is never ok, `basis: "existence"` | tests in FR-8, FR-9; evaluators never raise |
| NFR-3 | Testability | Fakes and fixtures; no model, network, subprocess; injectable `now` | grep of new tests finds none; new tests < 30 s |
| NFR-4 | Compatibility | No existing ticket rewritten, moved or newly blocked; `tickets.move` unchanged; existing tests unchanged | touched-module baseline equal before and after |
| NFR-5 | Auditability | Every gate outcome, refusals included, has an audit row | rows `ticket.block`, `ticket.close`, `ticket.close.override`; added to the action tuple |
| NFR-6 | Performance | Checks scale with the ticket; no repo walk, no git | `close-check` on 50 rows < 0.5 s; `scan` of 100 tickets < 2 s |
| NFR-7 | Prompt budget | Prompt text fits its cap, fit pinned by test; edited skills keep `description:` | persona caps tests; descriptions byte-identical |
| NFR-8 | Honesty of limits | Limits stated where read | verb hints, lint docstring, decision log |

## Business Rules

- **BR-1** Gates act only on transitions made after this ships; no existing ticket is touched.
- **BR-2** The judge does not close: verifier reports a `Disposition`; closing runs behind `close-check`; an agent never calls `close-override` or invents a reason.
- **BR-3** Evidence classes `accepted`/`missing`/`unverifiable`; prose never accepted; a phantom ref is worse than none; accepted means existence, not truth.
- **BR-4** Live Run (`runs.ACTIVE`) and held claim are paths; stale claim, terminal Run, resolved question and the human `owner` are not.
- **BR-5** `open` and terminal lanes have no liveness expectation; `kind=tickets` only.
- **BR-6** Override is a separate verb with `confirm`, ≥ 10-char reason, audit row and comment; `blocked` has no override.
- **BR-7** ERROR only for a broken harness; judgement is WARN and never fails CI.
- **BR-8** `blocked` needs a next action (pending question or open critical bug) and an owner (claim holder if held, else ticket `owner`); the owner half is nearly always satisfied (TD-2).
- **BR-9** One fact, one file: the task-boundary rule lives in `plan`.
- **BR-10** Prompt text fits the cap it is read under, tested; fixing a truncation never moves the cap.
- **BR-11** Human surfaces (board drag, hand edits) are not gated; a stated limit.

## Data Entities (new / changed)

| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Liveness result | new, computed | `ticket, stage, applies, ok, paths[], findings[]` | per call | `ticket_liveness.py`; FR-6 |
| Close-check result | new, computed | `ok, blocks[], warnings[], evidence{}, basis` | per call | `close_check.py`; FR-8 |
| Evidence ref grammar | new, documented | path[:N[-M]][::name], `run:<12hex>` | static | FR-8 |
| Audit actions | new values | `ticket.block`, `ticket.close`, `ticket.close.override` | append-only | `audit.py` |
| Verb rows | new | `ticket-liveness`, `close-check`, `close-override` | registry load | `verbs.toml` |
| Digest key | new, additive | `ticket_liveness` | per call | `context.py` |
| Lint findings | new / extended | `description-too-long`; `stale-count` for README.md | per run | `harness_lint.py` |

No persisted data, `ticket.toml` field or tracker kind is added.

## Edge Cases

Ticket with no verification table (T-019) → `no_verification`, override with reason · several tables → only those with `Status` and `Evidence` · `**PASS**` or "PASS — static only" is pass, "PASS / PENDING" is not · gitignored file or deleted Run → `missing` (warn if another ref resolves) · bare names, backslash and absolute paths, URLs → `unverifiable` · `claim_status` absent (T-020 not built) → `check_error` · claim older than the TTL during a long human session → `claim_stale` warn, block at close, re-claim refreshes · non-critical pending question makes `blocked` routable · kickoff placeholder plan tasks → `plan_open` (3 of 22 historical closes) · check and move not atomic · board drag or TOML edit bypasses the gate (BR-11) · unattended `/do` close stops and asks; a human at the CLI uses `close-override` · after this ticket `harness lint` shows 0 errors and 20 `description-too-long` warnings, so later "0 warnings" criteria must read "no new warnings".

## Contradictions with the dossier (verified, recorded in decision c1)

Item 8: Paperclip's default is claim-policy, evidence is the strong path, unknown refs are diagnostic (`native-status-arbitration.md:108-124, 305-310`). Item 10: Paperclip tests length only. Item 7: "lands in `harness_lint.py`" fails on CI and pre-commit facts; Paperclip counts a human owner as a path and is prospective only. Item 12: Paperclip's audit is an LLM-run skill with a cursor file. Item 13: hidden persona-cap trap (4,725 vs 4,000). Stale docs: "no worktree isolation" is only partly stale; OpenRouter "ships disabled" is stale in three places.

## Open, non-blocking (need the user; design works without)

- **Q11** hard human gate for `close-override`: needs the user to add `mcp__console__close-override` (and `console_close_override` for API rows) to `gated_tools` in `agents.toml` by hand. Without it: separate verb, `confirm`, reason, audit row, comment, protocol text.

## Acceptance Criteria

Every FR carries its own checklist. The ticket is accepted when all pass with cited evidence, `python console/kanban.py harness lint` exits 0 with 0 errors and no warning other than the measured `description-too-long` set, the roster line reads `39 skills, 7 agents`, the touched-module test baseline has no new failure, and the calibration and real-vault measurements are recorded in `T-021-verification.md`.

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-requirements-draft]] · [[T-021-decision-log]] · [[T-021-iteration-log]] · [[T-021-gap-analysis]] · [[T-021-critique-report]] · [[T-021-context-snapshot]] · [[T-021-user-stories]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]] · Dependency: [[T-020-requirements]] · [[T-020-decision-log]]
