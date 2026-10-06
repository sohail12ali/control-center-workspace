---
ticket: "T-032"
artifact: plan
---

# Plan: T-032

## Approach

Single-layer (one component: `desktop/src-tauri` plus a thin console config slice; 14 tasks but strictly serial chain inside one crate, no cross-ticket dependency chain; flat mode). Build order **B9 -> B3 -> B4** (analysis Recommended Path). Paths under `desktop/src-tauri/src/` unless stated. No new runtime dependency (NFR-4); filter is a hand-written scanner (D-7). No tech-select needed: no unmade tech choice.

Design notes the builder must follow:
- Seam named `Frames` (not `Source`, taken by voice_test.rs, D-2) with `cursor/since/rewound`, implemented by `Mic` and `FileFrames`. Time counted in samples; cap and window use captured samples (pre-compression), not buffer length.
- Env read ONCE into a `ReplayConfig {wav, sink}` value passed explicitly; tests construct it directly (no process-env mutation in parallel tests).
- Endpointer stays pure; the window/merge state machine is a pure type beside it so it is unit-testable without audio.

## Slices

### Slice 1 - B9 wav-replay seam (first)
T-032-01..05. Exit: headless take + sink + fixtures proven; live path unchanged.

### Slice 2 - B3 pause-tolerant endpointing
T-032-06..10. Exit: AC-2..9, AC-14 green on replay.

### Slice 3 - B4 junk filter
T-032-11..12. Exit: AC-10, AC-11.

### Slice 4 - Verify hand-off
T-032-13..14.

## Tasks

### [ ] T-032-01 - Frames seam + audio-time clock (2.5 h)
- [ ] FIRST ACTION of the build: `python console/kanban.py ticket move T-032 in-progress` (CLI only; no TOML hand-edit). Record `git ls-files --eol` for audio.rs/listen.rs/hands_free.rs/piper.rs/tts.rs.
- [ ] Define `Frames` trait + impl for `Mic`; add `FileFrames` (any rate/channels via `to_mono_16k` :198; feeds without sleeping; appends trailing silence >= silence_ms + merge_window_ms + 500 ms).
- [ ] Refactor `record_from` (:699) to run on `Frames` with sample-counted cap (replace :722 wall clock, :748 sleep applies to Mic only).
- **Done-criteria:** existing endpointer/VAD tests (audio.rs:851-1146) pass unmodified; unit test: FileFrames cursor/since/rewound semantics and trailing silence length. FR-1, FR-2; AC-15 (part).
- **Basis:** record_from ~70 lines (analysis Current State); Mic Drop FileSource :427-474 as reference.
- **Depends on:** -

### [ ] T-032-02 - Replay selection, WARN, state, hands-free through seam (2 h)
- [ ] `ReplayConfig` from `CC_REPLAY_WAV`; used by every take (tray/PTT/hands-free); cursor persists across takes; exhausted = "nothing heard".
- [ ] Replace concrete `Mic` in listen.rs (:126,398) and hands_free.rs (:337,352,368) with the seam; armed loop reads replay audio into the wake spotter.
- [ ] One WARN at first use naming the file only; `/listen/state` `source: "file"|"mic"`.
- **Done-criteria:** no settings key / bridge route / UI can enable replay (grep evidence recorded). FR-3, FR-5 (part); AC-13 (part).
- **Basis:** three files, signature threading; hands_free loop 66 lines.
- **Depends on:** T-032-01

### [ ] T-032-03 - Piper WAV sink `CC_TTS_SINK_WAV` (1.5 h)
- [ ] In `piper::speak_with` (piper.rs:176-266) write 16-bit mono WAV at voice rate (overwrite per reply) instead of `play` (:268); `stop()`/playing state still work; non-Piper backend (tts.rs:206-247) -> clear error.
- **Done-criteria:** unit test reads RIFF header + length > 0 with no output device; unsupported-backend error test. FR-4; AC-12.
- **Basis:** hand-written 44-byte header, no crate.
- **Depends on:** T-032-01 (shares ReplayConfig)

### [ ] T-032-04 - Fixture generator + fixtures (2 h)
- [ ] Committed script (desktop/tests/gen-replay-fixtures.ps1 or sidecar-style py) using Piper + synthetic silence/noise: (a) mid-pause 0.9 s, (b) 3 s gap, (c) 5x0.9 s pauses, (d) silence, (e) low noise, (f) three clicks, (g) hallucination-trigger search (time-box 30 min, else documented "not found").
- [ ] Provenance note "synthetic speech, not a human voice" (README in fixtures dir or script header).
- **Done-criteria:** 16 kHz mono wavs in desktop/tests/fixtures/; script reruns reproducibly. FR-6.
- **Basis:** piper.exe + en_US-amy-medium present (analysis :20).
- **Depends on:** - (parallel with 01-03; needed by 05)

### [ ] T-032-05 - Headless replay tests, B9 (2 h)
- [ ] Capture test: fixture (a) with window=0 baseline = two takes today; capture determinism twice, identical sample count, <2 s wall (NFR-1).
- [ ] State/WARN/source test; hands-free fed wake wav + request fires wake and takes headlessly (fake console).
- **Done-criteria:** AC-1, AC-12, AC-13 evidenced; single-threaded run first (`--test-threads=1`).
- **Basis:** fake console exists in listen tests (verify by Read); builder re-Reads.
- **Depends on:** T-032-02, 03, 04

### [ ] T-032-06 - Console config plumbing + pytest (1.5 h)
- [ ] `console/config/assistant.toml` add `listen_merge_window_ms=1200`, `listen_max_merges=4` documented beside :121-142.
- [ ] `console/server/assistant_config.py`: defaults (:154-165), allowlist (:222), bounds 0-5000 / 0-8 (:652-665), live-note (:245-292). Do not touch app.js/styles.css (FR-20).
- [ ] pytest: defaults, reject -1 / 5001 / max_merges 9, allowlist both keys, assert `CC_REPLAY_WAV`/`replay` not an allowlisted key.
- **Done-criteria:** `pytest -o addopts=""` count recorded. FR-19 (console half), FR-20; AC-14 (console half).
- **Basis:** mirrors existing 3 keys; files carry other edits -> surgical.
- **Depends on:** -  (may run any time; before T-032-07)

### [ ] T-032-07 - Rust Limits + `limits_from` (1 h)
- [ ] Add `merge_window_ms`, `max_merges` to `audio::Limits` (+Default :515-523); read in `listen::limits_from` (:180-199), clamp to bounds.
- **Done-criteria:** unit test `limits_from` reads both keys and defaults. FR-19; AC-14.
- **Basis:** two fields, copy of existing pattern.
- **Depends on:** T-032-01, 06

### [ ] T-032-08 - Pure window/merge state machine (3 h)
- [ ] Provisional endpoint (silence_ms) -> window in audio time; resume via same thresholds + `SPEECH_RUN`=3 -> merge+1; max_merges -> immediate end; `required_silence` first_pause floor `max(silence+window, first_pause)` for short (<1200 ms) utterances; window=0 == today's.
- [ ] Cap and Release outcomes (`Ending::Capped/Released`).
- **Done-criteria:** pure unit tests (synthetic score/loudness sequences) for window resume, click rejection, cap-of-merges, window=0 parity, first_pause=3000 ends at 3.0 s. FR-7, 8, 9, 12, 13, 14; AC-4, 5, 6, 8, 9 (unit level).
- **Basis:** Endpointer :399-465 is pure; Mic Drop assembler.rs:16-18,228 reference.
- **Depends on:** T-032-07

### [ ] T-032-09 - Integrate in `record_from`: gap compression, tail trim, release (2 h)
- [ ] Merge compresses kept silent gap to <= 300 ms; before transcription trim trailing silence to <= 300 ms past last speech frame; release during window ends at once; log merges + window time in summary line (listen.rs:570).
- **Done-criteria:** buffer tests: inner gap <= 300 ms, tail <= 300 ms, release immediate. FR-10, 11, 13; NFR-2; AC-7, 8.
- **Basis:** buffer ops on one Vec of samples.
- **Depends on:** T-032-08

### [ ] T-032-10 - Replay tests, B3 (2.5 h)
- [ ] Fixtures a-c, f via replay: AC-2 (1 take, merges=1; real base.en transcript has both clauses, skipped with stated reason if whisper-server absent), AC-3, AC-4 (max_merges 4 vs 0), AC-5, AC-6, AC-1 sample-count determinism with window on.
- **Done-criteria:** AC-2..6 evidenced; NFR-1 (<2 s capture of 20 s file).
- **Basis:** test-per-AC, helper from T-032-05.
- **Depends on:** T-032-05, 09

### [ ] T-032-11 - Junk filter pure module (1.5 h)
- [ ] New module (e.g. `transcript_filter.rs`, registered in main.rs surgically): hand-written scanner for `[..] (..) *..* ♪..♪` incl. unclosed; collapse whitespace; no-alphanumeric -> empty; case-insensitive exact list; keep bracketed text containing a digit.
- **Done-criteria:** AC-10 table test passes verbatim. FR-15, 17, 18 (todo for D-9 confirmed present via `todos` list); NFR-4.
- **Basis:** ~60 lines + table (Mic Drop speech.rs:115-150 reference).
- **Depends on:** - (can run any time; scheduled after B3 per order)

### [ ] T-032-12 - Apply filter at listen.rs:531-537 (1.5 h)
- [ ] Apply to engine text before gate (:542), Sent cue and `console_api::say` (:565); empty -> "nothing heard": no send, no cue, tray cancel, no hands_free.rs:398-403 error log; log category + word count only.
- **Done-criteria:** fake-console test: filtered transcript sends nothing, no cue, reason "nothing heard"; fixtures d/e replay end the same way; log capture contains no transcript text. FR-16; AC-11; NFR-3.
- **Basis:** 10-line change + tests.
- **Depends on:** T-032-11, 05

### [ ] T-032-13 - Docs + hygiene check (1 h)
- [ ] Document env vars and new keys in desktop/README.md (surgical, append); `git ls-files --eol` + `git diff --stat` before/after shows no EOL churn or unrelated hunks; no Cargo.toml dependency change.
- **Done-criteria:** NFR-3, NFR-4 evidence in progress.md via `progress-tracker`.
- **Basis:** small docs + diff review.
- **Depends on:** T-032-10, 12

### [ ] T-032-14 - Full suites (1 h)
- [ ] Full desktop unit suite (single-threaded first, then default), console `pytest -o addopts=""`; record counts; check whisper-server orphans.
- **Done-criteria:** AC-15; counts in progress.md.
- **Basis:** known slow cargo build.
- **Depends on:** T-032-13

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-032-01 Frames seam + clock | 2.5 h | ~70-line refactor + 1 new type |
| T-032-02 Selection/state/hands-free | 2 h | 3 files signature threading |
| T-032-03 Piper WAV sink | 1.5 h | piper.rs path + header writer |
| T-032-04 Fixtures | 2 h | script + Piper runs |
| T-032-05 B9 tests | 2 h | 3 AC |
| T-032-06 Console plumbing + pytest | 1.5 h | mirrors 3 existing keys |
| T-032-07 Limits/limits_from | 1 h | 2 fields |
| T-032-08 State machine | 3 h | core logic |
| T-032-09 record_from integration | 2 h | buffer ops |
| T-032-10 B3 tests | 2.5 h | 6 AC |
| T-032-11 Filter module | 1.5 h | ~60 lines + table |
| T-032-12 Apply filter | 1.5 h | small + tests |
| T-032-13 Docs/hygiene | 1 h | |
| T-032-14 Full suites | 1 h | |
| **Total** | **~25 h** | PERT-ish; +30% cargo/CI friction not included |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| AC-1 | T-032-01, 05, 10 |
| AC-2 | T-032-08, 09, 10 |
| AC-3 | T-032-08, 10 |
| AC-4 | T-032-08, 10 |
| AC-5 | T-032-08, 10 |
| AC-6 | T-032-08, 10 |
| AC-7 | T-032-09 |
| AC-8 | T-032-08, 09 |
| AC-9 | T-032-08 |
| AC-10 | T-032-11 |
| AC-11 | T-032-12 |
| AC-12 | T-032-03, 05 |
| AC-13 | T-032-02, 05 |
| AC-14 | T-032-06, 07 |
| AC-15 | T-032-01, 14 |

FR coverage: FR-1,2 (01) · FR-3,5 (02,05) · FR-4 (03) · FR-6 (04) · FR-7..9,12..14 (08) · FR-10,11 (09) · FR-15,17,18 (11) · FR-16 (12) · FR-19 (06,07) · FR-20 (06). NFR-1 (05,10), NFR-2 (09), NFR-3 (12,13), NFR-4 (13,14).

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| audio.rs / listen.rs / hands_free.rs carry other tickets' uncommitted edits (T-031 etc.); clobber or conflict | High | Med | Surgical Edit only; re-Read before EACH Edit; never revert/stash/checkout/format; `git ls-files --eol` + `git diff --stat` before/after; commit not done by planner | Builder |
| CRLF/LF mix introduced by edits | Med | Low | Record eol per file first; match as found; re-check after; fix only own lines | Builder |
| cargo build/test pitfalls on Windows | Med | Med | `source desktop/msvc-env.ps1` first; redirect output inside `cmd /c` (not `| Out-File`); check whisper-server orphans before/after; single-threaded tests first (`--test-threads=1`); never `grep -r` into `desktop/target`; judge cargo by output not exit code | Builder |
| Env-var tests race in parallel | Med | Med | `ReplayConfig` passed explicitly; tests never mutate process env | Builder |
| Refactor of `record_from` changes live mic behaviour | Med | High | Mic path keeps sleep/cap semantics; existing tests unchanged; manual/live note in verification | Builder |
| Cap/window sample counting vs compression drift | Med | Med | Cap counts captured samples pre-compression; dedicated test AC-8 | Builder |
| Whisper-server / piper absent -> AC-2 / fixtures unprovable | Low | Med | Skip with stated reason (BE HONEST); fixture (g) time-boxed | Verifier |
| +1.2 s latency perceived as regression | Med | Low | Setting 0 = today's; logged; speculative STT deferred (D-5) | Owner |
| Delegated build mis-reports (memory: subagent status not evidence) | Med | Med | Verifier re-counts tests independently | Verifier |

No high x high risks.

## Dependencies
- Blocks: T-019 AC-7/AC-8 evidence (closure stays T-019's, D-8)
- Blocked by: none hard. Soft: T-031 uncommitted edits in same files (see risks)

## VERIFY task list (verifier, independent counts)

- V-1 Re-run desktop unit suite single-threaded then default; record pass/fail counts; compare with builder's claim; check no whisper-server orphan.
- V-2 `pytest -o addopts=""` in console/; record count (compare to baseline); includes AC-14 tests.
- V-3 Per-AC evidence table AC-1..15 (test name -> result); AC-2 real-whisper run or stated skip.
- V-4 Hygiene: `git diff --stat`, `git ls-files --eol` vs pre-build, Cargo.toml unchanged, app.js/styles.css untouched, replay not in allowlist/bridge routes (grep).
- V-5 Log privacy: captured logs contain no transcript/discarded text; WARN names file only.
- V-6 `validate-artifacts T-032 links`, `reconcile`; D-9/D-5 todos present.
- V-7 Manual (owner): live mic regression, window feel at 1200 ms; report as not-run if not done.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements]] · [[T-032-user-stories]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
