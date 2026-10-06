---
ticket: "T-037"
artifact: decision-log
---

# Decisions: T-037

Status key: **user** = decided by the user before this ticket (cited) · **analyst default** = chosen in CLARIFY from the analysis' proposed defaults, revisable through a user veto before planning or `evolve` after freeze · **⚠ accepted** = default taken while a question is still open. Format per entry: what / why / rejected alternative.

## D-1 — Docked panel replaces the overlay on wide screens (⚠ accepted: default pending user confirmation of Q1)
**What:** On a viewport wider than 900 px, ticket detail opens as a docked, resizable panel and there is no scrim. At 900 px and below it is the existing modal with scrim, Esc and focus handling. **Status:** analyst default; Q1 (`T-037-questions.toml`, medium, non-blocking) stays open and is not answered here.
**Why:** the summary says "instead of the modal overlay" ([[T-037-summary]] scope 4).
**Rejected:** (B) opt-in "dock" toggle with the overlay as default: adds a Settings row on the contended `settings.js` and a second state to test; (C) other: unspecified.
**How switching to B stays small:** the mode decision is one function in the drawer IIFE, `dockMode()`, returning "viewport is wide". Option B changes that one expression to "wide AND `C.prefs.get("ticketDock", false)`" and adds one Settings toggle row; nothing else in the dock, splitter or tests depends on how the decision is made. FR-10 and FR-11 are written against `dockMode()`, not against the viewport directly.

## D-2 — One "wide" query, `(min-width: 901px)`, in CSS and JS (analyst default)
**What:** every splitter rule (handle visible, user size consumed) lives inside `@media (min-width: 901px)`, the complement of the structural cliff `@media (max-width: 900px)` (`styles.css:1994`) and the same query the Agents fold already uses (`styles.css:882`). `splitter.js` holds that string once (`C.splitter.WIDE`) and the dock mode uses it. Handles are `display:none` by default and shown only in the wide block, so hidden = inert (a `display:none` element is neither focusable nor hittable).
**Why:** one constant, no per-attach `matchMedia`; a viewport strictly between 900 and 901 px (analysis L8) then counts as "not wide" everywhere in T-037 code instead of half-wide.
**Rejected:** a `max-width: 900px` JS constant (a third copy of the cliff beside `agents.js:112,1498,1501`); editing `agents.js`' duplicates (out of scope; noted as a follow-up).

## D-3 — Sizes are written as `--sp-*` variables on the pane container and consumed only inside the wide query (analyst default)
**What:** JS writes `--sp-<name>` on the pane's own container (`.appshell`, `.ct-split`, `.vault`, `.lanes`, the dock). Existing rules consume them as `var(--sp-x, <today's value>)` only inside `@media (min-width: 901px)`. Never on `<html>`; never an inline `grid-template-columns` (it would beat the `<=900px` `1fr` at `styles.css:2006`).
**Why:** analysis N6 plus red-team CR-4: writing the existing `--vault-side` on `.vault` would also override the `:root` trim at <=900 (`styles.css:2024`). With a separate `--sp-*` name consumed only when wide, computed widths at <=900 are identical with or without a stored `layout`, which is testable (CSS text) and observable.
**Rejected:** reusing `--vault-side`/`--lane-w` as the written variable (overrides the media trims); a `matchMedia` listener in JS that adds/removes inline values (second source of truth for the cliff).

## D-4 — `layout` shape, validation, write rule (analyst default)
**What:** one object through `C.prefs` only: `{ v: 1, agents: {list, rail, railOff}, vault: {side, viewer, sideOff}, board: {lane}, dock: {w} }`, widths in integer px. Reads happen when a surface is built, never at script load. A write is read-modify-write of the whole object (T-036's `get` returns a clone): change one key, keep every other key including unknown ones. A non-object `layout`, or a non-finite, non-positive or non-number value, is ignored per key. The stored value is clamped when applied (build and window resize) and is **never** rewritten by a clamp; only a drag release, a keyboard step, a collapse/restore, a double-click or a Reset writes. Double-click deletes that key (default tracks the viewport again), it does not store the default.
**Why:** [[T-036-decision-log]] `t037-layout-contract` (key valid, 32 KB, `get` clone, `del("layout")` is the reset primitive); the Agents default is fluid (`clamp(208px,22vw,302px)`, `styles.css:841`), so a stored default would freeze it; closes G3-G5, CR-13.
**Rejected:** percentages (rounding, interact with minimums, T-036 already accepted px sharing as a risk); one key per handle in `C.prefs` (breaks the one-object-per-concern convention, `core.js:254-258`, and floods the Settings storage list).

## D-5 — Per-handle defaults, minimums, maximums (analyst default, ⚠ [unrealistic?] until seen in a browser)
**What:** see the table in the requirements (FR-5b). Defaults are today's CSS values; the flexible pane has its own minimum and bounds the dragged pane's maximum, so panes never overlap (G8). Vault stage minimum is 200 px because today's default at 901 px with the viewer open already leaves 239 px (snapshot §5).
**Why:** G2; arithmetic from `styles.css:841,938-941,1577-1578,78,1680`.
**Rejected:** one global minimum (the panes have different jobs); a minimum for the transcript above 320 px (breaks today's 901 px layout).

## D-6 — Collapse applies to three handles only (analyst default)
**What:** Agents list (reuses `setListShown`, one fact, one place), Agents rail, Vault sidebar. Not the Vault viewer (the X button closes it), the dock (X / Esc closes it), or the lane width. A collapsed rail or sidebar leaves its handle visible at the container edge as the restore affordance; click, Enter or double-click restores to the last width (G19, CR-10).
**Why:** a collapse needs one state and one way back; only these three panes have optional content.
**Rejected:** snap-collapse on every handle (a lane width of 0 or a closed dock by dragging is a surprise, not a feature).

## D-7 — Lane width: a handle on every non-cold lane's trailing edge, one global width (analyst default)
**What:** `--sp-lane` is written on `.lanes`. Every non-cold lane carries a handle on its trailing edge; the pointer delta is divided by that lane's ordinal among non-cold lanes so the edge stays under the pointer (the edge of lane k moves k times the width change); only the first handle is in the tab order and carries the ARIA value, the others are pointer-only and `aria-hidden`. The cold lane (52 px, `styles.css:699-702`) has none. The 1280 px trim and the 720 px bypass stay; the stored width applies in the wide block only.
**Why:** G9/CR-5: `.lanes` scrolls sideways (`styles.css:685`), so a single handle on lane 1 can be scrolled out of reach.
**Rejected:** one handle on lane 1 (scrolls away); per-lane widths (user decision: out); a slider in `.boardbar` (not VS Code-like).

## D-8 — Dock structure is a planning choice, bounded by acceptance criteria (analyst default)
**What:** requirements fix behaviour, not markup: the panel's top edge equals the topbar's bottom edge at every viewport height (including the `max-height:680px` trims, `styles.css:2075`); `main#view` keeps its element and id and shrinks; the same `aside` serves modal and docked modes so the body node survives a live mode switch. Design hint (non-binding): make `#app` a two-column grid in dock mode (`.topbar` spans both, the panel takes column 2), driven by `--sp-dock` on `#app`, which needs no topbar-height arithmetic.
**Why:** the panel changes page structure (analysis N7); overspecifying markup in a requirements document would pre-empt the planner.
**Rejected:** `position: fixed` with a hand-computed top offset (breaks when the topbar height changes); moving the panel inside `main#view` (then it scrolls with the page).

## D-9 — Refresh in place swaps in a new body node (analyst default; closes CR-1/G6)
**What:** a second `open()` while a panel is open keeps the same panel element, width, scroll position of the page and original focus-restore target, updates title/subtitle, replaces the `.dbody` with a **new** node and returns it, so a late `C.load` callback from the previous call paints into a detached node (as today). No `slidein` replay.
**Why:** `openTicket` is re-called five times to refresh (`board.js:412,416,419,420,458`) and `C.load` is asynchronous (`board.js:301`); reusing one node would let a stale response overwrite a newer one.
**Rejected:** clearing and reusing the same body node; keeping close+open (replays the animation, steals and re-captures focus, analysis N9).

## D-10 — Esc keeps today's semantics in both modes (analyst default; closes CR-12/G12)
**What:** modal mode: unchanged (document-level Esc closes). Docked mode: Esc closes only when the event target is inside the panel; Esc elsewhere (board search, a card, the topbar) does nothing to the panel. An Esc inside a drawer field still reverts that field and closes the panel (`board.js:333`, N8): not changed, not hidden.
**Why:** the brief asks for "only when focus is inside"; changing the field-revert behaviour is separate scope with its own regression risk.
**Rejected:** making the first Esc revert only (needs a handler order contract with `board.js` and a second Esc after blur, where focus is on `<body>`, would not be "inside").

## D-11 — Vault canvas resize is deferred by a flag, not removed (analyst default)
**What:** while a Vault pane drag is active, `resize()` returns early (module flag in `vault.js`); on release the flag is cleared and `resize()` runs once. The three `setTimeout(resize, 60)` calls (`vault.js:507,515,530`) stay untouched.
**Why:** N5: the `ResizeObserver` (`vault.js:450-452`) would reallocate both canvases per frame; the canvases keep their pre-drag pixel size during the drag (frozen, clipped by `.vault-stage` when it shrinks, blank strip when it grows; `resize()` writes inline px `style.width/height`, `vault.js:244-245`) and are crisp after the single `resize()` on release. *Amended 2026-10-05, see Amendment below.*
**Rejected:** dropping the observer or the timeouts (refactor outside scope); a ghost-line-only drag (less VS Code-like).

## D-12 — Which sections fold, and how (analyst default)
**What:** Overview `ov.glance`, `ov.attention`, `ov.flow`, `ov.recent`, `ov.jobs`, `ov.schedules`; Assistant home `as.talk`, `as.runs`, `as.tickets`; Agents rail `ag.budget`, `ag.plan`, `ag.todos`, `ag.files`, `ag.queued`; Vault cards `vault.filters`, `vault.display`, `vault.forces`, `vault.navigator`. Ids are literals (never derived from a title that carries a count). Defaults preserve today's look: all open except `vault.display` and `vault.forces` (closed, `vault.js:34-35`). Overview and Assistant use `C.panel(..., {collapse})`. The Agents rail uses `C.group(title, kids, {id, open})` (exported, quiet h4 look, same contract), because `collapsible()` is not exported and exporting it means editing `core.js` (T-036's file). Vault cards keep their own DOM (`.vault-card`) and move their state from `st.openCards` to the `panelOpen` map, set on toggle and read at build.
**Why:** `panelOpen` is one flat map (`core.js:261`), so ids must be globally unique (analysis N11); the three surfaces already look different from `.panel`.
Each rail section also keeps the class `ct-panel` (added to the `C.group` node) so `.ct-rail > .ct-panel` at <=900 px (`styles.css:2020`) still lays the rail out as a sideways strip (CR-21). The docked ticket panel carries `role="complementary"` (not `dialog`/`aria-modal`), flipped with the mode on a live switch (CR-24).
**Rejected:** exporting `collapsible` from `core.js` (T-036 hunk collision); building a second fold primitive in `splitter.js` (two sources of one behaviour).
**Getting-started card (`ov.onboarding`):** left on its own fold (`onboardingOpen`, `overview.js:50,87-102`); a second fold would duplicate it and its title changes (analysis N3). Analytics, Work, About: out, opt-in later, one line each.

## D-13 — Collapse all / Expand all (analyst default)
**What:** one helper in `splitter.js` (`C.splitter.foldBar(host)` returns the two-button control; its handlers query `[data-panel-id]` under `host` at click time and call `_setOpen`). Placed on Overview and Assistant home only. Not on the Agents rail (five transient sections rebuilt per meta event), not on Vault (four cards in a 262 px column). `settings.js` `jumpBar()` is not refactored (CR-15).
**Why:** Overview adds panels asynchronously and two remove themselves when empty (`overview.js:185,208`), so a build-time list would be stale (analysis N10).
**Rejected:** adding the helper to `core.js` (T-036); migrating Settings to it (scope creep).

## D-14 — Overview "Needs attention" Enter guard (analyst default)
**What:** the key handler (`overview.js:303-317`) ignores events whose target is inside the panel `<header>` and returns early while the panel is collapsed.
**Why:** analysis N2: Enter on the new collapse header would otherwise toggle and also click a row (navigate); a collapsed panel's hidden rows would still be clicked by Enter on the panel itself.

## D-15 — Reset layout: scope and live apply (analyst default; closes CR-8/G10, G3)
**What:** a `layoutPanel()` function in `settings.js` with one `kids.push(layoutPanel())` line placed beside `storage()`. It clears exactly `layout`, `panelOpen` and `chatListHidden`; not `onboardingOpen`, `hiddenTabs`, theme or anything else. Live apply without reload: `splitter.js` keeps a registry of live instances (pruned when a host is disconnected) and `C.splitter.reapplyAll()` re-reads prefs; the folds are re-read by re-rendering the active tab through the existing `ConsoleApp.go(active)` (`app.js:382`); an open dock is re-applied by the same registry. A toast confirms.
**Why:** folds are part of "layout" in VS Code terms and are what the user will expect to reset; `chatListHidden` is the Agents list pane state; `go()` already re-reads every pref (analysis Current State, re-render model).
**Rejected:** clearing all prefs (that is T-036's "Reset all preferences"); a live-subscribe event on `C.prefs` (editing `core.js`).

## D-16 — "Reset all preferences" is a cross-ticket acceptance check (analyst default)
**What:** T-036 owns that button. T-037 requires only that, after it runs, the live layout is back to defaults without a page reload (the same `reapplyAll()` and active-tab re-render), and records this as an acceptance check to run once both tickets are in. T-037 does not edit T-036's `storage()` code.
**Why:** [[T-036-decision-log]] `t037-layout-contract` and `settings-reset-wording`; one owner per code area.

## D-17 — `palette.js:103` is out of scope; a bug is logged (analyst default)
**What:** `showResult()` calls `app.drawer(...)` as a function; `drawer` is `{open, close}` (`app.js:52,382`). Not fixed here. Logged with the `bugs` skill as bug `D-1` in `T-037-bugs.toml` (medium, open; not to be confused with decision D-1 here).
**Why:** by reading only, not executed; unrelated to layout; fixing it would add a second drawer opener, changing FR-10's "single opener" premise.

## D-18 — Tab switch closes the dock (analyst default)
**What:** unchanged `go()` behaviour (`app.js:128`), including the `r` key and the refresh button. Consequence: the dock exists only on board tabs, so it never coexists with the Agents or Vault splitters.
**Rejected:** keeping the panel across tabs (it shows a board ticket on a tab that has no board).

## D-19 — Global listeners installed once, registry pruned (analyst default; closes CR-11/G11)
**What:** the window `resize` listener, the document keydown for the dock and the wide-query `change` listener are installed lazily, once, by `splitter.js`/the drawer IIFE, never per `attach`; the instance registry drops entries whose host is no longer connected on every `attach`, `resize` and `reapplyAll`. A drag whose handle is removed mid-way ends cleanly (G7).
**Why:** the board repaints per search keystroke (`board.js:245-290,555`), so per-attach listeners would pile up.

## D-20 — Verification strategy and baseline (analyst default; closes CR-3/CR-16/CR-17)
**What:** Python source-regexp tests carry what is checkable from text (list in the requirements § 15); everything else is **[BROWSER]** with a viewport and an expected measurement, labelled "not verified in a browser" until the parent session runs it. The baseline is compared by failing test id (`test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count`), not by counts, because another ticket may fix it first. There is no JS runner and none is added.
**Why:** harness evidence rule (cited evidence for every "done"); analysis N12.

## D-21 — File-collision rules (analyst default; closes G18)
**What:** `styles.css`: one `.sp-*` block mid-file beside `.split` (`styles.css:825-827`), plus in-place edits to the existing bare rules (`.appshell`, `.ct-split`, `.lane`, `.vault`, `.drawer`, print) and additions to the existing wide media block; nothing appended at the end, the `.ob-*` lines and the line-2129 `.ob-scrim` edit are not touched. `index.html`: one tag after `core.js`. `app.js`: only the `drawer` IIFE (`:14-53`) and an appended export member if needed; the three other-ticket hunks (`:346`, `:371-381`, `:383`) untouched. `settings.js`: one function and one push line. `core.js`: not edited. No commit, no stash, no reformat.
**Why:** analysis Constraints 1-2; BR-6.

## D-22 — Rollback (analyst default)
**What:** additive. Remove the `splitter.js` tag and file, revert the per-surface hunks; a stored `layout` is inert (unknown keys are preserved by T-036).

## D-23 — Handle stacking and drag side effects (analyst default; closes CR-14/CR-20)
**What:** `.sp` z-index 8 (above `.list-reveal` 6 and `.secnav` 5, below the topbar 20 and the drawer 41). During a drag `splitter.js` toggles a class on `document.body` that sets `user-select: none` and `cursor`, and a transparent overlay is not needed because capture retargets events; the class is removed in every end path.
**Why:** `styles.css:284,598,869,1679`; a class (not an inline style on `<html>`) keeps D-3 intact.

## Amendment 2026-10-05 — D-11 rationale corrected (evolve; trigger: discovery, [[T-037-critique-report]] CR-37)
**Before:** D-11 Why said the canvases "stretch via CSS during the drag and are crisp after release".
**After:** they are frozen at their pre-drag size during the drag, because `resize()` sets inline px `style.width/height` (`vault.js:244-245`) and the deferral flag skips it; one `resize()` on release makes them crisp. The decision itself (defer `resize()` with a module flag, keep the observer and the three timeouts) is unchanged.
**Requirements impact:** none. FR-8 and AC-8.1..8.4 stand (AC-8.3 asserts zero canvas reallocations during the drag and one after release, which this behaviour satisfies). Visual consequence to accept or reject in the browser: clipped or blank canvas edge during a Vault drag (the "ghost-line-only" alternative was already rejected as less VS Code-like).
**Cascade:** [[T-037-task-breakdown]] T-037-09 and checklist B-3 should say "frozen, not stretched, during the drag" (builder note / verifier wording); no plan task, estimate or AC changes. Reconcile run: see [[T-037-progress]].

## D-24 — Drawer opener line drift in frozen artifacts (verifier finding F-4, 2026-10-06)
**What:** the frozen [[T-037-requirements]] and [[T-037-plan]] cite the single drawer opener as `board.js:300`; it is now `console/static/board.js:317` (other tickets edited `board.js`). Frozen files are not edited; read every `board.js:300` there as `board.js:317`. Behaviour unchanged: `test_p10_drawer_export_shape_single_opener` is green.

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-context-snapshot]] · [[T-037-requirements-draft]] · [[T-037-requirements]] · [[T-037-gap-analysis]] · [[T-037-critique-report]] · [[T-037-iteration-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
