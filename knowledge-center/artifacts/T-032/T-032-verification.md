---
ticket: "T-032"
artifact: verification
---

# Verification: T-032

Verifier run 2026-10-06 on branch `development` (HEAD 2a3d3ce, uncommitted tree). Every figure below was produced by a fresh run by the verifier, not copied from the builder. All audio is committed synthetic fixtures (Piper speech + generated silence/noise) or the existing synthetic `status-ticket-two.wav`; no real microphone and no human voice was used. Hardware and feel checks are listed under Not Verified.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Fixture (a), no audio device: one take, Silence, <2 s wall, twice identical sample count | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:572-583 (fixture_a_is_one_take_with_the_window_on_identically_and_fast) (asserts [Silence, NothingHeard], first==second, wall<2 s); desktop/src-tauri/src/replay.rs:469-489 (a_take_on_an_exhausted_file_is_nothing_heard_and_does_not_hang); desktop/src-tauri/src/replay.rs:515 (a_spoken_fixture_ends_on_silence_and_is_deterministic). Builder logged 395 ms for 16 s of audio; I re-ran, passed. |
| AC-2 | Fixture (a) default settings: 1 take, merges 1, both clauses, inner gap <=300 ms, real base.en has both clauses | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:631-643 (a_merged_take_has_its_pause_squeezed_and_its_tail_trimmed) (merges 1, inner <=20 frames); desktop/src-tauri/src/replay.rs:722-737 (fixture_a_merged_is_transcribed_as_both_clauses) (ran, not skipped; my run: real base.en heard "show me the open tickets and which ones are blocked." via whisper-server); desktop/src-tauri/src/audio.rs:1606-1633 (a_merge_squeezes_the_pause_and_the_tail_to_300_ms) (exactly 300 ms). |
| AC-3 | Fixture (b) 3 s gap: 2 takes, merges 0 each | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:741-749 (a_three_second_gap_is_two_takes_with_no_merges) ([(Silence,0),(Silence,0),NothingHeard]). |
| AC-4 | Fixture (c): max_merges 4 ends at the 5th provisional endpoint with merges 4; 0 splits every pause | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:755-773 (max_merges_caps_how_many_pauses_one_take_absorbs) (4 -> [(Silence,4),(Silence,0),NothingHeard]; 0 -> six takes, 21 s audio <2 s wall); desktop/src-tauri/src/audio.rs:1537-1553 (after_max_merges_the_next_pause_ends_the_take_at_once) (pure, 2/4/0). |
| AC-5 | listen_merge_window_ms=0 reproduces today's behaviour: (a) becomes two takes | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:552-566 (with_no_window_fixture_a_replays_as_two_takes_identically_and_fast); desktop/src-tauri/src/replay.rs:778-784 (a_zero_window_splits_fixture_a_whatever_max_merges_says); desktop/src-tauri/src/audio.rs:1556-1579 (a_zero_window_is_the_plain_endpointer_first_pause_included) (end frame identical to bare Endpointer, 3 first_pause x 3 sequences). Caveat: ending parity only; the audio sent to STT is NOT byte-identical, see D-10. |
| AC-6 | Fixture (f): clicks inside the window do not extend the take | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/replay.rs:790-796 (clicks_in_the_window_do_not_extend_the_take) (merges 0, window_ms exactly 1200); desktop/src-tauri/src/audio.rs:1526-1534 (clicks_inside_the_window_neither_merge_nor_extend_it). |
| AC-7 | Audio sent to STT has <=300 ms trailing silence after last speech | PASS (synthetic audio, headless; not verified on hardware) | desktop/src-tauri/src/audio.rs:1606-1633 (a_merge_squeezes_the_pause_and_the_tail_to_300_ms) (tail == 4800 samples exactly); desktop/src-tauri/src/replay.rs:631-643 and desktop/src-tauri/src/replay.rs:648-654 (the_tail_is_trimmed_with_the_window_off_too) (replay tests allow <=20 frames = 320 ms, one frame of tolerance). Trim is unconditional (D-10, open). |
| AC-8 | Cap at 12 s audio-time with merges; release during a window ends at once | PASS (synthetic audio, headless; not verified on hardware; cap proven at a 4 s limit, not the 12 s default) | desktop/src-tauri/src/replay.rs:707-716 (the_cap_covers_windows_and_merges_in_audio_time) (Capped, merges>=1, <2 s wall); desktop/src-tauri/src/replay.rs:685-701 (release_during_the_window_ends_the_take_at_once) (Released, cursor <=2 frames past, window_ms<400); desktop/src-tauri/src/audio.rs:967 sample-counted cap plus live wall backstop (read, no test: needs a stalled Mic). |
| AC-9 | Short utterance ends no earlier than max(silence+window, first_pause); first_pause=3000 ends at 3.0 s | PASS (pure unit level; replay level not exercised) | desktop/src-tauri/src/audio.rs:1582-1603 (first_pause_is_a_floor_on_total_patience_for_a_short_utterance) (3000 -> 3000..3032 ms; 1500 inert at 1904 ms; long utterance unaffected). |
| AC-10 | Junk filter table | PASS | desktop/src-tauri/src/transcript_filter.rs:99-118 (the_ac_10_table) (the AC table verbatim, 8 drops + 3 keeps); desktop/src-tauri/src/transcript_filter.rs:121-136 (the_listed_hallucinations_are_dropped_in_any_case_and_spacing) (also "[blank_audio]", "(silence)" via the tag step, see D-11). |
| AC-11 | Filtered transcript: nothing sent, no Sent cue, reason "nothing heard"; fixtures (d)/(e) same | PASS (synthetic audio, headless; not verified on hardware; no-cue clause by code order only, not observable in a test) | desktop/src-tauri/src/listen.rs:1143-1151 (a_junk_transcript_sends_nothing_and_ends_as_nothing_heard) (fake console empty); desktop/src-tauri/src/listen.rs:1154-1158 (the_filter_runs_before_the_gate); desktop/src-tauri/src/listen.rs:1209-1221 (replaying_the_silence_and_noise_fixtures_ends_the_take_as_nothing_heard); desktop/src-tauri/src/listen.rs:1182-1205 (the_real_engines_answers_to_silence_and_noise_are_filtered) (my run: real engine said "you" for d, e, g); cue plays only after say at desktop/src-tauri/src/listen.rs:631-632, after the filter return at desktop/src-tauri/src/listen.rs:602. |
| AC-12 | CC_TTS_SINK_WAV: valid WAV, no output device; unsupported backend errors | PASS (synthetic audio, headless; not verified on hardware; "no output device opened" by code path only) | desktop/src-tauri/src/piper.rs:651-672 (piper_speaks_into_a_wav_file_when_a_sink_is_given) (real Piper: RIFF, >2 kB data, voice rate; my run ok); desktop/src-tauri/src/piper.rs:289-310 (write_sink) and the sink branch at desktop/src-tauri/src/piper.rs:263-266 never call play(); desktop/src-tauri/src/tts.rs:364-374 (a_file_sink_is_refused_by_every_backend_but_piper). |
| AC-13 | source:"file" in /listen/state; WARN logged; no key/route can enable replay; hands-free loop fed wake wav + request fires and takes headlessly | PASS (synthetic audio, headless; not verified on hardware; the WARN line itself is not captured, its text is asserted) | desktop/src-tauri/src/replay.rs:812-817 (listen_state_says_where_the_audio_comes_from); desktop/src-tauri/src/replay.rs:397-405 (a_replay_says_file_and_warns_once_naming_only_the_file); desktop/src-tauri/src/replay.rs:800-809 (nothing_in_the_console_or_its_settings_can_turn_replay_on); desktop/src-tauri/src/hands_free.rs:659 (the_armed_loop_fed_a_replay_wakes_and_takes_the_request_with_no_microphone) (my run: wake score 0.60, one POST with text "What is open?" and source voice); console/tests/test_assistant_commands.py:386::test_replay_can_not_be_turned_on_from_settings; grep: only replay.rs:160-162 reads CC_REPLAY_WAV/CC_TTS_SINK_WAV, nothing under console/ except that test. |
| AC-14 | Console tests: defaults, bounds, allowlist; limits_from reads them | PASS | console/tests/test_assistant_commands.py:367::test_the_merge_window_has_defaults_and_is_writable; console/tests/test_assistant_commands.py:382::test_a_merge_dial_outside_its_range_is_refused (-1, 5001, -1, 9); console/tests/test_assistant_commands.py:937::test_the_classification_matches_decision_d8; desktop/src-tauri/src/listen.rs:773-794 (limits_from_reads_the_merge_window_and_falls_back_to_the_defaults) and limits_from_clamps_a_hand_edited_merge_window. |
| AC-15 | Full desktop unit suite and console tests pass; existing endpointer tests unchanged | PASS (one pre-existing unrelated failure, see Test Results) | Independent re-run, counts under Test Results: cargo 365 passed / 0 failed (single-threaded and parallel x2), pytest 1 failed 2884 passed 1 skipped; the failure is console/tests/test_stylesheet.py:133 (onboarding-wizard.js .ob-count), same as the baseline. Existing endpointer tests: the audio.rs diff adds tests and two accessors only (T-032-progress.md entries T-032-01 and T-032-08). |

## Test Results

| Run | Command | Result |
|-----|---------|--------|
| Rust, single-threaded | `cargo test -- --test-threads=1` via cargo-safe.ps1 | `test result: ok. 365 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 38.58s` |
| Rust, default parallel #1 | `cargo test` | `test result: ok. 365 passed; 0 failed; ... finished in 18.41s` |
| Rust, default parallel #2 | `cargo test` | `test result: ok. 365 passed; 0 failed` |
| Rust, check | `cargo check` | `Finished dev profile`; 0 warning lines |
| Rust, real-engine subset | `cargo test -- --test-threads=1 --nocapture` with 5 name filters (AC-2, AC-11, AC-12, AC-13 tests) | `test result: ok. 5 passed; 0 failed`; whisper-server and Piper really ran (nothing skipped) |
| Python, full | `PYTHONUTF8=1 python -m pytest -o addopts="" -q -p no:cacheprovider` | `1 failed, 2884 passed, 1 skipped in 317.88s`; failing id `console/tests/test_stylesheet.py::test_every_class_the_js_styles_actually_exists` (`onboarding-wizard.js: .ob-count`) |
| Fixture reproducibility | `python desktop/tests/gen_replay_fixtures.py --check` | 8 same / 0 different; sha256 prefixes of d, e, f, g, g2 equal the committed files; fixture files unchanged afterwards |

Builder-reported vs independent: cargo 365/365 x3 matches; check 0 warnings matches; pytest `1 failed, 2884 passed, 1 skipped` matches exactly. The one failing test belongs to another ticket (a CSS rule for `.ob-count` in the onboarding wizard) and was not touched.

Stray processes: whisper-server.exe and piper.exe listed before and after every cargo run (`.meta` BEFORE and AFTER both empty) and after pytest: none left.

## Verify Cases (folded)

No separate `T-032-test-cases.md` was written. The plan's AC coverage table plus the AC rows above carry the case-to-AC trace (each AC maps to named, committed tests). No AC is without an automated case; the clauses that are code-path only are labelled in the rows.

## Edge Cases Probed

- Exhausted file source (CR-1): `record_frames` ends the take when `fresh.is_empty() && src.exhausted()` (desktop/src-tauri/src/audio.rs:997-1000); proved by a thread-guarded test that fails instead of hanging (desktop/src-tauri/src/replay.rs:469-489). No hang.
- Live mic wall-clock backstop (CR-2): present (desktop/src-tauri/src/audio.rs:967, `src.live() && started.elapsed() >= limits.max_take`), `Mic::live()` is true (desktop/src-tauri/src/audio.rs:924), file sources are not live. Verified by reading only: no test drives a stalled live source.
- Merge window / cap / parity: read `Window::push` (desktop/src-tauri/src/audio.rs:549-595): window 0 returns the bare Endpointer result (exact parity); max_merges reached waits only the first_pause floor; a resume is the Endpointer's own debounced run so clicks never merge.
- Pre-roll counts toward the cap (desktop/src-tauri/src/replay.rs:491-513).
- Replay playhead survives reopen and error (desktop/src-tauri/src/replay.rs:407-422); a missing file error contains "microphone" so hands-free stops rather than retries (desktop/src-tauri/src/replay.rs:424-430).
- Junk filter order: `deliver` filters before the gate; an empty result returns `Err("nothing heard")` and tray Cancel (desktop/src-tauri/src/listen.rs:597-603), distinct from the "speech engine returned nothing" path (desktop/src-tauri/src/listen.rs:556-559); the log line carries a word count and a reason only (desktop/src-tauri/src/listen.rs:638-640). `stt::transcribe` has one production call site (desktop/src-tauri/src/listen.rs:553), so push-to-talk, tray and hands-free share the one filter.
- Malformed input: non-16-bit WAV, truncated header, oversize data chunk (desktop/src-tauri/src/replay.rs:355-369); out-of-range console values rejected (console/tests/test_assistant_commands.py:382).

## Findings (challenge-implementation, ready review)

0 critical, 0 blocking. Minor and informational:

1. D-10 (OPEN, owner): the 300 ms tail trim is unconditional, so with the window at 0 the take ends at the same moment as before but STT gets about 400 ms less trailing silence (fixture a: 47616/40192 -> 41152/31936 samples). AC-5 holds for take boundaries, not for audio bytes.
2. D-11 (finding, owner informed): through the shipped whisper-server the noise fixture g2 returned a fluent sentence, so the filter does not catch it (by design, D-9, todo TD-1). Silence and low noise return "you" and are filtered. FR-6(g) "known hallucination" is met by silence -> "you" (an FR-15 list entry); "Thank you." was not found.
3. Corner: when `max_merges` is reached on an utterance under 1200 ms of speech with `first_pause` above silence, speech resuming inside the first_pause floor still merges, so `Take.merges` can read max+1. Today's first_pause behaves the same way; no AC is affected.
4. Test strength: AC-8's cap is proven at a 4 s limit; AC-9 only at pure unit level; AC-7's replay assertions allow one 16 ms frame over 300 ms (the pure test is exact); the Sent cue and the WARN log line are not directly observable in tests (asserted by code order and by the warning text).
5. Unchanged pre-existing behaviour: `listen.rs:623` logs the transcript of a sent (addressed) request; not part of FR-16, not changed.
6. Process: the builder's SIMPLIFY was a single-pass inline review (the agent fan-out was unavailable); `cargo check` has 0 warnings.

## Not Verified (hardware / human)

- A real microphone, a real human voice, the live `Mic` path end to end (the live cap backstop and sleep pacing are code-read only).
- V-7 (owner): the feel of the 1.2 s window and an audible Sent cue; the manual live-mic regression pass. OPEN.
- Whether replayed synthetic fixtures count as T-019 AC-7/AC-8 evidence is T-019's call (D-8).

## Hygiene

- `git ls-files --eol`: every touched tracked file `i/lf w/crlf`; the four new source/doc files `w/crlf`; `T-032-plan.md` and `ticket.toml` `w/lf`; a byte count found no mixed endings in any touched file.
- `desktop/src-tauri/Cargo.toml`, `Cargo.lock`, `console/static/*` unchanged (empty `git diff`); no new dependency. The only non-T-032 change in the tree is `knowledge-center/telemetry/2026-10.jsonl`.
- `git diff --stat`: 18 tracked files, +1325/-172 (includes the telemetry line); untracked: replay.rs, transcript_filter.rs, README-replay.md, gen_replay_fixtures.py, 8 fixture wavs.

## Artifact drift (reconcile)

- `T-032-summary.md` is stale: Status "Open", Stage "CANONICAL", Current State says "none built ... No code exists. Lane is `open`". Reality: 14/14 tasks done, lane `verify`.
- `T-032-progress.md` "Status Summary" still says "Stage: TEMPLATE - slice 1 ... in build", and the 2026-10-05 entry is the empty template (Done/Started/Blocked/Next blank). Dated entries are in order, none fused; one `## Links` block.
- `T-032-summary.md` Links block omits context-snapshot, gap-analysis, iteration-log, release, requirements-draft (siblings); each of those files has a single `## Links`. The artifact-map row still says "Open".
- `T-032-plan.md`: all 14 task headers are ticked, their inner sub-checkboxes are left unticked.
- No fix applied by the verifier (it does not write plan or summary); route to `progress-tracker`.

## Links
- [[T-032-summary]] · [[T-032-analysis]] · [[T-032-requirements]] · [[T-032-decision-log]] · [[T-032-plan]] · [[T-032-progress]] · [[T-032-verification]]
