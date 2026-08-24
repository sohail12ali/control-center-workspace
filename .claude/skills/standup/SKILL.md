---
name: standup
description: Cross-ticket digest from artifact-map + per-ticket summaries. Active / Blocked / At-risk / Closed-this-period. Use daily, at sprint boundaries, or when context is unclear.
---

# /standup

**When:** Daily, at sprint boundaries, or when cross-ticket context is unclear.

Inputs: `since` (ISO date or `1d`/`7d`/`30d`, default `1d`) · `tags` (filter by `summary.md` tags, e.g. `urgent`).

## Steps

1. Read `knowledge-center/artifact-map.md` for the ticket inventory.
2. Per ticket, read `summary.md` (Status, tags, Current State) and the last `progress.md` entry — summaries only, never full artifacts; this skill is fast by design.
3. Group: **Active** (In Progress, progress within `since`) · **Stale** (In Progress, older than `since`) · **Blocked** (Status=Blocked) · **At-risk** (unmitigated high×high risk in plan.md § Risks) · **Closed** (Complete, closed within `since`).
4. Render a one-screen table.

## Output

Markdown digest to chat. Write `knowledge-center/standups/{DATE}.md` only if the user asks — never auto-write.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
