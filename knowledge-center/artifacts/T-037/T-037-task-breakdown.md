---
ticket: "T-037"
artifact: task-breakdown
---

# Task breakdown: T-037

20 tasks, 7 build slices (S1-S7) plus a verification handoff (V). Inputs: [[T-037-components]] (C1-C11, hunks to avoid, build order), [[T-037-requirements]] (FR-1..15, AC ids, P-1..P-15, B-1..B-13), [[T-037-decision-log]] (D-1..D-23), [[T-037-user-stories]] (US-1..10). Task ids are `T-037-NN` in build order (the template's `{phase}-{slice}-{task}` is replaced on purpose; the slice is a column). Template: `.claude/skills/breakdown-tasks/template.md`.

**Produced by:** `breakdown-tasks` + `estimate(mode=upfront)`. **Consumed by:** [[T-037-implementation-plan]], [[T-037-plan]] (Effort table), `estimate(mode=forecast)`.

## Conventions (apply to every task)

- **Guard G (last step of every task).** Re-Read the file immediately before each Edit; small local edits; never rewrite a file; then `git diff --stat` and `git diff -U0 <file>` and confirm no foreign hunk moved. Other pipelines (`harness-t031`, `harness-t036`) and uncommitted T-020/T-021 work share this tree. No commit, stash, reformat or staging of others' hunks (D-21, BR-6). Never hand-edit `*.toml`.
- **Test command S.** `pytest -o addopts="" console/tests/test_splitter.py console/tests/test_stylesheet.py console/tests/test_plugins.py`. Compare failing **ids** to the baseline: only `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count` may be red (D-20). Test names are `test_p{N}_{what}`, so `-k "p7_"` runs one group.
- **Line numbers drift** (other tickets edit the same files): builders re-grep before every Edit.
- **Effort:** Dev h + QC h per task, buckets 0.5/1/1.5/2/3. Human-equivalent effort, not agent wall-clock. Basis and totals in § Estimate.
- **Status:** all `pending`. **[BROWSER]** ACs are never marked done by any task; they belong to T-037-20.
- **Builder runs (CR-28).** One run = a slice, or part of one: S1a = 01-02 (5.0 h), S1b = 03 (4.0 h), S1c = 04-05 (4.0 h), S2 6.0, S3 4.5, S4 4.0, S5 5.0, S6 2.0, S7a = 16-17 (5.0 h), S7b = 18-19 (5.0 h), V 2.0 (rule: <= 6 h per run). **Output discipline:** a single Write/Edit is at most ~150 lines (~4k tokens); `splitter.js` and `test_splitter.py` start small and grow by Edit, one group per task; no whole-file pastes in chat.
- **CSS source order (CR-25).** A rule inside a wide block overrides its base rule only if it comes later at equal specificity. The existing wide block (~882) precedes `.ct-split` (~938) and `.vault`/`.vault.has-viewer` (~1585-1591), so for those the consumer goes in a **second** `@media (min-width: 901px)` block placed right after the base rule; `.appshell` (~839) and `.lane` (~688) precede ~882 and may use it. `test_p8_wide_consumer_follows_its_base_rule` enforces it.
- **Host must be a containing block (CR-27).** A handle is `position: absolute` inside its host. `.appshell` and `.vault` are already `position: relative`; `.ct-split` (T-037-07), `.lane` (T-037-11) and the docked aside (T-037-16, `relative`, never `static`) get it in CSS, not inline.
- **Baseline (CR-29).** First step of T-037-01 also records `git diff -U0` hunk headers for every shared file (`core.js`, `app.js`, `index.html`, `overview.js`, `settings.js`, `styles.css`) in `T-037-progress.md` (via `progress-tracker`). Every "foreign hunks intact" and "nothing in `core.js`" check means **unchanged versus that baseline**, never "diff empty": T-036 will add `core.js` (`C.prefs`) and `app.js` ~266-276 (heartbeat) hunks mid-build.
- **Depends on column (CR-26).** Lists **hard** edges (cannot build or verify without); `after N` marks a build-order predecessor only (same file or hunk neighbourhood, one tree). The summary at the end of this file is the single source.
- **Q1 (dock replaces overlay vs opt-in) is OPEN** (user's call): S7 builds the accepted default. The opt-in alternative is a named small follow-up, not a task: change the one expression in `dockMode()` to "wide AND `C.prefs.get("ticketDock", false)`" plus one Settings toggle row (D-1).

## Slices and tasks

Each task: `Covers` (FR/AC ids) · `Split because` · `May touch` · `Must NOT touch` · `Tests` (new/extended in `console/tests/test_splitter.py`) · `Verify` · `Done` (command or file:line check). **Guard G ends every task.** Slice S1 has 5 tasks (guidance is 2-4): run it as three builder runs, S1a = T-037-01..02 (design + CSS, 5.0 h), S1b = T-037-03 (the core module, 4.0 h), S1c = T-037-04..05 (4.0 h), because C1 alone exceeds the 3 h cap and 01-03 together were 9.0 h with the larger T-037-02.

### S1 Foundation: design, CSS, splitter.js, script tag (C2, C1, C3, C11 skeleton)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-01 | Design C1's API against the dock and lane use cases | C1 (design) | FR-1..5, 9, 10, 15 (inputs) | 1 | 0.5 | done 2026-10-05 (contract in [[T-037-components]] § C1 API contract; actual effort not measured, agent run) | none |
| T-037-02 | `.sp-*` CSS block + `test_splitter.py` skeleton | C2, C11 | AC-1.3, 1.4, 5.1, 5.3 (CSS), 5.4, NFR print | 3 | 0.5 | done 2026-10-05 (`styles.css` 829-871, `console/tests/test_splitter.py`; Cmd S 29 passed + the one baseline red; actual effort not measured, agent run) | 01 |
| T-037-03 | `splitter.js` core: attach, ARIA, pointer, keys, collapse, persistence | C1 | AC-1.2, 1.5, 2.1, 2.2, 3.1, 4.1, 5.2, 5.3 (JS) | 3 | 1 | done 2026-10-05 (`console/static/splitter.js` 365 lines, P-2..P-5, P-9 in `test_splitter.py`; Cmd S 34 passed + the one baseline red; behaviour only checked in a scratch node harness, [BROWSER] items open; actual effort not measured, agent run) | 01, 02 |
| T-037-04 | `splitter.js` registry, install-once listeners, `reapplyAll`, `foldBar` | C1 | AC-4.2, 13.1 (half), 15.2 | 2 | 1 | done 2026-10-05 (`splitter.js` 465 lines: `prune`, `reapplyAll`, `install`, `foldBar`; P-6, P-13 in `test_splitter.py`; Cmd S 1 failed (baseline `.ob-count`) / 36 passed; behaviour only checked in a scratch node harness, [BROWSER] items open; attach-time prune keeps never-connected entries so late-mounted lanes survive, see [[T-037-progress]]; actual effort not measured, agent run) | 03 |
| T-037-05 | `<script>` tag in `index.html` + script-order test | C3, C11 | AC-1.1 | 0.5 | 0.5 | done 2026-10-05 (`index.html` line 47 between `core.js` 46 and `desktop-chrome.js`; P-1 in `test_splitter.py`; S1 checkpoint Cmd S 1 failed (baseline `.ob-count`) / 37 passed; actual effort not measured, agent run) | 04 |

**T-037-01 Design C1's API against the dock and lane use cases** (first build task)
- First step: `PYTHONUTF8=1 python console/kanban.py ticket move T-037 in-progress`.
- Covers: design inputs for FR-1..5, FR-9 (lane), FR-10 (dock), FR-15. Split because: C1 is the 9-dependent bottleneck; the design is reviewed against its two hardest consumers before any code (components.md bottleneck note).
- May touch: append one section `## C1 API contract` to `T-037-components.md`. No code, no `*.toml`.
- Must NOT touch: existing rows of `T-037-components.md`.
- First step also: record the baseline (Conventions, CR-29): `git diff -U0` hunk headers of `core.js`, `app.js`, `index.html`, `overview.js`, `settings.js`, `styles.css` into `T-037-progress.md` via `progress-tracker`.
- The contract names: (a) **handle host vs variable owner** as separate options (lane handle on a lane, `--sp-lane` on `.lanes`; dock handle on the aside, `--sp-dock` on `#app`); (b) **ordinal/scale and a `primary` flag** (only the first lane handle tabbable and carrying ARIA value, others `aria-hidden`); (c) per-handle key, default, min, max, optional flexible-pane bound, optional collapse hooks (list reuses `setListShown`), and drag start/end hooks (Vault's `resize()` flag, board repaint guard); (d) registry entry shape, `reapplyAll()`, how an open dock is re-applied; (e) `WIDE`; (f) `foldBar(host)`; (g) the single `layout` write helper; (h) a paper walk-through of all six rows (`agents.list`, `agents.rail`, `vault.side`, `vault.viewer`, `board.lane`, `dock.w`) with host, owner and variable named; (i) **host is a containing block** and where the handle's offset comes from (the pane's measured edge, so a fluid default such as `clamp(208px,22vw,302px)` is measured, not duplicated in JS); (j) the **option names listed verbatim** (host, owner, ordinal, primary, drag start/end hooks, collapse hooks, flexible-pane bound) so T-037-03 can Grep them (CR-34).
- Tests: none. Verify: `Grep "## C1 API contract"` in components.md, then check items (a)-(j) are present.
- Done: section exists, 70 lines or fewer, six walk-through rows, no "TBD"; `git diff -U0 T-037-components.md` shows only added lines; baseline recorded in `T-037-progress.md`.

**T-037-02 `.sp-*` CSS block + test skeleton**
- Covers: AC-1.3, 1.4, 5.1, 5.4, CSS half of 5.3; AC-1.6 is [BROWSER] (T-037-20). Split because: separate file and hunk in the hottest shared file (`styles.css`); the class names must exist before JS uses them (`test_every_class_the_js_styles_actually_exists`).
- May touch: `console/static/styles.css` (one new `.sp-*` block mid-file beside `.split` ~825-827); new `console/tests/test_splitter.py` (helpers `_read`, `_strip_comments`, `_media_blocks`).
- Must NOT touch: the end of the file (T-031 appends; `.ob-*` ~2201-2275); the `:2129` print line; any `.ob-*` line; no repeated bare class. Rules: `.sp` is `display:none` by default and shown only inside `@media (min-width: 901px)`; z-index 8; tokens for colour; no `transition` on `grid-template-columns` (~1581-1584); keep `min-width:0`/`min-height:0`.
- Block holds: `.sp` (6 px hit area, 20 px under `pointer: coarse`, `col-resize`), hover/active/focus-visible states, the drag body class (`user-select:none`, cursor), the fold bar, and **its own `@media print` block** hiding `.sp` and the fold bar (NFR "handles hidden in print"; `(min-width: 901px)` is also true when printing landscape; CR-31). Not the `:2129` line.
- Test helpers (in addition to `_read`, `_strip_comments`, `_media_blocks`): `_func_body(src, name)` and `_depth_at(src, idx)`, a brace-depth scanner of about 25 lines, needed by P-5, P-6, P-10 (CR-36). `_strip_comments` replaces comments with same-length spaces so offsets stay valid.
- Tests: **P-7** `test_p7_sp_css_present_midfile_hidden_by_default` (AC-1.3, 1.4, 5.1, NFR print: `.sp` line < `.ob-scrim` line when that rule exists and in every case < 85% of the file's lines, so it never depends on another ticket's block; default `display:none`, z-index 8, shown in a wide block; a print block hides `.sp`); **P-8** skeleton, three tests, vacuous until consumers land: `test_p8_sp_vars_only_in_wide_blocks_no_grid_transition` (AC-5.3, 5.4; pins the six names `--sp-(list|rail|side|viewer|lane|dock)`), `test_p8_wide_consumer_follows_its_base_rule` (CR-25: for each wide-block rule using `var(--sp-`, the same selector's top-level base rule is on an earlier line), `test_p8_min_zero_kept` (AC-5.4: `min-height: 0` in the `.appshell`, `.ct-split`, `.vault` base rules; the dock block gets `min-width: 0; min-height: 0`, checked in T-037-19).
- Verify: Cmd S, `-k "p7_ or p8_"`.
- Done: `Grep -n "^\.sp" console/static/styles.css` lines sit above the first `.ob-` line; `git diff -U0 console/static/styles.css` shows one `.sp-*` block, its print block and nothing else (both mid-file); no new red id.

**T-037-03 `splitter.js` core**
- Covers: FR-1..FR-4, JS half of FR-5; AC-1.2, 1.5, 2.1, 2.2, 3.1, 4.1, 5.2, 5.3. Split because: new foundation file, the highest-risk piece, independently reviewed.
- May touch: new `console/static/splitter.js` (ES5 IIFE, `window.Console.splitter`); `test_splitter.py`.
- Must NOT touch: `core.js` (T-036). In `splitter.js`: no `=>`, `let `, `const `, backtick, `innerHTML`, `localStorage`, `draggable`, `dragstart`; no top-level `prefs` call; `901px` once and no `max-width: 900px`; no `documentElement.style`/`gridTemplateColumns`; nothing attached to `.brandrow` (window drag, `desktop-chrome.js:74-85`).
- Builds the T-037-01 contract: `C.splitter(opts)`, `WIDE`, `role="separator"` ARIA with `aria-controls` ids assigned when absent, Pointer Events with capture and rAF-coalesced writes ending on up/cancel/lostpointercapture (body class removed on every path), `touch-action`, keys (arrows 16, Shift 64, Home/End, Enter), dblclick deletes the key, collapse below half the minimum and restore to last width, one read-modify-write `layout` helper, clamp at apply that never rewrites the stored value (D-4).
- Tests: **P-2** (AC-1.5), **P-3** (AC-1.2, 3.1), **P-4** (AC-2.1, 2.2), **P-5** (AC-4.1: one `prefs.set(` in a helper that reads `layout` first), **P-9** (AC-5.2 and the JS half of 5.3).
- Verify: Cmd S, `-k "p2_ or p3_ or p4_ or p5_ or p9_"`.
- Also builds the lane/dock-specific options of the contract (host != owner, ordinal/scale, primary flag, drag start/end hooks, flexible-pane bound) even though no test exercises them until S4/S7 (CR-34).
- Done: `Grep` of the forbidden tokens in `splitter.js` returns 0; `Grep -c "901px" console/static/splitter.js` = 1; `Grep -c "prefs.set(" console/static/splitter.js` = 1; each option name listed in `## C1 API contract` item (j) appears in `splitter.js` (one Grep per name, >= 1); listed P ids green.

**T-037-04 `splitter.js` registry, listeners, `reapplyAll`, `foldBar`**
- Covers: FR-4 (listeners), FR-13, FR-15.2; AC-4.2, AC-13.1 (the `foldBar` half), AC-15.2. Split because: install-once listeners and registry pruning (CR-11, D-19) are a separate review target from the attach logic.
- May touch: `splitter.js` (the file from T-037-03); `test_splitter.py`.
- Must NOT touch: anything outside `splitter.js`; same C1 token rules as T-037-03; no per-attach listeners; no `C.prefs.reset`.
- Builds: instance registry pruned by `isConnected` on every attach, resize and `reapplyAll`; window `resize` and wide-query `change` listeners installed once, lazily; `reapplyAll()` re-reads prefs and re-applies without rewriting stored values; a drag whose handle was removed ends cleanly; `foldBar(host)` whose handlers query `[data-panel-id]` under `host` at click time.
- Tests: **P-6** `test_p6_listeners_once_registry_pruned_reapplyall_exposed` (AC-4.2, 15.2); **P-13** `test_p13_foldbar_queries_at_click_time` (AC-13.1: the query sits inside the handler).
- Verify: Cmd S, `-k "p6_ or p13_"`.
- Done: `Grep -c 'addEventListener("resize"' console/static/splitter.js` = 1 and guarded by an installed flag; `Grep "isConnected" console/static/splitter.js` hits; P-6, P-13 green; no `C.prefs.reset`.

**T-037-05 Script tag + script-order test**
- Covers: AC-1.1. Split because: hard handoff and last step (tag only after the file is complete, so nothing loads a half-built file); different file, contended by another ticket's onboarding tag.
- May touch: `console/static/index.html` (one line `<script src="splitter.js"></script>` after `core.js` ~46, before `desktop-chrome.js`); `test_splitter.py`.
- Must NOT touch: the onboarding tag and its comment (~71-72); any other `index.html` line.
- Tests: **P-1** `test_p1_script_order_core_splitter_app` (core.js < splitter.js < app.js, and placed before `desktop-chrome.js`).
- Verify: Cmd S. S1 checkpoint: P-1..P-9 green, `test_plugins.py` green (its palette-order test also guards `core.js` < palette < `app.js`; `splitter.js` ships by the `*.js` export glob, `console/server/export.py:90`, no test needed; CR-41).
- Done: `Grep -n "splitter.js" console/static/index.html` returns one line between the `core.js` and `app.js` lines; `git diff -U0 console/static/index.html` shows exactly one added line; `git diff --stat` for S1 lists only `styles.css`, `index.html`, `splitter.js`, `test_splitter.py`, `T-037-components.md`.

### S2 Agents: list | main and transcript | rail (C4, C5)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-06 | Attach Agents list/main splitter and wide-block CSS | C4 | AC-6.1, 6.2 (5.6 list row, 6.3 browser) | 1.5 | 0.5 | done 2026-10-05 (`agents.js` `attachListSplitter` + `setListShown` re-apply + one call in the shell build; `styles.css` `.appshell` consumer in the existing wide block; P-12 list + P-8 list in `test_splitter.py`; Cmd S 1 failed (baseline `.ob-count`) / 44 passed; behaviour only in a scratch node harness, [BROWSER] open; actual effort not measured, agent run) | 05 |
| T-037-07 | Attach transcript/rail splitter in `mountChat` | C5 | AC-7.1 (7.2, 7.3 browser) | 1.5 | 0.5 | done 2026-10-05 (`mountChat` holds the `C.splitter` call, host `.ct-split`; `styles.css` `.ct-split` `position: relative` + a second wide block with `--sp-rail`, `.rail-off` fold and pinned children; P-12 rail + P-8 rail; [BROWSER] open; actual effort not measured, agent run) | 05; after 06 |
| T-037-08 | Convert rail sections to `C.group` with `ag.*` ids | C5 | AC-12.1 (part), 12.2 (rail) | 1.5 | 0.5 | done 2026-10-05 (five sections via one helper `railSection(id, title, kids)` = `C.group` + `classList.add("ct-panel")`, ids `ag.budget|plan|todos|files|queued` once each; P-11 x2; deviation: `ct-panel` literal count in `agents.js` is 3 not >=5, because the class is added in the one helper, not five literals; actual effort not measured, agent run) | none; after 07 |

**T-037-06 Agents list | main**
- Covers: FR-6; AC-6.1, 6.2; AC-5.6 and 6.3 are [BROWSER] (T-037-20). Split because: first consumer, proves the API on an existing collapse (`setListShown`).
- May touch: `console/static/agents.js` (`applyShell` ~114, `setListShown` ~130-132, shell build ~1469-1505); `console/static/styles.css` `.appshell` (~839-843) and the existing wide block (~882-894).
- Must NOT touch: the `agents.js` 900 px copies (~112, 1498, 1501; D-2); no second fold flag, `chatListHidden` only (BR-9); the `.appshell.hide-list` rules (~878-886) and the `.ap-rail{grid-column:1}`/`.ap-main{grid-column:2}` pinning; the `<=900px` `.appshell{grid-template-columns:1fr}` (~2006) must keep winning; the `.ct-split`/rail code (T-037-07).
- Builds: handle on `.appshell` (owner `.appshell`, `--sp-list`), min 180, max 480 with transcript >= 320, collapse hook calls `setListShown`, handle not rendered while folded, `.list-reveal` restores and takes focus; `.appshell` consumes `var(--sp-list, clamp(208px,22vw,302px))` inside the wide block only.
- Tests: **P-12** `test_p12_agents_list_collapse_uses_setlistshown_fallback_clamp` (AC-6.1, 6.2); P-8 (generic scan from T-037-02) must stay green with the new consumer.
- Verify: Cmd S, `-k "p12_ or p8_"`.
- Done: `Grep -n "var(--sp-list" console/static/styles.css` hits only inside the `min-width: 901px` block with the clamp fallback; `Grep -c "chatListHidden" console/static/agents.js` equals its count before the task; `git diff -U0 console/static/agents.js` hunks only in the listed regions.

**T-037-07 Agents transcript | rail attach**
- Covers: FR-7; AC-7.1; AC-7.2, 7.3, rail row of 5.6 are [BROWSER]. Split because: a different region (`mountChat`, `.ct-split`) and a hard attach-point risk (the rail is rebuilt per meta event).
- May touch: `agents.js` (`mountChat` ~951-960); `styles.css` `.ct-split` (~938-941: add `position: relative`, CR-27), `.ct-rail` (~960) and a **second** wide block placed right after `.ct-split` (CR-25: the existing wide block at ~882 comes before `.ct-split` and would lose).
- Must NOT touch: `#ctRail` as the handle's parent (append to `.ct-split`); the rail section code (~1165-1224, T-037-08); the `agents.js` 900 px copies; the `<=900px` `.ct-rail > .ct-panel` strip (~2020); T-037-06's list hunks.
- Builds: handle child of `.ct-split` (owner `.ct-split`, `--sp-rail`), default 260 (today's CSS value), min 200, max 520 with transcript >= 320; collapse `railOff` stored in `layout.agents`; a collapsed rail keeps its handle as the restore control (click, Enter, double-click); `.ct-split` consumes `var(--sp-rail, 260px)` in the wide block only.
- Tests: **P-12** `test_p12_rail_handle_appended_to_ct_split_in_mountchat` (AC-7.1).
- Verify: Cmd S, `-k "p12_ or p8_"`.
- Done: `Grep -n "ct-split" console/static/agents.js` shows the append inside `mountChat`; no `ctRail.appendChild(` for the handle; `var(--sp-rail` only inside the wide block.

**T-037-08 Rail sections to `C.group`**
- Covers: FR-12 (rail); AC-12.1 (ids once in `agents.js`; the cross-file check is final in T-037-14), AC-12.2 (rail part). Split because: a different change type (fold conversion, not attach); FR-12 is spread over C5/C6/C8 by design.
- May touch: `agents.js` rail sections (~1165, 1177, 1192, 1205, 1224).
- Must NOT touch: `core.js` (do not export `collapsible`; use the exported `C.group`); no ids derived from titles that carry counts; T-037-07's `mountChat` hunk; the `<=900px` strip rule (~2020).
- Builds: five sections become `C.group(title, kids, {id, open})` with literal ids `ag.budget`, `ag.plan`, `ag.todos`, `ag.files`, `ag.queued`, default open, each node keeping class `ct-panel` (D-12, CR-21).
- Tests: **P-11** `test_p11_rail_sections_c_group_ct_panel` (AC-12.2) and `test_p11_ag_ids_once_in_agents_js` (AC-12.1, partial).
- Verify: Cmd S, `-k "p11_"`.
- Done: five `ag.*` ids each once (`Grep -o '"ag\.[a-z]*"' console/static/agents.js`); `Grep -c "ct-panel" console/static/agents.js` >= 5; `git diff -U0 console/static/core.js` unchanged versus the recorded baseline (CR-29).

### S3 Vault panes and cards (C6)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-09 | Two Vault handles, drag flag around `resize()` | C6 | AC-8.1, 8.2 (8.3, 8.4 browser) | 2 | 1 | done 2026-10-05 (`vault.js` flag `paneDragging` as first statement of `resize()`, `attachSideSplitter`/`attachViewerSplitter`/`detachViewerSplitter`; `styles.css` second wide block after `.vault.has-viewer` with `--sp-side`/`--sp-viewer`, pinned children, `.side-off` fold = stage spans the sidebar track; P-12 x2 + P-8 vault in `test_splitter.py`; Cmd S 1 failed (baseline `.ob-count`) / 47 passed; behaviour only in a scratch node harness, [BROWSER] open; actual effort not measured, agent run) | 05 |
| T-037-10 | Vault card state moves to `panelOpen` (`vault.*` ids) | C6 | AC-12.1 (part), 12.2 (vault) | 1 | 0.5 | done 2026-10-05 (`vault.js` `CARDS` ids `vault.filters|display|forces|navigator`, local `panelMap`/`cardOpen`/`setCardOpen` mirroring `collapsible()` through public `C.prefs` (no public helper exists), `st.openCards` gone; P-11 x2 in `test_splitter.py`; Cmd S 1 failed (baseline `.ob-count`) / 49 passed; behaviour only in a scratch node harness, [BROWSER] open; actual effort not measured, agent run) | none; after 09 |

**T-037-09 Vault handles and drag flag**
- Covers: FR-8; AC-8.1, 8.2; AC-8.3, 8.4 are [BROWSER]. Split because: the canvas-reallocation risk (D-11) is its own review target; separate file (`vault.js`).
- May touch: `console/static/vault.js` (`resize()` ~233, observer ~450-452, wrap ~691); `styles.css` `.vault`/`.has-viewer` (~1585-1591) and a **second** wide block placed right after `.vault.has-viewer` (CR-25: the existing wide block at ~882 comes before them and would lose at equal specificity).
- Must NOT touch: the three `setTimeout(resize, 60)` (~507, 515, 530) and the `ResizeObserver` (D-11); the card code and `st.openCards` (~49, ~522-537; T-037-10); the `<=900px` `:root{--vault-side:218px}` and `.vault.has-viewer{...0}` (~2024-2025) and `<=720px` `.vault` rules (~2041-2044), which must still win (BR-3); handles are appended to `.vault`, never `.vault-stage`.
- Builds: `vault.side` (262, min 200, max 480, stage >= 200, collapse `sideOff`) and `vault.viewer` (400, min 280, max 720, stage >= 200, no collapse, present only with `.has-viewer`), owner `.vault`, `--sp-side`/`--sp-viewer` consumed as `var(--sp-x, <today's value>)` in the wide block only; a module flag set on drag start makes `resize()` return early; on release clear the flag and call `resize()` once (uses the T-037-01 drag start/end hooks). **Pin the children** inside the wide block (`.vault-side{grid-column:1}`, `.vault-stage{grid-column:2}`, `.vault-viewer{grid-column:3}`): `sideOff` hides the sidebar with `display:none` and, as `styles.css:887-891` documents for the Agents list, auto-placement would otherwise slide the stage into the 0-width column (CR-32). Known behaviour (CR-37): `resize()` writes inline px `style.width/height` (`vault.js:244-245`), so while the flag is set the canvas stays at its pre-drag size (clipped or a blank strip) and is crisp again on release; D-11's "stretch via CSS" is not what happens (D-11 amended 2026-10-05, wording only; B-3 wording: "frozen, not stretched, during the drag").
- Tests: **P-12** `test_p12_vault_drag_flag_guards_resize` (AC-8.1), `test_p12_vault_handles_on_vault_not_stage` (AC-8.2).
- Verify: Cmd S, `-k "p12_ or p8_"`.
- Done: `Grep -c "setTimeout(resize, 60)" console/static/vault.js` = 3 (unchanged); the flag test is the first statement in `resize()` (`Grep -n -A3 "function resize" console/static/vault.js`); `var(--sp-side`/`var(--sp-viewer` only in a wide block that comes after the `.vault.has-viewer` rule; the three children are pinned to columns 1/2/3 in the wide block.

**T-037-10 Vault cards to `panelOpen`**
- Covers: FR-12 (vault); AC-12.1 (vault ids), AC-12.2 (`panelOpen` in `vault.js`). Split because: a state migration (`st.openCards` to `panelOpen`) with its own default-closed rule, reviewed separately from the handles.
- May touch: `vault.js` (`st.openCards` ~49, defaults ~34-35, card build/toggle ~522-537).
- Must NOT touch: `core.js`; the `.vault-card` DOM (no `C.panel` swap); T-037-09's flag and handles; no `localStorage`.
- Builds: literal ids `vault.filters`, `vault.display`, `vault.forces`, `vault.navigator`; defaults open except `vault.display` and `vault.forces` (closed); state read at build and written on toggle through `panelOpen`; `st.openCards` removed.
- Tests: **P-11** `test_p11_vault_cards_use_panelopen` (AC-12.2), `test_p11_vault_ids_literal_once` (AC-12.1, partial).
- Verify: Cmd S, `-k "p11_"`.
- Done: `Grep -c "openCards" console/static/vault.js` = 0; four `vault.*` ids each once; `git diff -U0 console/static/core.js` unchanged versus the recorded baseline (CR-29).

### S4 Board lane width (C7)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-11 | `--sp-lane` consumed in the wide block (CSS) | C7 | AC-9.1 (CSS half) | 0.5 | 0.5 | done | 05 |
| T-037-12 | Lane handles in `board.js` (`laneNode`, `paint()`) | C7 | AC-9.1 (JS half) (9.2, 9.3, 2.5 browser) | 2 | 1 | done | 05, 11 |

**T-037-11 Lane width CSS**
- Covers: AC-9.1 (CSS half). Split because: a `styles.css` hunk is reviewed apart from `board.js` (hot shared file vs a file that was clean at planning).
- May touch: `styles.css` `.lanes` (~682), `.lane` (~688-689: add `position: relative` so the trailing-edge handle has a containing block, CR-27), the existing wide block (`.lane` precedes it, so equal specificity resolves in the consumer's favour; `.lane.cold` is more specific and keeps 52 px).
- Must NOT touch: `--lane-w` in `:root` (~78), the 1280 trim (~1983) and 720 bypass (~2056); `.lane.cold` 52 px (~699-702); no `transition` on `grid-template-columns`; the `.sp` block; any `.ob-*` line.
- Builds: `.lane` width reads `var(--sp-lane, var(--lane-w))` inside `@media (min-width: 901px)` only, so users with no stored width keep today's 270 / 252 and the trims.
- Tests: **P-8** (generic scan stays green with the new consumer); **P-12** `test_p12_lane_var_consumed_in_wide_block` (AC-9.1 half).
- Verify: Cmd S, `-k "p12_ or p8_"`.
- Done: `Grep -n "var(--sp-lane" console/static/styles.css` hits only inside the wide block; `Grep -c "\-\-lane-w" console/static/styles.css` equals its count before the task; `.lane` has `position: relative` (`Grep -n -A8 "^\.lane {" console/static/styles.css`).

**T-037-12 Lane handles in `board.js`**
- Covers: FR-9; AC-9.1 (JS half); AC-9.2, 9.3, 2.5 are [BROWSER]. Split because: separate file, and the first consumer where handle host != variable owner (lane vs `.lanes`) with ordinal scaling and a primary flag.
- May touch: `console/static/board.js` `laneNode` (~175-193) and `paint()` lane build (~261-279). Run `git diff -U0 console/static/board.js` first (clean at planning time).
- Must NOT touch: `.lane.cold` (click/Enter expands, ~194-203), so no handle there; `draggable`/`dragstart` on the handle (cards and lanes use HTML5 DnD, ~181-192); the refresh calls (~412-458) and `drawer` calls (~300, 398, 514, 521).
- Builds: a handle on every non-cold lane's trailing edge (host = the lane, owner `.lanes`, `--sp-lane`, min 200, max 480, no collapse); the pointer delta is divided by the lane's ordinal among non-cold lanes; only the first handle is tabbable and carries ARIA values, the rest `aria-hidden` (primary flag); no handle when no non-cold lane exists; a repaint mid-drag ends the drag cleanly and keeps the last valid width (drag end hook, FR-2).
- Tests: **P-12** `test_p12_lane_var_written_on_lanes_handles_non_cold_only` (AC-9.1: owner is `.lanes`, no `draggable` in the added code, cold lane excluded).
- Verify: Cmd S, `-k "p12_"`.
- Done: `git diff -U0 console/static/board.js` shows only hunks in the two listed ranges; `Grep -n "sp-lane" console/static/board.js` hits in `paint()`; added lines contain no `draggable`.

### S5 Overview and Assistant folds (C8)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-13 | Overview: six `ov.*` panels, `foldBar`, Enter guard | C8 | AC-12.1 (part), 12.2 (guard), 13.1 (part) | 2 | 1 | done | 05 |
| T-037-14 | Assistant: three `as.*` panels, `foldBar`; final id and `foldBar` tests | C8 | AC-12.1 (final), 12.3, 13.1 | 1.5 | 0.5 | done | 05, 08, 10, 13 (the 18-id gate reads their ids) |

**T-037-13 Overview folds**
- Covers: FR-12 (ov), FR-13 (ov); AC-12.1 (partial), 12.2 (guard), 13.1 (partial); AC-12.4, 12.5, 13.2 are [BROWSER]. Split because: separate file, and the Enter guard changes a row-navigation handler (D-14).
- May touch: `console/static/overview.js` panels (~194, 244, 259, 295, 334, 355), the Enter handler (~303-317), the first row for `foldBar`.
- Must NOT touch: the Getting-started card (~109-131) and "Open setup" (~122-127), owned by T-020/T-021; `ov.onboarding` keeps `onboardingOpen` (~50, 87-102); the self-removing empty panels (~185, 208); `settings.js` (no `foldBar` there, do not refactor `jumpBar()` ~1926).
- Builds: ids `ov.glance`, `ov.attention`, `ov.flow`, `ov.recent`, `ov.jobs`, `ov.schedules` via `C.panel(..., {collapse})`, default open; `C.splitter.foldBar(host)` as the first row, right-aligned; the Enter handler ignores events whose target is inside the panel `<header>` and returns early while collapsed.
- Tests: **P-11** `test_p11_overview_ids_once_enter_guard` (AC-12.1 partial, 12.2); **P-13** `test_p13_overview_uses_foldbar`.
- Verify: Cmd S, `-k "p11_ or p13_"`.
- Done: `Grep -o '"ov\.[a-z]*"' console/static/overview.js` lists six ids; `git diff -U0 console/static/overview.js` has no hunk in ~109-131; the guard reads the header target and collapsed state inside the handler.

**T-037-14 Assistant folds and final section checks**
- Covers: FR-12 (as), FR-13 (as); AC-12.1 (final), AC-12.3 (evidence), AC-13.1 (no `foldBar` in `settings.js`). Split because: separate file, and it closes the global "each id once, none across files" gate, which is final only after S5 (an independently reviewed check).
- May touch: `console/static/assistant.js` (~149, 164, 167); `test_splitter.py`. Run `git diff -U0 console/static/assistant.js` first.
- Must NOT touch: `settings.js`; other `assistant.js` regions; `core.js`.
- Builds: ids `as.talk`, `as.runs`, `as.tickets` via `C.panel(..., {collapse})`, default open; `foldBar` as the first row.
- Tests: **P-11** `test_p11_all_18_ids_each_once_none_across_files` (AC-12.1 final); **P-13** `test_p13_foldbar_only_overview_assistant_not_settings` (AC-13.1).
- Verify: Cmd S (P-1..P-9, P-11..P-13, P-15).
- Done: the 18-id test green; `git diff -U0 console/static/core.js` unchanged versus the baseline recorded in T-037-01, so no T-037 hunk (AC-12.3; T-036's own hunks may appear, CR-29); `Grep -c "foldBar" console/static/settings.js` = 0.

### S6 Reset layout (C9)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-15 | `layoutPanel()` and one `kids.push` in `settings.js` | C9 | AC-14.1, 14.2, 15.2 (14.3, 15.1 browser) | 1.5 | 0.5 | done | 04; after 14 (result observable on every surface) |

**T-037-15 Reset layout** (single task: one component; slice S6 is one task by design)
- Covers: FR-14, FR-15 (code side); AC-14.1, 14.2, 15.2. Split because: the shared Settings file holds four foreign hunks, and a cross-surface reset is reviewed on its own.
- First step: `git diff -U0 console/static/settings.js` and note the foreign hunks (`identity()` ~1654, "Run setup again" row ~1756-1768, `kids.push(identity())` ~1973, T-031's `assistant()`).
- May touch: `settings.js`: add `layoutPanel()` after `storage()` ends (~1805) and one `kids.push(layoutPanel())` after `kids.push(storage(paint))` (~1974); `test_splitter.py`.
- Must NOT touch: anything inside `storage()` (the "Run setup again" row and the local "Reset all preferences" are T-036/T-020's); `identity()` and its push; `assistant()`; `jumpBar()` (~1926); no `localStorage`, no `C.prefs.reset` (AC-14.2).
- Builds: a Reset layout button that runs three `C.prefs.del` (exactly `layout`, `panelOpen`, `chatListHidden`), then `C.splitter.reapplyAll()`, `ConsoleApp.go(active)` and a toast; theme, `hiddenTabs`, `onboardingOpen` untouched (D-15). The panel is `C.panel(..., {collapse: {id: "set.layout", open: false}})` like the 11 other Settings panels (`settings.js:90-1908`), so `jumpBar()` (`:1926-1951`) lists it with no change; `set.layout` is not one of the 18 FR-12 ids (CR-33). Reset also clears the `set.*` fold states because it deletes all of `panelOpen`: accepted by D-15.
- Tests: **P-14** `test_p14_layoutpanel_one_function_one_push` (AC-14.1; also `"set.layout"` once), `test_p14_reset_three_prefs_del_no_localstorage_no_prefs_reset` (AC-14.2, 15.2: also scans `splitter.js`).
- Verify: Cmd S, `-k "p14_"`.
- Done: `git diff -U0 console/static/settings.js` shows exactly two T-037 hunks (the function, the push) and the foreign hunks recorded at the start are byte-identical; P-14 green.

### S7 Docked ticket panel (C10, last: it changes page structure)

Q1 is open; these tasks build the accepted default (D-1). Everything is behind `dockMode()`.

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-16 | Dock mode switch and `#app` layout | C10 | AC-10.2 (10.1 kept) (10.3, 10.4, 11.5 browser) | 2 | 1 | done (S7a) | 05; after 15 |
| T-037-17 | Dock left-edge handle and `dock.w` width | C10 | FR-5 `dock.w` row (10.6, 5.6, 1.6 browser) | 1.5 | 0.5 | done (S7a) | 16 |
| T-037-18 | Dock focus, Esc, in-place refresh, print line | C10 | AC-10.1, 11.1, 11.2 (11.3, 11.4, 11.6 browser) | 2 | 1 | done (S7b) | 16; after 17 |
| T-037-19 | Dock tests (P-10, dock rows of P-8) | C10, C11 | AC-10.1, 10.2, 11.1, 11.2, 5.3, 5.4 | 1.5 | 0.5 | done (S7b) | 16, 17, 18 |

**T-037-16 Dock mode switch and layout**
- Covers: FR-10 (structure), FR-11 (live mode switch, no scrim); AC-10.2; the exported shape of AC-10.1 stays. Split because: a structural change to the `#app` grid, the riskiest piece, reviewed on its own.
- May touch: `console/static/app.js` drawer IIFE only (~14-53); `styles.css` one dock block after `.drawer .dbody` (~1691), inside `@media (min-width: 901px)`: `#app.has-dock{grid-template-columns:minmax(0,1fr) var(--sp-dock,430px)}`, `#app.has-dock > .topbar{grid-column:1/-1}`, `#app.has-dock > .drawer{position:relative;grid-column:2;grid-row:2;width:auto;min-width:0;min-height:0;z-index:auto;box-shadow:none;animation:none}` (`relative`, not `static`: the handle is an absolutely positioned child and needs the aside as its containing block; the inherited `top/right/bottom: 0` are zero offsets, so nothing shifts; CR-27). Placement was traced against the grid auto-placement algorithm: the aside (explicit row and column) is placed first, the topbar takes row 1 across both columns, `main#view` falls into row 2 column 1, so no explicit pin on `main#view` is needed.
- Must NOT touch: `app.js` boot `.then` (~346), `setTitle` (~371-381), export (~382-384) (the `{open, close}` export is unchanged, so no export edit), and the heartbeat `watchConnection` (~266-276, T-036 will edit it); `index.html` (nothing beyond T-037-05); `board.js`; the print block and line ~2129; any `.ob-*` line. `go()` keeps closing the dock (~128).
- Builds: one `dockMode()` = `window.matchMedia(C.splitter.WIDE).matches`; `open()` appends the same `aside.drawer` to `document.getElementById("app")` and sets `has-dock` when docked (no scrim, `role="complementary"`), else `document.body` with scrim and today's role; `close()` removes the aside and `has-dock`; one install-once wide-query `change` listener moves the same node with `appendChild` on a live switch, flips the role, and saves and restores `document.activeElement` (a move blurs focus).
- Tests: none here (T-037-19).
- Verify: Cmd S; `Grep` checks below.
- Done: `Grep -c "function dockMode" console/static/app.js` = 1 and `Grep "C.splitter.WIDE" console/static/app.js` hits; `git diff -U0 console/static/app.js` has hunks only in the drawer IIFE region and none at the foreign sites (~266-276 heartbeat, ~346, ~371-384); `var(--sp-dock` only inside the wide block; the docked aside is `position: relative`, never `static` (CR-27); `git diff -U0 console/static/index.html` shows only the T-037-05 line. Run S7a ends after T-037-17 (Greps + Test command S not worse than baseline; the P-10 tests arrive in S7b by design, CR-43).

**T-037-17 Dock handle and width**
- Covers: FR-10 (width), `dock.w` row of FR-5; AC-10.6, 5.6 (dock row), 1.6 are [BROWSER]. Split because: it consumes the C1 contract at its hardest shape (host = aside, owner = `#app`) plus the registry reset.
- May touch: `app.js` drawer IIFE; the T-037-16 dock block in `styles.css`.
- Must NOT touch: `splitter.js` (if the API cannot express host != owner, stop and report to the planner/`evolve`, do not patch ad hoc); the T-037-16 foreign-hunk list; print.
- Builds: a left-edge handle as a child of the aside straddling its border (host aside, owner `#app`, `--sp-dock` written on `#app`, key `dock.w`, default 430, min 320, max 720 with `main#view` >= 360, no collapse), created through `C.splitter(` so the registry's `reapplyAll()` (Reset layout) reverts it. That revert can never be observed (Reset lives on Settings and `go()` closes the dock, D-18; `open()` reads `dock.w` anyway), so it is kept by construction and costs no QC time (CR-38).
- Tests: none here (T-037-19).
- Verify: Cmd S; `Grep` checks below.
- Done: `--sp-dock` is written on `#app` and consumed as `var(--sp-dock, 430px)` only in the wide block; the handle is appended to the aside, not to `main#view`; `git diff -U0 console/static/app.js` stays within the drawer IIFE.

**T-037-18 Dock focus, Esc, refresh, print**
- Covers: FR-11; AC-10.1 (`board.js` stays the one opener), 11.1, 11.2; AC-10.5, 11.3, 11.4, 11.6 are [BROWSER]. Split because: behaviour semantics (focus, Esc, refresh) are reviewed apart from structure, and the print edit touches a shared block.
- May touch: `app.js` drawer IIFE; `styles.css` one new line `#app.has-dock{grid-template-columns:minmax(0,1fr)}` inside the existing `@media print` block after the `.panel{...}` line (~2131). Fallback only if that block shows a collision: a separate `@media print` block beside the dock rules.
- Must NOT touch: the `.drawer{display:none !important}` line (~2129) and its `.ob-scrim` edit (another ticket); `board.js` (the opener ~300 and the five refresh calls ~412, 416, 419, 420, 458); the three foreign `app.js` sites.
- Builds: initial focus on Close and restore to the opener (docked path included); Esc closes a docked panel only when the target is inside it, modal unchanged (an Esc in a field still reverts and closes, D-10); tab switch, `r` and refresh close it (existing `go()`); a repeat `open()` keeps the panel element, width and restore target, updates title/subtitle, swaps in a NEW `.dbody` and returns it, with no `slidein` replay (D-9); document-level listeners installed once.
- Tests: none here (T-037-19).
- Verify: Cmd S; `Grep` checks below.
- Done: `Grep -c "drawer.open(" console/static/board.js` = 1 and 0 in every other JS file; the print line appears once, after `.panel{`; `git diff -U0 console/static/styles.css` shows no T-037 hunk on the `:2129` line.

**T-037-19 Dock tests**
- Covers: AC-10.1, 10.2, 11.1, 11.2; dock rows of AC-5.3, 5.4. Split because: an independent test closure of the riskiest slice; a failing test goes back to the owner of T-037-16..18, not fixed here.
- May touch: `console/tests/test_splitter.py` only. Must NOT touch: any code.
- Tests: **P-10** `test_p10_drawer_export_shape_single_opener` (AC-10.1), `test_p10_dockmode_single_uses_wide_roles_flip` (AC-10.2), `test_p10_repeat_open_fresh_dbody_listeners_once` (AC-11.1: a structural proxy only, the `class: "dbody"` element is created inside `open()` outside any `if (panel)`-guarded branch and swapped in, the drawer IIFE is cut out by the `var drawer = (function` anchor, never by line number; the real proof is B-6), `test_p10_every_print_block_covers_dock` (AC-11.2: scans every `@media print` block), `test_p10_dock_handle_goes_through_splitter_registry`; **P-8** `test_p8_dock_vars_in_wide_block_no_grid_transition` (AC-5.3, 5.4 for `--sp-dock`, including `min-width: 0; min-height: 0` in the dock block).
- Verify: Cmd S, then `-k "p10_ or p8_"`. S7 checkpoint: `git diff --stat` shows `app.js`, `styles.css`, `test_splitter.py` (plus earlier slices) and no T-037 change to `core.js` (versus the baseline, CR-29).
- Done: all P ids green; failing ids are a subset of the baseline.

### V Verification handoff (owner: verifier)

| Task ID | Description | Component | Requirement/AC | Dev h | QC h | Status | Depends on |
|---|---|---|---|--:|--:|---|---|
| T-037-20 | Full-suite run, [BROWSER] checklist B-1..B-13, evidence diffs | C11, all | all [BROWSER] ACs; AC-12.3 evidence; AC-15.1 open | 0 | 2 | pending | 19 |

**T-037-20 Verification handoff**
- Covers: every [BROWSER] AC (map in § AC coverage), AC-12.3 and AC-15.1 evidence. Split because: a different owner (`verifier`), and the browser checks cannot be run by any agent here; the parent session runs them.
- May touch: `T-037-verification.md` (verifier's own artifact). Must NOT touch: any code, any `*.toml`; never mark a [BROWSER] AC done.
- Does: (1) run the full suite once, `pytest -o addopts="" console/tests` (~450 s); baseline 1 failed / 2273 passed, the failure is `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count`; compare by failing test **id** (the passed count rises by the number of new tests); (2) write the [BROWSER] checklist B-1..B-13, each labelled "not verified in a browser"; (3) evidence (AC-12.3, versus the baseline recorded in `T-037-progress.md` by T-037-01, never "diff empty"): no T-037 hunk in `core.js` (T-036's own hunks may be there), and other tickets' hunks intact (`app.js` ~346, ~371-384, plus T-036's ~266-276; `index.html` ~72; `overview.js` ~122-127; `settings.js` four hunks; `styles.css` `.ob-*` block and `:2129`); (4) record AC-15.1 as open until T-036 lands. The verifier owns the AC-12.3 evidence at close (T-037-14 pre-checks it).
- Checklist gaps found while mapping (the draft's B matrix does not name them): AC-4.4 (stored 2000 px at ~1000 px) is added to B-13; AC-5.6 (each row drags to its min and max) is added as a min/max leg to B-1..B-5.
- Verify: the suite command above. Done: `T-037-verification.md` lists B-1..B-13 each "not verified in a browser"; failing ids recorded and compared; `core.js` unchanged by T-037 versus the baseline.

## AC coverage

65 ACs (AC-1.1 .. AC-15.2): 30 [PY], 1 evidence-only (AC-12.3), 34 [BROWSER]. Result: **every AC maps to at least one task; none are uncovered.** [PY] ACs map to implementing tasks and the task whose test checks them; every [BROWSER] AC maps to T-037-20 only (never marked done by a build task).

**[PY] and evidence ACs**

| AC | Implemented by | Checked by (test, task) |
|---|---|---|
| 1.1 | 05 | P-1, 05 |
| 1.2 | 03 | P-3, 03 |
| 1.3, 1.4 | 02 | P-7, 02 (1.3 also `test_stylesheet.py`) |
| 1.5 | 03 | P-2, 03 |
| 2.1, 2.2 | 03 | P-4, 03 |
| 3.1 | 03 | P-3, 03 |
| 4.1 | 03 | P-5, 03 |
| 4.2 | 04 | P-6, 04 |
| 5.1 | 02 | P-7, 02 |
| 5.2 | 03 | P-9, 03 |
| 5.3 | 02 (CSS), 03 (JS); consumers 06, 07, 09, 11, 16, 17 | P-8 (02, grows), P-9 (03), dock rows (19) |
| 5.4 | 02; dock 16 | P-8, 02 and 19 |
| 6.1, 6.2 | 06 | P-12, 06 |
| 7.1 | 07 | P-12, 07 |
| 8.1, 8.2 | 09 | P-12, 09 |
| 9.1 | 11 (CSS), 12 (JS) | P-12, 11 and 12 |
| 10.1 | 16, 18 | P-10, 19 |
| 10.2 | 16 | P-10, 19 |
| 11.1 | 18 | P-10, 19 |
| 11.2 | 18 | P-10, 19 |
| 12.1 | 08, 10, 13, 14 | P-11, 08/10/13; final 14 |
| 12.2 | 08 (rail), 10 (vault), 13 (guard) | P-11, 08/10/13 |
| 12.3 (evidence) | all (no `core.js` edit) | `git diff --stat console/static/core.js`, 14 and 20 |
| 13.1 | 04 (`foldBar`), 13, 14 | P-13, 04/13/14 |
| 14.1, 14.2 | 15 | P-14, 15 |
| 15.2 | 04 (`reapplyAll`), 15 (no `C.prefs.reset`) | P-6 (04), P-14 (15) |

**[BROWSER] ACs, all verified only by T-037-20 (B ids from the draft § 15; "not verified in a browser")**

| AC | Check | AC | Check |
|---|---|---|---|
| 1.6 | B-1 (fine), B-9 (coarse) | 9.2, 9.3 | B-4 |
| 2.3 | B-3 | 10.3 | B-5 |
| 2.4 | B-9 | 10.4 | B-8 |
| 2.5 | B-4 | 10.5, 10.6 | B-5 |
| 2.6 | B-10 | 11.3, 11.4, 11.5, 11.6 | B-6 |
| 3.2, 3.3, 3.4 | B-1 (3.4 also B-2) | 12.4, 12.5 | B-11 |
| 4.3 | B-1 | 12.6 | B-8 |
| 4.4 | B-13 (**added**, not in the draft matrix) | 13.2 | B-11 |
| 4.5 | B-13 | 14.3 | B-12 |
| 5.5 | B-7 | 15.1 | B-12, open until T-036 lands |
| 5.6 | B-1..B-5 min/max leg (**added**) | 6.3 | B-1 |
| 7.2, 7.3 | B-2 (7.3 at ~800 also B-7) | 8.3, 8.4 | B-3 |

User stories: US-1 (01-05), US-2 (03), US-3 (03, 04), US-4 (02, 03, 06, 07, 09, 11, 16, 17, 19), US-5 (06-08), US-6 (09, 10), US-7 (11, 12), US-8 (16-19), US-9 (04, 08, 10, 13, 14), US-10 (15); T-037-20 verifies every story's [BROWSER] ACs.

## Dependency and ordering summary

"Depends on" in the tables lists the **hard** edges; `after N` is a build-order predecessor only. Build order is the task number (one sequential builder, one shared tree, `styles.css` shared by all slices). **This section is the single source for edges** (CR-26); [[T-037-plan]] § Tasks and [[T-037-components]] § Dependency graph repeat it.

```
S1: 01 design -> 02 C2 CSS -> 03 C1 core -> 04 C1 registry/foldBar -> 05 C3 tag
S2: 06 list -> 07 rail attach -> 08 rail folds        (agents.js, styles.css ~839-964)
S3: 09 vault handles -> 10 vault folds                (vault.js)
S4: 11 lane CSS -> 12 board.js handles                (styles.css, then board.js)
S5: 13 overview -> 14 assistant + final id gate        (overview.js, assistant.js)
S6: 15 reset layout                                    (settings.js; hard on 04, build-ordered after 14)
S7: 16 dock mode -> 17 handle/width -> 18 focus/Esc/refresh/print -> 19 tests
V : 20 verification handoff (verifier; parent session runs [BROWSER])
```

- **Hard edges (resolved):** 02 on 01; 03 on 01, 02; 04 on 03; 05 on 04; 06, 07, 09, 11, 13 on 05 (conservative for 11, a CSS-only line); 12 on 05, 11; 14 on 05, 08, 10, 13 (the 18-id gate reads their ids); 15 on 04 (`reapplyAll` must exist); 16 on 05; 17 on 16; 18 on 16; 19 on 16, 17, 18; 20 on 19; 08 and 10 have none (they use only the exported `C.group` and `panelOpen`).
- **Build-order-only edges:** 07 after 06, 08 after 07, 10 after 09 (same file, adjacent hunks); 15 after 14 (the reset is then observable on every surface); 16 after 15; 18 after 17 (same IIFE). The old "soft edge 17/19 to 15" (Reset reverts `dock.w`) is dropped as a reason: it cannot be observed (CR-38).
- **Acyclic, never blocked at its turn:** every hard edge points to a lower task number and the build order is the task number, so each task's hard predecessors are done when it starts. Only a stop inside T-037-17 (C1 cannot express host != owner) can block, and T-037-01 and T-037-03's option-name Grep exist to retire that early (CR-34).
- **Critical path:** 01 > 02 > 03 > 04 > 05 > S2..S6 > 16 > 17 > 18 > 19 > 20. The tasks are sequential in practice, so the Dev critical path equals total Dev (31.5 h). Heaviest tasks: 03 and 02 (3 h Dev each), then 04, 09, 13, 16, 18 (2 h each). The hard-edge-only chain is 01, 02, 03, 04, 05, 16, 18, 19, 20 (9 tasks). Logical parallelism exists (agents.js, vault.js, board.js, overview.js are disjoint files) but is not used: shared tree, concurrent T-031/T-036 edits.
- **Why S7 is last:** it changes page structure (`#app` grid); everything else should be stable first. **Why S1 is three runs and S7 two:** see Conventions (runs <= 6 h; S1a 5.0, S1b 4.0, S1c 4.0; S7a 5.0, S7b 5.0). **Why S6 has one task:** one component, no qualifying split.
- Slice checkpoints (each ends with Cmd S, failing ids compared to the baseline, then `git diff --stat`): S1 P-1..P-9 · S2 P-8, P-11 (rail), P-12 · S3 P-11 (vault), P-12 · S4 P-8, P-12 · S5 P-11 final, P-13 · S6 P-14 · S7 P-8, P-10. Run exits inside S1 and S7: S1a = contract + P-7, P-8 · S1b = P-2..P-5, P-9 + option-name Grep · S1c = P-1..P-9 + P-13 · S7a = Greps + Test command S · S7b = P-10 green.

## Estimate (mode=upfront)

**Basis:** components (11 components, decomposed into 20 task units); **confidence:** Medium; cone 0.8x to 1.3x of most-likely (reforecast with `estimate(mode=forecast)` once tasks have actuals). Human-equivalent hours, not agent wall-clock. Layer: UI (frontend only) plus test-authoring inside each task. Not written as a separate `T-037-effort-estimate.md`: the caller asked for this file only, and the plan's Effort table (part B2) takes these totals.

**Per-task basis** (Dev = build + the task's own pytest group; QC = run the slice checks, compare failing ids, `git diff` foreign-hunk review, read the change against its ACs)

| Task | Dev | QC | Basis |
|---|--:|--:|---|
| 01 | 1.0 | 0.5 | one ~40-60 line contract; paper walk-through of six rows |
| 02 | 3.0 | 0.5 | ~60-line CSS block + a print block in the hot file, five test helpers (two are new: `_func_body`, `_depth_at`) and the P-7 and three P-8 tests (was 2.0: +1.0 after CR-30, CR-31, CR-35, CR-36; the cap bucket) |
| 03 | 3.0 | 1.0 | ~200 lines ES5 (pointer, keys, ARIA, persistence) + five test groups; the cap bucket |
| 04 | 2.0 | 1.0 | registry, install-once listeners, `reapplyAll`, `foldBar` + two tests; concurrency-flavoured |
| 05 | 0.5 | 0.5 | one HTML line + one test; QC runs the S1 checkpoint |
| 06 | 1.5 | 0.5 | one attach + CSS fallback on an existing collapse |
| 07 | 1.5 | 0.5 | attach in `mountChat`; rebuild-per-event pitfall |
| 08 | 1.5 | 0.5 | five section conversions + ids + class kept |
| 09 | 2.0 | 1.0 | two handles + drag flag around canvas `resize()`; reallocation risk |
| 10 | 1.0 | 0.5 | state migration of four cards |
| 11 | 0.5 | 0.5 | one CSS consumer line |
| 12 | 2.0 | 1.0 | ordinal scaling, primary flag, repaint safety in a DnD file |
| 13 | 2.0 | 1.0 | six panels + `foldBar` + Enter guard on a live handler |
| 14 | 1.5 | 0.5 | three panels + `foldBar` + the final 18-id gate |
| 15 | 1.5 | 0.5 | one function + one push; foreign-hunk discipline |
| 16 | 2.0 | 1.0 | `#app` grid mode, role flip, live switch with focus save/restore |
| 17 | 1.5 | 0.5 | host != owner handle, clamp against `main#view` |
| 18 | 2.0 | 1.0 | focus, Esc, in-place refresh, print line |
| 19 | 1.5 | 0.5 | five test groups + one P-8 dock group |
| 20 | 0.0 | 2.0 | ~450 s suite run, id comparison, checklist B-1..B-13, evidence diffs (verifier; no dev) |

**Effort summary** (the Effort table of `T-037-plan.md` copies these rows)

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

Builder runs (CR-28), same hours: S1a 01-02 = 1.5 + 3.5 = 5.0; S1b 03 = 4.0; S1c 04-05 = 3.0 + 1.0 = 4.0 (13.0); S2 6.0; S3 4.5; S4 4.0; S5 5.0; S6 2.0; S7a 16-17 = 3.0 + 2.0 = 5.0; S7b 18-19 = 3.0 + 2.0 = 5.0 (10.0); V 2.0. Sum 13.0 + 6.0 + 4.5 + 4.0 + 5.0 + 2.0 + 10.0 + 2.0 = 46.5.

**Totals and range (components basis, cone 0.8x-1.3x)**

| Component | Most likely | Lower | Upper |
|---|--:|--:|--:|
| Development | 31.5 | 25.2 | 40.95 |
| QC | 15.0 | 12.0 | 19.5 |
| Risk reserve (+10% on Dev + QC, components basis) | 4.65 | n/a | n/a |
| **Final / Complete** | **51.15** (about 6.4 d at 8 h, indicative, no delivery date) | **37.2** (Dev + QC lower) | **60.45** (Dev + QC upper) |

Dev + QC without reserve: 46.5 h (was 45.5 before `challenge-plan`; the +1.0 h is T-037-02 Dev, CR-36). The upper bound includes no reserve, as in the skill.

**Cross-checks and caveats (BE HONEST)**
- Skill formula for QC (UI ratio 35% x 31.5 = 11.0 h, x1.5 cycle = 16.5 h, + 4 h UAT for 17-40 h Dev) gives about 20.5 h; the bottom-up QC above is 15.0 h. The gap (about 5.5 h) is the [BROWSER] matrix B-1..B-13 and UAT, which the **parent session** runs and which no task here includes. Indicative 3-4 h for B-1..B-13; it is not in the sums above. Rework after that matrix is not in the totals either, and the +10% reserve is thin for pointer and focus code no agent can exercise here (CR-42).
- No `effort-estimate.md` upper bound exists to compare against (none written), so the "task totals >10% over upper bound" check is vacuous; re-run `estimate(mode=forecast)` after the first slices have actuals.
- Q1 is open (non-blocking, default accepted): no widening applied. If the user picks opt-in, the follow-up is one expression in `dockMode()` plus one Settings toggle row (D-1), about 1 h Dev + 0.5 h QC, not in the totals.
- Largest uncertainty: C1's API fit for the dock and lane (T-037-01 exists to retire it), Vault canvas behaviour (T-037-09) and the browser-only behaviours (focus on the live mode switch, drag across the canvas), none of which can be exercised by an agent here.
- Hours are estimates, not actuals; nothing has been built.

## Links
- [[T-037-summary]] · [[T-037-requirements]] · [[T-037-user-stories]] · [[T-037-decision-log]] · [[T-037-components]] · [[T-037-plan]] · [[T-037-task-breakdown]] · [[T-037-implementation-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
