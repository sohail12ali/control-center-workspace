---
ticket: "T-013"
artifact: decision-log
---

# Decisions: T-013

## the-text-is-fixed-before-the-voice
**Decision:** `speech_text` is its own module, applied to every spoken reply,
regardless of which backend speaks it.
**Rationale:** A neural voice reading "asterisk asterisk T dash zero one zero"
still sounds like a machine. The text was half the complaint and none of the
cost — no download, no dependency, pure and testable.
**Impact:** The rules are opinions, so they live in a test file where they can
be argued with.

## piper-preferred-os-voice-fallback
**Decision:** Piper when installed; `System.Speech` / `say` / `spd-say`
otherwise, and `/health` names which.
**Rationale:** The same bargain whisper.cpp already struck for listening: a
deliberate fetch, a gitignored directory, no cloud, and nothing breaks when it
is absent.
**Impact:** `tts` becomes the choice between backends; `piper` owns playback.

## stream-the-pcm-rather-than-write-a-wav
**Decision:** `--output_raw` into a cpal output stream, resampled by linear
interpolation.
**Rationale:** A temp file plus a player would add a disk round trip and a
spawn to every reply — for a two-second utterance, most of the latency. And
killing the child mid-stream is what makes barge-in immediate.
**Impact:** ~80 lines of playback, and a six-line resampler for the 22.05 kHz
model into a 48 kHz device — the same argument as the capture side.

## tell-the-model-when-it-will-be-heard
**Decision:** A "this reply will be read aloud" section is added to the
injected context, but only when `speak` is on.
**Rationale:** The best markdown stripper still cannot turn a table into a
sentence. Asking for prose in the first place is better than repairing it.
Adding it unconditionally would shorten replies for an audience that is not
listening.
**Impact:** One conditional section in `_compose_extra`, with tests both ways.

## a-house-style-for-chats-that-have-no-persona
**Decision:** `console/config/house-style.md`, capped at 1,200 characters, is
appended to every chat this console starts.
**Rationale:** An agent chat's tone belongs to the CLI's own system prompt, and
`system_append` is the console's only channel into it. Used sparingly and
capped, because a page of tone instructions would crowd out the task.
**Impact:** Emptying the file switches it off — and that is a tested path, not
a claim.

## Links
- [[T-013-summary]] · [[T-013-analysis]] · [[T-013-requirements]] · [[T-013-decision-log]] · [[T-013-plan]] · [[T-013-progress]] · [[T-013-verification]]
