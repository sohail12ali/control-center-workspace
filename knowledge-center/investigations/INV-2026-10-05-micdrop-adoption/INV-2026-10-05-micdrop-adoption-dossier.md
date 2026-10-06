---
id: INV-2026-10-05-micdrop-adoption
date: 2026-10-05
owner: Sohail Ali
type: roadmap-dossier
status: approved
---

# Mic Drop — what Control Center can adopt

Scope: `control-center-workspace` measured against Mic Drop (`D:\Workspace\noble-workspace\mic-drop`, Rust,
v1.0.0-alpha.2, branch `rust-rewrite`; a voice front-end for *external* coding agents).
Classification: **feature/roadmap** — nothing here is a defect report, except the one bug in §1 that fell out of the comparison.

The two overlap on audio and model plumbing and differ on purpose: Mic Drop speaks to Claude Code / Cursor / Codex through
hooks and MCP; the control center's voice pipeline serves the console Assistant. So: **port the ideas that close real
gaps, not the code and not the agent integration.**

Method: three read-only Explore passes (Mic Drop models+audio; Mic Drop conversation+integration+UX; control-center voice
baseline) plus direct reads of `desktop/src-tauri/src/stt.rs`, `console/server/assistant_commands.py` and
`desktop/features.toml`. Mic Drop paths below are relative to its repo root. Mic Drop's working tree had 13 uncommitted files
when read, so some behaviour may still change.

---

## 1. Ground truth

### Already covered here — do not rebuild

Push-to-talk toggle (Ctrl+Alt+Space) · hands-free + wake word (rustpotter, user-recorded) · whisper.cpp local STT (`ggml-base.en`) ·
Piper TTS + OS-voice fallback · earshot VAD with adaptive floor · HUD with level meter · tray with state · earcons (`cue.rs`) ·
fast-command table with homophones (`assistant_commands.py`) · voice diagnostics panel · SSE state stream · shell↔console bridge.

### Gaps this dossier targets

| Gap | Evidence |
|---|---|
| **Bug:** a changed `stt_model` never reaches a running engine | `desktop/src-tauri/src/stt.rs:49-55` stores `Engine.model`; `ensure()` at `:245-269` compares only `engine.prompt` (`:255`). Verified by reading both. |
| No in-app model download/management | Manual `desktop/get-whisper.ps1` (Windows x64 only); Settings prints a hint. `stt::hint` points at `get-whisper.sh`, which does not exist. |
| No input/output device choice | `default_input_device()` (`audio.rs`, `Mic::open`) and `default_output_device()` (`piper.rs`, `cue.rs`). Explorer-reported; not re-run. |
| Noise transcribed as speech | `host.log` 2026-10-05: one take recorded 1.9 s of audio, transcribed "Hey, I'm gonna miss you." Explorer-reported. |
| No follow-up window after a reply | Each hands-free turn needs the wake word again. Explorer-reported. |
| Hotkeys/mute not wired | One hardcoded chord in `main.rs`; `desktop.hotkey.*` prefs specified in `desktop/features.toml` but unread; `mic_muted` and `dictate` rows are `available = false` (verified). |
| No audio-control voice commands | `assistant_commands.py` table has stop, mute, new chat, use-backend, status, digest, ticket ops, copy, remember, screenshot — no repeat/speed/model/voice (verified). |
| Spoken reply is the *first* paragraph | `console/server/assistant_reply.py`. Mic Drop abandoned that rule for an outcome-based summary. |
| Cloud STT approved but not built | Memory `desktop-assistant-programme`; `console/server/dotenv.py` `KEY_ALLOWLIST` is OPENROUTER / OPENAI / LMSTUDIO only. |
| T-019 AC-7/8 blocked on "a human voice" | No way to replay audio through the pipeline headlessly. |

---

## 2. Verdict per Mic Drop feature

**INCLUDE** = real gap, port it · **ADAPT** = take the idea, different implementation · **DEFER** = later or spike · **SKIP** = not for this project.

### A. Models

| # | Mic Drop feature | Verdict | Ticket |
|---|---|---|---|
| A1 | In-app model manager: catalog, installed / size / "in use", Download · Pause · Resume · Cancel · Delete, progress + speed + ETA | **INCLUDE** | [[T-031-summary]] |
| A2 | Resumable downloads: `.part` + HTTP Range, retry with backoff, "installed" only once a marker file lands last. **Improve on Mic Drop: add SHA256 verification** (it checks size only) | **INCLUDE** | [[T-031-summary]] |
| A3 | Picker over *installed* models + live swap (old keeps serving until the new one is ready) — also fixes the `ensure()` bug above | **INCLUDE** | [[T-031-summary]] |
| A4 | Size/quality hints (tiny ~100 MB … medium ~950 MB) | **INCLUDE** | [[T-031-summary]] |
| A5 | Voice picker + preview + speed slider | **INCLUDE** (UI; `speak_voices` already in bridge `/health`) | [[T-031-summary]] |
| A6 | Cloud STT: OpenAI-compatible `base_url`, key by env-var *name*, never stored | **INCLUDE**, opt-in, off by default | [[T-035-summary]] |
| A7 | Non-English: language setting + multilingual Whisper (`-l en` is hardcoded today) | DEFER | [[T-035-summary]] |
| A8 | Kokoro TTS (28 voices, ~330 MB) | DEFER — needs sherpa-onnx; spike only | [[T-035-summary]] |
| A9 | ElevenLabs cloud TTS | SKIP — extra key and privacy cost for little gain | — |
| A10 | GPU provider select | SKIP — nominal even in Mic Drop (CPU-only static lib) | — |
| A11 | sherpa-onnx as the single runtime | **SKIP wholesale** — large native dependency, rewrites code that just stabilised in T-019 | — |

### B. Audio

| # | Mic Drop feature | Verdict | Ticket |
|---|---|---|---|
| B1 | Device pickers: enumerate, pick **by name** (indices shift), substring match, hot-plug refresh, "(not connected)" | **INCLUDE** | [[T-031-summary]] |
| B2 | Mic test (2 s peak bar) + speaker test tone in Settings | **INCLUDE** | [[T-031-summary]] |
| B3 | Pause-tolerant endpointing: provisional end ~800 ms, wait a further ~1200 ms for resumed speech, merge + re-transcribe (max 4). Reference: `crates/micdrop-core/src/{vad,assembler}.rs` | **INCLUDE** | [[T-032-summary]] |
| B4 | Whisper junk filter: strip `[BLANK_AUDIO]`, `(music)`, `*x*`, drop "Thank you." on silence. Reference: `speech.rs:115-150` | **INCLUDE** | [[T-032-summary]] |
| B5 | Echo cancellation (WebRTC AEC3 via `sonora`) so voice barge-in works on speakers | DEFER — spike; cross-platform build risk | [[T-035-summary]] |
| B6 | Silero VAD | DEFER — only if earshot misfires in real use | — |
| B7 | Wake word from a typed phrase (keyword spotter), no recording | DEFER — needs sherpa-onnx; revisit after T-019 verifies | [[T-035-summary]] |
| B8 | Earcons, standalone noise suppression, AGC | SKIP — earcons exist; Mic Drop has no AGC and NS only inside AEC | — |
| B9 | **Headless wav-replay seam** (`stt.source=file`, `tts.sink=file`) | **INCLUDE** — build first in T-032 so B3/B4 are verified on real audio | [[T-032-summary]] |

### C. Conversation, turn to turn

| # | Mic Drop feature | Verdict | Ticket |
|---|---|---|---|
| C1 | **Turn loop**: mic closed while the agent works, reopens automatically after the reply (or a timeout) with no wake word; modes `turns` / `hands-free` / `push-to-talk`, switchable live | **INCLUDE** | [[T-033-summary]] |
| C2 | Hold-to-talk + rebindable hotkeys (talk / mute / cancel). Tauri global-shortcut reports key-up, so no 60 Hz key polling | **INCLUDE** | [[T-033-summary]] |
| C3 | Mute toggle + pause/resume ("stop listening" — commands still work) | **INCLUDE** | [[T-033-summary]] |
| C4 | Outcome-based spoken summary: short replies whole; else the "Summary/TL;DR" paragraph, else the **last** paragraph, skipping a trailing "Want me to…?". Reference: `text.rs` `spoken_summary` | **INCLUDE** | [[T-033-summary]] |
| C5 | Voice commands: repeat / repeat slowly, faster / slower, bigger / smaller model, switch voice, "what can I say" | **ADAPT** into `assistant_commands.py`, keeping its homophone handling | [[T-033-summary]] |
| C6 | Live barge-in (~200 ms of speech cuts the reply) | DEFER with B5 | [[T-035-summary]] |
| C7 | Dictation: paste into the focused agent window, pinned target, "cancel that" = Esc | DEFER — Windows-only focus; actuation was never in scope; ASK-gated | — |
| C8 | Per-agent voice, name routing, sessions mode | SKIP routing. **ADAPT later:** a distinct voice per role and spoken run-done / blocked announcements via the existing `attention` events | — |
| C9 | Hooks / `connect`, MCP tools, `claude -p` bridge, skill installers, inbox | SKIP — the console has its own MCP server and agent runner (T-023..T-028); Mic Drop stays the voice layer for external agents | — |

### D. UX and ops

| # | Mic Drop feature | Verdict | Ticket |
|---|---|---|---|
| D1 | Setup wizard Voice step: pick mic with a live meter, pick model (downloads), pick voice with an audible test. **Coordinate:** `onboarding_setup.py` and `onboarding-wizard.js` are uncommitted work on 2026-10-05 | **INCLUDE**, after T-031 | [[T-034-summary]] |
| D2 | Doctor: `--fix` pulls missing models; `--deep` records 2 s and plays a tone | **INCLUDE** — actions on the existing voice diagnostics panel | [[T-034-summary]] |
| D3 | Tray Microphone / Speaker / Listening-mode submenus, hot-plug refreshed | **INCLUDE**, after B1 | [[T-034-summary]] |
| D4 | Settings marks each key "(live)" or "(restart needed)" | **INCLUDE** (small) | [[T-031-summary]] |
| D5 | Live endpointing view (`micdrop tune`) | DEFER | — |
| D6 | Chat history with search, replay, prune | SKIP — one chat surface is [[T-030-summary]]; a "read this aloud" button can ride on it | — |
| D7 | npm launcher / installer / updater, Python legacy tree, plaintext uncapped `transcript.jsonl` | SKIP | — |

---

## 3. Order

1. [[T-031-summary]] — voice assets and devices (foundation; includes the `ensure()` fix).
2. [[T-032-summary]] — hear me properly (wav-replay seam first).
3. [[T-033-summary]] — talk turn to turn.
4. [[T-034-summary]] — onboarding and health (after T-031; wait for the uncommitted onboarding work to land).
5. [[T-035-summary]] — opt-ins and spikes.

## 4. Design decisions

- **Downloader lives in the console (Python), not the shell.** Settings UI and `assistant_config.py` are already there; it is cross-platform (closes the missing `get-whisper.sh` and Windows-only `get-piper.ps1` gap); it writes into `desktop/stt/` and `desktop/tts/`. The shell only reports installed assets through the existing bridge `/health` caps.
- **Port mechanics, not code:** `crates/micdrop-core/src/{download,models,catalog}.rs` (Range/resume/backoff/marker-last, static catalog), `vad.rs` + `assembler.rs` (merge window), `speech.rs` (filter), `text.rs` (summary).
- **Do not adopt sherpa-onnx** unless A8/B7 justify it after T-035.
- **Do not copy Mic Drop's weak spots:** no download checksums; config keys accepted but unused (`audio.sample_rate`, `stt.compute_type`); English-only commands; plaintext uncapped transcripts.

## 5. Evidence status

- **Verified directly:** the `stt.rs` model-staleness bug; `dictate` / `mic_muted` unavailable; the `assistant_commands.py` command list; onboarding files untracked; T-020 / T-021 active.
- **Explorer-reported, not re-run:** all Mic Drop behaviour (no checksums, merge-window timings, AEC wiring, unused config keys), and the control-center claims of no device selection, no cloud STT, and the `host.log` mis-transcription.
- **Unverified:** whether `sonora` (AEC3) builds on all three CI targets — the point of the B5 spike in T-035.

## Links
- [[T-031-summary]] · [[T-032-summary]] · [[T-033-summary]] · [[T-034-summary]] · [[T-035-summary]]
- Related: [[INV-2026-10-01-paperclip-adoption-dossier]] · [[T-019-summary]] · [[T-030-summary]]
