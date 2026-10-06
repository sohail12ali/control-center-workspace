---
ticket: "T-032"
artifact: requirements
status: frozen
frozen: "2026-10-06"
iteration: 0
---

# Requirements: T-032

Sources: [[T-032-analysis]] (file:line grounding) · [[T-032-gap-analysis]] (0 blockers) · [[T-032-decision-log]] (D-1..D-9). Build order: **B9 -> B3 -> B4**. Paths are under `desktop/src-tauri/src/` unless stated.

## Functional Requirements

### B9 headless wav-replay seam (build first)
1. **FR-1 Frame source seam.** The capture loop (`audio.rs` `record_from`, :699) reads audio through an abstraction (cursor / since / rewound) implemented by `Mic` and by a file source. VAD, `Endpointer`, limits and pre-roll run the SAME code for both. Live behaviour with no replay configured is unchanged.
2. **FR-2 Audio-time clock.** The take cap and the merge window are measured in captured audio (samples), not wall clock (today :722 wall, :748 sleep). A file source feeds as fast as consumed (no sleeps) and appends trailing silence >= `listen_silence_ms` + `listen_merge_window_ms` + 500 ms so the last utterance can close. Input WAV may be any rate/channels; converted by `to_mono_16k` (:198).
3. **FR-3 Selection.** Replay is chosen by environment variable `CC_REPLAY_WAV=<path>` (every take: tray, push-to-talk, hands-free). Not a setting, not a bridge route, not a Settings control. When active: one WARN at first use naming the file (not its contents) and `/listen/state` reports `source: "file"` (else `"mic"`). The cursor persists across takes; an exhausted file ends a take as "nothing heard".
4. **FR-4 File sink.** `CC_TTS_SINK_WAV=<path>` makes Piper synthesis write the reply to that WAV (16-bit mono at the voice rate, overwritten per reply) instead of opening an output device; `stop()`/playing state keep working. Only the Piper backend supports it; with another backend or no Piper it returns a clear error, never silent playback.
5. **FR-5 Headless round trip.** With both variables set, wake spotting (hands-free) and a take -> transcribe -> gate -> `console_api::say` run with no audio device present. The armed hands-free loop reads replay audio through the same abstraction (enables [[T-019-summary]] AC-7/AC-8 evidence; their closure is T-019's call, D-8).
6. **FR-6 Fixtures.** Committed 16 kHz mono wavs in `desktop/tests/fixtures/`, generated with Piper + synthetic silence by a committed script, provenance stated (synthetic speech, not a human voice): (a) one sentence with a 0.9 s mid-pause; (b) two sentences with a 3 s gap; (c) one sentence with 5 pauses of 0.9 s; (d) silence only; (e) low noise only; (f) three short clicks; (g) a noise or silence wav that real base.en turns into a known hallucination if one can be found (else documented as not found).

### B3 pause-tolerant endpointing
7. **FR-7 Provisional endpoint + window.** The existing end-of-speech silence (`listen_silence_ms`, default 700, :458-465) becomes the PROVISIONAL endpoint. After it, recording continues for a merge window of `listen_merge_window_ms` (default 1200; 0 = disabled = today's behaviour; allowed 0-5000), measured in audio time from the provisional mark.
8. **FR-8 Resume = merge.** Speech resuming inside the window (same adaptive thresholds and `SPEECH_RUN`=3 debounce, :125/:424, so clicks do not count) cancels the provisional end: the take continues as ONE contiguous buffer, merge count +1. No resume by window end: the take ends with `Ending::Silence`.
9. **FR-9 Merge cap.** `listen_max_merges` default 4 (allowed 0-8). After that many merges the next provisional endpoint ends the take immediately, no window. A merged take is transcribed ONCE, at dispatch, on the whole buffer (no text-level glue).
10. **FR-10 Inner pauses.** On a merge the silent gap kept in the buffer is compressed to <= 300 ms (Mic Drop `JOIN_SILENCE_MS`).
11. **FR-11 Tail trim.** Before transcription the trailing silence is trimmed to <= 300 ms past the last speech frame (the window must not feed Whisper seconds of silence).
12. **FR-12 Cap wins.** `listen_max_seconds` (12) caps the whole take, windows included, in audio time (`Ending::Capped`).
13. **FR-13 Release wins.** Stop/release during a window ends the take at once (`Ending::Released`), no waiting.
14. **FR-14 Knob reconciliation.** `listen_first_pause_ms` is kept (key, bounds, hands-free-only) but is demoted to a FLOOR on total patience: a short utterance (<1200 ms speech) ends no earlier than `max(silence + window, first_pause)` after its last speech. At defaults (1900 > 1500) it is inert; with the window at 0 behaviour equals today's. `listen_preroll_ms` and `RING` are untouched.

### B4 junk filter
15. **FR-15 Filter.** One pure function (own small module, no new crate, D-7) cleans every transcript: (a) remove sound tags `[..]`, `(..)`, `*..*`, `♪..♪` including an unclosed one; (b) collapse whitespace; (c) result with no alphanumeric char -> empty; (d) case-insensitive exact match of the result against {"thank you.", "thanks for watching!", "thank you for watching.", "you", "bye.", "[blank_audio]", "(silence)"} -> empty.
16. **FR-16 Where.** Applied to the engine text at `listen.rs` :531-537, before the gate (:542), the Sent cue and `console_api::say` (:565). An empty result ends the take as "nothing heard": no send, no cue, tray cancel, no hands-free error log (hands_free.rs:398-403). Logs state only that a transcript was filtered and why (category, word count) - never the text.
17. **FR-17 Preserve content.** Mixed text keeps its words ("[Music] open T-002" -> "open T-002"; "thank you for the summary" unchanged). Bracketed or parenthesised text containing a digit (e.g. "(T-002)") is NOT a sound tag and is kept.
18. **FR-18 Deferred.** Confidence-based rejection of plausible-sounding junk (the host.log:589 phrase would pass FR-15) is not in this ticket; tracked as a todo (D-9).

### Settings plumbing
19. **FR-19** Two new keys `listen_merge_window_ms`, `listen_max_merges` in `console/config/assistant.toml` (documented beside :121-142), defaults/allowlist/bounds/live-note in `console/server/assistant_config.py` (cf. :154-165, :222, :652-665, :245-292), read in `listen::limits_from` (:180) into `audio::Limits`; applied on the next take. Out-of-range values are rejected like the existing keys.
20. **FR-20** No Settings-tab UI is added in this ticket (keys editable via the existing generic path or file); `console/static/app.js` and `styles.css` are not touched.

## Non-Functional Requirements
1. **NFR-1 Determinism & speed.** Same wav + same settings -> identical take boundaries and merge counts, run to run; replaying a 20 s file finishes capture in < 2 s of wall time (STT excluded).
2. **NFR-2 Latency.** End-of-speech to dispatch grows by at most `listen_merge_window_ms` (default +1.2 s) and by 0 when set to 0. Each take logs merges and window time in its existing summary line (listen.rs:570).
3. **NFR-3 Safety/privacy.** The replay path never persists audio beyond the given files, never logs audio or discarded-speech text, and cannot be turned on from Settings, the bridge or the console (D-1).
4. **NFR-4 Hygiene.** No new crate dependency; no reverts/format of files carrying other tickets' edits; unit tests added beside the code, existing `audio.rs` endpointer tests still pass unchanged.

## Acceptance Criteria
- [ ] AC-1 (FR-1,2,3) A replay of fixture (a) with no audio device yields one take, end Silence, in wall time < 2 s capture, twice with identical sample count.
- [ ] AC-2 (FR-7,8,10) Fixture (a) with default settings: 1 take, merges = 1, buffer contains both clauses, inner gap <= 300 ms; real base.en transcript contains words from both clauses (skipped with a stated reason where whisper-server is absent).
- [ ] AC-3 (FR-7) Fixture (b) (3 s gap): 2 separate takes, merges = 0 each.
- [ ] AC-4 (FR-9) Fixture (c) with `listen_max_merges=4`: take ends at the 5th provisional endpoint with merges = 4; with 0 every pause splits.
- [ ] AC-5 (FR-7) `listen_merge_window_ms=0` reproduces today's behaviour: (a) becomes two takes.
- [ ] AC-6 (FR-8) Fixture (f) clicks inside the window do not extend the take.
- [ ] AC-7 (FR-11) The audio sent to STT has <= 300 ms of trailing silence after last speech.
- [ ] AC-8 (FR-12,13) Cap at 12 s audio-time with merges; release during a window ends at once.
- [ ] AC-9 (FR-14) A short utterance ends no earlier than `max(silence+window, first_pause)`; with `first_pause=3000` it ends at 3.0 s.
- [ ] AC-10 (FR-15,16,17) Table test: "[BLANK_AUDIO]", "(music)", "*coughs*", "♪ la ♪", "...", "[", "Thank you.", "you" -> "" ; "[Music] open T-002" -> "open T-002"; "(T-002) status" unchanged; "thank you for the summary" unchanged.
- [ ] AC-11 (FR-16) A filtered transcript sends nothing to the console (fake console), plays no Sent cue, and yields reason "nothing heard"; fixtures (d)/(e) end the same way.
- [ ] AC-12 (FR-4) With `CC_TTS_SINK_WAV` set a speak writes a valid WAV (RIFF header, length > 0) and opens no output device; unsupported backend -> error.
- [ ] AC-13 (FR-3,5) `/listen/state` shows `source:"file"` when replay is on; the WARN is logged; no settings key or bridge route can enable it; hands-free loop fed (wake wav + request) fires a wake and takes headlessly.
- [ ] AC-14 (FR-19) Console tests: defaults, bounds (reject -1, 5001, max_merges 9), allowlist for both keys; `limits_from` unit test reads them.
- [ ] AC-15 (NFR-4) Full desktop unit suite and console tests pass (`pytest -o addopts=""` count recorded); existing endpointer tests unchanged.

## Out of Scope
- Silero VAD (B6), echo cancellation (T-035), onboarding wizard (T-034), Settings UI controls for the new keys, speculative parallel transcription at the provisional endpoint (D-5), confidence-based junk rejection (D-9), file sinks for non-Piper TTS backends.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements-draft]] · [[T-032-context-snapshot]] · [[T-032-gap-analysis]] · [[T-032-iteration-log]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
- Dossier: [[INV-2026-10-05-micdrop-adoption-dossier]] · Related: [[T-019-summary]] · [[T-031-summary]] · [[T-035-summary]] · [[T-034-summary]]
