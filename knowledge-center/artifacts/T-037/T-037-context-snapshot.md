---
ticket: "T-037"
artifact: context-snapshot
status: draft
created: "2026-10-05"
last_updated: "2026-10-05"
scope: codebase + history
---

# Context Snapshot: T-037

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-037 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

A VS Code-like, more responsive console: draggable pane borders on Agents, Vault, a docked resizable ticket panel and board lane width; expandable sections on Overview, Assistant home, the Agents right rail and Vault sidebar cards; sizes and fold state persisted; a Reset layout control ([[T-037-summary]], user decisions 2026-10-05).

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Collapsible panel / group, persisted open state | `C.panel(..., {collapse:{id,open}})`, `C.group(..., {id,open})` | core.js helper, `panelOpen` pref, `.panel.collapsed`/`.group.collapsed` CSS | Reuse as is for Overview, Assistant, Agents rail; `_setOpen` and `data-panel-id` already exposed | `core.js:204-221,259-317`, `styles.css:504-556` |
| Settings jump bar with Collapse all / Expand all | `jumpBar(host)` | settings.js only, `.secnav` CSS | Pattern to copy; not exported, so a shared helper is needed | `settings.js:1926-1951`, `styles.css:597-607` |
| Foldable Agents chat list | `setListShown`, `applyShell`, `.hide-list`, `.show-main`, `.list-reveal` | agents.js state + 2 pref reads + CSS | The collapse half of the Agents list splitter; one state, do not add a second | `agents.js:101-134,1469-1505`, `styles.css:860-894` |
| Vault card fold (in memory) | `card(def, body)` | vault.js `st.openCards` | Move to the shared `panelOpen` map with `vault.*` ids | `vault.js:32-37,49,522-537` |
| Vault CSS-variable pane widths | `--vault-side`, `--vault-viewer`, `.has-viewer` | CSS only | The model for a variable-driven splitter | `styles.css:1576-1591` |
| Ticket drawer | `drawer.open(title, subtitle)` returns `.dbody` | app.js, `.drawer`/`.scrim` CSS | The API to keep; see caller table below | `app.js:14-53`, `styles.css:1672-1691` |
| Breakpoint crossing handler | `st.mql.onchange` | agents.js | Pattern for re-clamping / mode switch at 900 px | `agents.js:1496-1505` |
| Window-edge handling (frameless) | `startDragging` on `.brandrow` only | desktop-chrome.js | Confirms splitters in `#view` never start a window drag | `desktop-chrome.js:74-85`, `main.rs:221-237` |

### Drawer caller table (`ConsoleApp.drawer`)
| # | file:line | Call | Content | Relies on |
|---|---|---|---|---|
| 1 | `board.js:300` | `drawer.open(id, "")` in `openTicket(id)` | title = ticket id, no subtitle; body filled by `C.load` of `GET /api/ticket/{id}` then `paintTicket` | initial focus on Close (`app.js:48`), focus restore to the card (`:25`), Esc (`:28`), scrim click (`:33`) |
| 1a | `board.js:111,112` | card click / Enter / Space call `openTicket` | | |
| 1b | `board.js:412,416,419,420,458` | `openTicket(t.id)` re-called as a refresh after edits | | close+open each time, `slidein` replays (`styles.css:1684`) |
| 2 | `board.js:398` | `drawer.close()` after a stage move, then `reload()` | | |
| 3 | `board.js:514` | `drawer.close()` in `goHome()` then `go("assistant")` | | `go()` closes anyway (`app.js:128`) |
| 4 | `board.js:521` | `drawer.close()` in `fallbackCompose()` then `go("agents")` | | |
| 5 | `app.js:128` | `go()` closes the drawer on every navigation, also `r` key and refresh button | | |
| 6 | `app.js:150` | `drawer` passed to every tab as `api.drawer` | no tab reads it (grep of `static/*.js`) | |
| 7 | `palette.js:103` | `app.drawer(label, [pre.code JSON])` | verb result | **broken**: calls the `{open,close}` object as a function (`app.js:52,382`) |

Docked panel, what must be **preserved** (current contract): `open(title, subtitle)` returns the body node; `close()`; one panel at a time (`open` calls `close` first, `app.js:31`); Esc; initial focus plus restore; closes on tab switch; `<=900px` modal with scrim (full width at `<=720px`, `styles.css:2058`); hidden in print (`styles.css:2129`). What **changes**: no scrim and not modal on wide screens, in-flow width taken from `main#view`, a left-edge splitter with persisted width, in-place refresh instead of close+open, panel below the topbar instead of over it.

### Existing patterns to reuse
- One localStorage object per concern, flat map keyed by stable id — `core.js:254-258`.
- Stable id prefixes by surface: `set.*`, `set.assistant.*` — `settings.js:90-1908`.
- `hidden` attribute is honoured globally — `styles.css:249`.
- `min-width:0` / `min-height:0` on every nested grid/flex child — `styles.css:275-280,834-837`.
- Variables consumed inside the existing grid rule rather than inline `grid-template-columns` — `styles.css:1585-1591`.
- Python source-regexp tests for static assets — `console/tests/test_stylesheet.py`, `console/tests/test_plugins.py:227-260`.

### Naming and architectural conventions in play
- Each tab is a self-registering IIFE `(function (C) { "use strict"; ... })(window.Console);` with `C.tab(id, {layout, render, onLeave})` — `core.js:18-24`, `app.js:1-8`; tabs with `layout:"app"`: board, agents, vault (`board.js:553`, `agents.js:1601`, `vault.js:735`).
- `C.el(tag, attrs, children)` only; no innerHTML templates — `core.js:161-175`.
- CSS file order: tokens, base, layout, components, motion, responsive — `styles.css:1-10`; the `<=900px` block is the structural cliff — `styles.css:1994-2034`.

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-016 | Assistant as home, "Start agent" delegate path from the board drawer | Complete 2026-10-05 | The drawer's only content producer (`board.js:508-548`) came from here; keep it working |
| T-036 | Server-side prefs, UI version reload | Open, GROUND/plan written; `core.js` not yet changed | Contract for `layout` in [[T-036-decision-log]] `t037-layout-contract`; accepted risk: pixel `layout` shared across different window sizes |
| T-031 | Voice assets and devices (model manager) | Open, CANONICAL | Edits `settings.js` `assistant()` and appends to `styles.css`; no `app.js`/`index.html` edits ([[T-031-plan]] line 15, 40) |
| T-020 / T-021 | Onboarding wizard | Uncommitted | Source of the dirty hunks listed in the analysis; also the red `.ob-count` test |
| T-030 | One chat surface | Placeholder only (empty summary) | Nothing to reuse |

### Relevant commits / PRs
- `f8ffbc2` 2026-08-29 "Two kinds of agent, inline / @ # references, and a foldable chat list" — introduced `chatListHidden` (`git log -S`).
- `d005711` 2026-08-24 "Version 02 (#1)" — introduced `has-viewer` in `styles.css` (`git log -S`).
- `50df58b` 2026-09-11 "Make Settings a page you can read, and say what will answer you" — introduced `collapsible` in `core.js` (`git log -S`).
- HEAD `4338cb1` on `development`; `core.js`, `agents.js`, `vault.js`, `board.js`, `assistant.js` clean in the working tree at snapshot time.

### Known incidents / regressions in this area
- Chromium transition on `grid-template-columns` left the viewer track pinned at 0 (comment only, no date/ticket) — `styles.css:1581-1584`.
- `.ct-bar` defined twice clipped composer controls; origin of the duplicate-class test — `console/tests/test_stylesheet.py:9-13`.
- A missing `[hidden]` rule made `.fpick-panel` impossible to close — `styles.css:242-248`.
- Missing `min-width:0` on the topbar clipped tabs on phones — `styles.css:275-280`.

## 4. External Systems in the Loop

- **Tauri desktop webview** — frameless window (`decorations(false)` on non-macOS, `main.rs:236`), 1280x800 default, `min_inner_size(800,500)` (`:223-224`); `html.in-shell` injected by the host (`main.rs:119,123`). Pointer-capture behaviour in WebView2/WKWebView/WebKitGTK not verified.
- **Static export** (`console/server/export.py:87-90` globs `*.js`/`*.css`/`*.html`): a new `splitter.js` ships automatically; prefs fall back to local mode there ([[T-036-decision-log]] `prefs-client-contract`).
- **T-036 prefs store** — interface dependency only.

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- **Inline variable beats media query** — a size written on `<html>` overrides the `:root` trims at `styles.css:1983,2024` at every width; true for `--lane-w`, `--vault-side`. Bites if sizes are applied globally instead of per container.
- **Stored px vs shared prefs across window sizes** — after T-036 the app (min 800 px) and a browser share `layout` ([[T-036-decision-log]] `scope-boundaries` risk 2). Bites if a stored width is applied unclamped.
- **Small centre pane** — at 901 px with the viewer open the Vault stage is 901-262-400 = 239 px; Agents transcript at 901 px is 901-208-260 = 433 px (computed from `styles.css:841,940,1577-1578`).
- **Vault redraw per frame** — `resize()` reallocates both canvases per observer callback (`vault.js:233-252`).
- **Enter on a collapse header navigates** — `overview.js:303-317` (finding N2).
- **Merge collisions** in `settings.js` (T-031, T-036, onboarding all edit it) and `styles.css` (T-031 appends a block; onboarding `.ob-*` at the end).
- **Dock vs print** — `.drawer`/`.scrim` are listed in the print rule (`styles.css:2129`); a docked panel needs the same treatment.
- **Coarse pointers** — splitters on tablets `>=901px` need a larger hit area; existing convention is 30-34 px targets (`styles.css:2097-2113`).
- **Test baseline red** from another ticket (`.ob-count`), so a "suite green" claim is impossible until that lands.

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. Convert to open questions via `clarify` if any would change the draft.

- Drag, capture, clamping, focus ring and cursor behaviour in a real browser at ~400, ~800, ~1400 px — **[BROWSER] not verified**; no browser tool available.
- Pointer capture and `touch-action:none` inside the Tauri webview on Windows, macOS and Linux — **[BROWSER] not verified**.
- `palette.js:103` failure mode (TypeError then toast) — by reading `app.js:52,382` only; not executed.
- Computed overflow numbers for the docked board (N7 in the analysis) — arithmetic from CSS values, not measured.
- Whether Tauri's HTML5 drag-and-drop interception applies to this app — from Tauri documentation, not checked in `main.rs` runtime.
- T-036's actual `core.js` implementation — only its decision log was read; `core.js` is unmodified so far.
- Q1 in `T-037-questions.toml` (dock replaces overlay on wide screens) is open.

### Proposed stable section ids (for `requirements draft`, not decided)

| Surface | Section | Where today | Proposed id | Notes |
|---|---|---|---|---|
| Overview | Getting started / Setup complete | `overview.js:109-131` | `ov.onboarding` | already folds (`onboardingOpen`, `:50,87-102`); default: leave out |
| Overview | At a glance | `overview.js:259` | `ov.glance` | |
| Overview | Needs attention | `overview.js:295` | `ov.attention` | needs key-handler guard (`:303-317`) |
| Overview | Flow | `overview.js:334` | `ov.flow` | |
| Overview | Recently touched | `overview.js:355` | `ov.recent` | |
| Overview | Jobs | `overview.js:194` | `ov.jobs` | async, removes itself when empty |
| Overview | Scheduled | `overview.js:244` | `ov.schedules` | async, removes itself when empty |
| Assistant home | Talk | `assistant.js:149` | `as.talk` | |
| Assistant home | Runs | `assistant.js:164` | `as.runs` | |
| Assistant home | Tickets | `assistant.js:167` | `as.tickets` | |
| Agents right rail | Console budget | `agents.js:1165` | `ag.budget` | raw `section.ct-panel`; rebuilt per meta event |
| Agents right rail | Plan | `agents.js:1177` | `ag.plan` | same |
| Agents right rail | Todos | `agents.js:1192` | `ag.todos` | same |
| Agents right rail | Files touched (N) | `agents.js:1205` | `ag.files` | title carries a count, so id must not derive from it |
| Agents right rail | Queued (N) | `agents.js:1224` | `ag.queued` | same |
| Vault sidebar | Filters | `vault.js:33` | `vault.filters` | card state `st.openCards`, in memory |
| Vault sidebar | Display | `vault.js:34` | `vault.display` | |
| Vault sidebar | Forces | `vault.js:35` | `vault.forces` | |
| Vault sidebar | Navigator | `vault.js:36` | `vault.navigator` | `grow` card |

Other `C.panel` sections not in the named scope: Analytics 14 call sites (`analytics.js:90-242`), Work 6 (`work.js:95,135-138,213`), About 1 (`about.js:92`).

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-05 | Bash | `python console/kanban.py context T-037` (PYTHONUTF8=1) | trace-context digest |
| 2026-10-05 | Read | `T-037-summary.md`, `T-037-analysis.md`, `T-037-context-snapshot.md`, `analyze/SKILL.md`, `questions/SKILL.md` | scope, templates, protocol |
| 2026-10-05 | Grep | `console/` for splitter/drag/resize/pointer terms | lead L1 |
| 2026-10-05 | Read | `index.html`, `app.js`, `desktop-chrome.js`, `core.js` (1-130, 130-230, 230-490, 490-766) | script order, drawer, prefs, collapse |
| 2026-10-05 | Read | `styles.css` 1-260, 260-420, 462-560, 600-730, 820-980, 1180-1220, 1350-1380, 1565-1715, 1960-2150 | geometry and media queries |
| 2026-10-05 | Read | `board.js`, `overview.js`, `assistant.js` (full); `vault.js` 1-70, 228-290, 360-750; `agents.js` 30-160, 895-1000, 1140-1270, 1425-1610; `palette.js` 60-150; `settings.js` 1720-1805, 1890-1989 | callers, sections, re-render |
| 2026-10-05 | Grep | `drawer`, `collapse:`/`C.group(`/`.panel(`, `prefs.`, `layout:`, `ct-split|appshell|--vault|lane-w`, `Esc`, `composer-pick|onboarding-wizard|desktop-chrome` | caller and registry sweeps |
| 2026-10-05 | Read | `console/tests/test_stylesheet.py`, `test_plugins.py` 195-285; `console/server/export.py` (grep), `httpd.py` (grep) | test asserts, asset serving |
| 2026-10-05 | Bash | `git status`, `git diff -U0` on `console/static/*`, `git log -S` for `chatListHidden`, `has-viewer`, `collapsible` | conflict map, history |
| 2026-10-05 | Read | `desktop/src-tauri/src/main.rs` 212-250, `tauri.conf.json`; `console/config/boards/tickets.toml` (grep) | window config, lane count |
| 2026-10-05 | Read | `T-036-summary.md`, `T-036-decision-log.md` 34-85, `T-031-summary.md`, `T-031-plan.md`/`requirements.md` (grep) | dependency contracts |
| 2026-10-05 | Bash | `pytest -o addopts=""` on `test_stylesheet.py` + `test_plugins.py`; then full `console/tests` | baseline counts (1 failed, 24 passed; 1 failed, 2273 passed) |
| 2026-10-05 | WebFetch | w3.org APG Window Splitter; MDN `setPointerCapture` | research |
| 2026-10-05 | Bash | `python console/kanban.py tracker add T-037 questions ...` | recorded Q1 |
| 2026-10-05 | Read | `app.js` 1-160, `core.js` 196-320 and 436-466 and 735-767, `styles.css` 236-426, 464-610, 618-636, 660-720, 820-980, 1568-1702, 1960-2160, `agents.js` 96-139, 935-985, 1140-1260, 1455-1515, `board.js` 236-345, `overview.js` 290-360, `vault.js` 28-60, 440-550, `index.html`; Grep `C.panel(`/`collapse:`/`panelOpen`, `z-index`, `setInterval`, `ConsoleApp =` (requirements enrich spot checks) | cite line numbers in the requirements; confirmed `collapsible()` is not exported (`core.js:758`), `.ct-panel`/`.ap-rail` naming, `#app` two-row grid, `.grid` `align-items:start`, `ConsoleApp.go` export (`app.js:382`), `chatListHidden` Settings toggle (`settings.js:637`) |
| 2026-10-05 | Bash | `python console/kanban.py tracker add T-037 bugs ...` | logged `palette.js:103` bug as `D-1` |

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements-draft]] · [[T-037-context-snapshot]] · [[T-037-gap-analysis]] · [[T-037-iteration-log]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-summary]] · [[T-036-decision-log]] · [[T-031-summary]] · [[T-031-plan]] · [[T-016-summary]]
