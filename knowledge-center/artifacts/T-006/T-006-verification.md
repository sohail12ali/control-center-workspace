---
ticket: "T-006"
artifact: verification
---

# Verification: T-006

Verified 2026-09-07 against the release build on Windows 11.
**pytest 1023 passed** (992 before T-006), **cargo test 84 passed** (47 before),
zero compiler warnings, harness lint clean (39 skills, 7 agents).

`-o addopts=""` is needed for a trustworthy pytest count — `pytest.ini` sets
`-q`, under which this suite prints only progress dots.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Audio crates build here | PASS | Spiked before writing code against them: `cpal 0.16.0`, `earshot 1.2.2`, `tauri-plugin-global-shortcut 2.3.2`, `cargo build` exit 0. Still no CMake or LLVM needed |
| 2 | Real audio hardware reachable | PASS | Probe: input `Headset (realme Buds T500 Pro)` 1 ch **16000 Hz** F32, output present. Later run picked `Microphone Array (Intel Smart Sound)` — the default device is read live, not cached |
| 3 | Mic capture down to 16 kHz mono | PASS | `audio.rs`; 12 unit tests including a 1 kHz tone surviving 48→16 kHz resampling (190–210 zero crossings), stereo averaging, and clamping rather than wrapping out-of-range samples |
| 4 | A take ends when the speaker stops | PASS | `Endpointer` unit tests: leading silence never ends a take, 300 ms of speech plus 700 ms of silence does, a 48 ms click is not speech, a mid-sentence pause does not chop the take (that is what the two thresholds are for) |
| 5 | Speech to text, end to end | PASS | Live, against the real engine: `stt: model=ggml-base.en.bin heard "Status ticket too"` from a committed WAV fixture of synthesised speech. No microphone or person needed to re-run it |
| 6 | Engine fetched deliberately, never automatically | PASS | `desktop/get-whisper.ps1` (pinned `b4938`, `-WhatIf` supported). Absent engine → tray unavailable with the exact command to run. `desktop/stt/` gitignored |
| 7 | Replies read aloud | PASS | Live: `tts: backend=system.speech spoke 31 chars then stopped`. Process-based on all three platforms (`System.Speech` / `say` / `spd-say`) — nothing to install |
| 8 | Barge-in | PASS | `tts::stop()` kills the utterance; `listen` calls it before opening the mic, so talking over a reply interrupts it. Unit test covers stop-then-finished |
| 9 | `copy that` works (FR-8 from T-004) | PASS | The gap T-004 left: nothing called `write_last_reply`, so this could only answer "no last reply yet". Live: a real turn recorded a 194-char reply, `copy that` → `Copied.`, and the clipboard preview matched the reply |
| 10 | Muted means silent, but still copyable | PASS | `test_assistant_reply.py`: muted records the reply and speaks nothing; unmuted speaks the trimmed first paragraph; `reply_chars` honoured |
| 11 | Spoken replies are trimmed, not read whole | PASS | First paragraph, markdown stripped, capped at a sentence boundary. A model asked to be terse still emits headings; reading `##` aloud is worse than reading nothing |
| 12 | Push-to-talk hotkey | PASS (code) | `Ctrl+Alt+Space`, registered Rust-side so no capability is widened; a chord another app owns logs a warning rather than failing silently. **The physical keypress was not exercised** — see Not verified |
| 13 | One take at a time | PASS | Live: a second `POST /listen` while listening returned `already listening`; `release` ended it |
| 14 | Capabilities probed, not assumed | PASS | Live `/health`: `stt: true, stt_model: ggml-base.en.bin, speak: true, speak_backend: system.speech, ocr: true, capture: true`, `stt_hint: ""`. `/listen/state` names the microphone and whether the engine is loaded |
| 15 | Spoken ticket ids resolve | PASS | Driven by the real transcript. `Status ticket too` → `T-002`, and `for`→4, `won`→1 likewise. Homophones apply only inside an identified ticket span; `status of the migration` still falls through |
| 16 | The tray reflects the whole cycle | PASS | Live: `idle → listening → idle` around a real take, and `idle → thinking → idle` around a real turn |
| 17 | Nothing breaks the other platforms | PARTIAL | Compiles and tests green on Windows. The macOS and Linux paths (`say`, `spd-say`, `espeak-ng`, Linux/macOS whisper builds, Cmd+Option+Space) are written but **unexercised** — no hardware |

## Test Results

```
python -m pytest -o addopts="" -q     -> 1023 passed
cargo test                            ->   84 passed, 0 warnings
python console/kanban.py harness lint -> 39 skills, 7 agents | 0 error(s), 0 warning(s)
```

All three hardware paths in one run:

```
ocr: engine=winrt language=en-GB read "HELLO"
tts: backend=system.speech spoke 31 chars then stopped
stt: model=ggml-base.en.bin heard "Status ticket too"
```

Live, release build:

```
caps: stt=True  stt_model=ggml-base.en.bin  speak=True  speak_backend=system.speech
      ocr=True  capture=True   stt_hint=''

listen/state: available=True
              microphone='Microphone Array (Intel Smart Sound Technology...)'

POST /listen start   -> {listening: true}
POST /listen start   -> {ok: false, reason: 'already listening'}
POST /listen release -> {listening: false}
host.log             -> listen: nothing heard        (correct - nobody spoke)
tray during a take   -> ['listening']                (after the fix below)

a real turn          -> last reply recorded (194 chars)
'copy that'          -> {result: handled, command: copy_last, spoken: 'Copied.'}
clipboard preview    -> matched the reply
```

## Edge Cases Probed

- **Nothing heard**: a take with no speech returns `nothing heard` and does not
  start the engine at all — no wasted model load.
- **A transcript is untrusted text**: quotes, backslashes and control
  characters in it are JSON-escaped before the POST, so a recogniser's output
  cannot malform the request.
- **Engine died between takes**: `ensure` notices a dead or unresponsive child
  and restarts it rather than reporting a failure nobody can act on.
- **Two clipboard opens, two WinRT calls**: covered by T-005's mutex and OCR
  worker; still green with the new modules in the process.
- **A long reply**: capped at a sentence boundary, not mid-word.

## Notes

### Three real bugs, all found by running it rather than reading it

1. **The HTTP client hung instead of transcribing.** `whisper-server` answers
   with `Keep-Alive` and a `Content-Length`, ignoring a `Connection: close`
   request header. Reading the body to end-of-stream therefore waited for a
   close that was never coming, with the transcript already sitting in the
   socket. Now it honours `Content-Length`.
2. **Spoken ticket numbers did not resolve.** The engine transcribes "two" as
   **"too"**, so `status ticket two` — the headline example — fell through to a
   model instead of being answered for free. Fixed with a homophone table
   scoped to ticket-id spans only, and the real transcript is now a test case.
3. **The tray showed "idle" while the microphone was open.** `tray_link`'s
   reconnect loop applied `TurnEnd` unconditionally every few seconds, and
   since the stream 404s until an assistant chat exists, it repeatedly cleared
   a state the *shell* owns. It now clears only a stale `Thinking`. Two
   regression tests pin it.

A fourth was mine, not the product's: the live speech test left the engine
running, holding the test harness open on exit and looking exactly like a
hang. It now shuts the engine down before asserting.

### Not verified

- **The physical hotkey press.** Registration is covered and logged; sending a
  real system-wide chord to a running shell was not automated. One keypress by
  hand would close it.
- **A person speaking into the microphone.** The capture path is unit-tested
  and the device opens; the speech path is proven with a synthesised WAV
  fixture. What is untested is a live voice through the whole chain at once.
- **macOS and Linux.** No hardware. Recorded as PARTIAL on AC 17 rather than
  claimed.
- **Hands-free listening** was never in this ticket's scope; the mic is
  push-to-talk or click-to-talk.

### What speech costs, stated plainly

Audio never leaves the machine: a local engine process, a local model. The
model is 147 MB on disk and about 270 MB resident while loaded, and the shell
stops it on quit rather than leaving it there.

## Links
- [[T-006-summary]] · [[T-006-analysis]] · [[T-006-requirements]] · [[T-006-decision-log]] · [[T-006-plan]] · [[T-006-progress]] · [[T-006-verification]]
