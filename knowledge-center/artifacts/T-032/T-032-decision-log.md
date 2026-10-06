---
ticket: "T-032"
artifact: decision-log
---

# Decisions: T-032

All made by the analyst as sensible defaults (user asked for defaults, no blocking question); each is reversible by the owner.

## D-1 replay-selected-by-env-not-setting
**Decision:** Replay source and file sink are selected by env vars `CC_REPLAY_WAV` / `CC_TTS_SINK_WAV`, not by an `stt.source`-style setting.
**Rationale:** Settings are writable through the console and Settings tab; a setting that swaps the microphone for an arbitrary file is a privacy/abuse surface and a way to look like a dead mic. Env is process-owner-only and test-friendly. Mic Drop used config (`stt.source`); we deliberately differ.
**Impact:** FR-3/4, NFR-3; settings.js and bridge routes untouched; WARN + `source` in `/listen/state`.

## D-2 frames-abstraction-and-audio-clock
**Decision:** Introduce a cursor/since/rewound abstraction over `Mic` and a file source (name not `Source`, which voice_test.rs already uses); time is counted in audio samples.
**Rationale:** The Endpointer is already pure (audio.rs:399); only `record_from` couples hardware and wall time. Mic Drop learned the same (assembler.rs:16-18).
**Impact:** FR-1/2; touches audio.rs, listen.rs, hands_free.rs (all carry T-031 uncommitted edits - build on a committed base).

## D-3 merge-window-supersedes-first-pause
**Decision:** `listen_silence_ms` stays the provisional endpoint; merge window adds after it; `first_pause` becomes a floor on total patience for short utterances.
**Rationale:** Otherwise hands-free short utterances wait 1500+1200 = 2.7 s; this gives 1.9 s and is exactly today's when window = 0. No settings keys removed.
**Impact:** FR-14, AC-9. Provisional default stays 700 (not Mic Drop's 800) to avoid changing existing behaviour.

## D-4 window-applies-to-all-silence-ended-takes
**Decision:** Push-to-talk/tray takes ending by silence get the window too; Release bypasses it.
**Rationale:** "Stop cutting me off" is not hands-free-only (host.log:584 was a tray click). Cost is +1.2 s, configurable to 0.
**Impact:** FR-7/13, NFR-2.

## D-5 no-speculative-transcription-yet
**Decision:** Transcribe once at dispatch; do not transcribe speculatively at the provisional endpoint.
**Rationale:** Mic Drop does, to hide latency (assembler.rs:11-14); here whisper-server is one process and a wasted inference competes with the next. Measure first.
**Impact:** Out of scope; revisit if NFR-2 latency is unacceptable (todo recorded).

## D-6 hallucination-list-unconditional
**Decision:** Port the exact-match list unconditionally.
**Rationale:** Simple; bare "Thank you." is almost always silence-hallucination; hands-free speech is wake-prefixed so never bare. Known cost: a deliberately spoken bare "thank you" in push-to-talk is dropped.
**Impact:** FR-15, gap R-3.

## D-7 hand-written-scanner-no-regex-crate
**Decision:** Tag stripping is a small scanner, not Mic Drop's regex.
**Rationale:** No `regex` in Cargo.toml (:12-75); a new dependency needs tech-select(confirm-existing) for a ~20-line job. Also allows the keep-if-digit rule.
**Impact:** FR-15/17, NFR-4.

## D-8 t019-closure-stays-with-t019
**Decision:** T-032 provides the replay mechanism for T-019 AC-7/AC-8; it does not mark them done.
**Rationale:** AC-7 says "in the owner's own voice"; whether replayed fixtures count is the owner's judgement.
**Impact:** S-1.

## D-9 confidence-guard-deferred
**Decision:** The host.log:589 "Hey, I'm gonna miss you." case is not addressed by FR-15; a confidence/speech-ratio guard is a follow-up after probing whether the shipped whisper-server returns `no_speech_prob` (verbose_json).
**Rationale:** Unverified capability, and the log holds no audio so the cause is unknown. Not invented into requirements.
**Impact:** FR-18; todo recorded.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Dossier: [[INV-2026-10-05-micdrop-adoption-dossier]] · Related: [[T-019-summary]] · [[T-031-summary]] · [[T-035-summary]] · [[T-034-summary]]
