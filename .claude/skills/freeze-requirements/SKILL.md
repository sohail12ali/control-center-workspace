---
name: freeze-requirements
description: Final pre-freeze gate. Runs the freeze checklist; on pass finalizes requirements.md and hands off to extract-stories.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `{id}-requirements-draft.md`, `{id}-gap-analysis.md`, `{id}-questions.md`, `{id}-context-snapshot.md`, `{id}-iteration-log.md`.
2. Run the freeze checklist — fail at the first `✗`:
   - [ ] All `〈TBD〉` placeholders replaced or explicitly deferred with rationale in the section text
   - [ ] All ⚠ challenge findings resolved (removed) or explicitly accepted with `⚠ accepted: {rationale}`
   - [ ] No 🔴 blocker gaps remain in `{id}-gap-analysis.md`
   - [ ] All blocker/critical open questions in `{id}-questions.md` are answered or resolved
   - [ ] Every FR has at least one testable acceptance criterion (no vague modifiers)
   - [ ] Every NFR has a concrete target (number, role, duration) or an explicit "N/A — rationale"
   - [ ] Every new/changed entity has a canonical reference or a plan-to-create note
   - [ ] Out-of-scope list is non-empty (forces an explicit boundary)
   - [ ] Stakeholder sign-off recorded for every "sign-off required: yes" row
   - [ ] Interactions with Existing Features is populated (or explicit "no interactions" + rationale)
3. If any `✗`:
   - Do not freeze.
   - Report exactly which items failed, with section pointers.
   - Suggest the command to run (`identify-gaps` / `challenge-requirements` / `enrich-requirements` / `clarify` / `iterate-requirements`).
   - Append a freeze-attempt row to `{id}-iteration-log.md` (attempt N · fail · blockers remaining).
4. If all `✓`:
   - Set draft frontmatter: `status: frozen`, `freeze_status: frozen`, `frozen_at: {timestamp}`, `frozen_iteration: {N}`.
   - Finalize `{id}-requirements.md` (the scaffolded artifact from `kickoff`; consumable by `extract-stories`): title, frozen timestamp, iteration, Intent, in-scope/out-of-scope bullets, all FRs (condensed: id, title, actor, acceptance criteria checklist), NFR table, data entities table, business rules list, edge cases list, links back to the draft and iteration log.
   - Append a final pass entry to `{id}-iteration-log.md` (attempt N · pass · summary generated).
   - Hand off: `@planner → extract-stories {id}`.

# Output on fail
```
── freeze-requirements ──
Ticket: {id}
Result: ✗ FAIL (attempt {N})
Blockers:
  - [checklist item] {detail + pointer}
Suggested next: {command} {id}
```

# Output on pass
```
── freeze-requirements ──
Ticket:  {id}
Result:  ✓ FROZEN (iteration {N}, attempt {M})
Draft:   {id}-requirements-draft.md → status: frozen
Final:   {id}-requirements.md generated
FRs / NFRs / BRs: {a} / {b} / {c}
HANDOFF: @planner → extract-stories {id}
Next:    extract-stories {id}
```

# Rules
- Checklist runs deterministically — same inputs, same result.
- On fail: no file mutation except the iteration-log freeze-attempt row.
- On pass: `{id}-requirements.md` exists and links back to the draft and iteration log.
- Does not call `extract-stories` itself — only hands off. The user/orchestrator controls the transition.

**Delegates to:** none directly; hands off to `@planner` via `extract-stories`
**Next:** `extract-stories {id}`
