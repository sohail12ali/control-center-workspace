---
ticket: "T-032"
artifact: user-stories
created: "2026-10-05"
---

# User Stories: T-032

Extracted from frozen [[T-032-requirements]] (FR-1..20, NFR-1..4, AC-1..15). Task ids refer to [[T-032-plan]].

**Created by:** `requirements T-032 stories` · **Validated by:** `validate-artifacts T-032 links`

## Stories

### US-1: Replay audio headlessly (B9)

**As a** developer/verifier
**I want to** feed a wav file to the listen loop and capture Piper replies to a wav
**So that** the voice pipeline is testable deterministically with no microphone or speaker.

**Acceptance Criteria:**
- [ ] AC-1, AC-12, AC-13 (FR-1..6)

**Business Rules:**
- Selected only by env `CC_REPLAY_WAV` / `CC_TTS_SINK_WAV`; never a setting, bridge route or UI (D-1).
- Live behaviour unchanged when unset.

**Edge Cases:**
- Exhausted file = "nothing heard"; non-Piper TTS backend with sink set = clear error; any input rate/channels.

**Related Components:** audio.rs, listen.rs, hands_free.rs, piper.rs/tts.rs, desktop/tests/fixtures
**Related Tasks:** T-032-01..05

**Priority:** High
**Story Points:** 8

---

### US-2: Don't cut me off mid-thought (B3)

**As a** voice user
**I want** a short pause inside my sentence not to end my take
**So that** the assistant hears the whole request as one utterance.

**Acceptance Criteria:**
- [ ] AC-2..AC-9 (FR-7..14), AC-14 (FR-19)

**Business Rules:**
- Provisional endpoint 700 ms + merge window 1200 ms (0 = off); max 4 merges; cap 12 s and Release always win; transcribe once.
- Time is audio samples, not wall clock.

**Edge Cases:**
- Clicks in the window do not extend; 3 s gap = two takes; 5 pauses hit the merge cap; trailing silence trimmed to <= 300 ms.

**Related Components:** audio.rs (Endpointer, record_from), listen.rs (`limits_from`), assistant.toml, assistant_config.py
**Related Tasks:** T-032-06..10

**Priority:** High
**Story Points:** 8

---

### US-3: Don't act on Whisper hallucinations (B4)

**As a** voice user
**I want** silence/noise transcripts like "[BLANK_AUDIO]" or "Thank you." ignored
**So that** nothing is sent to the assistant when I said nothing.

**Acceptance Criteria:**
- [ ] AC-10, AC-11 (FR-15..18)

**Business Rules:**
- Pure function, hand-written scanner, no new crate (D-7); bracketed text with a digit is kept ("(T-002)").
- Logs never contain the filtered text.

**Edge Cases:**
- Mixed text keeps its words; bare spoken "thank you" in push-to-talk is dropped (D-6); plausible junk is out of scope (D-9).

**Related Components:** new filter module, listen.rs:531-537, hands_free.rs:398-403
**Related Tasks:** T-032-11..12

**Priority:** Medium
**Story Points:** 3

---

### US-4: Safe, verified delivery (NFR-1..4, AC-15)

**As a** maintainer
**I want** deterministic, dependency-free, non-destructive changes with recorded test counts
**So that** other tickets' uncommitted work is not harmed.

**Acceptance Criteria:**
- [ ] AC-15 (NFR-4); NFR-1..3 evidenced in T-032-05/10/13

**Related Tasks:** T-032-13, T-032-14

**Priority:** High
**Story Points:** 2

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | Replay audio headlessly | Pending | High | 8 | T-032-01..05 |
| US-2 | Pause-tolerant endpointing | Pending | High | 8 | T-032-06..10 |
| US-3 | Junk filter | Pending | Medium | 3 | T-032-11..12 |
| US-4 | Safe verified delivery | Pending | High | 2 | T-032-13, 14 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | audio.rs, listen.rs, hands_free.rs, piper.rs, fixtures | T-032-01..05 |
| US-2 | audio.rs, listen.rs, assistant.toml, assistant_config.py | T-032-06..10 |
| US-3 | filter module, listen.rs, hands_free.rs | T-032-11..12 |
| US-4 | all | T-032-13, 14 |

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-requirements]] · [[T-032-user-stories]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
