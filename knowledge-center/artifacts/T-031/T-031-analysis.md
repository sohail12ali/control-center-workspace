---
ticket: "T-031"
artifact: analysis
---

# Analysis: T-031

## Context

Foundation ticket of the Mic Drop adoption ([[INV-2026-10-05-micdrop-adoption-dossier]]): manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default. Ground truth was re-read in the code on 2026-10-05; the dossier's explorer-reported claims were re-checked (device selection: **confirmed**; `ensure()` bug: **confirmed by reading**, not by running). Network facts below were obtained live from Hugging Face and GitHub on the same day (scripts in the session scratchpad, not committed). Nothing here is a requirement; see [[T-031-requirements-draft]].

## Current State

**Models (shell, `desktop/src-tauri/src/stt.rs`)**
- Engine = `whisper-server` child process, kept warm (`stt.rs:49-59`). `Engine.model` is stored (`:52`, assigned `:336`) and read only by `loaded_model()` (`:374-376`).
- `ensure()` (`:245-352`) computes `stale = engine.prompt != wanted_prompt` (`:255`) and **never compares `engine.model`**. `prefer_model` (`:94-99`) only updates a static; nothing restarts anything. Confirmed bug: a changed `stt_model` never reaches a running engine until the shell restarts.
- `ensure()` holds the `ENGINE` mutex (`:246`) for the whole start, up to `START_TIMEOUT` 30 s (`:43`, wait loop `:327-343`). `running()` and `loaded_model()` take the same lock (`:366-376`) and are called from the bridge's `/listen/state` (`bridge.rs:415-416`); the bridge is a single thread (`bridge.rs:199-204`). A swap that starts the new engine under the lock would freeze every bridge call (voice panel polls twice a second, `settings.js:1120`).
- `prefer_model` is called from exactly one place, the per-take settings read (`listen.rs:241`). In armed hands-free the loop does not enter `take_inner` until the wake word fires (`hands_free.rs:313-357`), so nothing re-reads settings between takes.
- Model choice: `model_file()` (`stt.rs:143-162`) = `ggml-{wanted}.bin` else smallest `ggml-*.bin` with a warning on every call (also from `/health` through `model_name`, `bridge.rs:241`).
- `hint()` (`:197-211`) names `sh desktop/get-whisper.sh` on non-Windows (`:203`); that file does not exist (`desktop/` has only `get-whisper.ps1`, `get-piper.ps1`). Tests pin the current wording: `stt.rs:511` (`contains("get-whisper")`), `listen.rs:366`.
- Module doc: "nothing is downloaded from here" (`stt.rs:15-21`), repeated for piper (`piper.rs:11-13`) and in `get-whisper.ps1:3-5`. A download must therefore be an explicit user action.

**Voices (`piper.rs`, `tts.rs`)**
- `voices()` lists `*.onnx` stems (`piper.rs:97-113`) and is already in `/health` caps as `speak_voices` (`bridge.rs:238`). Nothing in `console/` reads it (grep of `console/**/*.{py,js}`: only `bridge.rs` mentions it). `voice()` falls back to the first sorted voice with a warning (`piper.rs:70-94`).
- `/speak` re-reads `speak_voice` and `speak_rate_percent` per request (`bridge.rs:491-519`); there is no per-request override, so a preview of an unsaved choice is impossible today. Rate and voice reach only piper (`tts.rs:164-169`); the OS synthesiser (`tts.rs:172-198`: System.Speech / `say` / `spd-say` / `espeak-ng`) ignores both and always plays to the OS default device.

**Devices (re-check of the dossier claim: confirmed)**
- Capture: `audio::available()` and `device_name()` use `default_input_device()` (`audio.rs:478-487`); `Mic::open()` does the same (`audio.rs:548-551`). Callers of `Mic::open`: `listen.rs:255`, `hands_free.rs:315`, `bridge.rs:260` (wake-sample recording).
- Playback: `piper.rs:246-247` and `cue.rs:83-84` use `default_output_device()`. No setting, route or UI selects a device. `/listen/state.microphone` (`bridge.rs:414`) therefore always reports the OS default.
- `Mic` stores no device name (`audio.rs:540-543`); `listen.rs` and `hands_free.rs` cache a `Mic` across takes (`listen.rs:105-125`, `hands_free.rs:313-325`), so a device change would also need a reopen (same class of bug as `ensure()`).
- `cpal = "0.16"` is already a dependency (`Cargo.toml:44`); cpal 0.16.0 has `input_devices()`, `output_devices()`, `Device::name()` (registry `traits.rs:61,69,90`). No new crate is needed. cpal 0.16 has no hot-plug callback, so "hot-plug refresh" can only mean re-enumerate on demand.
- Single-threaded bridge: any blocking route stalls `/state`, `/health`, `/listen/state`. `record_phrase` already blocks it for up to 3 s (`bridge.rs:259-276`); a 2 s mic test must instead start a thread and return, like `/listen` does (`bridge.rs:367-383`).

**Settings plumbing (console)**
- `assistant_config.py`: `DEFAULTS` (`:77-195`) is the schema; `speak_voice` (`:114`), `speak_rate_percent` (`:118`), `stt_model` (`:170`); `WRITABLE` (`:205-215`); validators for those keys (`:559-575`). Committed defaults `console/config/assistant.toml` (`:113,116,144`); per-machine overrides `console/.cache/assistant/settings.json`.
- Routes: `assistant_feature.py` `settings_get` (`:512-531`), `settings_post` (`:533-541`), `voice_state` -> `native_bridge.listen_state` (`:600-601`), registration (`:625-638`). `handlers()` runs `apply()` against a capture-only `_CaptureCtx` that implements only `get`, `post`, `register_tab` (`:657-690`): a new `ctx.*` call in `apply()` breaks the CLI.
- `native_bridge.py`: `capabilities()` (`:137-151`) has no caller outside tests (grep). The shell's `/health` caps are produced but unconsumed by the UI.
- The shell caches settings for 30 s (`console_settings.rs:132`, `all()` `:146-166`); `forget()` (`:137`) exists but nothing calls it on a console-side change. A Settings change therefore reaches the shell up to 30 s late, and in armed hands-free only when the next take reads settings.
- UI: `settings.js` `assistant()` (`:952-1555`); Voice group `:1385-1399` (free-text voice at `:1389`, speed number field `:1394`); Listening group `:1401-1423` (free-text `stt_model` at `:1412`); `row()` `:965-973`; `voicePanel()` `:1066-1126` shows `v.microphone` (`:1080`). Both hints tell the user to run the `.ps1` scripts (`:1391`, `:1414`).
- Uncommitted work by other tickets in `console/static/settings.js` sits at new-file lines 1652-1725, 1756-1769, 1771, 1973 (`git diff -U0`), i.e. outside `assistant()`; `styles.css`, `app.js` and `index.html` also carry uncommitted changes (git status). T-031 UI edits must be surgical Edit calls with unique anchors.

**Downloads today**
- Only the two Windows scripts. `get-whisper.ps1`: `ValidateSet` tiny.en/base.en/small.en/medium.en (`:21-22`), engine zip `whisper-bin-x64.zip` release `b4938` (`:29,41`), model from `huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-$Model.bin` (`:42`), no hash, `Invoke-WebRequest` (no resume). `get-piper.ps1`: five voices (`:27-29`), `piper_windows_amd64.zip` (`:45`), `resolve/main` URLs (`:53`), no hash. Nothing in `console/server` downloads files (grep `urlretrieve|hashlib|sha256|\.part`: only unrelated matches). The console runtime is stdlib-only by design (`console/requirements-dev.txt:3-6`, `knowledge-center/wiki/desktop-assistant.md:38-40`).
- `desktop/stt/` and `desktop/tts/` are gitignored (`.gitignore:94-98`). On this machine: `ggml-base.en.bin` (147,964,211 B), `en_US-amy-medium.onnx` (63,201,294 B) + `.onnx.json`, plus engine binaries. No `.part` files.

**Per-machine cache evidence (`console/.cache/`)**
- `assistant/settings.json`: no `stt_model`, `speak_voice`, `speak_rate_percent` or device keys, so this machine runs on defaults (base.en, first installed voice, OS devices).
- `desktop/host.log`: six `stt: engine up` lines (2026-09-16 .. 2026-10-05), every one `ggml-base.en.bin`; cold start to first transcript 792-1592 ms; mic open 891-1943 ms; no `restarting the engine` line ever, i.e. the prompt-change restart path has never fired. No device name is logged anywhere.
- `models/*.toml` are **LLM** catalogs (`model_catalog.py`, `/api/agents/models`), unrelated to speech models: a naming collision to avoid.
- `desktop/bridge.json` holds the bridge bearer token (secret; not reproduced in any artifact).

## Key Findings

1. **`ensure()` never compares `engine.model`** (`stt.rs:255`). Significance: the central A3 defect; the fix must also avoid holding `ENGINE` while the new process boots (see next) and must not retry a failing model every take.
2. **Live swap ("old keeps serving until new is ready") conflicts with the current lock scope** (`stt.rs:246` vs `bridge.rs:415`). Significance: a naive fix freezes the single-threaded bridge for up to 30 s per swap.
3. **Device selection is absent exactly as the dossier said** (`audio.rs:479,484,550`; `piper.rs:247`; `cue.rs:84`). Significance: B1 needs one shared resolver used by capture, piper and cues, plus mic reopen on change; `device_name()`, `available()` and `hint()` assume the OS default and become wrong once a device can be chosen.
4. **A settings change does not reach the shell promptly** (30 s cache, `console_settings.rs:132`; armed hands-free never re-reads). Significance: "(live)" labels (D4) and the live device/model swap are false without a console-to-shell poke; `/health` also reports a stale model until a take happens (`prefer_model` runs only inside a take).
5. **Dossier size hints do not describe ggml files.** The dossier's "tiny ~100 MB ... medium ~950 MB" are Mic Drop's sherpa-onnx int8 exports (`mic-drop/crates/micdrop-core/src/catalog.rs:32-41`). Measured ggml sizes (HF tree API, commit `5359861c`): tiny.en 77,704,715 B; base.en 147,964,211; small.en 487,614,201; medium.en 1,533,774,781. Significance: A4 hints must use these; "medium ~950 MB" would understate the download by 38%.
6. **Upstream SHA256 is available for every model and voice** (details: [[T-031-decision-log]] D-2). Local `ggml-base.en.bin`, `en_US-amy-medium.onnx` and `.onnx.json` hash to exactly the upstream values, so the legacy hand-installed files verify. Only the five `.onnx.json` files are non-LFS (no upstream SHA256, only a git blob SHA-1).
7. **HTTP Range works with stdlib `urllib` through HF's CDN redirect** (206 + `Content-Range`, 416 beyond EOF; tested with 16-byte requests). HF URLs can be pinned to a commit, which makes content immutable and the hash meaningful. `HEAD` on the unpinned `resolve/main` URL answers 302 with `x-linked-size`, not the file size, so the catalog (not a HEAD) must carry sizes.
8. **Engine binaries are a different problem from models.** whisper.cpp release `b4938` ships Windows (x64, Win32, blas, cublas) and Ubuntu (x64, arm64) archives with SHA256 digests, but **no macOS binary**; piper `2023.11.14-2` ships Linux/macOS/Windows archives with **no published digests**. A cross-platform "model manager" does not by itself make STT work on Linux/macOS. Recorded as scope assumption and Q1.
9. **Voice licences differ** (MODEL_CARDs at the pinned commit): ryan = CC BY-NC-SA 4.0 (non-commercial); alba = CC BY 4.0; northern_english_male = CC-BY-SA 4.0; amy = "See URL" (mimic3-voices); lessac = Blizzard 2013 licence page. This workspace is a reusable template, so shipping a non-commercial voice in a catalog needs a decision (Q2).
10. **Legacy and custom files must not vanish.** `assistant_config.py:166-169` documents dropping extra `ggml-*.bin` into `desktop/stt`; a catalog-only picker would hide them. The manager must list on-disk files not in the catalog and show hand-installed catalog files as "installed, not verified".
11. **The OS-voice fallback cannot honour voice, speed or output device** (`tts.rs:172-198`). Significance: the UI must say so, or the new controls look broken on machines without piper.
12. **Test constraints.** CI runs console tests on ubuntu (py 3.11, 3.13) and the desktop job on 3 OSes (`verify.yml:22-53,98-163`): no test may need audio hardware or the internet. Baseline: 2297 pytest tests collected (`console/tests` + `desktop/tests`, collect-only, current dirty tree); 181 `#[test]` in `desktop/src-tauri/src` (grep, not run). The repo has no JS test harness (`console/static/*.js` untested), so UI criteria are manual checks.
13. **Mic Drop mechanics worth porting** (not code): `.part` + Range with 200 (restart) / 206 (append) / 416 handling, retry cap 6 with delay 500 ms x 2^min(n,5), pause drops the connection and holds, cancel deletes the partial (`download.rs:7-10,224,270-303,355-363`); marker file written last (`models.rs:85-95,283-284`); device match = exact name first, then substring, among devices that support the direction (`audio.rs:105-154`); `measure_peak` for the mic test (`audio.rs:770-784`). Mic Drop's gaps to improve on: no checksum, first-substring-wins on ambiguity, HTTP 429 not retried.

## Research

- Hugging Face tree API `/api/models/{repo}/tree/{commit}` (LFS `oid` = SHA256) cross-checked against `x-linked-etag` on the resolve endpoint: all four STT models and five voice `.onnx` files agree. Details and values in [[T-031-decision-log]].
- Hardware reality: this Windows machine has a microphone and speakers (`host.log` mic opens), so enumeration and a headless mic test can be exercised here; peak response to a human voice and tone audibility cannot be asserted by a script.
- Not investigated: whisper-server's runtime `/load` endpoint as an alternative to a second process (restart-with-overlap is sufficient and does not depend on it); Linux/macOS device enumeration behaviour (ALSA/PipeWire list many pseudo-devices; no such hardware here).

## Recommended Path

Build the downloader as a stdlib-only console module (`voice_assets.py`) driven by a committed, reviewed catalog of 4 English ggml models and the 5 voices `get-piper.ps1` already offers, each file pinned to an HF commit with a SHA256, using `.part` + Range + backoff and atomic rename-after-verify, tested against a local range-capable HTTP server. On the shell side, extract a pure staleness check and make `ensure()` start the replacement engine without holding the engine lock (old keeps serving, a failing model is not retried per take), add one shared by-name device resolver used by capture, piper and cues with reopen-on-change, a non-blocking mic test and a speaker tone, and add a console-to-shell `settings/refresh` poke so "(live)" is true. Expose it through new routes in `assistant_feature.py`, two new keys (`input_device`, `output_device`) and an `APPLIES` map in `assistant_config.py`, and surgical edits to `settings.js` `assistant()` (installed-model and voice pickers, download drawer, device pickers, test buttons, "(live)" chips). Engine binaries, Linux/macOS engine acquisition and any change to the two `.ps1` scripts stay out of T-031 pending Q1. Real microphone/speaker behaviour is labelled "not verified on hardware".

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[INV-2026-10-05-micdrop-adoption-dossier]] · [[T-019-summary]] · [[T-032-summary]] · [[T-034-summary]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-release]]
