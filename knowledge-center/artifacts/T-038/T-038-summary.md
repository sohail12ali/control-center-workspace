---
tags: [active]
status: Open
ticket: "T-038"
---

# T-038: Command Center: MAPS Agentic OS 3-column UI with 6-view Brain canvas

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-06  
**Due:** 2026-10-10  

## Overview

**Re-scoped 2026-10-06** after a comparison with the existing console ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]). The original text described a new `center` tab with its own server module; that approach duplicates the Vault tab and is **superseded** (its plan file is kept for history and must not be built).

**Decisions (user, 2026-10-06):** extend the Vault instead of building a new tab; whole-workspace graph; four views first.

Scope: brain views as a mode of the existing Vault tab (`console/static/vault.js`, `console/server/vault.py`, `GET /api/vault/graph`):
1. **Richer graph data:** nodes beyond `knowledge-center/` (skills, agents, tickets, routines, runs, the root `CLAUDE.md`) with `area`, `layer`, `kind`, `path`, `note`, `changed`; our own areas and layers in a small config file, not the video's.
2. **Views:** rings, areas, timeline, plus today's force layout as "links"; circle if cheap; **3D orbit deferred**. Pure layout functions in a new `console/static/brain-views.js`; the choice persists through `Console.prefs`. No d3, no CDN.
3. **Interaction:** colour by area, shape by kind, a legend that isolates an area or kind, a node card with note, copy path and fly-to, search with fly-to; reuse the existing hover-dim, viewer column and splitter handles.
4. Decide in analysis whether the Vault joins the static export.

Out of scope here: the Needs-you panel ([[T-039-summary]]), the routines board ([[T-040-summary]]), the link checker ([[T-041-summary]]), the clock, heatmap, deep-work bar, gate countdown and system gauges.

## Current State

**Reset to GROUND (2026-10-06).** The earlier text claimed stage CANONICAL and a ready plan, but `T-038-requirements.md` is still an empty template and no code exists, so the pipeline starts again with the analyst; do not build from `T-038-plan.md`. The Vault already provides the force-directed canvas, hover-dim, search, viewer and size-by-links (evidence in the dossier). Open points: our area/layer mapping (ask the user), whole-workspace node counts and the cost of the O(n^2) force simulation, and static export. This ticket edits `vault.js` and `styles.css`: do not run it in parallel with another ticket touching them.

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-039-summary]] · [[T-040-summary]] · [[T-041-summary]] · [[T-037-summary]]
- [[T-038-summary]] · [[T-038-analysis]] · [[T-038-requirements]] · [[T-038-decision-log]] · [[T-038-plan]] · [[T-038-progress]] · [[T-038-verification]]
