---
name: standup
description: Cross-ticket digest from artifact-map + per-ticket summaries. Active / Blocked / At-risk / Closed-this-period. Use daily, at sprint boundaries, or when context is unclear.
---

# Inputs
- `since` (optional): ISO date or `1d` / `7d` / `30d` (default `1d`)
- `tags` (optional): filter by `summary.md` tags (e.g. `urgent`)

# Steps
1. Read `knowledge-center/artifact-map.md` for ticket inventory.
2. For each ticket, read `summary.md` (Status, tags, Current State) and last entry of `progress.md`.
3. Group:
   - **Active**: Status=In Progress, last progress within `since`
   - **Stale**: Status=In Progress, last progress older than `since`
   - **Blocked**: Status=Blocked
   - **At-risk**: any unmitigated high×high risk in plan.md (via `risk-scan`)
   - **Closed**: Status=Complete, closed within `since`
4. Render a one-screen table.

# Output
Markdown digest. Optionally writes to `knowledge-center/standups/{DATE}.md` if user asks.

# Rules
- Read summaries, not full artifacts. This skill is fast by design.
- Don't auto-write the standup file; output to chat unless requested.
