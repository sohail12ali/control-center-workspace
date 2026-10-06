---
ticket: "T-039"
artifact: plan
---

# Plan: T-039 — Needs you panel and panel freshness

## Approach

Structure: **flat** (one component, the console; one linear dependency chain; no cross-ticket dependency). It has 12 tasks, above the usual 6-task threshold; flat is kept because `analyze-components` would add nothing (one component, strictly sequential), and the parent asked for flat. Python-testable work first, then JS, then CSS, then pinned-test and docs work, then verification. Every task leaves `pytest` green on its own.

Defaults applied (Q1, Q2 non-blocking): answered questions go to Needs repair; the badge counts Needs you only. Each is a one-line override later (`_PENDING_Q` split in `overview.py`; the badge line in `app.js`).

Design points fixed here (builder follows):
- `needs_repair` is the concatenation of the five capped lists (8 each), each entry with `type` in `blocked|stale|unowned|answered|run`. `counts.needs_repair` is the sum of the five exact counts (a ticket both blocked and stale counts in both groups; tested).
- `needs_you` = approvals first, then questions with `critical` priority first, capped at 50; `counts.needs_you` exact.
- `full_overview(repo_root, now=None)`: `now` is a `datetime`; `generated_at` = `%Y-%m-%dT%H:%M:%SZ` (same format as `trackers._now_iso`).
- `core.js`: two self-contained pure functions `freshState(asOfMs, nowMs, afterSecs)` and `freshThreshold(pref, own)` (no closure variables, so a node test can slice and evaluate them), then the `opts.fresh` option, one shared timer, `C.fresh.count()`.
- The as-of row is class `fresh-row` (never `lrow`, so j/k row navigation skips it). The header chip is `fresh-mark`.
- Refresh = fetch `/api/overview` first, then repaint on success; on failure toast and keep the rows and old time (D-14). It must not go through `C.load` (which blanks the host on error, `core.js:1087-1090`).
- Row navigation becomes one shared function `rowNav(panel)` used by both attention panels (the `test_splitter.py` pins are updated deliberately, T-039-06).

## Verified references (current tree, 2026-10-06)

| Reference | Verified at |
|---|---|
| `needs_attention`, `_ATTN_RUNS`, `_PENDING_Q`, `full_overview` | `overview.py:21-22`, `:36-100`, `:140-147` |
| `C.panel`, `collapsible`, `C.load`, `C.prefs`, export object | `core.js:228-245`, `:283-322`, `:1080-1091`, `:960-996`, `:1302-1317` |
| Attention panel, key handler, other panels | `overview.js:272-323`, `:179-250`, `:252-369` |
| Badge sum | `app.js:286-295` |
| `.chip`, `.panel`, collapse rules, 620 px block | `styles.css:448-459`, `:468-522`, `:1433` |
| Pinned ids and handler text | `test_splitter.py:1118-1160` |
| **No `setInterval(` in core.js** | `test_prefs_client_source.py:202-204` (see PC-1) |
| ES5 scan flags any `=>` even in comments | `test_ui_constraints.py:45-50` |
| `assistant.js` reads `attention.blocked`; About copy | `assistant.js:123`; `about.js:25` |
| Export calls `full_overview` | `export.py:51` |

## Tasks

Test command (all tasks): `PYTHONUTF8=1 python -m pytest -o addopts="" -q console/tests/<file>` unless stated. Line endings: all touched sources are CRLF in the working tree except `test_splitter.py` and `test_ui_constraints.py` (LF); re-read before each edit, preserve, recount after.

### [x] T-039-01 — Payload split in `needs_attention` (3 h)
- **Files:** `console/server/overview.py`, `console/tests/test_attention.py` (additions only).
- **Do:** add `needs_you`, `needs_repair`, `answered`, `counts.needs_you/needs_repair/answered`; `type` on every entry; question entries `ref` + `priority`; approvals first then critical questions; cap 50; legacy keys kept, `questions` open-only.
- **Done-criteria:** AC-1.1, 1.2, 1.3, 1.4 (existing `test_questions_approvals_and_failed_runs` unchanged and green), 1.5, 2.1 (hash of ticket artifacts and `console/.cache/runs` unchanged over two calls), 2.2 (source has no mutator call), 3.1, 3.2, 3.3, 4.1.
- **Test:** `... console/tests/test_attention.py`
- **Basis:** about 60 changed lines plus 8 tests; fixtures exist (`repo`, `trackers.add(..., priority=)`, `agent_approvals` pending pattern in the existing test).
- **Depends on:** —

### [x] T-039-02 — `generated_at` (1 h)
- **Files:** `console/server/overview.py`, `console/tests/test_attention.py`.
- **Do:** `full_overview(repo_root, now=None)`; `export.py` untouched.
- **Done-criteria:** AC-8.1 (injected `now` and pattern match), AC-8.2 (`export_static` output: `data/overview.json` and `data.js` contain `generated_at`); `kanban overview` JSON still valid (NFR-6).
- **Test:** `... test_attention.py`
- **Basis:** 5 lines plus 3 tests.
- **Depends on:** T-039-01

### [x] T-039-03 — `core.js` pure helpers (1.5 h)
- **Files:** `console/static/core.js`; new `console/tests/test_fresh_core.py` (node slice test, `shutil.which("node")` skip-if-absent, plus source fallbacks).
- **Do:** `freshState`, `freshThreshold` (pref valid only if finite number 30..86400, else 300; own `staleAfter` wins), `freshAge` text helper ("just now", "N min ago", "N h ago", "N days ago"). Place after `collapsible`, NOT between the "reload holds" and "fetch" comment markers (`test_reload_source.py:229`). No `=>` anywhere, comments included.
- **Done-criteria:** AC-7.2 (299 s fresh, 300 stale, future age 0, NaN stale), AC-9.2 (`29`, `86401`, `"abc"` give 300), AC-9.1 (`staleAfterSecs` in `core.js`, nothing under `console/server` reads it), NFR-1.
- **Test:** `... test_fresh_core.py console/tests/test_ui_constraints.py`
- **Basis:** about 35 lines.
- **Depends on:** T-039-02 (ordering only)

### [x] T-039-04 — `C.panel` `opts.fresh`, shared timer, `C.fresh.count()` (2.5 h)
- **Files:** `console/static/core.js`, `console/tests/test_prefs_client_source.py` (narrow edit of `test_core_adds_no_interval`).
- **Do:** `opts.fresh = {asOf, staleAfter, onRefresh}` adds the `<time datetime>` row (last body child, class `fresh-row`, Refresh `<button>` only while stale, live and `onRefresh` given) and the header `fresh-mark` chip (`role="status"`, text "STALE", `title`); panels without `fresh` unchanged. One `setInterval` at 30 s, guarded against double start, `clearInterval` when none connected; makes no request; rewrites text only on change; reads `C.prefs.get("staleAfterSecs")` each tick; disconnected panels (`!node.isConnected`) pruned. Export `fresh: {count}` and `freshState`. Edit the old test to: no `setInterval(` outside the freshness block and exactly one inside it (intent kept: the prefs code adds no interval).
- **Done-criteria:** AC-7.1, 12.1, 13.1, 10.1 (core part), NFR-1, NFR-9; `test_reload_source.py` and `test_prefs_client_source.py` green. Browser items covered in T-039-12.
- **Test:** `... console/tests/test_fresh_core.py test_prefs_client_source.py test_reload_source.py test_ui_constraints.py`
- **Basis:** about 90 lines; the interval-pin conflict is the only unknown.
- **Depends on:** T-039-03

### [x] T-039-05 — CSS (1 h)
- **Files:** `console/static/styles.css`.
- **Do:** `.fresh-mark` next to the `.panel > header .chev` rules (about `:515-522`, as `.panel > header .fresh-mark`, flex none, no wrap, existing warn tokens, text not colour alone); `.fresh-row` next to `.panel > .body.flush` (`:488`), wraps freely, `min-width: 0`, small muted text; focus ring for its button via existing `.btn`. Never at file end; no new 900/901 px query; no bare repeated single-class selector.
- **Done-criteria:** NFR-2, NFR-4; `test_stylesheet.py` passes except the known `.ob-count` baseline failure. AC-13.2, 14.1 are [BROWSER] (T-039-12).
- **Test:** `... console/tests/test_stylesheet.py`
- **Basis:** about 20 lines.
- **Depends on:** T-039-04

### [x] T-039-06 — Overview: two attention panels (3 h)
- **Files:** `console/static/overview.js`, `console/tests/test_splitter.py` (deliberate).
- **Do:** new `needsPanel` (collapse id `ov.needsyou`, groups "Approvals", "Questions waiting", "and N more" row opens the Tickets board, empty state texts per FR-5) directly above `attnPanel` (`ov.attention`, title "Needs repair", groups "Blocked by a critical item", "Stale (N+ days)", "Nobody owns these", "Answers not yet applied", "Runs that need a look"); both `span2`; chip = exact count, tone `warn` above zero; `rowNav(panel)` shared function replaces the inline handler; question rows show `T-xxx Qn text` and a status chip, answered rows read "answered, not applied"; no `C.post(`/dismiss/clear in the row builder. Update `test_splitter.py`: `_OV_IDS` gains `ov.needsyou`; "18" becomes "19"; enter-guard test reads `rowNav` and asserts both panels call it.
- **Done-criteria:** AC-5.1, 2.3, 4.2 (code), 3.4 (code), 5.2-5.4 (code); NFR-1, NFR-8. Browser parts in T-039-12.
- **Test:** `... test_splitter.py test_ui_constraints.py test_stylesheet.py`
- **Basis:** about 110 changed lines; mostly reshaping existing code.
- **Depends on:** T-039-01, T-039-05

### [x] T-039-07 — Overview: freshness feeds and Refresh (2 h)
- **Files:** `console/static/overview.js`.
- **Do:** split `render` into fetch (`C.load`, first paint) and `paint(host, d, api)`; pass `fresh: {asOf: d.generated_at, onRefresh}` to At a glance, Needs you, Needs repair, Flow, Recently touched; Jobs and Scheduled pass `asOf: Date.now()` taken on successful fetch; `onRefresh` only when `!C.IS_STATIC`, fetches then repaints, on failure toasts and leaves the page; no `setInterval`/`setTimeout` in the file.
- **Done-criteria:** AC-10.1, 8.3 (code), 8.4 (code path), 10.2 (code), 11.1 (code: no `onRefresh` when static); NFR-9.
- **Test:** `... test_ui_constraints.py test_splitter.py`
- **Basis:** about 50 lines.
- **Depends on:** T-039-04, T-039-06

### [x] T-039-08 — Badge and About copy (0.75 h)
- **Files:** `console/static/app.js` (`:286-295` only), `console/static/about.js` (`:25` only).
- **Do:** badge = `counts.needs_you`, alert tone kept, hidden at zero, `title` and `aria-label` "N items need you" ("1 item needs you"); About text names Needs you.
- **Done-criteria:** AC-6.1, 5.5; AC-6.3 unchanged (`setInterval(refreshBadges, 30000)` still there; `test_reload_source.py:355` counts still 2).
- **Test:** `... test_reload_source.py test_ui_constraints.py test_fresh_source.py`
- **Basis:** 8 changed lines.
- **Depends on:** T-039-01

### [x] T-039-09 — Source assertions for the JS-side ACs (1.5 h)
- **Files:** new `console/tests/test_fresh_source.py`.
- **Do:** tests that read `overview.js`, `app.js`, `about.js`, `core.js`.
- **Done-criteria:** AC-2.3 (rows function has no `C.post(`/dismiss/clear; Jobs cancel excluded), AC-5.5, AC-6.1, AC-10.1, AC-12.1 (exactly one freshness `setInterval`, with `clearInterval`), AC-13.1 (`time` element with `datetime`, `role: "status"`), AC-9.1, `fresh-mark`/`fresh-row` exist in CSS, no new script tag in `index.html` (NFR-3), `requirements-dev.txt` untouched (NFR-5).
- **Test:** `... test_fresh_source.py`
- **Basis:** about 12 small tests; patterns follow `test_reload_source.py`.
- **Depends on:** T-039-07, T-039-08

### [x] T-039-10 — Docs (0.75 h)
- **Files:** `console/README.md` (a short subsection under the Overview/Static export material, about `:754-775`).
- **Do:** Needs you vs Needs repair, badge meaning, STALE/as-of, `staleAfterSecs` (30..86400, default 300, no Settings control), Refresh, export behaviour, payload keys, the D-15 limit.
- **Done-criteria:** the text states each of the above; no claim beyond tested behaviour.
- **Test:** none (read-through).
- **Basis:** about 25 lines.
- **Depends on:** T-039-07

### [x] T-039-11 — Full regression and hygiene (0.75 h)
- **Do:** `PYTHONUTF8=1 python -m pytest -o addopts="" -q` (whole console suite); `git diff --stat` shows only the files named above; `git ls-files --eol` per touched file and CRLF/LF counts unchanged in kind; `kanban overview` prints valid JSON.
- **Done-criteria:** NFR-11 (only the known `.ob-count` failure), NFR-3, NFR-5, NFR-6, NFR-10, NFR-12; cite the pass/fail counts.
- **Test:** the command above.
- **Basis:** suite run time plus review.
- **Depends on:** T-039-09, T-039-10

### [ ] T-039-12 — [BROWSER] manual verification, owned by the parent session (1.5 h)
- **Do:** run the console, check each [BROWSER] AC below at the stated viewport; record results in `T-039-verification.md`. Use a throwaway console for AC-8.4 and 9.3; export for AC-11.1.
- **Done-criteria:** every [BROWSER] AC marked pass/fail with evidence; any not run stays "not verified".
- **Test:** manual, real browser (no agent has browser tools).
- **Basis:** 20 checks, about 4 min each.
- **Depends on:** T-039-11

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-039-01 payload split | 3 h | ~60 lines + 8 tests |
| T-039-02 `generated_at` | 1 h | 5 lines + 3 tests |
| T-039-03 pure helpers | 1.5 h | ~35 lines + node/source test |
| T-039-04 panel option + timer | 2.5 h | ~90 lines; pin edit |
| T-039-05 CSS | 1 h | ~20 lines |
| T-039-06 two panels | 3 h | ~110 lines reshaped; pin updates |
| T-039-07 feeds + Refresh | 2 h | ~50 lines |
| T-039-08 badge + About | 0.75 h | 8 lines |
| T-039-09 source tests | 1.5 h | ~12 tests |
| T-039-10 docs | 0.75 h | ~25 lines |
| T-039-11 regression | 0.75 h | suite run |
| T-039-12 [BROWSER] (parent) | 1.5 h | 20 checks |
| **Total** | **19.25 h** (17.75 h agent + 1.5 h parent) | Estimates from line counts and AC counts; no velocity data cited |

## Acceptance criterion coverage

Every one of the 14 FRs and 44 ACs maps to at least one task. "[PY] task" is where the automated check lands; every [BROWSER] AC also maps to T-039-12.

| AC | Tag | Task(s) |
|----|-----|---------|
| 1.1, 1.2, 1.3, 1.4, 1.5 | PY | T-039-01 |
| 2.1, 2.2 | PY | T-039-01 |
| 2.3 | PY | T-039-06, T-039-09 |
| 2.4 | BROWSER | T-039-12 |
| 3.1, 3.2, 3.3 | PY | T-039-01 |
| 3.4 | BROWSER | T-039-06 (code), T-039-12 |
| 4.1 | PY | T-039-01 |
| 4.2 | BROWSER | T-039-06 (code), T-039-12 |
| 5.1 | PY | T-039-06 |
| 5.2, 5.3, 5.4 | BROWSER | T-039-06 (code), T-039-12 |
| 5.5 | PY | T-039-08, T-039-09 |
| 6.1 | PY | T-039-08, T-039-09 |
| 6.2, 6.3 | BROWSER | T-039-08 (code), T-039-12 |
| 7.1 | PY | T-039-04 |
| 7.2 | PY | T-039-03 |
| 7.3, 7.4 | BROWSER | T-039-04 (code), T-039-12 |
| 8.1, 8.2 | PY | T-039-02 |
| 8.3, 8.4 | BROWSER | T-039-07 (code), T-039-12 |
| 9.1 | PY | T-039-03, T-039-09 |
| 9.2 | PY | T-039-03 |
| 9.3 | BROWSER | T-039-12 |
| 10.1 | PY | T-039-07, T-039-09 |
| 10.2 | BROWSER | T-039-07 (code), T-039-12 |
| 11.1 | BROWSER | T-039-07 (code), T-039-12 |
| 12.1 | PY | T-039-04, T-039-09 |
| 12.2 | BROWSER | T-039-12 |
| 13.1 | PY | T-039-04, T-039-09 |
| 13.2, 13.3 | BROWSER | T-039-05 (css), T-039-12 |
| 14.1, 14.2 | BROWSER | T-039-05, T-039-12 |

Result: 44/44 ACs mapped (24 [PY] to tasks 01-09; 20 [BROWSER] to T-039-12). NFRs: 1 (T-039-03/04/06/07/11), 2-4 (05, 09), 5 (09, 11), 6 (02, 11), 7 (01), 8 (04, 06), 9 (04, 07), 10-12 (11).

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| `test_prefs_client_source.py:202` forbids any `setInterval(` in `core.js`; FR-12 needs one (PC-1) | High | Med | Narrow, documented edit of that test in T-039-04; parent runs `evolve` to record the NFR-8 exception | Builder / parent |
| 20 ACs are [BROWSER] and unverified until the parent session runs them | High | Med | T-039-12 owned by parent; report them as "not verified", never "done" | Parent |
| Other tickets edit `core.js`, `app.js`, `styles.css` at the same time | Med | Med | Re-read before each edit; surgical Edits; never reformat others' hunks | Builder |
| Line endings drift (CRLF tree, LF index; Write tool emits LF) | Med | Low | Check counts before and after; use Edit on CRLF files; flag any mismatch | Builder |
| Refresh failure blanks the page through `C.load` | Med | Med | Fetch first, repaint on success (T-039-07) | Builder |
| Timer leak or double start when tabs switch | Low | Med | Guard + prune + `C.fresh.count()` check (AC-12.2) | Builder |
| `counts.needs_repair` double-counts a blocked and stale ticket | Med | Low | Defined as the sum of group counts; tested in T-039-01 | Builder |
| `=>` in a comment trips the ES5 scan | Med | Low | Done-criteria forbid it; run `test_ui_constraints.py` per task | Builder |
| `node` absent, so AC-7.2/9.2 fall back to source reading | Med | Low | Skip-if-absent test plus source assertions; BROWSER checks cover the rest | Builder |

High×high risks: 0. Mitigated: 9/9.

## Plan critique

Run 2026-10-06 (`challenge-plan`, two passes). Pass 1 findings, all fixed in place:

| ID | Severity | Finding | Resolution |
|----|----------|---------|------------|
| PC-1 | critical | `test_prefs_client_source.py:202-204` asserts no `setInterval(` in `core.js`; FR-12/AC-12.1 requires one, and NFR-8 says no other existing test is edited | T-039-04 edits that test narrowly; recorded as a risk; parent to `evolve` the NFR-8 exception |
| PC-2 | major | AC-5.1 says the enter-guard test "still passes", but sharing one `rowNav` breaks its text pins | T-039-06 updates the pin deliberately (as the parent's brief asked); AC wording drift flagged |
| PC-3 | major | Refresh through `C.load` blanks the page on error, violating D-14/AC-8.4 | T-039-07 fetches first, repaints on success |
| PC-4 | major | CSS after the Overview tasks would leave `test_stylesheet.py` red after T-039-04 | CSS moved to T-039-05, right after the JS that uses it |
| PC-5 | major | `test_splitter.py` id count would be red between tasks | its update lives in T-039-06 with the new id |
| PC-6 | minor | As-of row with class `lrow` would be reached by j/k | class `fresh-row` fixed in the design points |
| PC-7 | minor | `counts.needs_repair` semantics unstated | defined as sum of group counts |
| PC-8 | minor | `=>` in comments fails the ES5 scan | added to done-criteria |
| PC-9 | minor | `fresh` code placed between the "reload holds" and "fetch" markers fails `test_reload_source.py:229` | placement rule in T-039-03 |
| PC-10 | minor | 12 tasks exceeds the 6-task threshold | justified in Approach (one component, linear chain) |

Pass 2: no new material findings. Open for the parent: acknowledge PC-1 (`evolve`) and PC-2 (AC-5.1 wording).

## Dependencies
- Blocks: —
- Blocked by: —  (T-037 and T-041 touch shared files; re-read before editing)

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
