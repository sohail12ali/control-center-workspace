---
tags: [active]
status: Open
ticket: "T-041"
---

# T-041: Nightly link checker: flag artifact-map and Links entries that moved

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-06  
**Due:**  

## Overview

From the MAPS video ([[INV-2026-10-06-maps-os-ui-adoption-dossier]]): a nightly check that flags signposts pointing at files that have moved, plus the rule "every fact has exactly one home".

Scope:
1. **A link/signpost checker** over `knowledge-center/artifact-map.md` rows and every ticket's `## Links` block: each wikilink must resolve to a file, each artifact must have a Links block, and no sibling link may be one-way. One command, non-zero exit on any problem, human-readable output. Reuse the wikilink resolution already in `console/server/vault.py` (`_extract_wikilinks`, basename match) and the structure of `console/server/harness_lint.py`; the `validate-artifacts` skill already defines the manual rule.
2. **Scheduling.** Register it as a routine in `console/config/schedules.toml`, parked until the user unparks it (like the existing `harness-lint` entry), so it can run nightly while the console is up.
3. A one-home check is only in scope if it can be made deterministic (analysis decides); do not invent heuristics for duplicated prose.

Known cases it should catch (found while building T-031..T-037): artifact sets whose frozen files lack sibling links, and progress files with fused `## Links` lines.

## Current State

GROUND not started. Findings come from a read-only code pass and must be re-verified in `analyze`. User decisions of 2026-10-06 are recorded in the dossier. Open points: which link forms count (wikilinks only, or also relative markdown paths); how to treat links from frozen files; whether the output feeds the Vault graph or the Needs-repair list ([[T-039-summary]]).

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-040-summary]] · [[T-039-summary]] · [[T-038-summary]]
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]]
