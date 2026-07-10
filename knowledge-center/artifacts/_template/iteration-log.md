---
ticket: "{ID}"
artifact: iteration-log
status: active
created: "{DATE}"
last_updated: "{DATE}"
current_iteration: 0
---

# Iteration Log: {ID}

> Append-only record of every pre-freeze revision to the requirements draft: what changed, why, and by which command. The draft itself is mutable; this log is the history.

**Appended by:** `draft-requirements`, `iterate-requirements`, `enrich-requirements`, `challenge-requirements`, `compare-with-existing`, `identify-gaps`, `freeze-requirements`

**One entry per command invocation that changed the draft.** If a command only read state, do not add an entry.

**Conventions:**
- **Iteration** increments only when `iterate-requirements` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### {DATE} · `draft-requirements` · v0 created
- **Trigger:** stakeholder intent: _verbatim quote_
- **Change type:** add
- **Scope:** whole document
- **Delta:** created draft from template; populated Intent + seed sections
- **Why:** baseline draft to iterate from
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, N 〈TBD〉
- **Next recommended:** `analyze-context {ID}` if not run, then `identify-gaps {ID}`

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| | | | | `freeze-requirements {ID}` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `{ID}-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[{ID}-summary]] · [[{ID}-analysis]] · [[{ID}-requirements-draft]] · [[{ID}-context-snapshot]] · [[{ID}-gap-analysis]] · [[{ID}-iteration-log]] · [[{ID}-decision-log]] · [[{ID}-questions]] · [[{ID}-plan]] · [[{ID}-progress]] · [[{ID}-verification]]
