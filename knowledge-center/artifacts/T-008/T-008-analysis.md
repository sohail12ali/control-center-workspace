---
ticket: "T-008"
artifact: analysis
---

# Analysis: T-008

## Context

T-006 gave the shell a microphone: press a hotkey, talk, and the transcript
becomes a turn. This ticket removes the press. That is a one-line change to
the trigger and a large change to what the feature *is*, which is why the work
here is mostly about the consequences rather than the loop.

## Current State

- `listen::take` records, ends the take on silence or a cap, transcribes with
  a local whisper.cpp model, and POSTs the transcript to the console.
- The tray reflects listening/thinking/speaking through `tray_state`.
- `tts::finished()` already says whether a reply is being read aloud, and the
  assistant state already knows when an approval card is open — both were
  built for other reasons and are exactly what a hands-free loop needs.

## Key Findings

- **The privacy question is a question about ordering, not about a feature.**
  Transcription is already local. So "does leaving the mic on send the room to
  a model?" is decided by where the wake-word check sits: before the POST, the
  answer is no; after it, the answer is yes no matter what the UI says.
- **Echo is a real failure mode, not a theoretical one.** Through speakers the
  assistant hears its own reply, transcribes it, and answers it. This is why
  pausing while speaking has to be the default, and why the headphone case
  needs its own setting rather than a shared one.
- **An approval card is a different pause for a different reason.** Someone
  reading "allow this?" out loud must not have that recorded as their next
  instruction, and that has nothing to do with echo — so it must not be
  switched off by the headphone setting.
- **A microphone left on is its own bug.** A time cap is cheap and is the
  difference between a feature you can leave on and one you have to remember.
- **No new pipeline is needed.** Every piece exists; this is a loop plus three
  policies.

## Research

Checked against the shipped push-to-talk path (`listen.rs`), the settings pair
(`assistant_config.py` + `assistant.toml`), the tray (`tray.rs`, and the T-006
bug where the tray showed idle with the microphone open), and the native
bridge's existing `POST /listen` modes.

## Recommended Path

Add the gate inside `listen` via a closure, put the loop and the policies in
their own module, surface it as a tray checkbox and two bridge modes, and make
every default the cautious one. Test the wake-word rule against **real**
recogniser output rather than typed strings, and run the whole thing live at
a microphone before calling it done.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
