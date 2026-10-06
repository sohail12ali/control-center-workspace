---
ticket: "T-037"
artifact: verification
---

# Verification: T-037

**Verifier run:** 2026-10-06 (`verifier`, read-only; no browser available to this agent). **Disposition: needs_human** (see Notes). Every `PASS` below is a source-regexp / static check (`[PY]`) or diff evidence; none is browser behaviour. `[BROWSER]` rows say `not verified in a browser` unless the parent section below observed them; rows the parent only partly covered say `(partial)` and are still not a pass.

## Acceptance Criteria

Totals: **31 PASS** (30 [PY] + AC-12.3 evidence), **34 not verified in a browser** (34 [BROWSER], 9 of them with partial parent-run evidence), **0 FAIL**.

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1.1 | script order core.js < splitter.js < app.js, away from the onboarding tag | PASS | `console/tests/test_splitter.py::test_p1_script_order_core_splitter_app`; `console/static/index.html:46-48` (core 46, splitter 47, desktop-chrome 48) (source-regexp, static; no browser) |
| AC-1.2 | ARIA attributes in source; aria-controls ids assigned | PASS | `console/tests/test_splitter.py::test_p3_handle_is_an_aria_separator_with_keys_and_reset`; `console/static/splitter.js:354-362` (source-regexp, static; no browser) |
| AC-1.3 | classes in styles.css; .sp-* mid-file; no repeated bare class | PASS | `console/tests/test_splitter.py::test_p7_sp_css_present_midfile_hidden_by_default`; `.sp` rule at `console/static/styles.css:852` of 2442 lines (source-regexp, static; no browser) |
| AC-1.4 | .sp z-index 8 (< topbar 20) | PASS | `console/tests/test_splitter.py::test_p7_sp_css_present_midfile_hidden_by_default`; `console/static/styles.css:853` z-index 8 (source-regexp, static; no browser) |
| AC-1.5 | no =>, let, const, backtick, innerHTML, localStorage, draggable, dragstart in splitter.js | PASS | `console/tests/test_splitter.py::test_p2_splitter_js_is_es5_without_forbidden_constructs`; independent grep -cF of each token in `console/static/splitter.js` = 0; node --check OK (source-regexp, static; no browser) |
| AC-1.6 | [BROWSER ~1400] hit area 6 px (20 px coarse), col-resize, token highlights, pane widths identical with/without handle | not verified in a browser | CSS values present (`console/static/styles.css:852-873`) but never measured; the parent section does not cover it. |
| AC-2.1 | capture, cancel, lostpointercapture, rAF, class removal | PASS | `console/tests/test_splitter.py::test_p4_drag_uses_capture_and_always_ends`; `console/static/splitter.js:213,235,369-370` (source-regexp, static; no browser) |
| AC-2.2 | touch-action; nothing attached to .brandrow | PASS | `console/tests/test_splitter.py::test_p4_drag_uses_capture_and_always_ends`; `console/tests/test_splitter.py::test_p7_sp_css_present_midfile_hidden_by_default`; `console/static/styles.css:856` touch-action none; grep brandrow in splitter.js = 0 (source-regexp, static; no browser) |
| AC-2.3 | [BROWSER ~1400] drag across the Vault canvas keeps going, no text selected | not verified in a browser | parent drag was on the Agents list only; Vault canvas drag not exercised. |
| AC-2.4 | [BROWSER ~1000 touch] finger drag works, no sideways scroll | not verified in a browser | touch not exercised (parent section). |
| AC-2.5 | [BROWSER] board repaint mid-drag: no error, no stuck class | not verified in a browser | board lane drag not exercised; builder's fake-DOM sim is not a browser. |
| AC-2.6 | [BROWSER Tauri/Windows] drag works, window does not move | not verified in a browser | Tauri/WebView2 not tested (parent section). |
| AC-3.1 | keys and dblclick in source | PASS | `console/tests/test_splitter.py::test_p3_handle_is_an_aria_separator_with_keys_and_reset`; `console/static/splitter.js:306-333,372` (source-regexp, static; no browser) |
| AC-3.2 | [BROWSER ~1400] Tab to handle, 3x ArrowRight = +48 px, aria-valuenow follows, focus ring | not verified in a browser (partial) | parent observed on a focused Agents handle: Arrow 16 px, Shift+Arrow 64 px, Home 180, End 480; Tab order, 3x ArrowRight, aria-valuenow tracking and focus ring not stated. |
| AC-3.3 | [BROWSER] double-click returns to default and key is gone from storage | not verified in a browser (partial) | parent: a synthetic dblclick reset 480 to the 302 default; real-mouse double-click unconfirmed; key removal not observed. |
| AC-3.4 | [BROWSER] rail below 100 px collapses; Enter restores | not verified in a browser | snap-collapse not exercised (parent section). |
| AC-4.1 | no top-level prefs call; prefs.set( only in one helper that reads layout first | PASS | `console/tests/test_splitter.py::test_p5_one_prefs_write_in_a_helper_that_reads_layout_first`; independent grep: one prefs.set( at `console/static/splitter.js:80` (inside writeLayout, which reads at :69) (source-regexp, static; no browser) |
| AC-4.2 | install-once resize listener, isConnected pruning | PASS | `console/tests/test_splitter.py::test_p6_listeners_once_registry_pruned_reapplyall_exposed`; `console/static/splitter.js:397,433-439`; one addEventListener resize at :436 (source-regexp, static; no browser) |
| AC-4.3 | [BROWSER] one drag = one write; click without move = none; reload restores | not verified in a browser (partial) | parent: dragged width persisted through a reload (server-side); write count and click-without-move not observed. |
| AC-4.4 | [BROWSER ~1000] stored 2000 shows clamped, stored value unchanged | not verified in a browser | not exercised. |
| AC-4.5 | [BROWSER] invalid layout renders defaults, no error | not verified in a browser | not exercised in a browser (builder fake-DOM sim only). |
| AC-5.1 | .sp hidden by default, shown only in the wide block | PASS | `console/tests/test_splitter.py::test_p7_sp_css_present_midfile_hidden_by_default`; `console/static/styles.css:853` (display none), `:873` wide block (source-regexp, static; no browser) |
| AC-5.2 | 901px once in splitter.js, no max-width: 900px | PASS | `console/tests/test_splitter.py::test_p9_one_wide_constant_and_no_inline_grid_or_root_writes`; independent grep: 901px count 1 (`console/static/splitter.js:22`), max-width: 900px count 0 (source-regexp, static; no browser) |
| AC-5.3 | every var(--sp- inside @media (min-width: 901px); no documentElement.style/gridTemplateColumns in JS | PASS | `console/tests/test_splitter.py::test_p8_sp_vars_only_in_wide_blocks_no_grid_transition`; `console/tests/test_splitter.py::test_p9_one_wide_constant_and_no_inline_grid_or_root_writes`; independent grep of var(--sp-: `console/static/styles.css:719,937,1005,1672-1673,1788`, each after a min-width 901px opener (718,931,1004,1671,1787); grep documentElement.style and gridTemplateColumns = 0 (source-regexp, static; no browser) |
| AC-5.4 | no transition on grid-template-columns; min-width/min-height 0 kept | PASS | `console/tests/test_splitter.py::test_p8_sp_vars_only_in_wide_blocks_no_grid_transition`; `console/tests/test_splitter.py::test_p8_min_zero_kept`; `console/tests/test_splitter.py::test_p8_dock_block_min_zero_no_transition_after_drawer_rules` (source-regexp, static; no browser) |
| AC-5.5 | [BROWSER 900/901/~800] none visible/tabbable at 900; work at 901; stored layout changes nothing at ~800 | not verified in a browser (partial) | parent: 901 both handles visible, 900 hidden and one column, 400 no overflow/no handles on 7 tabs; tabbability and ~800 stored-layout leg not stated. |
| AC-5.6 | [BROWSER ~1400] each row drags to its min and max, not beyond | not verified in a browser (partial) | parent: Agents list 180 (Home) and 480 (End, Shift+Arrow clamped); the other five rows not exercised. |
| AC-6.1 | collapse calls setListShown; no new flag | PASS | `console/tests/test_splitter.py::test_p12_agents_list_attach_reuses_setlistshown` (source-regexp, static; no browser) |
| AC-6.2 | var(--sp-list with the clamp fallback in the wide block | PASS | `console/tests/test_splitter.py::test_p8_agents_list_consumes_sp_list_with_clamp_fallback`; `console/static/styles.css:937` (source-regexp, static; no browser) |
| AC-6.3 | [BROWSER ~1400] drag to 300/180, fold below 90, restore, reload keeps width | not verified in a browser (partial) | parent: drag 302 to 419, size survives reload; fold below 90 and restore not exercised. |
| AC-7.1 | attach in mountChat, appended to .ct-split | PASS | `console/tests/test_splitter.py::test_p12_agents_rail_attached_in_mountchat_as_ct_split_child` (source-regexp, static; no browser) |
| AC-7.2 | [BROWSER ~1400] streaming meta repaints do not interrupt a drag | not verified in a browser | rail not exercised. |
| AC-7.3 | [BROWSER] restore by click/Enter/dbl-click; ~800 unchanged | not verified in a browser | rail not exercised. |
| AC-8.1 | drag flag around resize() | PASS | `console/tests/test_splitter.py::test_p12_vault_drag_flag_guards_resize` (source-regexp, static; no browser) |
| AC-8.2 | handles appended to .vault, not .vault-stage | PASS | `console/tests/test_splitter.py::test_p12_vault_handles_on_vault_not_stage` (source-regexp, static; no browser) |
| AC-8.3 | [BROWSER ~1400] canvas width/height setter spy: zero reallocations in a 2 s drag, one after release | not verified in a browser | parent moved the Vault sidebar handle by keyboard only (262 to 326); no setter spy, no pointer drag. |
| AC-8.4 | [BROWSER 901] viewer drag stops where the stage is 200 px | not verified in a browser | viewer handle not exercised. |
| AC-9.1 | --sp-lane on .lanes, consumed in the wide block | PASS | `console/tests/test_splitter.py::test_p8_lane_consumes_sp_lane_after_its_base_rule_with_lane_w_fallback`; `console/tests/test_splitter.py::test_p12_board_lane_handle_attach`; `console/static/styles.css:719` (source-regexp, static; no browser) |
| AC-9.2 | [BROWSER ~1400] lane 3 edge within 2 px of pointer; lanes equal; cold lane 52 px | not verified in a browser | board lane drag not exercised (parent section). |
| AC-9.3 | [BROWSER] repaint and Show more keep width; only the first handle tabbable | not verified in a browser | not exercised; the lane aria-valuenow fix of 2026-10-06 is source-level here (finding F-1). |
| AC-10.1 | exported shape; drawer.open( only in board.js | PASS | `console/tests/test_splitter.py::test_p10_drawer_export_shape_single_opener`; independent grep: only `console/static/board.js:317` (moved from :300 in the artifacts) (source-regexp, static; no browser) |
| AC-10.2 | one dockMode() using C.splitter.WIDE; both role values flipped on switch | PASS | `console/tests/test_splitter.py::test_p10_dockmode_single_uses_wide_roles_flip`; `console/static/app.js:24` (source-regexp, static; no browser) |
| AC-10.3 | [BROWSER ~1400, 1400x600] panel beside board, no scrim, topbar clickable, tops touch | not verified in a browser (partial) | parent at 1400: #app gets has-dock, no scrim, top bar hit-testable, panel 430 px with handle; 1400x600 and tops touching not stated. |
| AC-10.4 | [BROWSER ~800, ~400] scrim, modal, full width at 400 | not verified in a browser | not exercised. |
| AC-10.5 | [BROWSER 1280/1400] sideways scroll about 286/238 px accepted | not verified in a browser | not measured. |
| AC-10.6 | [BROWSER] clamp 320/720 and main#view >= 360; width survives reload | not verified in a browser | dock handle not dragged. |
| AC-11.1 | fresh .dbody on repeat open; listeners once | PASS | `console/tests/test_splitter.py::test_p10_repeat_open_swaps_in_fresh_dbody_listeners_once`; `console/tests/test_splitter.py::test_p10_listeners_flag_and_index_html_only_gains_the_splitter_tag` (source-regexp, static; no browser) |
| AC-11.2 | print block covers the dock and its #app layout | PASS | `console/tests/test_splitter.py::test_p10_every_print_block_covers_dock` (source-regexp, static; no browser) |
| AC-11.3 | [BROWSER] Esc rules | not verified in a browser (partial) | parent: Esc with focus inside the panel closes it and clears has-dock (real key press); Esc outside the panel, modal Esc and field-revert not observed; a synthetic Esc did not close it (finding F-3). |
| AC-11.4 | [BROWSER] Owner edit refresh: no slide-in, same width/focus, rapid refreshes | not verified in a browser | not exercised. |
| AC-11.5 | [BROWSER] 1400/800 with a half-typed field | not verified in a browser | live 901 px switch not exercised (parent section). |
| AC-11.6 | [BROWSER] print preview: no panel, no empty column | not verified in a browser | print preview not exercised; the CSS block is covered by AC-11.2's source test only. |
| AC-12.1 | each id once in its file, none across files | PASS | `console/tests/test_splitter.py::test_p11_section_ids_unique_and_scoped`; `console/tests/test_splitter.py::test_p11_ag_ids_once_in_agents_js`; `console/tests/test_splitter.py::test_p11_vault_ids_literal_once`; independent grep of all 18 ids: each found in exactly one script (overview 6, assistant 3, agents 5, vault 4) (source-regexp, static; no browser) |
| AC-12.2 | guard, panelOpen in vault.js, C.group + ct-panel in the rail | PASS | `console/tests/test_splitter.py::test_p11_overview_enter_guard`; `console/tests/test_splitter.py::test_p11_vault_cards_use_panelopen`; `console/tests/test_splitter.py::test_p11_rail_sections_c_group_ct_panel` (source-regexp, static; no browser) |
| AC-12.3 | evidence: no T-037 hunk in core.js, other tickets' hunks intact | PASS | git diff -U0 console/static/core.js: 12 hunks, 578 lines; grep -E for splitter, --sp-, foldBar, sp- = 0 matches. The literal grep for the word layout matches one line (diff line 43), a T-036 comment in the C.prefs block (panel layout), not a T-037 edit. Other tickets' hunks intact: builder-reported per slice (Guard G in `T-037-progress.md`), not independently diffed. |
| AC-12.4 | [BROWSER ~1400] folds survive tab switch, reload, rail repaints | not verified in a browser | parent: one Overview section folded 416 to 93 px and re-expanded; persistence not observed. |
| AC-12.5 | [BROWSER] Enter on header folds without navigating; body Enter opens a row | not verified in a browser | not exercised. |
| AC-12.6 | [BROWSER ~400] folds by touch; rail strip scrolls | not verified in a browser | touch not exercised. |
| AC-13.1 | query inside the handler; no foldBar in settings.js | PASS | `console/tests/test_splitter.py::test_p13_foldbar_queries_at_click_time`; `console/tests/test_splitter.py::test_p13_foldbar_used_on_overview_and_assistant_only`; independent grep: foldBar only in `console/static/overview.js:255`, `console/static/assistant.js:147` (source-regexp, static; no browser) |
| AC-13.2 | [BROWSER] async Jobs/Scheduled included; Settings buttons still work | not verified in a browser | parent saw the fold bar on Overview; its buttons were not pressed. |
| AC-14.1 | one function, one added push, other hunks unchanged | PASS | `console/tests/test_splitter.py::test_p14_layoutpanel_one_function_one_push`; `console/static/settings.js:2486,2676` (source-regexp, static; no browser) |
| AC-14.2 | three C.prefs.del, no localStorage, no C.prefs.reset | PASS | `console/tests/test_splitter.py::test_p14_reset_three_prefs_del_no_localstorage_no_prefs_reset`; `console/static/settings.js:2490-2492` (source-regexp, static; no browser) |
| AC-14.3 | [BROWSER ~1400] defaults restored without reload; theme and hidden tabs unchanged | not verified in a browser (partial) | parent: Reset layout removed the layout from the server and the Agents list returned to 302 px without reload; theme/hidden tabs and panel folds not stated. |
| AC-15.1 | [BROWSER, after T-036 lands] Reset all preferences resets live layout | not verified in a browser | cross-ticket; T-036 C.prefs hunks are present in the working tree (core.js diff) so it is now testable, but nobody has run it. |
| AC-15.2 | reapplyAll exposed; no dependency on C.prefs.reset | PASS | `console/tests/test_splitter.py::test_p6_listeners_once_registry_pruned_reapplyall_exposed`; `console/tests/test_splitter.py::test_p14_reset_three_prefs_del_no_localstorage_no_prefs_reset`; `console/static/splitter.js:471`; grep prefs.reset in splitter.js = 0 (source-regexp, static; no browser) |

## Test Results

Independent runs by the verifier (2026-10-06, `PYTHONUTF8=1`); builder-reported numbers were not copied.

| Run | Command | Verifier result | Builder-reported |
|-----|---------|-----------------|------------------|
| Scoped | `python -m pytest -o addopts="" console/tests/test_splitter.py console/tests/test_stylesheet.py console/tests/test_plugins.py -q` | `1 failed, 67 passed in 3.83s`; failing id `console/tests/test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`, another ticket's, not fixed) | `1 failed / 67 passed` (identical) |
| Splitter only | `python -m pytest -o addopts="" console/tests/test_splitter.py -q` | `43 passed in 0.98s` | not reported |
| Full suite (T-037-20) | `python -m pytest -o addopts="" -q` | `1 failed, 2877 passed, 1 skipped in 365.28s (0:06:05)`; the one failing id is the same `.ob-count` id; no new red id | baseline `1 failed / 2273 passed` (pre-T-037; the passed count rose with tests from several tickets, compared by id) |
| Syntax | `node --check console/static/{splitter,app,agents,vault,board,overview,assistant,settings}.js` | all 8 OK, no output | `splitter.js` OK reported only |
| AC-12.3 | `git diff -U0 console/static/core.js` | 12 hunks; 0 lines matching `splitter`, `--sp-`, `foldBar`, `sp-`; the broader word `layout` matches only a T-036 comment | builder: 0 |

Static-only caveat: type/syntax checks and source-regexp tests verify code shape, not the feature. There is no JS test runner; the builder's fake-DOM node simulations (kept in the session scratchpad, never committed) are not a browser and are not counted here.

## Edge Cases Probed

By the verifier (static): forbidden-token greps on `splitter.js` (all 0), single `prefs.set(`, single `901px`, `var(--sp-` placement against the wide blocks, single opener of `drawer.open(`, 18 section ids each in one script, `foldBar` only on Overview and Assistant, `layoutPanel` with three `C.prefs.del` and no `prefs.reset`. Code read of `splitter.js` (474 lines) for: invalid `layout` shapes (`validMember`, :43-60), clamp without rewriting storage (`apply`, :173-191), drag end on cancel / lostpointercapture / removed handle (`endDrag`, `prune`, :256-281, :394-406), one write per gesture (`setWidth`, `endDrag`), double-click right after a restore (`onDouble`, :328-333). None run in a browser.

Not probed by anyone in a browser: empty/invalid stored layout, 2000 px stored at 1000 px, repaint during a drag, touch, print, Tauri, 900.5 px, no-viewer Vault, all-cold board.

## Findings (logged, none redesigned)

- **F-1 (fixed 2026-10-06, source-level here):** the parent run found lane handles with no `aria-valuenow`. The builder's fix sets value attributes on every handle (`console/static/splitter.js:146-164`: `mark()` has no `primary` early return; `refresh()` updates all handles sharing `opts.key`), pinned by `console/tests/test_splitter.py::test_p12_every_lane_handle_carries_the_shared_width`. The caller reports a real-browser check of the fix; that check is not recorded in this artifact and the verifier did not observe it.
- **F-2 (decision/finding, not redesigned):** a saved 480 px Agents list leaves the transcript 421 px wide at 901 px. Within the FR-5 table (`agents.list` max 480, transcript >= 320; 421 >= 320), so spec-compliant, but narrower than the default would leave it. Accepted as is; revisit only if the user wants a tighter cap near 901 px.
- **F-3 (finding):** a synthetic Esc did not close the dock; a real key press with focus inside the panel did (parent section). That matches FR-11/AC-11.3 (Esc closes only when the target is inside the panel), so a synthetic event dispatched elsewhere not closing it is expected. Esc outside the panel and the modal Esc were not exercised.
- **F-4 (artifact drift, minor):** requirements and plan cite the single drawer opener as `board.js:300`; it is now `console/static/board.js:317`. Behaviour unchanged (`test_p10_drawer_export_shape_single_opener` green).
- **F-5 (artifact hygiene):** `T-037-progress.md` line 51 is a spliced fragment: the `T-037-01` entry text (starting `## Links` in [[T-037-components]]...) is fused onto a stray heading mid-file, and the `T-037-01` entry is interleaved into the head of the `T-037-15` entry (line 37). The Status Summary (line 9) still says PAUSED / lane `in-progress`. Not edited by the verifier; needs a repair pass by `progress-tracker`.
- **F-6 (open, non-blocking):** the `claimed_by = builder` claim on T-037 is stale (ttl); close-check blocks on it until released or refreshed.
- **F-7 (out of scope, existing):** bug `D-1`, `palette.js:103` calls `app.drawer(...)` as a function; logged in `T-037-bugs.toml`, not T-037's.
- **Q1 (open):** dock replaces the overlay on wide screens vs opt-in toggle. `accepted: default pending user confirmation`; the alternative is a one-function change (`dockMode()`, `console/static/app.js:24`). Not resolved by this run.
- **AC-15.1:** open; T-036's `C.prefs` is in the working tree, so the parent can now run the check.

## Notes

- Close-check (read-only, `verb run close-check --ticket T-037`, before this table was written): `ok: false`; blocks `criterion_not_pass` (the old placeholder row), `claim_stale` (F-6), `plan_open` (`T-037-20` unchecked). The 34 `not verified in a browser` rows are non-pass by design and keep the ticket from a clean close until a browser run covers them or the user accepts them.
- Review escalation: none (the `trace-context` digest shows no `review.escalated`).
- T-037-20 done-criteria: full suite once with failing id = baseline (met); every [BROWSER] check recorded as not verified or partial (met); AC-12.3 evidence (met); AC-15.1 open (met). The plan checkbox was not ticked by the verifier.
- Test-case design: [[T-037-test-cases]].

## Browser run by the parent session (2026-10-05, in-app browser, console on :8790)

Not the verifier's work (the formal verify step has not run). **The Tauri/WebView2 window, touch input and a real-mouse double-click were NOT tested.**

- **PASS: real pointer drag.** Dragging the Agents list handle moved the pane 302 px to 419 px, tracking the pointer. The size persisted through a reload (stored server-side).
- **PASS: keyboard.** On a focused handle: Arrow = 16 px, Shift+Arrow = 64 px (clamped at the 480 px max), Home = 180 px, End = 480 px.
- **PASS: reset (synthetic).** A dispatched `dblclick` reset 480 px to the 302 px default. A real-mouse double-click was attempted twice but the tool's click landed on a transcript element; unconfirmed by hand, not a code finding.
- **PASS: the 900/901 boundary.** At 901 px both handles are visible; at 900 px they are hidden and the layout is one column with no horizontal overflow. At 400 px: no horizontal overflow and no visible handles on overview, investigations, agents, vault, assistant, settings and todos.
- **PASS: Vault.** One sidebar handle with ARIA min/max; Shift+Arrow moved it 262 px to 326 px.
- **PASS: sections.** Overview has five collapsible sections plus a fold bar; collapsing one took it from 416 px to 93 px high and it re-expanded.
- **PASS: docked ticket panel.** Opening a ticket on the board (1400 px): `#app` gets `has-dock`, no scrim, top bar still hit-testable, panel 430 px wide with its own handle. Esc with focus inside the panel closes it and clears `has-dock`.
- **PASS: Reset layout.** The Settings button removed the layout from the server and the Agents list returned to 302 px without a reload.
- **Findings:** (1) the three lane handles on the board expose no `aria-valuenow`, unlike the other handles; (2) a saved 480 px list pane leaves the transcript only 421 px wide at 901 px; (3) Esc via a synthetic event did not close the dock (a real key press with focus inside did).
- **Not exercised:** touch drag, snap-collapse, board lane drag, HTML5 card drag with a handle present, print preview, the live 901 px switch with a half-typed field.

## Second browser run by the parent session (2026-10-06, in-app browser, 1400 px unless noted)

Adds to the 2026-10-05 section; same limits: **the Tauri window, real touch input and real printing were NOT tested.**

- **PASS: board lane drag (real pointer).** Dragging lane 3's handle 59 css px moved every lane 270 to 290 px; lane 3's right edge landed within about 5 px of the pointer; `aria-valuenow` read 290 on all four handles; `layout.board.lane = 290` stored on the server. Cards keep `draggable=true`; an actual card drop was not performed (it would change a ticket's lane).
- **PASS: snap-collapse.** Dragging the Agents list handle to the left edge collapsed the pane to 0 px (`sp-collapsed`, `hide-list`, `chatListHidden` persisted). The collapsed splitter handle is `display:none`, so restore is by the existing "Show the chat list" button, which restored 302 px. Click-to-restore on the handle itself therefore does not apply to Agents.
- **PASS: lane handles carry the value.** All four lane handles report `aria-valuenow 270` (min 200, max 480) after the fix; only the first is focusable, the rest are `aria-hidden` and `tabindex -1`, as designed.
- **PASS: docked panel resize.** The "Resize ticket panel" handle moved the panel 430 to 494 px with Shift+ArrowLeft; `layout.dock.w = 494` stored.
- **PASS: half-typed field survives the 901 to 900 px switch.** The text and focus were kept.
- **FINDING (new, F-8): the live 901 to 900 px switch leaves the docked state behind.** After the resize the panel is `position:fixed` but `#app` keeps `has-dock`, there is no scrim, `aria-modal` is null and the role is still `complementary`. Opening a ticket fresh at 900 px is correct (dialog, `aria-modal=true`, scrim, no `has-dock`). So in-place conversion on resize is incomplete. **Status: fixed at source level, not yet verified in a browser** (2026-10-06 fixer: a window `resize` listener now re-checks `dockMode()` and re-mounts on a flip; see [[T-037-progress]]).
- **PASS: Collapse all / Expand all** on Overview (all headers false, then all true).
- **PASS (static):** handles set `touch-action:none`; a coarse-pointer rule for the larger hit area and a print rule for the dock exist in `styles.css` (not exercised).
- **Not run on purpose: "Reset all preferences".** Preferences are now shared with the desktop app, so it would wipe the user's real settings. AC-15.1 stays for the user to run.
- **Not run:** Vault viewer handle (no note opened), HTML5 card drop, real print preview, touch drag, Tauri window.

## F-8 re-check by the parent session (2026-10-06, in-app browser)

After the fixer's change (`app.js` drawer IIFE: one shared `sync` bound to the media-query change and to `window resize`), with a ticket docked at 1400 px and text typed in a drawer field:
- **PASS at 900 px:** after a `resize` event the panel is `role=dialog`, `aria-modal=true`, a `.scrim` exists, `#app` has no `has-dock`, and the **same panel node** keeps the typed value and focus.
- **PASS at 901 px:** after a `resize` event the panel is `role=complementary`, no `aria-modal`, no scrim, `#app` has `has-dock`, the "Resize ticket panel" handle is present, and the same node keeps value and focus.
- **Limit of this check:** the in-app browser's viewport emulation does not deliver `resize` or media-query change events to the page, so the `resize` event was dispatched by script after each size change. The handler is proven; a real window drag-resize in the desktop app or a normal browser is NOT verified. The fix is correct only if a real resize fires the event it listens for (standard browser behaviour, but not observed here).

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements]] · [[T-037-test-cases]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
