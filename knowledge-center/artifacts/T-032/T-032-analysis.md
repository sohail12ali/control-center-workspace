---
ticket: "T-032"
artifact: analysis
---

# Analysis: T-032

## Context

Dossier rows B3 (pause-tolerant endpointing), B4 (Whisper junk filter), B9 (headless wav-replay seam, build first) from [[INV-2026-10-05-micdrop-adoption-dossier]] (dossier:77,78,83). Reference mechanics (ported, not copied): Mic Drop `assembler.rs` (merge window on the AUDIO clock, assembler.rs:16-18; cap, assembler.rs:228), `speech.rs:115-150` (junk filter), `audio.rs:427-474` FileSource / `:625` FileSink.

## Current State

- **Capture** — `Mic::record_from` (desktop/src-tauri/src/audio.rs:699-766) owns the whole loop: reads the cpal ring (`since`, :670), scores 256-sample frames with `earshot` (:705,739), feeds the pure `Endpointer::push(score, loudness) -> bool` (:399), and ends on the first `true`. The cap is WALL-clock (`started.elapsed()`, :722) and the loop sleeps 16 ms (:748). Nothing outside `Mic` can supply frames, so no take can run without hardware.
- **Endpointer** — one threshold: `required_silence` (:458-465): `trailing_silence` (700 ms) once >=1200 ms of speech (`SETTLED_SPEECH`, :64), else `first_pause` (1500 ms, hands-free only; `Limits::default` sets it equal to trailing, :515-523). Speech needs `SPEECH_RUN`=3 frames to reset the silence count (:125,430). A pause longer than 700 ms ends the take; there is no resume path. This is the "cut off mid-thought" defect.
- **Transcription** — `listen::take_inner` (listen.rs:397-580): `take.wav()` -> `stt::transcribe` (:531, stt.rs:1074 -> `extract_text` :1175) -> `trim` -> only an EMPTY string is rejected (:534-537, reason "the speech engine returned nothing") -> gate (:542) -> `console_api::say` (:565). There is no junk filtering anywhere; `grep clean|junk|BLANK_AUDIO` over src finds none. Only caller of `stt::transcribe` outside tests is listen.rs:531 (bridge.rs:1201-1213 are tests).
- **Knobs** — `limits_from` (listen.rs:180-199) reads `listen_silence_ms` 700, `listen_max_seconds` 12, `listen_first_pause_ms` 1500 (hands-free/patient only). Declared in console/config/assistant.toml:121-142, defaults console/server/assistant_config.py:154-165, allowlist :222, bounds :652-665 (silence/first_pause 200-5000, max 2-120, preroll 0-3000), live-note table :245-292. `listen_preroll_ms` 1000 is consumed by hands_free (hands_free.rs:368) via the ring (RING 4 s, audio.rs:76).
- **Hands-free** — armed loop (hands_free.rs:313-379) holds `Option<audio::Mic>`, reads `mic.since(cursor)` into the wake spotter, then `take_after_wake(from)` (listen.rs:156). Concrete `Mic` type threads through listen.rs (:126,398) and hands_free.rs (:337,352,368).
- **Output** — `piper::speak_with` (piper.rs:176-266) spawns piper (`--output_raw`), a reader thread fills a queue, `play` (:268) opens cpal. `tts.rs:206` `speak` picks piper or OS backends (powershell/say/spd-say/espeak, tts.rs:226-247). Playback is the only sink.
- **Fixtures / tools present** — desktop/tests/fixtures has 7 wake wavs (wake-*.wav, status-ticket-two.wav) read by wake.rs:385 tests; desktop/stt has whisper-server.exe + ggml-base.en.bin; desktop/tts has piper.exe + en_US-amy-medium. So real-whisper replay tests and synthetic-speech fixtures are buildable now. No `regex`/`hound` crate in Cargo.toml (checked :12-75).
- **Log evidence** — console/.cache/desktop/host.log:584-591 (2026-10-05): click->Talk, mic open 1943 ms, "1.9s of audio, ended by Silence", stt 790 ms, heard "Hey, I'm gonna miss you." and it was SENT to the assistant. The log holds no audio, so whether this was a hallucination on non-speech or a genuine mis-hear is UNKNOWN. Note: the mic-drop phrase list (speech.rs:117-125) would NOT have caught this phrase.

## Key Findings

- Finding: the Endpointer is pure and already testable; the only seam missing is the frame source plus a wall-clock cap. Significance: B9 is a small refactor of `record_from`, not a rewrite; Endpointer/VAD tests (audio.rs:851-1146) keep working.
- Finding: our takes are ONE contiguous buffer, unlike Mic Drop's separate utterances. Significance: "merge + re-transcribe" reduces to "keep recording through a resumed pause, transcribe once at dispatch"; no segment join or text-level glue. Speculative transcription at the provisional point (Mic Drop's latency hiding) is optional and deferred.
- Finding: merge window adds latency (end of speech to dispatch 700+1200 = 1.9 s). Significance: must be configurable to 0 and reconciled with `first_pause` (D-3), otherwise hands-free short utterances wait 2.7 s.
- Finding: a recording that keeps the 1.2 s merge-window silence would feed Whisper a long silent tail, the exact trigger for "Thank you." hallucinations. Significance: trim the tail before transcribing (FR-11).
- Finding: Mic Drop strips ALL parentheticals; Whisper may legitimately emit "(T-002)"-style text and ticket ids are this product's core vocabulary. Significance: tag stripping must preserve bracketed content containing digits (FR-17).
- Finding: both the replay seam and `hands_free.rs`/`listen.rs`/`audio.rs` are files with other tickets' uncommitted edits (git status M). Significance: builder must land on a committed T-031 base; conflict risk is high; no revert/format.
- Finding: T-019 AC-7/AC-8 (T-019-requirements.md:28-29) need the hands-free loop, not only a take, to accept replay audio.

## Research

None external. Whisper-server `verbose_json` / `no_speech_prob` availability in the shipped whisper.cpp build is UNVERIFIED (deferred probe, see todo).

## Recommended Path

1. B9 first: `Frames` abstraction over Mic and a file source; audio-time cap; env-selected replay + file TTS sink (D-1, D-2).
2. Fixtures generated with Piper + silence, then B3 merge window with `listen_merge_window_ms`/`listen_max_merges` (D-3, D-4).
3. B4 pure filter module applied at listen.rs:531-537 (D-6, D-7).
4. Verify headless via replay with real whisper-server where present.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Dossier: [[INV-2026-10-05-micdrop-adoption-dossier]] · Related: [[T-019-summary]] · [[T-031-summary]] · [[T-035-summary]] · [[T-034-summary]]
