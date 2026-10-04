---
ticket: "T-020"
artifact: iteration-log
status: frozen
created: "2026-10-01"
last_updated: "2026-10-01"
current_iteration: 2
---

# Iteration Log: T-020

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history.

**Appended by:** `requirements` (draft/enrich/iterate/freeze), `challenge-requirements`

**Conventions:**
- **Iteration** increments only when `requirements iterate` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### 2026-10-01 · `requirements draft` · v0 created
- **Trigger:** stakeholder intent, verbatim: "Make a Run survive the ways agent runs actually fail … items 1–6 of the Paperclip adoption dossier … Console server only; stdlib Python." (`T-020-summary.md`); "go wild, do end to end" (delegated authority, 2026-10-01).
- **Change type:** add
- **Scope:** whole document
- **Delta:** drafted Intent, Context, Scope (in/out/assumptions), FR-1..FR-25 in three slices, NFR-1..NFR-11, data entities, BR-1..BR-13, edge cases, dependencies, stakeholders. Interactions, Open Questions and Challenge Findings left as placeholders for the next passes.
- **Why:** GROUND found the Run store write-once, so the lifecycle (FR-1..FR-4) is added as the foundation for items 1-3 and 5; item 5's TTL narrowed per Paperclip's own rule.
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, 3 〈TBD〉 placeholders (§ 9, § 12, § 13)
- **Next recommended:** `challenge-requirements T-020`

### 2026-10-01 · `challenge-requirements` · gaps + redteam on v0
- **Trigger:** pre-freeze critique pass (no stakeholder feedback)
- **Change type:** add (findings only; no FR/BR/NFR text edited)
- **Scope:** § 9 Interactions (22 rows: overlap 7 / conflict 1 soft / reuse 8 / isolation 6), § 13 Challenge Findings (13), gap-analysis (15 gaps: 3 red), critique-report CR-1..CR-13
- **Delta:** gap categories touched: business rules, edge cases, NFR, data, integrations, UX, compliance, cross-cutting, stakeholders. Sections with ⚠: BR-1/BR-9, FR-2/3/7/9/13/14/17/20/23.
- **Why:** find-don't-fix pass before enrich/iterate
- **Questions opened:** Q1-Q3 (critical, red gaps), Q4-Q11 (decisions), Q12-Q14 (non-blocking, user-only)
- **Resulting draft state:** v0 - 13 ⚠, 0 answered Q, 2 〈TBD〉 left (§ 12 mirror, § 13 resolutions)
- **Next recommended:** `requirements enrich`, then clarify under delegated authority

### 2026-10-01 · `requirements enrich` · no bump
- **Trigger:** placeholders in v0 (§ 9, § 12, NFR targets)
- **Change type:** edit (placeholders only; Intent, Scope and BR text untouched)
- **Delta:** § 9 filled by the challenge pass; NFR targets were already concrete numbers and are marked proposals in the decision log (a5), not stakeholder-confirmed. Snapshot Open Confirmations kept for facts not verifiable here (resetsAt units, CLAUDECODE guard, output cadence during tools). Grounding re-read: `desktop/sidecar.py:208-245`, `tomlio.py:279-347`, `agent_approvals.py:79-209`.
- **Why:** no source can supply the NFR numbers; delegated authority covers the defaults.

### 2026-10-01 · `requirements iterate` · iteration 0 -> 1
- **Trigger (verbatim):** delegated authority "go wild, do end to end" (2026-10-01); answers Q1-Q11 recorded as delegated defaults (decision-log a1-a16).
- **Classified:** answer-Q x11, challenge-⚠ x13 (CR-1..CR-13), fr, br, edge, data.
- **Delta:** FR-2 (single write of terminal state + annotations; `retry_due`, `retry_of`); FR-3 (attribute-based session view, process_lost vs startup interrupted, Run covers chat until first terminal); FR-4 (`last_turn`, `turn_count`, `Approvals.pending_for`); FR-7 (per-turn cap); FR-9 (nt-only control test in CI); FR-11 (process_exit exit 0); FR-13 (patterns, evidence without Bash, worktree diff-stat); FR-14 (single-flight, exception isolation, off switches); FR-17 (action table); FR-18 (`run-retry` creates a new Run); FR-19..FR-23 rewritten around `claimed_run`; BR-9 narrowed; edge cases and data entities updated; § 12 mirrored; § 13 emptied.
- **Why:** each change traces to a CR id in [[T-020-critique-report]].
- **Gaps closed:** G2-G11, G15 (G14 accepted; G1, G12, G13 accepted). **Questions answered:** Q1-Q11. **Opened:** none new (Q12-Q14 stay open, non-blocking).
- **Resulting draft state:** v1 - 0 ⚠, 11 answered Q, 3 open non-blocking Q.

### 2026-10-01 · `challenge-requirements` · pass 2 on v1 (no bump)
- **Change type:** add findings only (CR-14..CR-18): quota wait horizon, record-before-kill, human-stop discriminator, verifier on escalated ticket, automatic actors via verb handlers.
- **Resulting draft state:** v1 - 5 ⚠ pending.

### 2026-10-01 · `requirements iterate` · iteration 1 -> 2
- **Trigger (verbatim):** pass-2 findings CR-14..CR-18, no new stakeholder input.
- **Classified:** challenge-⚠ x5; fr, br.
- **Delta:** FR-12 parse horizon vs FR-15 `quota_max_wait_secs` (6 h); FR-14/FR-7 record-then-kill with an ordering AC; FR-3 `stop_requested`; FR-25 verifier + fixer stop on `review.escalated`; BR-12 automatic actors use `ticket_comment`/`tracker_add`, thread and `run-watch` share one tick; FR-17 posts via `ticket_comment`.
- **Gaps closed:** none new. **Resulting draft state:** v2 - 0 ⚠, 0 open blockers.
- **Next recommended:** `requirements freeze`

### 2026-10-01 · `requirements freeze` · FROZEN at iteration 2
- **Checklist:** 10/10 pass (placeholders only in legend text; 18 findings resolved; 0 open red gaps; critical questions Q1-Q3 resolved; 25/25 FRs have AC; 11 NFRs with targets; entities referenced; out-of-scope non-empty; sign-off = delegated authority; interactions populated).
- **Wrote:** `T-020-requirements.md` (25 FR, 11 NFR, 13 BR). Draft frontmatter `frozen`.
- **Handoff:** @planner -> `requirements T-020 stories`

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| 1 | 2026-10-01 | pass | 0 (0 findings, 0 critical Q, 0 red gaps; Q12-Q14 open non-blocking) | `requirements T-020 freeze` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `T-020-requirements-draft.md`. The draft is mutable by design; this log plus git history is the source of truth.

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements-draft]] · [[T-020-context-snapshot]] · [[T-020-gap-analysis]] · [[T-020-iteration-log]] · [[T-020-decision-log]] · [[T-020-critique-report]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
