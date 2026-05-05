---
name: trace-context
description: Load all artifact files for a ticket and surface what's known. Use at the start of every agent turn so the agent works from current state, not stale context.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Resolve `knowledge-center/artifacts/{id}/`.
2. Read whichever exist: `{id}-summary.md`, `{id}-analysis.md`, `{id}-requirements.md`, `{id}-decision-log.md`, `{id}-questions.md`, `{id}-plan.md`, `{id}-progress.md`, `{id}-verification.md`.
3. Walk `[[wikilinks]]` one hop and read linked summaries.

# Output
Compact briefing (≤30 lines):
- Status, Owner, current stage
- Open requirements / unchecked plan tasks
- Latest progress entry
- Open blockers
- Linked tickets

# Rules
- Don't dump file contents; summarize.
- Flag missing-but-expected files for the current stage.
