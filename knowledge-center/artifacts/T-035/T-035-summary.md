---
tags: [active]
status: Open
ticket: "T-035"
---

# T-035: Voice opt-ins and spikes: cloud STT, language, echo-cancelled barge-in

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Opt-in features and time-boxed spikes ([[INV-2026-10-05-micdrop-adoption-dossier]]). Lowest priority; run after T-031..T-034.

Scope (dossier ids): **A6** cloud STT, opt-in and off by default — OpenAI-compatible `base_url`, API key referenced by env-var *name* and never stored; already approved in the desktop-assistant programme but unbuilt · **A7** non-English (language setting + multilingual Whisper; `-l en` is hardcoded in `stt.rs`) · **B5 + C6** spike: echo cancellation (`sonora` AEC3) so voice barge-in works on speakers — time-boxed to 1-2 days, the output is a go/no-go on whether it builds on Windows, macOS and Linux CI, not a shipped feature · **A8 / B7** decision only: whether Kokoro TTS or a typed-phrase wake word justify pulling in sherpa-onnx (default answer: no).

## Current State

GROUND not started. `sonora` cross-platform build status is unverified — that is the point of the spike. Past CI-only defects (RGBA icons, Linux libs, a bypassed test seam, job-object breakaway) argue for running the spike through CI, not just on Windows.

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Previous: [[T-034-summary]] · Related: [[T-019-summary]]
- [[T-035-summary]] · [[T-035-analysis]] · [[T-035-requirements]] · [[T-035-decision-log]] · [[T-035-plan]] · [[T-035-progress]] · [[T-035-verification]]
