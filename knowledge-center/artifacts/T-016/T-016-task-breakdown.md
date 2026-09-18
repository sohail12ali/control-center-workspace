---
ticket: "T-016"
artifact: task-breakdown
---

# Task breakdown: T-016

Task ID format: `{phase}-{slice}-{task}`. Plan.md also uses T-016-0N aliases.

**Produced by:** `breakdown-tasks`.

---

## Phase 1: Kernel verbs

### Slice 1a: Ticket + tracker verbs

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1-1-1 | `ticket-move` + `ticket-set` verb rows, handlers, tests | Mutation verbs | FR-5 | MCP lists tools; invalid lane errors like `tickets.move`; pytest | 2 | done | alias T-016-01; independent; actual ~2 h |
| 1-1-2 | `tracker-add` + `tracker-update` verb rows, handlers, tests | Mutation verbs | FR-5 | MCP lists tools; `needs_confirm`; pytest | 2 | done | alias T-016-02; independent of 1-1-1; actual ~2 h |

---

## Phase 2: Runs

### Slice 2a: Store and launch

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2-1-1 | Run JSON store create/get/list + states | Run store | FR-2 | Durable under `.cache/runs/`; interrupted ≠ done; pytest | 3 | done | alias T-016-03 |
| 2-1-2 | Wrap `verb_handlers.delegate` to write a Run | Delegate wrap | FR-2 | Delegate returns chat + run id; pytest | 2 | done | alias T-016-04; depends on 2-1-1 |
| 2-1-3 | Harness launch verb: `cursor-agent` + persona | Harness launch | FR-6 | Missing binary named fail; no claude fallback; pytest | 3 | done | alias T-016-05; depends on 2-1-1 |

---

## Phase 3: Home

### Slice 3a: Assistant tab

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3-1-1 | `register_tab` + home UI (talk, runs, ticket strip) | Assistant tab plugin | FR-1 | Tab exists; `say` unchanged; pytest/JS smoke | 3 | done | alias T-016-06; depends on 2-1-1 |
| 3-1-2 | Frontend: Assistant first iff `html.in-shell` | in-shell nav sort | FR-1 BR-4 | Browser Overview first; shell Assistant first | 1.5 | done | alias T-016-07; depends on 3-1-1 |

---

## Phase 4: Other surfaces

### Slice 4a: Board and inspector

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4-1-1 | Replace `startAgentFor` | Board start-run | FR-3 | Not compose+go(agents) only; ticket-scoped | 1.5 | done | alias T-016-08; depends on 2-1-1, 3-1-1 |
| 4-1-2 | Agents list shows Runs | Agents inspector | FR-4 | Same id as delegate; resume still works | 3 | done | alias T-016-09; depends on 2-1-1, 2-1-2 |

---

## Phase 5: Docs

### Slice 5a: Wiki

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 5-1-1 | Amend desktop-assistant.md + assistant.md Run line | Wiki + persona | FR-7 | grep no live-Agents-session tray lock | 1 | done | alias T-016-10; independent |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 | 4 | 4 | 0 | 0 | 100 |
| Phase 2 | 8 | 8 | 0 | 0 | 100 |
| Phase 3 | 4.5 | 4.5 | 0 | 0 | 100 |
| Phase 4 | 4.5 | 4.5 | 0 | 0 | 100 |
| Phase 5 | 1 | 1 | 0 | 0 | 100 |
| **Total** | **22** | **22** | **0** | **0** | **100** |

## Links
- [[T-016-summary]] · [[T-016-plan]] · [[T-016-components]] · [[T-016-task-breakdown]] · [[T-016-implementation-plan]]
