---
ticket: "T-029"
artifact: plan
---

# Plan: T-029

## Approach
Flat, docs-only. Three text edits, each sentence checked against code first.

## Slices

### Slice 1 — Truth pass

## Tasks

### [x] T-029-01 — Rewrite About Agents section and fix agents.js comment (0.5 h)
- [x] `about.js` agentsSect describes live chat; one-shot limits in one sentence
- [x] `agents.js` header comment: ticketed chats use a worktree
- **Done-criteria:** AC-1, AC-4
- **Basis:** audit drift list
- **Depends on:** —

### [x] T-029-02 — README: desktop pointer + four doors section (0.5 h)
- [x] Replace "planned native shell"
- [x] Add "Four doors, one manager" under Architecture
- **Done-criteria:** AC-2, AC-3, AC-5
- **Basis:** audit drift list
- **Depends on:** —

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-029-01 | 0.5 h | two small edits |
| T-029-02 | 0.5 h | one edit + one new section |
| **Total** | **1 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| AC-1, AC-4 | T-029-01 |
| AC-2, AC-3, AC-5 | T-029-02 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Docs-contract test pins README phrases | Low | Low | Kept `**No live steering (one-shot launcher only).**`; run test | Builder |

## Dependencies
- Blocks: —
- Blocked by: —

## Links
- [[T-029-summary]] · [[T-029-analysis]] · [[T-029-requirements]] · [[T-029-decision-log]] · [[T-029-plan]] · [[T-029-progress]] · [[T-029-verification]]
