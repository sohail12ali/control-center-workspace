---
name: trace-context
description: Load a ticket's current state in one call and surface what's known. Use at the start of every agent turn so the agent works from current state, not stale context.
---

# /trace-context

**When:** A ticket is in play and current state must be loaded.
**Order:** Start of every agent turn, before any other skill or output.

Input: `id` (required ticket id).

## Steps

1. **One call:**

   ```
   python console/kanban.py context {id}
   ```

   That returns the whole picture already reduced — lane, owner, blockers,
   unchecked plan tasks, open trackers, artifact inventory, recent progress, and
   spend to date. Read it and proceed.

2. **Only then, and only if needed:** open a specific artifact the digest points
   at. Reading a file the digest already summarised spends tokens to learn what
   you were just told.

3. Walk `[[wikilinks]]` one hop **only when the task depends on a linked
   ticket** — a linked-ticket sweep on every turn is the cost this skill exists
   to remove.

4. Flag missing-but-expected artifacts for the current stage.

## Why one call

Reading the eight artifacts by hand costs roughly **27 KB (~6,700 tokens)** on a
mid-sized ticket. The digest is **~1.7 KB (~420 tokens)** — measured on CC-T001,
a 16x reduction — and it arrives already reduced to conclusions rather than
material you have to reduce yourself, on every turn, identically.

Truncation is always stated. When the digest says a section was capped, that is
the signal to open the artifact; silence means you have the whole picture.

## Fallback

If `console/` is absent, read the artifacts directly per the old procedure:
`{id}-{summary,analysis,requirements,decision-log,plan,progress,verification}.md`
plus `{id}-{questions,bugs,todos}.toml`. Say that you fell back, so the cost is
visible rather than mysterious.

## Output

Chat briefing only (≤30 lines), no files written:

- Status, Owner, current stage
- Open requirements / unchecked plan tasks
- Latest progress entry
- Open blockers
- Linked tickets

**Delegates:** `console` (owns the `context` verb and its CLI).

**Version:** 2.0 — one-call digest via `console context` | **Updated:** 2026-08-29
