---
tags: [active]
status: In Progress
ticket: "T-016"
---

# T-016: Make the Assistant the home, and every piece of work a Run you can watch

**Status:** In Progress  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-11  
**Due:**  

## Overview

The Delivery Console is still a human kanban app that later grew an Agents tab, an Assistant, and a desktop shell. Agents and the Assistant already treat it as a backend; the product shape has not caught up.

This ticket inverts that. The desktop shell opens on the **Assistant** (talk, live runs, ticket strip). Boards, Work, Analytics, Vault, and the rest stay, as drawers. Every piece of work is a **Run** the console can start and watch — same object whether it came from the Assistant, the board, a schedule, or MCP. The console can **launch** a harness role as a named run; analyst / planner / builder / verifier still **do the work in Cursor**. T-015 stays in Verify on its own evidence and is not absorbed.

## Scope

**In**

- Product lock: Assistant is home in the desktop shell; other tabs are drawers. Amend [[desktop-assistant]] so it no longer says the tray remotes the Agents tab.
- A durable Run object wrapping today's chats and `console_delegate`, with an inspector (the Agents tab becomes that inspector, not a parallel product).
- Board "Start agent" becomes ask-the-Assistant or create-a-named-Run.
- Console can launch a named harness role as a Run. Cursor remains where those roles actually work (hybrid).
- Verb completeness for agent mutation: ticket move/set, tracker add/update, and whatever else GROUND proves MCP agents currently shell `kanban.py` to do. One mutation API; CLI, chat tools, and MCP stay adapters.

**Out**

- T-015 remaining verify work.
- Deleting tabs.
- Moving harness pipeline execution into the console (no in-console analyst/planner/builder loop).
- New backends, new harness agents, new desktop capture/voice features.
- Letting agents hand-edit `ticket.toml` or tracker TOML.

**Suggested slices** (planning, not committed): A product lock · B Run object · C verb completeness · D Assistant as home in the shell.

## Current State

**VERIFY (2026-09-11):** All 10 plan tasks implemented. Native shell will open on the Assistant tab; browser Overview stays first. Work is a durable Run. Four mutation verbs plus launch-role. Wiki tray lock matches the Assistant. close-work not run.

**GROUND snapshot (2026-09-11, before build):**

- Nav was ten tabs (`NAV_ORDER`). The Assistant plugin had routes and no tab.
- Board Start agent dumped a prompt into the Agents tab.
- MCP could not move a ticket without shelling `kanban.py`.
- Wiki said the tray remoted the live Agents session.

Locked with Irshad on 2026-09-11, recorded in [[T-016-decision-log]]: Assistant as home; hybrid harness; this ticket rather than a wiki-only lock.

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]] · [[T-016-test-cases]]
- Design: [[desktop-assistant]]
- Related: [[T-015-summary]] · [[T-004-summary]] · [[T-014-summary]]
