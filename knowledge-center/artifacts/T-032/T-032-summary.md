---
tags: [active]
status: Verify
ticket: "T-032"
---

# T-032: Hear me properly: pause-tolerant endpointing, junk filter, wav-replay seam

**Status:** Verify  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Make the pipeline stop cutting the user off and stop hearing things that were never said ([[INV-2026-10-05-micdrop-adoption-dossier]]).

Scope (dossier ids): **B9** headless wav-replay seam (a file source and file sink, so the pipeline can be driven with no mic) — **build this first** so the other two are verified on real audio · **B3** pause-tolerant endpointing (provisional end, wait for resumed speech, merge + re-transcribe, capped merges; reference `vad.rs` / `assembler.rs` in Mic Drop) · **B4** Whisper junk filter (sound tags, hallucinated "Thank you." on silence, punctuation-only output; reference `speech.rs:115-150`).

B9 also unblocks T-019 AC-7 and AC-8, which are pending "a real voice".

Out of scope: Silero VAD (B6), echo cancellation (T-035).

## Current State

**2026-10-06:** All 14 plan tasks (T-032-01..14) are built and SIMPLIFY ran. Lane is `verify`. The independent verifier's disposition is ready_to_close for code and tests (`close-check` ok:true, 0 blocks); see [[T-032-verification]]. 15 of 15 acceptance criteria PASS on synthetic audio; none is verified on real hardware. Evidence: cargo 365 passed (single-threaded and parallel); pytest 1 failed (the known `console/tests/test_stylesheet.py::test_every_class_the_js_styles_actually_exists`, `onboarding-wizard.js: .ob-count`, another ticket's) and 2884 passed.

Open OWNER items: **D-10** (the 300 ms tail trim is unconditional; a one-line alternative is recorded), **D-11** (noise fixture g2 returns fluent junk through the shipped engine; the confidence guard is deferred as TD-1) and **V-7** (feel of the 1.2 s window, audible Sent cue, live-mic regression: only the user can do these). `close-work` has NOT been run and `review-round` is NOT recorded. History and handoff: [[T-032-progress]], [[handoff-2026-10-06-pending-work]].

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Previous: [[T-031-summary]] · Next: [[T-033-summary]] · Related: [[T-019-summary]]
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Also: [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-release]] · [[T-032-requirements-draft]] · [[T-032-user-stories]]
