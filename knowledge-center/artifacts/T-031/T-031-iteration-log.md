---
ticket: "T-031"
artifact: iteration-log
status: active
created: "2026-10-05"
last_updated: "2026-10-05"
current_iteration: 2
---

# Iteration Log: T-031

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history.

**Appended by:** `requirements` (draft/enrich/iterate/freeze), `challenge-requirements`

**One entry per command invocation that changed the draft.** If a command only read state, do not add an entry.

**Conventions:**
- **Iteration** increments only when `requirements iterate` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### 2026-10-05 · `requirements draft` · v0 created
- **Trigger:** stakeholder intent: "let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default" (scope A1-A5, B1, B2, D4 as listed in `T-031-summary.md:17-19` and the analyst brief)
- **Change type:** add
- **Scope:** whole document
- **Delta:** created draft from template; Intent kept in stakeholder wording; 8 candidate FRs (coarse, AC stubs `〈TBD〉`); NFR seeds without targets; entities; BR-1..BR-6 from the approved design; 5 edge-case seeds; assumptions A-1..A-6 listed unconfirmed. v0 deliberately keeps the brief's wording where the snapshot has not yet been used to test it (installed list from `/health` caps, "tiny ~100 MB … medium ~950 MB", a blocking 2 s mic test).
- **Why:** baseline draft to iterate from
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, 28 lines containing 〈TBD〉 (grep count)
- **Next recommended:** `challenge-requirements T-031 (gaps + redteam)`

### 2026-10-05 · `challenge-requirements` (gaps + redteam) · pass 1
- **Trigger:** v0 draft
- **Change type:** add (⚠ findings, interactions table, open questions)
- **Scope:** §9 Interactions (19 rows: overlap 9, conflict 0, reuse 6, isolation 4), §12 Open Questions, §13 Challenge Findings; new `T-031-gap-analysis.md` (35 gaps: 🔴 0 · 🟡 31 · 🟢 4) and `T-031-critique-report.md` (CR-1..CR-13: 3 critical, 8 major, 2 minor)
- **Delta:** gap categories touched: all nine; ⚠ on §1, §3, §4 (FR-1..FR-8), §5, §10. Questions opened via the tracker: Q1 (scope, high: engine binaries), Q2 (decision, medium: non-commercial voice licence). No 🔴 gap: see the severity rule at the top of the gap analysis.
- **Why:** v0 kept the brief's wording; the snapshot contradicts several of its premises
- **Resulting draft state:** v0 — 13 ⚠, 0 answered Q, 28 lines with 〈TBD〉
- **Next recommended:** `requirements enrich` (replace placeholders with cited facts), then `iterate`

### 2026-10-05 · `requirements enrich` · source all
- **Trigger:** 28 〈TBD〉 lines + unlinked entities in the draft
- **Change type:** edit (placeholders only; Intent, Scope text and BR-1..BR-6 untouched)
- **Scope:** §4 AC stubs, §5 NFR targets, §6 entities, §10 dependencies; snapshot Source Log
- **Delta:** done as part of the iterate pass below, in a single editing sweep, because every enriched value (sizes, hashes, file:line, targets) is the same material that closes the ⚠ findings; recorded here so the order of operations stays visible. NFR numbers without a stakeholder source are marked `⚠ [unrealistic?]` and carried to the freeze checklist as accepted.
- **Why:** pipeline order (enrich before iterate)
- **Resulting draft state:** see iteration 1 entry

## Iteration 1 — close pass-1 findings

### 2026-10-05 · `requirements iterate` · iteration 0 -> 1
- **Trigger (verbatim):** challenge findings CR-1..CR-13 and gaps G1..G35 from pass 1 (no stakeholder feedback round; `challenge-⚠` class)
- **Change type:** edit, add, defer (CR-11 accepted), answer-Q (none answered; Q1, Q2 stay open)
- **Scope:** draft §3 (assumptions A-1..A-8, out-of-scope list), §4 (8 coarse FRs -> FR-1..FR-25 with AC-1..AC-73 and verification tags), §5 (NFR-1..NFR-14), §6 (entities), §7 (BR-1..BR-15), §8 (edge cases), §10, §11, §13; decision log D-1..D-13 written alongside
- **Delta:** FR-3 (live swap) rebuilt around a non-blocking replacement (D-6) after finding the engine mutex and single-threaded bridge; FR-12 added because "(live)" is false without a poke (D-7); mic test made non-blocking (D-11); A4 sizes replaced by measured ggml sizes (D-13); installed-state source refined (D-1); hashes obtained and recorded (D-2). Intent text and the brief's scope bullets are unchanged; the three places where the brief's wording was corrected (installed list source, A4 numbers, blocking mic test) are called out in §3 Assumptions.
- **Why:** each change traces to a CR/G id in the critique report and gap analysis
- **Gaps closed / opened:** closed 32 of 35 (G13, G16, G35 accepted); opened 0
- **Questions opened/answered:** Q1, Q2 opened during pass 1; none answered
- **Resulting draft state:** iteration 1 — 1 ⚠ (CR-11, accepted), 0 〈TBD〉 in content

### 2026-10-05 · `challenge-requirements` · pass 2
- **Trigger:** wording changed in iteration 1
- **Findings:** 6 new (CR-14 scope-creep, CR-15 spec-gap, CR-16 untestable, CR-17/CR-18 ambiguity, CR-19 unstated-assumption); 1 major, 5 minor. Gap analysis: no new gap ids.

## Iteration 2 — close pass-2 findings

### 2026-10-05 · `requirements iterate` · iteration 1 -> 2
- **Trigger (verbatim):** challenge findings CR-14..CR-19
- **Change type:** edit, accept-⚠ (CR-14)
- **Scope:** §2 tags line, FR-2 (failed-state semantics), FR-3 (two-file progress), AC-28 (OS-refused delete), AC-54 (scan scope), AC-63 (no audio file), NFR-10 wording, §13
- **Delta:** five targeted edits plus the accepted scope-creep note; no FR added or removed
- **Why:** CR-15 (major) was a real hole: a Windows file lock on delete had no defined outcome
- **Resulting draft state:** iteration 2 — 2 ⚠ accepted (CR-11, CR-14), 0 〈TBD〉 in content, 2 open non-critical questions (Q1 high, Q2 medium)

### 2026-10-05 · `challenge-requirements` · pass 3
- **Findings:** 0 new. Re-walked every FR against its AC tags, every AC id for uniqueness (AC-1..AC-73), every BR reference in FR text against §7, and the freeze checklist.

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| 1 | 2026-10-05 | pass | none (0 TBD, 0 open ⚠ except 2 accepted, 0 🔴 gaps, 0 critical questions) | `requirements T-031 freeze` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `T-031-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements-draft]] · [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-requirements]] · [[T-031-critique-report]] · [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
