---
tags: [active]
status: Done
ticket: "T-008"
---

# T-008: Hands-free listening: wake word, echo handling, barge-in

**Status:** Done  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-07  
**Due:**  

## Overview

Push-to-talk without the press. Turn it on from the tray (or
`POST /listen {"mode":"hands_free"}`) and talk when you want to; the wake word
is what tells the assistant a sentence was meant for it.

The design answers the three things an always-on microphone raises that
push-to-talk does not:

- **The room does not go to a model.** Audio is transcribed on this machine and
  the transcript is discarded unless it starts with the wake word. The check
  sits between transcription and the send, which is what makes that true
  rather than merely claimed.
- **The assistant does not hear itself.** Listening pauses while a reply is
  read aloud; a setting keeps the microphone open for headphones, which is
  what makes barge-in work by voice. It also pauses while an approval card is
  open — that one is not configurable.
- **It does not run forever.** A session stops on its own after
  `hands_free_max_minutes` and says why.

## Current State

Shipped and verified live: an overheard sentence was discarded, an addressed
one reached the console. pytest 1070 passed, cargo test 97 passed. The live
run also found and fixed a latent bug in the shared send path — `201 Created`
(the first message of a new chat) was being reported as a failure.

Follow-up, not in this ticket: VAD tuning. On a noisy microphone a take runs
to its 20-second cap instead of ending on silence, which makes replies feel
slow.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
