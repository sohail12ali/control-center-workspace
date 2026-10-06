---
tags: [active]
status: Open
ticket: "T-032"
---

# T-032: Hear me properly: pause-tolerant endpointing, junk filter, wav-replay seam

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Make the pipeline stop cutting the user off and stop hearing things that were never said ([[INV-2026-10-05-micdrop-adoption-dossier]]).

Scope (dossier ids): **B9** headless wav-replay seam (a file source and file sink, so the pipeline can be driven with no mic) — **build this first** so the other two are verified on real audio · **B3** pause-tolerant endpointing (provisional end, wait for resumed speech, merge + re-transcribe, capped merges; reference `vad.rs` / `assembler.rs` in Mic Drop) · **B4** Whisper junk filter (sound tags, hallucinated "Thank you." on silence, punctuation-only output; reference `speech.rs:115-150`).

B9 also unblocks T-019 AC-7 and AC-8, which are pending "a real voice".

Out of scope: Silero VAD (B6), echo cancellation (T-035).

## Current State

**2026-10-06 (corrected):** GROUND and CLARIFY are done: [[T-032-analysis]] is written and [[T-032-requirements]] is **frozen** (FR-1..20, NFR-1..4, AC-1..15; decisions D-1..D-9 in [[T-032-decision-log]]), with user stories in [[T-032-user-stories]] and a 14-task plan in [[T-032-plan]] (T-032-01..14, none built; order: wav-replay seam first, then endpointing, then the junk filter). The harness run that produced these stopped without a report, so `T-032-progress.md` is nearly empty, handoffs are not logged, and it is not confirmed that the plan was challenged. No code exists. Lane is `open`. Resume with a fresh harness that rebuilds state from these artifacts; see [[handoff-2026-10-06-pending-work]].

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Previous: [[T-031-summary]] · Next: [[T-033-summary]] · Related: [[T-019-summary]]
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
