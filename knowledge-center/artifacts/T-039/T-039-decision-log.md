---
ticket: "T-039"
artifact: decision-log
---

# Decisions: T-039

All decided 2026-10-06 by the analyst as stated defaults; none needed a blocking question. D-3 and D-5 are the two the user may want to override (tracked as non-blocking questions Q1 and Q2 in `T-039-questions.toml`). Evidence is in [[T-039-context-snapshot]].

## D-1 two-lists
**Decision:** Split `needs_attention` into "Needs you" (only a person can clear it) and "Needs repair" (the system or an agent must fix it). Two panels on Overview, Needs you first.
**Rationale:** The user's decision; today one panel mixes both (`overview.py:36-100`, `overview.js:272-303`).
**Impact:** FR-1, FR-5.

## D-2 needs-you-members
**Decision:** Needs you = open questions + pending approvals. Nothing else.
**Rationale:** Only these wait on a person. A question is answered by a person (`questions` skill step 3); an approval is decided by a person in the console or Telegram (`agent_approvals.py:172-201`, `telegram_bot.py:246-264`). Review escalation needs no kind of its own: it opens a critical question (`verb_handlers.py:640-643`) and its `human_decision` is an approval card (`agents.toml:119-127`), so it already appears twice-over as the two kinds above.
**Impact:** FR-1, AC-1.2, AC-1.3.

## D-3 answered-questions-are-repair
**Decision:** A question with status `answered` goes to Needs repair, labelled "answered, not applied". Only `open` is in Needs you.
**Rationale:** `answered` = a person already answered; the remaining step is folding the answer into the artifact (`.claude/skills/questions/SKILL.md:29-31`). Leaving it in Needs you would make a person look at something they already did. This differs from the ticket summary's "open or answered"; flagged for the user (Q1), one-line change in `_PENDING_Q`.
**Impact:** FR-1, AC-1.2.

## D-4 repair-members
**Decision:** Needs repair = blocked tickets, stale tickets, unowned tickets, runs in `failed|timed_out|scheduled_retry`, answered-not-applied questions. Behaviour of these five existing kinds is unchanged except the new grouping.
**Rationale:** Each is fixed by changing the work or the run, not by a person's judgement call; "blocked" is derived from critical open items whose open question already appears in Needs you.
**Impact:** FR-1.

## D-5 badge-counts-needs-you
**Decision:** The Overview nav badge counts Needs you only, keeps the alert tone, and its `title` and `aria-label` say so ("N items need you"). The repair total stays on the Needs-repair panel chip.
**Rationale:** The dossier requires the badge to say which list it counts; a badge that summed both would again blur "waits for me" with "needs fixing". Behaviour change: repair-only items no longer light the nav badge (today they do, `app.js:290-292`); the user may prefer a second count (Q2).
**Impact:** FR-6.

## D-6 additive-payload
**Decision:** Keep every legacy key of `attention` (`blocked, stale, unowned, questions, approvals, runs, counts.*`) and ADD `needs_you`, `needs_repair`, `counts.needs_you`, `counts.needs_repair`, `answered`. Only `questions` changes meaning (open only; answered moves to `answered`).
**Rationale:** `assistant.js:123` reads `attention.blocked`; the static export and `kanban overview` print the same payload; an additive change breaks nobody.
**Impact:** FR-1, NFR-6.

## D-7 needs-you-cap
**Decision:** Needs you is capped at 50 rows with an exact count and an "and N more" row; Needs repair keeps its cap of 8 per list.
**Rationale:** Today 9 questions are open (measured 2026-10-06), so cap 8 would hide a human-only item. 50 bounds the payload.
**Impact:** FR-3.

## D-8 freshness-clock
**Decision:** One shared 30 s timer in `core.js`, started when the first fresh panel is built and stopped when none is connected. It re-evaluates age; it never fetches. Not tied to the T-036 heartbeat.
**Rationale:** `probe()` only calls `onHeartbeat` when `/api/config` answers (`app.js:439-441`), so a heartbeat-driven tick would never mark data STALE while the server is down, the case that matters. T-036's "no timer of its own" applied to the version check, which is a comparison of a heartbeat reply; freshness is a comparison against the clock.
**Impact:** FR-7, FR-8, FR-9.

## D-9 stale-wording
**Decision:** The freshness mark reads "STALE" (upper case, own element `.fresh-mark`) with the age in `<time>`; the ticket-idle concept stays "Stale (N+ days)". Mark carries a `title`: "This panel's data is out of date".
**Rationale:** `stale` already names ticket idleness (`render.py:59`, `overview.js:265`); the user asked for the STALE mark, so keep the word but make the element and the title unambiguous.
**Impact:** FR-7, FR-13.

## D-10 timestamp-source
**Decision:** Panels fed by `/api/overview` use a server `generated_at` (UTC `YYYY-MM-DDTHH:MM:SSZ`) added to `full_overview()`. Jobs and Scheduled (separate endpoints, no stamp) use the browser time of their last successful fetch. Age = `max(0, now - asOf)`.
**Rationale:** In the static export, a client-side fetch time would always read "just now" for data frozen weeks ago; only the baked server stamp is honest there. Jobs/Scheduled are never in an export (`core.js:150-158`). Clamping at 0 covers clock skew.
**Impact:** FR-8, FR-11.

## D-11 threshold
**Decision:** Default 300 s for every panel. One preference `staleAfterSecs` (number, 30..86400, else the default) read through `C.prefs.get`; a panel may pass its own `staleAfter` in code. No new Settings control; the key shows in the Stored-preferences list like any other.
**Rationale:** The Overview is re-rendered on every visit of the tab and the badge polls at 30 s, so 5 minutes is long enough not to flicker and short enough to matter. The server never reads preferences (`prefs_store.py:11-14`), which is fine: STALE is a view concern computed in the browser.
**Impact:** FR-9.

## D-12 mark-in-header
**Decision:** The STALE chip is in the panel header (visible when the panel is collapsed); the "as of" line (`<time>`) is the last row of the panel body.
**Rationale:** A collapsed panel hides its body (`styles.css:522`); a mark that vanishes on collapse is the "hiding" the user rejected. At 400 px the header holds icon, truncating title, count chip, STALE chip, chevron; the body line wraps freely.
**Impact:** FR-7, FR-14.

## D-13 no-auto-rerender
**Decision:** Overview does not re-render by itself. A stale panel offers one "Refresh" button (live only) that re-renders the Overview.
**Rationale:** An auto re-render would drop keyboard focus and the `kbd` row in the attention panel (`overview.js:304-322`) and fight a person reading. A mark with no action is a dead end, so the button.
**Impact:** FR-10.

## D-14 failed-refresh-keeps-data
**Decision:** `asOf` moves only on a successful fetch. A failed refetch keeps the rows already shown and the old time, so the panel ages into STALE instead of silently looking current.
**Rationale:** "Not hiding or silently showing old data."
**Impact:** FR-8, AC-8.4.

## D-15 read-only-guarantee
**Decision:** The "agent never marks an item done" requirement is stated and tested at the Overview level: `needs_attention`/`full_overview` mutate nothing, rows only navigate, no dismiss/clear control exists. The residual: an agent with console CLI access can still change a tracker status; closing that is a separate ticket.
**Rationale:** BE HONEST: the system cannot guarantee more today (`config/verbs.toml:174-176` calls the review verb audit-checked).
**Impact:** FR-2.

## D-16 panel-ids
**Decision:** New collapse id `ov.needsyou` for Needs you; the old `ov.attention` id (and variable `attnPanel`) stays on Needs repair, so existing saved fold state and the enter-guard test keep their meaning. `test_splitter.py` `_OV_IDS` and its "18" become 7 and 19.
**Rationale:** `test_splitter.py:1118-1141` pins the ids; one deliberate edit beats a silent break.
**Impact:** FR-5, NFR-8.

## Amendment 2026-10-06 (evolve, target requirements, from plan critique PC-1 and PC-2)
**Reason:** discovery during plan challenge; two frozen statements contradict existing pinned tests. Not a scope expansion.
**A1 (PC-1, NFR-8):** Before: "no other existing test is edited except `test_attention.py` additions." After: also `console/tests/test_prefs_client_source.py::test_core_adds_no_interval` (`:202-204`), which asserts no `setInterval(` anywhere in `core.js` and so contradicts FR-12/AC-12.1 (one shared freshness timer). Task T-039-04 narrows it: no `setInterval(` outside the freshness block, exactly one inside it; its intent (the prefs code adds no interval) is kept.
**A2 (PC-2, AC-5.1):** Before: "the enter-guard test (`:1146-1160`) still passes." After: it is updated, not unchanged. Sharing one `rowNav(panel)` between both attention panels changes the pinned `attnPanel` handler text (`test_splitter.py:1118-1160`); task T-039-06 updates the pin deliberately and asserts both panels call `rowNav`.
**Cascade (re-validate):** plan T-039-04 and T-039-06 (already carry the edits); NFR-8 and AC-5.1 text in the requirements (annotated in place, original wording retained). No other FR/AC changes.

## D-17 no-new-file
**Decision:** No new JS file; helpers live in `core.js`; CSS mid-file next to `.panel`/`.chip`.
**Rationale:** Avoids script-order and `index.html` churn; `core.js` already owns `panel`.
**Impact:** NFR-3.

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
- Upstream: [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · [[T-036-summary]]
