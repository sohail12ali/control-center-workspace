---
ticket: "T-037"
artifact: requirements-draft
status: frozen
freeze_status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 2
iteration: 2
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Requirements Draft: T-037

> Working requirements document. **Frozen 2026-10-05 at iteration 2** (source of truth for planning: [[T-037-requirements]]; post-freeze changes go through `evolve`). Iteration 1 applied challenge pass 1 ([[T-037-critique-report]] CR-1..CR-20, [[T-037-gap-analysis]] G1-G26); iteration 2 applied pass 2 (CR-21..CR-24, G27-G30); every design choice is in [[T-037-decision-log]] (D-1..D-23).

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder · `[[link]]` grounded fact · **[PY]** testable by a Python source-regexp test (no JS runner exists; new tests listed in §15) · **[BROWSER]** needs a real browser at the stated viewport (and the Tauri webview where stated): *not verified in a browser* until someone runs it.

---

## 1. Intent

**Stakeholder (one line):** Sohail Ali wants the console to feel like VS Code: pane borders you can drag, sections you can fold, layout changes that are easy to make.

**Business driver:** the console is the daily surface for agents, the vault and tickets; every pane width is a fixed CSS value, the ticket drawer covers the page, and only Settings has foldable sections ([[T-037-analysis]] Current State).

**Raw intent verbatim** ([[T-037-summary]], user request 2026-10-05):
> more responsive, VS Code-like UI — expand sections and layout modifications easily done, able to move the layout borders like we do in VS Code

**Decisions already taken by the user (2026-10-05):** splitters on **all four** surfaces (Agents panes, Vault panes, ticket detail as a docked resizable panel, board lane width); build **alongside** [[T-031-summary]].

## 2. Context Summary

(Condensed from [[T-037-context-snapshot]]; facts cite file:line there.)

- **Similar existing features:** collapse primitive `C.panel(..., {collapse})` / `C.group` (`core.js:204-221,259-317`; `collapsible()` is not exported, `core.js:758`); Settings Collapse/Expand all (`settings.js:1926-1951`); Agents list fold (`agents.js:112-134,1498-1505`); Vault CSS-variable columns (`styles.css:1576-1591`); the one drawer (`app.js:14-53`); `C.prefs` get/set/del (`core.js:444-458`).
- **Affected code areas:** new `console/static/splitter.js`; `styles.css` (mid-file); `index.html` (one tag); `app.js` (drawer IIFE only); `agents.js`, `vault.js`, `board.js`, `overview.js`, `assistant.js`, `settings.js` (one function plus one push line).
- **Known risks from history:** a Chromium transition on `grid-template-columns` pinned the viewer track at 0 (`styles.css:1581-1584`); a missing `min-width:0` clipped tabs (`styles.css:275-280`); duplicate bare-class rules clipped composer controls (`test_stylesheet.py:9-13`); an inline custom property beats a media-query `:root` value (analysis N6).

## 3. Scope

### In scope
- **R-A** reusable splitter component (`splitter.js`, `.sp-*` CSS) · **R-B** persistence as one `layout` object through `C.prefs` · **R-C** responsive behaviour at the 900/901 px cliff.
- **R-D** four surfaces: Agents (list|main, transcript|rail), Vault (sidebar|canvas|viewer), ticket detail as a docked panel, board lane width.
- **R-E** foldable sections on Overview, Assistant home, Agents right rail, Vault sidebar cards; Collapse all / Expand all on Overview and Assistant home.
- **R-F** Reset layout in Settings, plus the cross-ticket acceptance check for "Reset all preferences".

### Out of scope (explicit)
- Per-lane widths (user decision: one global width). Analytics, Work, About sections (opt-in later, one line each).
- Fixing `palette.js:103` (logged as bug `D-1` in `T-037-bugs.toml`) and the baseline `.ob-count` test failure.
- Changing the `C.prefs` implementation (T-036), `core.js`, Tauri/Rust, vertical splitters (no surface needs one), user-defined layouts or presets, drag-to-rearrange panels.
- Editing the `agents.js` copies of the 900 px cliff (`agents.js:112,1498,1501`); a follow-up could point them at `C.splitter.WIDE`.
- Refactoring Settings' `jumpBar()` or changing Esc-in-a-drawer-field behaviour (D-10, D-13).

### Assumptions (decision log carries the rationale)
- A-1 The dock replaces the overlay on wide screens. ⚠ accepted: default pending user confirmation of Q1 (D-1).
- A-2 One `layout` object holds all stored pixel sizes (D-4).
- A-3 Browser verification is run by the parent session; until then it is labelled "not verified in a browser" (D-20).
- A-4 T-036's `C.prefs` keeps today's interface; T-037 ships against the unchanged local implementation if T-036 lands later ([[T-036-decision-log]] `t037-layout-contract`).

## 4. Functional Requirements

Common to every FR: no dependency, no build step, ES5 IIFE `(function (C) { "use strict"; ... })(window.Console)`, DOM through `C.el`, no innerHTML templates, colours through CSS tokens only.

### FR-1: Splitter component
**Description:** `console/static/splitter.js` registers `C.splitter(opts)` returning a controller (`el`, `get`, `set`, `destroy`) and the statics `C.splitter.WIDE`, `C.splitter.reapplyAll()`, `C.splitter.foldBar(host)`. The handle is an overlay on the pane border: it adds no grid track and changes no pane's measured width, and is never a child of a clipping ancestor that hides it (`.vault-stage` is `overflow:hidden`, `styles.css:1634`).
**Actor:** any tab. **Trigger:** surface build (render).
**Acceptance criteria:**
- [ ] AC-1.1 [PY] `index.html` lists `splitter.js` directly after `core.js` and before `app.js`; not adjacent to the `onboarding-wizard.js` tag (`index.html:72`).
- [ ] AC-1.2 [PY] handle built with `C.el` carrying `role="separator"`, `aria-orientation`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-valuetext`, `aria-controls`, `aria-label`, `tabindex`; values are px of the controlled pane; `aria-controls` references the pane's `id`, which `splitter.js` assigns when the pane has none.
- [ ] AC-1.3 [PY] every hyphenated `class:"…"` in `splitter.js` exists in `styles.css`; the `.sp-*` rules sit before the `responsive` section header and not at the end of the file; no bare single-class selector repeats (existing `test_stylesheet.py`).
- [ ] AC-1.4 [PY] `.sp` z-index is 8 (below the topbar 20, `styles.css:284`; above `.list-reveal` 6, `:869`).
- [ ] AC-1.5 [PY] `splitter.js` contains no `=>`, `let `, `const `, backtick, `innerHTML`, `localStorage`, `draggable`, `dragstart`.
- [ ] AC-1.6 [BROWSER] at ~1400 px the hit area is 6 px wide centred on the border (20 px under `(hover: none) and (pointer: coarse)`), `col-resize` cursor, hover and active highlight use tokens; the measured width of every adjacent pane is identical with the handle present and absent. ⚠ [unrealistic?] numbers proposed (coarse-pointer target convention `styles.css:2097-2113`).

### FR-2: Pointer drag
**Description:** Pointer Events only. On `pointerdown` the handle takes pointer capture; `pointermove` is coalesced to one style write per animation frame; `pointerup`, `pointercancel` and `lostpointercapture` all end the drag. While dragging, `document.body` carries a class that sets `user-select:none` and the resize cursor (D-23); it is removed in every end path, including the handle being removed from the DOM mid-drag (G7). `touch-action` lets touch drags work. A splitter is never created inside `.brandrow`, so it cannot start a desktop window drag (`desktop-chrome.js:74-85`).
**Acceptance criteria:**
- [ ] AC-2.1 [PY] source calls `setPointerCapture`, handles `pointercancel` and `lostpointercapture`, uses `requestAnimationFrame` in the drag path, and removes the body drag class in each end handler.
- [ ] AC-2.2 [PY] `.sp` sets `touch-action`; no code attaches a splitter to `.brandrow`.
- [ ] AC-2.3 [BROWSER] ~1400 px, Vault with the graph visible: dragging across the canvas keeps the drag, selects no text, and the cursor stays `col-resize` outside the handle.
- [ ] AC-2.4 [BROWSER] ~1000 px with touch emulation (coarse pointer): a finger drag resizes and the page does not scroll sideways during it.
- [ ] AC-2.5 [BROWSER] board repaint (type in the search box) while a lane drag is held: no error in the console, no stuck body class, the last valid width is kept.
- [ ] AC-2.6 [BROWSER] inside the Tauri webview (Windows): the drag works and the window does not move. macOS/Linux webviews not verified.

### FR-3: Keyboard, collapse, reset
**Description:** Handle is focusable (`tabindex=0`). ArrowLeft/ArrowRight move the border by 16 px (Shift: 64 px); Home/End go to the pane's minimum/maximum; Enter collapses/restores where the pane is collapsible (FR-5 table) and is a no-op elsewhere. Double-click resets that handle to its default by **deleting its key** (D-4) and restores a collapsed pane. Dragging so that the raw width falls below half the minimum collapses (collapsible panes only), otherwise the width clamps to the minimum. Click, Enter or double-click on a collapsed handle restores the last stored width. ⚠ [unrealistic?] step and threshold proposed.
**Acceptance criteria:**
- [ ] AC-3.1 [PY] source handles `ArrowLeft`, `ArrowRight`, `Home`, `End`, `Enter`, and `dblclick`.
- [ ] AC-3.2 [BROWSER] ~1400 px Agents: focus the handle with Tab, ArrowRight x3 changes the list by +48 px and `aria-valuenow` follows; a visible focus ring appears (tokens).
- [ ] AC-3.3 [BROWSER] double-click on a handle returns the pane to its default width and the `layout` key is gone (inspect storage), not set to the default number.
- [ ] AC-3.4 [BROWSER] dragging the Agents rail below 100 px collapses it; Enter on the remaining handle restores the previous width.

### FR-4: Persistence (`layout`)
**Description:** One `layout` object through `C.prefs.get/set/del` only (shape and rules: D-4, §6). Read when a surface is built, never at script load. Written once per completed drag, keyboard step, collapse/restore or double-click, never per pointer-move. Read-modify-write preserving unknown keys. Stored px are clamped when applied (build and window resize) and never rewritten by the clamp. The window `resize` listener and any document-level listener are installed once, lazily; the instance registry drops hosts that are no longer connected (D-19).
**Acceptance criteria:**
- [ ] AC-4.1 [PY] `splitter.js` has no top-level `C.prefs` call; `prefs.set(` appears only inside one write helper that calls `prefs.get("layout"` first.
- [ ] AC-4.2 [PY] `addEventListener("resize"` appears once in `splitter.js` behind an install-once guard; the registry pruning uses `isConnected`.
- [ ] AC-4.3 [BROWSER] wrap `C.prefs.set` in the console: one drag = one `layout` write; a click without movement = no write; reload at the same size restores the width.
- [ ] AC-4.4 [BROWSER] set a stored `agents.list` of 2000 at ~1000 px: the list shows its maximum, the stored value is still 2000, widening the window shows the larger width again.
- [ ] AC-4.5 [BROWSER] `layout` set to a string, to `null`, and to an object with `agents.list: "x"`: every surface renders its default, no error.

### FR-5: Wide only, and the pane table
**Description:** Handles are `display:none` by default and shown only inside `@media (min-width: 901px)` (D-2); hidden means unfocusable and unhittable. Sizes are written as `--sp-*` variables on the pane's own container and consumed only inside the same wide block (D-3): at 900 px and below, computed pane widths are identical with and without a stored `layout`, and the stacked layouts, the `min-width:0`/`min-height:0` rules and the 1280/1100/900/720 breakpoints are unchanged. No variable on `<html>`, no inline `grid-template-columns`, no `transition` on `grid-template-columns`.

| Handle | Default (today) | Min | Max | Collapse |
|---|---|---|---|---|
| `agents.list` | `clamp(208px, 22vw, 302px)` `styles.css:841` | 180 | 480, transcript >= 320 | yes, via `setListShown` |
| `agents.rail` | 260 `styles.css:940` | 200 | 520, transcript >= 320 | yes, `railOff` |
| `vault.side` | 262 `styles.css:1577` | 200 | 480, stage >= 200 | yes, `sideOff` |
| `vault.viewer` | 400 `styles.css:1578` | 280 | 720, stage >= 200 | no (X closes) |
| `board.lane` | 270, 252 at <=1280 `styles.css:78,1983` | 200 | 480 | no |
| `dock.w` | 430 `styles.css:1680` | 320 | 720, `main#view` >= 360 | no (X / Esc closes) |

The flexible pane's minimum bounds the dragged pane's maximum so panes never overlap; if even the minimums do not fit, the dragged pane sits at its minimum and the flexible pane shrinks (no horizontal page scroll). ⚠ [unrealistic?] all numbers proposed (D-5); Vault stage minimum is 200 because today's default at 901 px with the viewer open already leaves 239 px.
**Acceptance criteria:**
- [ ] AC-5.1 [PY] `.sp` has `display:none` outside any media query and a `display` other than `none` only inside `@media (min-width: 901px)`.
- [ ] AC-5.2 [PY] `splitter.js` contains the string `901px` exactly once (`C.splitter.WIDE`); no `max-width: 900px` there.
- [ ] AC-5.3 [PY] every use of `var(--sp-` in `styles.css` is inside an `@media (min-width: 901px)` block; no `documentElement.style` and no `gridTemplateColumns` in static JS.
- [ ] AC-5.4 [PY] `styles.css` has no `transition` naming `grid-template-columns`; `.ap-rail`, `.ap-main`, `.vault-stage`, `.vault-viewer`, `.lanes`-related rules keep their `min-width:0`/`min-height:0`.
- [ ] AC-5.5 [BROWSER] at exactly 900 px no handle is visible and Tab never lands on one; at 901 px handles work; at ~800 px with `layout` = list 400 / side 400 / lane 400 / dock 600 stored, every pane's computed width equals the same page with no `layout`.
- [ ] AC-5.6 [BROWSER] at ~1400 px each table row can be dragged to its min and max and not beyond.

### FR-6: Agents list | main (`.appshell`)
**Description:** A handle on the border between the chat list (`.ap-rail`, the list, despite the name) and `.ap-main` resizes the list through `--sp-list` on `.appshell`, consumed by the existing rule inside the wide block. Collapse and restore use the existing `setListShown(false|true)` and `chatListHidden` (one fact, one place; no second flag). While the list is folded the handle is not rendered and the existing `.list-reveal` button is the restore control; after Enter-collapse focus moves to it. `.appshell.hide-list` (`styles.css:883`) keeps winning when folded.
**Acceptance criteria:**
- [ ] AC-6.1 [PY] the collapse path in the Agents attach code calls `setListShown`; no new hidden-list flag or pref is introduced in `agents.js`.
- [ ] AC-6.2 [PY] `styles.css` consumes `var(--sp-list` in the wide block, with `clamp(208px, 22vw, 302px)` as the fallback.
- [ ] AC-6.3 [BROWSER] ~1400 px: drag the list from default to 300 and 180, below 90 it folds; reveal button and Enter restore; reload keeps the width and (after a fold) the fold.

### FR-7: Agents transcript | right rail (`.ct-split`)
**Description:** A handle on the border between `#ctScroll` and the rail. `.ct-split` is recreated per chat (`agents.js:960`), so the handle is attached in `mountChat` as a child of `.ct-split`, not of `#ctRail`, which is cleared on every `meta` event (`paintRail2`, `agents.js:1169-1171`). `--sp-rail` is written on `.ct-split`. Collapsed (`railOff`): rail hidden, handle stays at the container's right edge as the restore control.
**Acceptance criteria:**
- [ ] AC-7.1 [PY] the attach call sits in `mountChat`; the handle is appended to the `.ct-split` element, never to the `rail` variable.
- [ ] AC-7.2 [BROWSER] ~1400 px: while a chat streams (meta repaints) a drag is not interrupted and the handle and width survive; switching chats keeps the width.
- [ ] AC-7.3 [BROWSER] collapsed rail restores by click, Enter and double-click; at ~800 px the rail is below the transcript exactly as today.

### FR-8: Vault sidebar | canvas | viewer (`.vault`)
**Description:** Two handles on `.vault`: sidebar|stage (`--sp-side`, collapsible via `sideOff`) and stage|viewer (`--sp-viewer`), the latter present only while `.vault.has-viewer`. Handles are outside `.vault-stage`. While a pane drag is active `resize()` returns early (flag in `vault.js`); on release the flag clears and `resize()` runs once (D-11); the `setTimeout(resize, 60)` calls stay. A viewer that closes mid-drag ends the drag cleanly.
**Acceptance criteria:**
- [ ] AC-8.1 [PY] `vault.js` guards `resize()` with a drag flag, clears it on release and calls `resize()` after.
- [ ] AC-8.2 [PY] the Vault handles are appended to the `.vault` element (`#vaultWrap`), not to `.vault-stage`.
- [ ] AC-8.3 [BROWSER] ~1400 px with a graph of the real vault: devtools (a setter spy on the two canvases' `width`/`height`) shows zero backing-store reallocations during a 2-second drag and exactly one after release; the canvas is crisp after release.
- [ ] AC-8.4 [BROWSER] 901 px with the viewer open: dragging the viewer wider stops at the point where the stage is 200 px.

### FR-9: Board lane width
**Description:** One global lane width (BR-1) through `--sp-lane` on `.lanes`. Every non-cold lane has a handle on its trailing edge; the pointer delta is divided by the lane's ordinal among non-cold lanes so the edge stays under the pointer; only the first handle is in the tab order and carries the ARIA value, the others are pointer-only and `aria-hidden` (D-7). The cold lane gets none. The stored width applies in the wide block only, so the 1280 px trim (`styles.css:1982-1984`) and the 720 px bypass (`:2056`) are unchanged for users with no stored width.
**Acceptance criteria:**
- [ ] AC-9.1 [PY] `--sp-lane` is written on the `.lanes` element, not on `:root`/`<html>`; `styles.css` consumes it in the wide block.
- [ ] AC-9.2 [BROWSER] ~1400 px tickets board: dragging lane 3's edge keeps the pointer within 2 px of the edge; every non-cold lane has the same width; the cold lane stays 52 px.
- [ ] AC-9.3 [BROWSER] a search keystroke (board repaint) and "Show more" keep the stored width; the first handle is the only lane handle reachable by Tab.

### FR-10: Docked ticket panel
**Description:** When `dockMode()` is true (viewport wide, D-1) `ConsoleApp.drawer.open(title, subtitle)` shows the panel docked: no scrim, not modal (`aria-modal` false), `role="complementary"` with an `aria-label` (modal mode keeps `role="dialog"` and `aria-modal="true"`, `app.js:35`), top edge equal to the topbar's bottom edge at every viewport height including the `max-height:680px` trims (`styles.css:2075`), `main#view` keeps its element and id and shrinks, width from `dock.w` (default 430) with a left-edge handle. Otherwise (900 px and below) it is today's modal with scrim, `aria-modal`, `slidein`, full width at 720 px and below (`styles.css:2058`). `open()` returns the body node, `close()` is unchanged, the exported shape stays `{open, close}`, and `board.js:300` stays the only opener (`palette.js:103` out of scope, D-17). ⚠ accepted: default pending user confirmation of Q1; switching to the opt-in alternative changes only `dockMode()` (D-1).
**Acceptance criteria:**
- [ ] AC-10.1 [PY] `app.js` still exports `drawer` as an object with `open` and `close`; across `console/static/*.js`, `drawer.open(` is called only from `board.js`.
- [ ] AC-10.2 [PY] the mode decision is one function `dockMode()` in the drawer IIFE that uses `C.splitter.WIDE`; the drawer code sets both `role` values (`dialog` with `aria-modal`, `complementary` without) and flips them on a live mode switch.
- [ ] AC-10.3 [BROWSER] ~1400 px: opening a card shows the panel beside the board with no scrim; the topbar and tabs stay visible and clickable; the panel's top edge touches the topbar's bottom edge (also at 1400x600).
- [ ] AC-10.4 [BROWSER] ~800 px and ~400 px: scrim, modal, full width at 400 as today.
- [ ] AC-10.5 [BROWSER] ~1280 and ~1400 px with the default 430 px dock: the board scrolls sideways (about 286 and 238 px per the analysis arithmetic, not measured) and narrowing the dock or the lanes removes it; this is accepted behaviour (CR-18).
- [ ] AC-10.6 [BROWSER] dock drag clamps at 320 and 720, and never below `main#view` 360; reopening another ticket keeps the width after reload.

### FR-11: Dock behaviour
**Description:** (1) One panel at a time. (2) Initial focus goes to the panel's first button (Close), as today (`app.js:48`); on close focus returns to the opener if still connected (`app.js:25`). (3) Esc: modal mode unchanged; docked mode closes only when the event target is inside the panel, Esc elsewhere does nothing to it; Esc in a drawer field still reverts that field and closes (`board.js:333`; D-10, not changed). (4) Any tab switch, the `r` key and the refresh button close it (`go()`, `app.js:128`). (5) A second `open()` while open refreshes in place: same panel, width and original focus-restore target, no `slidein` replay, title/subtitle updated, `.dbody` replaced by a **new** node that is returned (D-9, closes CR-1). (6) When the viewport crosses 901 px while a ticket is open the same panel element switches mode, scrim added/removed, the body node (and an edit in progress) preserved, focus kept on the same control or moved to Close if the control was removed. (7) Hidden in print, and the dock's grid column does not reserve space in print.
**Acceptance criteria:**
- [ ] AC-11.1 [PY] the drawer code creates a fresh `.dbody` on a repeat `open()` (no reuse of the old node) and registers its keydown/matchMedia listeners once.
- [ ] AC-11.2 [PY] the `@media print` block hides the docked panel and resets the dock layout on `#app`.
- [ ] AC-11.3 [BROWSER] ~1400 px: Esc in the board search box with a docked panel open leaves it open; Esc with focus on its Close button closes it and focus returns to the card; Esc inside an owner field reverts and closes (unchanged).
- [ ] AC-11.4 [BROWSER] commit an edit in the Owner field (`patchTicket` then `openTicket`, `board.js:306-315,412`) and watch the refresh: the panel does not slide in again, width and focus owner stay; two rapid refreshes never show the older ticket's content.
- [ ] AC-11.5 [BROWSER] resize the window from 1400 to 800 px and back with a ticket open: it becomes modal (scrim), then docked again, and a half-typed value in a field survives both switches.
- [ ] AC-11.6 [BROWSER] Print preview with the dock open at ~1400 px: no panel, no empty column.

### FR-12: Foldable sections
**Description:** The sections below fold and persist through the existing `panelOpen` map (`{id: bool}`, `core.js:254-298`) under the literal, globally unique ids shown (BR-5). Enter/Space on a header toggles; `section._setOpen(bool)` and `data-panel-id` are preserved for `C.panel`/`C.group` sections. Defaults keep today's look. Overview and Assistant use `C.panel(..., {collapse:{id, open}})`; the Agents rail uses `C.group(title, kids, {id, open})` because `collapsible()` is not exported and `core.js` is not edited (D-12), and each rail section keeps the class `ct-panel` so the sideways strip at 900 px and below (`.ct-rail > .ct-panel`, `styles.css:2020`) is unchanged; Vault cards keep their own `.vault-card` DOM and move their state from `st.openCards` to `panelOpen`. The Getting-started card keeps its own fold (`onboardingOpen`, `overview.js:50,87-102`); Analytics, Work, About are out.

| Surface | Section (today) | Id | Default |
|---|---|---|---|
| Overview | At a glance `overview.js:259` | `ov.glance` | open |
| Overview | Needs attention `:295` | `ov.attention` | open |
| Overview | Flow `:334` | `ov.flow` | open |
| Overview | Recently touched `:355` | `ov.recent` | open |
| Overview | Jobs `:194` (async, self-removing) | `ov.jobs` | open |
| Overview | Scheduled `:244` (async, self-removing) | `ov.schedules` | open |
| Assistant home | Talk `assistant.js:149` | `as.talk` | open |
| Assistant home | Runs `:164` | `as.runs` | open |
| Assistant home | Tickets `:167` | `as.tickets` | open |
| Agents rail | Console budget `agents.js:1165` | `ag.budget` | open |
| Agents rail | Plan `:1177` | `ag.plan` | open |
| Agents rail | Todos `:1192` | `ag.todos` | open |
| Agents rail | Files touched (N) `:1205` | `ag.files` | open |
| Agents rail | Queued (N) `:1224` | `ag.queued` | open |
| Vault sidebar | Filters `vault.js:33` | `vault.filters` | open |
| Vault sidebar | Display `:34` | `vault.display` | closed |
| Vault sidebar | Forces `:35` | `vault.forces` | closed |
| Vault sidebar | Navigator `:36` (grow card) | `vault.navigator` | open |

The Overview "Needs attention" Enter handler (`overview.js:303-317`) ignores events whose target is inside the panel header and returns early while the panel is collapsed (D-14). Titles with counts never derive the id.
**Acceptance criteria:**
- [ ] AC-12.1 [PY] each id above appears as a literal exactly once in its file and in no other `static/*.js`; the Settings ids (`set.*`) are untouched.
- [ ] AC-12.2 [PY] `overview.js` Enter handler contains a header-target guard (`closest("header")`) and a collapsed check; `vault.js` reads and writes the `panelOpen` pref and no longer uses `st.openCards` as the store; `agents.js` rail uses `C.group` with the `ag.*` ids and keeps `ct-panel` on each section.
- [ ] AC-12.3 [PY] `core.js` has no T-037 change (verification evidence: `git diff` shows no T-037 hunk there; other tickets' hunks listed in the analysis are intact).
- [ ] AC-12.4 [BROWSER] ~1400 px: fold a section on each of the four surfaces, switch tab and back, reload: each stays as left; the Agents rail keeps its folds across `meta` repaints and chats.
- [ ] AC-12.5 [BROWSER] Overview: with "Needs attention" focused on its header, Enter folds it and does not navigate; Enter on the panel body still opens the highlighted row; a collapsed Overview panel in the grid shows only its header (no stretched empty card).
- [ ] AC-12.6 [BROWSER] ~400 px: folds work by touch; the Agents rail (below the transcript at <=900) still scrolls sideways with folded sections.

### FR-13: Collapse all / Expand all
**Description:** `C.splitter.foldBar(host)` in `splitter.js` returns a two-button control; its click handlers query `[data-panel-id]` under `host` at click time (G15, N10) and call `_setOpen`. Used on Overview and Assistant home only (D-13), placed by the caller as the first row of the page, right-aligned, above the panels. `settings.js` `jumpBar()` is not changed.
**Acceptance criteria:**
- [ ] AC-13.1 [PY] the query for `[data-panel-id]` runs inside the click handler, not at build; `settings.js` has no new reference to `foldBar`.
- [ ] AC-13.2 [BROWSER] Overview: panels added after build (Jobs, Scheduled) fold with the rest; a panel that removed itself is not an error; Settings' own Collapse/Expand all still works.

### FR-14: Reset layout
**Description:** Settings gains `layoutPanel()` as its own function with its own single `kids.push(layoutPanel())` line beside `storage()` (anchor by function name, not by the "Stored in this browser" title, which T-036 may reword). It deletes exactly `layout`, `panelOpen` and `chatListHidden` (D-15; not `onboardingOpen`, `hiddenTabs`, theme) and applies without a page reload: `C.splitter.reapplyAll()` re-applies live instances and the active tab is re-rendered through `ConsoleApp.go`, so folds are re-read; a toast confirms. Settings' "Start with the chat list folded" toggle reads its value on render. Re-rendering Settings returns the page to its top; accepted (CR-23).
**Acceptance criteria:**
- [ ] AC-14.1 [PY] `settings.js` gains one function and exactly one added `kids.push(` line; the other tickets' hunks (`identity()`, the storage-panel row, `kids.push(identity())`) are unchanged.
- [ ] AC-14.2 [PY] the function deletes only the three keys through `C.prefs.del`; it contains no `localStorage` and no `C.prefs.reset`.
- [ ] AC-14.3 [BROWSER] ~1400 px: after changing a list width, folding two Overview panels and hiding the Agents list, Reset layout returns every surface to defaults with no reload; theme and hidden tabs are unchanged.

### FR-15: "Reset all preferences" resets the live layout (cross-ticket acceptance check)
**Description:** T-036 owns that button and its code. Once T-036 lands, pressing it must also leave the live UI at default layout without a page reload (same mechanism as FR-14). T-037 does not edit T-036's `storage()`.
**Acceptance criteria:**
- [ ] AC-15.1 [BROWSER] after both tickets are in: change a pane width and a fold, press "Reset all preferences", confirm: layout is default with no reload. *Cannot be verified before T-036 lands; stays "not verified" until then.*
- [ ] AC-15.2 [PY] `reapplyAll` is exposed by `splitter.js` and nothing in T-037's `settings.js` function depends on T-036's `C.prefs.reset`.

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | Drag cost | at most one style write per animation frame; zero Vault canvas reallocations during a drag, one after release | N5; measured by call count, not frame rate. ⚠ [unrealistic?] proposed |
| Performance | Prefs write rate | exactly one `C.prefs.set("layout")` per completed drag, key step, collapse/restore, double-click; none per pointer-move; none on a click without movement | [[T-036-decision-log]] `t037-layout-contract`: debounce is a backstop |
| Compatibility | Stack | no dependency, no build step, ES5, `C.el`, no innerHTML templates, tokens only | `styles.css:4-6`, `core.js:161-175` |
| Compatibility | Tests | no new failing test id; the only red is `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count` (baseline 1 failed / 2273 passed); compared by id, not count | analysis N12; D-20 |
| Usability | Accessibility | APG Window Splitter keys and ARIA; visible focus ring; every handle has an accessible name | analysis Research |
| Usability | Touch | 20 px hit area under coarse pointer | ⚠ [unrealistic?] proposed (`styles.css:2097-2113`) |
| Maintainability | One fact, one place | one wide-query constant; `chatListHidden` the only list-fold flag; one `layout` object | D-2, D-4 |
| Compliance | Print and motion | dock and handles hidden in print; no size transitions; dock slide-in obeys the global reduced-motion switch | `styles.css:2117-2132` |
| Security / Auth | N/A | client-only state, no endpoint, no HTML injection (`C.el` with `text`) | no server surface added |
| Auditability | N/A | layout prefs are not audited; T-036's store applies its own rules | |
| Availability | Static export and local mode | `splitter.js` ships through the export glob (`export.py:87-90`); prefs fall back to local mode | [[T-036-decision-log]] `prefs-client-contract` |
| Scalability | N/A | a constant, small number of handles per page (at most 8) | |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `layout` pref | new key in `C.prefs` | `{ v: 1, agents: {list, rail, railOff}, vault: {side, viewer, sideOff}, board: {lane}, dock: {w} }`, integer px, booleans for `*Off` | write on drag release / key step / collapse / dbl-click; delete by Reset layout or per-key double-click | D-4; [[T-036-decision-log]] `t037-layout-contract` |
| `panelOpen` pref | exists | `{id: bool}`, ids in FR-12 | read per section build; written per toggle; deleted by Reset layout | `core.js:254-298` |
| `chatListHidden` pref | exists | bool | unchanged; deleted by Reset layout | `agents.js:132` |

### Data flows
Pointer or key → splitter clamps → surface callback writes `--sp-*` on the pane container → on release `C.prefs.set("layout")` (read-modify-write). Build → `C.prefs.get("layout")` → validate → clamp → variable. Reset → `C.prefs.del` ×3 → `reapplyAll()` + `go(active)`.

### Retention / archival
Same as every other pref; T-036 moves storage server-side with the same interface. Unknown keys inside `layout` are preserved.

## 7. Business Rules

- **BR-1:** One global lane width, never per-lane.
- **BR-2:** The stored pixel value is never rewritten by a clamp; only a user action writes `layout`.
- **BR-3:** At 900 px and below the structural CSS layouts apply and no stored size does.
- **BR-4:** Only one ticket panel is open at a time.
- **BR-5:** Section ids are globally unique across tabs (`panelOpen` is one flat map, `core.js:261`).
- **BR-6:** Other tickets' uncommitted hunks are never touched (D-21; [[T-037-analysis]] Constraints 1-2).
- **BR-7:** Reset and double-click delete keys; they never write default numbers.
- **BR-8:** Only `C.prefs` touches storage; T-037 never edits the `C.prefs` implementation.
- **BR-9:** Each pane's collapsed state is one fact: the Agents list in `chatListHidden`, the rail and Vault sidebar in `layout`.
- **BR-10:** Hidden means inert: a handle that is not shown cannot be focused or hit.

## 8. Edge Cases

- `layout` not an object, or a value not a positive finite number: ignored per key, defaults used (AC-4.5).
- Window narrower than the sum of minimums: dragged pane at its minimum, flexible pane shrinks, no overlap, no page scroll (FR-5).
- Handle removed during a drag (repaint, `go()`, viewer closing): drag ends, last valid value kept, no stuck class (AC-2.5).
- No non-cold lane on a board: no lane handle.
- Vault with no graph or no viewer: the viewer handle is not rendered; the sidebar handle still works.
- A restored Agents list at a stored width larger than the maximum at the current window: shown clamped, stored value untouched (AC-4.4).
- Two refreshes of the dock in a row: only the newest ticket's content shows (AC-11.4).
- Viewport exactly 900.5 px: counts as not wide everywhere in T-037 code (D-2).
- Print with the dock open (AC-11.6).

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| Ticket drawer, `app.js:14-53` | conflict: scrim, `aria-modal`, close+open refresh, covers the topbar (N7-N9) | high | modify (dock mode inside the same IIFE; `{open, close}` kept; D-8, D-9) |
| `chatListHidden` / `setListShown`, `agents.js:112-134` | overlap | low | reuse as the list collapse; no second flag (FR-6) |
| `C.panel` / `C.group` collapse, `core.js:204-317` | overlap | low | reuse; rail uses `C.group` because `collapsible()` is not exported (D-12) |
| Settings `jumpBar()`, `settings.js:1926-1951` | overlap | low | isolate; shared helper in `splitter.js` (D-13) |
| Vault `ResizeObserver`, `vault.js:450-452` | conflict: per-frame canvas reallocation | med | modify (drag flag, D-11) |
| `desktop-chrome.js:74-85` window drag | isolation | low | no handle inside `.brandrow` (AC-2.2) |
| Overview Needs-attention Enter handler, `overview.js:303-317` | conflict with the collapse header Enter | med | modify (guard, D-14) |
| Overview onboarding fold, `overview.js:50,87-102` | overlap | low | isolate (own fold stays, D-12) |
| Agents rail strip at <=900 px, `.ct-rail > .ct-panel`, `styles.css:2015-2020` | conflict: `C.group` sections would drop `.ct-panel` | med | modify (keep `ct-panel` on each rail section, FR-12) |
| CSS cliffs and `:root` trims, `styles.css:1982-2061` | conflict: inline variable beats the trim (N6) | high | isolate (`--sp-*` on containers, wide block only, D-2, D-3) |
| `palette.js:103` broken `app.drawer(...)` | isolation | low | defer: bug `D-1` logged (D-17) |
| T-036 `C.prefs`, [[T-036-decision-log]] | reuse (interface only) | med | reuse, never edit (BR-8) |
| Uncommitted hunks of T-031, T-036, T-020/T-021 in `settings.js`, `styles.css`, `app.js`, `index.html`, `overview.js` | conflict risk | high | isolate (BR-6, D-21) |
| Board card HTML5 DnD, `board.js:113-118,181-192` | isolation | low | lane handle never `draggable`; pointer events only on the handle |
| Vault canvas mouse events, `vault.js:382-436` | isolation | med | handles outside `.vault-stage` (AC-8.2) |
| Settings "Start with the chat list folded", `settings.js:637` | overlap with Reset | low | Reset deletes `chatListHidden`; toggle re-reads on render |
| Print rule, `styles.css:2129` | overlap | low | extend for the dock (AC-11.2) |
| `test_stylesheet.py`, `test_plugins.py:231-240` | reuse (constraints) | low | keep green (AC-1.1, AC-1.3) |

Counts: overlap 5 · conflict 6 · reuse 3 · isolation 4.

## 10. External Dependencies

- [[T-036-summary]]: `C.prefs` interface (same signatures), `t037-layout-contract`. Not landed at draft time (`core.js` unmodified); T-037 works against the unchanged local implementation and is picked up by T-036's import unchanged.
- [[T-031-summary]]: concurrent edits to `settings.js` and `styles.css` (appended block).
- Tauri webview (WebView2 / WKWebView / WebKitGTK): pointer capture unverified; only Windows is in the BROWSER plan.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner / user | Sohail Ali | VS Code-like feel; Q1; the proposed numbers | APPROVED of the frozen set requested in the analyst's report; Q1 default revisable |
| Concurrent ticket owners | T-031, T-036, T-020/T-021 sessions | no clobbered hunks; `layout` contract | no |
| Parent session | harness | runs the [BROWSER] checks | no |

## 12. Open Questions (mirrored)

Mirrored from `T-037-questions.toml` (`console/kanban.py tracker list T-037 questions`).

- Q1: dock replaces the overlay on wide screens, or opt-in toggle — status: **open**, medium, non-blocking. Default taken: replace (D-1), `⚠ accepted: default pending user confirmation of Q1`.

## 13. Challenge Findings (⚠)

Pass 1 raised CR-1..CR-20; iteration 1 resolved CR-1..CR-18 and CR-20 in place. Pass 2 raised CR-21..CR-24; iteration 2 resolved CR-21, CR-22, CR-24 in place (see [[T-037-critique-report]] Resolution column). Remaining, accepted:

- ⚠ accepted: CR-23 [ambiguity] §FR-14: re-rendering Settings after Reset returns the page to its top — rationale: `go()` clears and rebuilds `#view` by design (`app.js:141`); a live in-place re-apply of every Settings fold would need the unexported `collapsible()`; the toast confirms the action.
- ⚠ accepted: CR-19 [spof] §10: T-036 not landed, and app and browser share one `layout` last-writer-wins after it lands — rationale: already accepted by T-036 (`scope-boundaries` risk 2); stored px are clamped at apply time so a size from a larger window cannot break a smaller one.
- ⚠ accepted: Q1 default (FR-10, D-1) — rationale: matches the summary wording; one-function change to the alternative.
- ⚠ accepted: every `⚠ [unrealistic?]` number (hit area 6/20 px, step 16/64 px, collapse at half the minimum, the per-handle min/max in FR-5, drag-cost call counts, coarse-pointer 20 px) — rationale: tunables whose defaults are today's CSS values; they are confirmed or adjusted in the [BROWSER] pass and each is a single constant to change; no stakeholder has confirmed them yet.

## 14. Draft History

See [[T-037-iteration-log]] for per-iteration diff + rationale. Current iteration: **2**.

## 15. Test plan (ownership split)

### Python source-regexp tests to write (new file `console/tests/test_splitter.py`, no JS runner exists)
| # | Test | Covers |
|---|---|---|
| P-1 | script order: `core.js` < `splitter.js` < `app.js`, `splitter.js` not next to `onboarding-wizard.js` | AC-1.1 |
| P-2 | `splitter.js` ES5 and hygiene: no `=>`, `let `, `const `, backtick, `innerHTML`, `localStorage`, `draggable`, `dragstart`, `documentElement.style`, `gridTemplateColumns` | AC-1.5, AC-5.3 |
| P-3 | ARIA attributes and key names present | AC-1.2, AC-3.1 |
| P-4 | pointer API: `setPointerCapture`, `pointercancel`, `lostpointercapture`, `requestAnimationFrame`, body class removed in each end handler | AC-2.1 |
| P-5 | `prefs.set(` only inside one helper that reads `layout` first; no top-level `C.prefs` call | AC-4.1 |
| P-6 | install-once `resize` listener; `isConnected` pruning | AC-4.2 |
| P-7 | CSS: `.sp` default `display:none`, shown only in `@media (min-width: 901px)`, `touch-action`, z-index 8; `.sp-*` before the responsive header | AC-1.3, AC-1.4, AC-2.2, AC-5.1 |
| P-8 | CSS: every `var(--sp-` inside `@media (min-width: 901px)`; fallbacks equal today's values; no `transition` on `grid-template-columns`; kept `min-width:0`/`min-height:0` | AC-5.3, AC-5.4, AC-6.2 |
| P-9 | `splitter.js` has `901px` once and no `max-width: 900px` | AC-5.2 |
| P-10 | drawer: exported `{open, close}`, `dockMode()` uses `C.splitter.WIDE`, repeat `open()` builds a fresh `.dbody`, listeners registered once; `drawer.open(` only in `board.js`; print block covers the dock | AC-10.1, AC-10.2, AC-11.1, AC-11.2 |
| P-11 | section ids: each literal once in its file, none repeated across files; Overview guard; Vault uses `panelOpen`; Agents rail uses `C.group` | AC-12.1, AC-12.2 |
| P-12 | Agents: collapse path calls `setListShown`; attach in `mountChat`; handle appended to `.ct-split` not `rail`; Vault handles appended to `#vaultWrap`; `vault.js` drag flag around `resize()`; `--sp-lane` on `.lanes` | AC-6.1, AC-7.1, AC-8.1, AC-8.2, AC-9.1 |
| P-13 | `foldBar` queries `[data-panel-id]` inside the handler | AC-13.1 |
| P-14 | `settings.js`: one `layoutPanel`, one added `kids.push(layoutPanel())`, deletes only the three keys via `C.prefs.del`, no `localStorage` | AC-14.1, AC-14.2 |
| P-15 | existing `test_stylesheet.py` and `test_plugins.py` stay green except the baseline `.ob-count` failure | NFR Tests |

Evidence outside pytest (recorded in verification): `git diff` shows no T-037 hunk in `core.js` and the listed other-ticket hunks intact (AC-12.3, BR-6).

### [BROWSER] checks (parent session; labelled "not verified in a browser" until done)
| # | Viewport / setup | Check | ACs |
|---|---|---|---|
| B-1 | ~1400 px, Agents | list drag, clamp, fold, restore, keyboard, double-click, reload | 3.x, 6.3, 4.3 |
| B-2 | ~1400 px, Agents chat streaming | rail drag survives `meta` repaints; collapse restore | 7.2, 7.3 |
| B-3 | ~1400 px, Vault with graph; 901 px with viewer | zero canvas reallocations during a drag, one after, 200 px stage floor | 2.3, 8.3, 8.4 |
| B-4 | ~1400 px, tickets board | lane drag tracks the pointer, repaint keeps width, cold lane 52 px | 9.2, 9.3, 2.5 |
| B-5 | ~1400 and ~1280 px, ticket open | docked beside the board, topbar reachable, sideways scroll as computed, dock drag clamps | 10.3, 10.5, 10.6 |
| B-6 | docked panel behaviours | Esc rules, focus restore, refresh without slide-in or stale content, live 1400↔800 switch with an edit in progress, print preview | 11.3-11.6 |
| B-7 | exactly 900 and 901 px; ~800 px with a stored `layout` | handles absent and untabbable, computed widths unchanged | 5.5 |
| B-8 | ~400 px | modal full-width drawer, folds by touch, rail scroll | 10.4, 12.6 |
| B-9 | ~1000 px touch emulation | coarse hit area drag | 1.6, 2.4 |
| B-10 | Tauri webview on Windows | drag works, window does not move | 2.6 |
| B-11 | folds on all four surfaces, Overview Enter guard, Collapse/Expand all incl. async panels | persistence and guard | 12.4, 12.5, 13.2 |
| B-12 | Reset layout; later "Reset all preferences" after T-036 | no reload needed | 14.3, 15.1 |
| B-13 | invalid stored `layout` | defaults, no error | 4.5 |

## Freeze Checklist (run by `requirements freeze`)

Result 2026-10-05, iteration 2: all pass.

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred (grep: only the legend and this list name the token)
- [x] All ⚠ findings resolved or explicitly accepted with rationale (CR-1..CR-24: 22 resolved, CR-19 and CR-23 accepted; Q1 default and proposed numbers accepted, §13)
- [x] No 🔴 blocker gaps in the gap analysis (3 raised, 3 closed by decisions)
- [x] All blocker/critical open questions answered (none exist; Q1 is medium)
- [x] Every FR has at least one testable acceptance criterion (FR-1..FR-15, each [PY] or [BROWSER])
- [x] Every NFR has a concrete target or documented N/A (§5)
- [x] Every new/changed entity has a canonical reference or creation plan (§6)
- [x] Out-of-scope list is non-empty (§3)
- [x] Interactions with Existing Features populated (§9, 18 rows)
- [x] Stakeholder sign-off recorded where required: **recorded as requested, not claimed.** The user's brief is the source; sign-off is the user's APPROVED reply to the analyst report; Q1 stays open
- [x] `T-037-requirements.md` finalized for `requirements stories` consumption

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements-draft]] · [[T-037-context-snapshot]] · [[T-037-gap-analysis]] · [[T-037-iteration-log]] · [[T-037-decision-log]] · [[T-037-critique-report]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
