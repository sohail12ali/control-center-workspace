---
ticket: "T-037"
artifact: user-stories
created: "2026-10-05"
---

# User Stories: T-037

Stories for the frozen requirements ([[T-037-requirements]], iteration 2). Each story **references** its acceptance criteria by id (AC-n.m, full wording in the requirements) instead of copying them; BR-n and edge cases are also by reference. Verification tags: **[PY]** pytest source-regexp, **[BROWSER]** needs a real browser (not verified until the parent session runs it). Dock default is **⚠ accepted pending Q1** ([[T-037-decision-log]] D-1).

**Created by:** `requirements T-037 stories` · **Validated by:** `validate-artifacts T-037 links` · **Verified by:** `validate-artifacts T-037 links`

Components C1..C11 are defined in [[T-037-components]]. Tasks come from [[T-037-task-breakdown]] and are filled in below (T-037-20 verifies every story's [BROWSER] ACs).

## Stories

### US-1: Drag a pane border (FR-1, FR-2)

**As a** console user on a wide screen
**I want to** drag the border between two panes with a mouse or a finger
**So that** I can give the pane I am working in more room, as in VS Code

**Acceptance Criteria:** AC-1.1..AC-1.6 (splitter component, ARIA, `.sp-*` CSS, z-order, ES5 hygiene, hit area) · AC-2.1..AC-2.6 (pointer capture, rAF writes, clean end, touch, mid-drag repaint, Tauri/Windows)
**Business Rules:** BR-10 (hidden means inert)
**Edge Cases:** handle removed mid-drag ends cleanly; board repaint mid-drag keeps the last valid width
**Related Components:** C1, C2, C3, C11
**Related Tasks:** T-037-01..05
**Priority:** High · **Story Points:** 5

---

### US-2: Resize and collapse with the keyboard, undo with a double-click (FR-3)

**As a** keyboard or assistive-technology user
**I want to** move any pane border with the arrow keys, jump with Home/End, collapse with Enter, and reset with a double-click
**So that** every size is reachable without a pointer and any one size is easy to undo

**Acceptance Criteria:** AC-3.1..AC-3.4
**Business Rules:** BR-7 (reset deletes the key, never writes the default)
**Edge Cases:** collapse below half the minimum; restore returns to the last width
**Related Components:** C1, C2, C11
**Related Tasks:** T-037-02, 03
**Priority:** Medium · **Story Points:** 3

---

### US-3: My sizes are remembered, and bad data cannot break the page (FR-4)

**As a** returning user
**I want** my pane sizes to survive a reload, a smaller window and corrupt stored data
**So that** I set my layout once and it never gets in my way

**Acceptance Criteria:** AC-4.1..AC-4.5 (one `layout` object via `C.prefs`, one write per gesture, install-once listeners, clamp without rewriting, invalid data renders defaults)
**Business Rules:** BR-2 (a clamp never rewrites the stored value) · BR-7 · BR-8 (only `C.prefs` touches storage)
**Edge Cases:** stored 2000 px shows clamped and the stored value is unchanged; click without move writes nothing
**Related Components:** C1, C11
**Related Tasks:** T-037-03, 04
**Priority:** High · **Story Points:** 3

---

### US-4: Splitters appear only where there is room (FR-5)

**As a** user on a tablet, phone or narrow window
**I want** the layout to stay exactly as designed at 900 px and below
**So that** no handle, stored desktop width or half-applied rule squeezes or hides anything

**Acceptance Criteria:** AC-5.1..AC-5.6 (handles hidden by default, one `901px` constant, `--sp-*` consumed only in the wide block, no grid transition, 900/901/~800 behaviour, per-row min/max)
**Business Rules:** BR-3 (at <=900 px structural CSS applies, no stored size does)
**Edge Cases:** 900.5 px counts as not wide; window narrower than the minimums keeps the dragged pane at its minimum
**Related Components:** C1, C2, C4, C5, C6, C7, C10, C11
**Related Tasks:** T-037-02, 03, 06, 07, 09, 11, 16, 17, 19
**Priority:** High · **Story Points:** 3

---

### US-5: Resize the Agents panes (FR-6, FR-7)

**As an** Agents user
**I want to** drag the chat-list | transcript border and the transcript | right-rail border, and fold either side away
**So that** I can read a long transcript, or see the plan and files, without the other pane taking room

**Acceptance Criteria:** AC-6.1..AC-6.3 (list handle, `setListShown` collapse, `--sp-list` with fallback) · AC-7.1..AC-7.3 (rail handle attached in `mountChat`, survives streaming repaints, restore by click/Enter/double-click)
**Business Rules:** BR-9 (`chatListHidden` is the one list-fold fact; `layout` holds rail/sidebar collapse)
**Edge Cases:** handle not rendered while the list is folded; focus moves to `.list-reveal`; width kept across chats
**Related Components:** C1, C2, C4, C5
**Related Tasks:** T-037-06..08
**Priority:** High · **Story Points:** 5

---

### US-6: Resize the Vault panes (FR-8)

**As a** Vault user
**I want to** drag the sidebar | canvas border and, when a file is open, the canvas | viewer border
**So that** I can read a file wide or give the graph more room, with the graph staying sharp

**Acceptance Criteria:** AC-8.1..AC-8.4 (`resize()` guarded by a drag flag and run once after release, handles on `.vault`, zero canvas reallocations during a drag, viewer drag stops where the stage is 200 px)
**Business Rules:** BR-9 (sidebar collapse lives in `layout`)
**Edge Cases:** no viewer or empty vault means no viewer handle; the three existing `setTimeout(resize, 60)` calls stay
**Related Components:** C1, C2, C6
**Related Tasks:** T-037-09, 10
**Priority:** High · **Story Points:** 5

---

### US-7: Widen or narrow the board lanes (FR-9)

**As a** board user
**I want to** drag a lane edge to set one width for every lane
**So that** long ticket titles fit, or more lanes fit on screen

**Acceptance Criteria:** AC-9.1..AC-9.3 (`--sp-lane` on `.lanes`, handle on every non-cold lane's trailing edge, edge stays under the pointer, lanes equal, only the first handle tabbable, repaint and "Show more" keep the width)
**Business Rules:** BR-1 (one global lane width)
**Edge Cases:** board with no non-cold lane has no lane handle; the 1280 px trim and 720 px bypass are unchanged for users with no stored width
**Related Components:** C1, C2, C7
**Related Tasks:** T-037-11, 12
**Priority:** Medium · **Story Points:** 5

---

### US-8: Ticket detail opens as a docked, resizable panel (FR-10, FR-11)

**As a** board user on a wide screen
**I want** a ticket to open beside the board in a panel I can resize, instead of a modal over everything
**So that** I can keep working in the board (and the topbar) while a ticket stays open

**Acceptance Criteria:** AC-10.1..AC-10.6 (`open()` contract kept, one `dockMode()`, docked at ~1400 and modal at ~800/~400, accepted sideways scroll, clamp 320/720) · AC-11.1..AC-11.6 (fresh `.dbody` on repeat open, print, Esc rules, in-place refresh, live mode switch keeps edits)
**Business Rules:** BR-4 (one panel at a time) · ⚠ accepted default pending Q1 (D-1; switching is a one-function change)
**Edge Cases:** two rapid refreshes show the newest; half-typed field survives 1400 to 800; print with the dock open leaves no empty column
**Related Components:** C1, C2, C10
**Related Tasks:** T-037-16..19
**Priority:** Medium · **Story Points:** 8

---

### US-9: Fold sections, and collapse or expand them all (FR-12, FR-13)

**As a** console user
**I want to** fold the sections on Overview, Assistant home, the Agents rail and the Vault sidebar, and collapse or expand all at once on Overview and Assistant
**So that** I see only what I need and the choice is remembered

**Acceptance Criteria:** AC-12.1..AC-12.6 (18 literal ids, Enter guard, `panelOpen`, `C.group` + `ct-panel` in the rail, no `core.js` hunk, folds survive tab switch/reload/repaint, touch) · AC-13.1..AC-13.2 (`foldBar` queries at click time, async Jobs/Scheduled included)
**Business Rules:** BR-5 (section ids globally unique) · BR-6 (other tickets' hunks untouched)
**Edge Cases:** Enter on a collapsed header never navigates; Getting-started keeps its own fold; Settings' own buttons still work
**Related Components:** C1, C5, C6, C8
**Related Tasks:** T-037-04, 08, 10, 13, 14
**Priority:** High · **Story Points:** 8

---

### US-10: Reset layout in one click (FR-14, FR-15)

**As a** user whose layout drifted
**I want** a Reset layout control in Settings that returns sizes and folds to defaults without a reload
**So that** I can always get back to a known-good screen

**Acceptance Criteria:** AC-14.1..AC-14.3 (one function and one push, three `C.prefs.del`, defaults restored live; theme and hidden tabs unchanged) · AC-15.1..AC-15.2 (cross-ticket: "Reset all preferences" also resets the live layout; stays not verified until T-036 lands)
**Business Rules:** BR-6 · BR-7 (delete keys, never write defaults) · BR-8
**Edge Cases:** page returns to top after reset (accepted, CR-23); an open dock re-applies through the registry
**Related Components:** C1, C9
**Related Tasks:** T-037-04, 15
**Priority:** Medium · **Story Points:** 5

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Drag a pane border | Pending | High | 5 | T-037-01..05 |
| US-2 | Keyboard, collapse, double-click reset | Pending | Medium | 3 | T-037-02, 03 |
| US-3 | Sizes remembered, bad data safe | Pending | High | 3 | T-037-03, 04 |
| US-4 | Splitters only where there is room | Pending | High | 3 | T-037-02, 03, 06, 07, 09, 11, 16, 17, 19 |
| US-5 | Agents panes | Pending | High | 5 | T-037-06..08 |
| US-6 | Vault panes | Pending | High | 5 | T-037-09, 10 |
| US-7 | Board lane width | Pending | Medium | 5 | T-037-11, 12 |
| US-8 | Docked ticket panel | Pending | Medium | 8 | T-037-16..19 |
| US-9 | Foldable sections, collapse/expand all | Pending | High | 8 | T-037-04, 08, 10, 13, 14 |
| US-10 | Reset layout | Pending | Medium | 5 | T-037-04, 15 |
| **Total** | 10 stories | | | **50** | |

## Traceability Matrix

Every FR and every AC (65: AC-1.1 .. AC-15.2) is named by at least one story; none are orphaned. Tasks filled in from [[T-037-task-breakdown]] by `challenge-plan` (CR-39); T-037-20 verifies every story's [BROWSER] ACs.

| Story | FR | AC ids | Components | Tasks |
|-------|----|--------|-----------|-------|
| US-1 | FR-1, FR-2 | 1.1-1.6, 2.1-2.6 | C1, C2, C3, C11 | T-037-01..05 |
| US-2 | FR-3 | 3.1-3.4 | C1, C2, C11 | T-037-02, 03 |
| US-3 | FR-4 | 4.1-4.5 | C1, C11 | T-037-03, 04 |
| US-4 | FR-5 | 5.1-5.6 | C1, C2, C4, C5, C6, C7, C10, C11 | T-037-02, 03, 06, 07, 09, 11, 16, 17, 19 |
| US-5 | FR-6, FR-7 | 6.1-6.3, 7.1-7.3 | C1, C2, C4, C5 | T-037-06..08 |
| US-6 | FR-8 | 8.1-8.4 | C1, C2, C6 | T-037-09, 10 |
| US-7 | FR-9 | 9.1-9.3 | C1, C2, C7 | T-037-11, 12 |
| US-8 | FR-10, FR-11 | 10.1-10.6, 11.1-11.6 | C1, C2, C10 | T-037-16..19 |
| US-9 | FR-12, FR-13 | 12.1-12.6, 13.1-13.2 | C1, C5, C6, C8 | T-037-04, 08, 10, 13, 14 |
| US-10 | FR-14, FR-15 | 14.1-14.3, 15.1-15.2 | C1, C9 | T-037-04, 15 |

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements]] · [[T-037-requirements-draft]] · [[T-037-components]] · [[T-037-user-stories]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
