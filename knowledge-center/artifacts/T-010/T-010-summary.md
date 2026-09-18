---
tags: [active]
status: Done
ticket: "T-010"
---

# T-010: Voice responsiveness: HUD, cues, adaptive VAD, faster STT

**Status:** Done  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-07  
**Due:**  

## Overview

Two complaints, one ticket: you couldn't tell whether it was working, and it
took too long.

**Now you can see it.** A small panel appears near the tray while you talk —
a level meter that moves with your voice, then what it heard, then the reply —
and two short tones mark the microphone actually opening and the take being
sent. The transcript appears before the answer does, so "did it get that
right" is answered first.

**And it is about five times faster.** A spoken command went from **29.7 s**
to **5.3 s**, click to answer. Three separate causes, each measured rather
than guessed:

- **5.7 s of every take was spent waiting for a mutex.** `tray_link` held the
  assistant's lock across a three-second reconnect sleep, so opening the
  microphone queued behind it — twice per take.
- **Takes ran to their 20-second cap** because the detector's thresholds were
  fixed and this microphone's noise floor sits above them. It now measures the
  room first, and needs three speech frames in a row rather than one, so a tap
  or a fan can no longer hold a take open.
- **Transcription was using whisper's defaults.** Greedy decoding and every
  core: 2 854 ms → 2 209 ms on a fixed file, byte-identical transcript.

Also: hands-free now opens the microphone once per session instead of per
take, and the tray's *Mute replies* finally writes the setting that actually
decides whether replies are spoken — the two used to disagree, so the tray
could read "muted" while the assistant talked.

## Current State

Shipped and verified: cargo test 123, pytest 1088, harness lint clean, plus
live runs with before/after numbers from the shell's own log.

Not fixed, and written down: push-to-talk still waits ~0.9 s for WASAPI to
open the microphone (the tone is what covers it), and the wake word depends on
the recogniser catching the first word.

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
