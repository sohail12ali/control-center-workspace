---
tags: [active]
status: Open
ticket: "T-040"
---

# T-040: Routines board and Run now: schedules with last-run status

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-06  
**Due:**  

## Overview

From the MAPS video ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]): a routines board and a play button.

Scope:
1. **Routines board.** A panel listing every schedule from `console/config/schedules.toml` (id, cron, verb, enabled, next run) with the status of its last run from the job records (`console/.cache/jobs/`, `console/server/jobs.py`): done, error, interrupted, cancelled, or never run. Built on the existing "Scheduled" and "Jobs" panels (`console/static/overview.js:176-251`) and `console/server/schedules.py`; do not duplicate them.
2. **Run now.** A per-routine button that submits the routine through the existing `/api/jobs` path under the same concurrency cap (2) and the schedule's `confirm` flag. **No `.claude/queue/` file drop** (the video's mechanism; the console already has a job system).
3. Panel timestamps follow [[T-039-summary]]'s freshness option once it exists.

Caveat to keep visible in the UI: nothing fires while the console is not running (`schedules.py` docstring; the Scheduled panel already says so). "Runs while the laptop is closed" needs an always-on host, which is out of scope.

## Current State

GROUND not started. Findings come from a read-only code pass and must be re-verified in `analyze`. User decisions of 2026-10-06 are recorded in the dossier. Only two schedules exist and both are parked, so the board will often be nearly empty: the analyst should decide between an honest empty state and also unparking a harmless schedule (an ASK for the user).

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-039-summary]] · [[T-041-summary]] (the checker is a candidate routine) · [[T-023-summary]] (agent runs and wakeups)
- [[T-040-summary]] · [[T-040-analysis]] · [[T-040-requirements]] · [[T-040-decision-log]] · [[T-040-plan]] · [[T-040-progress]] · [[T-040-verification]]
