---
ticket: "T-010"
artifact: verification
---

# Verification: T-010

Verified 2026-09-07. **cargo test 123 passed** (110 before T-010), pytest
green, and every latency number below is measured from the shell's own log on
this machine rather than estimated.

## The headline

A spoken command, click to answer:

| | Before | After |
|---|---|---|
| Whole take | **29 665 ms** | **5 317 ms** |
| Waiting for the tray's mutex | 5 682 ms | 0 |
| Recording after you stopped talking | up to 20 000 ms | ~700 ms |
| Transcription (3.7 s of audio) | ~2 900 ms | 753 ms |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Where the time goes is measurable | PASS | Every take logs `took Xms (checks, record, stt, post)`; `CONSOLE_LOG=debug` adds a line per step. This is what found the rest of this table |
| 2 | The state-mutex stall is gone | PASS | `paint_listening` went from **2 947 ms** to **4 ms**. `tray_link` held the assistant lock across its three-second reconnect sleep, so every shell-side state change queued behind it — twice per take |
| 3 | A take ends when you stop | PASS | Live: `3.1s of audio, ended by Silence` and `3.7s … Silence`, where the same phrases previously logged `20.0s … Capped` |
| 4 | A noisy room cannot hold a take open | PASS | Unit: after speech, one high-scoring frame every ten (a tap, a fan harmonic) no longer resets the silence counter — `SPEECH_RUN` requires three frames in a row. This is the exact live failure from the first attempt, where a 3 s phrase recorded for 9.4 s |
| 5 | Transcription is faster with the same words | PASS | Same WAV through `whisper-cli`: 2 854 ms → 2 209 ms, byte-identical transcript. Flags: `-t 18 -bo 1 -nf -mc 0 -sns` |
| 6 | Hands-free opens the microphone once | PASS | Live: one `microphone open in 2287ms` for a session of two takes; the second take has no open at all. Push-to-talk still opens and closes per take, so the OS indicator stays honest |
| 7 | `tiny.en` is choosable, and not by accident | PASS | `stt_model` names the model; `model_file` no longer picks "smallest installed", which would have switched silently the moment a second model was downloaded. A name that looks like a path is refused |
| 8 | The overlay shows what is happening | PASS | Screenshotted mid-take: red dot, "Listening", the level meter, and the hint. It appears on a take and hides itself afterwards |
| 9 | The transcript appears before the answer | PASS | `tray_paint::said` pushes the heard text as soon as it is transcribed, so "did it get that right" is answered before the model has replied |
| 10 | Tones mark the mic opening and the send | PASS | Rendered and asserted in unit tests (audible peak, silent edges, rising for open and falling for dropped); heard live on this machine |
| 11 | One switch for speaking | PASS | Live through the tray menu: `speak` went `true → false → true` as *Mute replies* was ticked and unticked. Before, the tray toggle only reached the webview's `autoRead` while the server spoke anyway |
| 12 | The tray's initial tick is read, not assumed | PASS | Startup reads `speak` from the merged settings; it used to default to checked, disagreeing with a setting that defaults to on |

## Test Results

```
cargo test (desktop/src-tauri)        ->  123 passed
python -m pytest -o addopts="" -q     -> green (see below)
python console/kanban.py harness lint -> 0 error(s), 0 warning(s)
```

## The measurement that mattered

The 3-second gap between clicking and the microphone opening had three
suspects and the log ruled out all of them:

```
listen: step tts_stop 0ms
listen: step paint_listening 2947ms      <- here
tray-paint: by_id 0ms, decode 1ms, set_icon 2ms
```

Painting the icon costs 3 ms. *Waiting to be allowed to paint it* cost three
seconds, because `tray_link`'s reconnect loop wrote

```rust
if let Ok(a) = assistant.lock() { if ... { std::thread::sleep(RETRY); continue; } }
```

— holding the lock for the whole backoff. It cost that twice per take, and it
would have gone on being invisible: nothing was broken, everything was just
slow. Reading the state and releasing it before sleeping is the entire fix.

## Known and not fixed

- **Push-to-talk still waits ~0.9 s for the microphone.** That is
  `build_input_stream` plus `play` on WASAPI, measured at 870-2000 ms with
  finding the device and reading its format under 10 ms between them. Holding
  the stream open permanently would fix it and would also light the OS
  microphone indicator all day, which is a worse trade. The opening tone
  exists because of this: it plays when the mic is actually live.
- **The wake word depends on the first word surviving the recogniser.** In
  these tests the phrase was played through speakers into an array
  microphone, and "Console, what is open?" came back as "And so what is
  open?" — so hands-free discarded it, correctly, as unaddressed. That is
  partly a rig artifact, and partly a real property worth knowing: the first
  word is the one most often mangled, and it is the one the gate depends on.
  Not changed here, because loosening the rule is a decision about the rule.

## Links
- [[T-010-summary]] · [[T-010-analysis]] · [[T-010-requirements]] · [[T-010-decision-log]] · [[T-010-plan]] · [[T-010-progress]] · [[T-010-verification]]
