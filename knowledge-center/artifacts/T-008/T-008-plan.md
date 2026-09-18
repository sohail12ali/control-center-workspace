---
ticket: "T-008"
artifact: plan
---

# Plan: T-008

## Approach

A loop and three policies, not a second voice pipeline. `listen::take` already
records, detects the end of a take, transcribes and dispatches; hands-free
calls it repeatedly and adds one decision in front of the dispatch.

The single structural change is where the wake-word check happens. It sits
**between transcription and sending**, inside `listen`, reached through a gate
closure the caller supplies. That ordering is the whole privacy argument:
unaddressed speech is heard, transcribed locally and dropped, rather than
travelling anywhere to be judged.

## Tasks

### [x] T-008-01 — Settings (1 h)
- [x] Four keys in `assistant_config.DEFAULTS`, all writable, all validated
- [x] Documented in the committed `assistant.toml`
- **Done-criteria:** cautious defaults; a one-character wake word or a
  zero-minute cap is refused; the shipped file and `DEFAULTS` agree
- **Basis:** the existing settings pair; no new file
- **Depends on:** —

### [x] T-008-02 — The gate (2 h)
- [x] `is_addressed` / `should_send` in `hands_free.rs`
- [x] `listen::take_gated`, with `take` delegating to it
- **Done-criteria:** an unaddressed transcript is discarded before `say()`;
  push-to-talk behaviour is unchanged
- **Basis:** T-006's listen path
- **Depends on:** T-008-01

### [x] T-008-03 — The loop (2 h)
- [x] `start` / `stop` / `run`, policy fetched from the console
- [x] `should_pause` for echo and for an open approval card
- [x] Session time cap with a recorded stop reason
- **Done-criteria:** the loop pauses and stops for the stated reasons and says
  which
- **Basis:** T-006's tray state machine
- **Depends on:** T-008-02

### [x] T-008-04 — Surfaces (1 h)
- [x] Tray checkbox whose tick follows the outcome, plus a watcher that
      corrects it when the loop ends by itself
- [x] `POST /listen {mode:"hands_free"|"hands_free_off"}`, state on
      `GET /listen/state`
- [x] `features.toml` row flipped, exact-set test updated
- **Done-criteria:** the registry, the tray and the code agree
- **Basis:** T-002 tray, T-005 bridge
- **Depends on:** T-008-03

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-008-01 — Settings | 1 h | mirrors T-004's settings work |
| T-008-02 — The gate | 2 h | touches `listen`'s send path |
| T-008-03 — The loop | 2 h | new module |
| T-008-04 — Surfaces | 1 h | tray and bridge both established |
| **Total** | **6 h** | |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| 1 | T-008-04 |
| 2, 3, 4 | T-008-02 |
| 5, 6 | T-008-03 |
| 7 | T-008-01 |
| 8 | T-008-04 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| The gate is written but runs after the send | Low | High | It lives inside `listen` before `say()`; the discard is a distinct outcome the loop treats as normal | Builder |
| A recogniser's output defeats the wake-word rule | Med | Med | Tested against real whisper transcripts, not typed strings | Builder |
| The assistant answers its own voice | Med | High | Pause while speaking, on by default | Builder |
| A microphone left on forever | Med | Med | Session time cap, cannot be set to zero | Builder |

## Dependencies
- Blocks: —
- Blocked by: T-006 (voice)

## Links
- [[T-008-summary]] · [[T-008-analysis]] · [[T-008-requirements]] · [[T-008-decision-log]] · [[T-008-plan]] · [[T-008-progress]] · [[T-008-verification]]
