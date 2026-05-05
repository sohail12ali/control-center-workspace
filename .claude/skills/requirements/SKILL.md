---
name: requirements
description: CLARIFY-stage. Converts analysis + user intent into a frozen requirements.md (functional, non-functional, acceptance criteria, out-of-scope). Use before planning.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `analysis.md` and any prior `decision-log.md`.
2. Draft `requirements.md`:
   - Functional (capability statements, testable)
   - Non-Functional (perf, security, scalability with thresholds)
   - Acceptance Criteria (checkable, ≥1 per functional req)
   - Out of Scope (explicit exclusions)
3. List unresolved questions.
4. If user resolves, append decisions to `decision-log.md` (Context / Choice / Alternatives / Rationale).
5. Update `summary.md` Status → `In Progress`.

# Output
Path to requirements.md and a numbered list of open questions.

# Rules
- Each requirement must be testable. Reject vague terms ("fast", "user-friendly") — demand a metric.
- Don't proceed to planning while questions are unresolved; route back to user.
