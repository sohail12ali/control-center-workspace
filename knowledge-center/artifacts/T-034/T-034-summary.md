---
tags: [active]
status: Open
ticket: "T-034"
---

# T-034: Voice onboarding and health: wizard Voice step, doctor actions, tray device submenus

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Make voice setup guided and self-diagnosing ([[INV-2026-10-05-micdrop-adoption-dossier]]).

Scope (dossier ids): **D1** onboarding-wizard Voice step — pick the mic with a live level meter, pick a model (downloads via T-031), pick a voice with an audible "did you hear it?" test · **D2** doctor actions on the existing voice diagnostics panel — download missing models, record 2 s, play a tone · **D3** tray Microphone / Speaker / Listening-mode submenus, hot-plug refreshed.

Depends on [[T-031-summary]] (downloads, device pickers, mic test).

**Coordinate before starting:** `console/server/onboarding_setup.py` and `console/static/onboarding-wizard.js` were untracked, uncommitted work on 2026-10-05. Build on them only once they have landed.

## Current State

GROUND not started. Blocked on T-031 and on the onboarding work landing; not yet marked `blocked` on the board because neither has been attempted.

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Depends on: [[T-031-summary]] · Previous: [[T-033-summary]] · Next: [[T-035-summary]]
- [[T-034-summary]] · [[T-034-analysis]] · [[T-034-requirements]] · [[T-034-decision-log]] · [[T-034-plan]] · [[T-034-progress]] · [[T-034-verification]]
