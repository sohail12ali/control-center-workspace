---
ticket: "T-031"
artifact: requirements
status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 2
---

# Requirements: T-031 — Voice assets and devices: model manager, device pickers, mic test

**Frozen:** 2026-10-05 · iteration 2 · source of truth for planning. Full wording, flows and rationale: [[T-031-requirements-draft]]; history: [[T-031-iteration-log]]; decisions: [[T-031-decision-log]] (D-1..D-13); findings: [[T-031-critique-report]]; gaps: [[T-031-gap-analysis]]. Post-freeze changes go through `evolve`.

## Intent

Let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default ([[INV-2026-10-05-micdrop-adoption-dossier]]; brief ids A1-A5, B1, B2, D4). The downloader lives in the console (Python) and writes into `desktop/stt/` and `desktop/tts/`; the shell reports what it can use and what is loaded through the bridge `/health` caps (approved, D-1).

## Scope

**In:** model/voice manager with resumable SHA256-verified downloads (A1, A2, A4); installed-model picker, live swap and the `stt.rs` `ensure()` fix (A3); voice picker, preview, speed slider (A5); input/output device pickers by name with hot-plug refresh (B1); mic test and speaker tone (B2); per-key "(live)" / "(restart needed)" flags (D4); the bridge routes and caps these need.

**Out (explicit):** sherpa-onnx, Kokoro, cloud engines, GPU select (brief); wizard Voice step, doctor, tray submenus (T-034); endpointing, junk filter, wav-replay seam (T-032); **engine binaries** (`whisper-server`, `piper`; Q1 resolved by the user 2026-10-05: not downloaded, D-3); changes to the two `.ps1` scripts; quantised/multilingual models and extra voices; a CLI downloader; detecting a microphone that vanishes mid-session (unchanged from today, G13).

**Resolved by the user 2026-10-05 (both matched the frozen defaults, so no scope change):** Q1 (scope: engine binaries) -> models and voices only (D-3); Q2 (decision: non-commercial `en_US-ryan-medium`) -> keep all five voices, show each licence (D-12).

Verification tags: **[PY]** pytest, no internet/hardware · **[RS]** `cargo test`, no audio hardware · **[HL]** headless run of the real shell/console on this Windows machine (may use the internet) · **[UI]** manual browser check (no JS test harness exists) · **[HW]** needs a person or second physical device: *not verified on hardware* until someone does it.

## Functional Requirements

### Assets (console)
1. **FR-1 Catalog.** Committed `console/config/voice-assets.toml`: 4 STT models (`tiny.en`, `base.en`, `small.en`, `medium.en`) and the 5 voices `get-piper.ps1` offers; commit-pinned https URL, size, SHA256 + provenance per file; hint; licence for voices.
   - [ ] AC-1 [PY] every file: https `huggingface.co` URL pinned to a 40-hex commit, size > 0, 64-hex sha256, `hash_source` in {`hf-lfs-oid`, `computed-pinned` (+ `git_blob_sha1`)}, safe name; no entry without a hash.
   - [ ] AC-2 [PY][RS] filename contract `ggml-{name}.bin`, `{voice}.onnx` + `.onnx.json`, pinned on both sides.
   - [ ] AC-3 [PY] API returns `size_bytes`, `hint`, `license`; no hint states a size that differs from `size_bytes`.
2. **FR-2 Inventory and state.** `GET /api/assistant/voice/assets`: per catalog entry and per unlisted file on disk: state (`not_installed`, `partial`, `downloading`, `paused`, `retrying`, `verifying`, `installed`, `failed`), size, `verified`, `in_use`, `loaded`, progress, `free_bytes`; console scans the directories itself, shell caps add usable/loaded; works with the shell down; failed state persistence defined.
   - [ ] AC-4 [PY] empty/absent dirs: all `not_installed`, `free_bytes` present, 200.
   - [ ] AC-5 [PY] final+manifest -> `installed`/`verified:true`; final only -> `installed`/`verified:false`; `.part` only -> `partial`+bytes; manifest sha != catalog -> `verified:false`.
   - [ ] AC-6 [PY] uncatalogued `ggml-*.bin`/`*.onnx` listed `custom`; `.part`, `.manifest.json`, `.onnx.json`, non-model files not listed.
   - [ ] AC-7 [PY] `in_use` = configured (blank voice = first sorted installed) ; `loaded` from shell; shell down -> 200, `shell.reachable:false`, bridge timeout <= 1.5 s.
   - [ ] AC-8 [PY] no outbound internet call from the endpoint.
3. **FR-3 Download.** `POST .../assets/download {id}` starts a background job and returns it; progress: `state`, `done`, `total`, `speed_bps`, `eta_s`, `resumed_from`, `file` (voices: both files).
   - [ ] AC-9 [PY] byte-identical file + manifest, no `.part`, states downloading -> verifying -> installed.
   - [ ] AC-10 [PY] `done` non-decreasing, refreshed <= 500 ms, `speed_bps` > 0, `eta_s` null at speed 0.
   - [ ] AC-11 [PY] second Download returns the same job; one non-Range transfer.
   - [ ] AC-12 [PY] unknown id refused with no network call; `url`/`path`/`file`/`filename` in the body have no effect.
4. **FR-4 Resume, Range, retry.** `.part` + `Range: bytes=N-`; 206 append, 200 restart, 416 handled; 6 consecutive failures, delay 0.5 s x 2^min(n,5), counter resets on bytes; transport/429/5xx retry, other 4xx fail.
   - [ ] AC-13 [PY] Range header carries N; final correct.
   - [ ] AC-14 [PY] drop mid-body resumes; delays 0.5, 1, 2, 4, 8, 16, 16 s via injected sleep.
   - [ ] AC-15 [PY] 200 on Range restarts from zero.
   - [ ] AC-16 [PY] 6 failures -> `failed`, `.part` kept, resumable; 404 immediate; 429/503 retried.
   - [ ] AC-17 [PY] size/`Content-Range` mismatch -> "upstream file changed", `.part` removed.
5. **FR-5 Pause, resume, cancel.** Pause drops the connection, keeps `.part`; Resume uses Range; Cancel deletes `.part`; survives restart as `partial`.
   - [ ] AC-18 [PY] pause closes the connection, `done` stops, resume completes.
   - [ ] AC-19 [PY] cancel (active and paused) ends the thread, removes `.part`, `not_installed`.
   - [ ] AC-20 [PY] new manager over a `.part` -> `partial` + bytes; Download resumes by Range.
6. **FR-6 Verification and atomic install.** Size + SHA256 of the whole `.part`, then `os.replace` to the shell-visible name, then manifest last; voice: `.onnx.json` first, `.onnx` last; mismatch deletes `.part`, fails with expected/actual prefixes, no auto-retry; **Verify** action for hand-placed files.
   - [ ] AC-21 [PY] wrong bytes, right length -> `failed` (sha256), final name never exists, `.part` removed, no further GET.
   - [ ] AC-22 [PY] fault injection at four points: final name only after verification; rename-before-manifest fault -> `installed`/`verified:false`.
   - [ ] AC-23 [PY] `.onnx.json` before `.onnx`; failed `.onnx` leaves none.
   - [ ] AC-24 [PY] Verify: match -> manifest, `verified:true`; mismatch -> reported, file untouched.
   - [ ] AC-25 [PY] 32 MiB streams under 8 MiB Python allocations.
   - [ ] AC-26 [PY] catalog hashes equal the real local files when present; opt-in online check (`CC_ONLINE_TESTS=1`) of `x-linked-etag`.
7. **FR-7 Delete.** Removes final(s), manifest, `.part`; refused when in use, loaded, or downloading.
   - [ ] AC-27 [PY] full removal -> `not_installed`.
   - [ ] AC-28 [PY] refusals with reason; an OS-refused delete (lock) reported as a sentence, nothing half-deleted, not a 5xx.
   - [ ] AC-29 [PY] names validated (inventory + `^[A-Za-z0-9._-]+$`); traversal rejected; confined to the two dirs.
8. **FR-8 Safety and audit.** Catalog ids only; https; initial host `huggingface.co`; https-only redirects; no credentials; free-space check; ENOSPC fails the job; Download/Cancel/Delete/Verify audited.
   - [ ] AC-30 [PY] short disk refused before connecting.
   - [ ] AC-31 [PY] http non-loopback URL, http redirect, foreign host rejected; no `Authorization`; test-only loopback flag, guard inside the injectable path.
   - [ ] AC-32 [PY] write error -> `failed`, `.part` kept.
   - [ ] AC-33 [PY] each action writes an `audit.record`.

### Model selection and live swap
9. **FR-9 Installed-model picker.** `stt_model` becomes a dropdown of installed models with size and in-use marker; a missing configured name stays visible as "(not installed)"; server validation unchanged (D-9).
   - [ ] AC-34 [UI] behaviour as stated, saves with the "Saved" toast and "(live)" chip.
10. **FR-10 `ensure()` compares the model.** Pure staleness function over (model file name, prompt).
   - [ ] AC-35 [RS] table test incl. the regression row (running base.en, wanted tiny.en, same prompt -> stale).
   - [ ] AC-36 [RS] `model_file` preferred/smallest fallback; fallback warning once per distinct pair.
11. **FR-11 Live swap.** Replacement starts on a new port while the old serves; `ENGINE` not held while waiting; swap when it answers (<= 30 s); on failure old keeps serving, `swap_error` in `/listen/state`, not retried until the preference changes; a take never fails because of a swap (D-6).
   - [ ] AC-37 [RS] injected spawner: one replacement; old killed after it answers.
   - [ ] AC-38 [RS] `running()`/`loaded_model()` return < 100 ms during a blocked spawn.
   - [ ] AC-39 [RS] failed replacement: old serves, `swap_error` set, no retry, no `transcribe` error.
   - [ ] AC-40 [HL] real engine, `tiny.en` installed via the manager: change `stt_model`, transcribe the committed fixture; `/listen/state.model` = `ggml-tiny.en.bin`, transcript contains "status"; skip loudly without a second model; swap time recorded, not asserted.
12. **FR-12 Settings refresh.** After a settings write the console makes a best-effort `POST /settings/refresh` (<= 1 s); the shell drops its cache, re-reads settings, re-applies model/prompt/voice/rate/devices, starts any needed replacement in the background (D-7).
   - [ ] AC-41 [PY] `settings_post` triggers it; failure never fails the write.
   - [ ] AC-42 [RS] authenticated route; pure re-apply fn; device generation bumps only on change.
   - [ ] AC-43 [HL] `/health` `stt_model` shows the new model within 1 s without a take.
13. **FR-13 Truthful hints.** `stt::hint` names nothing that does not exist; non-Windows points to Settings → Assistant → Speech models and says the engine is installed separately.
   - [ ] AC-44 [RS] contains "Settings"; every `get-*` path it names exists; existing hint tests still pass.

### Voice
14. **FR-14 Voice picker and speed slider.** Dropdown over installed voices (first option "Automatic — first installed"), "(not installed)" for a missing configured one; slider 50-200 bound to `speak_rate_percent`; notice when the backend is not piper.
   - [ ] AC-45 [UI] behaves as stated; disabled with reason when no piper; saves with "(live)".
15. **FR-15 Preview.** `POST /api/assistant/voice/preview {voice?, rate_percent?}` speaks a fixed sample with those values, saving nothing; shell `/speak` accepts optional `voice`/`rate_percent`.
   - [ ] AC-46 [PY] validation (400 outside 50-200 or an uninstalled voice), forward with overrides, no settings written, `ok:false` when the shell is down.
   - [ ] AC-47 [RS] pure resolver: overrides win, absent -> settings, unknown voice falls back like `piper::voice`.
   - [ ] AC-48 [HW] preview audibly uses the chosen voice and speed — *not verified on hardware*.

### Devices
16. **FR-16 Enumerate.** Shell `GET /audio/devices` (names per direction + OS defaults); console `GET /api/assistant/voice/devices` adds `configured`, `resolved`, `match` (`exact`/`substring`/`none`/`default`), `fallback`; shell down -> 200 `ok:false` + reason.
   - [ ] AC-49 [RS][HL] lists by supported direction, empty lists without a panic; on this machine >= 1 input and output incl. the OS defaults.
   - [ ] AC-50 [PY] route shape from a fake bridge; shell down handled.
17. **FR-17 Keys.** `input_device`, `output_device` (strings, `""` = system default) in `DEFAULTS`, `WRITABLE`, committed `assistant.toml` (D-9).
   - [ ] AC-51 [PY] defaults, round trip, strip, control-char/length rejection, committed default equal, unknown key still rejected.
18. **FR-18 Match by name.** One pure Rust fn: exact (case-insensitive, trimmed) -> unique substring -> none; ambiguous = none with candidates; empty = default (D-5). Console/UI never re-implement it.
   - [ ] AC-52 [RS] table test (exact beats earlier substring, case/space, unique/ambiguous, empty, non-ASCII, identical names -> first).
   - [ ] AC-53 [RS] never returns a device lacking the direction.
19. **FR-19 Selected devices are used and kept current.** Capture, neural playback and cues use one shared resolver; unresolved -> system default + one warning per change + `fallback:true`; open mic reopens when the preference changes; `/listen/state.microphone`, `available()`, hint describe the resolved device; open error still says "microphone"; open log names the device.
   - [ ] AC-54 [RS] no `default_*_device()` call under `desktop/src-tauri/src/` outside the resolver (source scan; example exempt).
   - [ ] AC-55 [RS] unresolved -> default, `fallback`, single warning.
   - [ ] AC-56 [RS] `needs_reopen(opened_gen, current_gen)`; generation bumps only on change; take and armed hands-free loops use it and reset their cursor.
   - [ ] AC-57 [RS] open-failure text contains "microphone"; `microphone` reports the resolved name.
   - [ ] AC-58 [HW] two physical inputs: selection changes the source; unplug shows "(not connected)", capture continues on the default — *not verified on hardware*.
20. **FR-20 Device pickers.** "System default (name)" first, then devices by name; unresolved shows "NAME (not connected)" + the device in use; re-enumerates every 3 s while visible and on Refresh; shows the console's verdict; disabled with the reason when the shell is down.
   - [ ] AC-59 [UI] as stated; real plug/unplug within one poll is [HW], *not verified on hardware*.

### Tests (B2)
21. **FR-21 Mic test.** `POST /api/assistant/voice/test/mic` -> shell `POST /audio/test/mic`: fresh mic on the resolved input for 2.0 s on its own thread, returns at once; `{running, peak 0..1, device}` via `/listen/state.mic_test` (console `GET /api/assistant/voice`); level meter moves; 409 while a take or hands-free is active; peak only, no audio kept (D-11).
   - [ ] AC-60 [RS] `peak_of(&[i16])` cases.
   - [ ] AC-61 [RS] guard refuses while listening/hands-free.
   - [ ] AC-62 [PY] route forwards without waiting; `mic_test` present in the voice state.
   - [ ] AC-63 [HL] `/listen/state` answers < 500 ms during the test; `running` false within 5 s (2 s test + device open/close; amended from 3 s by D-20 after [HL] measured 2.7-3.3 s); peak in [0,1]; device = resolved; no `*.wav`/`*.raw`/`*.pcm` created. Bar tracking a real voice is [HW], *not verified on hardware*.
22. **FR-22 Speaker test.** `POST /api/assistant/voice/test/speaker` -> `POST /audio/test/speaker`: resolve output synchronously (fail fast with reason), play a two-note tone on a thread, ignoring the reply-mute switch.
   - [ ] AC-64 [RS] finite samples, peak <= 0.25, starts/ends near silence, 400-800 ms.
   - [ ] AC-65 [PY] forwards; unresolved output -> `ok:false` + reason. Audibility is [HW], *not verified on hardware*.
23. **FR-23 Test controls.** "Test microphone" (button, bar, peak, device) and "Test speaker" with sentence errors.
   - [ ] AC-66 [UI] buttons disable while running; bar moves; 409 and unresolved device shown as sentences.

### "(live)" flags (D4)
24. **FR-24 Per-key flags.** `assistant_config.APPLIES = {key: {when: live|restart|next_chat, note}}`; `GET /api/assistant/settings` returns `applies`; each row shows "(live)", "(restart needed)" or "(next chat)" with the note as tooltip (D-8).
   - [ ] AC-67 [PY] every `WRITABLE` key has a valid entry; a new key without one fails.
   - [ ] AC-68 [PY] settings GET returns `applies`.
   - [ ] AC-69 [UI] chip on each Assistant row; UI keeps no list of its own.
   - [ ] AC-70 [PY] (SHOULD) source scan: keys classified `restart` for hands-free appear in `fetch_policy`.

### Docs and compatibility
25. **FR-25 Docs, scripts, compatibility.** README, `assistant.toml` comments and Settings help describe the manager; scripts stay and their output is recognised; new keys additive.
   - [ ] AC-71 [PY] text check of README, `assistant.toml`, Settings strings.
   - [ ] AC-72 [PY] script-placed files read `installed`/`verified:false`; no device keys -> system default as before.
   - [ ] AC-73 [PY] `Cargo.toml` `[dependencies]` and `console/requirements-dev.txt` unchanged.

## Non-Functional Requirements

Targets marked ⚠ are analyst proposals with no stakeholder source, **accepted** at freeze because none exists and each is measurable.

| ID | Requirement | Target | Verified by |
|---|---|---|---|
| NFR-1 | Integrity: no incomplete or unverified shell-visible file | zero across the fault matrix | AC-21..23 |
| NFR-2 | No new dependency | Python stdlib; Rust deps and `requirements-dev.txt` unchanged | AC-73 |
| NFR-3 | Security: catalog-only fetch and delete, https, no credentials, confined paths | no non-catalog request; nothing outside `desktop/stt|tts` | AC-12, 29, 31 |
| NFR-4 | Responsiveness with two downloads and the shell stubbed | p95 < 250 ms over 50 local calls ⚠; shell calls time out at 1.5 s; no outbound internet call | AC-7, 8 |
| NFR-5 | Memory: stream, never buffer | < 8 MiB Python allocations for 32 MiB ⚠ | AC-25 |
| NFR-6 | Progress cadence | updated <= 500 ms; UI polls 1 s only while active | AC-10, UI |
| NFR-7 | Swap | <= `START_TIMEOUT` 30 s; zero failed takes; base.en baseline 0.8-1.6 s; small/medium not measured | AC-37..40 |
| NFR-8 | Portability / CI | pytest green on ubuntu py3.11/3.13 and Windows py3.14; cargo build/test on 3 OSes; no hardware or internet needed (online check opt-in) | CI jobs `tests`, `desktop` |
| NFR-9 | Hot-plug latency | <= 5 s (3 s poll + enumeration) ⚠ | AC-59 [HW] |
| NFR-10 | Privacy | no audio file from a mic test; no download without a click | AC-63, BR-1 |
| NFR-11 | Usability / accessibility | failures as sentences with the cause; progress bar `role="progressbar"` + `aria-valuenow` | AC-34, 45, 59, 66 [UI] |
| NFR-12 | Compatibility | additive; scripts keep working | AC-72 |
| NFR-13 | Observability | console logs each job; shell logs device on open and each swap | AC-57 |
| NFR-14 | Documentation agrees with code | text checks pass | AC-71 |

## Data Entities

Catalog entry (new, `console/config/voice-assets.toml`) · install manifest (new, `{final}.manifest.json` beside the asset, gitignored dirs) · download job (new, in memory, `console/server/voice_assets.py`) · settings keys `input_device`, `output_device` (new) and `APPLIES` (new) in `assistant_config.py` · device + verdict (shell, transient) · bridge additions: routes `/audio/devices`, `/audio/test/mic`, `/audio/test/speaker`, `/settings/refresh`, `/speak` overrides, caps (resolved voice, loaded model), `/listen/state` fields `mic_test`, `swap_error`. Fields: draft §6.

## Business Rules

BR-1 downloader in the console, shell reports usable/loaded via caps, no download without a click · BR-2 shell-visible name only for complete verified bytes · BR-3 hashes never invented, provenance recorded · BR-4 model name -> `ggml-{name}.bin`, fall back with a warning, validation unchanged · BR-5 devices by name, empty = default · BR-6 one matcher, no guessing, fall back to default and say so · BR-7 no delete while in use or downloading · BR-8 "in use" = configured (as the shell resolves it) or loaded · BR-9 ids/inventory names only, never URLs or file names from a request · BR-10 https, catalog, commit-pinned, https-only redirects, no credentials · BR-11 audited actions · BR-12 port Mic Drop's mechanics not its code; console stays stdlib-only · BR-13 preview saves nothing · BR-14 a `live` key reaches a running engine/mic without restart · BR-15 mic test refused while listening, keeps no audio.

## Edge Cases

Console restart mid-download (AC-20) · disk full (AC-30, 32) · Range ignored/416/other size (AC-15, 17) · hash mismatch (AC-21) · double click (AC-11) · hand-installed and extra files (AC-5, 6) · delete of a configured or locked model (AC-28) · new model fails to start (AC-39) · configured device unplugged (AC-58 [HW]); unplugged mid-hands-free not detected (unchanged) · identical or ambiguous device names (AC-52) · mic test during a take (AC-61) · speaker test with no output (AC-65) · shell down (AC-7, 50) · OS-voice fallback (AC-45) · Hugging Face unreachable or rate-limited (AC-16).

## Interactions with Existing Features

19 rows (overlap 9, conflict 0, reuse 6, isolation 4): draft §9. Must-modify: `stt.rs` `ensure`/`hint`, `audio.rs` `Mic::open`/`available`/`device_name`, `piper.rs` `play`, `cue.rs` `blow`, `listen.rs`/`hands_free.rs` mic cache, `bridge.rs` routes/caps, `console_settings.rs` cache, `settings.js` `assistant()` (surgical: other tickets' uncommitted hunks sit outside it; `styles.css` also dirty). Isolate: `get-*.ps1`, `model_catalog.py` (LLM catalogs, name collision), onboarding files (T-034). Constraint: no new `ctx.*` call in `assistant_feature.apply()` (CLI capture ctx). Error text pinned by `hands_free.rs:382`.

## Out of Scope
- See Scope above (sherpa-onnx, Kokoro, cloud engines, GPU select, T-034, T-032, engine binaries pending Q1, `.ps1` changes, extra catalog rows, CLI downloader, mid-session mic-loss detection).

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements]] · [[T-031-requirements-draft]] · [[T-031-iteration-log]] · [[T-031-gap-analysis]] · [[T-031-critique-report]] · [[T-031-context-snapshot]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[INV-2026-10-05-micdrop-adoption-dossier]] · Next: [[T-034-summary]] depends on this · Related: [[T-032-summary]], [[T-019-summary]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
