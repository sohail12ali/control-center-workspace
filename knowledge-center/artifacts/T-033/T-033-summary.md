---
tags: [active]
status: Open
ticket: "T-033"
---

# T-033: Talk turn to turn: turn loop, hold-to-talk, mute, spoken summary, audio voice commands

**Status:** Open  
**Stage:** GROUND  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Turn-to-turn conversation with the Assistant ([[INV-2026-10-05-micdrop-adoption-dossier]]).

Scope (dossier ids): **C1** turn loop — mic closed while the Assistant works, reopens after the reply (or a timeout) with no wake word; modes turns / hands-free / push-to-talk, switchable live · **C2** hold-to-talk + rebindable hotkeys (talk / mute / cancel) via Tauri global-shortcut key-up · **C3** mute toggle and pause/resume (`mic_muted` is `available = false` in `desktop/features.toml` today) · **C4** outcome-based spoken summary instead of the first paragraph (`assistant_reply.py`) · **C5** audio-control voice commands in `assistant_commands.py` — repeat, repeat slowly, faster/slower, bigger/smaller model, switch voice, what can I say — keeping the homophone table.

C5's model and voice commands depend on [[T-031-summary]]. Verify with the T-032 wav-replay seam, not by speaking.

Out of scope: live barge-in and echo cancellation (T-035), dictation into other windows (C7, ASK-gated), per-role voices (C8).

## Current State

GROUND not started. Verified: no hold-to-talk, one hardcoded chord, `desktop.hotkey.*` prefs unread, no follow-up window after a reply (the last is explorer-reported).

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Previous: [[T-032-summary]] · Depends on: [[T-031-summary]] · Related: [[T-030-summary]]
- [[T-033-summary]] · [[T-033-analysis]] · [[T-033-requirements]] · [[T-033-decision-log]] · [[T-033-plan]] · [[T-033-progress]] · [[T-033-verification]]
