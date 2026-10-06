---
tags: [active]
status: In Progress
ticket: "T-031"
---

# T-031: Voice assets and devices: model manager, device pickers, mic test

**Status:** In Progress  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

Foundation ticket of the Mic Drop adoption ([[INV-2026-10-05-micdrop-adoption-dossier]]): let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default.

Scope (dossier ids): **A1** model manager (catalog, installed/size/in-use, download · pause · resume · cancel · delete, progress/speed/ETA) · **A2** resumable downloads (`.part` + Range, backoff, marker-last, **SHA256 verify**) · **A3** picker over installed models + live swap, including the `stt.rs` `ensure()` fix (it compares only `engine.prompt`, never `engine.model`) · **A4** size/quality hints · **A5** voice picker + preview · **B1** input/output device pickers by name with hot-plug refresh · **B2** mic test + speaker test tone · **D4** "(live)" / "(restart needed)" flags on Settings keys.

Decision to confirm in `analyze`: the downloader lives in the console (Python), not the shell, and writes into `desktop/stt/` and `desktop/tts/`.

Out of scope: sherpa-onnx, Kokoro, cloud engines, GPU select, the wizard Voice step (T-034).

## Current State

GROUND and CLARIFY complete (2026-10-05): requirements frozen at iteration 2 ([[T-031-requirements]]: 25 FRs, 73 ACs, 14 NFRs). The device-selection claim is confirmed in code (`audio.rs:479,484,550`, `piper.rs:247`, `cue.rs:84`) and the `ensure()` bug confirmed by reading (`stt.rs:255`); upstream SHA256 for all 9 models/voices obtained ([[T-031-decision-log]] D-2). Q1 and Q2 resolved by the user (models and voices only; keep all five voices and show each licence).

CANONICAL (planner, 2026-10-05): multi-layer plan written, [[T-031-plan]]: 9 phases, 39 tasks, **83.5 h** (PERT 82.9 h, range 58.5-105.2 h, confidence Low; envelope in [[T-031-effort-estimate]]), all 73 ACs mapped, [HW] items tracked as "not verified on hardware". `challenge-plan`: 20 findings (4 critical, all resolved in the plan; gate clear), [[T-031-critique-report]] § Plan critique. Awaiting the owner's approval; next: `@builder` on T-031-01 (ticket to in-progress, baselines), then the mandatory mutex-free model swap in `stt.rs` (T-031-04).

BUILD (builder, 2026-10-05): lane `in-progress`; tasks done so far: T-031-01, T-031-02, T-031-03, T-031-04, T-031-05 (Rust; component R1 `stt.rs` complete) and the Python builder's entries in [[T-031-progress]] (count: tick marks in [[T-031-plan]]). Baselines: pytest 2302 passed, 1 pre-existing failure (another ticket's `.ob-count` CSS gap); cargo 181 passed, 0 failed ([[T-031-progress]]). T-031-02 (`stt.rs` model-aware `ensure()`): cargo 190 passed, 0 failed; T-031-03 (`EngineSlot` + injectable `Backend`): cargo 195 passed, 0 failed, real-engine fixture still runs. T-031-04 (mutex-free live model swap with leases): cargo 210 passed, 0 failed, single-threaded and without the flag. T-031-05 (truthful `stt::hint`, wording tests per OS): cargo 215 passed, 0 failed. Phase 4 (Rust, devices by name; component R2) done: T-031-16..19, new `devices.rs` (matcher, preferences + generation, 1 s cache, resolver), `Mic` opens the chosen device, take path and armed loop reopen on a change, playback and cues use the resolver, a source scan keeps one call site; cargo 252 passed, 0 failed (single-threaded and parallel); a real input switch and audibility on a second output are [HW], not verified ([[T-031-progress]]). Phase 5 (Rust) done: T-031-20..24 (`POST /settings/refresh` on a short thread with one settings applier, `/speak` per-request voice and speed, `voice_test.rs` mic test and speaker tone, `/audio/devices`, `/audio/test/*`, `/listen/state` `mic_test`/`swap_error`, caps `loaded_model`/`speak_voice_in_use`); cargo 297 passed, 0 failed, single-threaded and parallel; the live-swap HL test skipped (only base.en installed), tone audibility and bar-follows-voice are [HW] ([[T-031-progress]]). UI (builder, 2026-10-05): T-031-26 (chips), T-031-27 (speech-model manager list), T-031-28 (actions + ARIA progress bar), T-031-29 (`stt_model` picker) and T-031-34 (`get-whisper.ps1:103`) done in `console/static/settings.js` (inside `assistant()`), `console/static/styles.css` (T-031 block) and `desktop/get-whisper.ps1`; `node --check` 0; `test_plugins.py` + `test_stylesheet.py` 24 passed, 1 pre-existing `.ob-count` failure; seen in a headless Chrome against stubbed and real inventories, never against a real download or the shell, so UI-69a..c, UI-27a..e, UI-28a..f, UI-34a..d stay unticked for T-031-38 ([[T-031-progress]]). T-031-30 (voice picker, speed slider, Preview, OS-voice notice), T-031-31 (Audio devices group, pickers by name, 3 s re-list only while visible) and T-031-32 (Test microphone/speaker) done in the same two files; `node --check` 0, same pytest result; seen only in headless Chrome against stubbed device, preview and test answers (the running shell is an old build), so UI-45a..e, UI-59a..e, UI-66a..e stay unticked for T-031-38 and audibility/real plug-unplug are [HW] ([[T-031-progress]]).

VERIFY (verifier, 2026-10-05): 38 of 39 plan tasks done; T-031-38 (UI checklist) stays open by decision D-21 (24 of 33 items observed in a browser, 9 open). Independent re-runs by the verifier: full pytest `1 failed, 2876 passed, 1 skipped` (only the other ticket's `.ob-count` stylesheet test), desktop pytest `41 passed`, harness lint `0 error(s), 20 warning(s)`, `cargo test` `310 passed; 0 failed` (single-threaded and parallel twice), `cargo check`/`check --tests`/`build` clean with 0 warnings. Hardware rows HW-1..HW-8 are NOT verified on hardware; Linux/macOS and CI were not run. Not closed: see [[T-031-verification]] (per-AC table) and the close-check verdict there. Unresolved: the HUD webview incident of the user's running app (see [[T-031-progress]] INCIDENT).

## Links
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Next: [[T-032-summary]] · [[T-034-summary]] depends on this
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-gap-analysis]] · [[T-031-critique-report]] · [[T-031-iteration-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
