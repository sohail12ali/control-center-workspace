---
name: draft-requirements
description: Produces a v0 requirements draft from stakeholder intent, grounded in the codebase and prior artifacts. Pre-freeze. Use before extract-stories when requirements are not yet frozen.
---

# Inputs
- `id` (required): ticket id
- `intent` (optional): rough stakeholder intent in one or two sentences — will prompt if omitted

# Steps
1. Ensure the ticket scaffold exists (`kickoff {id}` if `knowledge-center/artifacts/{id}/` is missing).
2. If `{id}-context-snapshot.md` is missing or stale, invoke `analyze-context {id}` and wait for it.
3. Read `{id}-context-snapshot.md` plus any prior notes in the ticket directory.
4. Copy `knowledge-center/artifacts/_template/requirements-draft.md` into `knowledge-center/artifacts/{id}/{id}-requirements-draft.md`.
5. Populate v0:
   - **Intent** — echo stakeholder intent verbatim + one-line interpretation.
   - **Context Summary** — condense from the context snapshot, with wikilinks.
   - **Scope** — best-guess in-scope / out-of-scope; mark assumptions explicitly.
   - **Functional Requirements** — derive 3-8 candidate FRs from intent.
   - **Non-Functional Requirements** — seed categories with `〈TBD〉` targets.
   - **Data** — list entities touched (from context snapshot), wikilinked if a canonical note exists.
   - **Business Rules** — extract implicit rules from intent; number each `BR-{n}`.
   - **Edge Cases** — seed from similar-feature history in the context snapshot.
   - **External Dependencies** — list any external systems named in context.
   - **Open Questions** — add a placeholder question for every assumption.
6. Set frontmatter `iteration: 0`, `status: drafting`, `freeze_status: open`.
7. Append an initial entry to `{id}-iteration-log.md` describing what was drafted.
8. Append any new open questions to `{id}-questions.md` (stage: `requirements`).

# Output
```
── draft-requirements ──
Ticket:      {id}
Draft:       v0 created ({id}-requirements-draft.md)
FRs drafted: {N}
NFR slots:   {N} 〈TBD〉
Questions:   {N} opened
Iteration:   0
Next:        identify-gaps {id}  (then challenge-requirements, enrich-requirements, iterate-requirements)
```

# Rules
- Echo stakeholder intent verbatim in the Intent section — never paraphrase supplied copy.
- Every guess is marked explicit in Scope or logged as an open question — no silent assumptions.
- v0 may use `〈TBD〉` for NFR targets and AC stubs; don't drop template sections to save space.
- If the context snapshot is empty, fail and request `analyze-context {id}` first — don't draft ungrounded.
- One template, one draft file — don't invent parallel requirement files.
- End with the `## Links` block per `CLAUDE.md` § Filename and linking convention.

**Delegates to:** `analyze-context`, `kickoff`
**Next:** `identify-gaps` → `enrich-requirements` → `iterate-requirements` → `challenge-requirements` → `freeze-requirements` → `extract-stories`
