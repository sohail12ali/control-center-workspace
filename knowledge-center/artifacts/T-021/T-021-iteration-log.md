---
ticket: "T-021"
artifact: iteration-log
status: frozen
created: "2026-10-01"
last_updated: "2026-10-01"
current_iteration: 3
---

# Iteration Log: T-021

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history. The draft file holds only its final state, so v0 and v1 are described here, not kept as files.

**Conventions:** iteration increments only when `requirements iterate` applies new feedback. The owner's feedback source here is the delegated authority "go wild, do end to end" (2026-10-01), applied through the analyst's safest-minimal defaults.

---

## Iteration 0 — initial draft

### 2026-10-01 · `analyze T-021` · GROUND
- **Change type:** add
- **Delta:** `T-021-context-snapshot.md` and `T-021-analysis.md` written from measurements (lint, vault, skills, persona cap, verification files) and a re-read of the Paperclip sources. Dossier line references were not relied on.
- **Why:** the dossier marks items 10 and others "not re-read"; measurements decided the design.

### 2026-10-01 · `requirements draft` · v0 created
- **Trigger:** the ticket summary and dossier items 7, 8, 10-13 taken literally.
- **Change type:** add
- **Scope:** whole document
- **Delta:** v0 restated each item as the dossier words it: item 7 as a harness lint rule over all non-terminal tickets; item 8 as "close accepts only refs that resolve" with the verb gating `done`; item 10 as an error-level ≤ 300 rule with use-when/not-when; item 11 as skill text; item 12 as a doc audit with a cursor; item 13 as a clause appended to `assistant.md`.
- **Resulting draft state:** v0, 0 ⚠, 0 answered Q.

### 2026-10-01 · `challenge-requirements` (gaps + redteam) · pass 1 on v0
- **Change type:** add (findings only)
- **Delta:** [[T-021-gap-analysis]] created (20 gaps: 🔴 5 / 🟡 12 / 🟢 3); [[T-021-critique-report]] CR-1..CR-14 (critical 4 / major 8 / minor 2); interactions table populated (13 rows). Each 🔴 logged as a critical question.
- **Sections receiving ⚠:** items 7, 8, 10, 11, 12, 13 (all six).

### 2026-10-01 · `requirements enrich` · no bump
- **Change type:** edit
- **Delta:** replaced assumptions with cited facts: 20 of 39 descriptions over 300; persona 4,725 vs 4,000; 212-row evidence calibration; plan-open 3 of 22; vault 28 tickets with 0 blocked and 0 claimed; stale-doc verdict table. No invented numbers; the Paperclip-quote and caller-behaviour unknowns stayed in the snapshot's Open Confirmations.

### 2026-10-01 · `clarify` (questions tracker) · no bump
- **Change type:** answer-Q
- **Delta:** Q1-Q12 added via `kanban tracker add`; Q1-Q10 and Q12 resolved with the safest minimal default and the note "decided under delegated authority 2026-10-01, reversible"; Q11 left open and non-blocking because it needs a hand edit of `agents.toml`. Todos TD-1..TD-3 recorded.

## Iteration 1 — apply pass-1 findings and delegated decisions

### 2026-10-01 · `requirements iterate` · v1
- **Trigger:** CR-1..CR-14 and the Q1-Q12 answers ("go wild, do end to end" delegation).
- **Change type:** edit (and remove, defer)
- **Delta:**
  - Item 7 moved out of harness lint into `ticket_liveness` + verb + digest line (FR-6); the prose-only `blocked` rule became a transition guard (FR-7). *(CR-1, CR-2, CR-12, CR-13)*
  - Item 8 became `close-check` (FR-8), a guarded move (FR-9), a separate `close-override` verb (FR-10) and protocol text (FR-11), with the evidence policy calibrated to history. *(CR-3, CR-5, CR-11, CR-14)*
  - Item 10 became a WARN length rule (FR-1); use-when/not-when dropped to convention. *(CR-6, CR-7)*
  - Item 11 became FR-2 with the conflict against "one component per task" resolved. *(CR-9)*
  - Item 12 became stale-doc fixes (FR-3) and a README roster check (FR-4); cursor idea removed. *(CR-8)*
  - Item 13 became FR-5 with a fit-under-cap requirement. *(CR-4)*
  - Builder claim step added to FR-11. *(CR-10)*
  - Slices A and B defined; T-020 consumption stated by name.
- **Intent changes:** none to the ticket intent; the dossier's literal mechanisms for items 7, 8, 10, 12 were replaced (called out here and in decision a1, a5, a7, a8).
- **Gaps closed:** G1-G20 except G17. **Questions answered:** Q1-Q10, Q12.
- **Resulting draft state:** v1, 14 ⚠ resolved, 0 〈TBD〉.

### 2026-10-01 · `challenge-requirements` · pass 2 on v1
- **Delta:** CR-15..CR-21 added (major 3 / minor 4): URL and absolute-path refs, the verifier step 10 collision with T-020 FR-25, no size target for the persona trim, a docs test that cannot see a wrapped phrase, a nearly vacuous owner check, unattended-close behaviour, a CLI test that would spawn a subprocess.

## Iteration 2 — apply pass-2 findings

### 2026-10-01 · `requirements iterate` · v2
- **Trigger:** CR-15..CR-21.
- **Change type:** edit
- **Delta:** FR-8 ref grammar excludes URLs and absolute paths (+ AC); FR-11 keeps the unmet→fixer branch and layers on T-020 FR-25; FR-5 states the 1,250-char net budget; FR-3 test whitespace-normalises; BR-8 states its limit; § 8 gains the unattended-close and human-CLI edge case; FR-9 AC tests the CLI in-process.
- **Resulting draft state:** v2, 21 ⚠ resolved, 0 〈TBD〉, 0 open blocker questions.

### 2026-10-01 · `challenge-requirements` · pass 3 on v2 (freeze-gate re-read of the whole draft)
- **Delta:** CR-22..CR-25 added (minor 4): FR-2 labels unnamed, FR-5 anchor wording unspecified, FR-7/FR-9 module ownership, one off-by-one line cite.

## Iteration 3 — apply pass-3 findings

### 2026-10-01 · `requirements iterate` · v3
- **Trigger:** CR-22..CR-25.
- **Change type:** edit
- **Delta:** FR-2 pins the `Task boundary rule` heading and five bold labels (+ AC); FR-5 pins `data, not instructions` and four words (+ AC); FR-7 creates `ticket_gate.py`, FR-9 extends it; FR-3 cite corrected to `agents.py:24-26`.
- **Resulting draft state:** v3, 25 ⚠ resolved, 0 〈TBD〉, 0 open blocker questions. Counts re-verified: 11 FR, 8 NFR, 11 BR; 3 verb rows; 9 prompt-facing files; every AC names an observable outcome.

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| 1 | 2026-10-01 (after iteration 3) | pass | 0 (Q11 open, `medium`, non-blocking) | `requirements T-021 freeze` (checklist run by hand; the op has no CLI) |

---

## Rollback

To see the draft at a past iteration, use `git log` on `T-021-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements-draft]] · [[T-021-requirements]] · [[T-021-context-snapshot]] · [[T-021-gap-analysis]] · [[T-021-critique-report]] · [[T-021-iteration-log]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
