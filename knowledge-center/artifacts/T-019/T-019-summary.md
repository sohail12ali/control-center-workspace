---
tags: [active]
status: Verify
ticket: "T-019"
---

# T-019: Make hands-free listening actually work

**Status:** Verify  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-09-16  
**Due:**  

## Overview

Hands-free listening was unusable, and not for want of tuning: the wake word was
checked by transcribing every sound in the room with whisper and matching the resulting
**text**. This ticket moves detection off the transcript and onto the audio, which is
what the rest of the field does (Home Assistant's Assist pipeline and Wyoming, LiveKit
Agents, pipecat): ring-buffered capture → a cheap always-on spotter → and only then a
recogniser, opened with a pre-roll of the audio from before the word fired.

Claude Code is not prior art here and was checked: it has no hands-free loop at all, and
voice in the Claude apps is press-to-talk dictation to a cloud ASR with server-side
endpointing.

## Current State

Evidence gathered at GROUND, all citable. From `console/.cache/desktop/host.log`,
2026-09-16 16:08 — five consecutive takes, every one discarded:

```
16:08:11 listen: 6.4s of audio, ended by Silence  -> stt 1254ms -> "no console in what was heard"
16:08:21 listen: 8.6s ...                         -> stt 1079ms -> discarded
16:08:27 listen: 5.0s ...                         -> stt 1650ms -> discarded
16:08:39 listen: 10.0s ...                        -> stt 1029ms -> discarded
16:08:49 listen: 8.5s ...                         -> stt 1026ms -> discarded
```

Five causes, four of them in the design rather than in a setting:

1. **Wake word via full-utterance transcription** — `listen.rs:252` gated on text produced
   by whisper, so every noise cost a 5-10s recording plus ~1-1.6s of inference.
2. **The microphone was deaf while that ran** — `audio.rs` `Mic::take` cleared the shared
   buffer at the start of every take, so everything said during transcription and dispatch
   was discarded. The words most likely to be said there are the ones being repeated
   because the assistant just ignored you.
3. **No phonetic tolerance and no decoder bias** — the log says plainly that the recogniser
   wrote a different word.
4. **A 700ms silence cut takes** — splitting "console … what's open" across two takes, the
   second of which can never be addressed.
5. **Replies were slow for a separate reason** — `console/.cache/assistant/settings.json`
   still pins `backend: "claude"`. See § Reply speed: this half is **blocked on a key**,
   not on code.

Baseline before any change: **1444 python tests**, **176 Rust tests**.

## What changed

- `desktop/src-tauri/src/audio.rs` — a `Ring` behind an open microphone; nothing is ever
  cleared, readers hold a cursor, and a reader that falls behind is told so. `Endpointer`
  gained a first-pause grace (hands-free only).
- `desktop/src-tauri/src/wake.rs` (new) — rustpotter spotter, wakeword built from your own
  recordings, sensitivity, live score for diagnostics.
- `desktop/src-tauri/src/hands_free.rs` — the loop is now Armed → Capturing → Dispatch over
  one never-closed microphone. Unaddressed speech reaches no recogniser at all.
- `desktop/src-tauri/src/listen.rs` — `take_after_wake`, which starts a take in the past.
- `desktop/src-tauri/src/stt.rs` — whisper `--prompt` biasing toward the wake word and
  ticket ids; the engine restarts when the prompt changes.
- `console/` — five new settings with validation, four passthrough routes, a wake-word
  recorder and a live Voice diagnostics panel in Settings.

## Reply speed

Blocked, and left blocked rather than worked around: `OPENROUTER_API_KEY` is present in the
workspace `.env` **with an empty value**, and both local runtimes are down
(`127.0.0.1:11434` not listening; `192.168.1.14:1234` not answering). `claude` is correctly
the only backend that resolves. Two things were done rather than none:

- `agent_backends.unavailable_reason` now distinguishes a name that is present-but-empty
  from one that is absent. The old message sent people to look at a line already in the file.
- `settings.js` — the "what will answer you" panel threw `appendChild(null)` whenever
  nothing had been passed over, so it showed an error exactly when resolution was cleanest.
  Pre-existing, from T-015.

## Links
- [[T-019-summary]] · [[T-019-analysis]] · [[T-019-requirements]] · [[T-019-decision-log]] · [[T-019-plan]] · [[T-019-progress]] · [[T-019-verification]]
