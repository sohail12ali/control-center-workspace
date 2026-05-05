---
name: validate
description: Challenge an artifact (requirements, plan, or verification) for gaps, ambiguity, contradictions, and missing edge cases. Use before freezing requirements, before starting build, and before closing.
---

# Inputs
- `id` (required): ticket id
- `target` (required): one of `requirements`, `plan`, `verification`

# Steps
1. Read the target file plus `summary.md` and any upstream files.
2. For `requirements`: check testability, completeness vs. analysis findings, contradiction with decision-log.
3. For `plan`: check each task has done-criteria, dependencies are real, effort sums match total, risks have mitigations.
4. For `verification`: check every acceptance criterion has evidence, edge cases probed, no green-by-default.
5. Emit a critique list: `severity (block|warn) — issue — suggested fix`.

# Output
Critique list. If any `block` items: caller must address before advancing stage.

# Rules
- Be adversarial. The job is to find what's wrong, not to validate the author.
- Don't rewrite the target; suggest fixes for the owner.
