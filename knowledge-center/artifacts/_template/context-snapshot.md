---
ticket: "{ID}"
artifact: context-snapshot
status: draft
created: "{DATE}"
last_updated: "{DATE}"
scope: codebase + history
---

# Context Snapshot: {ID}

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze {ID} [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

_One-line restatement of the stakeholder intent this snapshot was gathered for._

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| | | | | |

### Existing patterns to reuse
- _pattern — path_

### Naming and architectural conventions in play
- _convention — where documented_

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| | | | |

### Relevant commits / PRs
- _short sha + subject_

### Known incidents / regressions in this area
- _bullet with date + ticket id_

## 4. External Systems in the Loop

- _system / API / team_

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- _risk — what would have to be true for it to bite_

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. Convert to open questions via `clarify` if any would change the draft.

- _bullet — unverified claim + where we'd confirm_

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| | Grep | | |
| | Read | | |

## Links
- [[{ID}-summary]] · [[{ID}-analysis]] · [[{ID}-requirements-draft]] · [[{ID}-context-snapshot]] · [[{ID}-gap-analysis]] · [[{ID}-iteration-log]] · [[{ID}-decision-log]] · [[{ID}-plan]] · [[{ID}-progress]] · [[{ID}-verification]]
