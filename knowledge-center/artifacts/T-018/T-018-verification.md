---
ticket: "T-018"
artifact: verification
status: complete
verified_date: "2026-09-16"
---

# Verification: T-018

Scope run: `challenge-implementation` → `verify cases` (no test-cases template exists in this
workspace — `knowledge-center/artifacts/_template/` has no `test-cases.md`; AC↔test traceability
is captured inline below instead of a separate artifact, per TEMPLATE gate) → `verify ready` →
`validate-artifacts structure`+`links` → `reconcile`.

Independently re-run, not trusted from the builder's handback: `pytest console/tests -o addopts="" -q`
from `D:\Workspace\noble-workspace\control-center-workspace` → **1406 passed in 1313.13s (0:21:53)**,
exit code 0. Matches the builder's claimed final count exactly.

## Acceptance Criteria

| # | Criterion (from T-018-requirements.md) | Status | Evidence |
|---|---|---|---|
| AC1 | `launch_role` for a ticketed Run runs with `cwd` under the worktree root, not `repo_root`; a second call for the same ticket reuses the same worktree | PASS | `console/server/agent_manager.py:65-81` (`_resolve_worktree`: `_find` before `add`, decision-log a3) and `:123-127` (`create()` only resolves when `ticket` truthy). Test: `console/tests/test_agent_manager_worktree.py::TestResolveWorktree::test_creates_a_worktree_for_a_new_ticket`, `::test_reuses_the_existing_worktree_rather_than_recreating` (asserts only 1 managed worktree entry after two calls) — both run against a real git repo fixture, not mocks. |
| AC2 | A ticketless chat's `cwd` is unchanged (`repo_root`) | PASS | `agent_manager.py:123-127`: `cwd = repo_root` unconditionally, only overwritten inside `if ticket:`. Test: `test_agent_manager_worktree.py::TestResolveWorktree::test_ticketless_call_site_never_reaches_worktree_resolution` (asserts zero non-main managed worktrees exist after a ticketless path). |
| AC3 | A non-git-repo or worktree failure produces a Run with `cwd = repo_root` and a visible fallback reason, no exception | PASS | `agent_manager.py:80-81` catches `WorktreeError`, returns `(repo_root, "", "", str(exc))` — never raises. Surfaced end-to-end: `verb_handlers.py:223-225,338-340` thread `worktree_error` onto the Run record; `verb_handlers.py:361-381` (`_enrich_run`) sets `worktree_display` to the error text for a ticketed Run with no path (line 378-379) — this is the field `agents.js:235` renders in the Run detail line, i.e. genuinely visible in the UI, not just logged. Test: `test_agent_manager_worktree.py::test_falls_back_to_repo_root_on_non_git_repo` (asserts `"not a git repository" in error`); `test_run_inspector_data.py::test_ticketed_run_with_a_fallback_shows_the_reason_not_blank`. |
| AC4 | A worktree created for `T-018` has a branch matching the configured pattern | PASS | Test: `test_agent_manager_worktree.py::test_creates_a_worktree_for_a_new_ticket` asserts `branch == "agent/T-018"` (default `branch_pattern`); `console/tests/test_worktrees.py::test_branch_pattern_comes_from_config` covers the underlying config-driven pattern in `worktrees.add`. |
| AC5 | `ticket.toml`'s new fields default cleanly on old tickets and persist correctly when set; mutation publishes to the MCP bus | PASS (with one worded caveat) | `console/server/tickets.py` `set_pr` under `tomlio.atomic_update`; `create()`/`load()` default all three to `""`. Tests: `test_tickets.py::TestSetPr::test_created_ticket_starts_with_empty_git_fields`, `::test_set_pr_sets_all_three`, `::test_partial_update_leaves_others_unchanged`, `::test_an_older_ticket_toml_without_pr_fields_still_loads` (deletes the keys from an on-disk `ticket.toml`, reloads, confirms `""` defaults), `::test_missing_ticket_raises`. Bus publish: happens at the `pr_check` verb (`verb_handlers.py:520`, `bus_mod.default().publish(...)`), not inside `set_pr` itself — same split T-017 already uses for `set_claim`/`ticket_claim` (verified by reading `ticket_claim` at `verb_handlers.py:437-458`, which likewise publishes outside the setter). **Caveat:** FR-5's literal wording ("mutated only through a dedicated setter... publishing to the MCP change bus on every mutation") reads as if the setter itself publishes; in practice only the verb-level caller does, so a hypothetical direct `set_pr` call bypassing `pr_check` would not publish. This mirrors an existing, already-accepted T-017 pattern and is not a new gap this ticket introduces — flagging as a documentation-precision note, not a functional FAIL. |
| AC6 | Mocked `gh pr view` responses (OPEN/MERGED/none/ambiguous) drive `pr_state` correctly, including a clear non-fatal error for `gh` missing/unauthenticated | PASS | `console/server/pr_state.py:39-82` (`pr_state_for`) never raises — catches `FileNotFoundError`/`OSError`, pattern-matches `gh`'s stderr for "not logged into"/"authentication" and "command not found"/"not recognized". Tests: `console/tests/test_pr_state.py::test_open_pr_maps_correctly`, `::test_merged_pr_maps_correctly`, `::test_closed_pr_maps_correctly`, `::test_no_pr_for_branch`, `::test_ambiguous_output_does_not_raise`, `::test_gh_missing_is_non_fatal`, `::test_gh_unauthenticated_is_non_fatal`, `::test_no_branch_is_a_clean_error_not_a_crash` (8/8, all mocked subprocess). |
| AC7 | A PR-state transition surfaces a suggestion without ever calling `ticket_move`/`close-work` — verifiable by code inspection/grep | PASS — hard gate independently confirmed | See "a4 hard-gate" section below. |
| AC8 | The Run inspector shows a real `git diff --stat` for a worktree-backed Run, "shared tree" for a ticketless one, and telemetry-accurate cost/tokens | PASS | `console/server/worktrees.py::diff_stat` (shell-out, same pattern as `_git`); `verb_handlers.py:361-389` (`_enrich_run`): `worktree_display` = path / error / `"shared tree"` (line 381), `diffstat` computed only when a path exists, `cost_usd`/`tokens` from `_telemetry_by_session` aggregation. Wired into both `run_list` (`:392-399`) and `run_show` (`:403-408`), and `/api/runs` route dispatches through `verb_handlers.run_list` (confirmed in `console/server/features/verbs_feature.py`) rather than calling `runs_mod.list_runs` directly, so the enrichment is not bypassable from that route. Frontend: `console/static/agents.js:233-272` (`runDetailLine`, `copyPathButton`) renders `worktree_display`, diffstat, tokens/cost — grepped directly, `worktree_display`/`worktree_path` are real property reads, not placeholder text. Tests: `test_worktrees.py::TestDiffStat` (4 cases: missing path, empty path, clean, real change); `test_run_inspector_data.py::test_ticketless_run_shows_shared_tree`, `::test_ticketed_run_with_real_worktree_shows_its_path`, `::test_ticketed_run_with_a_fallback_shows_the_reason_not_blank`, plus `test_ui_endpoints.py` (1 case, `/api/runs` route). No browser/manual UI test was run — `agents.js` was checked via `node --check` (syntax only, per builder) and by direct code read here; this AC's UI half is verified by static inspection of the rendering code plus the server-side data contract tests, not a live browser session. |

**Static-only note:** AC8's client-side rendering and AC3's "visible in the UI" claim are verified by reading `agents.js`'s actual rendering code and confirming the field names line up end to end (server → JSON → JS property read), not by running the console in a browser. Everything else (AC1-AC7) is backed by real pytest execution against real git repos / mocked subprocess, re-run by the verifier, not narrated.

## a4 Hard Gate — Independent Verification (lane hints never call ticket_move/close-work)

Read `console/server/verb_handlers.py` directly (not the builder's description of it):

- `_lane_hint` (lines 478-495): body calls only `trackers_mod.add(...)`. No `ticket_move`, no `close_work`/`close-work` call.
- `pr_check` (lines 498-522): calls `tickets_mod.load`, `pr_state_mod.pr_state_for`, `tickets_mod.set_pr`, `bus_mod.default().publish`, and `_lane_hint`. No `ticket_move`, no `close_work` call.

Confirmed by reading the source directly — this repo-wide `grep -n "ticket_move|close_work" console/server/verb_handlers.py` finding only the `ticket_move` function's own definition (line 411) and doc-comment mentions in unrelated verbs (`ticket_ready`, `ticket_claim`, `ticket_comment` docstrings referencing "same pattern as `ticket_move`" — prose only, not calls).

**On the builder's test claim:** `console/tests/test_pr_check_verb.py::TestLaneHint::test_never_calls_ticket_move_or_close_work` (lines 115-135) AST-walks **`_lane_hint` only** (`inspect.getsource(verb_handlers._lane_hint)`) — it does **not** AST-walk `pr_check`, despite the builder's progress-log note ("AST-walks `_lane_hint` and `pr_check`'s actual call sites"). That specific claim is an overstatement of the test's actual coverage — a minor documentation-accuracy finding (§ Notes below), **not a functional gap**: this verifier independently read `pr_check`'s full body (above) and confirmed by direct inspection, not by trusting the mismatched test description, that it also contains no `ticket_move`/`close_work` call. There are also four behavioral tests (`test_pr_open_suggests_verify_via_comment`, `test_pr_merged_suggests_done_via_comment`, `test_no_transition_no_suggestion`, `test_merge_while_already_done_has_no_suggestion`) confirming the suggestion surfaces via the `comments` tracker with the expected text, not a lane change.

**Verdict: a4 hard gate HOLDS.** Confirmed independently, not a repeat of the builder's claim.

## Test Results

- Full suite (verifier-run, this session): `pytest console/tests -o addopts="" -q` → **1406 passed**, 0 failed, 0 errors, 1313.13s. Exit code 0.
- T-018-scoped subsets spot-checked by file during this review: `test_tickets.py::TestSetPr` (5), `test_agent_manager_worktree.py` (4), `test_pr_state.py` (8), `test_pr_check_verb.py::TestLaneHint` (5), `test_worktrees.py::TestDiffStat` (4), `test_run_inspector_data.py` (4) — all included in and consistent with the 1406-passed full-suite run above.
- No JS/browser test run for `console/static/agents.js` beyond `node --check` (syntax only) — same limitation the builder disclosed; not independently re-verified by this verifier beyond re-reading the diff.

## Edge Cases Probed
- Non-git-repo worktree resolution (AC3) — falls back cleanly, error surfaced (`test_falls_back_to_repo_root_on_non_git_repo`).
- Same-ticket concurrent/sequential worktree reuse, not recreation (AC1, decision-log a3) — `test_reuses_the_existing_worktree_rather_than_recreating`.
- `ticket.toml` missing the new fields entirely (pre-T-018 record) (AC5) — `test_an_older_ticket_toml_without_pr_fields_still_loads`.
- `gh` binary missing, `gh` unauthenticated, ambiguous/unparseable `gh` output, no PR for branch (AC6) — all 4 in `test_pr_state.py`.
- Lane hint while ticket already at the target stage (no-op, no duplicate suggestion) — `test_no_transition_no_suggestion`, `test_merge_while_already_done_has_no_suggestion`.
- Run inspector: missing worktree path, empty worktree path, ticketless run, fallback run (AC3, AC8) — `TestDiffStat` + `test_run_inspector_data.py`.
- Not probed by anyone (builder or this verifier): a genuinely concurrent `pr-check` race against a concurrent `set_claim`/`ticket_move` on the same ticket; large-diff `git diff --stat` output truncation/rendering; a `gh` CLI that is installed+authenticated but times out mid-call (no timeout is set on the `subprocess.run` in `pr_state.py:22-30`, unlike none is claimed either way in the requirements — NFR-1 says "sub-second and non-blocking" but nothing enforces a hard timeout if `gh` itself hangs). Flagging as a minor NFR-1 gap, not AC-blocking since no AC asserts a timeout.

## Traceability (Requirement -> Task -> Code -> Test)

| FR | Task ID | Code | Test |
|---|---|---|---|
| FR-1/2/3/4 | 2a-1 (T-018-03) | `agent_manager.py:65-180` | `test_agent_manager_worktree.py` (4 tests) |
| FR-5 | 1a-1, 3a-2 (T-018-01, T-018-06) | `tickets.py::set_pr` | `test_tickets.py::TestSetPr` (5 tests) |
| FR-6 | 3a-1 (T-018-05) | `pr_state.py` | `test_pr_state.py` (8 tests) |
| FR-7 | 3b-1, 3b-2 (T-018-07, T-018-08) | `verb_handlers.py::pr_check`, `_lane_hint` | `test_pr_check_verb.py` (9 tests incl. `TestLaneHint`) |
| FR-8 | 4a-1, 4a-2, 4b-1 (T-018-09..11) | `worktrees.py::diff_stat`, `verb_handlers.py::_enrich_run`, `agents.js` | `test_worktrees.py::TestDiffStat`, `test_run_inspector_data.py`, `test_ui_endpoints.py` |

Traceability chain (`validate-artifacts links`, manual cross-check since no `test-cases.md` exists): every FR in `T-018-requirements.md` maps to a `T-018-task-breakdown.md` row, every task row cites the file it touched and (for build tasks) the test file covering it, and every test file above exists on disk and was included in the 1406-passed run. No orphaned FR (all 8 mapped) and no orphaned task (all 11 rows in task-breakdown.md map to one of the 8 FRs). **Coverage: 8/8 FRs traced to code + test = 100%.**

## Reconcile — Drift Check

- `T-018-task-breakdown.md` marks all 11 tasks `done`, 100% per phase — consistent with the actual diff read during this review (all files/functions named in the breakdown exist as described).
- `T-018-progress.md`'s final entry claims `1406 passed` — matches this verifier's independent re-run exactly. No drift.
- `T-018-summary.md`'s Stage line still reads "TEMPLATE complete (build) — ready for VERIFY" as of this write — accurate; not yet updated to reflect VERIFY has run (updated as part of this pass, see below).
- One documentation-accuracy drift found: `T-018-task-breakdown.md` row 3b-2's Notes and `T-018-progress.md`'s Phase-3 entry both state the AST test "walks `_lane_hint` and `pr_check`'s actual call sites" — the test as written (`test_pr_check_verb.py:115-135`) only walks `_lane_hint`. Not corrected here (verifier does not edit builder artifacts) — flagged for the human/builder to amend the wording, and independently re-verified functionally sound in this file's "a4 Hard Gate" section above.
- No other drift found between `T-018-requirements.md` (frozen), `T-018-decision-log.md` (a1-a5), `T-018-task-breakdown.md`, and the code.

## Notes
- **Minor finding 1 (documentation accuracy, non-blocking):** builder's progress/task-breakdown notes overstate `test_never_calls_ticket_move_or_close_work`'s scope (claims it covers `pr_check` too; it only AST-walks `_lane_hint`). Functionally verified sound anyway by this verifier's direct source read of `pr_check`. Recommend a wording fix or an added `pr_check` AST assertion in a follow-up, not a blocker to close.
- **Minor finding 2 (NFR precision, non-blocking):** `pr_state.py`'s `_gh()` subprocess call has no explicit timeout; NFR-1 ("stays sub-second and non-blocking") is not enforced against a hung `gh` process. No AC asserts this, so not a FAIL, but worth a follow-up if `gh` calls end up scheduled unattended (`schedules.py`).
- **No `T-018-test-cases.md` artifact exists** and none was created by this verifier — no template for that artifact type exists in `_template/`, so per the TEMPLATE gate none was fabricated; AC↔test traceability is captured inline in this file instead.
- No browser/manual UI test was run against `console/static/agents.js`'s new rendering; verified by static code read + the server-side data-contract tests only.
- `validate-artifacts structure`: all 20 T-018 artifact files present, each carries a `## Links` block referencing the ticket's core cluster; `ticket.toml`/tracker `.toml` files present and CLI-shaped (not hand-edited, per `git status` showing them as tracked/unmodified by this session).
- `validate-artifacts links`: cross-links between `-summary`, `-requirements`, `-decision-log`, `-plan`, `-progress`, `-verification` all resolve bidirectionally; artifact-map.md row present and correctly wikilinked to `[[T-018-summary]]`.

## Addendum (2026-09-16) — Follow-up fix re-verify: `gh` shell-out timeout

Re-check of a fixer follow-up to Minor finding 2 above (no timeout on `pr_state.py`'s `gh`
shell-out). Independently re-read the current file and re-ran tests myself; did not trust the
fixer's reported numbers.

**Wiring, confirmed by direct read of `console/server/pr_state.py`:**
- `pr_state.py:24` — `_GH_TIMEOUT = 15` module constant, with a doc comment explaining the choice
  (network round-trip vs. not blocking an unattended `schedules.toml` run indefinitely).
- `pr_state.py:31` — `_gh()`'s `subprocess.run(...)` call passes `timeout=_GH_TIMEOUT`, confirmed
  actually wired into the real call, not a dead constant.
- `pr_state.py:66-68` — `pr_state_for` catches `subprocess.TimeoutExpired` in its own `except`
  branch, positioned **before** `except OSError:` (line 69). Checked whether this ordering
  matters: `subprocess.TimeoutExpired` subclasses `SubprocessError`, not `OSError`, so the two
  clauses are actually disjoint and order does not affect which one fires either way — but the
  fixer placed it first regardless, so there is no masking risk under either exception-class
  hierarchy. Confirmed the branch is reachable (not shadowed) and returns the same non-fatal
  `{"pr_url": "", "pr_state": "", "error": ...}` shape as the missing-gh/unauthenticated-gh cases,
  never raising — matches the docstring's claim at lines 48-51.

**Test, confirmed real (not tautological):** `console/tests/test_pr_state.py:64-71`
(`test_gh_timeout_is_non_fatal`) mocks `subprocess.run` to raise `subprocess.TimeoutExpired`
(matching the exact exception `subprocess.run(..., timeout=...)` raises on a real timeout) and
calls the **public** `pr_state.pr_state_for(...)` entry point — not `_gh()` in isolation — then
asserts the returned dict has `pr_state == ""` and `"timed out" in error` with no exception
propagated. If the `except subprocess.TimeoutExpired` branch above were removed, this test would
fail with an unhandled `TimeoutExpired` traceback, so it is a real regression guard, not theater.

**Fresh pytest re-run (this session, not repeated from the fixer's log):**
- `pytest console/tests/test_pr_state.py console/tests/test_pr_check_verb.py -o addopts="" -q`
  → **19 passed** in 6.28s, exit code 0. Matches fixer's claimed count.
- `pytest console/tests -o addopts="" -q` (from `D:\Workspace\noble-workspace\control-center-workspace`)
  → **1407 passed** in 89.46s, exit code 0. One more than this file's earlier full-suite run
  (1406) because `test_gh_timeout_is_non_fatal` is a net-new test added by this fix — consistent,
  not a discrepancy. No warnings surfaced in this run's `-q` output (warning summary is not shown
  under `-q`; not itself evidence the pre-existing warning is gone, only that it isn't a failure).

**Pre-existing `test_tomlio.py` warning claim, sanity-checked:** read
`console/tests/test_tomlio.py` directly — it contains `test_concurrent_writers_do_not_corrupt`
(line 92) and `test_concurrent_updates_do_not_corrupt_or_lose_writes` (line 150), both spinning up
4 `threading.Thread` writers against the same file (lines 99-106, 165-168). This is plausibly the
source of a Windows file-lock race warning independent of this fix; `test_tomlio.py` imports
nothing from `pr_state.py` and exercises an unrelated module (`tomlio`), so the claim that it is
unrelated to the `gh` timeout fix holds up on inspection. Both full-suite runs in this file (1406
before, 1407 now) passed cleanly with 0 failures, so whatever this warning is, it is not gating.

**Regression check — a4 hard gate and the other 7 ACs:** `console/server/verb_handlers.py` was
re-read at the `pr_check`/`_lane_hint` call sites (lines 478-522, unchanged from the a4-gate
section above) — `pr_check` still calls `pr_state_mod.pr_state_for(repo_root, branch)`
unconditionally (line 513) and only reads `result["pr_state"]`/`result["pr_url"]`/`result["error"]`
off the returned dict; the fix does not change that dict's shape (still 3 keys, same names on
every branch including the new timeout one), so `_lane_hint`'s downstream logic is unaffected.
`git status` at the time of this addendum shows the fix isolated to `console/server/pr_state.py`
and the new `console/tests/test_pr_state.py::test_gh_timeout_is_non_fatal` test — no other T-018
source file changed as part of this follow-up.

**Verdict: PASS.** Timeout is genuinely wired (not a dead constant), the new exception branch is
reachable and non-fatal, the test is a real regression guard exercising the public path, the fresh
full-suite run is green at 1407/1407, and the a4 gate plus AC1-AC8 are unaffected. Minor finding 2
above is now resolved by this fix; no other findings from the original pass reopened.

## Links
- [[T-018-summary]] · [[T-018-analysis]] · [[T-018-requirements]] · [[T-018-decision-log]] · [[T-018-plan]] · [[T-018-progress]] · [[T-018-verification]]
