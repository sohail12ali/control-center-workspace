---
ticket: "T-037"
artifact: requirements
status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 2
---

# Requirements: T-037 — Resizable layout: draggable splitters, docked ticket panel, expandable sections

**Frozen:** 2026-10-05 · iteration 2 · source of truth for planning. Full wording and rationale: [[T-037-requirements-draft]]; history: [[T-037-iteration-log]]; decisions: [[T-037-decision-log]] (D-1..D-23); findings: [[T-037-critique-report]] (CR-1..CR-24); gaps: [[T-037-gap-analysis]] (G1-G30). Post-freeze changes go through `evolve`. Grounding: [[T-037-analysis]], [[T-037-context-snapshot]].

## Intent

A VS Code-like console: pane borders you can drag, sections you can fold, layout changes that are easy to make. User request 2026-10-05, verbatim: "more responsive, VS Code-like UI — expand sections and layout modifications easily done, able to move the layout borders like we do in VS Code". User decisions: splitters on all four surfaces (Agents panes, Vault panes, ticket detail as a docked resizable panel, board lane width); build alongside [[T-031-summary]].

## Scope

**In:** reusable splitter component (`console/static/splitter.js`, `.sp-*` CSS mid-file); one `layout` pref through `C.prefs`; wide-only behaviour at the 900/901 px cliff; Agents list|main and transcript|rail; Vault sidebar|canvas|viewer; docked ticket panel; one global lane width; foldable sections on Overview, Assistant home, Agents rail, Vault cards; Collapse all / Expand all on Overview and Assistant home; Reset layout in Settings; cross-ticket acceptance check for "Reset all preferences".

**Out (explicit):** per-lane widths; Analytics/Work/About sections (opt-in later, one line each); fixing `palette.js:103` (logged as bug `D-1`, `T-037-bugs.toml`) and the baseline `.ob-count` test failure; changing the `C.prefs` implementation or `core.js` (T-036); Tauri/Rust; vertical splitters; user-defined layouts/presets; drag-to-rearrange; editing the `agents.js` copies of the 900 px cliff; refactoring Settings `jumpBar()`; changing Esc-in-a-drawer-field behaviour.

**Open (non-blocking):** Q1 (dock replaces overlay on wide screens vs opt-in) stays open, medium. FR-10 takes the default. `⚠ accepted: default pending user confirmation of Q1`; the alternative is a one-function change (`dockMode()`, D-1).

**Constraints carried from the analysis:** no dependency, no build step, ES5 IIFE on `window.Console`, `C.el` DOM, no innerHTML templates, colours via tokens; CSS added mid-file (never appended); never revert, stash, reformat or stage other tickets' uncommitted hunks (`app.js:346,371-383`, `index.html:72`, `overview.js:122-127`, `settings.js` four hunks, `styles.css` `.ob-*` block and the `:2129` print edit); re-Read before every Edit; no commit.

Verification tags: **[PY]** pytest source-regexp (no JS runner exists) · **[BROWSER]** needs a real browser at the stated viewport: *not verified in a browser* until the parent session runs it.

## Functional Requirements

1. **FR-1 Splitter component.** `C.splitter(opts)` plus `WIDE`, `reapplyAll()`, `foldBar(host)`; handle is an overlay on the border (no grid track, no width change), `role="separator"` with APG ARIA, outside clipping ancestors.
   - [ ] AC-1.1 [PY] script order `core.js` < `splitter.js` < `app.js`, away from the onboarding tag.
   - [ ] AC-1.2 [PY] ARIA attributes in source; `aria-controls` ids assigned when absent.
   - [ ] AC-1.3 [PY] classes exist in `styles.css`; `.sp-*` mid-file, not at the end; no repeated bare class.
   - [ ] AC-1.4 [PY] `.sp` z-index 8 (< topbar 20).
   - [ ] AC-1.5 [PY] no `=>`, `let `, `const `, backtick, `innerHTML`, `localStorage`, `draggable`, `dragstart` in `splitter.js`.
   - [ ] AC-1.6 [BROWSER ~1400] hit area 6 px (20 px coarse), `col-resize`, token highlights; adjacent pane widths identical with and without the handle. ⚠ numbers proposed.
2. **FR-2 Pointer drag.** Pointer Events, capture, rAF-coalesced writes, end on up/cancel/lostpointercapture, body drag class always removed, `touch-action`, never in `.brandrow`.
   - [ ] AC-2.1 [PY] capture, cancel, lostpointercapture, rAF, class removal. AC-2.2 [PY] `touch-action`; nothing attached to `.brandrow`.
   - [ ] AC-2.3 [BROWSER ~1400] drag across the Vault canvas keeps going, no text selected. AC-2.4 [BROWSER ~1000 touch] finger drag works, no sideways page scroll.
   - [ ] AC-2.5 [BROWSER] board repaint mid-drag: no error, no stuck class, last valid width kept. AC-2.6 [BROWSER Tauri/Windows] drag works, window does not move (macOS/Linux not verified).
3. **FR-3 Keyboard, collapse, reset.** Arrows 16 px (Shift 64), Home/End min/max, Enter toggles collapse where allowed, double-click deletes the key, collapse below half the minimum, restore to last width. ⚠ proposed numbers.
   - [ ] AC-3.1 [PY] keys and `dblclick` in source. AC-3.2 [BROWSER ~1400] Tab to handle, 3x ArrowRight = +48 px, `aria-valuenow` follows, focus ring.
   - [ ] AC-3.3 [BROWSER] double-click returns to default and the key is gone from storage. AC-3.4 [BROWSER] rail dragged below 100 px collapses; Enter restores.
4. **FR-4 Persistence.** One `layout` object via `C.prefs` only; read at build, never at load; one write per completed gesture, never per pointer-move; read-modify-write keeping unknown keys; clamp at apply and on resize without rewriting the stored value; listeners installed once, registry pruned.
   - [ ] AC-4.1 [PY] no top-level prefs call; `prefs.set(` only in one helper that reads `layout` first. AC-4.2 [PY] install-once `resize` listener, `isConnected` pruning.
   - [ ] AC-4.3 [BROWSER] one drag = one write; click without move = none; reload restores. AC-4.4 [BROWSER ~1000] stored 2000 shows clamped, stored value unchanged, larger window shows it again.
   - [ ] AC-4.5 [BROWSER] invalid `layout` (string, null, bad member) renders defaults, no error.
5. **FR-5 Wide only, pane table.** Handles `display:none` by default, shown only in `@media (min-width: 901px)`; sizes are `--sp-*` on the pane container, consumed only in that block; at <=900 px computed widths are identical with or without `layout`; no `<html>` variable, no inline `grid-template-columns`, no `transition` on it.

   | Handle | Default | Min | Max | Collapse |
   |---|---|---|---|---|
   | `agents.list` | `clamp(208px,22vw,302px)` | 180 | 480, transcript >= 320 | yes via `setListShown` |
   | `agents.rail` | 260 | 200 | 520, transcript >= 320 | yes `railOff` |
   | `vault.side` | 262 | 200 | 480, stage >= 200 | yes `sideOff` |
   | `vault.viewer` | 400 | 280 | 720, stage >= 200 | no |
   | `board.lane` | 270 (252 <=1280) | 200 | 480 | no |
   | `dock.w` | 430 | 320 | 720, `main#view` >= 360 | no |

   - [ ] AC-5.1 [PY] `.sp` hidden by default, shown only in the wide block. AC-5.2 [PY] `901px` once in `splitter.js`, no `max-width: 900px`.
   - [ ] AC-5.3 [PY] every `var(--sp-` inside `@media (min-width: 901px)`; no `documentElement.style`/`gridTemplateColumns` in JS. AC-5.4 [PY] no `transition` on `grid-template-columns`; `min-width:0`/`min-height:0` kept.
   - [ ] AC-5.5 [BROWSER 900/901/~800] none visible or tabbable at 900; work at 901; stored layout changes nothing at ~800. AC-5.6 [BROWSER ~1400] each row drags to its min and max, not beyond. ⚠ numbers proposed.
6. **FR-6 Agents list | main.** Handle on `.appshell`, `--sp-list`; collapse reuses `setListShown`/`chatListHidden`; handle not rendered while folded, `.list-reveal` restores, focus moves to it.
   - [ ] AC-6.1 [PY] collapse calls `setListShown`; no new flag. AC-6.2 [PY] `var(--sp-list` with the clamp fallback in the wide block. AC-6.3 [BROWSER ~1400] drag to 300/180, fold below 90, restore, reload keeps width.
7. **FR-7 Agents transcript | rail.** Attached in `mountChat` as a child of `.ct-split` (not `#ctRail`), `--sp-rail`; collapsed rail keeps its handle as restore.
   - [ ] AC-7.1 [PY] attach in `mountChat`, appended to `.ct-split`. AC-7.2 [BROWSER ~1400] streaming `meta` repaints do not interrupt a drag; width kept across chats. AC-7.3 [BROWSER] restore by click/Enter/dbl-click; ~800 px unchanged.
8. **FR-8 Vault.** Two handles on `.vault`, viewer handle only with `.has-viewer`; `resize()` guarded by a drag flag, one call after release.
   - [ ] AC-8.1 [PY] flag around `resize()`. AC-8.2 [PY] handles appended to `.vault`, not `.vault-stage`.
   - [ ] AC-8.3 [BROWSER ~1400] canvas `width`/`height` setter spy: zero reallocations in a 2 s drag, one after release, crisp. AC-8.4 [BROWSER 901] viewer drag stops where the stage is 200 px.
9. **FR-9 Board lane width.** One global `--sp-lane` on `.lanes`; handle on every non-cold lane's trailing edge with pointer delta / ordinal; only the first in tab order; cold lane none; 1280 trim and 720 bypass unchanged for users with no stored width.
   - [ ] AC-9.1 [PY] `--sp-lane` on `.lanes`, consumed in the wide block. AC-9.2 [BROWSER ~1400] lane 3 edge stays within 2 px of the pointer; lanes equal; cold lane 52 px. AC-9.3 [BROWSER] repaint and "Show more" keep width; only the first handle is tabbable.
10. **FR-10 Docked ticket panel.** `dockMode()` true (wide): docked, no scrim, `role="complementary"`, top edge = topbar bottom edge, `main#view` shrinks, width `dock.w` with left-edge handle; else today's modal. `open()` returns the body node, `{open, close}` unchanged, `board.js:300` the only opener. ⚠ accepted: default pending user confirmation of Q1.
    - [ ] AC-10.1 [PY] exported shape; `drawer.open(` only in `board.js`. AC-10.2 [PY] one `dockMode()` using `C.splitter.WIDE`; both role values, flipped on mode switch.
    - [ ] AC-10.3 [BROWSER ~1400, 1400x600] panel beside board, no scrim, topbar clickable, tops touch. AC-10.4 [BROWSER ~800, ~400] scrim, modal, full width at 400.
    - [ ] AC-10.5 [BROWSER 1280/1400] sideways scroll about 286/238 px (computed) is accepted. AC-10.6 [BROWSER] clamp 320/720 and `main#view` >= 360; width survives reload.
11. **FR-11 Dock behaviour.** One panel; initial focus on Close and restore to opener; Esc docked only when the target is inside (modal unchanged; Esc in a field still reverts and closes); tab switch, `r`, refresh close it; repeat `open()` refreshes in place with a **new** `.dbody` returned; live mode switch at 901 keeps the node and edits; hidden in print with no leftover column.
    - [ ] AC-11.1 [PY] fresh `.dbody` on repeat open; listeners once. AC-11.2 [PY] print block covers the dock and its `#app` layout.
    - [ ] AC-11.3 [BROWSER] Esc rules. AC-11.4 [BROWSER] Owner edit refresh: no slide-in, same width/focus, two rapid refreshes never show older content.
    - [ ] AC-11.5 [BROWSER] 1400↔800 with a half-typed field: modal then docked, value survives. AC-11.6 [BROWSER] print preview: no panel, no empty column.
12. **FR-12 Foldable sections.** 18 literal ids in `panelOpen` (`ov.glance|attention|flow|recent|jobs|schedules`, `as.talk|runs|tickets`, `ag.budget|plan|todos|files|queued`, `vault.filters|display|forces|navigator`; defaults open except `vault.display`, `vault.forces`); Overview/Assistant via `C.panel`, Agents rail via `C.group` keeping `ct-panel`, Vault cards keep their DOM and move state to `panelOpen`; Getting-started keeps its own fold; Overview Enter handler ignores header targets and collapsed state.
    - [ ] AC-12.1 [PY] each id once in its file, none across files. AC-12.2 [PY] guard, `panelOpen` in `vault.js`, `C.group` + `ct-panel` in the rail. AC-12.3 evidence: no T-037 hunk in `core.js`, other tickets' hunks intact.
    - [ ] AC-12.4 [BROWSER ~1400] folds survive tab switch, reload, rail repaints. AC-12.5 [BROWSER] Enter on the header folds without navigating; Enter on the body still opens a row; collapsed panel shows only its header. AC-12.6 [BROWSER ~400] folds by touch; rail strip scrolls.
13. **FR-13 Collapse all / Expand all.** `foldBar(host)` queries `[data-panel-id]` at click time; first row, right-aligned, Overview and Assistant home only.
    - [ ] AC-13.1 [PY] query inside the handler; no `foldBar` in `settings.js`. AC-13.2 [BROWSER] async Jobs/Scheduled included; Settings' own buttons still work.
14. **FR-14 Reset layout.** `layoutPanel()` in `settings.js`, one new `kids.push` line beside `storage()`; deletes `layout`, `panelOpen`, `chatListHidden`; `reapplyAll()` + `ConsoleApp.go(active)`; toast; page returns to top (accepted, CR-23).
    - [ ] AC-14.1 [PY] one function, one added push, other hunks unchanged. AC-14.2 [PY] three `C.prefs.del`, no `localStorage`, no `C.prefs.reset`. AC-14.3 [BROWSER ~1400] defaults restored without reload; theme and hidden tabs unchanged.
15. **FR-15 "Reset all preferences" resets the live layout** (cross-ticket check; T-036 owns the button).
    - [ ] AC-15.1 [BROWSER, after T-036 lands] defaults without reload; stays "not verified" until then. AC-15.2 [PY] `reapplyAll` exposed; T-037 code does not depend on `C.prefs.reset`.

## Non-Functional Requirements

| Category | Requirement | Target |
|---|---|---|
| Performance | drag cost | at most one style write per frame; zero Vault canvas reallocations during a drag, one after (call counts) ⚠ proposed |
| Performance | prefs writes | exactly one `layout` write per completed gesture; none per pointer-move or click without movement |
| Compatibility | stack | no dependency/build step, ES5, `C.el`, no innerHTML templates, tokens only |
| Compatibility | tests | no new failing test id; only red is `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count` (baseline 1 failed / 2273 passed), compared by id |
| Usability | accessibility, touch | APG keys/ARIA, visible focus ring, accessible names; 20 px coarse hit area ⚠ proposed |
| Maintainability | one fact, one place | one wide-query constant; `chatListHidden` the only list-fold flag; one `layout` object |
| Compliance | print, motion | dock and handles hidden in print; no size transitions; global reduced-motion honoured |
| Security / Auth, Auditability, Scalability | N/A | client-only state, no endpoint, no HTML injection; prefs not audited; at most 8 handles per page |
| Availability | export, local mode | `splitter.js` ships via the export glob; prefs fall back to local mode |

## Data entities

| Entity | Source | Shape / lifecycle | Reference |
|---|---|---|---|
| `layout` | new `C.prefs` key | `{v:1, agents:{list,rail,railOff}, vault:{side,viewer,sideOff}, board:{lane}, dock:{w}}`; integer px; written per gesture; deleted by Reset or per-key double-click | D-4, [[T-036-decision-log]] `t037-layout-contract` |
| `panelOpen` | exists | `{id: bool}`; read per build, written per toggle; deleted by Reset layout | `core.js:254-298` |
| `chatListHidden` | exists | bool; deleted by Reset layout | `agents.js:132` |

## Business rules

BR-1 one global lane width · BR-2 a clamp never rewrites the stored value · BR-3 at <=900 px structural CSS applies, no stored size does · BR-4 one ticket panel at a time · BR-5 section ids globally unique · BR-6 other tickets' hunks untouched · BR-7 Reset and double-click delete keys, never write defaults · BR-8 only `C.prefs` touches storage, never edited by T-037 · BR-9 collapse state is one fact (`chatListHidden` for the list, `layout` for rail/sidebar) · BR-10 hidden means inert.

## Edge cases

Invalid `layout` → defaults · window narrower than the minimums → dragged pane at minimum, flexible pane shrinks, no overlap · handle removed mid-drag → clean end · board with no non-cold lane → no lane handle · no viewer or empty vault → viewer handle absent · stored width above the maximum → clamped, stored untouched · two rapid dock refreshes → newest wins · 900.5 px counts as not wide · print with the dock open.

## Test plan

Python (`console/tests/test_splitter.py`, source-regexp): P-1 script order · P-2 ES5/hygiene · P-3 ARIA/keys · P-4 pointer API · P-5 prefs write helper · P-6 listeners once · P-7 `.sp` CSS · P-8 `--sp-` consumption and no grid transition · P-9 `901px` once · P-10 drawer contract, print · P-11 section ids/guard/Vault/rail · P-12 per-surface attach points, vault flag, lane variable · P-13 `foldBar` · P-14 Settings one function/one push · P-15 existing stylesheet/plugin tests. [BROWSER] B-1..B-13 (viewport matrix and checks in the draft § 15). Evidence outside pytest: `git diff` shows no T-037 hunk in `core.js` and other tickets' hunks intact.

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-context-snapshot]] · [[T-037-requirements-draft]] · [[T-037-gap-analysis]] · [[T-037-critique-report]] · [[T-037-iteration-log]] · [[T-037-decision-log]] · [[T-037-user-stories]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
