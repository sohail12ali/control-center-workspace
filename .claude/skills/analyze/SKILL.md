---
name: analyze
description: GROUND-stage analysis. Mode survey (default) writes {T}-analysis.md — current state, findings, recommended path. Mode context deep-scans codebase + prior artifacts into {T}-context-snapshot.md to ground the requirements draft; descriptive only, never invents requirements. Use after kickoff, before requirements drafting, and whenever scope or intent shifts.
---

# /analyze

**When:** A ticket needs a GROUND-stage survey (`survey`), or the requirements pipeline needs grounding (`context`) — before `requirements draft`, and again whenever scope/intent shifts.
**Order:** after `kickoff` → next: `requirements {id} draft`.
**Inputs:** `id` (required); `mode` (optional): `survey` (default) `| context`; `focus`/`scope` (optional): area bias / `codebase | history | all` (default all).

## mode: survey

1. Survey related code/files via Glob+Grep, scoped by `focus`. Read prior artifacts in this and linked tickets.
2. Write `{id}-analysis.md`: Context (3-5 lines) · Current State (file:line citations) · Key Findings (each with significance) · Research (refs) · Recommended Path (one paragraph). Flag assumptions; never invent unstated facts.
3. Update `{id}-summary.md` Current State with a one-line takeaway. Surface open questions in chat.

## mode: context (deep-scan for requirements)

1. Copy `_template/context-snapshot.md` → `{id}-context-snapshot.md` if missing; else update in place.
2. **codebase:** resolve the relevant repo(s) from the ticket's stated scope first (never grep the workspace blind); grep similar features/domain terms; record one representative file per layer the repo actually has; note reusable patterns; cross-reference the target repo's own `CLAUDE.md`/rules.
3. **history:** `git log --oneline --grep` on domain keywords; read prior ticket artifacts under `knowledge-center/artifacts/*/` by keyword; note known issues from `knowledge-center/logs/`.
4. Populate every template section; cite every bullet (path, sha, or ticket id). Fill the Source Log table. Unverified claims go to Open Confirmations, never stated as fact.

## Output

`{id}-analysis.md` (survey) / `{id}-context-snapshot.md` with Source Log + Open Confirmations (context).

Report (context mode):
```
── analyze context ──
Ticket: {id} · Scope: {scope}
Similar features: {N} · Prior tickets: {N} · Source log: {N} · Open confirmations: {N}
Next: requirements {id} draft | requirements {id} enrich
```

**Version:** 2.0 — absorbed analyze-context as mode context | **Updated:** 2026-08-23
