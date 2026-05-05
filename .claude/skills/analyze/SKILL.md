---
name: analyze
description: GROUND-stage context analysis. Surveys current state, surfaces findings, recommends a path. Writes to analysis.md. Use after kickoff and before requirements drafting.
---

# Inputs
- `id` (required): ticket id
- `focus` (optional): area to bias the survey

# Steps
1. Survey related code/files via Glob+Grep, scoped by `focus`.
3. Read prior artifacts in this and linked tickets.
4. Write `artifacts/{id}/{id}-analysis.md`:
   - Context (3-5 lines)
   - Current State (file:line citations)
   - Key Findings (bullets, each with significance)
   - Research (refs)
   - Recommended Path (one paragraph)
5. Update `summary.md` Current State section with a one-line takeaway.

# Output
Path to analysis.md, plus list of open questions for the user.

# Rules
- Findings cite file paths with line numbers.
- Flag assumptions; never invent unstated facts.
