---
ticket: "T-006"
artifact: progress
---

# Progress: T-006

## Status Summary
Stage: VERIFY — voice, speech, spoken replies and the reply watcher built and verified live. Ready to close.

## Dated Log

### 2026-09-07
- Done: 
- Started: 
- Blocked: 
- Next: 

- Done: GROUND — dependency spike first again: `cpal 0.16`, `earshot 1.2.2`, `tauri-plugin-global-shortcut 2.3.2` all build with no C toolchain. Real hardware probed via a throwaway `cargo run --example`: input at 1 ch / **16000 Hz** — already the rate both the VAD and the recogniser want, so the common path does no resampling at all.
- Done: GROUND — the speech engine was downloaded only after asking. `desktop/get-whisper.ps1` (new) fetches a pinned whisper.cpp build and a ggml model into gitignored `desktop/stt/`; nothing in the repo downloads on its own, and an absent engine leaves the tray honestly unavailable with the command to fix it. First attempt 404'd because I used the release TITLE (`v1.9.3`) where the asset URL wants the git TAG (`b4938`) — verified both before correcting.
- Done: TEMPLATE — six new Rust modules: `tts.rs` (OS synthesiser per platform, text via stdin so a reply cannot inject shell syntax, `stop()` is barge-in), `audio.rs` (capture, downmix, resample, VAD end-pointing — a take ends when the SPEAKER stops, not on a timer), `stt.rs` (spawns `whisper-server` once and keeps the model warm; hand-written multipart), `listen.rs` (one spoken command: record → transcribe → the same `/api/assistant/say` a typed message uses), plus `/speak`, `/speak/stop`, `/speak/state`, `/listen`, `/listen/state` on the bridge and a Rust-side push-to-talk hotkey. Python: `assistant_reply.py` — the reply watcher deferred out of T-004 as FR-8.
- Done: TEMPLATE — fixed a T-004 defect found on the way: `STREAM_EVENT_TYPES` listed `attention` and `speaking.*`, which NOTHING emitted — they were placeholders for this watcher, so the stream had been carrying four of its six advertised event types. Replaced with the names a session really publishes; `reply` is now real because the watcher publishes it.
- Done: VERIFY — **cargo test 84 passed** (47 before), **pytest 1023 passed** (992 before), zero warnings, lint clean. All three hardware paths proven in one run: `ocr: engine=winrt read "HELLO"`, `tts: backend=system.speech spoke 31 chars then stopped`, `stt: model=ggml-base.en.bin heard "Status ticket too"`. Live: `copy that` → `Copied.` with the clipboard matching the reply (the thing T-004 could not do); tray `idle → listening → idle` around a take and `idle → thinking → idle` around a turn; a second listen refused with `already listening`. Full evidence in [[T-006-verification]].
- Done: SIMPLIFY — three real bugs, every one found by running it rather than reading it. (1) The STT client HUNG: `whisper-server` answers keep-alive with a `Content-Length` and ignores `Connection: close`, so reading to end-of-stream waited for a close that never came while the transcript sat in the socket — now it honours the length. (2) Spoken ticket ids did not resolve, because the engine transcribes "two" as **"too"**, so the headline example fell through to a model instead of being answered for free — fixed with a homophone table scoped to ticket-id spans only, with the real transcript as the test case. (3) The tray read "idle" WITH THE MICROPHONE OPEN: `tray_link`'s reconnect loop applied `TurnEnd` unconditionally every few seconds, clearing a state the shell owns; it now clears only a stale `Thinking`. A fourth was mine — the live speech test left the engine resident, holding the harness open and looking exactly like a hang.
- Blocked: none.
- Next: `close-work`. One physical hotkey press and one live voice through the whole chain are the only things left that a person has to do; hands-free listening and the Settings-tab control were never in this ticket.

## Links
- [[T-006-summary]] · [[T-006-analysis]] · [[T-006-requirements]] · [[T-006-decision-log]] · [[T-006-plan]] · [[T-006-progress]] · [[T-006-verification]]
