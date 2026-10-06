---
ticket: "T-039"
artifact: user-stories
created: "2026-10-06"
---

# User Stories: T-039

Extracted from the frozen [[T-039-requirements]] (14 FRs, 44 ACs). Tasks are in [[T-039-plan]]. [BROWSER] acceptance criteria stay unverified until the parent session runs T-039-12.

**Created by:** `requirements T-039 stories` · **Validated by:** `validate-artifacts T-039 links` · **Verified by:** `validate-artifacts T-039 links`

## Stories

### US-1: One list for what only I can resolve

**As a** workspace owner
**I want to** see a "Needs you" panel listing only open questions and pending approvals
**So that** I know at a glance what is waiting on my judgement and nothing else

**Acceptance Criteria:**
- [ ] AC-1.1, AC-1.2, AC-1.3, AC-1.5 (payload split; open vs answered; approvals; entry shape)
- [ ] AC-3.1, AC-3.2, AC-3.4 (cap 50, exact count, approvals first then critical questions, "and N more")
- [ ] AC-4.1, AC-4.2 (question row shows ticket id, `Qn`, text, status chip)
- [ ] AC-5.1 to AC-5.4 (two panels, ids, titles, empty states, keyboard)

**Business Rules:**
- Needs you = open questions + pending approvals, nothing else (D-2); answered questions go to Needs repair (D-3, Q1 default).
- Approvals sort before questions because they expire on a timeout (FR-3).

**Edge Cases:**
- More than 50 open questions: exact count in the chip, "and N more" row opens the Tickets board.
- Nothing waiting: "Nothing is waiting on you" empty state.

**Related Components:** `console/server/overview.py`, `console/static/overview.js`, `console/static/styles.css`
**Related Tasks:** T-039-01, T-039-05, T-039-06, T-039-09, T-039-12

**Priority:** High
**Story Points:** 5

---

### US-2: Repair work is kept apart from my decisions

**As a** workspace owner
**I want to** see blocked, stale, unowned work, failed runs and answers not yet applied in a separate "Needs repair" panel
**So that** things the system or an agent must fix do not blur with things I must decide

**Acceptance Criteria:**
- [ ] AC-1.3, AC-1.4 (repair members; legacy keys unchanged), AC-3.3 (8 per list kept)
- [ ] AC-5.2, AC-5.3, AC-5.5 (order, group headings, empty state, About copy)

**Business Rules:**
- The old collapse id `ov.attention` and variable `attnPanel` stay on this panel (D-16), so saved fold state keeps its meaning.

**Edge Cases:**
- A ticket both blocked and stale appears once per group; the chip is the sum of the group counts.

**Related Components:** `overview.py`, `overview.js`, `about.js`
**Related Tasks:** T-039-01, T-039-06, T-039-08, T-039-12

**Priority:** High
**Story Points:** 3

---

### US-3: The sidebar badge says what it counts

**As a** workspace owner
**I want to** see the Overview badge count only what needs me and say so on hover
**So that** a red number always means "a person must act"

**Acceptance Criteria:**
- [ ] AC-6.1 (badge reads `needs_you` only), AC-6.2 (title "N items need you"), AC-6.3 (30 s refresh, silent failure)

**Business Rules:**
- Repair-only items no longer light the badge (D-5, Q2 default); the repair total stays on its panel chip.

**Edge Cases:**
- Count 1 reads "1 item needs you"; zero hides the badge.

**Related Components:** `console/static/app.js`
**Related Tasks:** T-039-08, T-039-12

**Priority:** Medium
**Story Points:** 1

---

### US-4: Every panel shows how old it is and says STALE

**As a** workspace owner
**I want to** see an "As of {time} · {age}" line on each Overview panel and a STALE mark once the data is older than a threshold
**So that** a console tab left open never silently shows old data

**Acceptance Criteria:**
- [ ] AC-7.1 to AC-7.4 (`fresh` option; pure `freshState`; marks; age wording)
- [ ] AC-8.1 to AC-8.4 (server `generated_at`; shared as-of; failed fetch keeps rows and old time)
- [ ] AC-9.1 to AC-9.3 (default 300 s; preference `staleAfterSecs`; invalid value means default)
- [ ] AC-12.1, AC-12.2 (one shared 30 s timer, no requests, `C.fresh.count()`)
- [ ] AC-13.1 to AC-13.3 (text not colour; `<time>`; `role="status"`; focus ring)
- [ ] AC-14.1, AC-14.2 (no overflow at 400 px; nothing changes at the 900/901 px cliff)

**Business Rules:**
- The mark lives in the header so a collapsed panel still shows it (D-12).
- Age is `max(0, now - asOf)`; an unparsable `asOf` is stale (D-10).

**Edge Cases:**
- Server stopped after load: no panel blanks; all turn STALE after the threshold.
- Jobs and Scheduled use the browser time of their last successful fetch.

**Related Components:** `console/static/core.js`, `overview.js`, `overview.py`, `styles.css`
**Related Tasks:** T-039-02, T-039-03, T-039-04, T-039-05, T-039-07, T-039-09, T-039-12

**Priority:** High
**Story Points:** 8

---

### US-5: Refresh a stale panel without losing my place

**As a** workspace owner
**I want to** press "Refresh" on a stale panel in a live console
**So that** I get current data on purpose, and nothing re-renders under my keyboard focus

**Acceptance Criteria:**
- [ ] AC-10.1 (no timers in `overview.js`), AC-10.2 (button only while stale and live; clears chips)

**Business Rules:**
- Overview never re-renders itself (D-13). A failed refresh keeps the rows and the old time (D-14).

**Edge Cases:**
- Static export: no Refresh button.

**Related Components:** `overview.js`, `core.js`
**Related Tasks:** T-039-07, T-039-09, T-039-12

**Priority:** Medium
**Story Points:** 3

---

### US-6: An exported snapshot shows its own age

**As a** person opening a static export weeks later
**I want to** see the export's baked time and STALE marks
**So that** I do not mistake frozen data for current data

**Acceptance Criteria:**
- [ ] AC-8.2 (`generated_at` written to `overview.json` and `data.js`), AC-11.1 (STALE at open time, no Refresh)

**Business Rules:**
- The export pipeline is not changed; it picks the field up through `full_overview()` (scope).

**Edge Cases:**
- Jobs and Scheduled stay absent from an export, as today.

**Related Components:** `overview.py`, `console/server/export.py` (unchanged), `core.js`
**Related Tasks:** T-039-02, T-039-07, T-039-12

**Priority:** Medium
**Story Points:** 2

---

### US-7: The Overview never marks anything done

**As a** workspace owner
**I want to** know the Overview only reads and navigates
**So that** an agent or a stray click cannot clear something that needs me

**Acceptance Criteria:**
- [ ] AC-2.1 to AC-2.3 (write-nothing hash test; no mutator calls; no `C.post`/dismiss in the rows function), AC-2.4 (click issues no non-GET)

**Business Rules:**
- The guarantee is scoped to the Overview (D-15); an agent with console CLI access can still change a tracker status, tracked as a separate concern.

**Edge Cases:**
- The Jobs cancel button is a different function and stays.

**Related Components:** `overview.py`, `overview.js`
**Related Tasks:** T-039-01, T-039-06, T-039-09, T-039-12

**Priority:** High
**Story Points:** 2

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | One list for what only I can resolve | Pending | High | 5 | T-039-01, 05, 06, 09, 12 |
| US-2 | Repair work is kept apart | Pending | High | 3 | T-039-01, 06, 08, 12 |
| US-3 | Badge says what it counts | Pending | Medium | 1 | T-039-08, 12 |
| US-4 | Every panel shows its age and STALE | Pending | High | 8 | T-039-02, 03, 04, 05, 07, 09, 12 |
| US-5 | Refresh a stale panel | Pending | Medium | 3 | T-039-07, 09, 12 |
| US-6 | Export shows its own age | Pending | Medium | 2 | T-039-02, 07, 12 |
| US-7 | Overview never marks done | Pending | High | 2 | T-039-01, 06, 09, 12 |

## Traceability Matrix

| Story | FRs | Components | Tasks |
|-------|-----|-----------|-------|
| US-1 | FR-1, FR-3, FR-4, FR-5 | overview.py, overview.js, styles.css | T-039-01, 05, 06, 12 |
| US-2 | FR-1, FR-3, FR-5 | overview.py, overview.js, about.js | T-039-01, 06, 08 |
| US-3 | FR-6 | app.js | T-039-08 |
| US-4 | FR-7, FR-8, FR-9, FR-12, FR-13, FR-14 | core.js, overview.js, overview.py, styles.css | T-039-02, 03, 04, 05, 07 |
| US-5 | FR-10 | overview.js, core.js | T-039-07 |
| US-6 | FR-8, FR-11 | overview.py, core.js | T-039-02, 07 |
| US-7 | FR-2 | overview.py, overview.js | T-039-01, 06, 09 |

## Links
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-user-stories]] · [[T-039-release]]
