---
tags: [completed]
status: Complete
closed_date: 2026-08-29
ticket: "CC-T004"
---

# CC-T004: Phase 3a - scheduler: cron-driven verbs on the job queue

**Status:** Complete  
**Stage:** Closed  
**Owner:**  
**Created:** 2026-08-29  
**Due:**  

## Overview

Phase 3a — cron-driven verbs, with the running console as the clock. No daemon to install,
and the trade said out loud: nothing fires while the console is down, and missed firings are
skipped rather than replayed.

Scheduled work is ordinary work — it goes onto the same job queue, with the same durable
records, the same gates, and the same honest states.

## Current State

Closed 2026-08-29. 432 tests passing, harness lint clean.

**Phase 3b is blocked on the user**, not on code: exposing the console beyond localhost is a
security decision with several defensible answers, and push notifications need a channel
choice and credentials. Without notifications a remote run stalls at the first gated tool and
the 300-second timeout denies it, so that pair has to be decided together.

## Links
- [[CC-T004-summary]] · [[CC-T004-analysis]] · [[CC-T004-requirements]] · [[CC-T004-decision-log]] · [[CC-T004-plan]] · [[CC-T004-progress]] · [[CC-T004-verification]]

