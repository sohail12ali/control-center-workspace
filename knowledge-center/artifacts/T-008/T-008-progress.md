---
ticket: "T-008"
artifact: progress
---

# Progress: T-008

## Status Summary
Stage: VERIFY — built, tested, and run live. See [[T-008-verification]].

## Dated Log

### 2026-09-07
- Done:
  - T-008-01 Settings — four hands-free keys in `assistant_config.DEFAULTS`,
    all writable and validated, documented in the committed `assistant.toml`.
  - T-008-02 The gate — `is_addressed` / `should_send`, and `listen::take_gated`
    so the check runs after local transcription and before the send.
  - T-008-03 The loop — `hands_free::{start,stop,run}`, `should_pause` for echo
    and for an open approval card, session time cap with a recorded reason.
  - T-008-04 Surfaces — tray checkbox plus a watcher that corrects the tick
    when the loop ends by itself; `POST /listen {mode:"hands_free"|
    "hands_free_off"}`; `GET /listen/state` reports it; `features.toml` flipped.
  - Fixed a bug the live run exposed: `listen::say` accepted only `200`, so the
    first message of a new chat (`201 Created`) was reported as a failure.
    Push-to-talk had the same latent bug.
- Verified: pytest 1076 passed, cargo test 97 passed, and a live run where an
  overheard sentence was discarded and an addressed one was sent.
- Blocked: —
- Next: close-work. Follow-up (not this ticket): VAD tuning — on a noisy
  microphone a take runs to the cap instead of ending on silence.

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
