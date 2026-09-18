---
ticket: "T-008"
artifact: requirements
---

# Requirements: T-008

Push-to-talk already works. This ticket removes the press, which is a small
change to make and a large change to live with: a microphone that is always
open raises three problems push-to-talk simply does not have, and these
requirements are mostly about those three.

## Functional Requirements
1. Listening can be turned on and left on, from the tray and over the native
   bridge, and turned off the same way.
2. Speech is transcribed **on this machine** and the transcript is discarded
   unless it is addressed to the assistant by a wake word at the start of the
   utterance.
3. Requiring the wake word can be turned off — a legitimate choice with
   headphones on and nobody else in the room — but only deliberately.
4. Listening pauses while a reply is being read aloud, so the assistant does
   not hear its own voice and answer it. A setting keeps the microphone open
   for headphone use, which is what makes barge-in work by voice.
5. Listening pauses while an approval card is open, regardless of settings.
6. A session stops on its own after a configured number of minutes and records
   why it stopped.
7. The tray tick reflects the microphone's real state, including when the loop
   ended by itself.

## Non-Functional Requirements
1. Every default is the cautious one: wake word required, no listening while
   speaking, a time cap in place.
2. Settings live in the existing `assistant.toml` / settings-override pair —
   no second configuration file and no second TOML reader in the shell.
3. No second voice pipeline: recording, VAD, transcription and dispatch are
   the ones push-to-talk already uses.

## Acceptance Criteria
- [x] 1. Hands-free starts and stops from the tray and from `POST /listen`, and
      `GET /listen/state` reports whether it is on.
- [x] 2. An addressed utterance is sent; an unaddressed one never leaves the
      machine — the gate sits between transcription and the send.
- [x] 3. The wake word matches as a whole word at the start, tolerant of a
      recogniser's punctuation and of "hey"/"ok" in front of it.
- [x] 4. The gate holds against real recogniser output, not hand-typed strings.
- [x] 5. The loop pauses while speaking unless configured otherwise, and always
      while an approval is pending.
- [x] 6. A session ends at the time cap and says so.
- [x] 7. Settings validate: no one-character wake word, no zero-minute cap.
- [x] 8. `features.toml` says hands-free is available, pinned by the exact-set
      test.

## Out of Scope
- A Settings-tab control for these four settings (they round-trip through the
  API; there is no UI for them yet).
- Barge-in by voice while a *model turn* is in flight — pausing covers the
  spoken reply, not interrupting generation.
- Speaker identification. The wake word says something was addressed to the
  assistant, not who said it.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
