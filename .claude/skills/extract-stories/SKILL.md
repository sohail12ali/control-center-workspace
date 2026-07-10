---
name: extract-stories
description: Extract user stories from frozen requirements, formatted with acceptance criteria and traceability stubs.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `{id}-requirements.md` (or `{id}-requirements-draft.md` if requirements are not yet frozen — warn that stories built on an unfrozen draft may churn).
2. Identify all user-centric features (not implementation details).
3. Extract or create user stories in the format: `US-{n}: {Title}` — As a {role} I want to {action} So that {benefit}; Acceptance Criteria (checklist); Business Rules (numbered); Edge Cases (numbered).
4. Write `knowledge-center/artifacts/{id}/{id}-user-stories.md` with all stories.
5. Link each story to related components (placeholder — filled by later component/task-mapping steps).
6. Link each story to related tasks (placeholder — filled by task breakdown).

# Output
- `{id}-user-stories.md` created with {N} stories.
- Each story has: story id, priority, status, story points.
- Traceability stubs for components and tasks.

# Rules
- Each story has a clear benefit, not an implementation detail.
- Acceptance criteria are testable, not vague.
- 3-8 stories per ticket is the sweet spot — split or merge if wildly outside that range.
- Stories don't overlap — distinct concerns each.
- End with the `## Links` block per `CLAUDE.md` § Filename and linking convention.

**Delegates to:** none
**Next:** component/task planning (`plan`, `plan-effort`)
