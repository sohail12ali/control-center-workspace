---
ticket: "T-031"
artifact: components
---

# Components: T-031

Tracks every component this ticket touches, its dependencies, and its build status. Layers are renamed to what this project has: **Data/config**, **Console service (Python)**, **Shell service (Rust)**, **UI**, **Docs and verification**.

**Produced by:** `analyze-components` (graph built in the same pass). **Consumed by:** `breakdown-tasks`. **Sources:** [[T-031-requirements]] (25 FRs, 73 ACs), [[T-031-decision-log]], [[T-031-analysis]].

**Count note:** 15 components, above the skill's 5-12 guide. Kept because the frozen scope spans a Python console, a Rust shell and a vanilla-JS UI, and merging components would break "one component per task". Scope is frozen and user-approved, so there is no scope-reduction conversation to have; flagged here instead.

Task ids are in [[T-031-plan]] (`T-031-NN`); this file refers to them as `NN`.

---

## Data / config layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| K1 Voice-asset catalog | `console/config/voice-assets.toml` (new, committed; `tomlio` subset: `[[model]]` + `[[model.file]]`) | 4 STT models + 5 voices: pinned https URL, size, sha256, `hash_source`, hint, licence | none (values from D-2, D-12, D-13) | 2a | FR-1; AC-1, 2, 3, 26 | done (task 06, 2026-10-05; 4 models + 5 voices, 14 files; [[T-031-progress]]) |
| K2 Assistant keys on disk | `console/config/assistant.toml` | committed defaults `input_device = ""`, `output_device = ""`; comments updated | S4 | 3a, 8a | FR-17, FR-25; AC-51, 71 | done (task 13: `input_device` and `output_device` defaults in `assistant.toml`; task 33 comments) |
| K3 On-disk asset contract | `desktop/stt/ggml-{name}.bin`, `desktop/tts/{voice}.onnx` + `.onnx.json`, `*.part`, `*.manifest.json` (gitignored dirs; no code) | the one contract the console writes and the shell reads; the shell ignores `.part`/`.manifest.json` by extension | S1, S2 write; R1 and `piper.rs` read | 2b-2d | FR-2, 6; AC-2, 5, 22, 72; BR-2 | done (tasks 02, 06, 09, 21: filename contract pinned on both sides; AC-2) |

## Console service layer (Python, stdlib only)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| S1 Transfer engine | `console/server/voice_assets.py` (new) | one-file transfer: `.part` + Range, 200/206/416, retry/backoff, https-only redirects, host policy, no credentials, streaming | K1 | 2b | FR-4, FR-8; AC-13..17, 25, 31 | done (tasks 07, 08; `test_voice_assets_transfer.py`) |
| S2 Verify and atomic install | `voice_assets.py` | size + SHA256 of whole `.part`, `os.replace`, manifest last, voice two-file order, free-space check, write-error handling, Verify action | S1, K1 | 2c | FR-6, FR-8; AC-21..24, 30, 32; NFR-1 | done (task 09; `test_voice_assets_install.py`) |
| S3 Jobs, inventory, delete | `voice_assets.py` | per-id background job (pause/resume/cancel, progress), inventory with custom rows and `in_use`/`loaded`, delete with refusals and name validation | S1, S2, S4 (reads settings), S5 `native_bridge.capabilities` | 2d-2f | FR-2, 3, 5, 7; AC-4..12, 18..20, 27..29; NFR-4, 6 | done (tasks 10-12; `test_voice_assets_jobs.py`, `_inventory.py`, `_delete.py`) |
| S4 Settings schema and `APPLIES` | `console/server/assistant_config.py` | `input_device`/`output_device` in `DEFAULTS`/`WRITABLE` + validation; `APPLIES` map; settings GET returns `applies` | K2 | 3a | FR-17, FR-24; AC-51, 67, 68, 70, 72 | done (task 13, 2026-10-05: `assistant_config.py`, `assistant_feature.settings_get`, `assistant.toml` keys; 35 tests in `test_assistant_commands.py`) |
| S5 Console routes and shell client | `console/server/features/assistant_feature.py`, `console/server/native_bridge.py`, `console/tests/test_plugins.py` (pinned route set) | asset routes + audit; settings-refresh poke; devices/tests/preview routes; thin shell helpers | S3, S4, R4 (contract) | 3b, 3c, 6a | FR-8, 12, 15, 16, 21, 22; AC-12, 33, 41, 46, 50, 62, 65 | done (tasks 14, 15, 25; `test_voice_assets_routes.py`, `test_settings_refresh.py`, `test_voice_devices_routes.py`, `test_plugins.py`) |

## Shell service layer (Rust, `desktop/src-tauri/src/`)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| R1 STT model lifecycle | `stt.rs` | pure `engine_is_stale`; `model_file` preferred/fallback + warn-once; engine slot behind an injectable spawner; mutex-free live swap with an in-flight `Lease` so the old engine is never killed mid-inference (CR-36); failed-model memory + `swap_error`; truthful `hint` | none (K3 contract) | 1a-1c | FR-10, 11, 13; AC-2 (RS), 35..39, 44; NFR-7 | done 2026-10-05 (tasks 02-05; `desktop/src-tauri/src/stt.rs`, `listen.rs` test assertion; cargo 215 passed, 0 failed; [[T-031-progress]]) |
| R2 Device layer | `devices.rs` (new), `audio.rs`, `listen.rs`, `hands_free.rs`, `piper.rs`, `cue.rs`, `main.rs` (`mod` line only) | enumerate by name; one `pick_by_name`; preference + generation; one resolver (the only `default_*_device()` call site); `Mic` remembers device and generation; reopen loops; playback and cues use the resolver | none (cpal 0.16 already present) | 4a-4d | FR-16 (shell half), 18, 19; AC-49, 52..57 | done (tasks 16-19, 2026-10-05: `devices.rs` new, `audio.rs`, `listen.rs`, `hands_free.rs`, `piper.rs`, `cue.rs`, `main.rs`; 32 new tests, cargo 252 passed; real input switch and audibility on a second output are [HW], not verified) |
| R3 Preview and tests | `tts.rs`, `piper.rs` (voice/rate override, filename contract), `voice_test.rs` (new: `peak_of`, mic test state, tone), `cue.rs` (renderer reuse) | `/speak` overrides resolver; non-blocking 2 s mic test; speaker tone | R2 | 5b-5d | FR-15, 21, 22; AC-2 (RS), 47, 60, 61, 64 | done (tasks 21-23; `voice_test.rs`, `tts.rs`, `piper.rs`; tone audibility and bar-follows-voice are [HW], not verified) |
| R4 Bridge surface | `bridge.rs`, `listen.rs` (`apply_voice_settings`), `console_settings.rs` (existing `forget`) | `POST /settings/refresh` (async re-apply), `GET /audio/devices`, `POST /audio/test/{mic,speaker}`, `/speak` overrides, caps, `/listen/state` fields `mic_test`, `swap_error` | R1, R2, R3 | 5a, 5e | FR-12, 15, 16, 21, 22; AC-39 (field), 42, 49, 61 | done (tasks 20, 21, 24; `bridge.rs`; AC-43, 49, 63 observed on the real shell, T-031-37) |

## UI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| U1 Settings Assistant UI | `console/static/settings.js` `assistant()` (lines ~952-1555 only), appended block in `console/static/styles.css` | chips from `applies`; model manager; installed-model picker; voice picker + slider + preview; device pickers; test controls | S3/S5 routes (S4 `applies`) | 7a-7g | FR-9, 14, 20, 23, 24; AC-34, 45, 59, 66, 69; NFR-6, 11 | done (tasks 26-32; `settings.js`, `styles.css`); 24 of 33 [UI] items observed in a browser, 9 open (T-031-38, D-21) |

## Docs and verification

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| D1 Docs and compat | `console/README.md`, `desktop/README.md`, `console/config/assistant.toml` comments, Settings help strings, `desktop/get-whisper.ps1:103` (one line) | the manager is documented; scripts stay and are recognised; stale `desktop-listen-state` cite fixed | all behaviour tasks | 8a-8b | FR-25; AC-71, 72, 73; NFR-12, 14 | done (tasks 33, 34; `test_voice_docs.py`) |
| Q1 Verification | full pytest, `cargo test`, headless run, UI checklist, [HW] list | cross-cutting evidence; no new product code | everything | 9a-9e | AC-40, 43, 49 (HL), 63; AC-34, 45, 59, 66, 69 (manual); AC-48, 58 ([HW]); NFR-7..9 | partial: pytest, cargo, [HL] done (35-37); [UI] 9 items open (38); [HW] 8 rows NOT verified (39) |

---

## Dependency graph

Edge = "depends on". Task ids in brackets.

```
Q1 Verification [35-39]
 +- U1 Settings UI [26-32]
 |    +- S5 routes + client [14, 15, 25]
 |    |    +- S3 jobs/inventory/delete [10, 11, 12]
 |    |    |    +- S2 verify/install [09]
 |    |    |    |    +- S1 transfer engine [07, 08]
 |    |    |    |         +- K1 catalog [06]
 |    |    |    +- S4 settings + APPLIES [13] -- K2 assistant.toml keys
 |    |    +- R4 bridge surface [20, 21, 24]          (contract: /audio/*, /settings/refresh, /speak overrides)
 |    |         +- R1 STT lifecycle [02, 03, 04, 05]
 |    |         +- R3 preview + tests [21, 22, 23]
 |    |         |    +- R2 device layer [16, 17, 18, 19]
 |    +- S4 `applies` [13]
 +- D1 docs/compat [33, 34]   (after behaviour tasks, so text describes what exists)
K3 on-disk contract: written by S1/S2, read by R1 (`ggml-*.bin`) and `piper.rs` (`*.onnx`); pinned by tests on both sides [02, 21, 06/09]
```

**Classification**
- Roots (no dependencies): K1, R1, R2, S4 (K2 rides with it)
- Middle: S1, S2, S3, S5, R3, R4, U1
- Leaves (nothing depends on them): U1, D1, Q1
- Isolated components: none
- Circular dependencies: **none**. One near-cycle is deliberate: S5 (console) calls R4 routes and R4's refresh handler calls back to the console settings GET; the contract is HTTP both ways and the two sides are built in separate tasks (15 console helper, 20 shell route), so there is no build-order cycle. Runtime consequence handled in plan (async re-apply, task 20).
- Undeclared dependency found and fixed during analysis: the settings-refresh re-apply (R4) re-applies **device** preferences, so it depends on R2's preference/generation API. The suggested order put refresh before devices; it is moved after R2 core (task 16).

## Critical path and bottlenecks

- **Critical path (by dependency, effort-weighted):** 01 → 06 → 07 → 08 → 09 → 10 → 11 → 12 → 14 → 27 → 28 → 33 → 35 → 37 → 39 = **35.0 h** (the asset engine into the manager UI into the headless proof). The Rust chain 01 → 16 → 17 → 22 → 24 → 25 → 33 → 36 → 37 is 28.5 h; the swap chain 01 → 02 → 03 → 04 → 20 → 24 is 14.5 h before it joins.
- **Parallelizable (if more than one builder ever exists):** the Python asset chain (06-12, 14) is independent of the Rust chain (02-05, 16-24); settings keys (13) and the poke helper (15) are independent of both. Today there is one builder, so the plan is serial (83.5 h) and ordered to put the riskiest work first.
- **Bottleneck components (most depended on):** R2 device layer (R3, R4, S5, U1 all consume it), R4 bridge surface (S5, U1), S3 (S5, U1). All three are scheduled before their consumers.
- **Shared-file bottlenecks (merge risk, not dependency):** `bridge.rs` (tasks 20, 21, 24), `stt.rs` (02-05), `settings.js` (26-32), `assistant_feature.py` + `test_plugins.py` (14, 25). Serial edits, re-read before each, no parallel builders on these files.

## Suggested build order (reasoned, differs from the brief's list in two places)

1. **Phase 1, 01-05: start + shell model path.** Moved first: it is the riskiest design (engine mutex, injected spawner), the user-mandated item, isolated to `stt.rs`, and its first `cargo test` run surfaces any Windows toolchain problem before 80 hours depend on it.
2. **Phase 2, 06-12: asset engine (Python).** Pure stdlib, no cargo; catalog → transfer → retry/policy → install → jobs → inventory → delete.
3. **Phase 3, 13-15: settings keys + `APPLIES`, asset routes, refresh poke helper.**
4. **Phase 4, 16-19: devices.** Pure core, resolver + capture, reopen loops, playback.
5. **Phase 5, 20-24: refresh route (needs 04 and 16), `/speak` overrides, mic test, speaker tone, bridge routes/caps.**
6. **Phase 6, 25: console devices/tests/preview routes.**
7. **Phase 7, 26-32: UI** (chips first, because every later row calls the chip helper).
8. **Phase 8, 33-34: docs/compat and the one-line `.ps1` fix.**
9. **Phase 9, 35-39: verification.**

Deviations from the brief's order: (a) swap work first (above); (b) refresh route after the device core (undeclared dependency above).

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data / config | 3 | 0 | 0 | 3 |
| Console service | 5 | 0 | 0 | 5 |
| Shell service | 4 | 0 | 0 | 4 |
| UI | 1 | 0 | 0 | 1 (9 of 33 [UI] checks open, T-031-38) |
| Docs and verification | 2 | 0 | 1 (Q1: [UI] 9 items, [HW] 8 rows open) | 1 |
| **Total** | **15** | **0** | **1** | **14** |

*Reconciled by the verifier 2026-10-05 against [[T-031-progress]] and the plan headings (38 of 39 `[x]`).*

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-progress]] · [[T-031-verification]] · [[T-031-release]]
