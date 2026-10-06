---
ticket: "T-031"
artifact: plan
---

# Plan: T-031

Source of truth for scope: [[T-031-requirements]] (frozen iteration 2; 25 FRs, 73 ACs tagged [PY] [RS] [HL] [UI] [HW], 14 NFRs, 15 BRs). Q1 and Q2 are resolved by the user (models and voices only; keep all five voices and show each licence), so no engine-binary download is planned.

## Approach

1. **Console owns assets, shell owns engine and devices** (D-1, D-5, D-6, D-7, D-11): a stdlib-only downloader in `console/server/voice_assets.py` writes `desktop/stt|tts`; the shell resolves what is usable and loaded, picks devices by name, and swaps the speech model live. No new dependency anywhere (D-10; `cpal = "0.16"` already present).
2. **Seams before behaviour.** Python: an injected opener and sleep plus a local range-capable HTTP server, so no test touches the internet. Rust: an injectable engine spawner behind an `EngineSlot` instance (the process-wide `ENGINE` static cannot be tested in parallel), pure functions (`engine_is_stale`, `pick_by_name`, `needs_reopen`, `peak_of`, `speak_params`, tone renderer, `apply_voice_settings`) carry the tests, and bridge routes are tested by real loopback requests against `bridge::start` on a temp repo root.
3. **Riskiest first.** The mandatory mutex-free swap (`stt.rs:246` holds `ENGINE` for up to 30 s, `bridge.rs:415-416` reads it on a single-threaded bridge, `bridge.rs:199-204`) is Phase 1, so the toolchain, the seam design and the hardest test are proven before 80 hours depend on them. Order differs from the brief in two reasoned places (see [[T-031-components]] § Suggested build order).
4. **UI last, surgically.** The UI consumes stable routes and touches only `assistant()` in `console/static/settings.js`, with an appended block in `console/static/styles.css`; other tickets' uncommitted hunks stay byte-identical.
5. **Honest verification.** [PY] and [RS] are proven by named tests with counts; [HL] by a headless run of the real shell and console on this Windows machine; [UI] by a manual browser checklist; [HW] items are listed as "manual, NOT verified on hardware" and never get a test that pretends otherwise.

**Plan-level decisions** (recorded in [[T-031-decision-log]] D-14..D-19): D-14 the build-order refinements and the extra spawner-seam task; D-15 `/settings/refresh` re-applies on a short thread and returns at once (the console's settings GET "stalls ~3 s one request in fifteen", `console_settings.rs:123-126`, and the bridge is single-threaded); D-16 the catalog is read with `tomlio` (repo convention, no inline tables), not `tomllib`; D-17 the device verdict comes from the shell against its applied preference, so the matcher exists once; D-18 the one-line `get-whisper.ps1:103` exception; D-19 the backoff reading that reconciles AC-14 with AC-16.

**tech-select:** none required. Every choice the slices imply is covered by D-10 (confirm-existing): `urllib`, `hashlib`, `threading`, `http.server` (tests), `tomlio`; Rust `cpal`, `serde_json`, `std::sync::atomic`, hand-written loopback HTTP as in `console_settings.rs`. AC-73 pins that `Cargo.toml` `[dependencies]` and `console/requirements-dev.txt` stay unchanged.

## Structure

**Multi-layer.** Reason: 15 components across Python, Rust and UI, 39 tasks, a real dependency chain (catalog to transfer to install to jobs to routes to UI; device core to resolver to tests to bridge to console routes to UI). Chain: `analyze-components` ([[T-031-components]]) then `estimate` upfront ([[T-031-effort-estimate]]) then `breakdown-tasks` ([[T-031-task-breakdown]], [[T-031-implementation-plan]]) then `challenge-plan` ([[T-031-critique-report]] § Plan critique, [[T-031-plan-iteration-log]]).

## Build protocol (binding on the builder)

- **First action (task 01):** run `PYTHONUTF8=1 python console/kanban.py ticket move T-031 in-progress`. The builder runs it, not the planner. All `console/kanban.py` calls use `PYTHONUTF8=1` (`console/kanban.py context` crashes on cp1252 `→` without it; that crash is a separate existing task and is **not** fixed here).
- **After every task:** `progress-tracker` with `task_id`, the evidence line (test file and `N passed`, or the `test result:` line) and the files actually changed. A delegated agent's status line is a claim, not evidence (memory `subagent-status-not-evidence`): verify from `git status`, the named files, and the test count before marking `[x]`.
- **Cap rule:** every task is 0.5 to 3 h. If a task will not fit, stop, record it in progress.md, run `replan`; never stretch.
- **No** worktree isolation, **no** commit, push, stash or `git add`. The tree is shared and dirty with other tickets.

## Evidence conventions (used by every Done-criteria below)

- **PY** = from the repo root, `PYTHONUTF8=1 python -m pytest -o addopts="" <files> -q`; record the final `N passed` line. (`pytest.ini` sets `-q`, which prints bare dots; `-o addopts=""` gives a trustworthy count, and CI runs the same form, `verify.yml:48`.) "At least N tests" means N named tests exist and pass; the builder records the real count.
- **RS** = Rust in PowerShell from the repo root, sourcing the MSVC fixer first and reading the output file, never the exit code (memory `building-the-rust-shell`):
  `powershell -NoProfile -Command "$ErrorActionPreference='Continue'; . ./desktop/msvc-env.ps1 *>$null; cd desktop/src-tauri; cargo test <filter> -- --test-threads=1 2>&1 | Out-File -Encoding utf8 $env:TEMP/t031-rs.txt; exit 0"`, then read the file for `test result: ok. N passed; 0 failed`. Native and audio tests run `-- --test-threads=1` first (memory `windows-native-threading-traps`); drop the flag only after they pass. Task 01 records the baseline total; each Rust task reports baseline + its new tests.
- **No visible console windows:** any process a test or run spawns uses `CREATE_NO_WINDOW` (`0x0800_0000`, the existing pattern at `stt.rs:316-320`, `piper.rs:170-174`); Python tests spawn no processes. Task 37 checks with `knowledge-center/artifacts/T-003/ticket-scripts/list-console-windows.ps1` that no new visible console-class window exists.
- **No real network in Python tests.** Downloader tests run against a local range-capable server on `127.0.0.1` (helper `console/tests/voice_assets_server.py`, created in task 07) with an injected `sleep`; the loopback allowance is a test-only flag whose guard sits inside the injectable code path (a guard that runs ahead of the seam is not a seam, memory `cross-platform-defects-only-ci-finds`). The only internet use is the opt-in `CC_ONLINE_TESTS=1` check (AC-26) and the [HL] run (task 37).
- **Shared dirty files** (`console/static/settings.js`, `console/static/styles.css`; `app.js` and `index.html` are not touched at all): before the first edit of a task, copy the file to the session scratchpad; **re-read the file before every Edit**; after the task, `git diff --no-index <scratch copy> <file>` must show only that task's hunks, and `git diff -U0 <file>` must still contain the other tickets' hunks (new-file lines ~1652-1725, 1756-1769, 1771, 1973 in `settings.js`, outside `assistant()` at 952-1555) byte-identical. Never reformat, never rewrite a whole file, CSS only as one appended block (later tasks extend inside it using its comment anchors).
- **Do not touch:** `console/server/onboarding*.py`, `console/static/onboarding-wizard.js`, `console/server/setup_editor.py`, `console/server/features/shell_feature.py`, `console/server/dotenv.py`, `console/server/audit.py`, `console/config/agents.toml`, `console/static/app.js`, `console/static/index.html`, `console/server/features/onboarding_feature.py`. New audit action names are used without editing `audit.ACTIONS` (`audit.record` does not check it; `assistant.wake_train` is the precedent).
- **Constraint:** no new `ctx.*` call in `assistant_feature.apply()` beyond `ctx.get`/`ctx.post` (the CLI capture ctx implements only `get`, `post`, `register_tab`, `assistant_feature.py:657-675`).

## Slices

| Phase | Slice | Tasks | Delivers |
|-------|-------|-------|----------|
| 1 Start and shell model path | 1a-1c | 01-05 | step zero, `ensure()` fix, engine-slot seam, mutex-free swap, truthful hint |
| 2 Asset engine (Python) | 2a-2f | 06-12 | catalog, transfer, retry/policy, verify/install, jobs, inventory, delete |
| 3 Console settings, routes, poke | 3a-3c | 13-15 | keys + `APPLIES`, asset routes + audit, refresh poke helper |
| 4 Devices (Rust) | 4a-4d | 16-19 | pure core, resolver + capture, reopen loops, playback |
| 5 Refresh, preview, tests, bridge (Rust) | 5a-5e | 20-24 | `/settings/refresh`, `/speak` overrides, mic test, speaker tone, routes + caps |
| 6 Console routes | 6a | 25 | devices, tests, preview routes |
| 7 Settings UI | 7a-7g | 26-32 | chips, manager (2), model picker, voice, devices, tests |
| 8 Docs and compat | 8a-8b | 33-34 | docs, README, text checks, one-line `.ps1` fix |
| 9 Verification | 9a-9e | 35-39 | pytest, cargo, headless, UI checklist, [HW] list |

## Tasks

### [x] T-031-01 — Step zero: move the ticket to in-progress and record test baselines (0.5 h)
- [x] `PYTHONUTF8=1 python console/kanban.py ticket move T-031 in-progress` (the builder runs this, not the planner)
- [x] baseline pytest: `PYTHONUTF8=1 python -m pytest -o addopts="" -q` (about 225 s, memory `subagent-status-not-evidence`); record total, failed and the names of any pre-existing failures (the tree carries other tickets' uncommitted work, e.g. untracked `console/tests/test_onboarding_setup.py`)
- [x] baseline cargo: the RS command with no filter; record `test result:` total and any failure names (this also proves the Windows toolchain early, risk R-2)
- [x] note `desktop/stt` and `desktop/tts` contents (local `ggml-base.en.bin`, `en_US-amy-medium.onnx(.json)` are the legacy files AC-26 and AC-72 use) and whether `node` is on PATH (`node --version`; used for `node --check` in UI tasks, else say "not run")
- **Files may touch:** none in the product tree; `T-031-progress.md` via `progress-tracker` only
- **Done-criteria:** `ticket move` output shows lane `in-progress` and `console context T-031` (with `PYTHONUTF8=1`) no longer reports a stale lane; progress.md holds the baseline pytest total/failed, baseline cargo total/failed, the pre-existing failure list (or "none"), and the node check; every number is copied from command output, none estimated
- **Basis:** two long commands (pytest about 4 min, first cargo build about 1-2 min plus run) dominate; no code. Range 0.4-0.75 h.
- **Split because:** a process step that must precede every build task (hard handoff) and fixes the baseline later failures are judged against.
- **Depends on:** —

### [x] T-031-02 — `stt.rs`: `ensure()` compares the model (pure staleness fn, `model_file` fallback) (2 h)
- [x] extract `engine_is_stale(running_model, running_prompt, wanted_model, wanted_prompt) -> Option<Stale>`; `wanted_model` is the **resolved file name** from `model_file()` (a fallback compares like a choice), computed before the compare (D-6.1)
- [x] `ensure()` uses it (replace `stale = engine.prompt != wanted_prompt`, `stt.rs:255`); log reason (model or prompt)
- [x] `model_file` per-call warning (`stt.rs:155-158`) becomes once per distinct (wanted, fallback) pair via a small pure helper (D-6.5), because `ensure()` and `/health` now call it constantly
- [x] pin the filename contract `ggml-{name}.bin` in a test (AC-2 RS half)
- **Files may touch:** `desktop/src-tauri/src/stt.rs` only
- **Done-criteria:** RS `cargo test stt:: -- --test-threads=1` reports `test result: ok.` with baseline total + at least 8 new tests and 0 failed. Named tests: staleness table (same, model differs, prompt differs, both, resolved-fallback equals running gives `None`) **including the regression row: running `ggml-base.en.bin`, wanted `ggml-tiny.en.bin`, same prompt, is stale** (AC-35); `model_file` prefers the named file over the smallest, falls back to the smallest when absent (AC-36); fallback warning emitted once for repeated identical pairs and again for a different pair (AC-36); `ggml-{name}.bin` contract (AC-2). Existing `stt` tests stay green. `git diff --stat` lists only `stt.rs`.
- **Basis:** about 70 production lines and 120 test lines; about 6 cargo build cycles at 1-2 min. Range 1.5-3 h.
- **Split because:** the user-specified (a) of the pair: a self-contained, independently verifiable fix (AC-35/36) before the swap rework.
- **Depends on:** T-031-01

### [x] T-031-03 — `stt.rs`: engine slot behind an injectable spawner (behaviour-preserving seam) (2 h)
- [x] replace `static ENGINE: Mutex<Option<Engine>>` (`stt.rs:59`) with a static `EngineSlot` instance (`Mutex<SlotState>` + `Condvar`, `SlotState { engine, starting, failed }`); production code uses the static, tests build their own slot (the global would couple tests to each other and to `transcribes_a_spoken_command_from_a_fixture`)
- [x] `Spawner` (given binary, model, port, prompt returns a process handle) and readiness check (`responding(port)`) become injectable arguments of `ensure_with`; a tiny `Proc` trait (`alive`, `kill`) wraps `Child`; production spawner keeps `CREATE_NO_WINDOW`
- [x] `running()`, `loaded_model()`, `shutdown()` delegate to the static; semantics unchanged (still lock-holding start; the swap is task 04)
- **Files may touch:** `desktop/src-tauri/src/stt.rs` only
- **Done-criteria:** RS `cargo test stt:: -- --test-threads=1` shows all previously passing `stt` tests still pass, **including `transcribes_a_spoken_command_from_a_fixture` actually running against the real engine on this machine** (`--nocapture` output line `stt: model=... heard ...`, not `skipped:`), plus at least 3 new tests (slot built with a fake spawner; `ensure_with` starts once and reuses; shutdown kills via the fake). `grep -n "static ENGINE" desktop/src-tauri/src/stt.rs` shows an `EngineSlot`, not a `Mutex<Option<Engine>>`. No behaviour change: log lines `stt: engine up on {port} with {model}` and `stt: restarting the engine` unchanged.
- **Basis:** about 120 lines of refactor (trait objects, const-constructible statics) and 60 test lines; compile-error iteration dominates. Range 1.5-3 h.
- **Split because:** an independently reviewed, behaviour-preserving piece that task 04's test depends on (hard dependency); keeping it apart keeps the mandatory swap diff reviewable.
- **Depends on:** T-031-02

### [x] T-031-04 — MANDATORY `stt.rs`: live model swap that never holds the engine mutex across the start, with its own test (3 h)
- [x] `ensure_with`: short lock to read state; if the engine is alive and not stale return its port; if stale and alive and no replacement is starting, mark `starting`, **drop the lock**, start the replacement on a new port in a background thread, return the old port at once (a take never waits on, or fails because of, a swap, D-6); when the replacement answers (at most `START_TIMEOUT` 30 s) publish it under a **short** lock so new takes use it, then retire the old process (CR-36: a take that already holds the old port may be mid-inference, `INFER_TIMEOUT` 60 s; killing at once would fail that take, so `ensure_with` hands out a `Lease` guard that `transcribe` holds for the whole request, and the old engine is killed when its lease count reaches zero, immediately if there is none, and at `shutdown`)
- [x] first start or dead engine (no engine to serve): the starter spawns **outside** the lock; other callers wait on the `Condvar` with a timeout, never on the mutex
- [x] failed or never-answering replacement: kill it, keep the old engine, record `failed = (model file, prompt, message)`; do **not** retry that key per take; clear when the wanted key changes (D-6.3); `swap_error()` accessor for the bridge field (wired in task 24)
- [x] a prompt-only change takes the same path (today it kills first, `stt.rs:259-268`)
- [x] expose a `prewarm(repo_root)` entry the refresh route (task 20) can call to start the replacement in the background
- **Files may touch:** `desktop/src-tauri/src/stt.rs` only
- **Done-criteria:** RS `cargo test stt:: -- --test-threads=1` then once without the flag: `test result: ok.` with at least 9 new tests, all on a private `EngineSlot` with a fake spawner and fake readiness (no process, no network): (1) one replacement for two concurrent callers and the old process killed only after the new one answers, asserted from an ordered event log (AC-37); (9) **a take holding a lease on the old engine keeps it alive**: after the swap publishes, the old process is not killed until the lease is dropped, then it is killed once (CR-36); (2) **while a spawn is blocked, `loaded_model()` and `running()` each return in under 100 ms (20 calls, worst case asserted)** (AC-38, the mandatory proof that `ENGINE` is not held across the start); (3) during the blocked spawn `ensure_with` for a take returns the **old** port in under 100 ms; (4) failed replacement: old keeps serving, `swap_error()` non-empty, `ensure_with` returns `Ok(old_port)`, so no `transcribe` error (AC-39); (5) five further calls after a failure do not spawn again, and one attempt happens after the wanted key changes; (6) no engine at all: the starter blocks in the spawner, `loaded_model()` still answers at once, a second caller waits and receives the same port (spawner count 1); (7) a replacement that never answers is abandoned at an injected short timeout, old kept, error set; (8) a dead old engine is replaced synchronously. `transcribes_a_spoken_command_from_a_fixture` still runs for real and passes. Review check: no mutex guard is held across `spawner(` or `ready(` calls (`grep -n` of those call sites in the diff). `START_TIMEOUT` remains 30 s.
- **Basis:** about 220 production lines, 200 test lines; the concurrency tests are the hard part (deterministic blocking via channels, not sleeps). Range 2.5-4.5 h; at the cap, so if the design needs more than 3 h stop and `replan` rather than overrun. Memory while swapping is old + new model resident (D-6.6; small.en/medium.en unmeasured, risk R-9).
- **Split because:** the user's mandatory separate task with its own concurrency test; also the riskiest piece of the ticket.
- **Depends on:** T-031-03

### [x] T-031-05 — `stt::hint` tells the truth and the two wording tests stay in sync (1 h)
- [x] `stt.rs` `hint()` (`stt.rs:197-211`): remove the non-existent `sh desktop/get-whisper.sh`; every variant says where the fix is (Settings, Assistant, Speech models) and, on non-Windows, that the engine (`whisper-server`) is installed separately and put on PATH or in `desktop/stt` (D-3, D-6); Windows may still name `desktop/get-whisper.ps1` because it exists
- [x] update the test at `stt.rs:511` (`contains("get-whisper")`) and `listen.rs:366` (`contains("microphone") || contains("get-whisper")`) to the new wording, per OS (`cfg!(windows)`); do not delete them
- [x] pin the `hands_free.rs:382` contract: every non-empty hint contains the word "engine" (or the mic hint contains "microphone"), so a mid-session loss stops the loop instead of spinning; add the test
- **Files may touch:** `desktop/src-tauri/src/stt.rs`, `desktop/src-tauri/src/listen.rs` (test assertion only)
- **Done-criteria:** RS `cargo test stt:: listen:: hands_free:: -- --test-threads=1`: `test result: ok.`, at least 3 new tests: hint contains "Settings" in every non-empty variant; every `get-*.ps1`/`get-*.sh` path named in the hint exists under `desktop/` (AC-44); every non-empty variant contains "engine". Both previously pinned tests updated and green. `grep -rn "get-whisper.sh" desktop/src-tauri/src` returns nothing.
- **Basis:** about 25 production lines, 60 test lines, 3-4 cargo cycles. Range 0.75-1.5 h.
- **Split because:** the same file as 02-04 but a different, independently reviewed concern (user-facing wording, three pinned tests); kept after 04 so the shell never ships a truthful hint with a broken swap.
- **Depends on:** T-031-04

### [x] T-031-06 — Catalog `voice-assets.toml` + loader + catalog tests (3 h)
- [x] `console/config/voice-assets.toml` in the **`tomlio` subset** (`[[stt]]` + `[[stt.file]]`, `[[voice]]` + `[[voice.file]]`; no inline tables, no multi-line strings; `tomlio.py:1-13`): 4 STT models and 5 voices with the commit-pinned https URL, `size`, `sha256`, `hash_source` (`hf-lfs-oid` for the 9 large files, `computed-pinned` plus `git_blob_sha1` for the five `.onnx.json`), `hint` (D-13 sizes: tiny.en 74 MiB / 78 MB, base.en 141 MiB / 148 MB, small.en 465 MiB / 488 MB, medium.en 1.43 GiB / 1.53 GB, plus the one-line quality note), `license` copied verbatim (D-12; ryan labelled CC BY-NC-SA 4.0, non-commercial). Every value is copied from [[T-031-decision-log]] D-2; none typed from memory.
- [x] `console/server/voice_assets.py` (new): catalog dataclasses + `load_catalog(path)` via `tomlio.load` (D-16: repo convention, no `tomllib`) + `catalog_from_dict` for test fixtures; API-facing fields `size_bytes` (voices: sum of both files), `hint`, `license`
- **Files may touch:** `console/config/voice-assets.toml` (new), `console/server/voice_assets.py` (new), `console/tests/test_voice_assets_catalog.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_catalog.py`, at least 9 tests pass: AC-1 every file has an https `huggingface.co` URL whose path pins a 40-hex commit, size > 0, 64-hex sha256, `hash_source` in {`hf-lfs-oid`, `computed-pinned`} (with a 40-hex `git_blob_sha1` for the latter), a safe name (`^[A-Za-z0-9._-]+$`), and no entry lacks a hash; counts exactly 4 STT, 5 voices, 14 files (9 `hf-lfs-oid`, 5 `computed-pinned`); AC-2 (PY half) names are `ggml-{id}.bin`, `{voice}.onnx` and `{voice}.onnx.json`; AC-3 `size_bytes`, `hint`, `license` present and no hint states a size that differs from `size_bytes` (numbers parsed from the hint and compared); ryan's licence contains "NC"; the committed file loads through the console's own `tomlio`; AC-26 catalog hashes equal the real local `desktop/stt/ggml-base.en.bin`, `desktop/tts/en_US-amy-medium.onnx` and `.onnx.json` when present (skip **loudly** with the reason when absent) and an opt-in test (`CC_ONLINE_TESTS=1`) that compares `x-linked-etag` for the 9 LFS files and the SHA256 of the five small `.onnx.json` downloads to the catalog; the builder runs the online test **once** and records "ran, N passed" or "not run" in progress.md (not part of CI).
- **Basis:** about 150 lines of Python, about 140 lines of TOML (14 files), about 150 test lines; copying 14 hashes carefully is the risk, and the online check is the independent proof. Range 2-3.5 h.
- **Split because:** a self-contained deliverable (the catalog is the one source every later Python task reads) and the only place hashes enter the repo, so it is independently reviewed against D-2.
- **Depends on:** T-031-01

### [x] T-031-07 — Transfer core: `.part` + Range, 200/206/416, size checks, streaming; local range server (3 h)
- [x] `voice_assets.py`: `Transfer` (one file): streams 1 MiB chunks to `{final}.part`; resumes with `Range: bytes=N-`; 206 appends, 200 truncates and restarts, 416 with N == size means complete else deletes `.part` and restarts; `Content-Range` total or response size differing from the catalog size fails with "upstream file changed" and deletes `.part` (D-4); injectable `opener`, `sleep`, clock, stop callback (pause/cancel semantics land in task 10)
- [x] `console/tests/voice_assets_server.py` (new test helper, imported like `from conftest import ...` elsewhere in this suite): `http.server` on `127.0.0.1:0` with Range support, `ignore_range`, `status_script`, `drop_after`, `wrong_total`, `redirect_to`, request log (headers, ranges, connection count); generates large bodies from a reused 1 MiB block so memory stays measurable
- **Files may touch:** `console/server/voice_assets.py`, `console/tests/voice_assets_server.py` (new), `console/tests/test_voice_assets_transfer.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_catalog.py console/tests/test_voice_assets_transfer.py`, at least 7 new tests pass, no real network (loopback only): the Range header equals the existing `.part` size and the final bytes are correct (AC-13); a 200 reply to a Range request restarts from zero and the final bytes are correct (AC-15); 416 at full size completes, 416 below it restarts; catalog size or `Content-Range` mismatch yields "upstream file changed" and removes `.part` (AC-17); a fresh start sends no Range header; **32 MiB streams with `tracemalloc` peak under 8 MiB** (AC-25, NFR-5); a zero-byte reply is a failure, not an install.
- **Basis:** about 170 production lines, 150 helper lines, 150 test lines. Range 2.5-4 h (cap).
- **Split because:** first of the downloader chain and a hard dependency of 08-10; the local server helper is a reusable deliverable.
- **Depends on:** T-031-06

### [x] T-031-08 — Retry/backoff and URL policy (https only, host, https-only redirects, no credentials) (3 h)
- [x] `backoff_delay(failures) = 0.5 * 2**min(failures, 5)`; the transfer loop ports Mic Drop's mechanics (`mic-drop/crates/micdrop-core/src/download.rs:224,278,326,355`): `failures += 1` per consecutive failure, **give up when `failures > 6`**, sleep `backoff_delay(failures)` between attempts (so six sleeps of 1, 2, 4, 8, 16, 16 s, then the seventh consecutive failure fails), counter resets whenever bytes arrive; transport errors, 429 and 5xx retry, any other 4xx fails at once; `.part` kept on give-up (resumable)
- [x] URL policy checked inside the injectable request path (not ahead of it): only catalog URLs, `https` only, initial host exactly `huggingface.co`, redirects followed only to `https`, CDN hostnames not allow-listed (D-4), no `Authorization` or `Cookie` header ever sent (also stripped on redirect); a test-only `allow_loopback_http` flag admits `http://127.0.0.1` only
- **Spec note (see CR-21):** AC-14 lists seven delays `0.5, 1, 2, 4, 8, 16, 16` while FR-4/AC-16/D-4 cap consecutive failures at six. Both hold as written when the formula is a table and the loop is Mic Drop's: the table test asserts `backoff_delay(0..6) = 0.5, 1, 2, 4, 8, 16, 16` (AC-14 literally), the loop test asserts the sleeps actually taken for six consecutive failures are `1, 2, 4, 8, 16, 16` and the seventh fails (AC-16, D-4). If the owner wants a 0.5 s first sleep, that is an `evolve` of AC-14/D-4, not a build-time guess.
- **Files may touch:** `console/server/voice_assets.py`, `console/tests/voice_assets_server.py`, `console/tests/test_voice_assets_transfer.py`
- **Done-criteria:** PY `console/tests/test_voice_assets_transfer.py`, at least 10 new tests pass with an injected `sleep` that records instead of sleeping (the suite adds no wall-clock waits over 1 s): delay table (AC-14); six failures then success takes sleeps `[1, 2, 4, 8, 16, 16]`; the seventh consecutive failure ends `failed` with `.part` kept and a second Download resumes from it (AC-16); a mid-body drop resumes and bytes arriving reset the counter (more than six drops that each deliver bytes still succeed) (AC-14); 404 and 403 fail immediately with no sleep; 429 and 503 are retried (AC-16); connection refused is retried; AC-31: `http://` non-loopback URL rejected before any connection, an `http://` redirect target rejected, a foreign initial host and a look-alike host (`huggingface.co.evil.example`) rejected, a recorded request carries no `Authorization` or `Cookie`, and the policy still runs when a fake `opener` is injected.
- **Basis:** about 130 production lines, 200 test lines; the policy-inside-the-seam requirement and the redirect handler need care (`urllib` redirect handler subclass). Range 2.5-4 h (cap).
- **Split because:** an independently reviewed security surface (NFR-3) separate from the happy-path transfer; hard dependency of 09.
- **Depends on:** T-031-07

### [x] T-031-09 — Verify and atomic install: SHA256, `os.replace`, manifest last, voice file order, disk and write errors (3 h)
- [x] after the last byte: size check, SHA256 over the **whole** `.part`, then `os.replace(part, final)`, then `{final}.manifest.json` (`{id, sha256, size, source_url, commit, installed_at}`) via temp + replace, written **last**; the shell-visible name (`ggml-*.bin`, `*.onnx`) therefore never exists for incomplete or unverified bytes (BR-2)
- [x] voices: `.onnx.json` verified and replaced first, `.onnx` last; a failed `.onnx` leaves no `.onnx` and removes a `.onnx.json` this job created
- [x] hash mismatch: delete `.part`, fail with expected/actual prefixes (first 12 hex), **no automatic retry** (D-4)
- [x] free space checked against the remaining bytes (injected `disk_free`) **before connecting**; a write error (`ENOSPC`) fails the job and keeps `.part`
- [x] `verify_existing(spec, path)`: hashes a hand-placed file, writes the manifest on a match, reports a mismatch and leaves the file untouched
- **Files may touch:** `console/server/voice_assets.py`, `console/tests/voice_assets_server.py`, `console/tests/test_voice_assets_install.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_install.py` (plus the earlier two files still green), at least 9 tests pass: wrong bytes with the right length end `failed` (reason names sha256 with expected/actual prefixes), the final name never exists, `.part` is removed and the server logs no further GET (AC-21); a **four-point fault matrix** (after last byte; after hash before replace; after replace before manifest; during manifest write), parametrized, asserts the final name exists only after verification and that the rename-before-manifest case leaves a final file with no manifest (the inventory-state half, `installed`/`verified:false`, is asserted in task 11) (AC-22, NFR-1); voice order recorded as `.onnx.json` replace before `.onnx` replace, and a failed `.onnx` leaves no `*.onnx` (AC-23); Verify with a matching file writes the manifest, with a mismatching file reports expected/actual and leaves bytes and mtime unchanged (AC-24); a short disk is refused with **zero** requests recorded (AC-30); an `OSError(ENOSPC)` injected mid-write gives `failed` with `.part` kept (AC-32).
- **Basis:** about 150 production lines, 220 test lines; fault injection hooks must be real seams, not guards ahead of them. Range 2.5-4 h (cap).
- **Split because:** the integrity boundary (NFR-1) is independently reviewed and has its own fault matrix.
- **Depends on:** T-031-08

### [x] T-031-10 — Job manager: one job per id, pause/resume/cancel, progress, restart recovery (3 h)
- [x] `Manager`: `download(id)` starts a daemon thread and returns the job; a second `download` for the same id returns the existing job (no second transfer); `pause` drops the connection and keeps `.part`; `resume` reconnects with Range; `cancel` stops, joins and deletes `.part`; states `not_installed, partial, downloading, paused, retrying, verifying, installed, failed`; failed jobs persist their last error in memory and the state derives from disk after a restart
- [x] progress fields `state, done, total, speed_bps, eta_s, resumed_from, file`; for a voice `done`/`total` span both files and `file` names the current one (CR-17); published at most every 500 ms and at least on every state change; `eta_s` is null at speed 0
- [x] one `logging` record per job start, retry, finish, failure (NFR-13)
- **Files may touch:** `console/server/voice_assets.py`, `console/tests/test_voice_assets_jobs.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_jobs.py` (plus earlier files green), at least 10 tests pass, deterministic (injected clock, event-based waits, no assertion on wall time): states observed in order downloading, verifying, installed, with byte-identical file, a manifest and no `.part` (AC-9); `done` non-decreasing, republished at least every 500 ms of clock time, `speed_bps` > 0 while moving, `eta_s` null at speed 0 (AC-10); a second Download returns the same job and the server logs exactly one non-Range transfer (AC-11); pause closes the connection (server connection count returns to zero), `done` stops, resume sends Range and completes (AC-18); cancel while active and while paused ends the thread (`is_alive()` false) and removes `.part`, state `not_installed` (AC-19); a new `Manager` over an existing `.part` of N bytes reports `partial` with N bytes, and Download sends `Range: bytes=N-` with `resumed_from == N` (AC-20); two-file voice progress spans both files; one log record per lifecycle event (caplog); no thread outlives its test.
- **Basis:** about 200 production lines, 220 test lines; thread lifecycle and deterministic pause/cancel tests are the cost. Range 2.5-4 h (cap).
- **Split because:** threads and pause/cancel are a concurrency boundary reviewed apart from the transfer bytes (hard dependency of 11, 12, 14).
- **Depends on:** T-031-09

### [x] T-031-11 — Inventory and state: scan, custom rows, `verified`, `in_use`, `loaded`, shell down (3 h)
- [x] `inventory(...)`: per catalog entry and per unlisted `ggml-*.bin`/`*.onnx` on disk (`custom`): state, size, `verified` (manifest sha equals catalog sha), `in_use` (configured model as the shell resolves it: named file if present else the smallest `ggml-*.bin`; blank voice = first sorted installed, as `piper::voice`), `loaded` (from the shell), progress, `free_bytes`; `.part`, `.manifest.json`, `.onnx.json` and other files are never listed; works with the shell down: `shell.reachable:false`; when it is up, a `shell` object carries the caps subset the UI needs (`speak_backend`, `speak_voice_in_use`, `stt_model`, `loaded_model`; the UI has no other way to learn the speech backend, task 30)
- [x] `native_bridge.capabilities` gains an optional `timeout` argument (backward compatible); the inventory call uses <= 1.5 s (AC-7, NFR-4)
- **Files may touch:** `console/server/voice_assets.py`, `console/server/native_bridge.py` (add the optional `timeout` parameter only), `console/tests/test_voice_assets_inventory.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_inventory.py` (plus earlier files green), at least 9 tests pass: empty and absent directories give all `not_installed` and a present `free_bytes` (AC-4); final+matching manifest gives `installed`/`verified:true`, final only gives `installed`/`verified:false`, `.part` only gives `partial` with its byte count, a manifest sha differing from the catalog gives `verified:false` (AC-5); uncatalogued `ggml-*.bin` and `*.onnx` appear as `custom`, while `.part`, `.manifest.json`, `.onnx.json` and a stray `README.txt` do not (AC-6); `in_use` table including configured-but-absent (shell falls back to the smallest) and blank voice (first sorted) (AC-7); `loaded` comes from a fake bridge; shell down gives a normal answer with `shell.reachable:false` and the bridge call carries `timeout <= 1.5` (AC-7); **no outbound call**: `urllib.request.urlopen` and `socket.create_connection` patched to raise while only the injected fake bridge opener is allowed (AC-8); script-placed files (synthetic bytes matching a fixture catalog) read `installed`/`verified:false` (AC-72, files half); a rename-before-manifest leftover from task 09's fault reads `installed`/`verified:false` (AC-22, state half).
- **Basis:** about 150 production lines, 200 test lines. Range 2.5-3.5 h.
- **Split because:** a read-only, self-contained deliverable (the data the UI renders) that works with no shell; hard dependency of 12 and 14.
- **Depends on:** T-031-10

### [x] T-031-12 — Delete with refusals, OS-lock sentence, name validation and confinement (2 h)
- [x] `delete(name_or_id)`: removes final(s), manifest and `.part`; refused (with the reason) when the asset is in use, loaded in the engine, or downloading; names validated against the inventory **and** `^[A-Za-z0-9._-]+$`; path resolved and required to sit inside `desktop/stt` or `desktop/tts`; removal is rename-to-tombstone first, then unlink, rolling back on failure so nothing is half-deleted (a Windows lock raises `PermissionError`)
- **Files may touch:** `console/server/voice_assets.py`, `console/tests/test_voice_assets_delete.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_delete.py` (plus earlier files green), at least 8 tests pass: full removal of final, manifest and `.part` returns the entry to `not_installed` (AC-27); refusals for in-use, loaded and downloading each return a sentence with the reason and delete nothing (AC-28); a `PermissionError` injected on the second file of a voice restores the first, reports a sentence naming the file, and is **not** raised as a 5xx (AC-28); traversal (`../x`, `a/b`, `a\b`, an absolute path, empty, a name not in the inventory) is rejected and a symlink or junction escaping the two directories is refused (AC-29, NFR-3).
- **Basis:** about 90 production lines, 130 test lines. Range 1.5-2.5 h.
- **Split because:** a destructive action with its own safety rules, reviewed apart from the read-only inventory.
- **Depends on:** T-031-11

### [x] T-031-13 — Settings keys `input_device`/`output_device` and the `APPLIES` map (2 h)
- [x] `assistant_config.py`: add both keys to `DEFAULTS` (`""` = system default), `WRITABLE`, validation (stripped string, at most 200 characters, no control characters, `""` allowed, no path rules; D-9); `stt_model` and `speak_voice` validation stays shape-only (D-9)
- [x] `APPLIES = {key: {"when": "live"|"restart"|"next_chat", "note": str}}` next to `WRITABLE`, classified per D-8: live = `listen_max_seconds`, `listen_silence_ms`, `listen_first_pause_ms`, `stt_model` (note text: "the new model loads in the background; a take in the first seconds may still use the previous one", CR-39), `speak`, `speak_voice`, `speak_rate_percent`, `tray_click_action`, `reply_chars`, `session_idle_minutes`, `ticket_prefix`, `work_backend`, `work_model`, `backend_chain`, `input_device`, `output_device`; restart = `hands_free_require_wake`, `hands_free_wake_word`, `hands_free_listen_while_speaking`, `hands_free_max_minutes`, `wake_sensitivity`, `listen_preroll_ms` (hands-free off/on), `hud_dismiss_shortcut` (shell restart); next_chat = `backend`, `model`, `mode`
- [x] `settings_get` returns `applies` (static data; the hot path still touches no network); `console/config/assistant.toml` gains `input_device = ""` and `output_device = ""` with comments
- **Files may touch:** `console/server/assistant_config.py`, `console/server/features/assistant_feature.py` (the `settings_get` return only), `console/config/assistant.toml`, `console/tests/test_assistant_commands.py` (new test classes appended; existing tests untouched)
- **Done-criteria:** PY `console/tests/test_assistant_commands.py console/tests/test_assistant.py`, existing tests green and at least 9 new tests: both keys default `""`, round trip through `update`, are stripped, reject a control character and a 201-character value and accept 200, the committed `assistant.toml` default equals `DEFAULTS`, an unknown key is still rejected (AC-51); every `WRITABLE` key (26 now) has an `APPLIES` entry with a valid `when` and a non-empty `note`, and a copied `WRITABLE` with one extra key fails the same check (AC-67); `settings_get` returns `applies` equal to `APPLIES` (AC-68); an override file with no device keys merges to `""` (AC-72, keys half); SHOULD source scan: every `APPLIES` key classed `restart` for hands-free (the six above) appears in `fetch_policy` in `desktop/src-tauri/src/hands_free.rs` (AC-70).
- **Basis:** about 80 production lines, 150 test lines. Range 1.5-2.5 h.
- **Split because:** an independent, small contract (cross-language settings keys are a silent contract, `test_assistant_commands.py:349-357`) that three later tasks read (20, 25, 26).
- **Depends on:** T-031-01

### [x] T-031-14 — Asset routes with audit, plus the pinned route-set test (2 h)
- [x] routes registered in `assistant_feature.apply()` with `ctx.get`/`ctx.post` only: `GET /api/assistant/voice/assets`, `POST /api/assistant/voice/assets/{download,pause,resume,cancel,delete,verify}`; body carries a catalog id or inventory name only, never a URL or path (BR-9); one `Manager` per repo root kept in a module-level registry so jobs outlive a request (the CLI's `handlers()` rebuilds the capture ctx on every call)
- [x] `audit.record` for download, cancel, delete and verify (`assistant.voice_asset.<action>`, target = id; no edit to `audit.ACTIONS`, `audit.py` is another ticket's dirty file and `record()` does not check the tuple)
- [x] update the exact route-set assertion in `console/tests/test_plugins.py` (`assert set(routes) == {...}`, lines 204-224)
- **Files may touch:** `console/server/features/assistant_feature.py`, `console/server/voice_assets.py` (registry accessor only), `console/tests/test_plugins.py`, `console/tests/test_voice_assets_routes.py` (new)
- **Done-criteria:** PY `console/tests/test_voice_assets_routes.py console/tests/test_plugins.py console/tests/test_assistant.py console/tests/test_native_bridge.py`, at least 9 new tests and no regressions: an unknown id is refused (400) with **no network call** (an opener that raises if used) (AC-12); `url`, `path`, `file` and `filename` in the body change nothing (the recorded request URL is the catalog's) (AC-12); download, cancel, delete and verify each write exactly one audit record with the id as target (AC-33); pause and resume work through the routes; `GET assets` equals the inventory shape; **p95 under 250 ms over 50 `GET assets` calls with two active downloads (slow local server) and the shell absent** (NFR-4); `assistant_feature.handlers(repo)` still builds with the capture ctx (no new `ctx.*` method); the updated route-set test passes.
- **Basis:** about 110 production lines, 180 test lines. Range 1.5-2.5 h.
- **Split because:** the HTTP surface is a different component (S5) from the engine and has its own audit and pinned-route obligations; hard dependency of 27-28.
- **Depends on:** T-031-12, T-031-13

### [x] T-031-15 — Console-to-shell refresh poke: helper and best-effort call from `settings_post` (1.5 h)
- [x] `native_bridge.settings_refresh(repo_root, opener=None)`: `POST /settings/refresh`, timeout 1.0 s, returns the usual `{ok, ...}` shape; no pointer returns `{"ok": False, "reason": "shell not running"}` immediately
- [x] `settings_post` calls it after a successful `assistant_config.update` and **swallows every failure** (a failed poke never fails or delays the write beyond its 1 s cap; a rejected write pokes nothing)
- **Files may touch:** `console/server/native_bridge.py`, `console/server/features/assistant_feature.py` (the `settings_post` body only), `console/tests/test_settings_refresh.py` (new)
- **Done-criteria:** PY `console/tests/test_settings_refresh.py console/tests/test_native_bridge.py console/tests/test_assistant.py`, at least 5 new tests and no regressions: the helper POSTs `/settings/refresh` with the bearer token and `timeout <= 1.0`; no pointer returns `ok:false` without any network call; `settings_post` calls the helper exactly once per accepted write and zero times when validation rejects (AC-41); a helper that raises, returns `ok:false` or times out still returns the merged settings from `settings_post` (AC-41); the CLI path `assistant_feature.call(repo, "assistant.settings_post", ...)` still works.
- **Basis:** about 40 production lines, 100 test lines. Range 1-2 h.
- **Split because:** an independent deliverable owned by the console that the shell route (task 20) is built against; contract-first so the two sides are verified separately.
- **Depends on:** T-031-01

### [x] T-031-16 — `devices.rs` core: enumerate by direction, one pure `pick_by_name`, preferences, generation (3 h)
- [x] new `desktop/src-tauri/src/devices.rs` (and `mod devices;` in `main.rs`, which is not dirty): `enumerate()` returns per-direction names plus the OS defaults via the already-present cpal 0.16 (`input_devices()`, `output_devices()`, `Device::name()`), never panics (any error gives an empty list); **no new crate** (D-10)
- [x] pure `pick_by_name(wanted, names) -> Pick` (D-5): empty or whitespace gives `Default`; case-insensitive trimmed **exact** match (first wins on identical names); else a **unique** case-insensitive substring match; several substring candidates gives `None` carrying the candidates; zero gives `None`
- [x] pure `resolve_name(direction, wanted, &DeviceList) -> Verdict { configured, resolved, match_kind (exact/substring/none/default), fallback, candidates }` that only ever reads that direction's list
- [x] a small `Prefs` struct (preferred input and output names, two generation counters) with one global instance for production; `set_input(name) -> bool` / `set_output(name) -> bool` (trimmed; return `true` and bump the generation **only if the value changed**), `input_generation()`, `output_generation()`, `input_preference()`, `output_preference()`; tests build their own `Prefs` so default parallel `cargo test` cannot interfere (a process-wide static would couple tests); pure `needs_reopen(opened_gen, current_gen)`
- **Files may touch:** `desktop/src-tauri/src/devices.rs` (new), `desktop/src-tauri/src/main.rs` (the single `mod devices;` line)
- **Done-criteria:** RS `cargo test devices:: -- --test-threads=1`: `test result: ok.` with baseline + at least 10 new tests: the `pick_by_name` table (exact beats an earlier substring; case and surrounding spaces; unique substring; ambiguous gives `None` with candidates; empty and whitespace give `Default`; non-ASCII names; identical names give the first; empty list gives `None`) (AC-52); `resolve_name` never returns a name that is not in the requested direction's list, including a name present only in the other direction (AC-53); generation unchanged by re-setting the same value and bumped once by a change; `needs_reopen` cases (AC-56, pure half); `enumerate()` returns without a panic and keeps the two directions separate (AC-49, RS half; on a machine with no audio device the lists are empty and the test still passes). `git diff --stat` shows `devices.rs` new and `main.rs` one line.
- **Basis:** about 220 production lines, 180 test lines; the enumeration call is the only unknown (context snapshot §6). Range 2.5-3.5 h.
- **Split because:** the independently reviewed pure core (matcher BR-6 exists once) that tasks 17-24 all consume; bottleneck component R2.
- **Depends on:** T-031-01

### [x] T-031-17 — Resolver and capture: `Mic` opens the chosen device and remembers it (3 h)
- [x] enumeration is cached for about 1 s (injected clock; invalidated by a preference change) because `audio::available()` and `device_name()` are called from `/health` and from `/listen/state`, which the voice panel polls twice a second on the single-threaded bridge (CR-37); `/audio/devices` with the Refresh button bypasses the cache
- [x] `devices::resolve_input()` / `resolve_output()` return the device, its name and the verdict; an unresolved name falls back to the system default, logs **one** warning per change and sets `fallback: true` (D-5); these two functions are the **only** place `default_*_device()` is called (enforced by task 19's scan; `piper.rs` and `cue.rs` still call the OS default until T-031-19)
- [x] `audio.rs`: `Mic::open()` uses the resolver, stores `device_name` and the generation it opened under, exposes `needs_reopen()`; `available()` and `device_name()` describe the **resolved** device, so `/listen/state.microphone` and `listen::hint` are truthful; open failure text still contains "microphone"; the open log line names the device (NFR-13)
- **Files may touch:** `desktop/src-tauri/src/devices.rs`, `desktop/src-tauri/src/audio.rs`
- **Done-criteria:** RS `cargo test devices:: audio:: -- --test-threads=1`: `test result: ok.` with at least 7 new tests on pure helpers (a `choose(pick, names, default)` function carries the logic so no hardware is needed; one test covers the cache TTL with an injected clock: a second call within 1 s does not enumerate again, a call after 1 s or after a preference change does): an unresolved name picks the default with `fallback:true` (AC-55); the warning fires once for a repeated identical unresolved preference and again after it changes (AC-55); the no-device error and the open-failure error strings both contain "microphone" (AC-57); `device_name()` and `Mic`'s remembered name come from one resolver call (AC-57); on a machine with an input device, a hardware-gated test opens a `Mic` and checks the remembered name equals `device_name()` (skipped loudly, not failed, with no device; run single-threaded first). Existing `audio::` tests green.
- **Basis:** about 150 production lines, 120 test lines; `Mic::open` is long and fragile, edit in place. Range 2.5-3.5 h.
- **Split because:** the capture path is a different component from the pure core and carries the user-visible behaviour change (hard dependency of 18, 19, 22).
- **Depends on:** T-031-16

### [x] T-031-18 — Reopen on change in the take path and the hands-free loop (2 h)
- [x] `listen.rs` `take_inner`: reopen a cached `Mic` when `needs_reopen()`; a pre-roll cursor from a replaced mic is meaningless, so a reopened take starts now (pure `reopen_decision` function, logged)
- [x] `hands_free.rs` `run`: in the armed branch check `needs_reopen()` before `since(cursor)`; on a change drop the mic, open a new one, reset `cursor` to the new mic's cursor and `spotter.reset()`; an open failure returns the usual text containing "microphone" so the existing stop at `hands_free.rs:382` is unchanged
- **Files may touch:** `desktop/src-tauri/src/listen.rs`, `desktop/src-tauri/src/hands_free.rs`
- **Done-criteria:** RS `cargo test listen:: hands_free:: devices:: -- --test-threads=1`: `test result: ok.` with at least 4 new tests: the pure `reopen_decision` table (no mic opens; same generation keeps; changed generation replaces and resets the cursor; pre-roll dropped on replacement) (AC-56); re-applying an identical preference does not bump the generation, so nothing reopens (AC-56); source check that both `listen.rs` and `hands_free.rs` reference `needs_reopen`; the existing `hands_free` tests (including the pinned error words) stay green. Not verified on hardware: a real device switch mid-session is [HW] (task 39).
- **Basis:** about 60 production lines, 80 test lines. Range 1.5-2.5 h.
- **Split because:** a different component pair (`listen`/`hands_free`) with the armed-loop cursor semantics, reviewed apart from the resolver.
- **Depends on:** T-031-17

### [x] T-031-19 — Playback and cues use the resolver; source scan enforces one call site (1.5 h)
- [x] `piper.rs` `play()` and `cue.rs` `blow()` obtain their output device from `devices::resolve_output()`; the OS-voice fallback in `tts.rs` still plays to the system default and ignores voice, speed and device (D-5; the UI says so in task 30)
- [x] scan test in `devices.rs`: no `default_input_device(` or `default_output_device(` text under `desktop/src-tauri/src/` outside `devices.rs` (the needle is assembled from two pieces so the test file does not match itself; `examples/audio_probe.rs` is out of scope of the scan)
- **Files may touch:** `desktop/src-tauri/src/piper.rs`, `desktop/src-tauri/src/cue.rs`, `desktop/src-tauri/src/devices.rs` (scan test only)
- **Done-criteria:** RS `cargo test devices:: cue:: piper:: -- --test-threads=1`: `test result: ok.` with at least 2 new tests (the scan, and an output-resolution unit test); existing `cue` and `piper` tests green; `grep -rn "default_output_device\|default_input_device" desktop/src-tauri/src` lists only `devices.rs` lines (output pasted into progress.md) (AC-54). The audibility on a second output device is [HW] (task 39).
- **Basis:** about 25 production lines, 50 test lines. Range 1-2 h.
- **Split because:** the output side is a separate component pair and the scan is its independent gate.
- **Depends on:** T-031-17

### [x] T-031-20 — `POST /settings/refresh`: drop the cache, re-read, re-apply, pre-warm (3 h)
- [x] split the per-take settings reads in `listen.rs:238-248` into a pure `extract_voice_settings(&Value) -> VoiceSettings { model, prompt, voice, rate_percent, input_device, output_device }` and `apply_voice_settings(root, &VoiceSettings) -> Applied` (calls `stt::prefer_model`, `stt::prefer_prompt`, `tts::configure`, `devices::set_input/set_output`, reports what changed); `take_inner` uses the same pair, so there is one applier (D-7)
- [x] `bridge.rs`: authenticated `POST /settings/refresh` returns `{"applying": true}` **at once** and does `console_settings::forget()`, a fresh `console_settings::all(url)`, `apply_voice_settings`, and `stt::prewarm` when the model or prompt changed, on a short thread (D-15: the console's settings GET "stalls ~3 s one request in fifteen", `console_settings.rs:123-126`, and the bridge is single-threaded, `bridge.rs:199-204`; the console gives the poke 1 s). An unreachable console (settings `Null`) applies nothing rather than resetting every key to its default
- [x] add a read-only `stt::preferred_model()` getter for tests
- **Files may touch:** `desktop/src-tauri/src/listen.rs`, `desktop/src-tauri/src/bridge.rs`, `desktop/src-tauri/src/stt.rs` (getter only), `desktop/src-tauri/src/devices.rs` (only if needed to expose the preference getters)
- **Done-criteria:** RS `cargo test listen:: bridge:: devices:: -- --test-threads=1` then once in parallel: `test result: ok.` with at least 8 new tests: `extract_voice_settings` table (missing keys give `base.en`, blank voice, rate 100; values are trimmed; wake word and ticket prefix feed the prompt) (AC-42); `apply_voice_settings` reports `device_changed` only when a device name changed and the generation bumps once (AC-42); a `Null` settings object applies nothing; **loopback tests against a real `bridge::start` on a temp repo root** (a `TcpStream` helper that is reused by task 24): no token gives 401, a wrong token gives 401, the right token gives 200 with `applying: true` and the route returns in under 500 ms even when the console URL is unreachable (AC-42). `stt` and `listen` tests green. [HL] `/health` `stt_model` within 1 s is task 37 (AC-43).
- **Basis:** about 120 production lines, 170 test lines; the loopback test helper is new. Range 2.5-3.5 h.
- **Split because:** a different component (R4 bridge surface) and the first loopback-tested route; hard dependency of 21 and 24 (same file) and consumer of 04 and 16.
- **Depends on:** T-031-04, T-031-16

### [x] T-031-21 — `/speak` accepts per-request `voice` and `rate_percent` (1.5 h)
- [x] pure `speak_params(settings, body) -> (voice, rate)` in `tts.rs`: a non-blank `voice` and a numeric `rate_percent` in the body win, absent values come from settings (`speak_voice`, `speak_rate_percent`, default 100), the rate is clamped to 50-200; the unknown-voice fallback stays in `piper::voice`; nothing is saved (BR-13)
- [x] `bridge.rs` `/speak` arm uses it before `tts::configure`
- [x] `piper.rs`: a non-logging `voice_in_use(root, wanted) -> Option<String>` for caps (task 24) so `/health` polling does not repeat the fallback warning
- **Files may touch:** `desktop/src-tauri/src/tts.rs`, `desktop/src-tauri/src/piper.rs`, `desktop/src-tauri/src/bridge.rs` (the `/speak` arm only)
- **Done-criteria:** RS `cargo test tts:: piper:: bridge:: -- --test-threads=1`: `test result: ok.` with at least 5 new tests: overrides win over settings; absent overrides use settings; defaults when neither; an unknown voice falls back to the first sorted installed voice exactly as `piper::voice` does (temp dir with two fake `.onnx` files) (AC-47); `{voice}.onnx` and `{voice}.onnx.json` filename contract pinned (AC-2, RS half); `voice_in_use` does not log. [HW] that the preview is audibly the chosen voice and speed is task 39 (AC-48).
- **Basis:** about 40 production lines, 90 test lines. Range 1-2 h.
- **Split because:** a pure, independently verifiable resolver (AC-47) used by the console preview route; kept after 20 only because both edit `bridge.rs`.
- **Depends on:** T-031-20

### [x] T-031-22 — Mic test: `peak_of`, non-blocking 2 s test thread, guard, no audio kept (3 h)
- [x] new `desktop/src-tauri/src/voice_test.rs` (+ `mod voice_test;` in `main.rs`): `peak_of(&[i16]) -> f32` in 0..1 (`i16::MIN` maps to 1.0); `refuse_reason(listening, hands_free, already_running) -> Option<&str>`; `start_mic_test` returns **immediately** after starting a thread that opens a **fresh** `Mic` on the resolved input for 2.0 s, publishes `{running, peak, device}` and drives `audio::level()` for the live bar (`audio::set_level` becomes `pub(crate)`), then drops the device; peak only, samples are discarded per chunk and nothing is written to disk or sent (D-11, BR-15, NFR-10)
- [x] the thread body takes an injectable sample source and clock so it runs without hardware in tests
- **Files may touch:** `desktop/src-tauri/src/voice_test.rs` (new), `desktop/src-tauri/src/main.rs` (the `mod` line), `desktop/src-tauri/src/audio.rs` (`set_level` visibility only)
- **Done-criteria:** RS `cargo test voice_test:: audio:: -- --test-threads=1`: `test result: ok.` with at least 8 new tests: `peak_of` for empty, silence, +32767, `i16::MIN`, a half-scale tone (about 0.5 within 0.001) and a sweep proving the result is always within 0..1 (AC-60); `refuse_reason` table for listening, hands-free, already running and free (AC-61); with a fake source emitting a known ramp the reported peak equals the ramp's peak and `running` is false afterwards; `start_mic_test` returns in under 50 ms while the fake source blocks for 300 ms; the state JSON has exactly `running`, `peak`, `device` (plus `error` when a start failed); a start that fails to open reports the error text without panicking; a hardware-gated test (skipped loudly without an input device, single-threaded first) runs a real 2 s test and checks `peak` within 0..1. [HL] responsiveness during a real test and the "no audio file created" check are task 37 (AC-63); the bar tracking a real voice is [HW] (task 39).
- **Basis:** about 170 production lines, 150 test lines; thread and device lifecycle (memory `windows-native-threading-traps`: test single-threaded first). Range 2.5-3.5 h.
- **Split because:** a self-contained, parallelizable deliverable (R3) with its own concurrency and privacy obligations.
- **Depends on:** T-031-17

### [x] T-031-23 — Speaker test tone: renderer, fail-fast output resolution, mute bypass (1.5 h)
- [x] `voice_test.rs`: `tone_samples(rate)` two notes (about 250 ms each), 3 ms edge fades, peak at most 0.25; `speaker_test_with(resolve, play)` resolves the output **synchronously** (an unresolved or absent output returns an error naming the cause at once) and plays on a thread, **ignoring** the reply-mute switch (an explicit test)
- [x] `cue.rs`: extract the stream-and-hold part of `blow` into `play_buffer(device, config, samples)` with `blow` calling it (behaviour preserved), so the tone and the cues share one path
- **Files may touch:** `desktop/src-tauri/src/voice_test.rs`, `desktop/src-tauri/src/cue.rs`
- **Done-criteria:** RS `cargo test voice_test:: cue:: -- --test-threads=1`: `test result: ok.` with at least 5 new tests: at 44.1, 48 and 96 kHz the tone is finite, has a peak above 0.1 and at most 0.25, starts below 0.001, ends below 0.01, and lasts 400-800 ms (AC-64); an injected resolver that fails returns an error containing "output" and the player is never called; with `cue::set_muted(true)` the tone path still calls the player; all existing `cue` tests green. Audibility on a real device is [HW] (task 39, AC-65 audibility).
- **Basis:** about 60 production lines, 80 test lines. Range 1-2 h.
- **Split because:** a separate deliverable from the mic test (different device direction and files), and a refactor of `cue.rs` that needs its own regression check.
- **Depends on:** T-031-19, T-031-22

### [x] T-031-24 — Bridge routes and caps: `/audio/devices`, `/audio/test/*`, `/listen/state` fields (3 h)
- [x] `GET /audio/devices` returns `inputs`, `outputs`, `default_input`, `default_output`, and for each direction the verdict for the shell's **applied** preference (`configured`, `resolved`, `match`, `fallback`, `candidates`) from `devices::resolve_name`, so the matcher exists once (D-17); empty lists and no device never panic
- [x] `POST /audio/test/mic`: 409 with the refusal reason while a take or hands-free is active, otherwise starts the test and answers at once; `POST /audio/test/speaker`: synchronous resolve, 503 with the reason when unresolved, otherwise `{playing, device}`
- [x] extract the `/listen/state` JSON into `listen_state_json(root)` and add `mic_test` (from `voice_test`) and `swap_error` (from `stt`); `microphone` already reports the resolved device
- [x] `/health` caps gain `loaded_model` (`stt::loaded_model()`) and `speak_voice_in_use` (`piper::voice_in_use`)
- **Files may touch:** `desktop/src-tauri/src/bridge.rs`, `desktop/src-tauri/src/listen.rs` (a `#[cfg(test)]` setter for the listening flag only)
- **Done-criteria:** RS `cargo test bridge:: listen:: -- --test-threads=1` then once in parallel: `test result: ok.` with at least 8 new tests, using the loopback helper from task 20: `GET /audio/devices` returns 200 with `inputs` and `outputs` arrays (possibly empty) and two verdict objects, and 401 without the token (AC-49, route half); `POST /audio/test/mic` returns 409 with a reason while the test hook says a take is in progress, and 200 otherwise (AC-61, route level); `POST /audio/test/speaker` with no resolvable output returns 503 with a reason; `listen_state_json` has the keys `mic_test`, `swap_error`, `microphone`, `engine_running`, `model` (AC-39, field); `capabilities` includes `loaded_model` and `speak_voice_in_use` and the existing `capabilities_never_claim_what_is_not_built` stays green; plus one **[HL]-gated test** `live_swap_is_visible_in_listen_state` (AC-40): with the real engine, `prefer_model("base.en")`, transcribe `desktop/tests/fixtures/status-ticket-two.wav`, `prefer_model("tiny.en")`, wait (at most 30 s) until `loaded_model()` is `ggml-tiny.en.bin`, transcribe again, assert the transcript contains "status" and `listen_state_json(root)["model"] == "ggml-tiny.en.bin"`, print the swap time (recorded, not asserted); it **skips loudly** (`skipped: <reason>`, test passes) when the engine, either model or the fixture is absent, and task 37 runs it after installing `tiny.en` through the manager. `cargo build` succeeds (output pasted).
- **Basis:** about 130 production lines, 160 test lines. Range 2.5-3.5 h.
- **Split because:** the contract surface the console (task 25) is built against; independently reviewed as one route table.
- **Depends on:** T-031-04, T-031-16, T-031-21, T-031-22, T-031-23

### [x] T-031-25 — Console routes for devices, tests and preview (+ shell helpers) (3 h)
- [x] `native_bridge.py`: `audio_devices`, `mic_test`, `speaker_test` helpers (short timeouts, 2 s) and `speak(repo_root, text, voice=None, rate_percent=None)` extended **backward compatibly** (the payload gains `voice`/`rate_percent` only when given)
- [x] routes in `assistant_feature.apply()` (`ctx.get`/`ctx.post` only): `GET /api/assistant/voice/devices` (shell answer plus `configured` from settings; the verdict fields `resolved`, `match`, `fallback`, `candidates` come from the shell, never recomputed here, BR-6, D-17; shell down gives HTTP 200 `{ok:false, reason}`); `POST /api/assistant/voice/test/mic` and `.../test/speaker` (forward and return at once, no polling); `POST /api/assistant/voice/preview {voice?, rate_percent?}` (400 for `rate_percent` outside 50-200 or a voice that is not installed, blank voice allowed = automatic; speaks a fixed sample; **writes no setting**; `ok:false` + reason when the shell is down)
- [x] `GET /api/assistant/voice` already passes the shell's `/listen/state` through, so `mic_test` appears with no console code; pin it with a test
- [x] `voice_assets.installed_voices(repo_root)` helper for the preview validation; update the route-set assertion in `console/tests/test_plugins.py` again
- **Files may touch:** `console/server/native_bridge.py`, `console/server/features/assistant_feature.py`, `console/server/voice_assets.py` (helper only), `console/tests/test_plugins.py`, `console/tests/test_voice_devices_routes.py` (new), `console/tests/test_native_bridge.py` (new tests appended)
- **Done-criteria:** PY `console/tests/test_voice_devices_routes.py console/tests/test_plugins.py console/tests/test_native_bridge.py console/tests/test_assistant.py console/tests/test_voice_assets_routes.py`, at least 10 new tests with a fake bridge opener and no regressions: `GET devices` returns the documented shape and adds `configured` (AC-50); shell down returns 200 with `ok:false` and a reason (AC-50); the mic and speaker routes forward and return without waiting, and an unresolved output yields `ok:false` + reason (AC-62, AC-65); preview rejects 49, 201 and a non-numeric rate with 400, rejects an uninstalled voice with 400, forwards `voice` and `rate_percent` unchanged, and leaves the settings override file untouched (AC-46); preview with the shell down is `ok:false` (AC-46); the voice-state route returns a `mic_test` object from the fake shell (AC-62); the existing `speak` payload tests are unchanged and green; the updated route-set test passes.
- **Basis:** about 120 production lines, 200 test lines. Range 2.5-3.5 h.
- **Split because:** the console-side contract for the UI (S5), verified against a fake shell, independent of the shell build.
- **Depends on:** T-031-24, T-031-15

### [x] T-031-26 — UI: "(live)" / "(restart needed)" / "(next chat)" chips on every Assistant row (1.5 h)
- [x] `settings.js` `assistant()`: hold `applies` in a **closure variable set in `load()`** from `GET /api/assistant/settings` (do **not** read `d.applies` in `paint`: both repaint call sites, `load()` at the second `paint` and `save()`, pass objects that carry only `settings` and `backends`, so the chips would vanish on the second paint)
- [x] `row()` gains an optional fifth `key` argument; `toggle`, `field`, `choice` and the `roleRow` setrow pass their key; the chip text is only a label map (`live` to "(live)", `restart` to "(restart needed)", `next_chat` to "(next chat)") and the note is the tooltip; display-only rows with no `WRITABLE` key (effective route, voice panel, wake recorder, vision) get no chip; the page keeps **no list of its own** (AC-69)
- [x] first edit appends the T-031 block to `console/static/styles.css` (anchor comment `/* T-031 voice assets and devices */`) with the chip style; later UI tasks extend inside it
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (one appended block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied (only T-031 hunks; other tickets' hunks byte-identical, pasted `git diff --no-index --stat` line); `node --check console/static/settings.js` exits 0 when `node` exists (task 01 noted whether it does; otherwise "not run: no node"); checklist items UI-69a..c (chip on a live key, a restart key, a next-chat key, tooltip text from the server note) appended to progress.md for task 38 and left unticked; `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_plugins.py -q` still green (it checks `index.html`/`app.js` load order, which this task must not disturb).
- **Basis:** about 40 lines of JS and 8 of CSS; the cost is the re-read and diff discipline. Range 1-2 h.
- **Split because:** infrastructure every later UI row calls (hard dependency), and the first edit of the shared dirty files, so it gets its own diff check.
- **Depends on:** T-031-13

### [x] T-031-27 — UI: speech-model manager list, state, size, hint, licence, polling (3 h)
- [x] new inner function `assetManager()` after `voicePanel()` (anchor: its final `return row("Live", ...)`), shared `loadAssets()` fetch of `GET /api/assistant/voice/assets` (used again by tasks 29 and 30 so one request feeds all three pickers), rendered as a new group "Speech models and voices" inserted before the `"Hands-free"` group in `paint`
- [x] each row: name, kind (model or voice), state chip (`not_installed`, `partial`, `downloading`, `paused`, `retrying`, `verifying`, `installed`, `failed`), size (KiB/MiB/GiB from `size_bytes`), hint, licence (the ryan voice shows "CC BY-NC-SA 4.0, non-commercial"), "verified"/"not verified", "in use" marker, custom rows labelled; free disk space line; shell-down note; **1 s poll only while a job is active** (one timer per panel, cleared when idle, `C.get` is concurrency-gated, memory/gap G28)
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (inside the T-031 block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-27a..e appended to progress.md for task 38 (all 9 catalog rows plus custom files listed with state and size; hint and licence visible; no network request from the panel while idle; shell stopped shows the note, not an error box; ryan licence label); no other group's markup changed.
- **Basis:** about 130 lines of JS and 20 of CSS, no test harness; at the cap. Range 2.5-4 h; stop and `replan` if it will not fit.
- **Split because:** the read-only half of the manager UI; the action half (28) is separately reviewed.
- **Depends on:** T-031-14, T-031-26

### [x] T-031-28 — UI: manager actions, progress bar with ARIA, sentence errors (3 h)
- [x] buttons by state: Download (also resumes a partial or failed one), Pause, Resume, Cancel, Delete (disabled with the reason when in use or loaded; `window.confirm` first), Verify (for installed but not verified); each posts `{id}` only to `/api/assistant/voice/assets/<action>`
- [x] progress bar `role="progressbar"` with `aria-valuemin`, `aria-valuemax`, `aria-valuenow` and a text line (`NN%`, speed, time left); `eta` omitted when null (NFR-6, NFR-11)
- [x] failures show the server's sentence (disk full, upstream changed, checksum mismatch with expected/actual prefix, lock on delete), never a raw exception; the panel keeps polling only while a job is active
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (inside the T-031 block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-28a..f appended to progress.md for task 38 (start a real small download, watch the bar and its `aria-valuenow` in the DOM, pause then resume, cancel, delete, a refused delete shows the reason, a forced failure shows a sentence); no hash, URL or path is ever sent from the UI.
- **Basis:** about 140 lines of JS and 20 of CSS; at the cap. Range 2.5-4 h; stop and `replan` if it will not fit.
- **Split because:** the state-changing half of the manager UI with its own accessibility obligation (NFR-11).
- **Depends on:** T-031-27

### [x] T-031-29 — UI: `stt_model` becomes a picker over installed models (1.5 h)
- [x] replace the free-text `field(s, "stt_model", ...)` (the "Speech model" row in the Listening group) with a dropdown built from the shared `loadAssets()` result: installed models (catalog and custom) with size and an "in use" marker, a missing configured name kept visible as "NAME (not installed)", saved through the existing `save()` ("Saved" toast) with the "(live)" chip; server validation is unchanged (D-9)
- [x] the row hint no longer tells the reader to run `get-whisper.ps1` as the only path; it points at the manager above
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only). Shared dirty file: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-34a..d appended to progress.md for task 38 (only installed models are offered; sizes shown; the in-use one is marked; a configured but absent name shows "(not installed)"; choosing one shows "Saved" and the "(live)" chip) (AC-34).
- **Basis:** about 50 lines of JS. Range 1-2 h.
- **Split because:** an independently reviewed behaviour change to an existing row (AC-34), separate from the manager.
- **Depends on:** T-031-14, T-031-26, T-031-27 (uses the shared `loadAssets()` that task 27 introduces, CR-38)

### [x] T-031-30 — UI: voice picker, speed slider, Preview, OS-voice notice (2 h)
- [x] replace the free-text `speak_voice` field and the number `speak_rate_percent` field in the Voice group: dropdown over installed voices with first option "Automatic - first installed" (value `""`), a missing configured voice as "NAME (not installed)"; slider 50-200 (step 5) with a live number, saved on `change` (not on every `input`)
- [x] Preview button posts the **current control values** (saved or not) to `/api/assistant/voice/preview` and shows the server's sentence on failure; nothing is saved by previewing (BR-13)
- [x] when the shell reports `speak_backend` other than `piper` (from the assets response's `shell` object) the voice, slider and Preview are disabled with the reason "the OS voice is speaking: voice, speed and device choices do not apply" (D-5, AC-45)
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (inside the T-031 block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-45a..e appended to progress.md for task 38 (first option text; missing voice shown; slider moves 50 to 200 and saves once per release with the "(live)" chip; Preview sends the unsaved choice and leaves `console/.cache/assistant/settings.json` unchanged; disabled state and reason when piper is absent) (AC-45). Audibility is [HW] (task 39, AC-48).
- **Basis:** about 90 lines of JS, 10 of CSS. Range 1.5-2.5 h.
- **Split because:** an independently reviewed behaviour change to existing rows plus a new action (AC-45).
- **Depends on:** T-031-25, T-031-26, T-031-27 (uses the shared `loadAssets()` and the `shell` object from task 11, CR-38)

### [x] T-031-31 — UI: input and output device pickers, hot-plug refresh (2 h)
- [x] new group "Audio devices" inserted before the "Voice diagnostics" group: Microphone and Speaker rows; first option "System default (NAME)" (value `""`), then devices by name; an unresolved configured name shows "NAME (not connected)" plus the line "using NAME instead" from the shell's verdict (`fallback`); an ambiguous name shows the candidates; the console's `match` verdict is displayed, **not recomputed** (BR-6)
- [x] re-enumerates every 3 s **only while the group is visible** (the `IntersectionObserver` idiom of `voicePanel`) and on a Refresh button; a repaint is skipped while a select has focus or when the device list is unchanged, so the open dropdown is not closed under the user; disabled with the reason when the shell is down (NFR-9, FR-20)
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (inside the T-031 block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-59a..e appended to progress.md for task 38 (default option shows the real default's name; saving a choice shows "(live)"; a hand-edited unknown name shows "(not connected)" and the device in use; Refresh works; no polling when the group is scrolled out of view or the shell is down) (AC-59). A real plug or unplug within one poll is [HW] (task 39, NFR-9).
- **Basis:** about 110 lines of JS, 10 of CSS. Range 1.5-2.5 h.
- **Split because:** an independently reviewed UI behaviour with its own polling and focus rules (AC-59).
- **Depends on:** T-031-25, T-031-26

### [x] T-031-32 — UI: "Test microphone" and "Test speaker" controls (2 h)
- [x] in the "Audio devices" group: **Test microphone** posts to `/api/assistant/voice/test/mic`, then polls `GET /api/assistant/voice` (about every 250 ms, at most 4 s) and shows a level bar, the peak number and the device name until `mic_test.running` is false; **Test speaker** posts to `.../test/speaker`; buttons are disabled while running; a 409 ("stop listening first"), an unresolved device and any `ok:false` reason are shown as sentences (FR-23); the page says "if you heard nothing, check the output device above" because a script cannot hear
- [x] a small local `peakBar` helper (the existing `bar()` lives inside `voicePanel` and is left alone)
- **Files may touch:** `console/static/settings.js` (inside `assistant()` only), `console/static/styles.css` (inside the T-031 block). Shared dirty files: surgical edit only; never reformat; re-read before each edit.
- **Done-criteria:** snapshot-diff protocol satisfied; `node --check` exits 0 (or "not run: no node"); checklist items UI-66a..e appended to progress.md for task 38 (buttons disable while running; the bar moves while the mic test runs; starting it during a take or hands-free shows the 409 sentence; an unresolved output shows the reason) (AC-66). The bar tracking a real voice and the tone being audible are [HW] (task 39).
- **Basis:** about 80 lines of JS. Range 1.5-2.5 h.
- **Split because:** an independently reviewed UI behaviour (AC-66) that depends on both device pickers and the test routes.
- **Depends on:** T-031-25, T-031-31

### [x] T-031-33 — Docs and compatibility: READMEs, `assistant.toml` comments, Settings strings, text and dependency checks (2 h)
- [x] `console/README.md` (the voice section around lines 1010-1060): the Speech models manager, the catalog file and its refresh procedure (D-2: re-run the tree API, update commit and hashes in one reviewed change), the device pickers, the "(live)" flags; the two PowerShell scripts remain documented as optional on Windows and for the engines; `desktop/README.md`: new modules `devices.rs` and `voice_test.rs` in the table, the `/audio/*` and `/settings/refresh` routes, `get-whisper.ps1` row added to the layout table (FR-25, NFR-14)
- [x] `console/config/assistant.toml` comments for `speak_voice` and `stt_model` point at Settings first (the scripts second); no key or default changes beyond task 13
- [x] `console/tests/test_voice_docs.py` (new): text checks that README and `assistant.toml` mention the manager and `voice-assets.toml`, that `settings.js` contains "Speech models" and no longer contains the two old hint sentences ("Fetch one with desktop/get-whisper.ps1 -Model", "fetch one with desktop/get-piper.ps1" as the sole path) (AC-71); `Cargo.toml` `[dependencies]` names and versions equal a pinned list (captured from the unchanged file at the start of this task) and `console/requirements-dev.txt` equals its pinned lines (AC-73)
- **Files may touch:** `console/README.md`, `desktop/README.md`, `console/config/assistant.toml` (comments only), `console/tests/test_voice_docs.py` (new). `settings.js` is read, not edited, here (the hint text changed in tasks 29-30).
- **Done-criteria:** PY `console/tests/test_voice_docs.py console/tests/test_assistant_commands.py -q` at least 6 new tests pass: README and `assistant.toml` text checks (AC-71), Settings strings (AC-71), deps unchanged (AC-73), and the compatibility checks that script-placed files read `installed`/`verified:false` and that an absent device key means system default (AC-72, re-run of tasks 11 and 13 evidence by name). `git diff --stat -- desktop/src-tauri/Cargo.toml desktop/src-tauri/Cargo.lock console/requirements-dev.txt` is empty.
- **Basis:** about 120 lines of prose, 70 test lines. Range 1.5-2.5 h.
- **Split because:** documentation agreement (NFR-14) is independently reviewed and must follow the behaviour it describes.
- **Depends on:** T-031-14, T-031-25, T-031-29, T-031-30, T-031-32 (the old hint sentences leave `settings.js` in 29 and 30)

### [x] T-031-34 — `get-whisper.ps1:103`: fix the stale `desktop-listen-state` cite (one line) (0.5 h)
- [x] replace line 103, `Write-Host '  python console/kanban.py verb run desktop-listen-state'` (no such verb exists; `console/config/verbs.toml` lists only `desktop-windows`, `-monitors`, `-screenshot`, `-ocr`, `-clipboard-*`), with a line that names something that exists, for example `Write-Host '  Settings > Assistant > Voice diagnostics (shows the speech engine and the loaded model)'`; **ASCII only** (Windows PowerShell 5.1 mis-parses non-ASCII in script files, memory `tray-menu-automation`)
- **Exception recorded:** the frozen requirements say "no changes to the two .ps1 scripts"; this is a narrow one-line text fix by explicit user instruction (D-18). `get-piper.ps1` is not touched.
- **Files may touch:** `desktop/get-whisper.ps1` (line 103 only)
- **Done-criteria:** `git diff --stat -- desktop/get-whisper.ps1` shows `1 insertion(+), 1 deletion(-)` (pasted); `git diff --stat -- desktop/get-piper.ps1` is empty; a Grep for `desktop-listen-state` outside `knowledge-center/` returns no match; the script still parses (`powershell -NoProfile -Command "$e=$null; $null=[System.Management.Automation.Language.Parser]::ParseFile('desktop/get-whisper.ps1',[ref]$null,[ref]$e); $e.Count"` prints `0`); the file has no byte above 127 (pasted check). No `-WhatIf` or download run is needed.
- **Basis:** one line and four checks. Range 0.25-0.5 h.
- **Split because:** an explicit user-instructed exception to a frozen requirement, different file type and independently reviewable as a one-line diff.
- **Depends on:** T-031-01

### [x] T-031-35 — Verification: full pytest and CI-parity checks (1 h)
- [x] `PYTHONUTF8=1 python -m pytest -o addopts="" -q` (about 4 min; run it yourself, a delegated verifier stalled twice on the 600 s watchdog, memory `subagent-status-not-evidence`); then `python -m pytest desktop/tests -o addopts="" -q` (the CI desktop job's Python step) and `PYTHONUTF8=1 python console/kanban.py harness lint` (a CI job; no skill or agent changed, so it must still pass)
- **Files may touch:** none (record only)
- **Done-criteria:** the final pytest line is pasted: `passed` is at least the task-01 baseline plus 100 new tests (the Python tasks above add at least 101 named tests), and the failed list is a subset of the pre-existing failures recorded in task 01 (any **new** failure is a blocker routed to `fix`, not waved through); `desktop/tests` and `harness lint` results pasted; CI itself (ubuntu py3.11/3.13, Windows py3.14) is **not** run by the builder and is stated as such (NFR-8).
- **Basis:** two or three long commands, no code. Range 0.75-1.5 h.
- **Split because:** an independently reviewed verification gate (NFR-8) distinct from the per-task runs.
- **Depends on:** every Python-touching task (T-031-06 to 15, 25, 33) and T-031-34

### [x] T-031-36 — Verification: full `cargo test`, single-threaded first, and release build (1 h)
- [x] the RS command with no filter and `-- --test-threads=1`, then the same without the flag (parallel, as CI runs it); then `cargo build --release --manifest-path desktop/src-tauri/Cargo.toml` (as CI does, `verify.yml:147`)
- **Files may touch:** none (record only)
- **Done-criteria:** both `cargo test` runs end `test result: ok.` with 0 failed and a total of at least the task-01 baseline plus 75 (the Rust tasks add at least 81 named tests: 8, 3, 9, 3, 10, 7, 4, 2, 8, 5, 8, 5, 9 for tasks 02, 03, 04, 05, 16, 17, 18, 19, 20, 21, 22, 23, 24); `Finished` for the release build; the warning count is no higher than the task-01 baseline; `git diff --stat -- desktop/src-tauri/Cargo.toml desktop/src-tauri/Cargo.lock` is empty (no new dependency, AC-73, NFR-2); any failure is quoted from the output file, never inferred from an exit code. Linux and macOS are CI-only and not run here (stated).
- **Basis:** about 6-10 min of cargo time plus reading output. Range 0.75-1.5 h.
- **Split because:** an independently reviewed verification gate (NFR-8) distinct from the per-task runs.
- **Depends on:** every Rust-touching task (T-031-02 to 05, 16 to 24) and T-031-33

### [x] T-031-37 — Verification [HL]: headless run of the real shell and console on this machine (3 h)
- [x] snapshot `desktop/stt` and `desktop/tts` listings and the visible console-window list (`knowledge-center/artifacts/T-003/ticket-scripts/list-console-windows.ps1`) before; start the console (`python console/kanban.py serve`, only if not already serving) and the freshly built shell hidden; read `console/.cache/desktop/bridge.json` for the token (never print or copy the token into an artifact)
- [x] **manager end to end (internet):** `POST /api/assistant/voice/assets/download {"id":"tiny.en"}`, poll until `installed` with `verified:true`; independently hash the file with `hashlib` and compare with the catalog and with D-2 (record the SHA256 prefix and the seconds taken)
- [x] **AC-43:** `POST /api/assistant/settings {"stt_model":"tiny.en"}`, poll the bridge `/health` `caps.stt_model` until `ggml-tiny.en.bin`; record elapsed seconds (target 1 s; if the console's settings GET stalls the way `console_settings.rs:123-126` documents, repeat up to 3 times and report the stall honestly)
- [x] **AC-40:** run `live_swap_is_visible_in_listen_state` (task 24) with `--nocapture --test-threads=1`; it must **run, not skip**; record the printed swap time (recorded, not asserted)
- [x] **AC-49 (HL):** the bridge `GET /audio/devices` and the console `GET /api/assistant/voice/devices` list at least one input and one output including the OS defaults on this machine
- [x] **AC-63:** start the mic test via the console route; while it runs call `GET /listen/state` repeatedly (each answer under 500 ms); `mic_test.running` is false within 5 s (amended from 3 s by D-20; measured 2.69-3.26 s); `peak` is within 0..1; `device` equals the resolved input; no `*.wav`, `*.raw` or `*.pcm` created after the start (compare listings under `console/.cache` and `desktop`)
- [x] **cleanup:** delete `tiny.en` through the manager (this also proves Delete on a real file, AC-27) so `desktop/stt` matches the task-01 listing (otherwise the existing fixture test's smallest-first fallback would pick `tiny.en`); stop only the processes this task started; confirm no new visible console window
- **Files may touch:** none in the product tree (a scratch script in the session scratchpad is allowed); evidence goes to progress.md
- **Done-criteria:** progress.md holds, for each item above, the command, the observed value and pass or fail, with real numbers (download seconds, hash prefix, AC-43 elapsed, swap seconds, listen/state latencies, peak). Items that cannot run (no internet, no engine, no mic) are recorded as **not run, with the reason**, never as passed. Hardware-dependent claims (bar tracks a voice, audibility) are not made here.
- **Basis:** a 78 MB download and an engine start dominate; scripting the checks about 1 h. Range 2.5-4 h (cap; stop and `replan` if it will not fit).
- **Split because:** an independently reviewed integration gate on the real artifacts (E2E, external system).
- **Depends on:** T-031-35, T-031-36

### [ ] T-031-38 — Verification [UI]: manual browser checklist (2 h)
- [ ] serve the console; in a browser open Settings, Assistant; walk the checklist items UI-27*, UI-28*, UI-34*, UI-45*, UI-59*, UI-66*, UI-69* collected in progress.md by tasks 26-32, plus two cross-checks: the other Settings panels (including the onboarding-related ones) still render and `node --check` passes; and no panel request fires while the manager and device groups are idle or scrolled out of view
- [x] DOM check of the progress bar attributes (`role`, `aria-valuenow`) during a real small download (seen 2026-10-05, see progress.md T-031-38 entry; the checklist box above stays open: 9 items partial / NOT RUN)
- **Files may touch:** none (record only)
- **Done-criteria:** each checklist item is marked pass, fail or **not run** in progress.md with a one-line observation. If the builder has no browser, every item is recorded "not verified in a browser" and handed to the owner as a list; nothing is ticked on the strength of reading the code. Failures route to `fix`.
- **Basis:** about 35 observations at 3 minutes each plus fixes routed out. Range 1.5-3 h.
- **Split because:** an independently reviewed manual gate (no JS test harness exists, so [UI] ACs are manual by definition).
- **Depends on:** T-031-32, T-031-37

### [x] T-031-39 — Verification [HW]: hardware hand-off list, explicitly not verified (0.5 h)
- [x] add a "Manual / hardware - NOT verified on hardware" table to `T-031-verification.md` (the verifier owns the rest of that file) with one row per item and the exact human steps: HW-1 preview audibly uses the chosen voice and speed (AC-48); HW-2 two physical inputs: selecting one changes the source, unplugging the chosen one shows "(not connected)" while capture continues on the default (AC-58); HW-3 plug or unplug is reflected within one poll, at most 5 s (AC-59, NFR-9); HW-4 the mic-test bar tracks a real voice (AC-63, second half); HW-5 the speaker tone is audible on the chosen output (AC-65, audibility); HW-6 armed hands-free reopens on the new input after a change (AC-56, real device); HW-7 small.en and medium.en swap time and memory (NFR-7, unmeasured); HW-8 Linux and macOS enumeration and the engine-by-hand path (unverified off Windows)
- **Files may touch:** `knowledge-center/artifacts/T-031/T-031-verification.md` (that table only)
- **Done-criteria:** the table exists with all eight rows, each status "NOT verified on hardware" (or "unmeasured" / "unverified off Windows"), each with owner steps; no row is ticked; the summary and the final report to the user repeat that these were not verified. No test or script pretends to cover them.
- **Basis:** writing only. Range 0.25-0.75 h.
- **Split because:** hardware items are a different actor (a person with a second device); they are tracked, not claimed (user instruction).
- **Depends on:** T-031-38

## Effort

Hours are builder hours (one builder who can run commands) in the skill's 0.5 / 1 / 1.5 / 2 / 3 h buckets; the Basis column gives the unit of work; ranges and PERT are below. The table sums to the task estimates ([[T-031-task-breakdown]] has the same numbers).

| Task | Estimate | Basis |
|------|----------|-------|
| T-031-01 — Step zero: ticket in-progress, baselines | 0.5 h | two long commands, no code |
| T-031-02 — `ensure()` model-compare fix | 2 h | ~70 prod + 120 test lines, ~6 cargo cycles |
| T-031-03 — engine slot seam | 2 h | ~120 lines refactor, trait objects |
| T-031-04 — mutex-free live swap (MANDATORY) | 3 h | ~220 prod + 200 test lines, concurrency tests |
| T-031-05 — truthful hint | 1 h | ~25 prod + 60 test lines |
| T-031-06 — catalog + loader + tests | 3 h | ~150 py + 140 toml + 150 test lines |
| T-031-07 — transfer core + range server | 3 h | ~170 + 150 helper + 150 test lines |
| T-031-08 — retry/backoff + URL policy | 3 h | ~130 prod + 200 test lines |
| T-031-09 — verify + atomic install | 3 h | ~150 prod + 220 test lines, fault matrix |
| T-031-10 — job manager | 3 h | ~200 prod + 220 test lines, threads |
| T-031-11 — inventory | 3 h | ~150 prod + 200 test lines |
| T-031-12 — delete | 2 h | ~90 prod + 130 test lines |
| T-031-13 — settings keys + `APPLIES` | 2 h | ~80 prod + 150 test lines |
| T-031-14 — asset routes + audit | 2 h | ~110 prod + 180 test lines |
| T-031-15 — refresh poke helper | 1.5 h | ~40 prod + 100 test lines |
| T-031-16 — `devices.rs` core | 3 h | ~220 prod + 180 test lines |
| T-031-17 — resolver + capture | 3 h | ~150 prod + 120 test lines |
| T-031-18 — reopen loops | 2 h | ~60 prod + 80 test lines |
| T-031-19 — playback + scan | 1.5 h | ~25 prod + 50 test lines |
| T-031-20 — `/settings/refresh` | 3 h | ~120 prod + 170 test lines, loopback harness |
| T-031-21 — `/speak` overrides | 1.5 h | ~40 prod + 90 test lines |
| T-031-22 — mic test | 3 h | ~170 prod + 150 test lines, thread |
| T-031-23 — speaker tone | 1.5 h | ~60 prod + 80 test lines |
| T-031-24 — bridge routes + caps | 3 h | ~130 prod + 160 test lines |
| T-031-25 — console devices/tests/preview routes | 3 h | ~120 prod + 200 test lines |
| T-031-26 — UI chips | 1.5 h | ~40 js + 8 css lines, diff discipline |
| T-031-27 — UI manager list | 3 h | ~130 js + 20 css lines |
| T-031-28 — UI manager actions | 3 h | ~140 js + 20 css lines |
| T-031-29 — UI model picker | 1.5 h | ~50 js lines |
| T-031-30 — UI voice picker/slider/preview | 2 h | ~90 js + 10 css lines |
| T-031-31 — UI device pickers | 2 h | ~110 js + 10 css lines |
| T-031-32 — UI test controls | 2 h | ~80 js lines |
| T-031-33 — docs + text checks | 2 h | ~120 prose + 70 test lines |
| T-031-34 — `.ps1` one-line fix | 0.5 h | one line, four checks |
| T-031-35 — full pytest | 1 h | ~4 min runs + CI-parity |
| T-031-36 — full cargo test + release build | 1 h | 6-10 min cargo |
| T-031-37 — headless [HL] run | 3 h | 78 MB download, engine start, scripting |
| T-031-38 — UI manual checklist | 2 h | ~35 observations |
| T-031-39 — [HW] hand-off list | 0.5 h | writing |
| **Total (39 tasks)** | **83.5 h** | sum of the rows |

**By layer (for `estimate(mode=forecast)`):** data 3.0 (06) · service 55.0 (02-05, 07-25 excluding 06 and the UI) · UI 15.0 (26-32) · docs and process 3.5 (01, 33, 34, 39) · E2E 7.0 (35-38). 3.0 + 55.0 + 15.0 + 3.5 + 7.0 = 83.5.

**PERT** with the skill's layer multipliers (O = 0.7 M, P = M x multiplier: data 1.35, service 1.25, UI 1.20, docs 1.10, E2E 1.50): expected 82.9 h, optimistic 58.5 h, pessimistic 105.2 h. **Confidence Low:** no recorded actuals exist in the vault to calibrate against, and five unmeasured items sit on the path (swap time and memory for small.en and medium.en, cpal enumeration on the bridge thread, the Windows cargo cycle time, non-Windows behaviour, the console's settings-stall frequency). **Envelope:** the upfront estimate ([[T-031-effort-estimate]]) gives development 132.4 h [92.9, 166.0] on the skill's untuned human-team table; this plan is 63% of that and 10.1% under its lower bound, accepted with rationale as CR-23. QC (verifier stage, 72.7 h derived) is not in this total. **Forecast checkpoints:** `estimate(mode=forecast)` after task 05, then at the end of each phase; `replan` if variance exceeds 25%.

### Acceptance criterion coverage

73 of 73 acceptance criteria are mapped to at least one task; no AC is unmapped. "E" = tasks that build or enable it, "V" = tasks that verify it. [HW] criteria are mapped to task 39 as **manual, NOT verified on hardware** items and have no automated test pretending to cover them; [UI] criteria are verified manually in task 38.

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| AC-1 [PY] catalog fields | 06 |
| AC-2 [PY][RS] filename contract both sides | 06 (PY), 02 (`ggml-{name}.bin`), 21 (`{voice}.onnx`, `.onnx.json`) |
| AC-3 [PY] size_bytes, hint, licence | 06 |
| AC-4 [PY] empty dirs | 11 |
| AC-5 [PY] installed/verified/partial | 11 |
| AC-6 [PY] custom rows | 11 |
| AC-7 [PY] in_use, loaded, shell down, 1.5 s | 11 |
| AC-8 [PY] no outbound call | 11 |
| AC-9 [PY] full download states | 10 |
| AC-10 [PY] progress cadence | 10 |
| AC-11 [PY] second Download same job | 10 |
| AC-12 [PY] ids only | 14 |
| AC-13 [PY] Range header | 07 |
| AC-14 [PY] backoff delays | 08 (table + loop; see CR-21) |
| AC-15 [PY] 200 on Range | 07 |
| AC-16 [PY] 6 failures, 404, 429/503 | 08 |
| AC-17 [PY] upstream changed | 07 |
| AC-18 [PY] pause | 10 |
| AC-19 [PY] cancel | 10 |
| AC-20 [PY] restart recovery | 10 |
| AC-21 [PY] hash mismatch | 09 |
| AC-22 [PY] fault matrix | 09 (files), 11 (installed/unverified state) |
| AC-23 [PY] voice order | 09 |
| AC-24 [PY] Verify | 09 |
| AC-25 [PY] 8 MiB memory | 07 |
| AC-26 [PY] hashes equal real files; online opt-in | 06 (V run once), 37 |
| AC-27 [PY] delete | 12 (V on a real file in 37) |
| AC-28 [PY] refusals, OS lock | 12 |
| AC-29 [PY] name validation | 12 |
| AC-30 [PY] disk space | 09 |
| AC-31 [PY] URL policy | 08 |
| AC-32 [PY] write error | 09 |
| AC-33 [PY] audit | 14 |
| AC-34 [UI] model picker | 29 (E), 38 (V) |
| AC-35 [RS] staleness table | 02 |
| AC-36 [RS] `model_file`, warn once | 02 |
| AC-37 [RS] one replacement, old killed after | 04 |
| AC-38 [RS] readers under 100 ms | 04 |
| AC-39 [RS] failed replacement | 04, 24 (`swap_error` field) |
| AC-40 [HL] live swap with a real engine | 24 (test), 37 (run) |
| AC-41 [PY] poke from `settings_post` | 15 |
| AC-42 [RS] refresh route, pure re-apply, generation | 20 |
| AC-43 [HL] `/health` within 1 s | 20 (E), 37 (V) |
| AC-44 [RS] truthful hint | 05 |
| AC-45 [UI] voice picker, slider | 30 (E), 38 (V) |
| AC-46 [PY] preview validation | 25 |
| AC-47 [RS] speak resolver | 21 |
| AC-48 [HW] preview audibly the chosen voice | 21, 25, 30 (E); 39 (manual, NOT verified on hardware) |
| AC-49 [RS][HL] enumerate | 16 (RS), 24 (route), 37 (HL) |
| AC-50 [PY] devices route | 25 |
| AC-51 [PY] device keys | 13 |
| AC-52 [RS] matcher table | 16 |
| AC-53 [RS] direction safety | 16 |
| AC-54 [RS] one `default_*_device` site | 19 |
| AC-55 [RS] fallback, single warning | 17 |
| AC-56 [RS] reopen on change | 16 (pure), 18 (loops) |
| AC-57 [RS] "microphone" text, resolved name | 17 |
| AC-58 [HW] two inputs, unplug | 17, 18 (E); 39 (manual, NOT verified on hardware) |
| AC-59 [UI] device pickers | 31 (E), 38 (V); plug/unplug within a poll is 39 (HW) |
| AC-60 [RS] `peak_of` | 22 |
| AC-61 [RS] mic-test guard | 22, 24 (route 409) |
| AC-62 [PY] mic route, `mic_test` in state | 25 |
| AC-63 [HL] responsiveness, no audio file | 22 (E), 37 (V); bar tracks a voice is 39 (HW) |
| AC-64 [RS] tone | 23 |
| AC-65 [PY] speaker route | 25; audibility is 39 (HW) |
| AC-66 [UI] test controls | 32 (E), 38 (V) |
| AC-67 [PY] every key has `APPLIES` | 13 |
| AC-68 [PY] settings GET returns `applies` | 13 |
| AC-69 [UI] chips | 26 (E), 38 (V) |
| AC-70 [PY] SHOULD source scan | 13 |
| AC-71 [PY] text checks | 33 |
| AC-72 [PY] compat | 11 (files), 13 (keys), 33 |
| AC-73 [PY] deps unchanged | 33, 36 |

**Functional requirements:** FR-1 06 · FR-2 11 · FR-3 10 · FR-4 07, 08 · FR-5 10 · FR-6 09 · FR-7 12 · FR-8 08, 09, 14 · FR-9 29 · FR-10 02 · FR-11 03, 04 · FR-12 15, 20 · FR-13 05 · FR-14 30 · FR-15 21, 25, 30 · FR-16 16, 24, 25 · FR-17 13 · FR-18 16 · FR-19 17, 18, 19 · FR-20 31 · FR-21 22, 24, 25, 32 · FR-22 23, 24, 25, 32 · FR-23 32 · FR-24 13, 26 · FR-25 33, 34. All 25 covered.

**Non-functional requirements:** NFR-1 09 · NFR-2 33, 36 · NFR-3 08, 12, 14 · NFR-4 11, 14 · NFR-5 07 · NFR-6 10, 27, 28 · NFR-7 04, 37, 39 · NFR-8 35, 36 (CI itself not run by the builder) · NFR-9 31, 39 · NFR-10 22, 37 · NFR-11 27-32, 38 · NFR-12 11, 13, 33 · NFR-13 10, 17 · NFR-14 33. All 14 covered.

**Business rules:** BR-1 10, 14 (no download without a click: no startup hook is added) · BR-2 09 · BR-3 06 · BR-4 02 · BR-5, 6 16, 17 · BR-7 12 · BR-8 11 · BR-9 14 · BR-10 08 · BR-11 14 · BR-12 07-10 (ported mechanics, stdlib only) · BR-13 21, 25, 30 · BR-14 20 · BR-15 22.

## Risks

Likelihood and impact are low / med / high. Every row has a mitigation and a source; none is left without one. One row is high x high (R-4) and is mitigated.

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| R-1 `console/kanban.py context` and other CLI calls crash on a cp1252 console (`→` in output) | High | Low | every `kanban.py` call uses `PYTHONUTF8=1`; the crash itself is a separate existing task and is not fixed here; a CLI failure is read as this known issue only after confirming the traceback | Builder | context snapshot Source Log; brief |
| R-2 `cargo` cannot compile without the MSVC environment, and piped cargo reports a false exit 1 | High | Med | source `desktop/msvc-env.ps1` first; read the output file for `test result:` / `Finished`, never the exit code; task 01 runs the first cargo build so a broken toolchain shows before 80 h depend on it | Builder | memory `building-the-rust-shell` |
| R-3 Single-threaded bridge: a blocking route or a swap under the engine lock freezes `/state`, `/health`, `/listen/state` | Med | High | swap never holds `ENGINE` across the start and is proven by a test (04); mic test and refresh return at once (20, 22); loopback tests assert sub-500 ms answers (20, 24); HL checks `/listen/state` latency during a real test (37) | Builder | analysis finding 2; `bridge.rs:199-204`; gap G24 |
| R-4 Settings reach the shell up to 30 s late, and never in armed hands-free, so "(live)" is false | High | High | refresh poke (15, 20) drops the cache and re-applies at once; mic reopens on a preference change (18); keys that really need a restart are flagged "(restart needed)" (13, 26); the `restart` classification is source-scanned (13, AC-70) | Builder | CR-8; `console_settings.rs:132`; `hands_free.rs:313-357` |
| R-5 Native threading traps: concurrent OS resource use corrupts the heap (clipboard and WinRT precedents) | Med | High | Rust tests run `-- --test-threads=1` first; the mic test opens its own `Mic` on its own thread and never shares the cached one; hardware-gated tests skip loudly; tests build their own `Prefs` and `EngineSlot` instead of sharing statics | Builder | memory `windows-native-threading-traps` |
| R-6 Shared dirty files (`settings.js`, `styles.css`) carry other tickets' uncommitted work; a clobber cannot be recovered without a commit | Med | High | surgical `Edit` only, no whole-file write, re-read before each edit, scratchpad snapshot and `git diff --no-index` after each UI task, no stash/checkout/`git add`; onboarding files and `audit.py` are not touched; CSS is one appended block | Builder | git status; analysis; brief |
| R-7 Hugging Face unreachable, rate-limited, or a pinned commit removed | Low | Med | commit-pinned URLs + SHA256; resume and backoff with 429/5xx retry (08); hand placement plus Verify (09); opt-in online check (06); catalog refresh procedure documented (33); CR-11 accepted single host | Builder | decision log D-2; gap G22 |
| R-8 Two engines (old and new model) resident during a swap; small.en and medium.en memory unmeasured | Med | Med | the swap starts only when the preference changes; the old process is killed as soon as the new one answers; failed model is not retried per take (04); measurement listed as HW-7 (39), not claimed | Builder | decision log D-6.6 |
| R-9 A delegated builder or verifier mis-reports state | Med | High | every task closes with the named files present, `git status`, and a test count from a command the builder ran; `progress-tracker` entries must cite the count; full-suite runs (35, 36) are run directly | Builder | memory `subagent-status-not-evidence` |
| R-10 cpal enumeration from the bridge thread is untested; non-Windows device lists are noisy and unverified | Med | Med | `enumerate()` is defensive and never panics (16); tested for no panic with zero devices (CI has none); HL on Windows (37); non-Windows labelled unverified (39) | Builder | context snapshot §6; gap G16 |
| R-11 Rust and Python tests that pass on Windows fail on the ubuntu/macOS CI (hint wording, no audio device, py3.11 vs 3.14) | Med | High | per-OS hint assertions (05); hardware-gated tests skip, never fail; no hardware or internet in default tests; CI is **not** run by the builder, so a CI-only failure is a residual risk stated in the final report | Builder | CR-24; memory `cross-platform-defects-only-ci-finds` |
| R-12 AC-43 (1 s) flakes when the console's settings GET stalls (about 1 request in 15) | Med | Low | the refresh route answers at once and re-applies on a thread; HL repeats up to 3 times and reports a stall rather than hiding it | Builder | `console_settings.rs:123-126` |
| R-13 A task overruns its bucket; sixteen sit at the 3 h cap | Med | Med | cap rule: stop and `replan`; forecast after task 05 and each phase | Builder | CR-34 |
| R-14 Pre-existing failures from other tickets' dirty tree are mistaken for T-031 regressions | Med | Med | task 01 records baseline failures; 35 and 36 compare against them | Builder | git status |
| R-15 The existing fixture test picks the smallest model once `tiny.en` is installed next to `base.en` | Low | Low | task 37 deletes `tiny.en` through the manager after the proof (which also proves Delete); `desktop/stt` is compared with the task-01 listing | Builder | `stt.rs:593-625` |
| R-16 AC-14 (seven delays) and AC-16 (six failures) disagree by one in the frozen requirements | Med | Low | the delay function is tested as a table (AC-14 literally) and the loop as Mic Drop's six sleeps then fail (AC-16, D-4); owner may `evolve` AC-14 | Builder | CR-21 |

## Dependencies
- **Blocks:** [[T-034-summary]] (wizard Voice step, doctor, tray submenus consume this ticket's routes and keys); [[T-032-summary]] is related, not blocked.
- **Blocked by:** none. Requirements are frozen (iteration 2) and Q1 and Q2 are resolved by the user (decision log D-3, D-12).
- **Task-level chains:** [[T-031-components]] § Critical path (35.0 h through the asset engine into the manager UI), and the same-file ordering rule in [[T-031-task-breakdown]] § Conventions.

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-progress]] · [[T-031-verification]] · [[T-031-release]]
- [[INV-2026-10-05-micdrop-adoption-dossier]] · [[T-034-summary]] · [[T-032-summary]]

