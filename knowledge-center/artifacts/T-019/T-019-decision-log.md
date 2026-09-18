---
ticket: "T-019"
artifact: decision-log
---

# Decisions: T-019

## D-1 — Wake detection moves off the transcript and onto the audio

**Decided:** a dedicated always-on spotter scores the microphone stream; whisper is not
started unless it fires.

**Why:** the old design answered "was that for me?" by running a recogniser on everything
and matching text. That is expensive (a second of inference per noise), deaf (the mic was
cleared between takes) and unreliable (`base.en` does not reliably write "console").
Every local-voice stack that works this way — Home Assistant's Assist pipeline over
Wyoming, LiveKit Agents, pipecat — stages it the other way round.

**Rejected:** keeping whisper and fixing it around the edges (a ring buffer plus fuzzy
matching plus prompt bias). Cheaper to build, but it still pays ~1.5s of CPU for every
noise in the room, and it still sends speech nobody addressed through a recogniser.

## D-2 — rustpotter, with recordings you make yourself

**Decided:** `rustpotter = "3"`, Apache-2.0, with the wakeword built from 3-8 recordings
of the user's own phrase, stored at `desktop/stt/wake/{name}.rpw` (gitignored — it is a
recording of somebody's voice).

**Why:** pure Rust, no ONNX runtime and no C toolchain, which is the constraint
`Cargo.toml` already states for `cpal` and `earshot`. It is trained on the user's voice
saying the user's phrase rather than on one of three phrases somebody else trained.

**Rejected:** openWakeWord's pretrained models (oww_rs, livekit-wakeword). More accurate
in the abstract, but the pretrained models are CC-BY-NC-SA and limited to "hey jarvis" /
"alexa" / "hey mycroft" unless retrained — and this workspace is a reusable template.

**Correction to the approved plan:** rustpotter is Apache-2.0, not MIT as the plan said.

**Cost, recorded because it is a real one:** rustpotter 3.0.2 is dormant (Oct 2023) and
pulls `candle-core 0.2.2`, which no longer compiles — `half` 2.4+ moved its `SampleUniform`
impls to `rand_distr` 0.5 while candle uses 0.4, giving twenty trait-bound errors that name
neither crate. Pinned with a direct `half = "=2.3.1"` dependency in `Cargo.toml`, with the
reason written above it, because a lockfile entry would not survive `cargo update`. If this
becomes untenable, the fallback is `oww_rs`.

## D-3 — The old path stays as a fallback, and says so

**Decided:** a machine with no wakeword recorded still gets hands-free, on the old
transcribe-everything gate, and the log and Settings both say which is running.

**Why:** the alternative is a tray switch that does nothing until you have visited a
settings page you do not know exists. Silence about which of two very different behaviours
is in force is the failure mode this whole ticket is about.

## D-4 — The first-pause grace is hands-free only

**Decided:** `listen_first_pause_ms` (1500) applies only while an utterance is still under
~1.2s of speech, and only on the hands-free path. `Endpointer::new` and `Limits::default`
ask for no grace at all.

**Why:** a pause straight after a wake word is someone deciding what to ask. A pause after
a push-to-talk keypress is someone finishing a short command — "open T-002" — and making
that wait 1.5s is the same mistake in the other direction. Caught by an existing test
(`a_configured_silence_window_is_honoured`) failing.

## D-5 — No `voice_backend` setting

**Decided:** the approved plan proposed a separate backend for spoken turns. Not built.

**Why:** `backend` already means "what answers the Assistant", and a spoken turn and a
typed one are deliberately the same turn through the same endpoint. A third overlapping
setting would be a second answer to one question, against the CANONICAL gate. The real
problem was configuration, and it is reported rather than routed around — see
[[T-019-summary]] § Reply speed.

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
