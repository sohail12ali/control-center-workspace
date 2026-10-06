---
ticket: "T-039"
artifact: verification
---

# Verification: T-039

## Acceptance Criteria

Verified 2026-10-06 by the verifier: tests re-run and code read; builder numbers were not copied. [BROWSER] rows cite the parent section below where it covers them. Nothing in this table claims browser behaviour the verifier saw.

| # | Tag | Status | Evidence |
|---|-----|--------|----------|
| AC-1.1 | PY | PASS | `console/tests/test_attention.py::test_payload_has_both_lists_and_exact_counts` asserts the four keys and counts == list lengths (2/0); `overview.py:107-123`. |
| AC-1.2 | PY | PASS | `console/tests/test_attention.py::test_open_answered_and_resolved_questions_land_apart`: open in `needs_you` only, `answered` (type answered) in `needs_repair` only, resolved/closed in neither; `overview.py:70-77`. |
| AC-1.3 | PY | PASS | `console/tests/test_attention.py::test_pending_approval_is_needs_you_only`, `console/tests/test_attention.py::test_repair_kinds_and_what_is_left_out` (failed/timed_out/scheduled_retry runs, blocked, stale, unowned in; done run and done-lane ticket out), `console/tests/test_attention.py::test_review_escalation_adds_no_entry_of_its_own`. |
| AC-1.4 | PY | PASS | `console/tests/test_attention.py::test_legacy_keys_keep_their_shape`; `git diff --numstat test_attention.py` = 222 added, 0 deleted, so the existing assertions are untouched and pass; `overview.py:110-120` legacy keys; `assistant.js:123` reads `attention.blocked`, kept. |
| AC-1.5 | PY | PASS | `console/tests/test_attention.py::test_payload_has_both_lists_and_exact_counts` checks `id,title,kind,stage,type,href` on every needs_you entry and `ref`/`priority` on the question; approval `href: agents` (`overview.py:81-82`). |
| AC-2.1 | PY | PASS | `console/tests/test_attention.py::test_needs_attention_writes_nothing_and_leaves_approvals_pending` hashes the artifacts dir and `console/.cache/runs` of a temp repo before/after two calls: equal; approval still pending. |
| AC-2.2 | PY | PASS | `console/tests/test_attention.py::test_overview_source_calls_no_mutator`; I also read `overview.py` in full: only reads (`list_items`, `list_runs`, `pending_all`). |
| AC-2.3 | PY | PASS | `console/tests/test_fresh_source.py::test_ac23_attention_rows_only_navigate` (attnGroup, moreRow, rowNav, ofType free of `C.post(`/dismiss/clear/done; the only `C.post(` is in `jobRow`, `overview.js:198`). |
| AC-2.4 | BROWSER | not verified in a browser | Source: row `onclick` only calls `api.go` (`overview.js:20-23,46`). Network-panel check not run. |
| AC-3.1 | PY | PASS | `console/tests/test_attention.py::test_needs_you_is_capped_at_50_with_the_exact_count` (60 questions: 50 rows, count 60); `overview.py:102,121`. |
| AC-3.2 | PY | PASS | `console/tests/test_attention.py::test_needs_you_order_is_approval_then_critical_then_normal`. |
| AC-3.3 | PY | PASS | `console/tests/test_attention.py::test_repair_groups_keep_cap_8_with_exact_counts` (10 unowned: 8 rows, count 10). |
| AC-3.4 | BROWSER | not verified in a browser | Code read: `overview.js:352` adds `moreRow(counts.needs_you - rows)`, chip = `counts.needs_you` (`:358`). The parent run had 13 items, below the cap. |
| AC-4.1 | PY | PASS | `console/tests/test_attention.py::test_question_ref_is_the_tracker_item_id` (Q1..Q3). |
| AC-4.2 | BROWSER | not verified in a browser | Source: `attnGroup` prints `r.id + " " + r.ref + " "` then the title (`overview.js:28-29`). The parent section does not record row text. |
| AC-5.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac51_two_attention_panels_and_seven_overview_ids` (exactly the 7 `ov.*` literals, needsPanel before attnPanel); `test_splitter.py` `_OV_IDS` has 7 entries, 19 overall; the enter-guard test was updated deliberately per amendment A2 and asserts both panels call `rowNav` (`git diff test_splitter.py`). |
| AC-5.2 | BROWSER | partly observed by the parent | Parent section: Needs you (13) directly above Needs repair (3). Exact titles, independent folding and fold memory after reload: not verified in a browser. |
| AC-5.3 | BROWSER | not verified in a browser | Empty-state strings are in source (`overview.js:357,386-387`) and match FR-5; rendering not observed. |
| AC-5.4 | BROWSER | not verified in a browser | `rowNav` header guard read at `overview.js:61`. See defect D-A (Enter on the Refresh button). |
| AC-5.5 | PY | PASS | `console/tests/test_fresh_source.py::test_ac55_about_names_needs_you`; `about.js:25`. |
| AC-6.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac61_the_badge_counts_needs_you_only`; `app.js:292-294` reads `c.needs_you` only. |
| AC-6.2 | BROWSER | partly observed by the parent | Parent section: badge 13 with title/aria-label "13 items need you". The 2-questions-plus-failed-run case and the hidden-at-zero case: not verified in a browser. |
| AC-6.3 | BROWSER | not verified in a browser | `setInterval(refreshBadges, 30000)` is untouched (pinned in `test_ac61`). |
| AC-7.1 | PY | PASS | Read `console/static/core.js:228-249`: without `opts.fresh`, `live` is null and nothing is added; the existing panel/UI tests pass (`console/tests/test_ui_constraints.py`, `console/tests/test_stylesheet.py`; focused run 186 passed, 1 known failure). |
| AC-7.2 | PY | PASS | `console/tests/test_fresh_core.py::test_ac72_the_threshold_is_stale_at_the_limit_not_below_it` and `::test_ac72_a_future_time_has_age_zero_and_nan_is_stale` run under node v24 (not skipped): 299 s fresh, 300 s stale (age 300), future time age 0, NaN/null/undefined stale; `core.js:343-347`. |
| AC-7.3 | BROWSER | partly observed by the parent | Parent section: STALE chip text + role=status + visible on a scratch panel with a 10 min old `asOf`; chip empty while fresh. Collapsed stale panel: not verified in a browser. |
| AC-7.4 | BROWSER | partly observed by the parent | Age text steps are PASS under node (`console/tests/test_fresh_core.py::test_ac74_the_age_text_steps`); the parent saw "just now" and "10 min ago". Advancing with no new request: not verified in a browser. |
| AC-8.1 | PY | PASS | `console/tests/test_attention.py::test_full_overview_generated_at_uses_the_injected_now` (2026-10-06T09:05:07Z) and `console/tests/test_attention.py::test_full_overview_generated_at_matches_the_pattern_without_now`; `overview.py:164-169`. Live: `kanban overview` printed `generated_at` 2026-10-06T10:24:43Z. |
| AC-8.2 | PY | PASS | `console/tests/test_attention.py::test_static_export_carries_generated_at` (the exported overview JSON and the data script both carry the stamp). |
| AC-8.3 | BROWSER | partly observed by the parent | Parent section: the four overview-fed panels show the server time, Scheduled the browser fetch time. The Jobs panel is not mentioned (hidden when there are no jobs); same time across all five: not verified in a browser. |
| AC-8.4 | BROWSER | not verified in a browser | Source: `refresh` fetches first and repaints only on success (`overview.js:311-318`, pinned by `console/tests/test_fresh_source.py::test_refresh_fetches_first_and_never_blanks_the_page`); the server-stop run was not done. |
| AC-9.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac91_the_threshold_preference_is_read_in_core` and `console/tests/test_fresh_core.py::test_the_preference_key_is_in_core_and_not_read_by_the_server`; `core.js:411`. |
| AC-9.2 | PY | PASS | `console/tests/test_fresh_core.py::test_ac92_a_bad_preference_means_the_default` under node (29, 86401, 'abc', NaN, null all give 300; 30 and 86400 accepted). |
| AC-9.3 | BROWSER | not verified in a browser | Needs the preference written; the parent deliberately did not. |
| AC-10.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac101_overview_adds_no_timer`; grep of `setInterval|setTimeout` in `overview.js` is empty. |
| AC-10.2 | BROWSER | partly observed by the parent | Parent section: Refresh visible on a stale scratch panel, callback fired once; hidden while fresh. Real re-render with a new `generated_at`, chips clearing, kbd row kept: not verified in a browser. |
| AC-11.1 | BROWSER | not verified in a browser | Source: `C.IS_STATIC ? null` (`overview.js:324`) and `IS_STATIC` skips the button (`core.js:377`); no export was opened. |
| AC-12.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac121_exactly_one_freshness_interval_with_a_stop_path`; read `core.js:415-416` (guard on `freshTimer === null`, `clearInterval`); `freshTick` (`:407-413`) makes no request. |
| AC-12.2 | BROWSER | not verified in a browser | `freshCount` prunes disconnected panels (`core.js:426-429`). Note: it also prunes a fresh panel built but not yet attached; harmless today because every panel is attached in the same synchronous pass. |
| AC-13.1 | PY | PASS | `console/tests/test_fresh_source.py::test_ac131_time_element_and_status_role`; `core.js:376,382,395`. |
| AC-13.2 | BROWSER | not verified in a browser | Chip text is `STALE` (`core.js:399`), not colour alone, by source; forced-colors rendering not observed. |
| AC-13.3 | BROWSER | FAIL by source reading (defect D-A); not verified in a browser | Tab reaching Refresh and Space activation are fine by source. Enter on the Refresh button inside Needs you / Needs repair is swallowed: `rowNav` (`overview.js:57-70`) guards INPUT/TEXTAREA and the header only, so a focused Refresh under a panel that has rows takes the Enter branch (`rows[idx].click(); e.preventDefault()`), which cancels the button's activation and opens the highlighted row instead. Not exercised in a browser. |
| AC-14.1 | BROWSER | partly observed by the parent | Parent section: real Overview `scrollWidth` 400 at 400 px. The long-titled collapsed stale panel case: not verified in a browser. |
| AC-14.2 | BROWSER | not verified in a browser | The diff adds no media query (`git diff styles.css`, NFR-4); widths not measured. |

**Totals (44):** [PY] 24 of 24 PASS. [BROWSER] 20: 7 partly observed by the parent (AC-5.2, 6.2, 7.3, 7.4, 8.3, 10.2, 14.1), 12 not verified in a browser (AC-2.4, 3.4, 4.2, 5.3, 5.4, 6.3, 8.4, 9.3, 11.1, 12.2, 13.2, 14.2), 1 FAIL by source reading (AC-13.3, defect D-A). No [BROWSER] row is a full PASS yet.

## NFR check

| NFR | Result | Evidence |
|-----|--------|----------|
| 1 ES5 | PASS | `node --check` ok and 0 `=>` in core, overview, app, about; `test_ui_constraints.py` passes |
| 2 CSS | PASS | `fresh-mark`, `fresh-row` have rules mid-file (`styles.css` diff); `test_stylesheet.py` fails only on the known `onboarding-wizard.js: .ob-count` |
| 3 No new file/script | PASS | `git diff -- console/static/index.html` is 0 bytes; `test_nfr3_no_new_script_and_order_kept` |
| 4 900 px cliff | PASS | styles diff has no `@media` |
| 5 No dependency | PASS | `test_nfr5_no_new_dependency` (`pytest>=8.0` only, no package.json) |
| 6 Compatibility | PASS | `kanban overview` valid JSON: `generated_at`, `counts.needs_you` 13, `counts.needs_repair` 3 (= blocked 1 + stale 2 + unowned 0 + answered 0 + runs 0), legacy keys present |
| 7 Testable server logic | PASS | `needs_attention` pure apart from the registry read; `full_overview(now=)` |
| 8 Test pins | PASS | only A1 (`test_prefs_client_source.py`, 7+/1-) and A2 (`test_splitter.py`, 14+/8-) edits; `test_attention.py` additions only |
| 9 Cost | PASS by source | one 30 s timer, tick has no request (`test_ac121`); payload bounded at 50 rows. Timing not measured |
| 10 Line endings | PASS | byte counts below |
| 11 Baseline | PASS | full suite 1 failed (known), 3065 passed, 1 skipped |
| 12 Shared files | not checked | would need the T-037 diff history; the diffs read are surgical |

Line endings (byte counts, Python): core.js 1426 CRLF/0 LF; overview.js 445/0; app.js 735/0; about.js 281/0; styles.css 2456/0; overview.py 175/0; test_attention.py 252/0; test_prefs_client_source.py 453/0; README.md 1364/0; verification.md and summary.md all CRLF; as found LF: `T-039-plan.md` 232 LF/0 CRLF, `test_fresh_core.py` 110 LF, `test_fresh_source.py` 139 LF, `test_splitter.py` 1416 LF. `git ls-files --eol -m` over console and T-039 files shows no mixed file (i/lf with w/crlf or w/lf).

## Test Results

| Command | Result |
|---------|--------|
| `PYTHONUTF8=1 python -m pytest -o addopts="" -q -p no:cacheprovider` (full, run 2, 12 min under concurrent load) | `1 failed, 3065 passed, 1 skipped in 756.42s`; failure `console/tests/test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`, known, not this ticket). Equals the builder's count. Run 1 (190 s) reported 3024 passed: it started before concurrent T-041 test files settled (3067 collected afterwards), so it is not used |
| T-039 files alone: `test_attention test_fresh_core test_fresh_source test_ui_constraints test_reload_source test_prefs_client_source test_splitter test_stylesheet test_plugins` | `1 failed, 186 passed in 5.01s` (same known failure) |
| `node --check` core/overview/app/about | all ok; `grep -c '=>'` is 0 in each |
| `git diff -- console/static/index.html` | empty |
| `kanban overview` | valid JSON as listed under NFR 6 |
| Voice-assets flake | did not fail in either full run; not re-run alone |

Static-only: every [PY] AC for the JS side is verified by source pins and node-sliced pure functions, not by running the page. Type checks and tests verify code, not the feature in a browser.

## Defects

- **D-A (major, AC-13.3 / FR-13; found by reading, not run in a browser):** `rowNav` in `console/static/overview.js:57-70` swallows Enter on the Refresh `<button>` that sits in the as-of row inside Needs you and Needs repair (panels with rows): it clicks the highlighted row and calls `preventDefault`, so a keyboard user pressing Enter on Refresh navigates away instead of refreshing. Space works. No test covers it. Suggested fix (for @fixer): return early in `rowNav` when the target is a button or inside `.fresh-row`, and add a source pin. Not fixed here. D-A: fixed at source level, pending browser re-check.
- **D-B (minor):** the freshness STALE mark is an always-present empty `role="status"` span that gains text, not constant text; the parent section flags that announcement is unverified. Within FR-13 as the builder implemented it; needs a real screen reader to confirm.

No other defect found. Critique pass (`challenge-implementation`): 0 critical, 1 major (D-A), 1 minor (D-B), plus the prune-before-attach note on AC-12.2. Issues by class: arch=0 security=0 perf=0 style=0, a11y/behaviour=2.

## Edge Cases Probed
- 60 open questions: capped at 50, count 60 (`test_needs_you_is_capped...`).
- Missing/unparsable `asOf`, NaN, null, undefined: stale (node test).
- Future `asOf`: age 0 (node test).
- Preference 29, 86401, 'abc', NaN: default 300 (node test).
- A ticket both stale and unowned: counted in both groups, `needs_repair` equals the sum of group counts (`test_repair_count_is_the_sum_of_group_counts`).
- Terminal-lane ticket and `done` run: in neither list.
- Failed refetch: source keeps rows and old time (`refresh` and `opsHost`); not run against a stopped server.
- Concurrent, large payload, malformed tracker file: not probed beyond the above.

## Amendments A1 and A2
Consistently recorded. A1 (PC-1, NFR-8, `test_core_adds_no_interval`) and A2 (PC-2, AC-5.1, enter-guard pin) appear in requirements (annotated in place with original wording kept, lines 49 and 97), decision-log "Amendment 2026-10-06", iteration-log "Post-freeze amendments", and plan tasks T-039-04 and T-039-06. The code matches: test diffs are exactly the narrowed interval pin and the `rowNav` pin. Reconcile run (read-only): requirements, plan, decision-log, iteration-log, code and tests agree on the 14 FR / 44 AC / 7 `ov.*` ids / 19 overall ids. The builder had not run reconcile; this was it.

## Drift for the parent (verifier fixes nothing outside this file)
1. `T-039-summary.md`: frontmatter `status: Open`, header "Status: Open", "Stage: CANONICAL (plan written ... awaiting approval to build)" and "Current State" ("No code touched; no commit", "Lane stays open") are stale; build is 11 of 12 tasks done and the lane is in-progress.
2. `knowledge-center/artifact-map.md:24`: row reads "Open"; `link-check` reports `map-status-drift` (ticket.toml stage in-progress means "In Progress"). This is the one `link-check` error.
3. `T-039-progress.md` Status Summary line reads "Stage: TEMPLATE — slice 1 (T-039-01..05) in build; 0/5 done." but 11 of 12 tasks are done.
4. Links blocks: `T-039-progress.md`, `-release.md`, `-summary.md` omit siblings (`link-check`: 4 `links-incomplete` and 25 `one-way-link` warnings across progress, release, summary, verification). The verification Links block was completed in this change.
5. `T-039-questions.toml`: Q1 and Q2 still open (non-blocking defaults D-3 and D-5); not for the verifier to answer.
6. Untracked and not T-039's: `.cursor/mcp.json`, `AGENTS.md`; `console/server/link_check.py` and `console/tests/test_link_check.py` look like T-041.

## close-check (read-only)
`kanban verb run close-check --ticket T-039` after this write: `ok: false`; 21 blocks = 20 `criterion_not_pass` (every [BROWSER] row; AC-13.3 is also a source-reading FAIL) + `plan_open` (T-039-12). Evidence quality: 24 pass rows, 24 accepted, 0 prose-only, 0 phantom. `plan-status`: 11 of 12 done; `blockers`: none recorded on the ticket.

## Disposition
`needs_fix` for D-A (small, one guard plus a pin), then the parent's browser run (T-039-12) must cover the 12 unverified and 7 partly observed rows and re-test Enter on Refresh. Open owner questions: Q1 (answered questions in Needs repair, default D-3), Q2 (badge counts Needs you only, default D-5); both low priority, defaults applied.

## Browser run by the parent session (2026-10-06, in-app browser, console on :8790 restarted onto this code)

Run after build slice 2 (tasks 06..09), before the formal verify. **Not covered: the Tauri app window, a real screen reader, the real 30 s timer flipping a server-fed panel to STALE (needs a 300 s wait or a preference change that would alter the user's shared preferences), a collapsed panel showing the STALE chip (the scratch panel was not collapsible), static export.**

- **PASS: payload split is live.** `/api/overview` returns `generated_at` (UTC), `counts.needs_you = 13`, `counts.needs_repair = 3`, `needs_you`/`needs_repair`/`answered` lists, and every legacy key (`blocked`, `stale`, `unowned`, `questions`, `runs`) is still present.
- **PASS: two panels render.** The Overview shows "Needs you" (13) directly above "Needs repair" (3). The sidebar badge reads 13 and carries the title/aria-label "13 items need you".
- **PASS: freshness on the live panels.** At a glance, Needs you, Needs repair, Flow and Recently touched each show "As of <local time> . just now" with a real `time datetime` equal to the server `generated_at`; Scheduled shows the browser fetch time. The STALE chip is present with `role="status"` and empty while fresh; the Refresh button exists but is `display:none` while fresh.
- **PASS: stale state, on a scratch panel built with an old `asOf` (10 minutes, threshold 300 s).** The chip reads "STALE" (text, `role="status"`, visible); the as-of row ("As of ... . 10 min ago") is the last child of the body; Refresh is visible and its callback fired once. The pure helper returns age 600 and stale for 10 minutes, age 60 and fresh for 1 minute, age 0 for a future time, and stale with no age for a missing or unparsable time.
- **PASS: no horizontal overflow at 400 px** on the real Overview (`scrollWidth` 400).
- **Finding (minor):** none blocking. The status chip is `:empty{display:none}` while fresh; whether a screen reader announces the change to visible text is unverified, as the builder noted.
- Test hygiene: the scratch panel was removed afterwards; no user preference was changed (the `staleAfterSecs` preference was not written).

## D-A re-check by the parent session (2026-10-06, in-app browser, after the fixer's change to `rowNav`)

- **PASS: Enter on Refresh no longer opens the highlighted row.** On the Overview "Needs you" panel (13 rows), the Refresh button in the as-of row was focused and a real Enter keypress sent. The page stayed on `#overview`, no ticket drawer opened, the button's click fired exactly once, and the panel's `time datetime` advanced from `10:47:16Z` to `10:47:25Z` (a real refetch and repaint).
- **How it was staged, and its limit:** the data was fresh, so the Refresh button was `display:none` by design; it was made visible by script (`style.display`) to focus it. The same guard code covers "Needs repair" (`rowNav(attnPanel)`), which was NOT keyed separately. A genuinely stale panel was not waited for (300 s) and no preference was changed.
- **Still not covered:** a real screen reader on the status chip, the Tauri app window, the static export, and the real 30 s timer flipping a server-fed panel to STALE.

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
