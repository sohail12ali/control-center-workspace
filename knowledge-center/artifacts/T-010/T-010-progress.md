---
ticket: "T-010"
artifact: progress
---

# Progress: T-010

## Status Summary
Stage: VERIFY — measured before and after, live. See [[T-010-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-010-01 Instrumented the take path; `CONSOLE_LOG=debug` for step detail.
  - T-010-02 Found the real cost: `tray_link` held the assistant's mutex
    across its three-second reconnect sleep, so every shell-side state change
    queued behind it — 2 947 ms per paint, twice a take. Now 4 ms.
  - T-010-03 Detector calibrates to the room, requires a run of speech frames,
    and drifts with the noise floor; cap and silence window are settings.
  - T-010-04 whisper flags verified against `--help` and benchmarked:
    2 854 ms to 2 209 ms, identical transcript. `stt_model` names the model.
  - T-010-05 Overlay panel and tones, both driven from `tray_paint`.
  - T-010-06 Tray mute writes `speak`; initial tick read from settings.
- Corrected mid-run: the first VAD attempt still took 9.4 s for a 3 s phrase
  live — thresholds alone were not enough, which is what `SPEECH_RUN` fixes.
  A mangled CRLF block made the mute POST a silent no-op until the live test
  caught it.
- Verified: 29 665 ms to 5 317 ms end to end; cargo test 123, pytest 1088,
  lint clean.
- Blocked: —
- Next: T-011, session resume.

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
