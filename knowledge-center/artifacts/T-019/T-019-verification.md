---
ticket: "T-019"
artifact: verification
---

# Verification: T-019

## Automated

| Suite | Result |
|-------|--------|
| `python -m pytest -o addopts=""` | **1445 passed**, 0 failed (baseline 1444; +6 new, −5 folded into existing classes) |
| `cargo test --bins` (`. ./desktop/msvc-env.ps1` first) | **181 passed**, 0 failed (baseline 176) |

New tests, and what each one pins:

- `audio::a_reader_sees_everything_written_while_it_was_away` — the defect itself: audio
  arriving while the shell is transcribing is still there afterwards.
- `audio::the_ring_wraps_without_reordering_the_audio`, `a_burst_longer_than_the_ring_keeps_its_tail` —
  a burst larger than the ring advances the cursor by what was **written**, not what was
  kept. This caught a real bug in the first implementation: the cursor stopped tracking
  real time, which would have silently misplaced every pre-roll.
- `audio::rewinding_gives_back_audio_from_before_now` + `..._is_clamped` — pre-roll.
- `audio::someone_who_has_only_just_started_is_given_longer_to_think`,
  `once_a_sentence_is_under_way_...`, `push_to_talk_asks_for_no_grace_at_all` — D-4.
- `wake::the_spotter_fires_on_the_phrase_it_was_trained_on` — **the load-bearing one.**
- `wake::the_spotter_ignores_speech_that_is_not_the_phrase`.
- `wake::a_built_wakeword_is_what_makes_the_machine_available`.
- `stt::the_prompt_names_the_words_a_general_model_would_not_expect`.

### On the wake fixtures, said plainly

`desktop/tests/fixtures/wake-*.wav` are **synthetic**: piper (`en_US-amy-medium`) saying
"Console." at three paces for training, and "Console, what is open?" / "Shall we get lunch
after this?" / "The console is slow today." for scoring, all resampled to 16 kHz mono.

That is not a substitute for a real voice and is not offered as one. What it does prove,
without a microphone and on every future run, is that the whole path works: build a
template from WAVs, load it, frame the stream in ring-sized reads, score it, fire on the
phrase and not on speech in general. Every one of those was absent before this ticket.

Worth noting: "The console is slow today" does **not** fire it. The word is present; the
spotter is matching sound, not spelling, so the mid-sentence mention the old string gate
could only get right by luck is now simply wrong-sounding.

## Live, on this machine

Debug build launched 2026-09-16 17:00, driven through the real console API, then stopped.

- `GET /api/assistant/voice` → console → bridge → shell, returning the live microphone name
  (`Microphone Array (Intel® Smart Sound Technology...)`), input level, wake score, engine
  state. **Evidence:** the JSON, and the Settings panel rendering it.
- `POST /api/assistant/wake/train` with the three fixtures staged as samples →
  `{"installed": ["console"], "wakeword": "console.rpw"}`, and `available` flipped to true.
- Settings → Assistant → Hands-free renders the recorder (Say it / Build / Remove, with
  "recorded: console"), Sensitivity and Pre-roll. Voice diagnostics renders live.
- `POST /api/assistant/wake/forget` via the Remove button → back to "not recorded —
  hands-free falls back to transcribing everything", and the file is gone from disk.

**Found live and fixed:** `wake::hint` returned "no wake word recorded" while simultaneously
reporting one installed — a panel printing that field would have told someone to record what
they already had. Now empty when available, matching `listen::hint`, with a test.

**Found live and fixed:** `settings.js` threw `appendChild(null)` in the "what will answer
you" panel whenever no backend had been rejected, so it showed an error precisely when
resolution was cleanest. Pre-existing from T-015.

## Not verified, and why

1. **Speaking the wake word into the microphone.** It needs a human voice; every layer
   under it is covered above, but the thing itself is for the owner of the machine to try.
   Record the phrase in Settings first — no wakeword is installed right now, deliberately:
   the synthetic one was removed, because a template of piper's voice would match the user's
   worse than nothing would.
2. **End-to-end spoken latency under ~2.5s.** Depends on the reply backend, which is blocked
   — see [[T-019-summary]] § Reply speed. The listening half of that budget is measurable
   from `listen: took …ms` in `host.log`.
3. **`--vad` / silero in whisper-server.** The bundled build supports it (`--help` confirms
   `--vad`, `-vm`), but no silero ggml is installed and the endpointer already ends takes
   correctly. Not fetched: it would be a download and a dependency for a problem nobody has.

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
