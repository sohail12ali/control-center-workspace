---
ticket: "T-016"
artifact: components
---

# Components: T-016

**Produced by:** `analyze-components`. **Consumed by:** `breakdown-tasks`.

## Data layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| Run store | json files | Tagged-union Run records in `console/.cache/runs/` | — | 2 | FR-2 | done |

## Service layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| Mutation verbs | verb rows | ticket move/set, tracker add/update | `tickets.py`, `trackers.py` | 1 | FR-5 | done |
| Delegate wrap | verb/handler | `console_delegate` writes a Run | Run store, `agent_manager` | 2 | FR-2 | done |
| Harness launch | verb | `cursor-agent` + persona → chat Run | Run store, `agent_backends` | 2 | FR-6 | done |
| Assistant tab plugin | plugin | `register_tab` + home payload (runs, tickets) | Run store, `assistant_feature` | 3 | FR-1 | done |

## UI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| in-shell nav sort | js | Assistant first iff `html.in-shell` | Assistant tab plugin | 3 | FR-1 BR-4 | done |
| Board start-run | js | Replace `startAgentFor` | Run store / Assistant `say` | 4 | FR-3 | done |
| Agents inspector | js | List Runs; keep chat resume | Run store, `agents.js` | 4 | FR-4 | done |

## Docs layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| Wiki + persona | markdown | Fix tray lock; Run-watch line | — | 5 | FR-7 | done |

---

## Dependency graph

```
Mutation verbs (root)
Wiki (root)

Run store (root)
  ├─ Delegate wrap
  ├─ Harness launch
  ├─ Assistant tab plugin
  │    └─ in-shell nav sort (leaf)
  ├─ Board start-run (leaf)
  └─ Agents inspector (leaf)
```

No cycles. Bottleneck: Run store. Critical path: Run store → Assistant tab → in-shell sort (3 components). Verbs and wiki parallelizable with everything.

Suggested build order: Slice 1 verbs → Slice 2 store/delegate/launch → Slice 3 tab/sort → Slice 4 board/inspector → Slice 5 wiki.

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data | 1 | 0 | 0 | 1 |
| Service | 4 | 0 | 0 | 4 |
| UI | 3 | 0 | 0 | 3 |
| Docs | 1 | 0 | 0 | 1 |
| **Total** | **9** | **0** | **0** | **9** |

## Links
- [[T-016-summary]] · [[T-016-requirements]] · [[T-016-plan]] · [[T-016-components]] · [[T-016-task-breakdown]] · [[T-016-implementation-plan]]
