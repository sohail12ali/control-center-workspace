---
ticket: "T-037"
artifact: components
---

# Components: T-037

Tracks every component T-037 touches or creates, its dependencies and build status. Source: [[T-037-requirements]] (frozen, iteration 2), decisions [[T-037-decision-log]] (D-n), evidence [[T-037-context-snapshot]]. Frontend-only, one codebase (`console/static/`), so the layers are: **Foundation** (new), **Surface** (existing tabs that attach), **Shell** (page chrome), **Test**. Slices S1..S7 are *proposed* here and finalised by `plan`.

**Produced by:** `analyze-components` · **Consumed by:** `breakdown-tasks`. Line numbers are as read on 2026-10-05 and **drift** (other tickets edit the same files); builders re-grep before every Edit.

**Concurrency (restated).** `harness-t031` and `harness-t036` edit the same working tree at the same time. Never touch: `core.js` (T-036, `C.prefs`); the `.ob-*` block at the end of `styles.css` (`.ob-scrim` ~2201 to ~2275) and the print-rule `.ob-scrim` edit (`styles.css:2129`); `app.js` boot `.then` (`:346`), `setTitle` (`:371-381`), export (`:382-384`); `settings.js` `identity()` (`:1654`), the "Run setup again" row (`:1756-1768`, inside `storage()`), `kids.push(identity())` (`:1973`); `overview.js` "Open setup" button (`:122-127`); `index.html:72` onboarding tag. T-031 appends CSS at the end of `styles.css` and edits `settings.js` `assistant()`. **T-036 will add** `core.js` hunks (`C.prefs`, ~444-458), `app.js` ~266-276 (heartbeat) and `settings.js` `storage()` (Reset all preferences) during this build, so "no T-037 hunk in `core.js`" is checked against the baseline recorded in T-037-01, never as "diff empty" (CR-29). Rules: re-Read before every Edit, small edits, never revert, stash, reformat or stage others' hunks, no commit (D-21, BR-6).

---

## Foundation layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C1 `console/static/splitter.js` | new JS module (ES5 IIFE, `window.Console.splitter`) | `C.splitter(opts)`, `WIDE` (the one `(min-width: 901px)` string), `reapplyAll()`, `foldBar(host)`; pointer/keyboard/ARIA, one `layout` write per gesture, install-once global listeners, instance registry | C2 (class names must exist), `C.el`/`C.prefs` (existing) | S1 | FR-1..FR-4, FR-5 (JS half), FR-13, FR-15.2 · AC-1.2, 1.5, 1.6, 2.1-2.6, 3.1-3.4, 4.1-4.5, 5.2, 5.3, 13.1, 15.2 | pending |
| C2 `.sp-*` CSS block | CSS (mid-file in `styles.css`) | handle, hit area, focus ring, drag body class, `.sp` hidden by default and shown only in the wide block, z-index 8, fold bar | none | S1 | AC-1.3, 1.4, 1.6, 2.2, 5.1, 5.3, 5.4, 5.5 | pending |
| C3 `index.html` script tag | HTML (one line) | `<script src="splitter.js">` after `core.js`, before `app.js`, away from the onboarding tag | C1 (file must exist) | S1 | AC-1.1 | pending |

## Surface layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C4 Agents list \| main attach | view edit (`agents.js` + `.appshell` CSS) | handle on `.appshell`, `--sp-list`; collapse reuses `setListShown`/`chatListHidden`; handle absent while folded | C1, C2, C3 | S2 | FR-6 · AC-6.1-6.3; `agents.list` row of FR-5 (AC-5.6) | pending |
| C5 Agents rail attach | view edit (`agents.js` `mountChat` + `.ct-split`/`.ct-rail` CSS) | handle as child of `.ct-split`, `--sp-rail`, `railOff` collapse; the five rail sections become `C.group` with `ag.*` ids keeping `ct-panel` | C1, C2, C3 | S2 | FR-7, FR-12 (rail) · AC-7.1-7.3, 12.1, 12.2, 12.4, 12.6 | pending |
| C6 Vault panes + cards | view edit (`vault.js` + `.vault` CSS) | two handles on `.vault` (viewer one only with `.has-viewer`), drag flag around `resize()`, one `resize()` after release; card open state moves from `st.openCards` to `panelOpen` (`vault.*` ids) | C1, C2, C3 | S3 | FR-8, FR-12 (vault) · AC-8.1-8.4, 12.1, 12.2, 12.4 | built 2026-10-05 (`vault.js`, `styles.css` second wide block after `.vault.has-viewer`, P-8/P-11/P-12 vault tests; AC-8.3, 8.4, 12.4 [BROWSER] open) |
| C7 Board lane width | view edit (`board.js` `paint()`/`laneNode` + `.lanes`/`.lane` CSS) | one global `--sp-lane` on `.lanes`; handle on every non-cold lane's trailing edge (pointer delta / ordinal; first handle tabbable only) | C1, C2, C3 | S4 | FR-9 · AC-9.1-9.3 | done (AC-9.2/9.3 [BROWSER] not verified) |
| C8 Overview + Assistant folds | view edit (`overview.js`, `assistant.js`) | `C.panel(..., {collapse})` on `ov.*` (6) and `as.*` (3); `foldBar` first row; Enter guard on "Needs attention" | C1 (`foldBar`), C3 | S5 | FR-12 (ov/as), FR-13 · AC-12.1, 12.2, 12.4-12.6, 13.1, 13.2 | done |
| C9 Reset layout | view edit (`settings.js`) | new `layoutPanel()` + one `kids.push` beside `storage()`; deletes `layout`, `panelOpen`, `chatListHidden`; `reapplyAll()` + `ConsoleApp.go(active)`; toast | C1 (`reapplyAll`); observable result needs C4, C5, C6, C7, C8 | S6 | FR-14, FR-15 · AC-14.1-14.3, 15.1, 15.2 | done (code; [BROWSER] not verified) |

## Shell layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C10 Docked ticket panel | shell edit (`app.js` drawer IIFE + dock CSS + one print line) | `dockMode()` via `C.splitter.WIDE`; wide: the same `aside.drawer` lives in `#app` as a second grid column (no scrim, `role="complementary"`, left-edge handle, `--sp-dock`); else today's modal; in-place refresh with a new `.dbody`; Esc/focus rules; live mode switch | C1, C2, C3 (soft: C9 resets it through the registry) | S7 | FR-10, FR-11, `dock.w` row of FR-5 · AC-10.1-10.6, 11.1-11.6 | done (S7a, S7b) |

## Test layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C11 `console/tests/test_splitter.py` | new pytest file (source-regexp; no JS runner exists) | P-1..P-14 (P-15 = existing `test_stylesheet.py`/`test_plugins.py`); skeleton in S1, one test group added with each component | each component it checks (C1-C10) | S1 skeleton, grows S2-S7 | every [PY] AC (see matrix below) | pending |

---

## Per-component detail: files and hunks to avoid

| C | Files touched (where) | Hunks to avoid / constraints |
|---|----------------------|------------------------------|
| C1 | new `console/static/splitter.js` | No `core.js` edit (T-036); no `=>`/`let`/`const`/backtick/`innerHTML`/`localStorage`/`draggable`/`dragstart` (AC-1.5); no top-level `prefs` call (AC-4.1); `901px` once, no `max-width: 900px` (AC-5.2); no `documentElement.style`/`gridTemplateColumns` (AC-5.3); nothing attached to `.brandrow` (AC-2.2, window drag lives there, `desktop-chrome.js:74-85`). **API must separate "handle host" from "variable owner"**: lane handles sit on lanes but `--sp-lane` is on `.lanes` (D-7); the dock handle sits on the aside but `--sp-dock` is on `#app` (D-3, D-8). Lane handles also need an ordinal/scale and a "primary" flag (only the first is tabbable, others `aria-hidden`). **The host must be a containing block** (handles are `position: absolute`): see C5, C7, C10 (CR-27). |
| C2 | `styles.css` | `.sp-*` block mid-file beside `.split` (`:825-827`), never appended at the end (T-031 appends; T-020/021 `.ob-*` ends the file); no `.ob-*` line; not `:2129`. No repeated bare class (`test_stylesheet.py` `rules()` ignores nested `@media`, so overrides in the wide block are safe). Every `var(--sp-` inside `@media (min-width: 901px)`; no `transition` on `grid-template-columns` (`:1581-1584`); keep `min-width:0`/`min-height:0`. Also its own `@media print` block hiding `.sp` and the fold bar (NFR; the wide query is true when printing landscape; CR-31). **Source order:** a consumer in a wide block must come after its base rule, so `.ct-split` (~938) and `.vault` (~1585) get a second wide block right after the base rule; the existing block (~882) is only valid for `.appshell` (~839) and `.lane` (~688) (CR-25). |
| C3 | `index.html` | One line after `core.js` (`:46`), before `desktop-chrome.js`. Do not touch the onboarding tag and its comment (`:71-72`). No other `index.html` edit anywhere in T-037 (see dock decision). |
| C4 | `agents.js` (`applyShell` `:114`, `setListShown` `:130-132`, shell build `:1469-1505`); `styles.css` `.appshell` (`:839-843`) + the existing wide block (`:882-894`) | `agents.js` 900 px copies (`:112,1498,1501`) are out of scope (D-2). No second fold flag: `chatListHidden` only (BR-9). Existing `.appshell.hide-list` rules (`:878-886`) and `.ap-rail{grid-column:1}`/`.ap-main{grid-column:2}` pinning stay; the `<=900px` `.appshell{grid-template-columns:1fr}` (`:2006`) must keep winning. |
| C5 | `agents.js` (`mountChat` `:951-960`, rail sections `:1165,1177,1192,1205,1224`); `styles.css` `.ct-split` (`:938-941`), `.ct-rail` (`:960`) | Handle appended to `.ct-split`, not `#ctRail` (rebuilt per meta event). `.ct-split` gets `position: relative` (it is unpositioned today) so the handle has a containing block (CR-27). Keep class `ct-panel` on each `C.group` node so `.ct-rail > .ct-panel` at `<=900px` (`:2020`) still lays out the strip (D-12). Ids are literals, never derived from titles with counts. Do not export `collapsible` from `core.js`. |
| C6 | `vault.js` (`resize()` `:233`, observer `:450-452`, card `:522-537`, `st.openCards` `:49`, wrap `:691`); `styles.css` `.vault`/`.has-viewer` (`:1585-1591`) | The three `setTimeout(resize, 60)` (`:507,515,530`) and the `ResizeObserver` stay (D-11). The `<=900px` `:root{--vault-side:218px}` and `.vault.has-viewer{...0}` (`:2024-2025`) and `<=720px` `.vault` rules (`:2041-2044`) must still win at their widths (BR-3). Defaults: `vault.display`, `vault.forces` closed. Consumers go in a second wide block after `.vault.has-viewer` (CR-25) and the three children are pinned to columns 1/2/3 there, because `sideOff` hides the sidebar with `display:none` (the trap at `:887-891`; CR-32). `resize()` writes inline px size (`vault.js:244-245`), so the canvas freezes, not stretches, during a drag (CR-37). |
| C7 | `board.js` (`laneNode` `:175-193`, `paint()` lanes build `:261-279`); `styles.css` `.lanes` (`:682`), `.lane` (`:688-689`) | No handle on `.lane.cold` (click/Enter expands, `:194-203`). Handle must not use `draggable` (cards and lanes use HTML5 DnD, `:181-192`). `--lane-w` `:root` (`:78`), 1280 trim (`:1983`) and 720 bypass (`:2056`) unchanged. `.lane` gets `position: relative` (it is unpositioned today; CR-27); `.lane` precedes the existing wide block, so that block is valid for its consumer (CR-25). `board.js:412-458` refresh calls and `drawer` calls (`:300,398,514,521`) untouched. board.js was clean at planning time; confirm with `git diff` before editing. |
| C8 | `overview.js` (panels `:194,244,259,295,334,355`; Enter handler `:303-317`); `assistant.js` (`:149,164,167`) | `overview.js:109-131` Getting-started card and "Open setup" (`:122-127`) untouched (`ov.onboarding` keeps `onboardingOpen`). Enter guard: ignore header targets and collapsed state only. No `foldBar` in `settings.js`; do not refactor `jumpBar()` (`:1926`). |
| C9 | `settings.js`: one new function after `storage()` (ends `:1805`), one `kids.push(layoutPanel())` after `kids.push(storage(paint))` (`:1974`) | Do **not** edit inside `storage()` (the "Run setup again" row `:1756-1768` and the local `Reset all preferences` are others'); not `identity()` (`:1654`) or `kids.push(identity())` (`:1973`). Run `git diff -U0 settings.js` first; four others' hunks must be intact afterwards (AC-14.1). No `localStorage`, no `C.prefs.reset` (AC-14.2). T-036 owns "Reset all preferences". |
| C10 | `app.js` drawer IIFE only (`:14-53`); `styles.css` (dock block after `.drawer .dbody`, `:1691`; one new line in the existing print block); no `board.js` edit | `app.js` `:346`, `:371-381`, `:382-384` untouched (the `{open, close}` export is unchanged, so no export edit is needed), and `:266-276` (T-036's heartbeat). `index.html` unchanged. Print line `:2129` untouched (see dock decision). `drawer.open(` only in `board.js:300` (AC-10.1). `go()` still closes the dock (`app.js:128`). |
| C11 | new `console/tests/test_splitter.py` | Compare failing test **ids** to baseline (only `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count`), not counts (D-20). Run `pytest -o addopts=""`. |

---

## Dock placement decision (resolves D-8, which left structure to the planner)

**Decision:** in dock mode the same `aside.drawer` is a **third child of `#app`**, a second grid column beside `main#view`; in modal mode it stays on `document.body` with the scrim, as today. This is the D-8 hint, checked against the code:

- `#app` has exactly two children, `header.topbar` and `main#view` (`index.html:17-42`), and nothing in `console/` addresses it by id (grep: only CSS `styles.css:262-277`), so a class and a custom property on it collide with nothing.
- `#app` is `display:grid; grid-template-rows:auto 1fr; height:100dvh; overflow:hidden` (`styles.css:268-273`). Row 1 `auto` is the topbar's own height (`--topbar-h` 48 + `--tabs-h` 40, trimmed to 42 + 36 under `max-height:680px`, `:75-76,2075`), so a panel in row 2 starts exactly at the topbar's bottom edge with no arithmetic (AC-10.3), and the topbar (`position:sticky; z-index:20`, `:281-286`) is never covered.
- Today the aside is appended to `document.body` (`app.js:45-46`) as `position:fixed; top:0; right:0; bottom:0; width:min(430px,100vw); z-index:41` (`styles.css:1678-1685`) with a full-screen `.scrim` (`:1673-1677`): its top is 0, which is why a docked panel under the topbar needs the in-grid placement (the alternative, a hand-computed `top`, is rejected in D-8).

**CSS (all inside `@media (min-width: 901px)`, one dock block placed after `.drawer .dbody`, `styles.css:1691`):**
`#app.has-dock { grid-template-columns: minmax(0, 1fr) var(--sp-dock, 430px) }` · `#app.has-dock > .topbar { grid-column: 1 / -1 }` · `#app.has-dock > .drawer { position: relative; grid-column: 2; grid-row: 2; width: auto; min-width: 0; min-height: 0; z-index: auto; box-shadow: none; animation: none }`. **`relative`, not `static` (CR-27):** the handle is an absolutely positioned child of the aside, and `#app` is unpositioned (`styles.css:268-273`), so with a static aside the handle's containing block would be the initial containing block and it would land in the wrong place. The inherited `top/right/bottom: 0` (`:1679`) are zero relative offsets and shift nothing; `z-index: auto` keeps the handle (z 8) above `main#view` in the same stacking context. **Grid placement traced:** the aside has an explicit row and column and is placed first; the topbar (`grid-column: 1 / -1`, auto row) takes row 1; `main#view` falls into row 2 column 1; so `main#view` needs no explicit pin. `main#view` has `overflow: auto` and `min-width: 0` (`:403`), so it shrinks and scrolls; the aside is bounded by the `1fr` row (`min-height: 0`) and `.dbody` scrolls (`:1691`). `100dvh` stays on `#app` only (`:271`; no other `dvh`/`vh` rule exists), so nothing else needs the dock's width or height. Specificity beats bare `.drawer` (`:1678`) and the `<=720px` `.drawer{width:100vw}` (`:2058`, not wide anyway). `main#view` keeps its element, id and `min-width:0` (`:403`) and shrinks. Pinned placement stays inside the wide query, for the reason already written at `styles.css:887-891`.
**JS (`app.js:14-53` only):** `open()` appends the aside to `document.getElementById("app")` and sets `has-dock` + `--sp-dock` when `dockMode()`; `close()` removes the aside and `has-dock`. A live switch at 901 px moves the same node with `appendChild` (subtree and field values survive; a move blurs the focused element, so the IIFE saves and restores `document.activeElement`: builder detail, [BROWSER] check under AC-11.5). `animation: none` while docked is proposed, not required.
**Files that change:** `app.js` `:14-53` · `styles.css` (dock block + one print line) · `index.html`: **no edit beyond the C3 splitter tag** (`#app` already exists in the markup and the aside is built by `C.el`), so the dock adds no collision with `index.html:72`. `board.js` unchanged for the dock.
**Print:** the aside keeps the class `drawer`, so `styles.css:2129` (`.drawer{display:none !important}`) already hides it and **line 2129 is not edited**. What remains is the empty second grid column: add one line `#app.has-dock { grid-template-columns: minmax(0, 1fr); }` inside the existing `@media print` block, after the `.panel{...}` line (`:2131`), later in the file than the wide block so equal specificity resolves in its favour. Fallback if that block shows a collision: a separate `@media print` block beside the dock rules; P-10 must scan every print block.
**Handle:** a child of the aside at its left edge, straddling the border. `main#view` is a sibling, not an ancestor, and `#app` bounds both, so nothing clips it. Its overlap onto the right edge of `main#view` may cover that pane's scrollbar: **unverified**, [BROWSER] check with AC-1.6/AC-10.3.
**Caller compatibility (re-verified in `challenge-plan`):** `board.js:299-304` keeps the returned body only in the closure of its own `C.load`; the five refresh sites (`:412, 416, 419, 420, 458`) call `openTicket` again after `patchTicket` has already called `reload()`, so every call gets its own new `.dbody` and an older in-flight load paints into a detached node, exactly as today (D-9). `drawer.close()` is called from inside the panel (`:398, 514, 521`) and from `go()` (`app.js:128`), which also removes `has-dock`. There is no other opener: `palette.js:103` calls `app.drawer(...)` as a function (bug D-1, out of scope). **Not verifiable by reading, so a [BROWSER] item (B-6):** focus after `appendChild` on a live mode switch, and the handle over the `main#view` scrollbar.
**Q1 note:** the whole dock is behind `dockMode()` (D-1); if the user picks the opt-in option, only that expression and one Settings row change.

---

## Dependency graph

Edge = "depends on". `──►` hard (cannot build or verify without), `··►` soft (verified later, not a build blocker).

```
C2 .sp CSS ◄── C1 splitter.js ◄── C3 script tag ◄──┬── C4 Agents list|main
(root)          (class names must exist)            ├── C5 Agents rail
                                                    ├── C6 Vault
                                                    ├── C7 Board lane
                                                    ├── C8 Overview/Assistant
                                                    └── C10 Dock (also needs C1, C2 directly)
C9 Reset layout ──► C1 only (hard);  C4, C5, C6, C7, C8 ··► C9 (soft: the reset is observable only once they exist)
C11 test_splitter.py ──► every component it checks (C1..C10); skeleton from C1+C2+C3, one group added per slice
```

| C | Depends on (hard) | Soft | Class |
|---|-------------------|------|-------|
| C1 | C2 | | middle |
| C2 | none | | **root** |
| C3 | C1 | | middle |
| C4, C5, C6, C7 | C1, C2, C3 | | middle |
| C8 | C1, C3 | | middle |
| C9 | C1 | C4, C5, C6, C7, C8 (the reset is only observable once they exist) | middle |
| C10 | C1, C2, C3 | none (build order puts it after C9; the old "reset reverts `dock.w`" soft edge can never be observed: Reset lives on Settings and `go()` closes the dock, D-18; CR-38) | middle |
| C11 | C1..C10 (each test group needs its component) | | **leaf** |

Edges (CR-26, one edge set with [[T-037-task-breakdown]] § Dependency and ordering summary): **30 hard** (1 + 1 + 12 + 2 + 1 + 3 + 10) + **6 soft/ordering** (5 "observable only with" edges into C9, 1 build-order edge C10 after C9). It was drawn as 35 hard before `challenge-plan`, which contradicted the C9 row. Depth by hard edges: 5 levels (C2 · C1 · C3 · {C4..C10} · C11); depth in the sequential build order: 7 (C2 · C1 · C3 · {C4..C8} · C9 · C10 · C11).
**Critical path (build order):** C2 → C1 → C3 → (C4 | C5 | C6 | C7 | C8) → C9 → C10 → C11, 7 nodes. By size and risk the heavy nodes are **C1** and **C10**; at task level the Dev critical path is the whole build (31.5 h, sequential).
**Bottlenecks (all pending):** C1 (9 dependents; one API must serve four attach shapes), C2 and C3 (7 each; C2 also lives in the hottest shared file). **Design C1's API against its two hardest consumers before S1 is called done:** the dock (handle host is the aside, `--sp-dock` owner is `#app`, mode switch, reset through the registry) and the lane (handle host is a lane, `--sp-lane` owner is `.lanes`, ordinal scaling, first handle only tabbable).
**Parallelizable (logically):** C4+C5 (`agents.js`), C6 (`vault.js`), C7 (`board.js`), C8 (`overview.js`/`assistant.js`) touch disjoint JS files, so they are independent chains. **Not parallelised in practice:** one working tree, T-031/T-036 editing concurrently, and `styles.css` is shared by all, so the build is sequential.
**Circular dependencies: none.** Every edge runs from a consumer to the foundation (C2 ◄ C1 ◄ C3 ◄ surfaces ◄ C11; C9 and C10 are surfaces for this purpose); CSS never depends on JS; C1 knows no surface code (surfaces register themselves, C1 only walks the registry). The runtime loop `reapplyAll()` → `ConsoleApp.go()` → surface build → `C.splitter()` is a call flow, not a build dependency. **Isolated components: none** (C11 ties to all).

---

## Safe sequential build order

Follows the analysis' suggestion; **no adjustment of the order** (S1 is three builder runs and S7 two, see [[T-037-task-breakdown]] Conventions). Each slice ends with `pytest -o addopts=""` on `test_splitter.py`, `test_stylesheet.py`, `test_plugins.py`, failing ids compared to the baseline (D-20), then `git diff` to confirm other tickets' hunks are intact.

| Slice | Components | Why here | Test groups that become checkable |
|-------|-----------|----------|-----------------------------------|
| S1 | C2 → C1 → C3 → C11 skeleton | classes before JS (`test_every_class_the_js_styles_actually_exists` checks hyphenated JS classes); tag last so nothing loads a half-built file; tests pin the API before any consumer | P-1, P-2, P-3, P-4, P-5, P-6, P-7, P-9, P-15 |
| S2 | C4 → C5 | same file (`agents.js`) and CSS region (`styles.css:839-964`); C4 is the simplest consumer and proves the API on an existing collapse (`setListShown`); C5 adds the `.ct-split` attach and rail `C.group` sections | P-12 (agents), P-11 (rail part), P-8 (agents rows) |
| S3 | C6 | Vault: drag flag around `resize()` plus card state moved to `panelOpen` | P-12 (vault flag), P-11 (vault part) |
| S4 | C7 | board lanes: first consumer with host != variable owner and ordinal scaling | P-12 (lane variable), P-8 |
| S5 | C8 | needs `foldBar` (C1); finishes the 18 section ids, so the "each id once, none across files" check is only final here | P-11 (final), P-13 |
| S6 | C9 | all `layout`, `panelOpen`, `chatListHidden` consumers exist, so AC-14.3 can be exercised on every surface | P-14 |
| S7 | C10 | **last**: it changes page structure (`#app` grid) and everything else should already be stable (build order only; no soft edge to C9, CR-38). Two builder runs: S7a = C10 mode switch, layout and handle; S7b = focus, Esc, refresh, print, tests | P-10, P-8 (dock) |

After S7 the parent session runs the [BROWSER] matrix B-1..B-13; AC-12.3 evidence (`git diff` shows no T-037 hunk in `core.js`) and AC-15.1 (after T-036 lands) stay open until then.

## Test-group to component map (for C11)

| Test | Checks | Component(s) |
|------|--------|--------------|
| P-1 | script order | C3 |
| P-2, P-3, P-4, P-5, P-6, P-9 | ES5 hygiene, ARIA/keys, pointer API, prefs write helper, listeners once, `901px` once | C1 |
| P-7 | `.sp` CSS present, mid-file, hidden by default | C2 |
| P-8 | every `var(--sp-` inside a `@media (min-width: 901px)` block; no grid transition | C2, C4-C7, C10 |
| P-10 | drawer contract, one opener, `dockMode()`, print | C10 |
| P-11 | section ids, Enter guard, Vault `panelOpen`, rail `C.group`/`ct-panel` | C5, C6, C8 |
| P-12 | per-surface attach points, vault flag, lane variable | C4, C5, C6, C7 |
| P-13 | `foldBar` queries at click time | C1, C8 |
| P-14 | Settings one function, one push | C9 |
| P-15 | existing stylesheet/plugin tests | all |

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Foundation (C1-C3) | 3 | 3 | 0 | 0 |
| Surface (C4-C9) | 6 | 6 | 0 | 0 |
| Shell (C10) | 1 | 1 | 0 | 0 |
| Test (C11) | 1 | 1 | 0 | 0 |
| **Total** | **11** | **11** | **0** | **0** |

Every FR (1-15) maps to at least one component (FR-1..4 C1; FR-5 C1, C2, C4-C7, C10; FR-6 C4; FR-7 C5; FR-8 C6; FR-9 C7; FR-10, FR-11 C10; FR-12 C5, C6, C8; FR-13 C1, C8; FR-14, FR-15 C9) and every [PY] AC to C11.

## C1 API contract

Design only (T-037-01, no code), inserted above `## Links` so that block still ends the file. Paper-checked on 2026-10-05 against the real consumers: `board.js` `laneNode` 175-205 (the lane node is built before it has a parent) and `paint()` 261-279 (a fresh `.lanes` every paint); `app.js:17-53` (aside appended to `document.body`); `core.js:259-298` (`section.dataset.panelId`, `section._setOpen`); `.appshell` 839 and `.vault` 1585 (already `position: relative`), `.ct-split` 938 and `.lane` 688 (not). Option names below are verbatim: T-037-03 Greps each as `opts.<name>`.

**Exports on `window.Console.splitter` (only these four):** `C.splitter(opts)` returns the handle element · `C.splitter.WIDE` · `C.splitter.reapplyAll()` · `C.splitter.foldBar(host)`. Internals named here: `registry`, `writeLayout`.

- **(a) Host vs owner, two options.** `opts.host`: the element the handle is appended to; it must be a containing block (i). `opts.owner`: the element that receives `--sp-<cssVar>`, or a function returning it, resolved on every apply (a lane is built before its `.lanes` exists, so it passes `function () { return lanes; }`; a null return skips the write). Default `owner` = `host`. `opts.pane`: the element whose edge is measured and whose id goes into `aria-controls` (assigned `sp-pane-N` when it has none). `opts.dir`: `1` when the pane grows as the pointer moves right (handle on the pane's right edge: list, side, lane), `-1` when it grows moving left (left edge: rail, viewer, dock).
- **(b) Scale and primary.** `opts.ordinal` (default 1): the pointer delta is divided by it, so lane k's edge, which moves k times the width change, stays under the pointer; it counts non-cold lanes only. `opts.primary` (default true): only a primary handle gets `tabindex="0"`, `aria-valuenow/min/max` and key handling; the others are pointer-only with `aria-hidden="true"`. For `board.lane` the primary is the first non-cold lane.
- **(c) Per-handle options.** `opts.key` (`"group.member"` inside `layout`, e.g. `"agents.list"`), `opts.cssVar` (`list|rail|side|viewer|lane|dock`), `opts.label` (aria-label), `opts.min`, `opts.max` (px, hard bounds). **No default width is passed**: the default lives only in the CSS fallback `var(--sp-x, <today's value>)` and the current width is the pane's measured width. `opts.flexPane` (element or function) + `opts.flexMin` (px): on drag and keys the maximum is lowered to `width + (flexPane width - flexMin)`; at apply the clamped value is written, then lowered by any shortfall of `flexPane` below `flexMin` (never below `min`), and the stored value is never touched (D-4). `opts.onDragStart(handle)` / `opts.onDragEnd(handle, changed)` run around every gesture on every end path (up, cancel, `lostpointercapture`, handle removed: that end writes the last applied width once, if it changed, then calls `reapplyAll()` so a rebuilt owner picks it up); Vault passes its `resize()` defer flag and flush, the board its repaint guard. Collapse (agents.list, agents.rail, vault.side only): `opts.collapseGet()` (is it folded), `opts.collapseSet(off)` (surface-owned; the list passes `setListShown(!off)`), `opts.collapseKey` (layout member the splitter stores the boolean in, e.g. `"agents.railOff"`; absent when the surface owns the state, as `chatListHidden` does for the list), `opts.keepWhenCollapsed` (rail and side true: the handle stays at the container edge as the restore control; list false: `handle.hidden = true`, `.list-reveal` restores). A release below `min / 2` collapses; the stored width key is untouched, so restore returns to it (or to the CSS default when absent). ArrowRight changes the width by `dir * 16` (Shift 64), ArrowLeft by `-dir * 16`: the handle moves the way the arrow points.
- **(d) Registry.** `registry` is an array of `{ opts, host, pane, handle, apply }`. Every attach, window `resize`, wide-query `change` and `reapplyAll()` first drops entries whose `host.isConnected` is false. `apply()` re-reads `layout` (never cached), clamps, writes or removes the owner variable, calls `collapseSet` when the stored fold state differs, repositions the handle, and **never writes** `layout`; an entry mid-drag is skipped. `reapplyAll()` = prune + `apply()` on each. Attach always applies once, because an owner such as `.lanes` is new on every paint. **An open dock** is attached by `open()` with host = the aside and owner = `function () { return document.getElementById("app"); }`; while the aside is connected its entry is live, so Reset layout (`del("layout")` then `reapplyAll()`) reaches it with no dock-specific code, and a closed dock's entry is pruned. The attach is unconditional: below 901 px the handle is `display: none` and `--sp-dock` is consumed only by `#app.has-dock`, so a modal open is unaffected.
- **(e) `WIDE`** is the string `"(min-width: 901px)"`, the only `901px` in `splitter.js`; one lazily created `matchMedia(WIDE)` serves the `change` listener, and `app.js` `dockMode()` reads `window.matchMedia(C.splitter.WIDE).matches`. JS never branches on width to write a variable (CSS consumes `--sp-*` only in the wide block, so writing at any width is inert).
- **(f) `foldBar(host)`** returns a `div.sp-foldbar` holding "Expand all" and "Collapse all" `btn sm` buttons; the caller inserts it as the first row. Both handlers run `host.querySelectorAll("[data-panel-id]")` at click time (panels are rebuilt) and call `node._setOpen(true|false)` (`core.js:296`, which persists to `panelOpen` itself). No state is captured; `layout` is not involved.
- **(g) One write helper.** `writeLayout(path, value)` holds the only `prefs.set(` in the file: read `C.prefs.get("layout", null)`, start `{ v: 1 }` if it is not a plain object, copy the group object, set `group.member = value` (delete it when `value === undefined`), keep every unknown key, `C.prefs.set("layout", obj)`. Callers: drag release (only if the width changed), a key step, collapse/restore, double-click (deletes `key`). Never apply, clamp, resize or `reapplyAll()`; never `C.prefs.reset`.

**(h) Paper walk-through, all six rows (host, owner, variable named for each):**

| Row | host (handle child of) | owner (holds the variable) | pane measured, `dir` | variable and consumer | extras |
|---|---|---|---|---|---|
| `agents.list` | `#agShell` (`.appshell`, relative) | `#agShell` (default) | `.ap-rail`, 1 | `--sp-list`: `.appshell` columns, fallback `clamp(208px,22vw,302px)` | `flexPane .ap-main` 320; `collapseSet` = `setListShown`, no `collapseKey`, `keepWhenCollapsed` false |
| `agents.rail` | `.ct-split` (needs `position: relative`; not `#ctRail`, which scrolls and is rebuilt per meta event) | `.ct-split` | `#ctRail`, -1 | `--sp-rail`: `.ct-split` columns, fallback 260px | `flexPane .ct-scroll` 320; `collapseKey "agents.railOff"`, `keepWhenCollapsed` true; re-attached by `mountChat`, old entry pruned |
| `vault.side` | `.vault` (relative) | `.vault` | `.vault-side`, 1 | `--sp-side`: `.vault` columns, fallback `var(--vault-side)` | `flexPane .vault-stage` 200; `collapseKey "vault.sideOff"`, `keepWhenCollapsed` true |
| `vault.viewer` | `.vault` | `.vault` | `.vault-viewer`, -1 | `--sp-viewer`: `.vault.has-viewer` columns, fallback `var(--vault-viewer)` | `flexPane .vault-stage` 200; attached only while `.has-viewer`; `onDragStart/End` = `resize()` flag and flush |
| `board.lane` | the lane node (`.lane`, needs `position: relative`) | `.lanes`, by function | the lane node, 1 | `--sp-lane`: `.lane` flex-basis and max-width, fallback `var(--lane-w)` | one handle per non-cold lane, `ordinal` k, `primary` only on the first; no `flexPane` (the board scrolls sideways); `onDragStart/End` = repaint guard |
| `dock.w` | the `aside.drawer` (`position: relative`, never `static`) | `#app`, by function | the aside, -1 | `--sp-dock`: `#app.has-dock` second column, fallback 430px | `flexPane main#view` 360; no collapse |

- **(i) Containing block and handle offset.** `.sp` is `position: absolute; top: 0; bottom: 0` with `transform: translateX(-50%)`; JS writes only `style.left`: the pane's measured edge in host coordinates, `paneRect[dir === 1 ? "right" : "left"] - hostRect.left - host.clientLeft`, clamped to `[w/2, host.clientWidth - w/2]` with `w = handle.offsetWidth` (so a collapsed pane's handle sits on the container edge, still visible). It is measured after every apply, every drag frame (rAF) and every resize, and skipped when the handle has no box (`offsetWidth === 0`). A fluid default such as `clamp(208px,22vw,302px)` is therefore measured, never duplicated in JS; a pane at `display: none` measures 0 and counts as collapsed. `.appshell` and `.vault` are already containing blocks; `.ct-split` (T-037-07), `.lane` (T-037-11) and the dock aside (T-037-16) get `position: relative` in CSS. Lane handles overhang their lane by at most 10 px, inside the 14 px side padding of `.lanes`.
- **(j) Verbatim option names:** `host`, `owner`, `pane`, `dir`, `ordinal`, `primary`, `key`, `cssVar`, `label`, `min`, `max`, `flexPane`, `flexMin`, `onDragStart`, `onDragEnd`, `collapseGet`, `collapseSet`, `collapseKey`, `keepWhenCollapsed` (19). Not options: `WIDE`, `reapplyAll`, `foldBar`, `writeLayout`, `registry`.
- **Findings that shaped the design:** the lane node has no parent yet at construction (lazy `owner`); `.lanes` and `.ct-split` are rebuilt on every paint or chat switch (attach applies once, registry pruning, no per-attach listeners); the dock needs host != owner and `reapplyAll()` reaching an open aside (d); a lane repaint mid-drag is an ordinary end path. **Decisions made here, not in the decision log:** key direction (`dir * 16`), the rule that no default width is passed to JS, and the repaint-end write; all [BROWSER] checks in T-037-20.

## Links
- [[T-037-summary]] · [[T-037-requirements]] · [[T-037-user-stories]] · [[T-037-decision-log]] · [[T-037-context-snapshot]] · [[T-037-plan]] · [[T-037-components]] · [[T-037-task-breakdown]] · [[T-037-implementation-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
