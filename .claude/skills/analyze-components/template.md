---
ticket: "{T}"
artifact: components
---

# Components: {T}

Tracks every component this ticket touches, its dependencies, and its build status. Layers below are examples — rename/remove/add to match what this project actually has (e.g. a CLI-only project might have just "core logic" and "CLI layer").

**Produced by:** `analyze-components` (which also builds the dependency graph below in the same pass). **Consumed by:** `breakdown-tasks` (tasks + implementation-plan synthesis).

---

## Data layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| {Name} | table/migration/schema | | | | | pending |

## Service layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| {Name} | endpoint/service/repository | | | | | pending |

## UI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| {Name} | view/component/view-model | | | | | pending |

---

## Dependency graph

```
{ComponentA}
  └─ calls {ComponentB}
      └─ reads/writes {ComponentC}
```

---

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data | | | | |
| Service | | | | |
| UI | | | | |
| **Total** | | | | |

## Links
- [[{T}-summary]] · [[{T}-requirements]] · [[{T}-plan]] · [[{T}-components]] · [[{T}-task-breakdown]] · [[{T}-implementation-plan]]
