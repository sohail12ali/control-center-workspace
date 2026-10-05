---
ticket: "T-019"
artifact: plan
---

# Plan: T-019

> **Reconstructed 2026-10-05** from [[T-019-progress]] (2026-09-16 entries). The build ran without a written plan; the two template placeholders that stood here were never real tasks. The tasks below are the work progress records as done ([[T-019-decision-log]] D-6).

## Approach
Move wake detection off the transcript and onto the audio: a ring-buffered capture, then a cheap always-on spotter, then a recogniser opened with pre-roll ([[T-019-summary]] § Overview).

## Tasks

### [x] T-019-01 — Audio and wake pipeline (desktop shell)
- [x] `audio.rs` ring buffer with cursor reads; `record_from`; first-pause grace in `Endpointer`
- [x] `wake.rs` rustpotter spotter: train, forget, samples, sensitivity, live score
- [x] `hands_free.rs` as Armed → Capturing → Dispatch over one open mic; `listen.rs` `take_after_wake`
- [x] `stt.rs` decoder prompt biasing; engine restarts when the prompt changes
- **Done-criteria:** AC-1..AC-5 covered by `cargo test --bins`
- **Depends on:** —

### [x] T-019-02 — Console settings, recorder and diagnostics
- [x] `listen_first_pause_ms`, `listen_preroll_ms` and `wake_sensitivity` with validation, plus a float branch in `_coerce`
- [x] Four passthrough routes; wake recorder and Voice diagnostics panel in Settings
- [x] Live drive against the debug build; two bugs found and fixed (`wake::hint`, `settings.js` `appendChild(null)`)
- **Done-criteria:** AC-6
- **Depends on:** T-019-01

AC-7 and AC-8 are verification steps that need the owner's voice. They are tracked in [[T-019-verification]], not as build tasks.

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
