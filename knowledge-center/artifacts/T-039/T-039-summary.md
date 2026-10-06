---
tags: [active]
status: Open
ticket: "T-039"
---

# T-039: Needs you panel and panel freshness: human-only list, timestamps, STALE marks

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-06  
**Due:**  

## Overview

From the MAPS video ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]): a list reserved for what only a human can resolve, and a freshness stamp on every panel.

Scope:
1. **"Needs you" vs "Needs repair".** `console/server/overview.py:34-96` (`needs_attention`) mixes items that wait for a human (open or answered questions, pending approvals, reviews) with items that need repair (failed or timed-out runs, stale or unowned tickets). Split it into two lists so "Needs you" is the one list that only a person clears; the agent never marks an item done (today's behaviour, now stated and tested). The sidebar badge must say which list it counts.
2. **Panel freshness.** One option on the shared panel helper (`C.panel`, `console/static/core.js`): each panel shows its own timestamp and is marked STALE after a threshold, instead of hiding or silently showing old data. Apply it to the Overview panels first.
3. Preferences, if any (for example the staleness threshold), go through `Console.prefs`.

Out of scope: the routines board ([[T-040-summary]]), the brain views ([[T-038-summary]]).

## Current State

GROUND not started. Findings come from a read-only code pass and must be re-verified in `analyze`. User decisions of 2026-10-06 are recorded in the dossier. Overview and the approvals plumbing (`agent_approvals.py`, `telegram_bot.py`) already exist; this ticket reshapes what they show. Open points for analysis: which existing attention kinds belong to "Needs you"; the STALE threshold per panel; how the static export (`export.py`) shows timestamps.

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-040-summary]] · [[T-038-summary]] · [[T-037-summary]] (shares `styles.css` and `core.js`)
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-requirements]] · [[T-039-decision-log]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]]
