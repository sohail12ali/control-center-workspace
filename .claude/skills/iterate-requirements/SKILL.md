---
name: iterate-requirements
description: Apply a round of stakeholder feedback to the requirements draft, log the diff, and bump the iteration counter. Pre-freeze. The only command that bumps iteration.
---

# Inputs
- `id` (required): ticket id
- `feedback` (optional): stakeholder feedback, verbatim — will prompt if omitted

# Steps
1. Read `{id}-requirements-draft.md`, `{id}-gap-analysis.md`, and `{id}-questions.md`.
2. Capture feedback verbatim into the iteration-log entry — stakeholder wording is often load-bearing.
3. Classify each feedback point: `intent | scope | fr | nfr | data | br | edge | integration | stakeholder | challenge-⚠ | answer-Q`.
4. Apply changes **in place** in `{id}-requirements-draft.md` (mutable artifact — no version files):
   - Edit the affected section.
   - If closing a `⚠` challenge finding, remove it from the Challenge Findings section and apply the fix in the original section.
   - If closing an open question, also mark it resolved in `{id}-questions.md`.
   - If closing a gap, also update `{id}-gap-analysis.md` Resolution Log.
5. Bump `iteration: N → N+1` in draft frontmatter; update `last_updated`.
6. Append a full entry to `{id}-iteration-log.md`: trigger (feedback verbatim), change type, scope, delta bullets, why, gaps closed/opened, questions opened/answered, resulting state (⚠ count, 〈TBD〉 count).
7. Re-run the freeze checklist mentally — if it would pass, suggest `freeze-requirements`; otherwise suggest the most effective next pass (`identify-gaps` if blockers may have changed, `challenge-requirements` if wording changed significantly, `enrich-requirements` if new entities were introduced).

# Output
```
── iterate-requirements ──
Ticket:          {id}
Iteration:       {N-1} → {N}
Feedback points: {N}
Changes applied: {N}  (sections: {list})
Gaps closed:     {N}
Gaps opened:     {N}
Questions closed: {N}
⚠ remaining:     {N}
〈TBD〉 remaining: {N}
Next:            {best next pass}
```

# Rules
- Iteration counter increments by exactly 1 per call.
- Feedback is recorded verbatim in the iteration log.
- Every applied change traces to a feedback point (1:N mapping allowed).
- No silent Intent rewrites — if Intent needs to change, call it out explicitly.
- `{id}-questions.md` and `{id}-gap-analysis.md` stay in sync with the draft.

**Delegates to:** `questions` (resolve), `clarify` (if feedback raises new questions)
**Next:** `challenge-requirements` | `identify-gaps` | `freeze-requirements`
