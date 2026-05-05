---
name: clarify
description: Resolve open questions on an artifact through targeted user conversation. Distinct from `requirements` (which drafts) — `clarify` closes ambiguity into decisions. Use whenever an artifact has unresolved Qs blocking the next stage.
---

# Inputs
- `id` (required): ticket id
- `target` (optional): `requirements` | `plan` | `analysis` (default: whichever has open Qs)

# Steps
1. Pull all open questions from target file and `manage-questions` queue.
2. Group by theme; ask user the smallest set that unblocks the stage (≤5 at a time).
3. For each answer, append to `decision-log.md`: Context / Choice / Alternatives / Rationale.
4. Patch the target file to remove resolved ambiguity (replace placeholders, rewrite vague clauses with the metric the user gave).
5. Update `manage-questions` queue: mark resolved, link to decision.

# Output
List of resolved Qs and the patched section refs.

# Rules
- Don't invent answers; if the user defers, mark Q as `deferred` not resolved.
- One decision per Q. Bundle only when Qs are truly the same axis.
- After clarifying, re-run `validate(target)` before advancing stage.
