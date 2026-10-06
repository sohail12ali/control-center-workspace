---
ticket: "T-037"
artifact: iteration-log
status: active
created: "2026-10-05"
last_updated: "2026-10-05"
current_iteration: 2
---

# Iteration Log: T-037

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history.

**Appended by:** `requirements` (draft/enrich/iterate/freeze), `challenge-requirements`

**One entry per command invocation that changed the draft.** If a command only read state, do not add an entry.

**Conventions:**
- **Iteration** increments only when `requirements iterate` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### 2026-10-05 · `requirements draft` · v0 created
- **Trigger:** stakeholder intent, verbatim: "more responsive, VS Code-like UI — expand sections and layout modifications easily done, able to move the layout borders like we do in VS Code" (user request 2026-10-05; decisions: splitters on all four surfaces, build alongside T-031)
- **Change type:** add
- **Scope:** whole document
- **Delta:** created draft from template; Intent, Context, Scope (in/out/assumptions), FR-1..FR-14 (one per brief item R-A..R-F, AC mostly tagged [PY]/[BROWSER]), NFR seeds, entities, BR-1..BR-6, edge cases, dependencies, stakeholders, Q1 mirrored
- **Why:** baseline draft to iterate from, grounded in [[T-037-analysis]] and [[T-037-context-snapshot]]
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, 8 〈TBD〉 (hit area, key step, collapse threshold, drag cost, touch target, `layout` shape, panelOpen-in-reset) + empty Interactions table
- **Next recommended:** `challenge-requirements T-037` (gaps + red-team)

### 2026-10-05 · `challenge-requirements` pass 1 (gaps + red-team) · no bump
- **Change type:** add (⚠ lines, Interactions table, gap rows; FR/BR text untouched)
- **Gap categories touched:** stakeholders 1, rules 4, edge 7, NFR 2, data 2, integrations 2, UX 3, compliance 2, cross-cutting 3 = 26 gaps (🔴 3: G6 stale body, G9 lane handle placement, G10 reset live apply · 🟡 18 · 🟢 5)
- **Interactions:** 17 rows (overlap 5 · conflict 5 · reuse 3 · isolation 4)
- **Findings:** CR-1..CR-20 (critical 1, major 12, minor 7), kinds: unstated-assumption 5, ambiguity 6, untestable 3, contradiction 2, nfr-unmeasurable 1, scope-creep 1, unrealistic-constraint 1, spof 1
- **Questions opened:** 0. The three 🔴 gaps each have one technically correct answer (no stakeholder judgment), so they go to the decision log in `requirements iterate` rather than to `questions`. Deviation from `challenge-requirements` step 4, stated here and in the report.
- **Sections with ⚠:** §4 FR-1, FR-2, FR-3, FR-4, FR-5, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14; §5; §6; §10
- **Resulting draft state:** v0 — 20 ⚠, 8 〈TBD〉, Q1 open (medium)
- **Next recommended:** `requirements enrich` (replace the 〈TBD〉 numbers), then `questions` extract, then `requirements iterate`

### 2026-10-05 · `requirements enrich` (source: codebase) · no bump
- **Change type:** edit
- **Delta:** replaced 5 numeric 〈TBD〉 with grounded proposals, each marked `⚠ [unrealistic?]`: hit area 6 px / 20 px coarse (AC-1.4; target convention `styles.css:2097-2113`), key step 16 / Shift 64 px (AC-3.2), collapse below half the minimum (AC-3.3), drag cost as call counts (NFR; N5 `vault.js:233-252`), coarse-pointer target (NFR). Left the `layout` shape and the Reset scope as 〈TBD〉: they are design decisions, not facts (go to `iterate`, decision-log D-4, D-15).
- **Bug logged:** `T-037-bugs.toml` `D-1` (palette.js:103 `app.drawer(...)` called as a function), the `bugs` skill; out of scope for the fix.
- **Questions extract (`questions op=extract`):** assumptions A-1..A-3 map to Q1 (open) and the decision log; no new question (analysis' non-blocking defaults adopted in D-1..D-23). Q1 stays open, medium, non-blocking.
- **Resulting draft state:** v0 — 20 ⚠, 2 〈TBD〉 (`layout` shape in §6, Reset scope in FR-14), Q1 open

---

## Iteration 1 — apply challenge pass 1

### 2026-10-05 · `requirements iterate` · 0 → 1
- **Trigger (verbatim):** challenge pass 1 findings CR-1..CR-20 ([[T-037-critique-report]]) and gaps G1-G26 ([[T-037-gap-analysis]]); no new stakeholder statement. Classification: challenge-⚠ ×20 (fr 11, nfr 2, data 2, br 2, edge 3).
- **Change type:** edit (Intent, Scope in/out unchanged except the out-of-scope list gained the `agents.js` duplicate edit and the `jumpBar`/Esc non-goals, called out here)
- **Delta:**
  - FR-1..FR-5 rewritten: handle API and overlay rule, drag cleanup and rAF, keyboard/collapse/double-click-deletes, `layout` rules and install-once listeners, wide-only rule (`min-width: 901px`) and the six-row pane table (D-2, D-3, D-5, D-6).
  - FR-6..FR-9 per surface with the attach location (`mountChat`, `.vault`, `.lanes`), collapse via `setListShown`, `vault.js` drag flag, lane handles with scaled delta (D-7, D-11).
  - FR-10/FR-11 split: dock mode and `dockMode()` (Q1 path), behaviours incl. fresh `.dbody` on refresh (CR-1/D-9), live mode switch, Esc semantics (D-10), print.
  - FR-12 id table (18 ids with defaults), FR-13 `foldBar`, FR-14 Reset scope (`layout`, `panelOpen`, `chatListHidden`), new FR-15 cross-ticket check.
  - §5 NFR targets, §6 `layout` shape, BR-1..BR-10, §8 edge cases, §9 Interactions (17 rows), §13 accepted items, new §15 test plan (P-1..P-15, B-1..B-13).
  - Decision log written: D-1..D-23. Bug `D-1` (palette) logged earlier.
- **Why:** each point traces to a CR/G id in the report and gap Resolution Log.
- **Gaps closed:** G1-G15, G17-G20, G24, G26 (incl. 🔴 G6, G9, G10); G16, G21, G22, G23, G25 are 🟢 no-action (see gap Resolution Log). **Questions opened/answered:** none; Q1 stays open.
- **Resulting draft state:** v1 — 1 ⚠ accepted block (CR-19 + Q1 default + proposed numbers), 0 〈TBD〉.

## Iteration 2 — apply challenge pass 2

### 2026-10-05 · `challenge-requirements` pass 2 · no bump
- **Walked:** FR-1..FR-15 against `styles.css:2015-2020` (rail strip), `app.js:35`, `core.js:304-317` (`C.group`), `overview.js:303-317`, `board.js:299-304`, the AC wording for vague modifiers.
- **Gaps:** G27 🟡 rail loses `ct-panel`, G28 🟢 foldBar placement, G29 🟢 Reset scroll-to-top, G30 🟡 docked ARIA role and `aria-controls` ids. 🔴 0. **Interactions:** +1 conflict row (rail strip). **Findings:** CR-21 (major, contradiction), CR-22 (minor, ambiguity), CR-23 (minor, ambiguity), CR-24 (minor, unstated-assumption). Also removed one vague modifier found while reading ("visually smooth", AC-8.3 and B-3 → countable reallocations).
- **Questions opened:** 0.
- Deviation, stated: the four findings were applied in iteration 2 without first being written as `⚠` lines in the draft (one working pass); they are recorded in the report and gap analysis.

### 2026-10-05 · `requirements iterate` · 1 → 2
- **Trigger (verbatim):** challenge pass 2 findings CR-21, CR-22, CR-23, CR-24 (no stakeholder statement). Classification: challenge-⚠ ×4 (fr 3, accepted 1).
- **Change type:** edit, accept-⚠
- **Delta:** FR-12 keeps `ct-panel` on rail sections (+ AC-12.2); FR-13 placement; FR-10 docked `role="complementary"` and AC-10.2; AC-1.2 `aria-controls` ids; FR-14 notes the scroll-to-top, CR-23 accepted (draft §13); Interactions +1 row; D-12 amended; AC-8.3/B-3 reworded.
- **Gaps closed:** G27, G28, G30; G29 accepted. **Questions:** none opened or answered.
- **Resulting draft state:** v2 — 0 〈TBD〉, 0 unresolved ⚠ (3 accepted blocks), 0 🔴, Q1 open (medium).

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| 1 | 2026-10-05 | pass: all checklist items ✓ (sign-off item recorded as "user APPROVED requested, not claimed", see requirements § Stakeholders) | 0 blockers; Q1 open (medium, accepted default) | `requirements T-037 freeze` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `T-037-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[T-037-summary]] · [[T-037-analysis]] · [[T-037-requirements-draft]] · [[T-037-context-snapshot]] · [[T-037-gap-analysis]] · [[T-037-iteration-log]] · [[T-037-decision-log]] · [[T-037-plan]] · [[T-037-progress]] · [[T-037-verification]]
