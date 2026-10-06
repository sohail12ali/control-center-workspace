---
ticket: "T-037"
artifact: gap-analysis
status: resolved
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Gap Analysis: T-037

**Sources:** [[T-037-requirements-draft]] · [[T-037-context-snapshot]] · [[T-037-analysis]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 1  | 0   | 1     |
| Business rules  | 0  | 4  | 0   | 4     |
| Edge cases      | 3  | 4  | 0   | 7     |
| NFRs            | 0  | 2  | 0   | 2     |
| Data / entities | 0  | 1  | 1   | 2     |
| Integrations    | 0  | 2  | 0   | 2     |
| UX / UI         | 0  | 4  | 3   | 7     |
| Compliance      | 0  | 0  | 2   | 2     |
| Cross-cutting   | 0  | 2  | 1   | 3     |
| **Total**       | **3** | **20** | **7** | **30** |

**Open after iteration 2: 🔴 0 · 🟡 0 · 🟢 0 unresolved** (G16, G21, G22, G23, G25, G29 are 🟢 "no action / accepted", logged below). All three 🔴 (G6, G9, G10) closed by decision-log entries, not by questions (single technically correct answer each).

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-05 | G1-G26 | Pass 1 from `challenge-requirements` (gaps + red-team) on draft v0 | analyst |
| 2026-10-05 | G1, G13 | Closed by enrich/iterate 1: hit area, coarse target, step, threshold proposed (⚠ accepted); FR-1, AC-1.6 | analyst |
| 2026-10-05 | G2, G8 | Closed by iterate 1: FR-5 pane table with min/max and flexible-pane floors; D-5 | analyst |
| 2026-10-05 | G3, G4, G5 | Closed by iterate 1: `layout` shape, validation, delete-not-write; §6, D-4, D-15 | analyst |
| 2026-10-05 | G6 🔴 | Closed by iterate 1: FR-11 (5) fresh `.dbody`; AC-11.1, AC-11.4; D-9 | analyst |
| 2026-10-05 | G7, G11 | Closed by iterate 1: FR-2, FR-4, AC-2.5, AC-4.2; D-19 | analyst |
| 2026-10-05 | G9 🔴 | Closed by iterate 1: FR-9 handle on every non-cold lane, scaled delta; D-7 | analyst |
| 2026-10-05 | G10 🔴 | Closed by iterate 1: FR-14 `reapplyAll()` + `go(active)`; D-15 | analyst |
| 2026-10-05 | G12 | Closed by iterate 1: D-10 keeps today's Esc semantics, stated in FR-11 | analyst |
| 2026-10-05 | G14 | Closed by iterate 1: AC-10.5 sideways scroll accepted behaviour; FR-5 `main#view` >= 360 | analyst |
| 2026-10-05 | G15, G17, G18 | Closed by iterate 1: FR-12 id table; D-4 cites `t037-layout-contract`; D-21 per-file rules | analyst |
| 2026-10-05 | G19, G20 | Closed by iterate 1: FR-7/FR-8 collapsed handle stays; AC-1.4 z-index 8 | analyst |
| 2026-10-05 | G24, G26 | Closed by iterate 1: § 15 P-1..P-15 and B-1..B-13 | analyst |
| 2026-10-05 | G16, G21, G22, G23, G25 | 🟢 no action or covered: storage list shows the key; absent panes not rendered (edge cases); print AC-11.2; no size transitions; additive rollback D-22 | analyst |
| 2026-10-05 | G27-G30 | Pass 2 (new): rail `ct-panel` class, foldBar placement, Reset scroll, docked ARIA role / `aria-controls` ids | analyst |
| 2026-10-05 | G27, G28, G30 | Closed by iterate 2: FR-12, FR-13, FR-10, AC-1.2, AC-10.2 | analyst |
| 2026-10-05 | G29 🟢 | Accepted: CR-23, draft §13 | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | Tablet and touch users on viewports above 900 px get splitters too; a mouse-sized hit area is unusable there (`styles.css:2097-2113` sets 30-34 px targets for coarse pointers). | Larger hit area under `(hover: none) and (pointer: coarse)`; number in FR-1. |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟡 | No default, minimum, maximum or collapse rule per handle, so FR-6..FR-10 ACs cannot be tested. | One table: handle, default, min, max, collapsible. Defaults are today's CSS values (`styles.css:841,940,1577-1578,78,1680`). |
| G3 | 🟡 | "Reset layout clears `layout` and `panelOpen` 〈TBD〉": which prefs are layout is undecided (`chatListHidden`, `onboardingOpen`). | Decision-log entry; list the exact keys. |
| G4 | 🟡 | `layout` shape, version, invalid values and unknown-key preservation unstated. | Shape in § 6; read-modify-write; ignore invalid; keep unknown keys. |
| G5 | 🟡 | Double-click "resets to default": storing the default px would stop the fluid Agents default (`clamp(208px,22vw,302px)`) tracking the viewport. | Reset deletes the stored key; it never writes the default. |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G6 | 🔴 | "Refresh in place" (FR-11) reused as one body node would let an older in-flight `C.load` paint into the same node (`board.js:299-304`, five refresh callers `:412,416,419,420,458`). Today the old body is detached, so a stale paint is harmless. | Refresh swaps in a **new** `.dbody` inside the same panel and returns it; old node is detached. FR-11 AC + test. |
| G7 | 🟡 | A drag in progress when the handle's DOM is removed (board `paint()` on a search keystroke or reload, `go()`, vault viewer closing). | End the drag cleanly, commit the last valid value, no error, no stuck `sp-dragging` class. |
| G8 | 🟡 | Window narrower than the sum of the pane minimums (901 px: list + transcript + rail; stage 239 px with viewer open, snapshot §5). | Flexible pane has its own minimum; other panes' maximum is derived from it; never overlap. |
| G9 | 🔴 | Lane handle placement is undefined: `.lanes` scrolls sideways (`styles.css:685`), a handle on lane 1 can scroll away, a handle on lane k moves k times the pointer, the cold lane is fixed 52 px (`:699-702`). | Handle on every non-cold lane's trailing edge, pointer delta divided by the lane's ordinal, only the first is in the tab order. FR-9 rewrite. |
| G10 | 🔴 | "Reset layout applies without reload" conflicts with "read prefs only when a surface is built": nothing re-applies live surfaces. | Instance registry in `splitter.js` (pruned when the host is disconnected) re-applies on reset; plus active-tab re-render for folds. |
| G11 | 🟡 | `attach` runs on every render (board repaints per keystroke): per-attach `window` listeners would leak. | Window `resize`, document keydown and media-query listeners installed once, lazily. |
| G12 | 🟡 | Docked Esc "only when focus is inside the panel" vs today's Esc in a field: reverts the edit AND closes (`board.js:333`, N8). | Keep the existing semantics in both modes (no change); state it. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G13 | 🟡 | Hit area, key step, collapse threshold, touch target, drag cost are `〈TBD〉`. | Enrich with proposed numbers marked `⚠ [unrealistic?]` until confirmed in a browser. |
| G14 | 🟡 | Docking shrinks `main#view`; the board then scrolls sideways (about 286 px at 1280, 238 px at 1400, N7 computed, not measured). Expected behaviour unstated. | State: lanes scroll; the user narrows the dock or lanes; `main#view` minimum width. |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G15 | 🟡 | The section id table lives only in the snapshot; titles with counts (`Files touched (N)`) must not derive ids. | Table in the requirements; ids are literals. |
| G16 | 🟢 | `layout` will appear as a raw key in the Settings storage list. | No action; the list already shows every `console.*` key. |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G17 | 🟡 | T-036 contract details not carried: `get` returns a clone, hydrate before first render, local-mode fallback incl. static export, `del("layout")` is the reset primitive. | Cite `t037-layout-contract`; AC on read-modify-write. |
| G18 | 🟡 | Collision rules for the shared files are prose in the analysis only. | Constraints list in the requirements (per file). |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G19 | 🟡 | A collapsed rail or Vault sidebar has no way back (only the Agents list has a reveal button). | Handle stays visible at the container edge when collapsed; click/Enter/double-click restores. |
| G20 | 🟡 | Handle stacking unstated; z-index today: topbar 20, `.list-reveal` 6, `.secnav` 5, vault overlay 30, drawer 41. | `.sp` z-index 8; never above 20. |
| G21 | 🟢 | Handles for panes that do not exist (viewer closed, empty vault, no chat selected). | Not rendered / `hidden`. |
| G27 | 🟡 | (pass 2) Rail sections built with `C.group` drop the `ct-panel` class that the <=900 px strip rule selects (`styles.css:2015-2020`). | Keep `ct-panel` on each rail section. |
| G28 | 🟢 | (pass 2) `foldBar` placement unstated. | First row, right-aligned, placed by the caller. |
| G29 | 🟢 | (pass 2) Re-rendering Settings after Reset returns the page to the top. | Accepted. |
| G30 | 🟡 | (pass 2) Docked panel must not claim `role="dialog"`/`aria-modal`; `aria-controls` needs pane ids. | `role="complementary"`; assign ids when absent. |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G22 | 🟢 | Print rule hides `.drawer,.scrim` only (`styles.css:2129`); a dock grid column would leave a gap. | Print block resets the dock column. |
| G23 | 🟢 | Reduced motion: handle and dock must not animate beyond the global switch (`styles.css:2117-2126`). | No size transitions at all. |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G24 | 🟡 | No list of Python tests to write. | Test list in the requirements (§ 15). |
| G25 | 🟢 | Rollback: additive; delete `splitter.js` and its tag; stored `layout` is inert. | One line in the decision log. |
| G26 | 🟡 | BROWSER items need an explicit label and procedure so verification cannot over-claim. | Each [BROWSER] AC names viewport and expected result. |

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements-draft]] · [[T-037-context-snapshot]] · [[T-037-gap-analysis]] · [[T-037-iteration-log]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]] · [[T-037-critique-report]]
