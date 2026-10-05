---
ticket: "T-019"
artifact: requirements
---

# Requirements: T-019

> **Reconstructed 2026-10-05**, at the Verify-pile walk ([[T-023-analysis]]). T-019 went from GROUND straight to build, and this file was left as the empty template. Each item below is restated from the five causes in [[T-019-summary]] § Current State, which is the intent the build was aimed at. Nothing here is new scope (see [[T-019-decision-log]] D-6).

## Functional Requirements
1. FR-1: Detect the wake word on the **audio** with an always-on spotter. Unaddressed speech reaches no recogniser (summary cause 1).
2. FR-2: The microphone is never deaf. Audio that arrives while a take is being transcribed or dispatched is kept (cause 2).
3. FR-3: A take that follows the wake word starts **in the past**, with a configurable pre-roll, so the start of the request is not lost (causes 1 and 4).
4. FR-4: Bias the recogniser towards the wake word and ticket ids (cause 3).
5. FR-5: Hands-free gets a first-pause grace so "console … what's open" is not split across two takes. Push-to-talk gets none (cause 4; D-4).
6. FR-6: Settings exposes a wake-word recorder (record / build / remove), sensitivity, pre-roll and first-pause, all validated, plus live voice diagnostics.

## Non-Functional Requirements
1. Spoken turn latency of about 2.5 s end to end, from the end of speech to the start of the reply (summary § Reply speed).

## Acceptance Criteria
- [ ] AC-1 Spotter fires on the trained phrase and not on other speech (FR-1)
- [ ] AC-2 A reader sees audio written while it was away; the ring keeps order and its tail (FR-2)
- [ ] AC-3 Rewind gives back pre-roll audio, clamped to what the ring holds (FR-3)
- [ ] AC-4 The decoder prompt names the wake word and ticket ids (FR-4)
- [ ] AC-5 First-pause grace applies to hands-free only (FR-5)
- [ ] AC-6 Voice settings are validated, and the recorder and diagnostics work against the running shell (FR-6)
- [ ] AC-7 With a wake word recorded in the owner's own voice, saying it into the microphone starts a take (FR-1, real voice)
- [ ] AC-8 A spoken hands-free turn meets the latency target, measured from `host.log` and telemetry (NFR-1)

## Out of Scope
- A separate `voice_backend` (D-5). Silero VAD in whisper-server (verification § Not verified 3).

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
