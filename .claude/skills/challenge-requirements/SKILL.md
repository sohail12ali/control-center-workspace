---
name: challenge-requirements
description: Adversarial + completeness critique of the requirements draft in one pass — red-team dimensions (ambiguity, contradiction, untestable criteria, unstated assumptions, unrealistic constraints) plus gap analysis (missing stakeholders, business rules, edge cases, NFRs, data flows, integrations, compliance) and existing-feature overlap/conflict/reuse. Pre-freeze, find-don't-fix. Re-run after each requirements iterate pass.
---

# /challenge-requirements

**When:** After `requirements draft` and after any pass that changes draft wording; re-run after each `requirements iterate`; pre-freeze only. Find-don't-fix — records findings, never patches (`requirements iterate` applies fixes). Routed to by `criticize`.
**Order:** after `requirements draft|enrich|iterate` → next: `clarify` (blockers/conflicts) → `requirements iterate`.
**Inputs:** `id` (required); `dimension` (optional): `gaps | redteam | all` (default `all`).

## Steps — gaps dimension (completeness)

1. Read `{id}-requirements-draft.md` + `{id}-context-snapshot.md`. Copy `_template/gap-analysis.md` → `{id}-gap-analysis.md` if missing; else update in place (preserve the Resolution Log).
2. Walk each internal-completeness category, recording gaps with stable `G{n}` ids (auto-increment doc-wide, never reused/renumbered; closed gaps keep their id in the Resolution Log): **Stakeholders** · **Business rules** (quantities, thresholds, ordering, state transitions implied but unstated) · **Edge cases** (concurrency, partial failures, idempotency, empty/over-limit) · **Non-functional** (every `〈TBD〉`/number-less NFR row) · **Data/entities** (FKs, lifecycle, canonical refs) · **Integrations** · **UX/UI** (errors, offline, accessibility) · **Compliance/audit** · **Cross-cutting** (flags, backfill, rollback).
3. **Existing-feature interactions** (same pass): compare each FR against similar entry points, components on the same entities, and prior tickets. Classify: **overlap** (reuse/extend candidate) · **conflict** (would break an existing contract/invariant) · **reuse** (use as-is) · **isolation** (shared terms, distinct flows — document the boundary). Write the table into the draft § Interactions with Existing Features: existing feature (wikilink) | interaction | risk | action (modify/extend/isolate/defer/reject). Populate even at zero. Reuse hits get wikilinked from FR/Data sections. Never rewrite FR text.
4. Severity per gap: 🔴 **blocker** (changes scope/entity shape/FR behavior/NFR targets — every conflict is 🔴) · 🟡 **important** (changes AC or test plan) · 🟢 **minor**. Every 🔴 → `console/kanban.py tracker add {id} questions "..." --set type=requirements --set priority=critical` (conflicts: high-or-critical).
5. Update the gap Summary table (every category row, even 0).

## Steps — redteam dimension (adversarial)

6. Walk every draft section; write findings **inline** in § Challenge Findings (never rephrase source text; no edits to FR/BR/NFR text): **ambiguity** (vague modifiers, undefined pronouns/terms) · **contradiction** (scope↔FR, FR↔BR, FR↔NFR, NFR↔snapshot) · **untestable** (AC without observable outcome, thresholds without numbers) · **unstated-assumption** · **unrealistic-constraint** (targets unsupported by infra per snapshot) · **spof** (single external dependency, no fallback) · **scope-creep** (in-scope not traceable to Intent; out-of-scope re-entering via FR) · **nfr-unmeasurable**.
7. Finding format (grep-able): `⚠ [{kind}] §{section}: {one-sentence issue} — resolution: 〈TBD〉`. Update header counts.
8. Sync `{id}-critique-report.md` per `.claude/skills/challenge-standards/rules.md`: scaffold if missing; map each `⚠` to a `CR-{n}` row (severity default `major`; `critical` for freeze-blocking ambiguity/contradiction); update Summary + "Last run"; point back to draft sections, don't duplicate text.
9. Append iteration-log entry (no bump) listing gap categories touched and sections that received `⚠`.

## Output

- `{id}-gap-analysis.md` — `G{n}` gaps, severities, Summary table, Resolution Log preserved.
- `{id}-requirements-draft.md` — § Interactions with Existing Features table + § Challenge Findings `⚠` lines (the only draft sections written).
- `{id}-critique-report.md` — `CR-{n}` rows per `challenge-standards/rules.md`.
- `{id}-questions.toml` — new entries per 🔴 (CLI only). Iteration-log entry, no bump.

Report:
```
── challenge-requirements ──
Ticket:       {id}
Gaps:         {N}  (🔴 {b} / 🟡 {i} / 🟢 {m})
Interactions: {N}  (overlap {o} / conflict {c} / reuse {r} / isolation {i})
Findings:     {N}  (ambiguity {n} · contradiction {n} · untestable {n} · unstated-assumption {n} · unrealistic {n} · spof {n} · scope-creep {n} · nfr-unmeasurable {n})
Questions opened: {N}
Next:         clarify {id} → requirements {id} iterate "resolutions"
```

**Version:** 2.0 — absorbed identify-gaps as the gaps dimension | **Updated:** 2026-08-23
