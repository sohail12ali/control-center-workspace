---
ticket: "T-037"
artifact: critique-report
---

# Critique report: T-037

Scaffolded on first use per `.claude/skills/challenge-standards/rules.md` (no `_template/critique-report.md` exists; T-031's report was the shape reference).

## Requirements critique

**Last run:** 2026-10-05 · `challenge-requirements` pass 2 (after iteration 1): 4 new findings. Pass 1 raised CR-1..CR-20 on draft v0 (closed in iteration 1, CR-19 accepted); pass 2 raised CR-21..CR-24 (closed in iteration 2, CR-23 accepted). Pass 3 not needed: iteration 2 changed wording only to close these four, and the freeze gate re-reads the draft.

| Severity | Count |
|---|---|
| critical | 1 |
| major | 13 |
| minor | 10 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | critical | unstated-assumption | draft §4 FR-11 / G6 | "Refresh in place" can reuse one body node, so an older in-flight `C.load` paints into it (`board.js:299-304`) | resolved: requirements iterate 2026-10-05 — FR-11 (5), AC-11.1, AC-11.4, D-9 |
| CR-2 | major | nfr-unmeasurable | draft §4 FR-1,FR-3, §5 / G13 | Hit area, key step, collapse threshold, touch target, drag cost have no number or measurement method | resolved: enrich + iterate — numbers proposed with `⚠ [unrealistic?]` and accepted (draft §13); drag cost as call counts |
| CR-3 | major | untestable | draft §4 [BROWSER] ACs / G26 | [BROWSER] criteria name no viewport, steps or expected measurement | resolved: requirements iterate — each [BROWSER] AC names viewport and measurement; § 15 B-1..B-13 |
| CR-4 | major | unstated-assumption | draft §4 FR-5 / G2 | A `--vault-side` written on `.vault` also beats `:root{--vault-side:218px}` at <=900 px (`styles.css:2024`) | resolved: requirements iterate — FR-5, AC-5.3, AC-5.5, D-3 (`--sp-*` consumed in the wide block only) |
| CR-5 | major | ambiguity | draft §4 FR-9 / G9 | Lane handle placement, sideways scroll, pointer scaling, cold lane unstated | resolved: requirements iterate — FR-9, AC-9.2, AC-9.3, D-7 |
| CR-6 | major | untestable | draft §4 FR-12 / G15 | AC-12.1 proves neither persistence nor uniqueness; no id table; titles carry counts | resolved: requirements iterate — FR-12 id table, AC-12.1, AC-12.4, D-12 |
| CR-7 | major | ambiguity | draft §4 FR-13 | Which pages get Collapse all / Expand all, and where | resolved: requirements iterate — FR-13 (Overview, Assistant home), D-13 |
| CR-8 | major | contradiction | draft §4 FR-14 vs FR-4 / G10 | Reset "without reload" vs "read only when built" | resolved: requirements iterate — FR-14 (`reapplyAll()` + `go(active)`), FR-4 registry, D-15, D-19 |
| CR-9 | major | unstated-assumption | draft §4 FR-10 | Q1 default stated, path to the opt-in alternative not | resolved: requirements iterate — FR-10 `dockMode()`, D-1 |
| CR-10 | major | unstated-assumption | draft §4 FR-3 / G2 | Which handles collapse is undefined | resolved: requirements iterate — FR-5 table "Collapse" column, D-6 |
| CR-11 | major | unstated-assumption | draft §4 FR-4 / G11 | Global listeners and instance registry unconstrained though `attach` runs per render | resolved: requirements iterate — FR-4, AC-4.2, D-19 |
| CR-12 | major | contradiction | draft §4 FR-11 / G12 | "Esc only when focus is inside" vs Esc in a drawer field (reverts and closes, `board.js:333`) | resolved: requirements iterate — FR-11 (3), AC-11.3, D-10 (unchanged, stated) |
| CR-13 | major | ambiguity | draft §6, FR-14 / G3,G4 | `layout` shape, invalid values, Reset scope were `〈TBD〉` | resolved: requirements iterate — §6, FR-14, AC-4.5, D-4, D-15 |
| CR-14 | minor | ambiguity | draft §4 FR-2 | No mechanism for "no text selection" | resolved: requirements iterate — FR-2 body class, D-23 |
| CR-15 | minor | scope-creep | draft §4 FR-13 | A shared helper invites refactoring `jumpBar()` | resolved: requirements iterate — out of scope list, FR-13, AC-13.1, D-13 |
| CR-16 | minor | unrealistic-constraint | draft §5 | Baseline comparison by count is fragile | resolved: requirements iterate — NFR Tests (by test id), D-20 |
| CR-17 | minor | untestable | draft §4 AC-11.1 | Python can check print CSS text only | resolved: requirements iterate — AC-11.2 [PY] text + AC-11.6 [BROWSER] |
| CR-18 | minor | ambiguity | draft §4 FR-10 / G14 | Topbar overlap and sideways scroll when docked unstated | resolved: requirements iterate — FR-10, AC-10.3, AC-10.5 (accepted behaviour) |
| CR-19 | minor | spof | draft §10 | T-036 not landed; shared `layout` last-writer-wins across clients | accepted: T-036 `scope-boundaries` risk 2; px clamped at apply time (draft §13) |
| CR-20 | minor | ambiguity | draft §4 FR-1 / G20 | Handle stacking order unstated | resolved: requirements iterate — AC-1.4 (z-index 8), D-23 |
| CR-21 | major | contradiction | draft §4 FR-12 vs FR-5 / G27 | Rail sections built with `C.group` lose the `ct-panel` class, so the <=900 px sideways strip (`styles.css:2020`) would break, contradicting "stacked layouts unchanged" | resolved: requirements iterate 2 — FR-12 keeps `ct-panel`, AC-12.2, Interactions row, D-12 |
| CR-22 | minor | ambiguity | draft §4 FR-13 / G28 | `foldBar` placement left to the caller without a stated position | resolved: requirements iterate 2 — FR-13 first row, right-aligned |
| CR-23 | minor | ambiguity | draft §4 FR-14 / G29 | Re-rendering Settings after Reset scrolls the page to the top | accepted: `go()` rebuilds `#view` by design (`app.js:141`); in-place re-apply needs unexported `collapsible()` (draft §13) |
| CR-24 | minor | unstated-assumption | draft §4 FR-1, FR-10 / G30 | Docked panel keeps `role="dialog"`/`aria-modal`; `aria-controls` needs ids the panes lack | resolved: requirements iterate 2 — FR-10 `role="complementary"`, AC-10.2, AC-1.2 |

## Plan critique

**Last run:** 2026-10-05 · `challenge-plan` (planner part C) over [[T-037-plan]], [[T-037-components]], [[T-037-task-breakdown]], [[T-037-implementation-plan]] against the frozen [[T-037-requirements]] and [[T-037-decision-log]]. `T-037-effort-estimate.md` is missing, skipped on purpose (the estimate lives in the breakdown § Estimate, written by `estimate(mode=upfront)`). The ids continue the ticket sequence (CR-25..CR-44; the caller's "PC-n" example is not used, one sequence per `challenge-standards/rules.md`). Evidence is cited from the real tree on 2026-10-05; line numbers drift.

Gate: **clear** (0 critical). The 9 major findings were fixed in the planning artifacts in the same pass (the caller asked for fixes, so the skill's "findings only" rule 7 was not applied); each finding below keeps its row and status. Evolve candidates: CR-37 (decision text only). No product/design question needs `questions.toml` (no critical finding).

| Severity | Count |
|---|---|
| critical | 0 |
| major | 9 |
| minor | 11 |

By kind: traceability 3 · scope-drift 1 · contradiction 5 · sequencing-risk 3 · effort-unrealistic 2 · untestable 5 · layer-violation 0 · rollback-gap 0 · critical-path 1 (total 20).

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-25 | major | sequencing-risk | `styles.css:882-894` vs `:938-941`, `:1585-1591` | Wide-block consumers for `.ct-split` and `.vault`/`.vault.has-viewer` would go into the existing wide block, which precedes their base rules at equal specificity: the base wins, a stored width is silently inert at >=901 px, and no [PY] test sees it | fixed: breakdown Conventions "CSS source order", T-037-07/09 put the consumer in a second wide block right after the base rule, new `test_p8_wide_consumer_follows_its_base_rule` (T-037-02), plan R13 |
| CR-26 | major | contradiction | breakdown tables vs § Dependency summary vs components graph | Table said 15 on "06-14" and 16 on "05, 15" while the hard list said 04 and 05; components drew C4-C8 into C9 as 5 hard edges (35 total) while its C9 row says hard on C1 only; 14 omitted hard 08 and 10 (the 18-id gate reads their ids); 07, 08, 10, 18 listed build-order predecessors as if hard | fixed: one edge set (see plan § Tasks and breakdown § Dependency summary), tables, plan and components aligned; 30 hard + 6 soft edges; acyclic (every hard edge points to a lower task number) |
| CR-27 | major | contradiction | components "Dock placement decision", T-037-16, `styles.css:1678`, `:938`, `:688` | The docked aside was set `position: static`, but its handle is an absolutely positioned child; with a static aside the containing block is the initial containing block (`#app` is unpositioned, `:268-273`), so the handle lands in the wrong place. `.ct-split` and `.lane` hosts are unpositioned too (`.appshell` `:842` and `.vault` `:1589` are relative) | fixed: docked aside `position: relative` (offsets are 0, so no shift), `position: relative` added to the `.ct-split` and `.lane` base rules in T-037-07 and T-037-11, C1 contract item (i) |
| CR-28 | major | effort-unrealistic | plan § Slices, implementation-plan § Phases | S1a (01-03) = 8.0 h and S7 = 10.0 h as single builder runs; S1a holds a contract, a CSS block, a ~200-line ES5 module and five test groups; the previous planner already died on a >16k-token response | fixed: runs S1a 01-02, S1b 03, S1c 04-05, S7a 16-17, S7b 18-19; every run <= 6 h; output-discipline rule (single Write/Edit <= ~150 lines) |
| CR-29 | major | contradiction | Done lines of 08, 10, 14, 20; common slice exit; AC-12.3 | "`git diff` of `core.js` empty" fails for a reason that is not T-037's: T-036 will edit `core.js` (`C.prefs`, [[T-036-summary]] item 2) and `app.js:266-270` (heartbeat, item 1) during this build; AC-12.3 says "no T-037 hunk" | fixed: baseline of `git diff -U0` for every shared file recorded in `T-037-progress.md` at the start of T-037-01; every check reads "unchanged versus the baseline"; T-036's expected hunks added to the avoid list |
| CR-30 | major | untestable | AC-5.4, breakdown T-037-02 (P-8) | "`min-width:0`/`min-height:0` kept" has no named test; the P-8 skeleton checks "no grid transition" only | fixed: P-8 also asserts `min-height: 0` in the `.appshell`, `.ct-split`, `.vault` base rules (`:842`, `:939`, `:1588`) and `min-width: 0; min-height: 0` in the dock block |
| CR-31 | major | traceability | NFR Compliance "dock and handles hidden in print"; `styles.css:2128-2132` | Only the dock is covered (AC-11.2, T-037-18). Handles and the fold bar have no print rule or task, and `(min-width: 901px)` is true when printing landscape (>= ~1000 css px), so the wide block would show them | fixed: T-037-02 adds a separate `@media print` block beside the `.sp-*` block hiding `.sp` and the fold bar (not at `:2129`), P-7 asserts it |
| CR-32 | major | sequencing-risk | T-037-09 vs `styles.css:887-891` | Vault `sideOff` must hide the sidebar (BR-10); the file documents the trap (a `display:none` child lets auto-placement slide the stage into the 0 column) and pins children for the Agents list only. T-037-09 did not carry the lesson | fixed: T-037-09 pins `.vault-side`, `.vault-stage`, `.vault-viewer` to columns 1/2/3 inside the wide block, with a Done check; `.ct-split` needs no pin (the transcript is its first child) |
| CR-33 | minor | traceability | T-037-15, `settings.js:90-1908`, `:1926-1951` | The plan does not say whether `layoutPanel()` folds. All 11 Settings panels use `collapse: {id: "set.*"}` and `jumpBar()` builds chips only from `section.panel.collapsible` | fixed: collapsible, id `set.layout`, `open: false`, outside the 18 FR-12 ids (P-11's pattern covers `ov`, `as`, `ag`, `vault` prefixes only); P-14 asserts the id once |
| CR-34 | major | untestable | T-037-03 Done, R10 | The lane/dock-specific API (host != owner, ordinal, primary flag, drag hooks) is first exercised in S4 and S7, so a C1 gap surfaces three slices late | fixed: T-037-03 Done adds a Grep that every option named in `## C1 API contract` appears in `splitter.js`; the contract gets items (i) host is a containing block and (j) option names listed verbatim |
| CR-35 | minor | untestable | T-037-02 P-7 | "`.sp` before the first `.ob-` rule" anchors on another ticket's block (`styles.css:2201`); if T-020/T-021 rename or move it the test errors or lies | fixed: `.sp` line < `.ob-scrim` line when that rule exists, and in every case < 85% of the file's lines |
| CR-36 | minor | untestable | T-037-02 helpers; five [PY] ACs spot-checked | Helpers `_read`, `_strip_comments`, `_media_blocks` cannot support P-5, P-6 or P-10. Feasibility: AC-5.3 (every `var(--sp-` in a wide block), AC-4.1 (`prefs.set(` once, in a helper reading `layout`), AC-4.2 (one `addEventListener("resize"` inside a flagged installer) and AC-12.1 (18 literal ids) are robust against T-031/T-036 (new file or literal ids); AC-11.1 (fresh `.dbody`) is only a structural proxy; real proof is B-6 | fixed: `_func_body(src, name)` and `_depth_at(src, idx)` added to T-037-02 (brace-depth scanner, about 25 lines); this, the print block and the two extra P-8 tests are the +1.0 h Dev on T-037-02 (2.0 to 3.0) |
| CR-37 | minor | contradiction | D-11 vs `vault.js:244-245` | D-11 says canvases stretch via CSS during a drag, but `resize()` writes inline px `style.width/height`, so skipping it freezes the canvas at its pre-drag size (clipped when the stage shrinks, blank strip when it grows) until release. AC-8.3 (zero reallocations, one after) still holds | fixed via `evolve` 2026-10-05 (decision-log "Amendment 2026-10-05"): D-11 wording amended; builder note in T-037-09; B-3 wording "frozen, not stretched, during the drag" |
| CR-38 | minor | critical-path | components C10 soft edge, breakdown 17/19 | "Reset reverts `dock.w` through the registry" can never be observed: Reset lives on Settings and `go()` closes the dock (`app.js:128`, D-18); the dock reads `dock.w` at `open()` anyway | accepted: the hook stays by construction (handle made through `C.splitter(`, one P-10 source test), no QC time; S7 after S6 is build order only |
| CR-39 | minor | traceability | [[T-037-user-stories]] lines 171-198 | 20 cells say "TBD in plan"; the mapping existed only in breakdown § AC coverage, and US-4 omitted 16 and 19 (the dock rows of AC-5.4) | fixed: both tables filled |
| CR-40 | minor | scope-drift | `about.js:220-228` | The keyboard help lists Esc but not the splitter keys; no FR or AC asks for it | accepted: out of T-037 (no requirement; a hunk in a file no task touches); "close the drawer, or clear the search box" stays true when docked; follow-up todo candidate, one row in `keysSect()` |
| CR-41 | minor | contradiction | breakdown T-037-05 Verify, plan S1 row | "`test_plugins.py` green (export glob)": that file guards palette/in-shell assets (`test_plugins.py:227-285`); the export is `console/server/export.py:90` (`*.js` glob) and needs no test | fixed: wording corrected in the breakdown |
| CR-42 | minor | effort-unrealistic | plan § Effort | Rework after the parent session's [BROWSER] matrix is outside the totals, and +10% reserve is thin for pointer/focus code that no agent can exercise (R5, R9) | accepted: stated under the Effort table; re-run `estimate(mode=forecast)` after S1 |
| CR-43 | minor | untestable | S7 tasks 16-18 | Done-criteria are Grep-only until T-037-19, so the riskiest slice has no automated net until its last task | accepted: by design (independent closure; a failing test returns to the owner task); source-regexp tests written earlier would be fitted to the same code and add no detection; S7a exit = Greps + Test command S not worse than baseline, S7b exit = P-10 green |
| CR-44 | minor | sequencing-risk | P-8, P-10 versus concurrent tickets | `var(--sp-` could false-match a foreign `--sp-` token (none today: no `--sp-` in `styles.css`); a fix of bug D-1 (`palette.js:103`) that adds a second `drawer.open(` turns P-10 red, which is a real signal about AC-10.1 | accepted: P-8 pins the six names (`list`, `rail`, `side`, `viewer`, `lane`, `dock`); a P-10 failure on a second opener goes to `evolve`, not a patch |

## Links
- [[T-037-summary]] · [[T-037-requirements-draft]] · [[T-037-requirements]] · [[T-037-gap-analysis]] · [[T-037-iteration-log]] · [[T-037-decision-log]]
- Plan stage: [[T-037-plan]] · [[T-037-components]] · [[T-037-task-breakdown]] · [[T-037-implementation-plan]] · [[T-037-plan-iteration-log]] · [[T-037-user-stories]]
