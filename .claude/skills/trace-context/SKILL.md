---
name: trace-context
description: Load all artifact files for a ticket and surface what's known. Use at the start of every agent turn so the agent works from current state, not stale context.
---

# /trace-context

**When:** A ticket is in play and current state must be loaded.
**Order:** Start of every agent turn, before any other skill or output.

Input: `id` (required ticket id).

## Steps

1. Resolve `knowledge-center/artifacts/{id}/`.
2. Read whichever exist: `{id}-summary.md`, `{id}-analysis.md`, `{id}-requirements.md`, `{id}-decision-log.md`, `{id}-questions.toml`, `{id}-plan.md`, `{id}-progress.md`, `{id}-verification.md`.
3. Walk `[[wikilinks]]` one hop; read linked summaries.
4. Summarize — never dump file contents. Flag missing-but-expected files for the current stage.

## Output

Chat briefing only (≤30 lines), no files written:
- Status, Owner, current stage
- Open requirements / unchecked plan tasks
- Latest progress entry
- Open blockers
- Linked tickets

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
