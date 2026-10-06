---
ticket: "T-031"
artifact: implementation-plan
---

# Implementation plan: T-031

Master plan: phases, slices, tasks, files, effort. Synthesised from [[T-031-requirements]] (scope and AC), [[T-031-plan]] (approach, risks, canonical Done-criteria), [[T-031-components]] (graph) and [[T-031-task-breakdown]] (atomic tasks). Those are inputs; this file does not repeat their evidence commands.

## Ticket summary

Let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default (Mic Drop adoption foundation, [[INV-2026-10-05-micdrop-adoption-dossier]]). A stdlib-only downloader in the console writes `desktop/stt/` and `desktop/tts/` with resumable, SHA256-verified, atomically installed files; the shell reports what it can use and has loaded, picks input and output devices by name, swaps the speech model live without holding the engine lock, and offers a non-blocking mic test, a speaker tone and a per-request voice preview; Settings shows "(live)" / "(restart needed)" / "(next chat)" on every key. Scope: A1-A5, B1, B2, D4 (25 FRs, 73 ACs, 14 NFRs, 15 BRs). Out: engine binaries (Q1 resolved, D-3), sherpa-onnx, Kokoro, cloud engines, GPU select, wizard/doctor/tray submenus (T-034), endpointing and junk filter (T-032), quantised or multilingual models, a CLI downloader, mid-session mic-loss detection. Resolved by the user: Q1 models and voices only; Q2 keep all five voices and show each licence.

**Totals:** 9 phases, 39 tasks, **83.5 h** (PERT expected 82.9 h, range 58.5 to 105.2 h, confidence Low); envelope Development 132.4 h [92.9, 166.0] ([[T-031-effort-estimate]]; reconciled there). Critical path 35.0 h; plan is serial because there is one builder and the dirty shared files forbid parallel edits. Build protocol, evidence conventions and the shared-file rules are in [[T-031-plan]] and bind every task below: first action `PYTHONUTF8=1 python console/kanban.py ticket move T-031 in-progress`, `progress-tracker` after every task, no commit, push, stash or `git add`, no new dependency.

## Phase 1: Start and shell model path (8.5 h)

The riskiest design first. The shell holds `ENGINE` for up to 30 s while a model starts (`stt.rs:246`, `START_TIMEOUT` `:43`), and the single-threaded bridge calls `running()` and `loaded_model()` from `/listen/state` (`bridge.rs:415-416`). This phase fixes the stale-model bug, gives the engine slot a test seam, and makes the swap lock-free, proving the Windows cargo toolchain on the way.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 1a | 01 | in-progress, baselines | none (progress.md) | 0.5 | process |
| 1a | 02 | `engine_is_stale`, `model_file` fallback, warn once | `desktop/src-tauri/src/stt.rs` | 2 | AC-2 (RS), 35, 36 |
| 1b | 03 | `EngineSlot` with injectable spawner (no behaviour change) | `stt.rs` | 2 | enabler for AC-37..39 |
| 1b | 04 | **mutex-free live swap**, failed-model memory, `swap_error` | `stt.rs` | 3 | AC-37, 38, 39 |
| 1c | 05 | truthful `hint`, three wording tests in sync | `stt.rs`, `listen.rs` (test only) | 1 | AC-44 |

Requirements satisfied: FR-10, FR-11, FR-13; NFR-7. Components: R1.

## Phase 2: Asset engine, Python (20 h)

Pure stdlib, no shell needed. Catalog, then one-file transfer with Range and retry, then the integrity boundary, then jobs, inventory and delete. All network behaviour is tested against a local range-capable server with an injected sleep.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 2a | 06 | catalog + loader | `console/config/voice-assets.toml` (new), `console/server/voice_assets.py` (new), `console/tests/test_voice_assets_catalog.py` (new) | 3 | AC-1, 2, 3, 26 |
| 2b | 07 | transfer core, Range, 200/206/416, streaming | `voice_assets.py`, `console/tests/voice_assets_server.py` (new), `console/tests/test_voice_assets_transfer.py` (new) | 3 | AC-13, 15, 17, 25 |
| 2b | 08 | retry/backoff, URL policy | `voice_assets.py`, `voice_assets_server.py`, `test_voice_assets_transfer.py` | 3 | AC-14, 16, 31 |
| 2c | 09 | verify, atomic install, manifest last, disk/write errors | `voice_assets.py`, `voice_assets_server.py`, `console/tests/test_voice_assets_install.py` (new) | 3 | AC-21, 22, 23, 24, 30, 32 |
| 2d | 10 | job manager: pause/resume/cancel, progress, restart recovery | `voice_assets.py`, `console/tests/test_voice_assets_jobs.py` (new) | 3 | AC-9, 10, 11, 18, 19, 20 |
| 2e | 11 | inventory, custom rows, `in_use`/`loaded`, shell down | `voice_assets.py`, `console/server/native_bridge.py` (optional `timeout` only), `console/tests/test_voice_assets_inventory.py` (new) | 3 | AC-4, 5, 6, 7, 8, 22 (state), 72 |
| 2f | 12 | delete with refusals and confinement | `voice_assets.py`, `console/tests/test_voice_assets_delete.py` (new) | 2 | AC-27, 28, 29 |

Requirements satisfied: FR-1 to FR-8; NFR-1, 3, 4, 5, 6, 13. Components: K1, K3, S1, S2, S3.

## Phase 3: Console settings, routes, poke (5.5 h)

The console-side contract: two device keys and the `APPLIES` map, the asset routes with audit, and the best-effort poke that makes "(live)" true.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 3a | 13 | `input_device`/`output_device`, `APPLIES`, `applies` in settings GET | `console/server/assistant_config.py`, `console/server/features/assistant_feature.py` (`settings_get` return only), `console/config/assistant.toml`, `console/tests/test_assistant_commands.py` | 2 | AC-51, 67, 68, 70, 72 |
| 3b | 14 | asset routes + audit + pinned route-set test | `assistant_feature.py`, `voice_assets.py` (registry accessor), `console/tests/test_plugins.py`, `console/tests/test_voice_assets_routes.py` (new) | 2 | AC-12, 33; NFR-3, 4 |
| 3c | 15 | `settings_refresh` helper + call from `settings_post` | `native_bridge.py`, `assistant_feature.py` (`settings_post` only), `console/tests/test_settings_refresh.py` (new) | 1.5 | AC-41 |

Requirements satisfied: FR-8 (audit), FR-12 (console half), FR-17, FR-24 (server half). Components: S4, S5, K2.

## Phase 4: Devices, Rust (9.5 h)

One matcher and one resolver. `devices.rs` is the only file allowed to call `default_*_device()`; capture, playback and cues all go through it, and the open mic reopens when the preference changes.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 4a | 16 | enumerate, pure `pick_by_name`, `Prefs`, generation, `needs_reopen` | `desktop/src-tauri/src/devices.rs` (new), `main.rs` (one `mod` line) | 3 | AC-49 (RS), 52, 53, 56 (pure) |
| 4b | 17 | resolver + `Mic` remembers device and generation | `devices.rs`, `audio.rs` | 3 | AC-55, 57 |
| 4c | 18 | reopen in the take path and the armed loop | `listen.rs`, `hands_free.rs` | 2 | AC-56 |
| 4d | 19 | playback and cues use the resolver; source scan | `piper.rs`, `cue.rs`, `devices.rs` (scan test) | 1.5 | AC-54 |

Requirements satisfied: FR-16 (shell half), FR-18, FR-19. Components: R2.

## Phase 5: Refresh, preview, tests, bridge surface, Rust (12 h)

The shell grows the routes the console and UI need. Everything that could block returns at once because the bridge has one thread; routes are tested by real loopback requests against `bridge::start` on a temp repo root.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 5a | 20 | `POST /settings/refresh`, `apply_voice_settings`, pre-warm | `listen.rs`, `bridge.rs`, `stt.rs` (getter), `devices.rs` (getters if needed) | 3 | AC-42, 43 (E) |
| 5b | 21 | `/speak` `voice`/`rate_percent` overrides, `voice_in_use` | `tts.rs`, `piper.rs`, `bridge.rs` (`/speak` arm) | 1.5 | AC-47, 2 (RS) |
| 5c | 22 | mic test: `peak_of`, 2.0 s thread, guard | `desktop/src-tauri/src/voice_test.rs` (new), `main.rs` (one `mod` line), `audio.rs` (`set_level` visibility) | 3 | AC-60, 61 |
| 5d | 23 | speaker tone, fail-fast output, mute bypass | `voice_test.rs`, `cue.rs` | 1.5 | AC-64 |
| 5e | 24 | `/audio/devices`, `/audio/test/*`, `/listen/state` fields, caps; HL-gated swap test | `bridge.rs`, `listen.rs` (`#[cfg(test)]` setter only) | 3 | AC-49 (route), 61 (route), 39 (field), 40 (test) |

Requirements satisfied: FR-12 (shell half), FR-15 (shell half), FR-16, FR-21, FR-22. Components: R3, R4.

## Phase 6: Console routes for devices, tests, preview (3 h)

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 6a | 25 | helpers + routes: devices, mic/speaker test, preview; pass-through of `mic_test` | `native_bridge.py`, `assistant_feature.py`, `voice_assets.py` (helper), `console/tests/test_plugins.py`, `console/tests/test_voice_devices_routes.py` (new), `console/tests/test_native_bridge.py` | 3 | AC-46, 50, 62, 65 |

Requirements satisfied: FR-15, FR-16, FR-21, FR-22 (console halves). Component: S5.

## Phase 7: Settings UI (15 h)

All edits are surgical, inside `assistant()` of `console/static/settings.js` (lines ~952-1555) plus one appended block in `console/static/styles.css`; `app.js` and `index.html` are not touched and there is no new JS file. Each task snapshots the file to the scratchpad first, re-reads before every edit, and checks `git diff --no-index` shows only its own hunks. Chips come first because every later row calls the chip helper; `applies` is held in a closure variable because both `paint` call sites drop everything except `settings` and `backends`.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 7a | 26 | chips on every row bound to a key | `settings.js`, `styles.css` (appended block) | 1.5 | AC-69 |
| 7b | 27 | manager list, state, size, hint, licence, 1 s poll while active | `settings.js`, `styles.css` | 3 | NFR-6, 11 |
| 7c | 28 | actions, progress bar with ARIA, sentence errors | `settings.js`, `styles.css` | 3 | NFR-11 |
| 7d | 29 | `stt_model` picker over installed models | `settings.js` | 1.5 | AC-34 |
| 7e | 30 | voice picker, speed slider, Preview, OS-voice notice | `settings.js`, `styles.css` | 2 | AC-45 |
| 7f | 31 | device pickers, 3 s refresh while visible | `settings.js`, `styles.css` | 2 | AC-59 |
| 7g | 32 | Test microphone and Test speaker | `settings.js`, `styles.css` | 2 | AC-66 |

Requirements satisfied: FR-9, FR-14, FR-20, FR-23, FR-24 (UI half). Component: U1. UI criteria are manual (task 38); there is no JS test harness.

## Phase 8: Docs and compatibility (2.5 h)

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 8a | 33 | READMEs, `assistant.toml` comments, text and dependency checks | `console/README.md`, `desktop/README.md`, `console/config/assistant.toml` (comments), `console/tests/test_voice_docs.py` (new) | 2 | AC-71, 72, 73 |
| 8b | 34 | `get-whisper.ps1:103` one-line fix (user-instructed exception, D-18) | `desktop/get-whisper.ps1` (line 103 only) | 0.5 | FR-25 |

Requirements satisfied: FR-25; NFR-2, 12, 14. Component: D1.

## Phase 9: Verification (7.5 h)

Builder-run evidence only; the verifier stage (`challenge-implementation`, `verify`, `validate-artifacts`, `close-check`) follows separately.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 9a | 35 | full pytest, `desktop/tests`, `harness lint` | none | 1 | NFR-8 (Python) |
| 9b | 36 | full `cargo test` (single-threaded, then parallel), release build, deps unchanged | none | 1 | NFR-8 (Rust), AC-73 |
| 9c | 37 | **[HL]** headless run: manager end to end, AC-43, AC-40, devices, mic test, no audio file, no console window | none (scratch scripts only) | 3 | AC-40, 43, 49, 63 |
| 9d | 38 | **[UI]** manual browser checklist | none | 2 | AC-34, 45, 59, 66, 69 |
| 9e | 39 | **[HW]** hand-off list, not verified | `T-031-verification.md` (that table) | 0.5 | AC-48, 58, 59 (plug), mic bar, tone audibility |

## Reconciliation

| Level | Figure |
|-------|--------|
| Sum of the nine phase totals | 8.5 + 20.0 + 5.5 + 9.5 + 12.0 + 3.0 + 15.0 + 2.5 + 7.5 = **83.5 h** |
| [[T-031-task-breakdown]] effort summary | 83.5 h (same) |
| [[T-031-plan]] effort table | 83.5 h (same) |
| By layer | data 3.0 + service 55.0 + UI 15.0 + docs/process 3.5 + E2E 7.0 = 83.5 h |

All 73 ACs, 25 FRs, 14 NFRs and 15 BRs are mapped in [[T-031-plan]] § Acceptance criterion coverage. [HW] items are tracked in task 39 as "not verified on hardware".

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-progress]] · [[T-031-verification]] · [[T-031-release]]
