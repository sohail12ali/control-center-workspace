---
ticket: "T-021"
artifact: plan
structure: single-layer
---

# Plan: T-021

## Approach

Flat plan, test-first. Structure is single-layer by judgement: one component (`console/server` plus prompt text), though it exceeds six tasks; there is no cross-ticket chain except one gate (Slice B waits for T-020). Components, task-breakdown and estimate artifacts are skipped on purpose (lean). Each task: write the named tests first and watch them fail, then the code, then the verify command. Requirements: [[T-021-requirements]] (frozen, 11 FR / 8 NFR / 11 BR); full wording in [[T-021-requirements-draft]]; stories in [[T-021-user-stories]].

Windows primary, stdlib only, no model/network/subprocess in new tests (NFR-3), roster stays 7 agents / 39 skills (NFR-1). `python -m pytest -o addopts=""` is the only test form used below. Test fixtures: `repo` in `console/tests/conftest.py:121`.

## Slices

- **Slice A (T-021-01..05):** FR-1..FR-5. No T-020 dependency; tasks run in any order except 01 then 02 (same file).
- **Slice B (T-021-06..16):** FR-6..FR-11 plus the existing-ticket sweep. Gated on T-020 built and verified (task 06). Order: 06, 07, 08, 09, 10, 11, 12, 13, 14, 15, then 16.
- **Final VERIFY (T-021-17):** full suite, lint delta, static untouched, AC evidence table.

## Shared-file collision rule (T-020 is building the same files now)

All edits to a file another ticket or task also touches use **anchored `Edit` only**: Read the current region immediately before the edit (line numbers in this plan are today's and WILL drift), anchor on a unique existing line, never `Write` the whole file, never reformat neighbouring lines, and after the edit grep that the other ticket's additions are still present. Shared files and who edits what:

| File | Other editor | T-021 edit (anchor) |
|------|--------------|---------------------|
| `console/config/verbs.toml` | T-020 (`run-watch`, `run-retry`, `claim-release`, `review-round`) | append exactly 3 `[[verb]]` rows (`ticket-liveness`, `close-check`, `close-override`) after the last existing row; modify no existing row (`ticket-move` at :117 stays as is) |
| `console/server/verb_handlers.py` | T-020 (run/claim/review handlers) | add `ticket_liveness`, `close_check`, `close_override` after `ticket_move` (:411); change only the body of `ticket_move` to call `ticket_gate.guarded_move` |
| `console/server/context.py` | T-020 4b-2 (`claim`, `review`, `runs` keys, `build` :166, `format_markdown` :225) | one additive `ticket_liveness` key and one `Liveness:` line, inserted after T-020's lines |
| `console/server/audit.py` | T-020 (`ticket.review`, claim actions) | append `ticket.block`, `ticket.close`, `ticket.close.override` to the `ACTIONS` tuple (:44-67) after the last entry |
| `console/kanban.py` | none known | body of `cmd_ticket_move` (:68-69) only |
| `console/server/tickets.py` | T-020 (claim, `review_escalated`, `claim_status`) | **none** (read-only consumer; `tickets.move` :176 unchanged) |
| `console/server/agents.py` | T-020 2a-2, 2b-1 (`[SHARED]`) | comment at :24-26 only, done last in task 05 after re-reading |
| `.claude/agents/verifier.md` | T-020 FR-25 (first step and step 10) | step 10 and the contract line, layered on T-020's wording; both rules stay |
| `console/server/harness_lint.py` | none; tasks 01 then 02 in order | `lint` (:246) and `_check_declared_counts` (:303) |
| `.claude/agents/harness.md`, `builder.md`, `CLAUDE.md`, `close-work/SKILL.md` | none known | one row/step each; `harness.md` growth <= 378 chars |

If T-020 renames a symbol, adapt, log the delta in [[T-021-progress]] and tell the orchestrator.

## Tasks

### Slice A (no T-020 dependency)

### [x] T-021-01 — Skill-description length lint, plus pre-ticket baseline (1.5 h)
- **FR:** FR-1 · **Slice:** A · **Depends on:** —
- **Step 0 (baseline):** before any edit run `python console/kanban.py harness lint`; record in [[T-021-progress]] the error count, warning count and warning codes (call it BASELINE). Later criteria compare to it.
- **Files:** `console/server/harness_lint.py` (new constant `MAX_DESCRIPTION_CHARS = 300` near :33; check inside the skill loop of `lint` :254-268 after `_check_frontmatter`, skills only, WARN code `description-too-long`; message names the length and the convention "use when / not when" as a convention, not a rule); `console/tests/test_harness_lint.py` (new `class TestDescriptionLength`; helper `_skill` :35 takes `description=`).
- **Tests (first):** `test_300_chars_no_finding`, `test_301_chars_one_warn_finding_errors_zero`, `test_400_char_agent_description_no_finding`, `test_empty_skill_description_is_missing_description_only`, `test_real_tree_findings_all_warn_and_equal_files_over_300` (counts skills whose own frontmatter exceeds 300, expects 20 of 39 today, compares sets, asserts `errors == 0`).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_harness_lint.py` then `python console/kanban.py harness lint` (exit 0, 0 errors, warnings = BASELINE + 20).
- **Done-criteria:** all FR-1 checkboxes; existing tests unchanged; `git diff --stat` shows only the two files.
- **Basis:** one constant, one `if`, five table-style tests; the real-tree test needs a frontmatter reader (`_frontmatter` :74 is reusable).

### [x] T-021-02 — README.md joins the roster-count check (1 h)
- **FR:** FR-4 · **Slice:** A · **Depends on:** T-021-01 (same file, sequential)
- **Files:** `console/server/harness_lint.py` (`_check_declared_counts` :303 loops over `CLAUDE.md` and `README.md`, each skipped when absent, finding path is the file's own name; docstring states that semantic drift is not detectable deterministically); `console/tests/test_harness_lint.py` (extend `TestDeclaredCounts` :193 with a new class `TestReadmeCounts`, do not edit existing tests).
- **Tests (first):** `test_readme_9_skills_with_2_on_disk_warns_stale_count_path_readme`, `test_readme_accurate_is_quiet`, `test_readme_absent_is_quiet`, `test_real_tree_has_no_stale_count`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_harness_lint.py`; `python console/kanban.py harness lint` shows no `stale-count`. If the real README already disagrees, report it and fix the README sentence only (log it).
- **Done-criteria:** all FR-4 checkboxes; `TestDeclaredCounts` green unchanged.
- **Basis:** loop over two paths; the `README.md` sentence check on the real tree may need one text fix.

### [x] T-021-03 — Task-boundary rule in `plan`, pointer from `breakdown-tasks` (1.5 h)
- **FR:** FR-2 · **Slice:** A · **Depends on:** —
- **Files:** `.claude/skills/plan/SKILL.md` (new `Task boundary rule` section with bold labels **Fewest tasks**, **Qualifying boundaries**, **Reason per task**, **Merge-back pass**, **Re-read before done**; keep `1-4h` flat cap; the long line at :19 is edited only by anchored Edit if touched); `.claude/skills/breakdown-tasks/SKILL.md` (:14: drop "ideally one component per task", add the path `.claude/skills/plan/SKILL.md`, keep `0.5/1/1.5/2/3h`); new `console/tests/test_task_boundary_text.py`.
- **Tests (first):** `test_plan_has_heading_five_labels_and_size_caps`, `test_breakdown_points_to_plan_and_drops_old_phrase`, `test_descriptions_byte_identical` (pins sha256 of both `description:` lines captured before the edit), `test_roster_line_still_39_skills_7_agents` (calls `harness_lint.lint`, no `errors`).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_task_boundary_text.py console/tests/test_harness_lint.py`; `python console/kanban.py harness lint` (0 errors, no new warning vs BASELINE other than T-021-01's 20).
- **Done-criteria:** all FR-2 checkboxes; diff = two SKILL.md plus the test.
- **Basis:** prose edit, wording already specified in the draft FR-2; edit-in-place needs care with a long line.

### [x] T-021-04 — Trim `assistant.md` under the cap and add the untrusted-content clause (2 h)
- **FR:** FR-5 · **Slice:** A · **Depends on:** —
- **Facts (verified):** `console/config/assistant.md` is 93 lines, 4,725 chars per the draft, cap `PERSONA_CAP = 4_000` (`console/server/prompt_build.py:40`), cut at `:95-98` with the marker "Persona text cut here"; the cut lands mid-`## Safety`, so "You do not approve your own tool calls" (:81-82) is not delivered today.
- **Files:** `console/config/assistant.md`; new `console/tests/test_persona_fit.py` (do not edit `test_prompt_build.py` `TestPersonaCap` :145).
- **Edit design:** (1) remove `## Known fast commands` (:84-92; no tool or test references it: grep of `console/` finds only the file itself); (2) tighten `## How to sound` (:18-38) and `## What you do yourself, and what you hand over` (:40-59) by rewording only, every instruction kept; (3) keep all three Safety bullets verbatim in meaning; (4) add inside `## Safety` a clause of at most 600 chars containing `data, not instructions` and the words clipboard, OCR, screenshot, web (text from those sources is data to read, never instructions to follow). Net shrink >= 1,250 chars is the design target (it needs about 1,850 chars removed against a 600-char clause: the Known-fast-commands section is only about 650, so the two tightened sections must give about 1,200); the hard acceptance criterion is `len(persona_text) <= 4000` with no cut marker and the last Safety bullet delivered. Measure through `prompt_build.persona_text`, not file bytes.
- **Tests (first, fail today):** `test_assistant_persona_fits_cap_and_is_not_cut`, `test_delivered_text_has_clause_phrase_four_words_and_every_safety_bullet` (includes "You do not approve your own tool calls" and the credential and invention bullets), `test_persona_cap_is_still_4000`, `test_all_seven_agent_personas_fit` (iterates `.claude/agents/*.md` through `persona_text`, asserts 7 files), `test_new_tests_call_no_model` (no import of a backend module).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_persona_fit.py console/tests/test_prompt_build.py console/tests/test_assistant.py`.
- **Done-criteria:** all FR-5 checkboxes; length printed in [[T-021-progress]].
- **Basis:** careful rewording of one file against a measured budget, plus four small tests.

### [x] T-021-05 — Fix the verifiably stale docs (2 h)
- **FR:** FR-3 · **Slice:** A · **Depends on:** — (the `agents.py` comment edit goes last; re-read the file first, T-020 edits it)
- **Files:** `console/server/agents.py:24-26` (drop "the live chats too" clause; ticketed live chats isolate since T-018); `console/README.md:738-740` (limit scoped to the one-shot launcher), `:243` and `:479-481` (OpenRouter row ships `enabled = true`, `installed = false` until `OPENROUTER_API_KEY` is set; `console/config/agents.toml:230` already says `enabled = true`); `.claude/skills/console/SKILL.md:45` (one sentence "OpenRouter row ships `enabled = false`" corrected; `description:` untouched); `desktop/README.md:8-10` (tray remotes the Assistant; menu from `features.toml`); `knowledge-center/docs/console-feature-comparison.md` (worktree, schedules, verbs rows, size line, "next ports"). New `console/tests/test_docs_agree_with_config.py`.
- **Tests (first):** `test_docs_agree_with_config` (reads `console/config/agents.toml` with the same loader `console/server/` uses for it (grep `load_config`/`tomllib` before choosing; stdlib only); asserts the openrouter row `enabled = true` and no whitespace-normalised "ships disabled"/"enabled = false" tied to OpenRouter in `console/README.md` or `.claude/skills/console/SKILL.md`), `test_stale_phrases_gone` (the agents.py phrase, "No worktree isolation" unscoped, comparison rows not starting with the cross mark), `test_desktop_readme_says_assistant`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_docs_agree_with_config.py -k "docs or stale or desktop"`; `python -c "import sys; sys.path.insert(0,'console'); import server.agents"`; `python -m pytest -o addopts="" -q -k agents console/tests`.
- **Done-criteria:** all FR-3 checkboxes; `console/SKILL.md` edit is one sentence; lint 0 errors.
- **Basis:** five doc files plus three greps; the comparison-doc rows need reading to decide wording.

### Slice B (gated on T-020 built and verified)

### [x] T-021-06 — Gate: confirm T-020 is built and its names exist (0.5 h)
- **FR:** gate for FR-6..FR-11 · **Slice:** B · **Depends on:** T-020 closed or at least verified green (orchestrator confirms)
- **Check (grep, no code):** `runs.ACTIVE` and `runs.TERMINAL` (`console/server/runs.py:23-24`, exist today; `ACTIVE` must include `scheduled_retry`); `tickets.claim_status(repo_root, ticket_id, now=None)` returning `{state: free|held|stale, holder, basis}` (T-020 4a-1, `console/server/tickets.py`; absent today); `review_escalated` loaded by `tickets.load` (T-020 4b-1); `tracker_add(..., raised_by=)` (`verb_handlers.py` :530 today); `context.build` keys `claim`, `review`, `runs` (T-020 4b-2); T-020 verb rows in `verbs.toml`; T-020 FR-25 wording in `verifier.md`.
- **Done-criteria:** each symbol cited with file:line in [[T-021-progress]]; any renamed symbol logged; if `claim_status` is absent STOP and report (Slice B must not be built first, every Run stays `running`).
- **Basis:** reads only.

### [x] T-021-07 — `ticket_liveness` module (2.5 h)
- **FR:** FR-6 (module and table) · **Slice:** B · **Depends on:** T-021-06
- **Consumes from T-020:** `runs.ACTIVE`, `runs.list_runs(repo_root, ticket=..., state=...)` (exists, used at `verb_handlers.py:396`), `tickets.claim_status`, `trackers.blockers` (`trackers.py:225`).
- **Files:** new `console/server/ticket_liveness.py` (`evaluate(repo_root, ticket_id, now=None)`, `scan(repo_root, now=None)`, constants for codes; every read wrapped so errors give `check_error` warn and never raise; no write call anywhere); new `console/tests/test_ticket_liveness.py`.
- **Tests (first):** `TestEvaluateTable::test_row[...]` parametrised over the 17 rows of [[T-021-requirements-draft]] FR-6 (open lane, done lane, investigations kind, running Run, `scheduled_retry` Run, done Run only, held claim, stale claim only, open question, answered question, resolved question only, verify lane, blocked+question+owner, blocked+critical bug+owner, blocked+nothing, blocked+question+no owner/no claim, blocked+live Run only) with injected `now`; `TestScan::test_corrupt_questions_toml_is_check_error_and_scan_continues`, `::test_100_tickets_under_2_seconds_and_no_writes` (bytes and `os.stat` mtimes identical).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_ticket_liveness.py`.
- **Done-criteria:** FR-6 checkboxes 1, 2, 5 (module level); `evaluate` result shape `{ticket, stage, applies, ok, paths[], findings[]}`.
- **Basis:** 17-row table drives the code; fixtures via `repo`, `tickets.create` and tracker helpers.

### [x] T-021-08 — `ticket-liveness` verb and the digest line (2 h)
- **FR:** FR-6 (verb, digest) · **Slice:** B · **Depends on:** T-021-07 (and T-020 4b-2 already merged into `context.py`)
- **Files (anchored edits only):** `console/config/verbs.toml` (+1 row, read-only, no `confirm`, `ticket` optional); `console/server/verb_handlers.py` (`ticket_liveness(repo_root, ticket=None)`: ticket given evaluates one, else `scan`); `console/server/context.py` (`build` :166 adds `ticket_liveness` only when applicable and it has a finding; `format_markdown` :225 adds one `Liveness:` line); `console/tests/test_ticket_liveness.py` (extend); `console/tests/test_context.py` (add a class, never edit existing tests).
- **Tests (first):** `TestDigest::test_in_progress_without_path_shows_line_and_json_key`, `::test_done_and_healthy_tickets_render_as_before`, `TestVerb::test_runs_without_confirm_and_returns_scan`, `::test_mcp_tool_list_contains_ticket_liveness`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_ticket_liveness.py console/tests/test_context.py console/tests/test_mcp.py console/tests/test_mutation_verbs.py`.
- **Done-criteria:** FR-6 checkboxes 3, 4; the real-vault informational scan is task 16.
- **Basis:** two small additive edits to shared files plus tests.

### [x] T-021-09 — `ticket_gate` with the `blocked` branch; CLI and verb wired (3 h)
- **FR:** FR-7 · **Slice:** B · **Depends on:** T-021-08 (routability function reused); T-020 `claim_status`
- **Files:** new `console/server/ticket_gate.py` (`guarded_move(repo_root, ticket_id, stage, now=None)`; `blocked` branch only for now; routability reuses `ticket_liveness`, no second rule engine; the write goes through `backends_mod.default_backend().move` exactly as `verb_handlers.ticket_move` does today :419); `console/server/verb_handlers.py` (`ticket_move` :411 body calls the gate and keeps the `bus_mod.default().publish` call); `console/kanban.py` (`cmd_ticket_move` :68 calls the gate, prints JSON, `SystemExit(1)` on refusal); `console/server/audit.py` (`ACTIONS` +`ticket.block`); new `console/tests/test_ticket_gate.py`.
- **Tests (first):** `TestBlockedGate::test_no_question_refused_lane_unchanged_one_audit_row`, `::test_after_tracker_add_question_move_succeeds`, `::test_empty_owner_no_claim_is_blocked_no_owner`, `::test_other_moves_and_moves_out_of_blocked_unevaluated`, `::test_cli_and_verb_return_same_refusal` (in-process `cmd_ticket_move`), `::test_other_kinds_never_refused`, `::test_invalid_lane_still_raises_valueerror`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_ticket_gate.py console/tests/test_mutation_verbs.py console/tests/test_mcp.py console/tests/test_agents_catalog.py console/tests/test_context.py`.
- **Done-criteria:** all FR-7 checkboxes; `TestTicketMoveSet` (`test_mutation_verbs.py:28`) green unchanged; board drag (`boards_feature.py:64`) untouched.
- **Basis:** new module with one branch, three call-site edits, audit tuple.

### [x] T-021-10 — `close_check` parsers: status classes and evidence refs (3 h)
- **FR:** FR-8 (grammar) · **Slice:** B · **Depends on:** T-021-06 (no T-020 symbol needed here, pure functions)
- **Files:** new `console/server/close_check.py` (pure helpers only in this task: `parse_verification_tables(text)` keeping tables with `Status` and `Evidence` columns, `classify_status(cell)` -> pass/descoped/not_pass, `extract_refs(cell)`, `resolve_ref(repo_root, ticket_id, ref)` -> accepted/missing/unverifiable with `run:<12hex>` via `runs.get` requiring state `done`); new `console/tests/test_close_check_parse.py`.
- **Tests (first):** `TestStatusClass::test_table` (`**PASS**`, "PASS — static only" pass; "PASS / PENDING", "NOT MET", "FAILED" not pass; DEFERRED/CUT/DROPPED/N/A descoped; empty not pass), `TestRefs::test_resolution_table` (nonexistent path, line beyond EOF, absent `::name`, unknown run, `running` run -> missing; bare `tray.rs`, `pytest 1406 passed`, `2 947 ms to 4 ms`, backslash path, `/tmp/x.py`, URL -> unverifiable; accepted: existing `console/x.py:3`, `::test_y` via `(def|class)\s+name\b`, artifact name under the ticket dir), `test_no_subprocess_no_git_no_write`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_close_check_parse.py`.
- **Done-criteria:** FR-8 ref-table and status-class checkboxes; `basis` constant `"existence"` defined here.
- **Basis:** the grammar is fully specified in the draft FR-8; mostly regex and a table test.

### [x] T-021-11 — `close_check.evaluate`, the ten blocks, four warnings, `close-check` verb (3 h)
- **FR:** FR-8 · **Slice:** B · **Depends on:** T-021-10
- **Consumes from T-020:** `tickets.claim_status` (stale blocks, held warns), `review_escalated` ticket field, critical review question through `trackers.blockers` (no new code), `runs.get`.
- **Files:** `console/server/close_check.py` (`evaluate(repo_root, ticket_id, now=None)`; never raises, any exception becomes block `check_error`; blocks `no_verification`, `criterion_not_pass`, `evidence_empty`, `evidence_phantom`, `critical_question_open`, `critical_bug_unverified`, `claim_stale`, `review_escalated`, `plan_open` (via `context.plan_tasks` :67), `check_error`; warnings `evidence_prose_only`, `evidence_partial`, `criterion_descoped`, `claim_held`); `console/config/verbs.toml` (+1 row `close-check`, `needs_ticket`, read-only, hint states "existence, not truth"); `console/server/verb_handlers.py` (`close_check(repo_root, ticket=None)`); new `console/tests/test_close_check.py`.
- **Tests (first):** `TestBlocks::test_each_code_fires_on_planted_fixture_and_not_on_clean` (parametrised, ten codes), `::test_clean_fixture_ok_with_exact_counts`, `TestRowPolicy::test_accepted_plus_missing_is_partial_warn`, `::test_only_missing_is_phantom_block`, `::test_all_prose_table_ok_with_warnings`, `TestT020::test_stale_claim_blocks_held_warns_escalated_blocks_critical_question_blocks`, `TestTotal::test_corrupt_verification_and_injected_exception_return_blocks`, `::test_no_writes`, `::test_50_rows_under_half_second`, `TestVerb::test_on_cli_mcp_and_verb_list` (CLI `verb list`, MCP tool list, and the HTTP verb route using whatever pattern `test_mcp.py`/`test_mutation_verbs.py` already use; if no HTTP test pattern exists, state that the route is generic and cite the registry load).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_close_check.py console/tests/test_close_check_parse.py console/tests/test_mcp.py console/tests/test_mutation_verbs.py`.
- **Done-criteria:** FR-8 checkboxes except the 22-ticket calibration (task 16).
- **Basis:** parser exists after task 10; remainder is fixtures and orchestration of existing readers.

### [x] T-021-12 — Terminal-lane branch of `guarded_move` (2 h)
- **FR:** FR-9 · **Slice:** B · **Depends on:** T-021-09, T-021-11
- **Files:** `console/server/ticket_gate.py` (terminal branch: lane has `terminal = true` per `boards_mod.lanes_for` as in `context.py:174`, ticket kind `tickets`, ticket not already terminal -> `close_check.evaluate`; blocks -> `{ok: False, blocked: True, ticket, blocks, hint}` and audit `ticket.close` `refused: <codes>`; ok -> existing move path then audit `ticket.close` with evidence counts and warning codes; evaluator exception -> block `check_error`); `console/server/audit.py` (`ACTIONS` +`ticket.close`; anchored); `console/tests/test_ticket_gate.py` (add `TestCloseGate`).
- **Tests (first):** `test_open_critical_question_refused_lane_unchanged_audit_row`, `test_clean_ticket_moves_and_audit_carries_counts`, `test_injected_exception_leaves_lane_and_returns_check_error`, `test_cli_and_verb_agree_and_cli_exits_1`, `test_direct_tickets_move_still_unguarded`, `test_non_terminal_reopen_and_other_kinds_not_checked`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_ticket_gate.py console/tests/test_agents_catalog.py console/tests/test_context.py console/tests/test_pr_check_verb.py console/tests/test_mutation_verbs.py`.
- **Done-criteria:** all FR-9 checkboxes; `tickets.move` byte-unchanged (`git diff console/server/tickets.py` empty from this ticket).
- **Basis:** one branch added to a module whose shape task 09 fixed.

### [x] T-021-13 — `close-override` verb (2 h)
- **FR:** FR-10 · **Slice:** B · **Depends on:** T-021-12
- **Files:** `console/config/verbs.toml` (+1 row `close-override`, `needs_ticket`, `needs_confirm`); `console/server/verb_handlers.py` (`close_override(repo_root, ticket=None, reason="")`: trimmed reason >= 10 chars; refuses already-terminal and non-`tickets`; runs `close_check.evaluate`; moves to the board's first terminal lane with `tickets.move` regardless; reuses `ticket_comment` for the comment, author `close-override`; publishes `ticket://{T}` like `ticket_move` :420); `console/server/audit.py` (`ACTIONS` +`ticket.close.override`; anchored); new `console/tests/test_close_override.py`.
- **Tests (first):** `test_empty_and_9_char_reason_refused_no_override_audit_row`, `test_valid_reason_on_blocked_fixture_done_one_audit_row_with_reason_and_codes_one_comment`, `test_without_confirm_raises_verberror`, `test_listed_on_cli_and_mcp`, `test_already_done_and_investigations_refused`, `test_no_blocks_says_no_override_needed`.
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_close_override.py console/tests/test_mutation_verbs.py console/tests/test_mcp.py`.
- **Done-criteria:** all FR-10 checkboxes. Q11 (hard human gate via `gated_tools` in `agents.toml`) stays open and non-blocking; `agents.toml` is not touched.
- **Basis:** small handler composed of existing pieces.

### [x] T-021-14 — Protocol text: close-work, harness, builder, CLAUDE.md (2 h)
- **FR:** FR-11 items 1, 3, 4, 5 · **Slice:** B · **Depends on:** T-021-12, T-021-13 (the text names the shipped verbs)
- **Files (anchored edits):** `.claude/skills/close-work/SKILL.md` (new step 1 runs `python console/kanban.py verb run close-check --ticket {id}` and aborts on `ok:false`, listing block codes; step 4 `ticket move {id} done` (:18) states the guard re-runs the check; Gate (:25) adds "never edit `verification.md` only to satisfy `close-check`; never call `close-override` or invent a reason; only the user supplies one"; steps renumbered by anchored edit, `description:` untouched); `.claude/agents/harness.md` (row :30 "Verification clean": `close-check`, then `close-work` only on `ok`; growth <= 378 chars); `.claude/agents/builder.md` (claim step: on the first task run `verb run claim --ticket {id} agent=<identity>`, re-claim to refresh on long work); `CLAUDE.md` (verifier row :36: `close-work` becomes `close-check`, with "`harness` runs `close-work`"); new `console/tests/test_close_protocol_text.py`.
- **Tests (first):** `test_close_work_mentions_close_check_close_override_and_forbids_agent_reason`, `test_harness_row_has_close_check_and_growth_within_378`, `test_builder_has_claim_step`, `test_claude_md_verifier_row_has_close_check`, `test_contract_headers_intact` (`── Builder ──`, `── Harness ──`), `test_descriptions_byte_identical` (sha256 pinned pre-edit), `test_every_persona_within_cap` (reuses T-021-04's loop).
- **Verify:** `python -m pytest -o addopts="" -q console/tests/test_close_protocol_text.py console/tests/test_persona_fit.py console/tests/test_harness_lint.py`; `python console/kanban.py harness lint` (0 errors, no new `stale-count`, `39 skills, 7 agents`).
- **Done-criteria:** FR-11 checkboxes for these four files; diff limited to them plus tests.
- **Basis:** four prose edits with measured length limits.

### [x] T-021-15 — Protocol text: `verifier.md` step 10 and `Disposition` line (1 h)
- **FR:** FR-11 item 2 · **Slice:** B · **Depends on:** T-021-14; T-020's FR-25 edit of `verifier.md` merged first (T-020 4b-3)
- **Files:** `.claude/agents/verifier.md` (step 10 at :22 today: clean -> report `Disposition`, run `close-check`, hand to `harness` or the user, do not run `close-work`; unmet branch kept; contract gains `Disposition: ready_to_close | needs_fix | blocked | needs_human`; `▶️ Next` line :48 reconciled; header `── Verifier ──` intact; both T-020 FR-25 rules kept); `console/tests/test_close_protocol_text.py` (extend).
- **Tests (first):** `test_verifier_step_10_has_close_check_and_no_close_work_instruction`, `test_verifier_contract_has_disposition_and_header`, `test_verifier_keeps_t020_fr25_phrase` (phrase read from the file as left by T-020, recorded in progress), `test_verifier_description_byte_identical`.
- **Verify:** same command as task 14 plus `console/tests/test_agent_protocol_text.py` if T-020 created it.
- **Done-criteria:** FR-11 checkbox 1 for `verifier.md`, 2, 3, 4 overall; no new file under `.claude/agents` or `.claude/skills`.
- **Basis:** one step and one contract line.

### [x] T-021-16 — Read-only sweep over every existing ticket, calibration, rollback proof (2 h)
- **FR:** FR-6 informational check, FR-8 calibration, BR-1, NFR-4 · **Slice:** B · **Depends on:** T-021-13
- **Files:** optional script `knowledge-center/artifacts/T-021/ticket-scripts/sweep.py` (stdlib; imports `server.close_check`, `server.ticket_liveness`; calls `evaluate`/`scan` only, never `ticket_gate`, never a mutating verb; hashes every file under `knowledge-center/artifacts/` before and after and fails on any difference); results written into [[T-021-verification]].
- **Scope:** T-001..T-022 and CC-T001..CC-T006 (28 dirs with `ticket.toml`). Record per ticket: lane, `close-check` verdict (ok / block codes / warning codes), liveness finding. Calibration over the 22 done tickets: pass rows, `evidence_empty` (expect 0), `evidence_phantom` (expect <= 3 of 212), prose-only share (expect ~84 %); more than 10 % of pass rows blocked means the parser is wrong: fix the parser, not the tickets. Note T-021 and T-022 themselves will show blocks (open plan tasks); that is expected, not a defect.
- **Verify:** `python knowledge-center/artifacts/T-021/ticket-scripts/sweep.py` prints the table and `files changed: 0`; `python console/kanban.py verb run ticket-liveness` agrees with the sweep's liveness column.
- **Done-criteria:** table and counts in [[T-021-verification]]; hash check proves 0 writes; no existing ticket moved or edited.
- **Basis:** a loop plus a table; most time is reading outliers.

### Rollback (written before build, kept in [[T-021-progress]])

Slice A: revert per file; `description-too-long` is removed by deleting the constant and its `if`; doc and prompt edits revert independently. Slice B: no data migration exists (no `ticket.toml` field, no tracker kind), so rollback is code only. (1) To switch the gates off while keeping the read-only checks: revert the body of `verb_handlers.ticket_move` (:411) and `kanban.cmd_ticket_move` (:68) to the direct call they make today; `ticket_gate.py` becomes unused and `tickets.move` was never modified. (2) To remove everything: delete `ticket_liveness.py`, `close_check.py`, `ticket_gate.py`, the three `verbs.toml` rows, the three handlers, the `context.py` key and line, and the three `ACTIONS` entries; audit rows already written stay (append-only, harmless). (3) Emergency bypass without code: the board drag (BR-11), `tickets.move` directly, or `close-override` with a reason by the user. Protocol text reverts per file; revert text and gate together so agents are not told to call a verb that is gone.

### Final VERIFY phase

### [x] T-021-17 — Full-suite verification and AC evidence table (2 h)
- **FR:** all, NFR-1, NFR-3, NFR-4, NFR-7 · **Slice:** B (also closes A) · **Depends on:** T-021-01..16
- **Steps:** (1) `python -m pytest -o addopts="" -q` from the repo root: record the count, compare to the touched-module baseline taken before task 01 (record that baseline in [[T-021-progress]] at start; T-020's 3 date-rot failures must already be fixed by T-020); no new failure. (2) `python console/kanban.py harness lint`: 0 errors, `39 skills, 7 agents`, warnings = BASELINE + 20 `description-too-long`, no other new code, no `stale-count`. (3) `git status --short console/static` empty and `git diff --stat` shows no `agents.toml`, no new directory under `.claude/skills` or `.claude/agents`, only 3 added rows in `verbs.toml`. (4) grep the new tests for `subprocess`, `socket`, `urllib`, `openai`: none (NFR-3); new tests under 30 s (`--durations=10`). (5) fill the table in [[T-021-verification]]: one row per FR checkbox with evidence as file:line or test node id, plus the calibration and sweep results from task 16. (6) `reconcile`, then hand to `verifier` (who reports a Disposition; closing runs behind `close-check`, using the gate this ticket built).
- **Done-criteria:** every row cited; no row says PASS without a command output or file:line; deviations listed.
- **Basis:** commands and writing the table; no code.

**AC evidence table skeleton (for [[T-021-verification]])**

| AC | Task | Evidence (command output or file:line) | Status |
|----|------|----------------------------------------|--------|
| FR-1 (5) | 01 | | |
| FR-2 (4) | 03 | | |
| FR-3 (5) | 05 | | |
| FR-4 (3) | 02 | | |
| FR-5 (5) | 04 | | |
| FR-6 (6) | 07, 08, 16 | | |
| FR-7 (5) | 09 | | |
| FR-8 (8) | 10, 11, 16 | | |
| FR-9 (6) | 12 | | |
| FR-10 (4) | 13 | | |
| FR-11 (4) | 14, 15 | | |
| NFR-1..8 | 17 | | |
| Calibration and real-vault sweep | 16 | | |

<!-- TASKS-END -->

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| 01 lint length + baseline | 1.5 h | one rule, five tests |
| 02 README count | 1 h | loop over two paths |
| 03 task-boundary text | 1.5 h | prose + 4 tests |
| 04 assistant trim | 2 h | rewording against a measured budget |
| 05 stale docs | 2 h | five files + greps |
| 06 T-020 gate | 0.5 h | greps |
| 07 liveness module | 2.5 h | 17-row table |
| 08 liveness verb + digest | 2 h | two shared-file edits |
| 09 gate (blocked) | 3 h | new module, 3 call sites |
| 10 close-check parsers | 3 h | grammar from draft |
| 11 close-check evaluate | 3 h | ten blocks, four warnings |
| 12 guarded close | 2 h | one branch |
| 13 close-override | 2 h | composed handler |
| 14 protocol text (4 files) | 2 h | measured prose |
| 15 verifier.md | 1 h | one step |
| 16 sweep + calibration | 2 h | script + reading outliers |
| 17 final verify | 2 h | commands + table |
| **Total** | **33 h** (A 8, B 23, VERIFY 2) | task sizes, no history of similar tickets; +20 % on 09-11 if T-020 names drift |

### Acceptance criterion coverage

Every FR checkbox is mapped in the skeleton table under task 17; FR-to-task: FR-1 01 · FR-2 03 · FR-3 05 · FR-4 02 · FR-5 04 · FR-6 07/08/16 · FR-7 09 · FR-8 10/11/16 · FR-9 12 · FR-10 13 · FR-11 14/15 · NFR-1..8 17 (NFR-3 also in every test task, NFR-5 in 09/12/13, NFR-6 in 07/11). Ticket-level acceptance (lint 0 errors and measured warnings only, roster line, baseline, calibration): 01, 17, 16. 11/11 FR covered.

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| T-020 symbol renamed or not yet built when Slice B starts | Med | High | task 06 gate with file:line citations; stop if `claim_status` absent; adapt and log | Builder |
| Shared-file edit clobbers T-020 work (`verbs.toml`, `verb_handlers.py`, `context.py`, `audit.py`, `agents.py`, `verifier.md`) | Med | High | anchored Edit only, Read before edit, grep that T-020 additions survive; `agents.py` comment last | Builder |
| Calibration shows > 10 % of historical pass rows blocked (parser defect) | Med | Med | task 16 gate; fix parser, never tickets; fail-closed stays | Builder |
| Assistant trim changes behaviour or drops a rule | Low | Med | length measured via `persona_text`; test pins every Safety bullet and the clause; no rule deleted | Builder |
| Lint gains 20 warnings; "0 warnings" criteria in T-020/T-022 become false | High | Low | criteria read "no new warnings vs BASELINE"; orchestrator amends listed lines | Orchestrator |
| Gate refuses a legitimate close that agents then work around | Med | Med | human `close-override`; rollback paragraph; BR-11 board drag stays open | Builder |
| Q11 hard human gate not configured | Med | Low | non-blocking, stated in verb hint and protocol text; user adds tool name to `gated_tools` | User |
| Windows path handling in ref resolver (`/` only, backslash unverifiable) | Low | Med | table test rows for backslash, `/tmp`, URL | Builder |

No high x high risk.

## Dependencies
- Blocks: T-022 pins quotes after T-020 and T-021 are built (see "Prompt-facing files edited").
- Blocked by: T-020 built and verified, for Slice B only.

## Prompt-facing files edited (for T-022's planner)

| File | Task | Text change (descriptions stay byte-identical) |
|------|------|-----------------------------------------------|
| `console/config/assistant.md` | 04 | `## Known fast commands` removed; two sections reworded shorter; untrusted-content clause in `## Safety` (phrase `data, not instructions`; clipboard, OCR, screenshot, web) |
| `.claude/skills/plan/SKILL.md` | 03 | new `Task boundary rule` with five bold labels |
| `.claude/skills/breakdown-tasks/SKILL.md` | 03 | points to the plan rule; "ideally one component per task" dropped |
| `.claude/skills/close-work/SKILL.md` | 14 | first step `close-check`; Gate forbids editing `verification.md` to satisfy it and agent use of `close-override` |
| `.claude/skills/console/SKILL.md` | 05 | one sentence: OpenRouter row ships `enabled = true` |
| `.claude/agents/verifier.md` | 15 | step 10: `Disposition`, `close-check`, no `close-work`; contract line `Disposition:` (on top of T-020 FR-25) |
| `.claude/agents/harness.md` | 14 | "Verification clean" row: `close-check` then `close-work` only on `ok` (<= +378 chars) |
| `.claude/agents/builder.md` | 14 | claim step on the first task |
| `CLAUDE.md` | 14 | verifier row: `close-check`; harness runs `close-work` |

Scenarios worth pinning in T-022: injected instruction in clipboard text not obeyed; verifier stops at `close-check` and does not run `close-work`; builder claims on its first task. T-022 quotes must be taken after T-020 and T-021 are built.

## Criteria for the orchestrator to amend (not edited here)

After T-021 ships `harness lint` reports 0 errors and BASELINE + 20 warnings. These lines say "0 warnings" and should read "no new warnings vs the pre-ticket baseline (T-021 adds 20 `description-too-long` warnings)" if they are verified after T-021 ships; they stay true if verified before:
- `T-020-requirements.md:256` and `:343`
- `T-020-implementation-plan.md:268` and `:279`
- `T-022-requirements.md:179`
- `T-022-plan.md:166`

## Orchestrator CLI steps

1. `python console/kanban.py ticket move T-021 in-progress` when task 01 starts (ungated: not a terminal or `blocked` move).
2. Run Slice A tasks any time; start Slice B only after T-020 is verified (task 06).
3. After each task: `progress-tracker`, tick the plan heading `[x]`.
4. Before closing: task 17, then `python console/kanban.py verb run close-check --ticket T-021` (built by this ticket) and `close-work`. If it blocks, fix the cause; `close-override` is the user's call only.
5. Optional (Q11): the user adds `mcp__console__close-override` and `console_close_override` to `gated_tools` in `agents.toml` by hand.

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-requirements-draft]] · [[T-021-decision-log]] · [[T-021-critique-report]] · [[T-021-user-stories]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
- Dependency: [[T-020-requirements]] · [[T-020-implementation-plan]]
