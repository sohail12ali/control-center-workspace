---
ticket: "T-010"
artifact: analysis
---

# Analysis: T-010

## Context

Two complaints from using the voice loop: you cannot tell whether it heard
you, and a turn takes too long.

## Current State

- Feedback is the tray icon and its tooltip, both five pixels wide in a corner
  nobody is looking at while they talk.
- Two switches disagree about spoken replies: the tray's *Mute replies*
  mirrors the webview's `autoRead` (off by default) while the server-side
  `speak` setting defaults on and speaks through the bridge regardless.
- From the T-009 live log, a spoken command took 29.7 s.

## Key Findings

- **"It feels slow" is three different problems.** The log said: 5.7 s of
  unexplained waiting, 20 s of recording after the speaker stopped, and 2.9 s
  of transcription. Fixing any one alone would still have felt slow.
- **The unexplained 5.7 s was a lock, not the tray.** Inside the repaint
  everything is 0-3 ms; the wait was to acquire the assistant's mutex, which
  `tray_link` held across a three-second sleep.
- **The detector's thresholds were absolute.** On a microphone whose noise
  floor sits above them, `Ending::Silence` can never fire, so every take ran
  to the cap. Measuring the room first is the fix, and a single spurious frame
  still defeats it, which is why a run of frames is required.
- **Opening a microphone is expensive and unavoidable.** 870-2000 ms of
  `build_input_stream`; finding the device is 1-3 ms. The only way to remove
  it is to hold the stream open, which lights the OS indicator — honest for
  hands-free, dishonest for push-to-talk.
- **A cue is worth more than a saving.** Nothing can make WASAPI fast, but a
  tone at the moment the mic goes live turns dead air into "wait for the beep".

## Research

Read `listen.rs`, `audio.rs`, `stt.rs`, `tray_link.rs`, `tts.rs`,
`assistant_reply.py`, `voice.js`, `desktop-tray.js`; ran `whisper-server
--help` before adding a single flag, and benchmarked the ones it actually has
on a fixed WAV.

## Recommended Path

Instrument first and fix what the numbers say — which turned out to be a
mutex, not the tray or the device. Then the detector, then the decoder. Add
the overlay and the tones last, because they are what makes the remaining
second acceptable rather than what removes it.

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
