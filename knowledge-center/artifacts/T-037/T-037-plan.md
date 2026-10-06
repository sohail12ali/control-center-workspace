---
ticket: "T-037"
artifact: plan
---

# Plan: T-037

Structure: **multi-layer** (11 components, 20 tasks, several slices) — detail in [[T-037-components]], [[T-037-task-breakdown]], [[T-037-implementation-plan]]. This file is the canonical checklist, effort and risk register. Task detail (Covers / May touch / Must NOT touch / Tests / Done) lives only in the breakdown, under the task id.

## Approach

- One reusable `C.splitter(opts)` in new `console/static/splitter.js` (ES5 IIFE, `window.Console.splitter`) plus one `.sp-*` CSS block mid-file in `styles.css` (C1, C2). No `core.js` edit.
- Sizes are `--sp-*` custom properties on the pane container, consumed only inside `@media (min-width: 901px)` as `var(--sp-x, <today's value>)`: no stored width means no visual change (D-2, D-3).
- One `layout` object through `C.prefs` (interface only; T-036 owns the implementation, contract `t037-layout-contract`); read-modify-write helper, clamp at apply (D-4).
- Sections use `C.splitter.foldBar` plus the exported `C.panel`/`C.group`, 18 literal ids, no `collapsible` export (D-12, D-13).
- Dock: the same `aside.drawer` is moved into `#app` as a second grid column when `dockMode()` is true, modal otherwise ([[T-037-components]] "Dock placement decision", D-8).
- Build is sequential, one builder, slices S1..S7 in a shared tree, Guard G after every task; verifier slice V; [BROWSER] ACs belong only to T-037-20. Builder runs are at most 6 h: S1 is three runs (S1a 01-02, S1b 03, S1c 04-05), S7 two (S7a 16-17, S7b 18-19), each Write/Edit at most ~150 lines (CR-28).
- Three traps found by `challenge-plan` and built into the tasks: a wide-block consumer must follow its base rule in source order, so `.ct-split` and `.vault` get a second wide block (CR-25); every handle host must be a containing block, so the docked aside is `position: relative` (CR-27); a hidden grid child needs its siblings pinned, so Vault `sideOff` pins its columns (CR-32). Single edge set for dependencies: [[T-037-task-breakdown]] § Dependency and ordering summary (CR-26).
- Q1 (dock replaces overlay vs opt-in) is OPEN and non-blocking: the default is built (D-1). The opt-in alternative is a named follow-up (one expression in `dockMode()` + one Settings toggle row, about 1 h Dev + 0.5 h QC, not in the totals).

## Slices

Common exit for every slice: Test command S (`pytest -o addopts="" console/tests/test_splitter.py console/tests/test_stylesheet.py console/tests/test_plugins.py`) with failing ids a subset of the baseline (only `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count`, D-20), and `git diff --stat` shows no foreign hunk moved and no T-037 change to `core.js`, both **versus the baseline recorded in `T-037-progress.md` by T-037-01** (T-036 will add its own `core.js` and `app.js` ~266-276 hunks mid-build, so "diff empty" would fail for the wrong reason; CR-29). Entry for S2+ = previous slice exit. Run order and gates: [[T-037-implementation-plan]].

| Slice | Tasks | Components | Slice-specific exit (tests named in the breakdown) |
|-------|-------|------------|-----------------------------------------------------|
| S1 Foundation (3 runs) | S1a 01-02, S1b 03, S1c 04-05 | C2, C1, C3, C11 skeleton | S1a: contract + P-7, P-8 green · S1b: P-2..P-5, P-9 green, contract option names found in `splitter.js` · S1c (S1 exit): P-1..P-9, P-13 green; `test_plugins.py` green; diff lists only `styles.css`, `index.html`, `splitter.js`, `test_splitter.py`, `T-037-components.md` (entry: lane moved to in-progress, baseline recorded) |
| S2 Agents | 06-08 | C4, C5 | P-8, P-11 (rail), P-12 (list, rail) green |
| S3 Vault | 09-10 | C6 | P-11 (vault), P-12 (vault) green; `setTimeout(resize, 60)` count still 3 |
| S4 Board lane | 11-12 | C7 | P-8, P-12 (lane) green; `board.js` hunks only in `laneNode` and `paint()` |
| S5 Overview, Assistant | 13-14 | C8 | P-11 (all 18 ids), P-13 green; no `foldBar` in `settings.js` |
| S6 Reset layout | 15 | C9 | P-14 green; exactly two T-037 hunks in `settings.js` |
| S7 Dock (2 runs) | S7a 16-17, S7b 18-19 | C10, C11 | S7a: Greps + Test command S not worse than baseline · S7b (S7 exit): P-8 (dock rows), P-10 green; `app.js` hunks only in the drawer IIFE |
| V Verification | 20 | C11 | full suite once, failing ids compared; B-1..B-13 listed "not verified in a browser"; AC-15.1 recorded open |

## Tasks

Heading format is machine-read (`console context`, `progress-tracker`): keep `### [ ] T-037-NN — title (X h)`; flip to `[x]` only on done with evidence. Effort = Dev + QC from the breakdown. The Done line is a pointer plus the key check; subtask lists are not repeated here (breakdown is canonical). **Depends on** lists hard edges; `after N` is build order only (CR-26); the single edge set is the breakdown's § Dependency and ordering summary. Every hard edge points to a lower task number, so there is no cycle and no task is blocked at its turn.

**S1 Foundation** (three runs: S1a = 01-02, S1b = 03, S1c = 04-05)

### [x] T-037-01 — Design C1's API against the dock and lane use cases (1.5 h)
- **Done-criteria:** `## C1 API contract` appended to [[T-037-components]], ≤70 lines, items (a)-(j), six walk-through rows, no "TBD"; first step `PYTHONUTF8=1 python console/kanban.py ticket move T-037 in-progress`, then the `git diff -U0` baseline of the six shared files recorded in `T-037-progress.md` (CR-29).
- **Basis:** Dev 1.0 + QC 0.5; one ~40-60 line contract, paper walk-through of six rows.
- **Depends on:** —

### [x] T-037-02 — `.sp-*` CSS block + `test_splitter.py` skeleton (3.5 h)
- **Done-criteria:** `-k "p7_ or p8_"` green (Test command S); `.sp` rules sit above the first `.ob-` line; one added `.sp-*` block plus its own `@media print` block hiding `.sp` and the fold bar in `styles.css`, both mid-file; P-8 includes the source-order and `min-height: 0` tests.
- **Basis:** Dev 3.0 + QC 0.5; ~60-line CSS block + print block in the hot shared file, five test helpers (`_func_body`, `_depth_at` are new), P-7 and three P-8 tests (Dev was 2.0; +1.0 after `challenge-plan`, CR-30/31/35/36).
- **Depends on:** T-037-01

### [x] T-037-03 — `splitter.js` core: attach, ARIA, pointer, keys, collapse, persistence (4 h)
- **Done-criteria:** P-2..P-5, P-9 green; forbidden-token Grep in `splitter.js` = 0; `901px` count 1; `prefs.set(` count 1; every option named in the C1 contract item (j) is found in `splitter.js` (CR-34).
- **Basis:** Dev 3.0 + QC 1.0; ~200 lines ES5 + five test groups (the 3 h cap bucket).
- **Depends on:** T-037-01, T-037-02

### [x] T-037-04 — `splitter.js` registry, install-once listeners, `reapplyAll`, `foldBar` (3 h)
- **Done-criteria:** P-6, P-13 green; `addEventListener("resize"` count 1 behind an installed flag; `isConnected` present; no `C.prefs.reset`.
- **Basis:** Dev 2.0 + QC 1.0; registry pruning, listeners once, `reapplyAll`, `foldBar`; concurrency-flavoured.
- **Depends on:** T-037-03

### [x] T-037-05 — `<script>` tag in `index.html` + script-order test (1 h)
- **Done-criteria:** P-1 green; exactly one added `index.html` line between `core.js` and `app.js`; S1 checkpoint P-1..P-9 + `test_plugins.py` green.
- **Basis:** Dev 0.5 + QC 0.5; one HTML line + one test; QC runs the S1 checkpoint.
- **Depends on:** T-037-04

**S2 Agents**

### [x] T-037-06 — Attach Agents list/main splitter and wide-block CSS (2 h)
- **Done-criteria:** `-k "p12_ or p8_"` green; `var(--sp-list` only inside the wide block with the clamp fallback; `chatListHidden` count unchanged.
- **Basis:** Dev 1.5 + QC 0.5; one attach + CSS fallback on an existing collapse.
- **Depends on:** T-037-05

### [x] T-037-07 — Attach transcript/rail splitter in `mountChat` (2 h)
- **Done-criteria:** `-k "p12_ or p8_"` green; handle appended to `.ct-split` (not `#ctRail`); `var(--sp-rail` only in a wide block placed after the `.ct-split` rule, and `.ct-split` is `position: relative` (CR-25, CR-27).
- **Basis:** Dev 1.5 + QC 0.5; attach in `mountChat`; rail is rebuilt per meta event.
- **Depends on:** T-037-05; after T-037-06

### [x] T-037-08 — Convert rail sections to `C.group` with `ag.*` ids (2 h)
- **Done-criteria:** `-k "p11_"` green; five `ag.*` ids once each; `ct-panel` count ≥5; `core.js` unchanged versus the T-037-01 baseline.
- **Basis:** Dev 1.5 + QC 0.5; five section conversions, ids, class kept.
- **Depends on:** none (hard); after T-037-07

**S3 Vault**

### [x] T-037-09 — Two Vault handles, drag flag around `resize()` (3 h)
- **Done-criteria:** `-k "p12_ or p8_"` green; `setTimeout(resize, 60)` count = 3 (unchanged); flag test is the first statement in `resize()`; handles appended to `.vault`, not `.vault-stage`; consumers in a wide block after `.vault.has-viewer`, and `.vault-side`/`.vault-stage`/`.vault-viewer` pinned to columns 1/2/3 there (CR-25, CR-32).
- **Basis:** Dev 2.0 + QC 1.0; two handles + drag flag around canvas `resize()`; reallocation risk.
- **Depends on:** T-037-05

### [x] T-037-10 — Vault card state moves to `panelOpen` (`vault.*` ids) (1.5 h)
- **Done-criteria:** `-k "p11_"` green; `openCards` count in `vault.js` = 0; four `vault.*` ids once each; `core.js` unchanged versus the T-037-01 baseline.
- **Basis:** Dev 1.0 + QC 0.5; state migration of four cards.
- **Depends on:** none (hard); after T-037-09

**S4 Board lane width**

### [x] T-037-11 — `--sp-lane` consumed in the wide block (CSS) (1 h)
- **Done-criteria:** `-k "p12_ or p8_"` green; `var(--sp-lane` only inside the wide block; `--lane-w` count in `styles.css` unchanged; `.lane` is `position: relative` (CR-27).
- **Basis:** Dev 0.5 + QC 0.5; one CSS consumer line.
- **Depends on:** T-037-05

### [x] T-037-12 — Lane handles in `board.js` (`laneNode`, `paint()`) (3 h)
- **Done-criteria:** `-k "p12_"` green; `git diff -U0 console/static/board.js` hunks only in `laneNode` and `paint()` lane build; no `draggable` in added lines; no handle on `.lane.cold`.
- **Basis:** Dev 2.0 + QC 1.0; ordinal scaling, primary flag, repaint safety in a DnD file.
- **Depends on:** T-037-05, T-037-11

**S5 Overview and Assistant folds**

### [x] T-037-13 — Overview: six `ov.*` panels, `foldBar`, Enter guard (3 h)
- **Done-criteria:** `-k "p11_ or p13_"` green; six `ov.*` ids; no `overview.js` hunk in the Getting-started card (~109-131); guard reads header target and collapsed state in the handler.
- **Basis:** Dev 2.0 + QC 1.0; six panels + `foldBar` + Enter guard on a live handler.
- **Depends on:** T-037-05

### [x] T-037-14 — Assistant: three `as.*` panels, `foldBar`; final id and `foldBar` tests (2 h)
- **Done-criteria:** the 18-id test (`test_p11_all_18_ids_each_once_none_across_files`) green; `foldBar` count in `settings.js` = 0; `core.js` unchanged versus the T-037-01 baseline, so no T-037 hunk (AC-12.3).
- **Basis:** Dev 1.5 + QC 0.5; three panels + `foldBar` + the final 18-id gate.
- **Depends on:** T-037-05, T-037-08, T-037-10, T-037-13 (the gate reads their ids)

**S6 Reset layout**

### [x] T-037-15 — `layoutPanel()` and one `kids.push` in `settings.js` (2 h)
- **Done-criteria:** `-k "p14_"` green; `git diff -U0 console/static/settings.js` shows exactly two T-037 hunks and the foreign hunks recorded at the start are byte-identical; three `C.prefs.del`, no `C.prefs.reset`, no `localStorage`; the panel is collapsible with id `set.layout`, `open: false`, like the 11 other Settings panels (CR-33).
- **Basis:** Dev 1.5 + QC 0.5; one function + one push; foreign-hunk discipline.
- **Depends on:** T-037-04 (hard: `reapplyAll` must exist); after T-037-14 (build order: the reset is then observable on every surface)

**S7 Docked ticket panel** (last: it changes page structure; everything behind `dockMode()`)

### [x] T-037-16 — Dock mode switch and `#app` layout (3 h)
- **Done-criteria:** `function dockMode` count 1 in `app.js` using `C.splitter.WIDE`; `app.js` hunks only in the drawer IIFE; `var(--sp-dock` only in the wide block; the docked aside is `position: relative`, not `static` (CR-27); `index.html` diff still only the T-037-05 line.
- **Basis:** Dev 2.0 + QC 1.0; `#app` grid mode, role flip, live switch with focus save/restore.
- **Depends on:** T-037-05 (hard); after T-037-15 (build order only)

### [x] T-037-17 — Dock left-edge handle and `dock.w` width (2 h)
- **Done-criteria:** `--sp-dock` written on `#app`; handle appended to the aside and created via `C.splitter(`; if C1 cannot express host ≠ owner, stop and escalate (planner/`evolve`), do not patch `splitter.js` ad hoc.
- **Basis:** Dev 1.5 + QC 0.5; host ≠ owner handle, clamp against `main#view`.
- **Depends on:** T-037-16

### [x] T-037-18 — Dock focus, Esc, in-place refresh, print line (3 h)
- **Done-criteria:** `drawer.open(` count 1 in `board.js`, 0 in every other JS file; print line appears once after `.panel{`; no T-037 hunk on the `:2129` line; repeat `open()` returns a NEW `.dbody` (D-9).
- **Basis:** Dev 2.0 + QC 1.0; focus, Esc, in-place refresh, print line.
- **Depends on:** T-037-16 (hard); after T-037-17 (same IIFE)

### [x] T-037-19 — Dock tests (P-10, dock rows of P-8) (2 h)
- **Done-criteria:** `-k "p10_ or p8_"` green; all failing ids a subset of the baseline; S7 diff shows `app.js`, `styles.css`, `test_splitter.py` and no T-037 change to `core.js` (versus the baseline).
- **Basis:** Dev 1.5 + QC 0.5; five test groups + one P-8 dock group.
- **Depends on:** T-037-16, T-037-17, T-037-18

**V Verification handoff** (owner: verifier)

### [ ] T-037-20 — Full-suite run, [BROWSER] checklist B-1..B-13, evidence diffs (2 h)
- **Done-criteria:** `pytest -o addopts="" console/tests` once, failing id = baseline only; `T-037-verification.md` lists B-1..B-13 each "not verified in a browser"; no T-037 hunk in `core.js` versus the baseline in `T-037-progress.md` (AC-12.3); AC-15.1 recorded open until T-036 lands.
- **Basis:** Dev 0.0 + QC 2.0; ~450 s suite, id comparison, checklist, evidence diffs (verifier, no dev).
- **Depends on:** T-037-19

## Effort

Copied from [[T-037-task-breakdown]] § Effort summary (upfront, components basis, confidence Medium, human-equivalent hours, nothing built yet). Per-task hours are in the task headings above.

| Slice | Tasks | Dev (h) | QC (h) | Estimated (h) | Completed | In-progress | Remaining | % complete |
|---|---|--:|--:|--:|--:|--:|--:|--:|
| S1 | 01-05 (5) | 9.5 | 3.5 | 13.0 | 0 | 0 | 13.0 | 0% |
| S2 | 06-08 (3) | 4.5 | 1.5 | 6.0 | 0 | 0 | 6.0 | 0% |
| S3 | 09-10 (2) | 3.0 | 1.5 | 4.5 | 0 | 0 | 4.5 | 0% |
| S4 | 11-12 (2) | 2.5 | 1.5 | 4.0 | 0 | 0 | 4.0 | 0% |
| S5 | 13-14 (2) | 3.5 | 1.5 | 5.0 | 0 | 0 | 5.0 | 0% |
| S6 | 15 (1) | 1.5 | 0.5 | 2.0 | 0 | 0 | 2.0 | 0% |
| S7 | 16-19 (4) | 7.0 | 3.0 | 10.0 | 0 | 0 | 10.0 | 0% |
| V | 20 (1) | 0.0 | 2.0 | 2.0 | 0 | 0 | 2.0 | 0% |
| **Total** | **20** | **31.5** | **15.0** | **46.5** | **0** | **0** | **46.5** | **0%** |

- **Total 46.5 h** = Dev 31.5 + QC 15.0 (slices 13.0 + 6.0 + 4.5 + 4.0 + 5.0 + 2.0 + 10.0 + 2.0 = 46.5). It was 45.5 h before `challenge-plan`: +1.0 h Dev on T-037-02 (CR-36). **Indicative range 37.2-60.45 h** (cone 0.8x-1.3x of most likely, no reserve in the bounds). **Reserve +10%: 4.65 h**, so Final/Complete 51.15 h (about 6.4 d at 8 h, indicative, no delivery date).
- Builder runs (hours as above): S1a 01-02 = 5.0, S1b 03 = 4.0, S1c 04-05 = 4.0, S2 6.0, S3 4.5, S4 4.0, S5 5.0, S6 2.0, S7a 16-17 = 5.0, S7b 18-19 = 5.0, V 2.0 (each at most 6 h, CR-28).
- Not in the totals: the [BROWSER] matrix B-1..B-13 and UAT run by the parent session (indicative 3-4 h), rework that matrix triggers (the reserve is thin for pointer and focus code nobody can exercise here, CR-42), and the Q1 opt-in follow-up (about 1.5 h).
- Re-run `estimate(mode=forecast)` once the first slices have actuals.

### Acceptance criterion coverage

65 ACs (AC-1.1 .. AC-15.2): 30 [PY], 1 evidence-only (AC-12.3), 34 [BROWSER]. Every AC maps to at least one task. Task ids are `T-037-NN`. **[BROWSER] ACs are covered only by T-037-20 and are never marked done by a build task**; the check ids (B-1..B-13) are in [[T-037-task-breakdown]] § AC coverage.

| AC group | [PY] / evidence ACs → implemented by (checked in the same task unless noted) | [BROWSER] ACs → T-037-20 |
|---|---|---|
| AC-1 | 1.1 → 05; 1.2, 1.5 → 03; 1.3, 1.4 → 02 | 1.6 |
| AC-2 | 2.1, 2.2 → 03 | 2.3, 2.4, 2.5, 2.6 |
| AC-3 | 3.1 → 03 | 3.2, 3.3, 3.4 |
| AC-4 | 4.1 → 03; 4.2 → 04 | 4.3, 4.4, 4.5 |
| AC-5 | 5.1 → 02; 5.2 → 03; 5.3 → 02, 03 (consumers 06, 07, 09, 11, 16, 17; dock rows checked in 19); 5.4 → 02, 16 (checked 19) | 5.5, 5.6 |
| AC-6 | 6.1, 6.2 → 06 | 6.3 |
| AC-7 | 7.1 → 07 | 7.2, 7.3 |
| AC-8 | 8.1, 8.2 → 09 | 8.3, 8.4 |
| AC-9 | 9.1 → 11 (CSS), 12 (JS) | 9.2, 9.3 |
| AC-10 | 10.1 → 16, 18 (checked 19); 10.2 → 16 (checked 19) | 10.3, 10.4, 10.5, 10.6 |
| AC-11 | 11.1, 11.2 → 18 (checked 19) | 11.3, 11.4, 11.5, 11.6 |
| AC-12 | 12.1 → 08, 10, 13, 14 (final 14); 12.2 → 08, 10, 13; 12.3 (evidence) → 14, 20 | 12.4, 12.5, 12.6 |
| AC-13 | 13.1 → 04, 13, 14 | 13.2 |
| AC-14 | 14.1, 14.2 → 15 | 14.3 |
| AC-15 | 15.2 → 04 (`reapplyAll`), 15 (no `C.prefs.reset`) | 15.1 (open until T-036 lands) |

Count check: [PY] 5+2+1+2+4+2+1+2+1+2+2+2+1+2+1 = 30; evidence 1; [BROWSER] 1+4+3+3+2+1+2+2+2+4+4+3+1+1+1 = 34; total 65.

Non-AC requirements, also mapped (CR-30, CR-31): NFR "handles hidden in print" → 02 (print block, P-7) and the dock → 18, 19 (P-10); AC-5.4's `min-width:0`/`min-height:0` half → 02 (`test_p8_min_zero_kept`) and 19 (dock block).

## Risks

Scan (`op risk`) over requirements, decision-log, components, task-breakdown and memory, re-run after `challenge-plan` (part C: [[T-037-critique-report]] § Plan critique, CR-25..CR-44, 0 critical); R13 is new and R2 and R10 were extended. Re-run `plan risk` after any `evolve` or `replan`. Rated 13; **mitigated 13/13; high×high: 0**. Top risks (high×med, med×high) all carry an explicit mitigation.

| # | Risk | Likelihood | Impact | Mitigation | Owner | Source |
|---|------|-----------|--------|------------|-------|--------|
| R1 | **T-036 not landed**: `C.prefs` is still localStorage-backed, the `layout` contract is unmet, FR-15 AC-15.1 cannot be verified | Med | Med | Code only against the `C.prefs.get/set/del` interface and the D-4 `layout` shape; no `core.js` edit; AC-15.1 stays "not verified" and is recorded open in T-037-20; check `t037-layout-contract` still matches before S6 | Builder / Verifier | FR-15, D-4, [[T-036-decision-log]] `t037-layout-contract` |
| R2 | **T-031 appends to `styles.css` / edits `settings.js`; T-036 will edit `core.js`, `app.js` ~266-276 and `settings.js` `storage()`** while T-037 edits the same hunks' neighbours | High | Med | `.sp-*` block mid-file (never appended); `settings.js` limited to one function + one push; baseline of `git diff -U0` recorded in T-037-01, every check is "unchanged versus the baseline" (never "diff empty", CR-29); foreign hunks must be byte-identical (Guard G) | Builder | D-21, [[T-037-components]] C2, C9, [[T-036-summary]] |
| R3 | **Red baseline test** (`test_every_class_the_js_styles_actually_exists` on `.ob-count`) hides a new failure or is fixed by another ticket mid-build | High | Low | Compare failing test **ids**, never counts; only that one id may be red; fixing it is out of scope | Builder / Verifier | D-20 |
| R4 | **Concurrent edits**: an Edit fails or clobbers because another pipeline changed the file | High | Med | Re-Read immediately before each Edit, small local edits, retry on failure; never `Write` over a shared file; no commit, stash, reformat or staging of others' hunks; `git diff --stat` at every slice exit | Builder | D-21, BR-6, breakdown Guard G |
| R5 | **Tauri/WebView pointer capture unverified**: drag end paths and `touch-action` behave differently in the desktop shell than in a browser | Med | Med | End drag on up/cancel/`lostpointercapture`, body class removed on every path (D-23); keyboard path for every handle; B-1 and B-9 run by the parent session in browser and shell, labelled "not verified" until then | Verifier / parent session | D-23, FR-2, B-1, B-9 |
| R6 | **`collapsible()` is not exported** from `core.js`, so rail sections cannot use it directly | Low | Med | Use exported `C.group` and keep the `ct-panel` class so the `<=900px` strip rule still lays out; do not export `collapsible` (AC-12.3 evidence: no T-037 hunk in `core.js` versus the T-037-01 baseline) | Builder | D-12, T-037-08 |
| R7 | **Vault canvas reallocation** during drag (`resize()` runs per frame) | Med | Med | Drag-flag makes `resize()` return early, one `resize()` on release via the drag start/end hooks; the three `setTimeout(resize, 60)` and the `ResizeObserver` stay; B-3 in a browser | Builder / Verifier | D-11, T-037-09 |
| R8 | **Lane-handle scaled-delta geometry**: one global width, handle per non-cold lane, repaint mid-drag (the board repaints per search keystroke) | Med | Med | Settled on paper in T-037-01 (host = lane, owner `.lanes`, ordinal divisor, primary flag); drag-end hook on repaint keeps the last valid width; P-12 lane test; B-4 | Builder | D-7, D-19, T-037-12 |
| R9 | **Dock in-place refresh race and focus loss**: the board's five refresh calls re-open the drawer while docked; `appendChild` on a live mode switch blurs focus | Med | High | Repeat `open()` keeps the panel element, swaps in a NEW `.dbody`, no `slidein` replay (D-9); save/restore `document.activeElement`; listeners installed once; P-10 tests in T-037-19; B-6 in a browser | Builder | D-9, D-19, [[T-037-components]] dock decision, T-037-16, T-037-18 |
| R10 | **C1 cannot express host ≠ owner** (dock aside vs `#app`, lane vs `.lanes`); C1 has 9 dependents | Med | High | T-037-01 designs the API against the dock and lane before any code, with a six-row paper walk-through and the option names listed verbatim; T-037-03 Done greps every listed option name in `splitter.js` so a gap shows in S1, not in S4 or S7 (CR-34); T-037-17 stops and escalates via the planner/`evolve` if C1 cannot express it, no ad hoc patch | Builder / Planner | [[T-037-components]] bottleneck note, T-037-01, T-037-17 |
| R11 | **Subagent status is not evidence**: a delegated build reports done without the tree matching | Med | Med | Verify each slice from the tree, not the report: Done-line Greps, Test command S failing ids + test count, `git diff --stat` | Harness / Verifier | memory `subagent-status-not-evidence` |
| R12 | **Stacking and print**: `.sp` (z-index 8) vs topbar (20) and dock (41); an empty dock column in print; handles and fold bar printing on a wide page | Low | Med | z-index 8 per D-23; one print line `#app.has-dock{grid-template-columns:minmax(0,1fr)}` in the existing print block, a separate print block hiding `.sp` and the fold bar (T-037-02, CR-31), P-10 scans every `@media print` block; B-7 | Builder | D-23, [[T-037-components]] dock decision |
| R13 | **Silent CSS traps** (found by `challenge-plan`): a wide-block consumer placed before its base rule loses the cascade, so a stored width is inert at >=901 px (`.ct-split` ~938, `.vault` ~1585); an unpositioned handle host misplaces the handle (docked aside, `.ct-split`, `.lane`); a `display:none` grid child lets siblings slide into the 0 column (Vault `sideOff`, `styles.css:887-891`) | Med | Med | Source-order rule + `test_p8_wide_consumer_follows_its_base_rule` (CR-25); host `position: relative` in CSS, aside never `static` (CR-27); Vault columns pinned (CR-32); B-1..B-5 min/max legs in a browser | Builder | CR-25, CR-27, CR-32, [[T-037-task-breakdown]] Conventions |

## Dependencies

- Blocked by: none hard. T-036 is needed only to verify AC-15.1 (the build does not depend on it).
- Blocks: none.
- Related: T-031 (appends to `styles.css`, edits `settings.js`), T-036 (owns `C.prefs` and "Reset all preferences"; will edit `core.js`, `app.js` ~266-276 and `settings.js` `storage()`), T-020/T-021 (uncommitted hunks to preserve: `app.js` ~346, ~371-384; `index.html` ~72; `overview.js` ~122-127; `settings.js` four hunks; `styles.css` `.ob-*` block and `:2129`). Line numbers re-checked against the tree on 2026-10-05 and unchanged.
- Follow-up candidate, not a task (CR-40): one row in `about.js` `keysSect()` (~220-228) for the splitter keys. CR-37 (D-11 wording, "canvases stretch via CSS") is done: amended via `evolve` 2026-10-05, see [[T-037-decision-log]] Amendment.
- Open question: Q1 (non-blocking, default built, D-1).

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements]] · [[T-037-user-stories]] · [[T-037-decision-log]] · [[T-037-components]] · [[T-037-task-breakdown]] · [[T-037-implementation-plan]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
