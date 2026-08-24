---
ticket: "{T}"
artifact: task-breakdown
---

# Task breakdown: {T}

Atomic tasks per slice, with acceptance criteria and effort. Task ID format: `{phase}-{slice}-{task}` (e.g. `2-3-2` = Phase 2, Slice 3, Task 2).

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis step), `estimate(mode=forecast)`.

---

## Phase 1: {Phase name}

### Slice 1a: {Slice name}

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1a-1 | | | | | | pending | |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 | | | | | |
| **Total** | | | | | |

---

## Conventions

**Status:** pending · in-progress · done · blocked (see Notes for why).
**Effort:** 0.5 / 1 / 1.5 / 2 / 3h buckets — no micro- or mega-tasks.
**Dependencies:** note in Notes column, e.g. "depends on 1a-1".

## Links
- [[{T}-summary]] · [[{T}-plan]] · [[{T}-components]] · [[{T}-task-breakdown]] · [[{T}-implementation-plan]] · [[{T}-effort-estimate]] · [[{T}-effort-forecast]]
