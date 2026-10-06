---
ticket: "T-031"
artifact: requirements-draft
status: frozen
freeze_status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 2
iteration: 2
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Requirements Draft: T-031

> Requirements draft. **Frozen 2026-10-05 at iteration 2** — see [[T-031-requirements]]; further change only through `evolve`.

**Command reference:**
- **Created by:** `requirements T-031 draft`
- **Grounded by:** `analyze T-031` → writes `T-031-context-snapshot.md`
- **Gaps surfaced by:** `challenge-requirements T-031 (gaps dimension)`
- **Challenged by:** `challenge-requirements T-031` (adds ⚠ markers below)
- **Enriched by:** `requirements T-031 enrich [source]`
- **Cross-checked by:** `challenge-requirements T-031 (overlap/conflict/reuse dimension)`
- **Iterated by:** `requirements T-031 iterate "feedback"`
- **Frozen by:** `requirements T-031 freeze` → produces `T-031-requirements.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default.

**Business driver:** Foundation ticket of the Mic Drop adoption ([[INV-2026-10-05-micdrop-adoption-dossier]]); T-034 (wizard Voice step, doctor, tray submenus) depends on its downloads, device pickers and mic test.

**Raw intent verbatim:**
> Foundation ticket of the Mic Drop adoption: let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default. Scope: A1 model manager (catalog, installed/size/in-use, download · pause · resume · cancel · delete, progress/speed/ETA) · A2 resumable downloads (`.part` + Range, backoff, marker-last, SHA256 verify) · A3 picker over installed models + live swap, including the `stt.rs` `ensure()` fix (it compares only `engine.prompt`, never `engine.model`) · A4 size/quality hints (tiny ~100 MB … medium ~950 MB) · A5 voice picker + preview + speed slider · B1 input/output device pickers by name with hot-plug refresh · B2 mic test + speaker test tone · D4 "(live)" / "(restart needed)" flags on Settings keys. Decision: the downloader lives in the console (Python), not the shell, and writes into `desktop/stt/` and `desktop/tts/`; the shell only reports installed assets through the existing bridge `/health` caps. Out of scope: sherpa-onnx, Kokoro, cloud engines, GPU select, the wizard Voice step (T-034), endpointing (T-032). ([[T-031-summary]], dossier §2/§4, analyst brief 2026-10-05)

## 2. Context Summary

(Condensed from [[T-031-context-snapshot]])

- **Similar existing features:** whisper engine in `stt.rs`; installed voices already in `/health` caps (`speak_voices`, unconsumed); settings schema `assistant_config.py`; bridge client `native_bridge.py`; `voicePanel()` in `settings.js`; `cue.rs` tones; Windows scripts `get-whisper.ps1`/`get-piper.ps1`.
- **Affected code areas:** shell (`stt.rs`, `audio.rs`, `piper.rs`, `cue.rs`, `listen.rs`, `hands_free.rs`, `bridge.rs`, `console_settings.rs`); console (`voice_assets.py` new, `assistant_config.py`, `assistant_feature.py`, `native_bridge.py`, `config/`); UI (`settings.js` `assistant()`).
- **Known risks from history:** engine start under a mutex on a single-threaded bridge; settings cache (30 s); cross-platform defects only CI finds; shared dirty files.

## 3. Scope

### In scope
- Model and voice manager in Settings → Assistant (A1, A4), resumable verified downloads written by the console (A2).
- Installed-model picker, live model swap and the `ensure()` fix (A3); voice picker, preview, speed slider (A5).
- Input/output device pickers by name with hot-plug refresh (B1); mic test and speaker test tone (B2).
- Per-key "(live)" / "(restart needed)" flags (D4).
- The bridge `/health` caps and routes these need.

### Out of scope (explicit)
- sherpa-onnx, Kokoro, cloud engines, GPU select — per brief.
- Wizard Voice step, doctor actions, tray device submenus — T-034.
- Endpointing, junk filter, wav-replay seam — T-032.
- Engine binaries (`whisper-server`, `piper`): not downloaded by T-031 (default, Q1 open; [[T-031-decision-log]] D-3). On Linux/macOS a model download therefore does not by itself enable listening; the hint says so.
- Changes to `get-whisper.ps1` / `get-piper.ps1`, quantised or multilingual models, additional voices beyond the five, a CLI downloader.
- Detecting a microphone that disappears during a hands-free session (unchanged from today; recorded as G13).

### Assumptions
(Iteration 1-2: each resolved by a grounded fact or a recorded default; none is silent.)
- A-1 (was: installed list from `/health` caps) -> console scans the two directories for existence and verification; shell caps supply usable/loaded/resolved. Refines the approved wording; D-1. **Flag for the owner.**
- A-2 (was: brief's "tiny ~100 MB … medium ~950 MB") -> catalog byte sizes (tiny.en 77,704,715 · base.en 147,964,211 · small.en 487,614,201 · medium.en 1,533,774,781); D-13.
- A-3 (was: blocking 2 s mic test) -> non-blocking start + polled result; D-11.
- A-4 Catalog = the models and voices the two scripts offer; D-3, licences D-12 (Q2).
- A-5 Absent configured device -> fall back to the system default, warn, report `fallback`; D-5.
- A-6 Engine binaries are not part of the model manager; D-3 (Q1).
- A-7 Settings changes reach the shell through a refresh poke; D-7.
- A-8 A third flag value "(next chat)" in addition to "(live)" and "(restart needed)"; D-8.

## 4. Functional Requirements

Number each `FR-{n}`. Each must be independently verifiable.

Verification tags: **[PY]** pytest, no internet, no hardware (local range-capable `http.server`, fake bridge opener, tmp dirs) · **[RS]** `cargo test`, no audio hardware · **[HL]** headless run of the real shell/console on this Windows machine, no human (may use the internet, e.g. to install `tiny.en`) · **[UI]** manual browser check (the repo has no JS test harness) · **[HW]** needs a person or a second physical device: *not verified on hardware* until someone does it.

#### Assets (console, Python)

### FR-1: Catalog (A1, A4)
**Description:** A committed catalog `console/config/voice-assets.toml` lists exactly 4 STT models (`tiny.en`, `base.en`, `small.en`, `medium.en`) and the 5 voices `get-piper.ps1` offers. Each file has a commit-pinned https URL, byte size and SHA256 with its provenance; each entry has a display name, a one-line quality hint and (voices) a licence string. Values are those in [[T-031-decision-log]] D-2/D-12.

**Actor:** Maintainer (reviewed change); console (reader).

**Acceptance criteria (testable):**
- [ ] AC-1 [PY] The catalog loads; every file has an `https://huggingface.co/...` URL pinned to a 40-hex commit, `size_bytes` > 0, a 64-hex `sha256`, `hash_source` in {`hf-lfs-oid`, `computed-pinned`} (the latter also carries `git_blob_sha1`), and a name matching `^[A-Za-z0-9._-]+$`. An entry without a hash fails the test.
- [ ] AC-2 [PY][RS] Shell filename contract: STT file is `ggml-{name}.bin`, voice is `{voice}.onnx` + `{voice}.onnx.json`. Python asserts the catalog follows it; a Rust test asserts `model_file` resolves `ggml-tiny.en.bin` and `piper::voices` lists `{voice}` from `{voice}.onnx` in a temp dir.
- [ ] AC-3 [PY] The API returns `size_bytes`, `hint` and (voices) `license` per entry; no hint contains a literal size that differs from `size_bytes` (the dossier's "950 MB" must not appear).

**Business rules invoked:** BR-3, BR-9, BR-12

### FR-2: Inventory and state (A1)
**Description:** `GET /api/assistant/voice/assets` returns, for each catalog entry and each unlisted model/voice file found on disk, its state, size on disk, whether it is verified, whether it is in use or loaded, any job progress, and free disk space. States: `not_installed`, `partial`, `downloading`, `paused`, `retrying`, `verifying`, `installed`, `failed`. Installed state comes from the console's own scan of `desktop/stt` and `desktop/tts`; the shell's `/health` caps add what it can use and what is loaded. It works with the shell down. A `failed` job keeps its reason until the next Download of that asset; after a console restart a failed asset reads `partial` if a `.part` was kept, else `not_installed`.

**Actor:** Console UI.

**Acceptance criteria (testable):**
- [ ] AC-4 [PY] With both directories empty or absent every catalog entry is `not_installed`, `free_bytes` is present, status 200.
- [ ] AC-5 [PY] Final file + valid manifest -> `installed`, `verified: true`; final file without a manifest (hand-installed) -> `installed`, `verified: false`; only `{final}.part` -> `partial` with its byte count; a manifest whose sha256 differs from the catalog -> `verified: false`.
- [ ] AC-6 [PY] A `ggml-*.bin` or `*.onnx` not in the catalog is listed `custom: true` with its size, selectable and deletable; `.part`, `.manifest.json`, `.onnx.json` and non-model files (`*.dll`, `*.ort`, directories) are not listed.
- [ ] AC-7 [PY] `in_use` = configured (a blank `speak_voice` resolves to the first sorted installed voice, as `piper.rs:79-86`) and `loaded` = reported by the shell. With the shell unreachable: status 200, `shell.reachable: false`; the bridge call timeout is at most 1.5 s (asserted on the fake opener).
- [ ] AC-8 [PY] The endpoint makes no outbound internet call (`urlopen` patched to raise for non-loopback hosts; response still 200).

**Business rules invoked:** BR-1, BR-8

### FR-3: Download (A1, A2)
**Description:** `POST .../assets/download {id}` starts a background download of one catalog entry and returns its job at once. Progress reports `state`, `done`, `total`, `speed_bps`, `eta_s`, `resumed_from`, `file`; for a voice, `done` and `total` cover both of its files.

**Actor:** Console user.

**Acceptance criteria (testable):**
- [ ] AC-9 [PY] Against a local range-capable server, the file lands byte-identical at its final name with its manifest, no `.part` remains, and the observed states include `downloading` -> `verifying` -> `installed`.
- [ ] AC-10 [PY] While a slow server streams, `done` is non-decreasing and refreshed at least every 500 ms; `speed_bps` > 0; `eta_s` is null when speed is 0.
- [ ] AC-11 [PY] A second Download for an asset that already has an active job returns that job; the server sees one non-Range transfer, not two.
- [ ] AC-12 [PY] An unknown `id` is refused ("not in the catalog") with no network call; a body carrying `url`, `path`, `file` or `filename` has no effect (a URL pointing at the test server receives no request).

**Business rules invoked:** BR-1, BR-2, BR-10

### FR-4: Resume, Range and retry (A2)
**Description:** Bytes stream to `{final}.part`. An existing `.part` of N bytes is continued with `Range: bytes=N-`. 206 appends; 200 restarts from zero; 416 with N equal to the size means complete, otherwise restart. Up to 6 consecutive failures are retried with delays of 0.5 s x 2^min(n,5), the counter resetting when bytes arrive. Transport errors, 429 and 5xx retry; other 4xx fail at once ([[T-031-decision-log]] D-4).

**Acceptance criteria (testable):**
- [ ] AC-13 [PY] A `.part` of N bytes makes the request carry `Range: bytes=N-`; the final file is correct.
- [ ] AC-14 [PY] A connection dropped mid-body is retried with Range and completes; the delays recorded by an injected sleep follow 0.5, 1, 2, 4, 8, 16, 16 s and the counter resets after bytes arrive.
- [ ] AC-15 [PY] A server that ignores Range (200) restarts the file from zero; final bytes correct.
- [ ] AC-16 [PY] Six consecutive failures -> `failed` with the reason, `.part` kept, a later Download resumes it; 404 fails immediately; 429 and 503 are retried.
- [ ] AC-17 [PY] A `Content-Range` total or `Content-Length` that disagrees with the catalog size fails with "upstream file changed" and removes the `.part`.

**Business rules invoked:** BR-2

### FR-5: Pause, resume, cancel (A1)
**Description:** Pause drops the connection and keeps `.part` (state `paused`); Resume reconnects with Range; Cancel stops the job and deletes `.part`. State survives a console restart as `partial`.

**Acceptance criteria (testable):**
- [ ] AC-18 [PY] After Pause the server sees the connection close, `.part` is kept and `done` stops growing; Resume completes via Range.
- [ ] AC-19 [PY] Cancel, while downloading and while paused, ends the job thread, removes `.part` and leaves the asset `not_installed`.
- [ ] AC-20 [PY] A new manager over a directory holding a `.part` reports `partial` with bytes > 0, and Download resumes it with Range.

### FR-6: Verification and atomic install (A2)
**Description:** After the last byte the size and the SHA256 of the whole `.part` are checked (phase `verifying`). Only then is the `.part` renamed to the shell-visible name (`os.replace`) and the manifest `{final}.manifest.json` written last. A voice installs its `.onnx.json` first and its `.onnx` last. A mismatch deletes the `.part`, fails with expected/actual prefixes and is not retried automatically. A **Verify** action hashes an installed file (e.g. one from the `.ps1` scripts) and writes the manifest on a match.

**Acceptance criteria (testable):**
- [ ] AC-21 [PY] A body of the right length with wrong bytes -> `failed` naming sha256 with expected/actual prefixes; no final-named file exists at any time during the run (polled by a second thread); `.part` removed; the server sees no further GET.
- [ ] AC-22 [PY] Fault injection after the last byte, before the rename, after the rename and before the manifest: a final-named file exists only after verification succeeded; after the rename-before-manifest fault the asset reads `installed`, `verified: false`.
- [ ] AC-23 [PY] For a voice, `.onnx.json` is in place before `.onnx`; if the `.onnx` download fails no `.onnx` exists.
- [ ] AC-24 [PY] Verify on a hand-placed file: matching hash -> manifest written, `verified: true`; mismatch -> `verified: false` with expected/actual prefixes and the file untouched.
- [ ] AC-25 [PY] Streaming a 32 MiB asset peaks below 8 MiB of Python allocations (tracemalloc).
- [ ] AC-26 [PY] Catalog values equal the real bytes: where `desktop/stt/ggml-base.en.bin` and `desktop/tts/en_US-amy-medium.onnx(.json)` exist their SHA256 equals the catalog (skipped when absent). Opt-in online variant (`CC_ONLINE_TESTS=1`): HEAD of each pinned large-file URL returns `x-linked-etag` equal to the catalog sha256.

**Business rules invoked:** BR-2, BR-3

### FR-7: Delete (A1)
**Description:** Delete removes the final file(s), manifest and any `.part`. It is refused for an asset that is in use (configured, or loaded by the engine) or downloading, with the reason.

**Acceptance criteria (testable):**
- [ ] AC-27 [PY] Delete removes final, manifest and `.part`; the asset reads `not_installed`.
- [ ] AC-28 [PY] Delete is refused with a stated reason when the asset is configured (including a blank voice resolving to it), reported loaded by the shell, or downloading. When the shell is down and the operating system refuses the delete (Windows file lock on a model an engine still has open), the refusal is reported as a sentence with the cause, nothing is half-deleted, and the response is not a server error.
- [ ] AC-29 [PY] Names are validated against the inventory and `^[A-Za-z0-9._-]+$`; `../x`, absolute paths, backslashes and NUL are rejected; nothing outside `desktop/stt` and `desktop/tts` is ever touched.

**Business rules invoked:** BR-7, BR-9

### FR-8: Download safety and audit (A2)
**Description:** Requests carry catalog ids only. URLs must be https, the initial host `huggingface.co`, redirects followed only to https, no credentials sent. Free disk space is checked before connecting; a write error (ENOSPC) fails the job and keeps `.part`. Download, Cancel, Delete and Verify are audited.

**Acceptance criteria (testable):**
- [ ] AC-30 [PY] With free space stubbed below the remaining bytes the download is refused before any connection, naming needed and free bytes.
- [ ] AC-31 [PY] The policy layer rejects an `http://` non-loopback catalog URL, a redirect to `http://`, and a non-`huggingface.co` initial host; the server sees no `Authorization` header. The loopback exception is a test-only flag and the guard sits inside the injectable fetch path, not ahead of it.
- [ ] AC-32 [PY] A write error mid-stream -> `failed`, `.part` kept.
- [ ] AC-33 [PY] Each of Download, Cancel, Delete and Verify writes an `audit.record` with action, target id and outcome.

**Business rules invoked:** BR-1, BR-10, BR-11

#### Model selection and live swap (A3)

### FR-9: Installed-model picker
**Description:** In Settings → Assistant the free-text `stt_model` field becomes a dropdown of installed STT models (catalog and custom) showing size and an "in use" marker; a configured model that is not installed is shown as "NAME (not installed)". Selecting posts `stt_model` through the existing settings route. Server-side validation of `stt_model` is unchanged ([[T-031-decision-log]] D-9).

**Acceptance criteria (testable):**
- [ ] AC-34 [UI] The dropdown lists installed models only, marks the in-use one, keeps a missing configured name visible, saves on change with the "Saved" toast, and shows the "(live)" chip.

**Business rules invoked:** BR-4

### FR-10: `ensure()` compares the model (A3 bug)
**Description:** A pure function decides whether a running engine is stale: its loaded model file name differs from the wanted file name (the resolved result of `model_file()`, so a fallback counts), or its prompt differs. `ensure()` uses it. Today it compares only the prompt (`stt.rs:255`).

**Acceptance criteria (testable):**
- [ ] AC-35 [RS] Table test: running `ggml-base.en.bin`, wanted `ggml-tiny.en.bin`, same prompt -> stale (model); same model, different prompt -> stale (prompt); both -> stale; neither -> not stale. The first row is the regression: today's inline condition returns false for it.
- [ ] AC-36 [RS] In a temp directory `model_file` returns the preferred model when present and the smallest `ggml-*.bin` when not, and the fallback warning is emitted once per distinct (wanted, fallback) pair, not on every call.

### FR-11: Live swap
**Description:** On a stale engine the replacement starts on a new port while the old one keeps serving; the engine mutex is not held while waiting for it; only when it answers is the slot swapped and the old process killed, within `START_TIMEOUT` (30 s). If the replacement fails, the old engine keeps serving, the failure is recorded and reported in `/listen/state` (`swap_error`), and that model name is not retried until the preference changes. A transcription never fails because of a swap ([[T-031-decision-log]] D-6).

**Acceptance criteria (testable):**
- [ ] AC-37 [RS] With an injected spawner: a model change spawns exactly one replacement; the old engine is killed only after the replacement answered; takes before that use the old port.
- [ ] AC-38 [RS] `running()` and `loaded_model()` return within 100 ms while a replacement spawn is blocked.
- [ ] AC-39 [RS] A replacement that never answers leaves the old engine serving, sets `swap_error`, is not retried for the same name, and `transcribe` does not return an error because of it.
- [ ] AC-40 [HL] On this machine, with `tiny.en` installed through the manager: change `stt_model` via the settings route, run one transcription of `desktop/tests/fixtures/status-ticket-two.wav`; `/listen/state.model` reports `ggml-tiny.en.bin` and the transcript contains "status". Skipped loudly when a second model is absent. The measured swap time is recorded in verification (not asserted).

### FR-12: Console-to-shell settings refresh
**Description:** After a successful settings write the console makes a best-effort `POST /settings/refresh` (timeout at most 1 s; failure never fails the write). The shell drops its settings cache, re-reads the merged settings and re-applies model, prompt, voice/rate and device preferences, and starts any needed replacement engine in the background ([[T-031-decision-log]] D-7).

**Acceptance criteria (testable):**
- [ ] AC-41 [PY] `settings_post` triggers `native_bridge.settings_changed`; the fake opener sees `POST /settings/refresh` with timeout <= 1; a refusing or erroring bridge still leaves the write successful.
- [ ] AC-42 [RS] The route is authenticated; the pure re-apply function sets model, prompt, voice/rate and device preferences from a settings `Value`, bumps the device generation only when a device name changed, and drops the cache.
- [ ] AC-43 [HL] After a settings POST, `GET /health` caps `stt_model` shows the new resolved model within 1 s without any take.

### FR-13: Truthful hints (A1)
**Description:** `stt::hint` no longer names a file that does not exist. On non-Windows it points to Settings → Assistant → Speech models and says the engine (`whisper-server`) must be installed separately; on Windows it keeps the `.ps1` and adds the Settings path.

**Acceptance criteria (testable):**
- [ ] AC-44 [RS] The hint for a machine with neither engine nor model contains "Settings"; every `get-*` path it names exists under `desktop/`; the existing tests (`stt.rs:505-523`, `listen.rs:366`) still pass.

#### Voice (A5)

### FR-14: Voice picker and speed slider
**Description:** The free-text voice field becomes a dropdown over the installed voices (shell caps `speak_voices`, merged with the console scan), first option "Automatic — first installed"; a configured voice that is not installed reads "NAME (not installed)". Speed is a range slider 50-200 bound to `speak_rate_percent` with its value shown. When the shell reports `speak_backend` other than `piper`, the group states that voice, speed and output device do not apply to the OS voice.

**Acceptance criteria (testable):**
- [ ] AC-45 [UI] Dropdown, slider and OS-voice notice behave as described; with no piper the controls are disabled with the reason; both save through the existing settings route and show "(live)".

### FR-15: Voice preview
**Description:** `POST /api/assistant/voice/preview {voice?, rate_percent?}` speaks a fixed short sample through the shell with those values for this utterance only, without saving them. The shell's `/speak` accepts optional `voice` and `rate_percent`; absent, it behaves as today.

**Acceptance criteria (testable):**
- [ ] AC-46 [PY] The route accepts a blank or installed voice and a rate of 50-200 (otherwise 400), forwards `/speak` with the overrides, writes no settings, and returns `ok: false` with a reason when the shell is down.
- [ ] AC-47 [RS] A pure function resolves the voice and rate for a `/speak` body: overrides win, absent values fall back to settings; an unknown override voice falls back as `piper::voice` does.
- [ ] AC-48 [HW] The preview is audibly the chosen voice at the chosen speed. Not verified on hardware until a person listens.

**Business rules invoked:** BR-13

#### Devices (B1)

### FR-16: Enumerate devices
**Description:** The shell enumerates input and output devices with cpal 0.16 (`GET /audio/devices`: names per direction, the OS default of each). The console proxies it as `GET /api/assistant/voice/devices`, adding for each direction `configured`, `resolved`, `match` (`exact` / `substring` / `none` / `default`) and `fallback`. With the shell down the route answers 200 with `ok: false` and the reason.

**Acceptance criteria (testable):**
- [ ] AC-49 [RS] `list_devices` returns inputs, outputs and the default names; zero devices gives empty lists, no panic; a device appears only under a direction it supports. [HL] On this machine it lists at least one input and one output and includes the OS default names (skips with no devices).
- [ ] AC-50 [PY] The route returns `{devices, default, configured, resolved, match, fallback}` per direction from a fake bridge; shell down -> 200 with `ok: false`.

### FR-17: Device settings keys
**Description:** `input_device` and `output_device` are strings, `""` meaning the system default; additive keys in `DEFAULTS`, `WRITABLE` and `console/config/assistant.toml` ([[T-031-decision-log]] D-9).

**Acceptance criteria (testable):**
- [ ] AC-51 [PY] Both keys default to `""`, are writable, round-trip, are stripped, reject control characters and more than 200 characters, accept `""`; the committed file ships the same default; an unknown key is still rejected.

### FR-18: Match by name
**Description:** One pure Rust function resolves a configured name against the enumerated names of one direction: exact (case-insensitive, trimmed), else unique substring, else no match; several substring candidates is no match with the candidates listed; an empty name means the default ([[T-031-decision-log]] D-5). The console and UI never re-implement it.

**Acceptance criteria (testable):**
- [ ] AC-52 [RS] Table test: exact beats a substring that sorts earlier; case and surrounding space ignored; one substring hit resolves; two hit -> no match with both listed; empty -> default; non-ASCII names; two identical names resolve to the first (documented limitation).
- [ ] AC-53 [RS] The resolver never returns a device lacking the requested direction.

**Business rules invoked:** BR-5, BR-6

### FR-19: Selected devices are used and kept current
**Description:** Capture (`Mic::open`), neural playback (`piper::play`) and cues (`cue::blow`) use the resolved device through one shared resolver. An unresolved name falls back to the system default, logs a warning once per change and reports `fallback: true`. A microphone already open in a take loop or hands-free reopens when the input preference changes (generation counter). `/listen/state.microphone`, `audio::available()` and `listen::hint` describe the resolved device; the open error still contains "microphone" (`hands_free.rs:382`); the open log line names the device.

**Acceptance criteria (testable):**
- [ ] AC-54 [RS] No call to `default_input_device()` or `default_output_device()` remains under `desktop/src-tauri/src/` outside the shared resolver (source scan test; the `audio_probe` example is exempt).
- [ ] AC-55 [RS] A name that does not resolve yields the default device, `fallback = true`, and a single warning per distinct name.
- [ ] AC-56 [RS] A pure `needs_reopen(opened_generation, current_generation)`; after `prefer_devices` changes the input name the generation increases, and unchanged settings leave it unchanged. The take loop and the armed hands-free loop use it and reset their cursor on reopen.
- [ ] AC-57 [RS] A device-open failure message contains "microphone"; `/listen/state.microphone` returns the resolved name.
- [ ] AC-58 [HW] With two physical inputs, selecting the second makes the next take capture from it; unplugging the chosen one shows "(not connected)" and capture continues on the default. Not verified on hardware.

**Business rules invoked:** BR-5, BR-6, BR-14

### FR-20: Device pickers in Settings
**Description:** Input and Output dropdowns list "System default (name)" first, then devices by name. A configured name that does not resolve reads "NAME (not connected)" and states which device is used instead. The list re-enumerates every 3 s while the panel is visible and on a Refresh button. The pickers apply no matching logic of their own; they show the console's `match`/`resolved`. With the shell down they are disabled with the reason.

**Acceptance criteria (testable):**
- [ ] AC-59 [UI] Behaviour as described; a plug/unplug of a real device appears within one poll (HW part: not verified on hardware).

#### Tests (B2)

### FR-21: Mic test
**Description:** `POST /api/assistant/voice/test/mic` -> shell `POST /audio/test/mic` starts a thread that opens a fresh microphone on the resolved input for 2.0 s and returns at once. The result (`running`, `peak` 0..1, `device`) is read from `/listen/state.mic_test` (console: `GET /api/assistant/voice`), and the existing level meter moves while it runs. It is refused (409) while a take or hands-free is active. Only the peak is kept; no audio is written or sent ([[T-031-decision-log]] D-11).

**Acceptance criteria (testable):**
- [ ] AC-60 [RS] `peak_of(&[i16])`: silence 0.0, full-scale positive or negative 1.0, mixed content its absolute maximum.
- [ ] AC-61 [RS] The guard refuses while listening or hands-free is on and allows otherwise.
- [ ] AC-62 [PY] The route forwards and returns without waiting for the 2 s; `GET /api/assistant/voice` includes `mic_test` from the shell state.
- [ ] AC-63 [HL] On this machine: after the call `/listen/state` still answers in under 500 ms, `mic_test.running` becomes false within 3 s, `peak` is in [0,1], `device` equals the resolved input, and no audio file (`*.wav`, `*.raw`, `*.pcm`) is created anywhere under the repo during the test. [HW] The bar follows a real voice: not verified on hardware.

**Business rules invoked:** BR-6, BR-15

### FR-22: Speaker test tone
**Description:** `POST /api/assistant/voice/test/speaker` -> `POST /audio/test/speaker` resolves the output device synchronously (fails fast with a reason), then plays a two-note tone on a thread through the cue renderer, regardless of the reply-mute switch.

**Acceptance criteria (testable):**
- [ ] AC-64 [RS] The tone renders finite samples, peak at most 0.25, starting and ending near silence, 400-800 ms long.
- [ ] AC-65 [PY] The route forwards; an unresolved output returns `ok: false` with the reason. [HW] The tone is audible on the chosen output: not verified on hardware.

### FR-23: Test controls in Settings
**Description:** "Test microphone" (button, level bar, final peak number, device name) and "Test speaker" (button, status) with plain-language errors, in the voice/devices area of Settings → Assistant.

**Acceptance criteria (testable):**
- [ ] AC-66 [UI] Buttons disable while a test runs; the bar moves; a refusal (409) and an unresolved device are shown as sentences.

#### "(live)" flags (D4)

### FR-24: Per-key apply flags
**Description:** `assistant_config.APPLIES` maps every writable key to `{when, note}` with `when` in `live | restart | next_chat`; `GET /api/assistant/settings` returns it as `applies`; each Settings → Assistant row shows "(live)", "(restart needed)" or "(next chat)" with the note as tooltip ([[T-031-decision-log]] D-8).

**Acceptance criteria (testable):**
- [ ] AC-67 [PY] Every key in `WRITABLE` has an `APPLIES` entry with a valid `when` and a non-empty note; adding a writable key without one fails the test.
- [ ] AC-68 [PY] `GET /api/assistant/settings` returns `applies`.
- [ ] AC-69 [UI] Each Assistant settings row shows its chip; the UI keeps no list of its own.
- [ ] AC-70 [PY] (SHOULD) A scan of `hands_free.rs` `fetch_policy` finds every key classified `restart` for hands-free, so a reader moving between per-take and per-session is noticed.

#### Docs and compatibility

### FR-25: Docs, scripts and compatibility
**Description:** README text, `assistant.toml` comments and Settings help no longer present the `.ps1` scripts as the only way and describe the manager. The scripts stay and their output is recognised. New keys are additive: absent, behaviour equals today.

**Acceptance criteria (testable):**
- [ ] AC-71 [PY] Text check: `console/README.md`, `console/config/assistant.toml` and the Settings strings mention Settings → Assistant for models and voices.
- [ ] AC-72 [PY] A file produced by a script (no manifest) is listed `installed`, `verified: false` (AC-5); with no device keys present the shell resolves the system default exactly as before.
- [ ] AC-73 [PY] `desktop/src-tauri/Cargo.toml` `[dependencies]` and `console/requirements-dev.txt` are unchanged (diff).

**Business rules invoked:** BR-11, BR-12

## 5. Non-Functional Requirements

Targets marked `⚠ [unrealistic?]` are analyst proposals with no stakeholder source; they are carried to freeze as accepted (rationale in the cell).

| ID | Category | Requirement | Target | Method / notes |
|---|---|---|---|---|
| NFR-1 | Integrity | A shell-visible model/voice file is never incomplete or unverified | zero occurrences across the fault-injection matrix | AC-21, AC-22, AC-23 |
| NFR-2 | Dependencies | No new runtime dependency | `Cargo.toml` `[dependencies]` and `console/requirements-dev.txt` unchanged; Python stdlib only | AC-73; D-10 |
| NFR-3 | Security | Only catalog files are fetched or deleted; https only; no credentials; names confined to two directories | no request for a non-catalog URL; no path outside `desktop/stt|tts` | AC-12, AC-29, AC-31. The console has no auth of its own (`httpd.py:_announce_binding`), so confinement is the control |
| NFR-4 | Performance | Inventory, devices and state endpoints stay responsive with two downloads running and the shell stubbed | p95 under 250 ms over 50 local calls `⚠ [unrealistic?]` (proposed; no stakeholder figure; local loopback only); shell calls time out at 1.5 s; no outbound internet call | AC-7, AC-8; memory `assistant-slowness-was-configuration`: a 3 s stall on a hot endpoint was once real |
| NFR-5 | Memory | Download streams, never buffers a file | peak Python allocations under 8 MiB for a 32 MiB asset `⚠ [unrealistic?]` (proposed) | AC-25 |
| NFR-6 | Progress cadence | State is fresh while bytes flow | updated at least every 500 ms; UI polls at 1 s only while a download is active | AC-10; UI check |
| NFR-7 | Swap | The replacement engine is ready within the existing limit; no take fails because of a swap | at most `START_TIMEOUT` = 30 s (`stt.rs:43`); zero failed takes. Measured baseline: base.en cold start 792-1592 ms (`host.log`). small.en/medium.en time and memory not measured | AC-37..AC-40; record the measured time in verification |
| NFR-8 | Portability / CI | Python tests pass on ubuntu py3.11 and 3.13 and on Windows py3.14; `cargo build`/`test` pass on Windows, Linux, macOS; no test needs audio hardware or the internet | CI jobs `tests` and `desktop` green (`verify.yml:22-53,98-163`); online check opt-in via `CC_ONLINE_TESTS=1` | G33 |
| NFR-9 | Hot-plug latency | A plugged/unplugged device shows in the picker | within 5 s (3 s poll + enumeration) `⚠ [unrealistic?]` (proposed) | AC-59 [HW]: not verified on hardware |
| NFR-10 | Privacy | Mic test keeps the peak only; nothing downloads without a click | no audio file written by a mic test; no network call at startup | AC-63; BR-1 |
| NFR-11 | Usability / accessibility | States and errors in plain sentences with the cause; progress bar exposes `role="progressbar"` with `aria-valuenow` | every failure state shows a sentence | AC-34, AC-45, AC-59, AC-66 [UI] |
| NFR-12 | Compatibility | Additive; scripts keep working | absent keys = today's behaviour; script output recognised | AC-72 |
| NFR-13 | Observability | Downloads and swaps leave log lines | console prints start/finish/fail per job; shell logs device name on open and each swap | AC-57; UI/log check |
| NFR-14 | Documentation | Docs state what the code does | text checks pass | AC-71 |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Catalog entry | new | `id` (`stt:base.en`, `tts:en_US-amy-medium`), `kind`, `name`, `hint`, `license` (voices), `files[]` {`name`, `url` (commit-pinned https), `size_bytes`, `sha256`, `hash_source`, `git_blob_sha1` (computed-pinned only)} | static, committed, reviewed; refreshed by a reviewed change | new `console/config/voice-assets.toml`; values in [[T-031-decision-log]] D-2 |
| Install manifest | new | `{id, file, sha256, size, source_url, commit, installed_at}` | written last on install or Verify; removed on delete; gitignored with its directory | `{final}.manifest.json` in `desktop/stt` or `desktop/tts` (`.gitignore:94-98`) |
| Download job | new | `id, state, done, total, speed_bps, eta_s, resumed_from, file, error` | in memory, one per asset id; derived from `.part` after a restart | new `console/server/voice_assets.py` |
| Settings keys | changed | `input_device`, `output_device` (new); `stt_model`, `speak_voice`, `speak_rate_percent` (unchanged) | per-machine override, committed default `""` | `assistant_config.py:77-215`, `console/config/assistant.toml` |
| `APPLIES` map | new | `{key: {when: live/restart/next_chat, note}}` | static code | `assistant_config.py` next to `WRITABLE` |
| Device | shell, transient | `name`, `default`, direction; verdict `{configured, resolved, match, fallback}` | enumerated on demand, never stored | `audio.rs` |
| Bridge additions | new | caps: resolved voice, loaded model, device lists on `/audio/devices`; routes `/audio/devices`, `/audio/test/mic`, `/audio/test/speaker`, `/settings/refresh`; `/speak` overrides; `/listen/state` fields `mic_test`, `swap_error` | with the shell build | `bridge.rs:222-250,410-436,491-519` |

### Data flows
Hugging Face → console `.part` → size + SHA256 → atomic rename in `desktop/stt|tts/` → manifest → shell reads by file name (extension filter ignores `.part`/`.manifest.json`) → `/health` caps (usable, resolved, loaded) → console UI. Settings: UI → `POST /api/assistant/settings` → merged file → best-effort `POST /settings/refresh` → shell re-applies statics.

### Retention / archival
Models stay until deleted; `.part` removed on cancel.

## 7. Business Rules

- **BR-1:** The downloader lives in the console and writes into `desktop/stt/` and `desktop/tts/`; the shell reports what it can use and what is loaded through `/health` caps (approved, D-1). Nothing is downloaded without an explicit user click, never at startup or first use.
- **BR-2:** A shell-visible file name exists only for complete, verified bytes; a `.part` is never treated as installed.
- **BR-3:** Hash values are never invented; every catalog hash records its provenance (`hf-lfs-oid` or `computed-pinned`) and says where upstream publishes none.
- **BR-4:** A model name in settings names a file `ggml-{name}.bin`; a missing one falls back with a warning (existing behaviour, `stt.rs:143-162`); server validation of the name is unchanged.
- **BR-5:** Devices are chosen by name, never by index; empty means the system default.
- **BR-6:** Matching lives in one place (the shell's `pick_by_name`); an ambiguous substring never guesses; an unresolved name falls back to the system default and says so.
- **BR-7:** An asset that is in use (configured, or loaded by the engine) or downloading cannot be deleted.
- **BR-8:** "In use" = configured as the shell resolves it (blank `speak_voice` = first sorted installed voice) or loaded by the engine.
- **BR-9:** Requests name assets by catalog id or on-disk inventory name only; URLs and file names never come from a request.
- **BR-10:** Download URLs are https, from the committed catalog, pinned to a commit; redirects only to https; no credentials.
- **BR-11:** State-changing asset actions are audited.
- **BR-12:** Mic Drop's mechanics are ported, not its code; the console runtime stays stdlib-only.
- **BR-13:** A preview never changes stored settings.
- **BR-14:** A settings change must reach a running engine or microphone without a restart where the key is classified `live`.
- **BR-15:** The mic test is refused while a take or hands-free is active, and keeps no audio.

## 8. Edge Cases

- Console restarts mid-download -> state `partial`, Download resumes (AC-20).
- Disk full or too small -> refused before connecting / `failed`, `.part` kept (AC-30, AC-32).
- Server ignores Range, answers 416, closes early or serves another size -> AC-15, AC-17.
- Hash mismatch -> `.part` deleted, `failed`, no retry loop (AC-21).
- Double click or two tabs -> one job (AC-11).
- Hand-installed or extra files -> shown, never hidden (AC-5, AC-6).
- Delete of the configured model, or one the engine still has open (Windows lock) -> refused with reason (AC-28).
- A new model fails to start during a swap -> old engine keeps serving, one wait not one per take (AC-39).
- A configured device is unplugged -> "(not connected)", capture continues on the default (AC-58 [HW]); unplugged during a hands-free session is not detected (unchanged, G13).
- Two devices with the same name or an ambiguous substring -> first exact / no match with candidates (AC-52).
- Mic test during a take or hands-free -> 409 (AC-61). Speaker test with no output device -> reason shown (AC-65).
- Shell down -> inventory still works, device pickers disabled with the reason (AC-7, AC-50).
- OS-voice fallback active -> voice, speed and output device do not apply; UI says so (AC-45).
- Hugging Face unreachable or rate-limited -> retries with backoff, then `failed` with the cause; a proxy/TLS error shows its text (AC-16).

## 9. Interactions with Existing Features

(Populated by `challenge-requirements T-031 (overlap/conflict/reuse dimension)`)

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| `stt.rs` `ensure`/`prefer_model`/`hint` (`:245-352`, `:94-99`, `:197-211`) | overlap — the bug itself; hint names a missing script and tests pin its wording (`stt.rs:511`, `listen.rs:366`) | high | modify |
| `piper.rs` `voices`/`voice`/`play` (`:70-113`, `:241-247`) | overlap — list already built; playback hardwired to default | med | reuse list, modify `play` |
| `tts.rs` OS-voice backends (`:172-198`) | isolation — cannot honour voice, speed or output device | med | isolate; disclose in UI |
| `cue.rs` `blow`/`render` (`:82-155`) | overlap — default output hardwired; renderer reusable for the test tone | low | modify |
| `audio.rs` `Mic::open`/`available`/`device_name` (`:478-551`) and `/listen/state.microphone` | overlap — all assume the OS default; one consumer, `settings.js:1080` (grep) | med | modify |
| `listen.rs` / `hands_free.rs` cached `Mic`, stop-on-error text (`hands_free.rs:382`) | overlap — a device change needs reopen; error strings pinned | med | modify |
| `bridge.rs` `/health` caps, `/listen/state`, `/speak`, single-threaded loop | overlap — extend caps and routes; must not block | med | extend |
| `console_settings.rs` 30 s cache (`:132`) | overlap — delays every "live" change; no push path | med | extend (refresh poke) |
| `assistant_config.py` `DEFAULTS`/`WRITABLE`/`update` | reuse | low | extend |
| `assistant_feature.py` settings and voice routes; `_CaptureCtx` | reuse; CLI ctx supports only `get/post/register_tab` | low | extend, no new `ctx.*` |
| `native_bridge.py` `capabilities()` (no non-test caller) | reuse — first real consumer | low | reuse |
| `settings.js` `assistant()` Voice/Listening groups, `voicePanel` | overlap — free-text voice/model fields, `.ps1` hints; other tickets' hunks outside this function | med | modify surgically |
| `desktop/get-whisper.ps1`, `get-piper.ps1` | isolation — keep, same filenames; `get-whisper.ps1:103` cites a non-existent verb | low | isolate |
| `model_catalog.py`, `/api/agents/models`, `console/.cache/models/` | isolation — these are LLM catalogs; name collision | low | isolate; name new things "voice assets" |
| `onboarding_setup.py`, `onboarding-wizard.js` (uncommitted) | isolation — T-034 builds on them | low | do not touch |
| T-032 B9 wav-replay seam | overlap (future) — a file source bypasses the device resolver | med | keep one resolver function |
| T-034 wizard/doctor/tray | reuse — consumes downloads, devices, mic test | med | stable route contract |
| T-019 `wake.rs` ring/spotter | reuse — a reopened `Mic` resets the cursor | low | reuse |
| Mic Drop `download.rs`/`models.rs`/`audio.rs` | reuse of mechanics only, not code | low | reuse |

Counts: overlap 9 · conflict 0 · reuse 6 · isolation 4. No row is a conflict: the two contract changes (`audio::device_name`/`available`, the settings cache) are made deliberately inside this ticket and their only consumers were checked by grep.

## 10. External Dependencies

- Hugging Face `ggerganov/whisper.cpp` (commit `5359861c739e955e79d9a303bcbc70fb988958b1`) and `rhasspy/piper-voices` (commit `c10ece1aade47bb51c153c893d14e5bf8e5b7117`); anonymous access, 302 to a signed CDN. Single host, no mirror: accepted (CR-11), see §13.
- cpal 0.16 (already a dependency, `Cargo.toml:44`) for device enumeration; WASAPI on Windows, CoreAudio, ALSA/PipeWire.
- `whisper-server` and `piper` binaries installed by the user (Windows: the two scripts; elsewhere: by hand, Q1).
- Mic Drop checkout `D:\Workspace\noble-workspace\mic-drop` — read-only reference.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner | Sohail Ali | scope, design; approved dossier (`status: approved`, `INV-2026-10-05-micdrop-adoption-dossier.md:6`) and "start implementing" (`T-031-progress.md:14`); owns Q1, Q2 and the D-1 refinement | yes — recorded for scope and design; freeze-level APPROVED requested in the analyst report |
| Console user (Windows, Linux, macOS) | — | works without a PowerShell script; honest about what is missing | no |
| Downstream | T-034 (wizard Voice step, doctor, tray submenus) | stable route contract: assets, devices, test | no |
| Adjacent | T-032 (wav-replay seam, endpointing) | one input-device resolver a file source can sit above | no |

## 12. Open Questions (mirrored)

Mirrored from `T-031-questions.toml` (`console/kanban.py tracker list T-031 questions`). Blocker questions must be resolved before freeze.

- Q1 (scope, high): does the downloader also fetch the engine binaries, or only models and voices? — status: open
- Q2 (decision, medium): keep `en_US-ryan-medium` (CC BY-NC-SA 4.0) in a reusable template's catalog? — status: open
- Assumptions A-1..A-6 are unconfirmed; low-risk defaults are recorded in [[T-031-decision-log]] (D-1..D-13), not asked.

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements T-031`. Each must be resolved or explicitly accepted before freeze.)

Pass 2 (2026-10-05, after iteration 1) raised 6 findings (1 major, 5 minor: CR-14..CR-19), closed in iteration 2 by the edits listed in [[T-031-iteration-log]]; one is accepted below. Pass 3 found nothing new.

Pass 1 (2026-10-05) raised 13 findings (3 critical, 8 major, 2 minor; rows in [[T-031-critique-report]]). Iteration 1 closed 12 by fixing the originating sections; each fix is listed in [[T-031-iteration-log]]. One remains, accepted:

- ⚠ [scope-creep] §4 FR-6, FR-9/FR-12, FR-24 (CR-14): four items are not literal brief items — the Verify action, listing custom/hand-installed files, the console-to-shell settings refresh, and the third flag value "(next chat)". **Accepted:** each traces to the brief — Verify makes A2's "SHA256 verify, do better than Mic Drop" true for files the scripts already placed; custom rows stop A3's installed-model picker hiding a model that works today; the refresh makes D4's "(live)" and A3's "live swap" true; "(next chat)" keeps D4 from labelling `backend`/`model`/`mode` falsely. Each is one FR/AC and can be dropped by an `evolve` without touching the rest.
- ⚠ [spof] §10 (CR-11): single download host (Hugging Face), no fallback source — **accepted:** every file is pinned and hash-verified, downloads resume and retry with backoff, files are plain files that can be placed by hand (the manager shows them as installed, unverified, and Verify checks them), and a second mirror would add trust surface for no verified benefit. Revisit if Hugging Face removes a pinned commit.

## 14. Draft History

See [[T-031-iteration-log]] for per-iteration diff + rationale.

Current iteration: **2**

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred
- [x] All ⚠ findings resolved or explicitly accepted with rationale (CR-11, CR-14 accepted)
- [x] All blocker open questions answered (no critical question exists; Q1 high and Q2 medium stay open by design)
- [x] Every FR has at least one testable acceptance criterion (25 FRs, 73 ACs)
- [x] Every NFR has a concrete target or documented reason for absence (14)
- [x] Every new/changed entity has a canonical reference or creation plan
- [x] Out-of-scope list is non-empty
- [x] Stakeholder sign-off recorded (scope/design: dossier `status: approved`, `T-031-progress.md:14`; freeze-level APPROVED requested in the analyst report)
- [x] `T-031-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements-draft]] · [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-requirements]] · [[T-031-critique-report]] · [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
