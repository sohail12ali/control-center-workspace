---
tags: [active]
status: Open
ticket: "T-037"
---

# T-037: Resizable layout: draggable splitters, docked ticket panel, expandable sections

**Status:** Open  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

The user asked on 2026-10-05 for a more responsive, VS Code-like layout: draggable pane borders, expandable sections, layout changes that are easy to make.

**Decisions (user, 2026-10-05):** splitters on **all four** surfaces below; build **alongside** T-031.

Scope:
1. **A reusable splitter component** (new `console/static/splitter.js`, `.sp-*` CSS): pointer drag with capture, double-click to reset, keyboard (`role="separator"`, arrow keys, `aria-valuenow`), min/max, collapse when dragged past the minimum, touch-safe. Sizes persist through `C.prefs` as one `layout` object (convention: one object per concern, `core.js:256-258`).
2. **Agents panes:** chat list | transcript (`.appshell`, `styles.css:839-843`, `clamp(208px,22vw,302px) 1fr`, existing fold `chatListHidden`) and transcript | right rail (`.ct-split`, `styles.css:938-941`, `minmax(0,1fr) 260px`).
3. **Vault panes:** sidebar | canvas | viewer (`.vault`, `styles.css:1585-1591`, driven by `--vault-side` 262px and `--vault-viewer` 400px — the model for a CSS-variable splitter).
4. **Ticket detail as a docked, resizable panel** instead of the modal overlay + scrim (`console/static/app.js:17-53`, `.drawer` `styles.css:1678`, `width:min(430px,100vw)`); the drawer is shared by every caller via `ConsoleApp.drawer.open`, so keep that API.
5. **Board lane width:** one draggable width for all lanes (`--lane-w` 270px, `styles.css:688-694`). Per-lane resizing is explicitly out.
6. **Expandable sections everywhere sections exist:** the collapse primitive (`C.panel(..., {collapse:{id,open}})`, `core.js:259-298`) is used only on Settings today; extend it to Overview, Assistant home, the Agents right rail and the Vault sidebar cards (open state currently in memory only, `vault.js:522-537`), with Collapse all / Expand all and persistence.
7. A **Reset layout** control, added as its own function next to the "Stored in this browser" panel so it does not collide with other edits to `settings.js`.

Constraints found: the structural responsive cliff is `max-width:900px` (`styles.css:1994-2034`) and is **duplicated in JS** (`agents.js:112`, `agents.js:1501`) — splitters must switch off at and below it, in step with both; keep `min-width:0` / `min-height:0` on nested flex/grid children; do **not** add a transition on `grid-template-columns` (`styles.css:1581-1584`); every pane-size state must live outside the tab DOM because each tab re-renders on `go()`; a splitter must not start a desktop window drag (`desktop-chrome.js:30-35` `isInteractive`).

## Current State

**GROUND analysis done 2026-10-05** ([[T-037-analysis]], [[T-037-context-snapshot]]): every lead below re-verified, 5 corrected (drawer has one opener not "every caller", a latent `palette.js:103` bug, window drag is bound to `.brandrow` only, unrelated drag code exists, fluid Agents list); Q1 (dock replaces overlay on wide screens?) open. Original inventory, now verified: no splitters, pointer-drag code or resize cursors exist anywhere; every pane width is a fixed CSS value; the `C.prefs` store is browser-local, so layout would differ between the app and a browser until [[T-036-summary]] lands.

**TEMPLATE slice S1a built 2026-10-05** (T-037-01..02, 2/20 tasks): `## C1 API contract` in [[T-037-components]] and the `.sp-*` CSS block + print block in `styles.css` (829-871) with `console/tests/test_splitter.py` (P-7, P-8 skeleton); Cmd S 1 failed (baseline `.ob-count`) / 29 passed. **S1b built 2026-10-05** (T-037-03, 3/20 tasks): `console/static/splitter.js` core (attach, ARIA, pointer, keys, collapse, `layout` write helper) + P-2..P-5, P-9; Cmd S 1 failed (baseline) / 34 passed; behaviour not browser-verified. **S1c built 2026-10-05** (T-037-04..05, 5/20 tasks, S1 complete): `splitter.js` gains registry pruning, install-once window listeners, `C.splitter.reapplyAll()` and `C.splitter.foldBar(host)`; `<script src="splitter.js">` added to `index.html` after `core.js`; P-1, P-6, P-13 added; Cmd S 1 failed (baseline `.ob-count`) / 37 passed; behaviour not browser-verified. **S2 built 2026-10-05** (T-037-06..08, 8/20 tasks): Agents list | main and transcript | rail handles attached in `agents.js` (`attachListSplitter`, a `C.splitter` call in `mountChat`), `--sp-list`/`--sp-rail` consumed in wide blocks of `styles.css`, the five rail sections now `C.group`s with `ag.*` ids and `ct-panel` kept; P-8/P-11/P-12 (agents) added; Cmd S 1 failed (baseline `.ob-count`) / 44 passed; behaviour not browser-verified. **S3 built 2026-10-05** (T-037-09..10, 10/20 tasks): Vault sidebar and viewer handles on `.vault` (`attachSideSplitter`, `attachViewerSplitter`/`detachViewerSplitter`), a drag flag that makes `resize()` wait and runs it once on release, `--sp-side`/`--sp-viewer` consumed in a second wide block after `.vault.has-viewer` (children pinned, folded sidebar = `.side-off`), and the four Vault cards now keep their state in `panelOpen` (`vault.*` ids, `st.openCards` gone); P-8 vault, P-11 vault, P-12 vault added; Cmd S 1 failed (baseline `.ob-count`) / 49 passed; behaviour not browser-verified. Next: S4 (T-037-11..12, board lane width). Lane moved to `in-progress`; detail in [[T-037-progress]].

**Current State (2026-10-06): VERIFY.** Build is 19/20 (S1a..S7b), SIMPLIFY done (nothing removed; one lane-handle `aria-valuenow` fix in `splitter.js`), lane `verify`. The verifier (read-only, no browser) recorded disposition `needs_human` in [[T-037-verification]]: **31 PASS / 34 not verified in a browser / 0 FAIL**; scoped suite 1 failed (baseline `.ob-count`) / 67 passed, full suite 1 failed / 2877 passed (same baseline id, no new red id). Q1 (dock replaces overlay on wide screens vs opt-in) is open as `accepted: default pending user confirmation`. T-037-20 stays open: the parent's partial browser run is not a pass, the Tauri/touch/print and remaining [BROWSER] rows are pending, and the stale `claimed_by = builder` claim must be released or refreshed before close-check. Not run: `close-work`. Detail in [[T-037-progress]].

**Conflict map (uncommitted work by other tickets, do not clobber):** `app.js` (3 hunks: boot-time `ConsoleOnboarding.maybeOpen`, `setTitle`, export object), `index.html` (the `onboarding-wizard.js` script tag), `overview.js` (an Open-setup button), `settings.js` (+90: `identity()` panel, storage-panel row, `render()` push), `styles.css` (+80 `.ob-*` lines appended at the END of the file). Rules for this ticket: add CSS in the middle of `styles.css` next to the related rules, never at the end; add the `splitter.js` tag after `core.js`/`icons.js`, away from the onboarding tag; append to the `ConsoleApp` export rather than rewriting it.

**Test constraints** (`console/tests/test_stylesheet.py`, `test_plugins.py:227-260`): no bare single-class selector defined twice (only `.card`); every hyphenated class used from JS must appear in `styles.css`; script order `core < palette < app`. There is no JS test runner, so verification is Python source-regexp tests plus real browser checks at ~400, ~800 and ~1400 px, and a check inside the Tauri webview (pointer capture there is unverified).

## Links
- Depends on: [[T-036-summary]] (preference store) · Related: [[T-031-summary]] (also edits `settings.js` and `styles.css`) · [[T-030-summary]] (one chat surface)
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-test-cases]] · [[T-037-verification]]
