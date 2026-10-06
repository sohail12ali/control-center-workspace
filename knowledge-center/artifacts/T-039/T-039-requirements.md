---
ticket: "T-039"
artifact: requirements
status: frozen
frozen_at: "2026-10-06"
frozen_iteration: 1
---

# Requirements: T-039 — Needs you panel and panel freshness

**Frozen:** 2026-10-06 · iteration 1 · source of truth for planning. Rationale and numbers: [[T-039-decision-log]] (D-1..D-17); findings: [[T-039-critique-report]] (CR-1..CR-16); gaps: [[T-039-gap-analysis]] (G1-G14); history: [[T-039-iteration-log]]; facts: [[T-039-context-snapshot]], [[T-039-analysis]]. Full draft wording: [[T-039-requirements-draft]]. Post-freeze changes go through `evolve`.

## Intent

From a video about a personal "AI OS" dashboard ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]), user decisions 2026-10-06: (1) one list reserved for what only a person can resolve ("Needs you"), separate from what needs repair; the agent never marks an item done. (2) every panel shows its own timestamp and is marked STALE after a threshold instead of hiding or silently showing old data.

## Scope

**In:** `needs_attention` split and `generated_at` in `console/server/overview.py`; two attention panels and freshness feeds in `console/static/overview.js`; a `fresh` option on `C.panel` plus one shared timer in `console/static/core.js`; the Overview nav badge in `console/static/app.js`; CSS next to `.panel`/`.chip` in `styles.css`; one view preference `staleAfterSecs`; the static export picks the new fields up through `full_overview()` with no change to `export.py`.

**Out (explicit):** routines board ([[T-040-summary]]); brain views ([[T-038-summary]]); clock, heatmap, deep-work bar, gate countdown, system gauges; freshness on non-Overview tabs (the option is generic, applying it elsewhere is a later one-line change per panel); the Getting-started card; a Settings control for the threshold; auto-refresh of Overview; a new JS file or script tag; server-side enforcement that agents cannot change a tracker status (D-15); a `review_escalated` entry (D-2).

**Open (non-blocking, defaults applied):** Q1 answered questions go to Needs repair (D-3); Q2 badge counts Needs you only (D-5). Both are one-line changes if the user overrides.

Tags: **[PY]** pytest, no browser; **[BROWSER]** needs a real browser at the stated viewport, *not verified* until the parent session runs it (no agent has browser tools). JS has no unit runner here: freshness math is [PY]-checked by source and, if `node` exists, by an optional skip-if-absent test of the pure function; otherwise [BROWSER].

## Functional Requirements

1. **FR-1 Payload split.** `needs_attention(repo_root)` adds `needs_you` and `needs_repair` (lists of entries, each with `type`) and `counts.needs_you`, `counts.needs_repair` (exact totals). Needs you = open questions (`type: "question"`, with `ref` = question id and `priority`) + pending approvals (`type: "approval"`, `href: "agents"`). Needs repair = blocked, stale, unowned tickets, runs in `failed|timed_out|scheduled_retry`, and answered questions (`type: "answered"`). Legacy keys stay (D-6); `questions` becomes open-only and a new `answered` list holds the rest.
   - [ ] AC-1.1 [PY] result has `needs_you`, `needs_repair`, `counts.needs_you`, `counts.needs_repair`; counts equal list lengths when under the caps.
   - [ ] AC-1.2 [PY] an `open` question is in `needs_you` only; an `answered` question is in `needs_repair` only (`type: "answered"`); `resolved`/`closed` in neither.
   - [ ] AC-1.3 [PY] a pending approval is in `needs_you`; a `failed`, `timed_out` and `scheduled_retry` run, a blocked, a stale and an unowned ticket are in `needs_repair`; a `done` run and a terminal-lane ticket are in neither; a ticket with `review_escalated` adds no entry of its own.
   - [ ] AC-1.4 [PY] legacy keys `blocked, stale, unowned, questions, approvals, runs` and `counts.*` keep their shape; `assistant.js:123`'s `attention.blocked` still resolves; the existing `test_attention.py` assertions pass unchanged.
   - [ ] AC-1.5 [PY] each `needs_you` entry has `id, title, kind, stage, type, href`; question entries also `ref` and `priority`.
2. **FR-2 Read-only; no clearing.** The Overview never marks an item done: `needs_attention`/`full_overview` write nothing, and attention rows only navigate. Clearing happens in the underlying surface (tracker answer, approval decision, run/ticket state). Limit stated in D-15.
   - [ ] AC-2.1 [PY] hash every file under the ticket artifacts dir and `console/.cache/runs`, call `needs_attention` twice, hashes unchanged; a pending approval is still pending.
   - [ ] AC-2.2 [PY] `overview.py` source contains no call to a mutator (`.decide(`, `tracker`/`tickets` `add|update|set_|patch|move`, file writes).
   - [ ] AC-2.3 [PY] the function that renders attention rows in `overview.js` contains no `C.post(` and no `dismiss`/`clear`/`done` control (the Jobs cancel button is a different function and stays).
   - [ ] AC-2.4 [BROWSER ~1400] clicking a row opens its board or Agents tab and issues no non-GET request (network panel).
3. **FR-3 Caps and order.** Needs you shows up to 50 rows, approvals first (they expire on a timeout), then questions with `critical` priority first; the chip shows the exact count; beyond 50 an "and N more" row opens the Tickets board. Needs repair keeps its existing 8 per list.
   - [ ] AC-3.1 [PY] 60 open questions give `len(needs_you) == 50` and `counts.needs_you == 60`.
   - [ ] AC-3.2 [PY] with an approval and a critical and a normal question, order is approval, critical, normal.
   - [ ] AC-3.3 [PY] each repair list is `<= 8` with exact counts (unchanged).
   - [ ] AC-3.4 [BROWSER ~1400] with more than 50, the "and N more" row is present and the header chip shows the full count.
4. **FR-4 Row content.** Question rows show ticket id, question ref (e.g. `Q3`), text and a status chip; approval rows show the tool and chat. Answered rows read as "answered, not applied".
   - [ ] AC-4.1 [PY] `ref` equals the tracker item id for each question entry.
   - [ ] AC-4.2 [BROWSER ~1400] a question row shows `T-xxx Qn text`.
5. **FR-5 Two panels.** Overview renders "Needs you" (collapse id `ov.needsyou`, groups "Approvals", "Questions waiting") immediately above "Needs repair" (kept id `ov.attention`, variable `attnPanel`, groups "Blocked by a critical item", "Stale (N+ days)", "Nobody owns these", "Answers not yet applied", "Runs that need a look"), both full width. Empty states: Needs you "Nothing is waiting on you" / "No open questions or approvals."; Needs repair "Nothing needs repair" / "No blocked, stale or unowned work, answers waiting to be applied, or failed runs." Header chip is the list's exact count; tone `warn` when above zero.
   - [ ] AC-5.1 [PY] `overview.js` has exactly seven `collapse: { id: "ov.*" }` literals including `ov.needsyou` and `ov.attention`; `test_splitter.py` `_OV_IDS` and its count (18 to 19) are updated in the same change, and the enter-guard test (`:1146-1160`) still passes. **Amended 2026-10-06 (PC-2, see [[T-039-decision-log]] Amendment):** it no longer passes unchanged; one shared `rowNav` changes the pinned `attnPanel` text (`test_splitter.py:1118-1160`), so task T-039-06 updates that pin deliberately and the test then asserts both panels call `rowNav`.
   - [ ] AC-5.2 [BROWSER ~1400] Needs you is above Needs repair; titles read exactly as above; each folds independently and remembers its state after reload.
   - [ ] AC-5.3 [BROWSER ~1400] with no items, both empty states show with their text; with items, the group headings above appear only for non-empty groups.
   - [ ] AC-5.4 [BROWSER ~1400] in each panel `j`/`k`/arrows move the highlighted row, Enter opens it; Enter on a header folds without opening a row.
   - [ ] AC-5.5 [PY] `about.js` Overview description no longer says "blocked, stale and unowned work" alone and names Needs you.
6. **FR-6 Badge.** The Overview nav badge counts `counts.needs_you` only, keeps the alert tone, is hidden at zero, and carries `title` and `aria-label` "N items need you" (singular "1 item needs you").
   - [ ] AC-6.1 [PY] the badge block in `app.js` reads `needs_you` and no longer sums `blocked/stale/unowned/runs`.
   - [ ] AC-6.2 [BROWSER ~1400] with 2 open questions and 1 failed run the badge shows 2 and its title says "2 items need you"; with only the failed run the badge is hidden.
   - [ ] AC-6.3 [BROWSER] the badge still refreshes every 30 s and survives a failed fetch silently (existing behaviour, unchanged).
7. **FR-7 Panel freshness option.** `C.panel(title, kids, headExtra, opts)` accepts `opts.fresh = { asOf, staleAfter, onRefresh }` (`asOf` an ISO string or epoch ms). Without it a panel is structurally identical to today. With it: a `<time datetime=ISO>` "As of {local time} · {age}" as the last row of the body; while stale, a header chip `.fresh-mark` with the text "STALE" and `title` "This panel's data is out of date" (D-9, D-12); a missing or unparsable `asOf` renders "As of unknown" and counts as stale.
   - [ ] AC-7.1 [PY] a panel built without `opts.fresh` has the same structure (existing tests pass; no new class on it).
   - [ ] AC-7.2 [PY] a pure function `C.freshState(asOfMs, nowMs, afterSecs)` returning `{ageSecs, stale}` exists in `core.js`; stale is `ageSecs >= afterSecs`; negative age is 0; invalid `asOf` is stale. If `node` is available a skip-if-absent test evaluates it for: 299 s fresh, 300 s stale, future time age 0, `NaN` stale.
   - [ ] AC-7.3 [BROWSER ~1400] a panel older than the threshold shows the STALE chip in its header and the as-of row; a fresh panel shows the as-of row and no chip; a collapsed stale panel still shows the chip.
   - [ ] AC-7.4 [BROWSER ~1400] age text reads "just now" under 60 s, "N min ago" under 1 h, "N h ago" under 48 h, "N days ago" after, and advances with no new request (test with the preference at 30 on a throwaway console).
8. **FR-8 Timestamp sources and failure.** `full_overview()` adds `generated_at` (UTC `YYYY-MM-DDTHH:MM:SSZ`, same as `trackers._now_iso`; takes an optional `now` for tests). At a glance, Needs you, Needs repair, Flow and Recently touched use it. Jobs and Scheduled use the browser time of their last successful fetch. `asOf` moves only on success; a failed fetch keeps the shown rows and the old time (D-14).
   - [ ] AC-8.1 [PY] `full_overview(repo, now=X)["generated_at"]` equals X formatted, and matches the pattern with no `now`.
   - [ ] AC-8.2 [PY] `export_static` writes `generated_at` into `data/overview.json` and `data.js`.
   - [ ] AC-8.3 [BROWSER ~1400] the five overview-fed panels show the same as-of time; Jobs and Scheduled show their own.
   - [ ] AC-8.4 [BROWSER ~1400, throwaway console] stop the server after load: no panel disappears or blanks, every panel becomes STALE after the threshold; restart, press Refresh, chips clear.
9. **FR-9 Threshold.** Default 300 s for every panel. Preference `staleAfterSecs` (finite number 30..86400; anything else means the default) read with `C.prefs.get` on each tick, so a change made in another browser applies. A panel may pass its own `staleAfter` in code, which wins. No Settings control (D-11).
   - [ ] AC-9.1 [PY] `staleAfterSecs` appears in `core.js`; nothing under `console/server` reads it.
   - [ ] AC-9.2 [PY] with the node test or by reading source: `29` and `86401` and `"abc"` resolve to 300.
   - [ ] AC-9.3 [BROWSER] preference 30 makes a loaded panel STALE after 30 s; preference `"abc"` behaves as 300.
10. **FR-10 No auto re-render; Refresh.** Overview never re-renders itself. A stale panel in a live console shows a "Refresh" button in the as-of row, which re-renders the Overview (`onRefresh`); there is no button in the static export.
   - [ ] AC-10.1 [PY] `overview.js` adds no `setInterval`/`setTimeout`.
   - [ ] AC-10.2 [BROWSER ~1400] Refresh appears only while stale and live; pressing it re-renders with a new `generated_at` and clears the chips; the keyboard-highlighted row is not lost between ticks (no re-render without the button).
11. **FR-11 Static export.** An exported Overview shows its baked `generated_at` as "As of", turns STALE once older than the threshold at open time, has no Refresh button, and still omits Jobs and Scheduled as today.
   - [ ] AC-11.1 [BROWSER file://] export, then open it after setting the preference to 30 and waiting 30 s (or an export at least 5 min old): chips show STALE; as-of shows the export time; no Refresh button.
12. **FR-12 One timer.** A single shared 30 s timer in `core.js` starts when the first fresh panel connects, stops when none is connected, makes no request, and rewrites DOM text only when the displayed string changed. A read-only `C.fresh.count()` returns the connected fresh panels (disconnected ones pruned).
   - [ ] AC-12.1 [PY] `core.js` has exactly one freshness `setInterval`, guarded against double start, with a `clearInterval` path.
   - [ ] AC-12.2 [BROWSER] open Overview, go to another tab and back ten times: `C.fresh.count()` equals the number of fresh panels now on screen and the page makes no extra requests per tick.
13. **FR-13 Accessibility.** STALE is text, not colour alone; the as-of value is a real `<time>` element; the STALE chip is `role="status"` and constant text (announced once on transition, never re-announced per tick); the Refresh button is a `<button>` with a visible focus ring.
   - [ ] AC-13.1 [PY] `core.js` creates a `time` element with `datetime` and gives the mark `role: "status"`.
   - [ ] AC-13.2 [BROWSER ~1400] in forced-colors or greyscale the STALE chip is still identifiable by its text; contrast uses existing tokens.
   - [ ] AC-13.3 [BROWSER] Tab reaches Refresh; Enter/Space activate it; the header chip is not a tab stop.
14. **FR-14 Layout.** The marks fit without horizontal overflow at 400 px; no change at the 900/901 px cliff.
   - [ ] AC-14.1 [BROWSER 400 px] Overview with a long-titled, collapsed, stale panel: `document.documentElement.scrollWidth <= clientWidth`; the STALE chip is visible; the as-of row wraps.
   - [ ] AC-14.2 [BROWSER 899/901/1000/1400] panel widths and the stat tiles are the same as before the change apart from the new panel and rows.

## Non-Functional Requirements

1. **NFR-1 ES5.** Every changed `console/static/*.js` stays ES5 IIFE style: no `=>`, no statement-leading `let`/`const`, no backticks. Evidence: `test_ui_constraints.py` passes.
2. **NFR-2 CSS.** New hyphenated classes used from JS (`fresh-mark`, `fresh-row`) each exist in `styles.css`; added mid-file next to `.panel`/`.chip` rules, not at the end; no new bare single-class selector repeats an existing one; no `.fresh` bare class collision. Evidence: `test_stylesheet.py` passes except the known baseline failure `onboarding-wizard.js: .ob-count`.
3. **NFR-3 No new file or script.** No new `.js`; `index.html` script tags and order unchanged (`core.js` before `overview.js` before `app.js`).
4. **NFR-4 900 px cliff.** No new media query at 900/901 px; new rules need none, or use the existing `max-width: 620px` block.
5. **NFR-5 No new dependency.** `console/requirements-dev.txt` unchanged; no package manifest.
6. **NFR-6 Compatibility.** Additive payload (FR-1, D-6); `kanban overview` still prints valid JSON; the static export format is unchanged except the new fields.
7. **NFR-7 Testable server logic.** `needs_attention` and `full_overview` stay pure functions of the repo (plus an optional injected `now`), covered by `console/tests/test_attention.py` additions; no test needs a browser.
8. **NFR-8 Test pins updated deliberately.** `test_splitter.py` ids (7 in `overview.js`, 19 overall) are changed in the same commit as the new id; no other existing test is edited except `test_attention.py` additions. **Amended 2026-10-06 (PC-1, see [[T-039-decision-log]] Amendment):** exception for `test_prefs_client_source.py::test_core_adds_no_interval` (`:202-204`), narrowed to "no `setInterval(` outside the freshness block, exactly one inside it", because it contradicts FR-12/AC-12.1; and the `test_splitter.py` attention-panel pin (see AC-5.1).
9. **NFR-9 Cost.** No new request; one 30 s timer; payload build stays near today's 0.11 s; Needs-you payload bounded at 50 rows.
10. **NFR-10 Line endings.** Working tree is CRLF and the index LF: preserve what each file has when editing (check CRLF/LF counts before and after); artifacts keep CRLF; never anchor an Edit on the bare Links heading text.
11. **NFR-11 Baseline.** `PYTHONUTF8=1 python -m pytest -o addopts="" -q` shows no failure beyond the known `.ob-count` one (handoff section 5: 1 failed, ~2877 passed, 1 skipped, plus the new tests).
12. **NFR-12 Shared files.** `core.js`, `app.js`, `styles.css` are edited by other tickets (T-037): re-read before each edit, keep edits surgical, never revert or reformat another ticket's uncommitted hunks.

## Traceability

| Requirement | Source | Decision |
|---|---|---|
| FR-1, FR-3, FR-4, FR-5 | user decision (1); [[T-039-summary]] scope 1 | D-1, D-2, D-3, D-4, D-6, D-7, D-16 |
| FR-2 | user decision (1) "agent never marks done" | D-15 |
| FR-6 | [[T-039-summary]] scope 1, last sentence | D-5 |
| FR-7, FR-8, FR-9, FR-10, FR-12 | user decision (2); summary scope 2-3 | D-8, D-9, D-10, D-11, D-13, D-14 |
| FR-11 | summary open point (static export) | D-10 |
| FR-13, FR-14 | analyst brief (accessibility, 400 px) | D-12 |
| NFR-1..NFR-12 | analyst brief constraints; test files cited in [[T-039-context-snapshot]] | D-17 |

## Out of Scope
- See Scope above (routines board, brain views, clock/heatmap/deep-work/gate/gauges, non-Overview panels, Settings control, auto-refresh, server-side agent clear prevention).

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
- Upstream: [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · [[T-040-summary]] · [[T-038-summary]] · [[T-037-summary]]
