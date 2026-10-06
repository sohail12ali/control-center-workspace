---
ticket: "T-037"
artifact: implementation-plan
---

# Implementation plan: T-037

**Ticket:** Resizable layout: draggable splitters, docked ticket panel, expandable sections. Frontend only (`console/static/*`, new `console/tests/test_splitter.py`), no `core.js` edit. **Synthesised from** [[T-037-requirements]] (FR-1..15, 65 ACs), [[T-037-plan]] (Approach, Risks), [[T-037-components]] (C1-C11) and [[T-037-task-breakdown]] (20 tasks). Per-task detail (Covers / May touch / Must NOT touch / Tests / Done) is not repeated: it lives only in the breakdown under the task id. **Effort: 46.5 h = Dev 31.5 + QC 15.0**, identical to the breakdown and plan (arithmetic in § Effort reconciliation; 45.5 h before `challenge-plan`, +1.0 h Dev on T-037-02). Status: nothing built.

## Fixed conventions (apply to every run)

- **Test command S:** `pytest -o addopts="" console/tests/test_splitter.py console/tests/test_stylesheet.py console/tests/test_plugins.py`. Baseline red: `test_stylesheet.py::test_every_class_the_js_styles_actually_exists` on `.ob-count`. Compare failing **ids**, never counts (D-20). `-k "p7_"` runs one P group.
- **Guard G (last step of every task):** re-Read before each Edit, small local edits, never rewrite a shared file, then `git diff --stat` and `git diff -U0 <file>`; foreign hunks (T-020/T-021, T-031, T-036) must not move. No commit, stash, reformat or staging (D-21). Never hand-edit `*.toml`.
- **Line numbers drift:** builders re-grep before every Edit.
- **First build task moves the lane:** `PYTHONUTF8=1 python console/kanban.py ticket move T-037 in-progress` (first step of T-037-01, before any edit).

## Phases, slices, builder runs

One sequential builder, one shared working tree, `styles.css` shared by every slice. **A builder run = one slice, at most 6 h** (S1 is three runs, S1a/S1b/S1c, and S7 two, S7a/S7b, because C1 alone exceeds the 3 h task cap and a single Write/Edit must stay at most ~150 lines; CR-28). Entry gate of every run after the first = the previous run's exit gate. Every slice exit gate = Test command S with failing ids a subset of the baseline + `git diff --stat` showing no foreign hunk moved and no T-037 change to `core.js`, both **versus the baseline recorded by T-037-01** (T-036 will add its own `core.js` and `app.js` ~266-276 hunks; "diff empty" is not a valid check, CR-29), plus the slice-specific checks below.

### Phase 1 — Foundation (S1): the splitter primitive exists before any consumer uses it

C2 (`.sp-*` CSS) first so class names exist before JS references them; then C1 (`splitter.js`), then the `<script>` tag last so nothing loads a half-built file.

**S1a — T-037-01..02** (design contract + baseline, CSS block + print block + test skeleton; 5.0 h)
- Files: `T-037-components.md` (one appended `## C1 API contract`, items (a)-(j)), `T-037-progress.md` (the `git diff -U0` baseline), `console/static/styles.css` (one `.sp-*` block beside `.split` and its own print block, mid-file), new `console/tests/test_splitter.py`.
- Entry: requirements frozen (`status: frozen`, iteration 2), plan APPROVED, lane move run as the first step of T-037-01.
- Exit: contract has six walk-through rows and no "TBD"; baseline recorded; P-7 and the three P-8 tests green (P-8 vacuous until consumers land).

**S1b — T-037-03** (`splitter.js` core: attach, ARIA, pointer, keys, collapse, persistence; 4.0 h)
- Files: new `console/static/splitter.js`, `test_splitter.py`. The highest-risk file gets a run of its own.
- Entry: S1a exit.
- Exit: P-2..P-5, P-9 green; forbidden-token Grep in `splitter.js` = 0; every option named in contract item (j) found in `splitter.js` (CR-34).

**S1c — T-037-04..05** (registry/listeners/`reapplyAll`/`foldBar`, script tag + order test; 4.0 h)
- Files: `splitter.js`, `console/static/index.html` (one line after `core.js`), `test_splitter.py`.
- Entry: S1b exit.
- Exit (S1 checkpoint): P-1..P-9 and P-13 green; `test_plugins.py` green (its palette-order test; the export is by the `*.js` glob, CR-41); `git diff --stat` lists only `styles.css`, `index.html`, `splitter.js`, `test_splitter.py`, `T-037-components.md`.
- S1 effort 13.0 h (Dev 9.5, QC 3.5). Covers FR-1..5, 13 (half), 15.2; AC-1.1-1.5, 2.1, 2.2, 3.1, 4.1, 4.2, 5.1-5.4, NFR print.

### Phase 2 — Surfaces (S2..S6): each surface adopts the primitive; slices are independent files but run in order

| Slice | Run | Files | Entry → exit (slice-specific) | Effort | FR / AC |
|-------|-----|-------|-------------------------------|--------|---------|
| S2 Agents | T-037-06..08 | `agents.js`; `styles.css` (`.appshell` in the existing wide block; `.ct-split` gets `position: relative` and a second wide block right after it, CR-25/27) | S1 exit → P-8, P-11 (rail), P-12 (list, rail) green; `chatListHidden` count unchanged; handle on `.ct-split`, not `#ctRail` | 6.0 h | FR-6, 7, 12 (rail); AC-6.1, 6.2, 7.1, 12.1/12.2 (part) |
| S3 Vault | T-037-09..10 | `vault.js`; `styles.css` (`.vault`, `.has-viewer`; a second wide block after them that also pins the three children to columns 1/2/3, CR-25/32) | S2 exit → P-11 (vault), P-12 (vault) green; `setTimeout(resize, 60)` count 3; `openCards` count 0 | 4.5 h | FR-8, 12 (vault); AC-8.1, 8.2, 12.1/12.2 (part) |
| S4 Board lane | T-037-11..12 | `styles.css` (`.lanes`, `.lane` + `position: relative`, existing wide block); `board.js` (`laneNode`, `paint()`); run `git diff -U0 console/static/board.js` first | S3 exit → P-8, P-12 (lane) green; `board.js` hunks only in the two ranges; no `draggable` in added code | 4.0 h | FR-9; AC-9.1 |
| S5 Overview, Assistant | T-037-13..14 | `overview.js`; `assistant.js` (run `git diff -U0` first) | S4 exit → P-11 (18 ids, none across files), P-13 green; no hunk in `overview.js` ~109-131; `foldBar` count in `settings.js` 0 | 5.0 h | FR-12 (ov, as), 13; AC-12.1 final, 12.2, 12.3, 13.1 |
| S6 Reset layout | T-037-15 | `settings.js` (record foreign hunks with `git diff -U0` first) | S5 exit → P-14 green; exactly two T-037 hunks; foreign hunks byte-identical | 2.0 h | FR-14, 15 (code); AC-14.1, 14.2, 15.2 |

### Phase 3 — Shell (S7): the dock, last, because it changes page structure

**S7 — T-037-16..19** (two runs; behind `dockMode()`, Q1 default built per D-1): **S7a = 16-17** (mode switch, `#app` layout, handle and width; 5.0 h), **S7b = 18-19** (focus, Esc, in-place refresh, print line, tests; 5.0 h).
- Files: `console/static/app.js` (drawer IIFE only), `styles.css` (one dock block after `.drawer .dbody` with the aside `position: relative`, one print line in the existing print block), `test_splitter.py`.
- Entry: S6 exit (T-037-16's hard edge is T-037-05; build order puts it after 15, nothing more: Reset cannot be exercised against the dock, CR-38). S7b entry = S7a exit = Greps of T-037-16/17 + Test command S not worse than baseline (no P-10 test exists yet by design, CR-43).
- Exit (S7b): P-8 (dock rows), P-10 green; `drawer.open(` count 1 in `board.js` and 0 elsewhere; `app.js` hunks only in the drawer IIFE (none at the three foreign sites); no T-037 hunk on the `:2129` print line. If T-037-17 finds C1 cannot express host ≠ owner: stop, report, `evolve`; do not patch `splitter.js` ad hoc.
- Effort 10.0 h (Dev 7.0, QC 3.0). FR-10, 11; AC-10.1, 10.2, 11.1, 11.2 and the dock rows of 5.3, 5.4.

### Phase 4 — Verification (V): owner verifier

**V — T-037-20.** Entry: S7 exit. Runs the full suite once, writes the [BROWSER] checklist B-1..B-13 (each "not verified in a browser"), records the evidence diffs and AC-15.1 as open. Exit: `T-037-verification.md` filled as above. Effort 2.0 h QC. The parent session, not an agent here, runs the browser matrix.

### Effort reconciliation

Slices 13.0 + 6.0 + 4.5 + 4.0 + 5.0 + 2.0 + 10.0 + 2.0 = **46.5 h**; Dev 9.5 + 4.5 + 3.0 + 2.5 + 3.5 + 1.5 + 7.0 + 0.0 = **31.5**; QC 3.5 + 1.5 + 1.5 + 1.5 + 1.5 + 0.5 + 3.0 + 2.0 = **15.0**. Runs: S1a 5.0 + S1b 4.0 + S1c 4.0 = 13.0; S7a 5.0 + S7b 5.0 = 10.0. Matches [[T-037-task-breakdown]] § Effort summary and the [[T-037-plan]] Effort table. Indicative range 37.2-60.45 h (0.8x and 1.3x of 46.5); +10% reserve 4.65 h (not in the sum), Final/Complete 51.15 h. Not included: the browser matrix and UAT (indicative 3-4 h), rework that matrix triggers (CR-42), the Q1 opt-in follow-up (~1.5 h).

## Verification strategy

- **[PY] (30 ACs):** source-regexp tests in `console/tests/test_splitter.py`, one group per P id, grown slice by slice (map in [[T-037-components]] "Test-group to component map"). There is no JS runner and none is added (D-20). Slice checks run Test command S, never the full suite.
- **[BROWSER] (34 ACs):** not runnable by any agent here. Only T-037-20 lists them (B-1..B-13, AC-4.4 added to B-13, AC-5.6 min/max leg added to B-1..B-5); each stays "not verified in a browser" until the parent session runs it. No build task marks one done.
- **Full suite once, at V:** `pytest -o addopts="" console/tests` (~450 s). Baseline 1 failed / 2273 passed; the failure is the `.ob-count` id above. The passed count rises by the number of new tests, so compare by failing id.
- **Evidence by `git diff`, always versus the baseline recorded by T-037-01 (CR-29):** no T-037 hunk in `core.js` (AC-12.3; T-036's own hunks may be present, so "diff empty" is not the check); foreign hunks intact: `app.js` ~346 and ~371-384 (and T-036's ~266-276), `index.html` ~72, `overview.js` ~122-127, `settings.js` four hunks (`identity()`, "Run setup again" row, `kids.push(identity())`, T-031's `assistant()`), `styles.css` `.ob-*` block and `:2129`.
- **AC-15.1** stays open until T-036 lands (R1 in [[T-037-plan]]).
- **Subagent status is not evidence** (memory): after each delegated run, verify from the tree: the task's Done-line Greps, Test command S ids and test count, `git diff --stat`.

## Rollback (D-22)

Additive; nothing outside T-037's own hunks needs to change back.
1. Delete `console/static/splitter.js` and its `<script>` tag in `index.html` (the one T-037-05 line).
2. Delete the `.sp-*` block and its print block, every `var(--sp-*)` consumer line and the two extra wide blocks (after `.ct-split` and after `.vault.has-viewer`, with the Vault column pins), the `position: relative` added to `.ct-split` and `.lane`, the dock block and the one print line in `styles.css`.
3. Remove the per-surface attach lines and fold conversions: `agents.js`, `vault.js` (the `st.openCards` state is restored; stored `panelOpen` keys are inert), `board.js`, `overview.js`, `assistant.js`; the `layoutPanel()` function and its one push in `settings.js`; the dock hunks in the `app.js` drawer IIFE.
4. `console/tests/test_splitter.py` may be removed with the rest.
5. A stored `layout` pref is inert (unknown keys are preserved by T-036); no data migration.
6. Revert by Edit of the T-037 hunks only. **Do not `git checkout`/stash a shared file**: T-020/T-021, T-031 and T-036 hunks live in the same files.

## Handoff gate: CANONICAL → TEMPLATE (self-check, not yet a `handoff` run)

Gate (handoff skill): `plan.md` has Approach + Tasks · `challenge-plan` clean · effort sums match.

| Check | State |
|-------|-------|
| [[T-037-plan]] has Approach and Tasks (20 headings, all `[ ]`, machine-parsable) | done |
| Effort sums match (plan = breakdown = this file = 46.5 h; Dev 31.5, QC 15.0) | done (re-summed after `challenge-plan`) |
| Every AC covered by at least one task (65/65; [BROWSER] only by T-037-20) | done |
| Every task has done-criteria and a basis; no effort without basis | done |
| Risks rated with mitigation (13/13, high×high 0) | done, re-run after `challenge-plan` |
| `challenge-plan` clean (no unresolved critical findings) | **done 2026-10-05**: CR-25..CR-44, 0 critical, 9 major fixed, 11 minor (fixed or accepted), 1 evolve candidate (CR-37); [[T-037-critique-report]] § Plan critique |
| User APPROVED (build → `@builder`) | pending; Q1 stays open and non-blocking |

On pass: `handoff` T-037 CANONICAL → TEMPLATE, then `@builder` on S1a (T-037-01..02), whose first step is the lane move above, then the baseline record.

## Links
- [[T-037-summary]] · [[T-037-requirements]] · [[T-037-user-stories]] · [[T-037-decision-log]] · [[T-037-components]] · [[T-037-plan]] · [[T-037-task-breakdown]] · [[T-037-implementation-plan]] · [[T-037-progress]] · [[T-037-verification]]
- Related: [[T-036-decision-log]] · [[T-031-summary]]
