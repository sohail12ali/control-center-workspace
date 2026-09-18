---
ticket: "T-010"
artifact: requirements
---

# Requirements: T-010

## Functional Requirements
1. While you talk, something on screen shows that the microphone is hearing
   you, then what it heard, then the reply.
2. A tone marks the microphone actually opening, and another marks the take
   being sent.
3. A take ends shortly after you stop talking, in a room with a noise floor.
4. Transcription is faster, with the same words out.
5. The whisper model is a named choice, not a consequence of what is on disk.
6. Hands-free does not reopen the microphone between takes.
7. One switch decides whether replies are spoken aloud.

## Non-Functional Requirements
1. Every latency claim is measured from the shell's own log, before and after.
2. The overlay has no API access, no token and no polling.
3. The tray, the overlay and the tones move from the SAME event.
4. Push-to-talk must not hold the microphone open when it is not recording.

## Acceptance Criteria
- [x] 1. A take's time is broken down in the log (`checks`, `record`, `stt`,
      `post`), with per-step detail under `CONSOLE_LOG=debug`.
- [x] 2. No state change waits on a lock held across a sleep.
- [x] 3. A take in this room ends on silence, not on the cap.
- [x] 4. One noisy frame per ten cannot hold a take open (unit).
- [x] 5. Decode flags are faster on a fixed WAV with an identical transcript.
- [x] 6. Hands-free opens the microphone once per session.
- [x] 7. `stt_model` selects the model; a path-shaped name is refused.
- [x] 8. The overlay appears on a take, shows level, transcript and state, and
      hides itself.
- [x] 9. The tray's mute writes `speak`, and its initial tick is read from it.

## Out of Scope
- Removing the ~0.9 s microphone open for push-to-talk: the only way is to
  hold the device open, which lights the OS indicator all day.
- Streaming partial transcripts.
- Changing the wake-word rule (see the verification's note on first words).

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
