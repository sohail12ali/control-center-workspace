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

**Appended by:** `requirements` (draft/enrich/iterate/freeze), `challenge-requirements`

**One entry per command invocation that changed the draft.** If a command only read state, do not add an entry.

**Conventions:**
- **Iteration** increments only when `requirements iterate` applies new stakeholder feedback. Other commands record under the *current* iteration.
- **Change type:** `add | edit | remove | defer | accept-⚠ | answer-Q`

---

## Iteration 0 — initial draft

### {DATE} · `requirements draft` · v0 created
- **Trigger:** stakeholder intent: _verbatim quote_
- **Change type:** add
- **Scope:** whole document
- **Delta:** created draft from template; populated Intent + seed sections
- **Why:** baseline draft to iterate from
- **Resulting draft state:** v0 — 0 ⚠, 0 answered Q, N 〈TBD〉
- **Next recommended:** `analyze {ID}` if not run, then `challenge-requirements {ID} (gaps dimension)`

---

## Freeze attempts

| Attempt | Timestamp | Result | Blockers remaining | Command |
|---|---|---|---|---|
| | | | | `requirements {ID} freeze` |

---

## Rollback

To see the draft at a past iteration, use `git log` on `{ID}-requirements-draft.md`. The draft is mutable by design — this log plus git history is the source of truth.

## Links
- [[{ID}-summary]] · [[{ID}-analysis]] · [[{ID}-requirements-draft]] · [[{ID}-context-snapshot]] · [[{ID}-gap-analysis]] · [[{ID}-iteration-log]] · [[{ID}-decision-log]] · [[{ID}-plan]] · [[{ID}-progress]] · [[{ID}-verification]]
