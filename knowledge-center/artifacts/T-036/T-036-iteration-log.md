---
ticket: "T-036"
artifact: iteration-log
status: active
created: "2026-10-05"
last_updated: "2026-10-05"
current_iteration: 3
---

# Iteration Log: T-036

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history.

**Appended by:** `requirements` (draft/enrich/iterate/freeze), `challenge-requirements`

**One entry per command invocation that changed the draft.** If a command only read state, do not add an entry.

**Conventions:**
- **Iteration** increments only when `requirements iterate` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### 2026-10-05 · `requirements draft` · v0 created
- **Trigger:** stakeholder intent: "the app and the web app UI is out of sync" (user, 2026-10-05); decision "auto-reload on a new UI version **and** shared preferences through the server" ([[T-036-summary]])
- **Change type:** add
- **Scope:** whole document
- **Delta:** created draft from template; 8 FRs (FR-1..FR-8, 60 ACs: AC-1..AC-60), 12 NFRs (AC-61..AC-64 added for them), 14 BRs, 10 edge cases, entities table; written faithfully from [[T-036-decision-log]] (including its `ConsoleApp.holdReload`, `value !== defaultValue`, and `to`-comparison loop-guard wording). 5 non-blocking open questions logged through the CLI: Q1 live pickup (medium), Q2 sidecar check (medium), Q3 idle 30 s (low), Q4 delete-after-import (low), Q5 per-device keys (low)
- **Why:** baseline draft to iterate from
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, 3 〈TBD〉 (NFR-4, NFR-5, NFR-6 targets) + the §9 Interactions table pending
- **Next recommended:** `challenge-requirements T-036` (gaps + red-team + interactions)

### 2026-10-05 · `challenge-requirements` · pass 1 (gaps + red-team + interactions)
- **Trigger:** draft v0
- **Gaps:** 30 (G1..G30): 🔴 4 · 🟡 20 · 🟢 6; categories touched: stakeholders 2, business rules 3, edge cases 11, NFR 2, data 2, integrations 2, UX 3, compliance 2, cross-cutting 3. Each 🔴 has a default proposed in [[T-036-gap-analysis]]; none needs the user (the harness rule for this ticket), so no question was added beyond Q1-Q5.
- **Findings (⚠ in draft §13):** 18 (critical 2, major 7, minor 9); sections that received ⚠: FR-2, FR-3, FR-4, FR-5, FR-6, FR-8, BR-5, NFR-4..6, AC-17, AC-18, AC-22, AC-32. By kind: contradiction 3 · ambiguity 3 · unrealistic-constraint 1 · unstated-assumption 7 · spof 1 · nfr-unmeasurable 1 · scope-creep 1 · untestable 1.
- **Interactions (draft §9):** 23 rows: overlap 12 · conflict 1 · reuse 5 · isolation 5. The one conflict (tab script load order vs `ConsoleApp.holdReload`, CR-1) is a design flaw in the decision log, resolved by default D-11.
- **Delta to the draft:** only §9 and §13 (find-don't-fix); FR/BR/NFR text untouched.
- **Next recommended:** `requirements enrich`, then `questions` extract, then `requirements iterate` to close CR-1..CR-18 with defaults D-11..D-20.

### 2026-10-05 · `requirements enrich` · no bump
- **Trigger:** `〈TBD〉` in NFR-4, NFR-5, NFR-6; unlinked mentions
- **Change type:** edit
- **Scope:** §5 NFR-4..NFR-6; two ACs added (AC-65 [DOC], AC-66 [PY]); snapshot Source Log row added
- **Delta:** the three targets replaced with grounded numbers marked `⚠ [unrealistic?]` (≤ 2 ms per stamp on a measured 0.144 ms; ≤ 100 bytes added to a 2031-byte response; 0 new timers/requests; ≤ 1 POST per 250 ms; 3 s hydration bound against a 15 s shared timeout, `core.js:50`); anchors re-verified on the current tree (all decision-log line numbers still hold); extra stale statements already included in FR-7 (`settings.js:4-5`, `about.js:158-159`, `core.js:256-258,444`)
- **Why:** skill rule: proposed numbers stay `⚠ [unrealistic?]` until the owner confirms; nothing invented without a source
- **Resulting draft state:** 0 〈TBD〉 · 18 ⚠ open · gap-analysis unchanged
- **`questions` extract:** 5 open (Q1 medium, Q2 medium, Q3 low, Q4 low, Q5 low), 0 critical, 0 blockers (`tracker blockers T-036` empty). Each has a recorded default, so the freeze gate ("blocker/critical answered") is not blocked; they are mirrored in draft §12.

### 2026-10-05 · `requirements iterate` · iteration 0 -> 1
- **Trigger (verbatim):** challenge findings CR-1..CR-18 and gaps G3, G6, G7, G8 (🔴) from pass 1; `Blocker gaps and conflicts: first try to resolve them with a reasonable default recorded in T-036-decision-log.md` (harness brief)
- **Change type:** edit, accept-⚠ (CR-11, CR-14, CR-18), add
- **Scope:** FR-1..FR-6 text, AC-11, AC-12, AC-17..AC-20, AC-22, AC-32, AC-53 reworded, AC-67..AC-77 added, BR-5 reworded, BR-12 reworded, BR-15/BR-16 added, NFR-9 reworded, §6 entities, §8 edge cases (+9), §9 conflict row closed, §13
- **Delta:** D-11..D-20 added to [[T-036-decision-log]] (hold registry moves to `Console.holdReload` in `core.js`; dirty-field rule; unknown-version rule; count-only loop guard; write-failure and keepalive policy; import `rejected` bucket and closed-window toast; 3 s hydration bound; nav listener bound once and pickup rebuild only on change; `audit.ACTIONS` registration; manual reload is consent). No FR added or removed; Intent and Scope untouched (the S-list is unchanged; A-1..A-8 unchanged).
- **Why:** CR-1 (a `TypeError` that would abort `agents.js`/`todos.js`) and CR-2 (local-mode recovery impossible) were real design flaws in the decision log, not wording problems
- **Gaps closed / opened:** closed G2-G9, G14-G18, G20-G24, G27, G30 (accepted: G1, G10-G13, G19, G25-G26, G28-G29); opened 0
- **Questions opened/answered:** none new; Q1-Q5 stay open and non-blocking
- **Resulting draft state:** iteration 1 — 3 ⚠ accepted, 0 〈TBD〉, 77 ACs

### 2026-10-05 · `challenge-requirements` · pass 2
- **Trigger:** wording changed in iteration 1 (FR-1..FR-6, new ACs, new BRs)
- **Findings:** 6 new (CR-19 contradiction major, CR-20 unstated-assumption major, CR-21 ambiguity minor, CR-22 untestable minor, CR-23 untestable minor, CR-24 ambiguity minor). CR-19 is a flaw in the iteration-1 dirty-field rule itself; CR-20 is a flaw in the original `prefs-live-pickup` text. Gaps: 3 new (G31 two-tab/equal-value import, G32 own-rev adoption, G33 absent `prefs_rev`; edge cases). Interactions: no new rows.
- **Next recommended:** `requirements iterate` (iteration 2) to close CR-19..CR-24, then a short pass 3.

### 2026-10-05 · `requirements iterate` · iteration 1 -> 2
- **Trigger (verbatim):** challenge findings CR-19..CR-24 and gaps G31-G33 from pass 2
- **Change type:** edit
- **Scope:** FR-3 dirty-field rule, FR-4 POST response shape, FR-6 (rev adoption, equal-value import, absent `prefs_rev`), AC-10, AC-25, AC-46, AC-53, AC-60 (now [DOC]), AC-69; AC-78, AC-79, AC-80 added
- **Delta:** D-12 revised and D-21 added in [[T-036-decision-log]]; no FR added or removed; Intent and Scope untouched
- **Why:** CR-19 was a hole in my own iteration-1 rule (dictated text); CR-20 was a flaw in the original `prefs-live-pickup` text (it would hide another client's change)
- **Gaps closed / opened:** closed G31, G32, G33; opened 0
- **Resulting draft state:** iteration 2 — 3 ⚠ accepted, 0 〈TBD〉, 80 ACs

### 2026-10-05 · `challenge-requirements` · pass 3
- **Trigger:** wording changed in iteration 2
- **Findings:** 1 new: CR-25 (minor, ambiguity): queued deltas versus import, reset and refresh unstated. Gaps: no new ids. Interactions: no new rows. Re-walked every FR against its AC tags, every AC id for uniqueness and continuity (AC-1..AC-80), and every BR reference in FR text against §7.

### 2026-10-05 · `requirements iterate` · iteration 2 -> 3
- **Trigger (verbatim):** challenge finding CR-25
- **Change type:** edit
- **Scope:** FR-5 description (pending-delta rules); AC-81 added
- **Delta:** `reset()` discards queued deltas; queued deltas are re-applied over the hydrate and import maps; `refresh()` runs only with none pending. No decision-log entry needed (consequence of D-15/D-21).
- **Gaps closed / opened:** none
- **Resulting draft state:** iteration 3 — 3 ⚠ accepted, 0 〈TBD〉, 81 ACs (PY 46 · BROWSER 31 · DOC 4)

### 2026-10-05 · `challenge-requirements` · pass 4
- **Findings:** 0 new. Re-walked the iteration-3 change against FR-5/FR-6/FR-7 and the AC tags; AC ids unique and continuous (AC-1..AC-81); BR-1..BR-16 each referenced or standalone; no `〈TBD〉` outside the legend and checklist text.

### 2026-10-05 · `requirements freeze` · iteration 3
- **Result:** ✓ FROZEN (iteration 3). Draft frontmatter `status: frozen`, `freeze_status: frozen`, `frozen_at: "2026-10-05"`, `frozen_iteration: 3`; [[T-036-requirements]] finalized (8 FRs, 81 ACs: PY 46 · BROWSER 31 · DOC 4; 12 NFRs; 16 BRs; 23 interaction rows).
- **Checklist:** all 9 items ✓; sign-off: owner decision 2026-10-05 in [[T-036-summary]], freeze-level APPROVED requested in the analyst report (not yet given).
- **Hand-off:** `@planner → requirements T-036 stories` (harness runs the handoff).

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| 1 | 2026-10-05 | pass | none (0 〈TBD〉, 0 open ⚠ except 3 accepted, 0 🔴 gaps open, 0 critical or high questions; Q1-Q5 medium/low open by design) | `requirements T-036 freeze` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `T-036-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements-draft]] · [[T-036-context-snapshot]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-critique-report]]
- [[T-036-requirements]]
