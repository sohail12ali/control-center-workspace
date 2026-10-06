---
tags: [active]
status: Verify
ticket: "T-041"
---

# T-041: Nightly link checker: flag artifact-map and Links entries that moved

**Status:** Verify  
**Stage:** VERIFY  
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

Requirements frozen at iteration 1 in [[T-041-requirements]] (15 FRs, 10 NFRs, 36 ACs: 33 `[PY]`, 3 `[MANUAL]`), 13 decisions in [[T-041-decision-log]], plan in [[T-041-plan]] ([[T-041-user-stories]], 7 tasks). Build tasks T-041-01..06 and the docs and real-vault part of T-041-07 are done; lane `verify`. Verifier result ([[T-041-verification]]): 33 of 33 `[PY]` criteria pass; the 3 `[MANUAL]` criteria (AC-34, 35, 36) passed in the parent session's run on 2026-10-06. Two low findings: L1 (`map-row-format` findings carry no `refs`, `link_check.py:~510`, so `--ticket` omits a malformed row for that ticket) and L2 (docstring typo). The nightly schedule `link-check-nightly` stays PARKED. Owner questions Q1 (one-way as WARN) and Q2 (02:30) are open. Follow-up repairs TD-1 (about 34 existing errors) and TD-2 (template Links symmetry) must land before unparking. `close-work` not run; `review-round` not recorded.

## Links
- [[INV-2026-10-06-maps-os-ui-adoption-dossier]] · Related: [[T-040-summary]] · [[T-039-summary]] · [[T-038-summary]]
- [[T-041-summary]] · [[T-041-analysis]] · [[T-041-context-snapshot]] · [[T-041-requirements-draft]] · [[T-041-requirements]] · [[T-041-decision-log]] · [[T-041-gap-analysis]] · [[T-041-critique-report]] · [[T-041-iteration-log]] · [[T-041-user-stories]] · [[T-041-plan]] · [[T-041-progress]] · [[T-041-verification]] · [[T-041-release]]
