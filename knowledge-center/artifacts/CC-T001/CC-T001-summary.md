---
tags: [completed]
status: Complete
ticket: "CC-T001"
closed_date: 2026-08-29
---

# CC-T001: Phase 0 - harness foundation: defects, tests, CI, telemetry

**Status:** Complete  
**Stage:** Closed  
**Owner:** Sohail Ali  
**Created:** 2026-08-29  
**Due:**  

## Overview

Phase 0 of the Control Center v3 roadmap. Everything the later phases stand on: the three
config defects fixed, a test suite and CI where there were none, a skill linter, and
per-run token/cost telemetry.

Telemetry is the load-bearing item. Roadmap items #2 (fewer tokens) and #6 (prune unused
skills) are both unfalsifiable without it — this ticket exists so those can be decided on
evidence instead of intuition.

## Current State

Grounded 2026-08-29 across all six workspace repos. Findings are canonical in
[[INV-2026-08-29-control-center-v3-dossier]]; not restated here.

Baseline at kickoff:

| Surface | Baseline |
| --- | --- |
| Tests | 0 |
| CI | none (no `.github/`) |
| `.claude/settings.json` | 5 non-schema keys; no `permissions` block |
| Token/cost telemetry | none |
| Skill lint | none |

## Links
- [[CC-T001-summary]] · [[CC-T001-analysis]] · [[CC-T001-requirements]] · [[CC-T001-decision-log]] · [[CC-T001-plan]] · [[CC-T001-progress]] · [[CC-T001-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
