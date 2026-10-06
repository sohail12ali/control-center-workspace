---
tags: [active]
status: Verify
ticket: "T-039"
---

# T-039: Needs you panel and panel freshness: human-only list, timestamps, STALE marks

**Status:** Verify  
**Stage:** VERIFY  
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

GROUND and CLARIFY done 2026-10-06. Requirements frozen at iteration 1: 14 FRs, 44 ACs (24 [PY], 20 [BROWSER]), 12 NFRs ([[T-039-requirements]]), with amendments A1 (NFR-8) and A2 (AC-5.1) recorded in [[T-039-decision-log]]. Plan: [[T-039-user-stories]] (7 stories), [[T-039-plan]] (12 tasks). Build tasks T-039-01..11 are done; T-039-12 (the [BROWSER] checklist) is the parent's and is pending. Lane `verify`. Verifier result ([[T-039-verification]]): 24 of 24 [PY] criteria pass; of 20 [BROWSER] criteria, 7 are partly observed by the parent session and 12 are not verified in a browser; defect D-A (Enter on the Refresh button swallowed by `rowNav`, found by reading) is now fixed at source level, pending a browser re-check. `close-check` is blocked by the [BROWSER] criteria and task T-039-12. Q1 and Q2 defaults are applied and still open as owner questions. `close-work` not run; `review-round` not recorded.

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-040-summary]] · [[T-038-summary]] · [[T-037-summary]] (shares `styles.css` and `core.js`)
- [[T-039-summary]] · [[T-039-analysis]] · [[T-039-context-snapshot]] · [[T-039-requirements-draft]] · [[T-039-requirements]] · [[T-039-gap-analysis]] · [[T-039-critique-report]] · [[T-039-iteration-log]] · [[T-039-decision-log]] · [[T-039-user-stories]] · [[T-039-plan]] · [[T-039-progress]] · [[T-039-verification]] · [[T-039-release]]
