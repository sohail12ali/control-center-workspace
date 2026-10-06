---
ticket: "T-031"
artifact: task-breakdown
---

# Task breakdown: T-031

Atomic tasks per slice. **Task id convention (deviation from the template, on purpose):** the id column is the plan's `T-031-NN`, not `{phase}-{slice}-{task}`. `console context` and `progress-tracker` parse `T-031-NN` from [[T-031-plan]]; a second id for the same task would be two names for one fact. Phase and slice are the section headings (`1a`, `2b`, ...), and component ids (`K1`, `S1`, `R1`, `U1`, ...) are from [[T-031-components]].

**Canonical home of the full Done-criteria, files-allowed lists, evidence commands and "Split because" reasons is [[T-031-plan]]** (one fact, one file). The rows below carry the short form: what, component, ACs, the observable result, effort, dependencies.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis), `estimate(mode=forecast)`, `progress-tracker` (patches the Status and actual-effort cells).

Effort buckets are the skill's 0.5 / 1 / 1.5 / 2 / 3 h. A task that will not fit its bucket is stopped and sent to `replan`, never stretched.

---

## Phase 1: Start and shell model path

### Slice 1a: `ensure()` model-compare fix

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-01 | Step zero: `ticket move T-031 in-progress`; record pytest/cargo baselines | Q1 | process (summary Status; risk R-1, R-2) | ticket lane is `in-progress`; baseline counts and pre-existing failures written to progress.md | 0.5 | done | first task; blocks all. Done 2026-10-05: actual about 0.15 h; pytest 1 failed (`test_stylesheet.py::test_every_class_the_js_styles_actually_exists`, other ticket's `.ob-count`) / 2302 passed; cargo 181 passed, 0 failed, 0 ignored; see [[T-031-progress]] |
| T-031-02 | `stt.rs`: pure `engine_is_stale` over (model file, prompt); `model_file` preferred/smallest fallback; fallback warning once per distinct pair; pin `ggml-{name}.bin` | R1 | FR-10; AC-35, 36, 2 (RS half) | table test incl. regression row (running base.en, wanted tiny.en, same prompt, stale); warn-once test | 2 | done | depends on 01. Done 2026-10-05: actual about 0.5 h; `cargo test stt:: -- --test-threads=1` 21 passed (12 + 9 new), full suite 190 passed, 0 failed; see [[T-031-progress]] |

### Slice 1b: engine slot seam and mutex-free live swap (MANDATORY)

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-03 | `stt.rs`: `ENGINE` static becomes an `EngineSlot` instance with an injectable spawner and readiness check; behaviour preserved | R1 | FR-11 (enabler); AC-37..39 (enabler) | all existing `stt` tests green; fixture transcription unchanged; slot is constructible in tests | 2 | done | depends on 02; same file. Done 2026-10-05: actual about 0.75 h; `cargo test stt:: -- --test-threads=1` 26 passed (21 + 5 new), fixture transcription still real (`stt: model=ggml-base.en.bin heard "Status ticket too"`), full suite 195 passed, 0 failed; see [[T-031-progress]] |
| T-031-04 | `stt.rs`: start the replacement outside the lock, publish under a short lock, old keeps serving and is killed only when no in-flight take still holds a lease on it (CR-36), failed model not retried until the preference changes, `swap_error` accessor | R1 | FR-11; AC-37, 38, 39; NFR-7 | `cargo test` proves a concurrent `loaded_model()`/`running()` returns in under 100 ms while a stubbed start is blocked; a leased old engine survives the swap until released | 3 | done | depends on 03; its own task and test by user instruction. Done 2026-10-05: actual about 1.5 h; `cargo test stt:: -- --test-threads=1` 41 passed, the same without the flag 41 passed, full suite 210 passed, 0 failed (16 new swap tests, AC-38 proof fails under a lock-holding mutation); see [[T-031-progress]] |

### Slice 1c: truthful hint

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-05 | `stt::hint` names only things that exist; non-Windows points at Settings and says the engine is installed separately; keep the two wording tests in sync | R1 | FR-13; AC-44 | hint contains "Settings"; every `get-*` path it names exists; `stt.rs:511` and `listen.rs:366` tests green | 1 | done | depends on 04 (same file). Done 2026-10-05: actual about 0.5 h; `cargo test -- stt:: listen:: hands_free:: --test-threads=1` 60 passed, full suite 215 passed, 0 failed (5 new hint tests, both pinned wording tests updated per OS); see [[T-031-progress]] |

## Phase 2: Asset engine (Python)

### Slice 2a: catalog

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-06 | `voice-assets.toml` (4 models, 5 voices) in the `tomlio` subset + catalog loader + catalog tests | K1 | FR-1; AC-1, 2 (PY half), 3, 26 | every file pinned, hashed, sized; catalog hashes equal local legacy files when present | 3 | done (actual ~0.5 h; 23 passed + 1 opt-in online, ran) | depends on 01; values from D-2/D-12/D-13 |

### Slice 2b: transfer

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-07 | `voice_assets.py` transfer core: `.part` + Range, 206 append / 200 restart / 416, size and `Content-Range` mismatch, 1 MiB streaming; local range-capable test server | S1 | FR-4; AC-13, 15, 17, 25 | byte-identical result; 32 MiB under 8 MiB Python allocations | 3 | done (actual ~0.6 h; 14 transfer tests pass) | depends on 06 |
| T-031-08 | Retry and backoff (6 consecutive failures, 0.5 x 2^min(n,5), reset on bytes; transport/429/5xx retry, other 4xx fail) and URL policy (https only, host `huggingface.co`, https-only redirects, no `Authorization`) | S1 | FR-4, FR-8; AC-14, 16, 31 | delays 0.5, 1, 2, 4, 8, 16, 16 via injected sleep; 404 immediate; policy rejections | 3 | done (actual ~0.7 h; 28 new tests, 42 in file) | depends on 07 |

### Slice 2c: verify and atomic install

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-09 | Whole-`.part` size + SHA256, `os.replace`, manifest last, voice `.onnx.json` before `.onnx`, mismatch handling, free-space check, write-error handling, Verify action | S2 | FR-6, FR-8; AC-21, 22, 23, 24, 30, 32; NFR-1 | final name never exists for unverified bytes across a four-point fault matrix | 3 | done (actual ~0.6 h; 17 install tests pass) | depends on 08 |

### Slice 2d: jobs

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-10 | Per-id background job: download, pause, resume, cancel, progress fields and 500 ms cadence, same-job on second click, restart derives `partial` from `.part`, per-job console log | S3 | FR-3, FR-5; AC-9, 10, 11, 18, 19, 20; NFR-6, 13 | states downloading to verifying to installed; cancel ends the thread and removes `.part` | 3 | done (actual ~0.8 h; 18 job tests pass) | depends on 09 |

### Slice 2e: inventory

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-11 | Inventory and state: scan both dirs, catalog + custom rows, `verified`, `in_use`, `loaded` from shell caps, `free_bytes`, shell down handled, no outbound call | S3 | FR-2; AC-4, 5, 6, 7, 8, 72 (files half); NFR-12 | script-placed files read installed/unverified; shell down gives 200 with `shell.reachable:false` | 3 | done (actual ~0.6 h; 19 inventory tests pass) | depends on 10 |

### Slice 2f: delete

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-12 | Delete with refusals (in use, loaded, downloading), OS-lock sentence, name validation and confinement | S3 | FR-7; AC-27, 28, 29; NFR-3 | traversal rejected; nothing half-deleted; no 5xx | 2 | done (actual ~0.4 h; 30 delete tests pass) | depends on 11 |

## Phase 3: Console settings, routes, poke

### Slice 3a: settings keys and `APPLIES`

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-13 | `input_device`/`output_device` in `DEFAULTS`/`WRITABLE` + validation + `assistant.toml` keys; `APPLIES` map; settings GET returns `applies`; source-scan test | S4, K2 | FR-17, FR-24; AC-51, 67, 68, 70, 72 (keys half) | a new `WRITABLE` key without an `APPLIES` entry fails a test | 2 | done (actual ~0.4 h; 35 new tests pass, 228 in the two assistant files) | depends on 01 |

### Slice 3b: asset routes

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-14 | Asset routes (assets, download, pause, resume, cancel, delete, verify) with audit and body-field rejection; pinned route-set test updated; responsiveness test | S5 | FR-8; AC-12, 33; NFR-3, 4 | one `audit.record` per action; p95 under 250 ms over 50 calls with two active downloads and a stubbed shell | 2 | done (actual ~0.8 h; 39 new tests pass; p95 ~3 ms measured) | depends on 12, 13 |

### Slice 3c: refresh poke

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-15 | `native_bridge.settings_refresh` helper (timeout <= 1 s) + best-effort call from `settings_post` | S5 | FR-12; AC-41 | settings write succeeds when the shell is down; helper called once per write | 1.5 | done (actual ~0.3 h; 22 new tests pass, 111 with the bridge and assistant files) | depends on 01 |

## Phase 4: Devices (Rust)

### Slice 4a: pure device core

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-16 | New `devices.rs`: `enumerate()` by direction without panic, pure `pick_by_name`, preference statics, generation counter, `needs_reopen`; `mod devices;` in `main.rs` | R2 | FR-16 (shell half), FR-18; AC-49 (RS), 52, 53, 56 (pure half) | table test for exact / unique substring / ambiguous / empty / non-ASCII / identical names; never returns a device lacking the direction | 3 | done (actual ~0.8 h; 14 new tests, devices:: 14 passed, full 234 passed) | depends on 01 |

### Slice 4b: resolver and capture

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-17 | `resolve_input()`/`resolve_output()` (unresolved falls back to default, one warning per change, `fallback` flag); `audio.rs` `Mic::open`, `available`, `device_name` use it; `Mic` remembers device name and generation; open log names the device; enumeration cached about 1 s so the 2 Hz voice panel does not enumerate twice per poll (CR-37) | R2 | FR-19; AC-55, 57 | fallback test; open-failure text still contains "microphone"; cache TTL test | 3 | done (actual ~1 h; 11 new tests, devices:: 22 + audio:: 33 passed, full 245 passed; hardware-gated test ran here) | depends on 16 |

### Slice 4c: reopen loops

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-18 | `listen.rs` take path and `hands_free.rs` armed loop reopen the mic when the generation changed and reset their cursor/spotter; `hands_free.rs:382` contract kept | R2 | FR-19; AC-56 (loops) | pure decision fn tested; generation bumps only on change | 2 | done (actual ~1 h; 5 new tests, listen:: 7 + hands_free:: 12 + devices:: 22 passed, full single-threaded 250 passed; parallel run fails 4 stt tests from machine load, see progress.md) | depends on 17 |

### Slice 4d: playback

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-19 | `piper.rs` `play()` and `cue.rs` `blow()` use `resolve_output()`; source-scan test that no `default_*_device()` call remains outside `devices.rs` | R2 | FR-19; AC-54 | scan finds zero call sites outside the resolver (example exempt) | 1.5 | done (actual ~0.7 h; 2 new tests, devices:: 24 passed; grep lists only devices.rs:111-112; full 252 passed single-threaded and parallel) | depends on 17 |

## Phase 5: Refresh, preview, tests, bridge surface (Rust)

### Slice 5a: settings refresh

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-20 | `POST /settings/refresh` (authenticated, returns at once, re-apply on a short thread); pure `apply_voice_settings` in `listen.rs` (also used per take); starts a needed replacement in the background | R4 | FR-12; AC-42 | loopback test: 401 without the token, 200 with it; device generation bumps only on change | 3 | done (actual ~1 h; 13 new tests: listen:: 16 passed, bridge:: 11 passed, devices:: 24 passed; full 265 passed single-threaded and parallel; mutation check: a synchronous refresh fails both bridge timing tests) | depends on 04, 16 |

### Slice 5b: `/speak` overrides

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-21 | Pure `speak_params` resolver; `/speak` accepts optional `voice`, `rate_percent`; pin `{voice}.onnx` + `.onnx.json` contract | R3 | FR-15 (shell half); AC-47, 2 (RS half) | overrides win, absent uses settings, unknown voice falls back like `piper::voice` | 1.5 | done (actual ~0.5 h; 11 new tests: tts:: 11 passed, piper:: 8 passed, bridge:: 12 passed; full 276 passed single-threaded and parallel) | depends on 20 (same file `bridge.rs`) |

### Slice 5c: mic test

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-22 | New `voice_test.rs`: `peak_of(&[i16])`, 2.0 s mic test on its own thread with a fresh `Mic` on the resolved input, state `{running, peak, device}`, guard refuses while a take or hands-free is active, drives `audio::level()`, keeps no audio | R3 | FR-21; AC-60, 61; NFR-10 | `peak_of` cases; guard test; test thread joins within 3 s | 3 | done (actual ~0.5 h; 8 new tests: voice_test:: 8 passed, audio:: 33 passed; hardware-gated test RAN on the real mic) | depends on 17 |

### Slice 5d: speaker tone

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-23 | Two-note tone renderer (finite, peak <= 0.25, soft edges, 400-800 ms); resolve output synchronously (fail fast with reason), play on a thread, bypass the reply-mute switch | R3 | FR-22; AC-64 | renderer property tests; unresolved output returns a reason | 1.5 | done (actual ~0.3 h; 4 new tests: voice_test:: 12 passed, cue:: 5 passed; audibility is [HW], not verified) | depends on 19, 22 |

### Slice 5e: bridge routes and caps

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-24 | `GET /audio/devices` (names, OS defaults, applied-preference verdict), `POST /audio/test/mic` (409 when busy), `POST /audio/test/speaker`, `/listen/state` fields `mic_test` and `swap_error`, caps for resolved voice and loaded model | R4 | FR-16, 21, 22; AC-49 (route half), 61 (route), 39 (field) | loopback tests: shapes, auth, 409, no panic with zero devices | 3 | done (actual ~0.7 h; 8 new tests: bridge:: 20 passed; full 297 passed single-threaded and parallel; HL swap test skipped: tiny.en not installed) | depends on 04, 16, 21, 22, 23 |

## Phase 6: Console routes for devices, tests, preview

### Slice 6a

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-25 | `native_bridge` helpers + routes `GET voice/devices` (adds `configured`), `POST voice/test/mic`, `POST voice/test/speaker`, `POST voice/preview` (validation, no settings written); `mic_test` visible in `GET /api/assistant/voice`; pinned route-set test updated | S5 | FR-15, 16, 21, 22; AC-46, 50, 62, 65 | fake-bridge tests: validation 400s, forwarding with overrides, shell-down `ok:false` | 3 | done (actual ~0.6 h, untimed estimate; 32 new tests: 27 in test_voice_devices_routes.py, 5 in test_native_bridge.py; 5-file run 182 passed) | depends on 24, 15 |

## Phase 7: Settings UI (`settings.js` `assistant()` only; shared dirty files)

All Phase 7 tasks: surgical in-place edits, pre-edit snapshot to the scratchpad, post-edit `git diff --no-index` showing only T-031 hunks, CSS only as an appended block. No new JS file (so `index.html` is untouched).

### Slice 7a: chips

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-26 | `chip(key)` helper reading `applies` from the settings response; every Assistant row (`toggle`/`field`/`choice` and later rows) shows "(live)", "(restart needed)" or "(next chat)" with the note as tooltip | U1 | FR-24; AC-69 [UI] | UI keeps no list of its own; manual check (task 38) | 1.5 | done (actual ~1 h; node --check 0; 20 chips seen in headless Chrome; UI-69a..c unticked for task 38) | depends on 13 |

### Slice 7b-7c: model manager

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-27 | Manager list: catalog + custom rows with state chips, size, hint, licence (ryan labelled CC BY-NC-SA 4.0 non-commercial), in-use marker, free space; 1 s poll only while a job is active | U1 | FR-2/3 (UI side); NFR-6, 11 | manual check (task 38); no polling when idle | 3 | done (actual ~1.5 h + harness trouble; node --check 0; 9 rows listed, poll ~1/s only while a job runs, flat when idle; UI-27a..e unticked for task 38) | depends on 14, 26 |
| T-031-28 | Manager actions: Download, Pause, Resume, Cancel, Delete, Verify; progress bar with `role="progressbar"` and `aria-valuenow`; sentence errors | U1 | FR-3, 5, 6, 7 (UI side); NFR-11 | manual check (task 38) | 3 | done (actual ~1.5 h; node --check 0; actions/ARIA bar/sentences seen in headless Chrome against a stand-in server, not a real download; UI-28a..f unticked for task 38) | depends on 27 |

### Slice 7d: installed-model picker

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-29 | `stt_model` becomes a dropdown of installed models with size and in-use marker; a missing configured name shows "(not installed)"; saves with the "Saved" toast and "(live)" chip; hint text no longer says "run get-whisper.ps1" only | U1 | FR-9; AC-34 [UI] | manual check (task 38) | 1.5 | done (actual ~0.5 h; node --check 0; picker seen in headless Chrome, stubbed for the not-installed case; UI-34a..d unticked for task 38) | depends on 14, 26, 27 |

### Slice 7e: voice

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-30 | Voice dropdown (first option "Automatic - first installed"), speed slider 50-200 bound to `speak_rate_percent`, Preview button, OS-voice notice and disabled state when the backend is not piper | U1 | FR-14, FR-15 (UI side); AC-45 [UI] | manual check (task 38) | 2 | done (actual ~0.7 h; node --check 0; seen in headless Chrome with stubbed assets/preview; UI-45a..e unticked for task 38) | depends on 25, 26, 27 |

### Slice 7f: device pickers

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-31 | Input/output pickers: "System default (name)" first, "NAME (not connected)" plus the device in use, 3 s re-enumerate only while visible, Refresh button, console verdict shown, disabled with reason when the shell is down | U1 | FR-20; AC-59 [UI] | manual check (task 38); real plug/unplug is [HW] | 2 | done (actual ~1 h; node --check 0; seen in headless Chrome with stubbed devices; UI-59a..e unticked for task 38) | depends on 25, 26 |

### Slice 7g: test controls

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-32 | "Test microphone" (button, level bar, peak, device) and "Test speaker"; buttons disabled while running; 409 and unresolved-device errors as sentences | U1 | FR-23; AC-66 [UI] | manual check (task 38) | 2 | done (actual ~0.8 h; node --check 0; seen in headless Chrome with stubbed test routes; UI-66a..e unticked for task 38) | depends on 25, 31 |

## Phase 8: Docs and compatibility

### Slice 8a

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-33 | README (console, desktop), `assistant.toml` comments, Settings help strings describe the manager; text-check test; deps-unchanged test | D1 | FR-25; AC-71, 72, 73; NFR-2, 12, 14 | text-check and deps tests pass; `Cargo.toml` `[dependencies]` and `requirements-dev.txt` unchanged | 2 | done 2026-10-05 | depends on 14, 25, 29, 30, 32 |

### Slice 8b

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|-------------|-----------|----------------|---------------------|-----------:|--------|-------|
| T-031-34 | `desktop/get-whisper.ps1:103` one-line text fix: stale `desktop-listen-state` cite. Exception to the requirements' "no changes to the two .ps1 scripts", by explicit user instruction, limited to that line | D1 | FR-25 (user instruction) | `git diff` shows one line changed; no `desktop-listen-state` anywhere outside artifacts; script still parses | 0.5 | done (actual ~0.2 h; 1 insertion/1 deletion, parser 0 errors, grep clean; whole-file "no byte above 127" does not hold: pre-existing em dash at line 26, see progress.md) | depends on 01 |

## Phase 9: Verification (builder-run, evidence-only)

| Task ID | Description | Slice | Component | Requirement/AC | Effort (h) | Status | Notes |
|---------|-------------|-------|-----------|----------------|-----------:|--------|-------|
| T-031-35 | Full pytest (`PYTHONUTF8=1`, `-o addopts=""`) | 9a | Q1 | NFR-8 (Python half); all [PY] ACs | 1 | done 2026-10-05: `1 failed, 2876 passed, 1 skipped` (only the other ticket's `.ob-count`); re-run by the verifier, same numbers | after every Python-touching task (06-15, 25, 33) and 34 |
| T-031-36 | `cargo test` single-threaded first, then default; `cargo build` | 9b | Q1 | NFR-8 (Rust half); all [RS] ACs | 1 | done 2026-10-05: `cargo test` 310 passed, 0 failed (single-threaded and parallel x2); re-run by the verifier, same numbers | after every Rust-touching task (02-05, 16-24) and 33 |
| T-031-37 | Headless run of the real shell and console: tiny.en via the manager, live swap, `/health`, devices, mic test | 9c | Q1 | AC-40, 43, 49 (HL), 63; NFR-7, 10 | 3 | done 2026-10-05: AC-40 swap 1.0166 s, AC-43 0.02-0.28 s, AC-49 ok, AC-63 2.7-3.3 s (bound amended to 5 s, D-20) | after 35, 36 |
| T-031-38 | UI manual checklist in a browser (or recorded as not run) | 9d | Q1 | AC-34, 45, 59, 66, 69 [UI]; NFR-6, 11 | 2 | PARTIAL (D-21): 24 of 33 [UI] items observed in a browser, 9 open (UI-28d/e/f, UI-45d, UI-59e wording, UI-66b-e, UI-27a); plan heading stays `[ ]` | after 32, 37 |
| T-031-39 | [HW] hand-off list written into `T-031-verification.md`, status "not verified on hardware" | 9e | Q1 | AC-48, 58, 59 (plug/unplug), mic-bar-tracks-voice, tone audibility; NFR-9 | 0.5 | done 2026-10-05: HW-1..HW-8 written, none verified on hardware | after 38; documents, never claims |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1: Start and shell model path (01-05) | 8.5 | 0 | 0 | 8.5 | 0% |
| Phase 2: Asset engine (06-12) | 20.0 | 0 | 0 | 20.0 | 0% |
| Phase 3: Console settings, routes, poke (13-15) | 5.5 | 0 | 0 | 5.5 | 0% |
| Phase 4: Devices (16-19) | 9.5 | 0 | 0 | 9.5 | 0% |
| Phase 5: Refresh, preview, tests, bridge (20-24) | 12.0 | 0 | 0 | 12.0 | 0% |
| Phase 6: Console routes for devices/tests/preview (25) | 3.0 | 0 | 0 | 3.0 | 0% |
| Phase 7: Settings UI (26-32) | 15.0 | 0 | 0 | 15.0 | 0% |
| Phase 8: Docs and compat (33-34) | 2.5 | 0 | 0 | 2.5 | 0% |
| Phase 9: Verification (35-39) | 7.5 | 0 | 0 | 7.5 | 0% |
| **Total (39 tasks)** | **83.5** | 0 | 0 | **83.5** | 0% |

*Verifier note (2026-10-05): the per-phase Completed/Remaining columns above were never maintained by `progress-tracker` and still read 0 h; the actuals are in the per-task entries of [[T-031-progress]] (a forecast should be rebuilt from those, not from this table).*

By layer for `estimate(mode=forecast)`: data 3.0 (06) · service 55.0 (02-05, 07-15, 16-25) · UI 15.0 (26-32) · docs/process 3.5 (01, 33, 34, 39) · E2E 7.0 (35-38). Sum 83.5.

Suggested build order is the numeric order (dependencies hold); critical path and parallelizable chains are in [[T-031-components]].

---

## Conventions

**Status:** pending · in-progress · done · blocked (see Notes for why).
**Effort:** 0.5 / 1 / 1.5 / 2 / 3 h buckets. At the 3 h cap, a task that will not fit stops and goes to `replan`.
**Dependencies:** Notes column, e.g. "depends on 04". Same-file ordering (`stt.rs`: 02-05; `bridge.rs`: 20, 21, 24; `settings.js`: 26-32; `assistant_feature.py` + `test_plugins.py`: 14, 25) is a dependency even when no logic links the tasks.
**After every task:** `progress-tracker` with `task_id` and the evidence line (test count or output line); status is verified from the tree and a test count, never from a delegate's report.

## Links
- [[T-031-summary]] · [[T-031-plan]] · [[T-031-components]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-effort-estimate]] · T-031-effort-forecast (not produced)
- [[T-031-requirements]] · [[T-031-user-stories]] · [[T-031-decision-log]] · [[T-031-analysis]] · [[T-031-critique-report]] · [[T-031-plan-iteration-log]] · [[T-031-progress]] · [[T-031-verification]]

- Also: [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-release]] · [[T-031-requirements-draft]]
