---
ticket: "T-031"
artifact: context-snapshot
status: draft
created: "2026-10-05"
last_updated: "2026-10-05"
scope: codebase + history
---

# Context Snapshot: T-031

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-031 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Let the user manage speech models and pick audio devices from Settings instead of a PowerShell script and the OS default (`T-031-summary.md:17`): model manager with resumable, SHA256-verified downloads, installed-model picker with live swap (incl. the `stt.rs` `ensure()` fix), voice picker + preview + speed, input/output device pickers by name, mic test + speaker tone, and "(live)"/"(restart needed)" flags on Settings keys.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Whisper engine + model choice | `stt::ensure`, `prefer_model`, `model_file`, `hint` | shell | fix in place; extract pure staleness fn | `desktop/src-tauri/src/stt.rs:94-99,143-162,197-211,245-352` |
| Installed voice list | `piper::voices`, caps `speak_voices` | shell -> bridge | already produced, no console consumer | `piper.rs:97-113`, `bridge.rs:238` |
| Settings schema + validation | `DEFAULTS`/`WRITABLE`/`update` | console | add keys here, not elsewhere | `console/server/assistant_config.py:77-215,511-594` |
| Settings routes | `settings_get/post`, `voice_state` | console | extend; add routes beside them | `console/server/features/assistant_feature.py:512-541,600-638` |
| Shell client | `native_bridge._call/_request`, `listen_state`, `speak` | console | new helpers follow `wake_sample` shape | `console/server/native_bridge.py:72-119,154-167,185-205` |
| Shell reads settings | `console_settings::all/forget/str_at/u64_at` | shell | one reader; add the poke here | `desktop/src-tauri/src/console_settings.rs:132-182` |
| Live level meter | `audio::level()` | shell | reuse for mic-test bar | `desktop/src-tauri/src/audio.rs:514-526`, `bridge.rs:431` |
| Synthesised tones | `cue::render`, `blow` | shell | reuse for speaker test | `desktop/src-tauri/src/cue.rs:82-155` |
| Voice diagnostics panel | `voicePanel()` | UI | polling idiom (IntersectionObserver, 500 ms) | `console/static/settings.js:1066-1126` |
| Wake-sample recorder | `wakeRecorder`, `POST /wake/sample` | UI + bridge | precedent for blocking mic call and button UX | `settings.js:1004-1059`, `bridge.rs:259-276,442-461` |
| Fake-opener bridge tests | `Bridge`, `Refusing`, `Erroring` | tests | pattern for new `native_bridge` tests | `console/tests/test_native_bridge.py:23-72` |
| Settings tests | `TestListeningSettings` | tests | pattern for new keys + "committed file ships same default" | `console/tests/test_assistant_commands.py:330-395` |
| Windows download scripts | `get-whisper.ps1`, `get-piper.ps1` | scripts | keep; same file names the manager must recognise | `desktop/get-whisper.ps1:21-42`, `desktop/get-piper.ps1:27-53` |

### Existing patterns to reuse
- Committed defaults vs per-machine override: `console/config/assistant.toml` + `console/.cache/assistant/settings.json` (`assistant_config.py:1-29`).
- Fall back and warn, do not fail, on a named asset that is missing: `stt.rs:143-162`, `piper.rs:65-94`.
- Long blocking work runs on its own thread and the route returns at once: `bridge.rs:367-383`.
- Test seams by injection (fake opener, `runner`), and "a guard that runs ahead of the seam is not a seam" (memory `cross-platform-defects-only-ci-finds`).
- Audit every state-changing route: `audit.record(...)` in `settings_post` (`assistant_feature.py:538-540`).
- Skip-loudly integration tests when the engine is absent: `stt.rs:593-625`.

### Naming and architectural conventions in play
- Artifacts `{T}-{artifact}.md` with `## Links`; trackers CLI-only (`CLAUDE.md` Layout).
- Console runtime stdlib-only; new HTTP surface = module + plugin row, `httpd.py` never edited (`knowledge-center/wiki/desktop-assistant.md:38-40,52-53`). T-031 adds routes to the existing assistant plugin, so no `plugins.toml` change.
- Cross-language setting keys are a silent contract: the shell reads keys by name and falls back to its own defaults (`test_assistant_commands.py:349-357`).
- `desktop/stt/`, `desktop/tts/` gitignored (`.gitignore:94-98`); shell filename contract `ggml-{name}.bin` (`stt.rs:147`) and `{voice}.onnx` (`piper.rs:74`, `.onnx.json` `:122`).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-006 | whisper.cpp STT, `get-whisper.ps1`, push-to-talk | closed 2026-09-07 | "Nothing downloads on its own" rule; engine-start under mutex (memory `desktop-assistant-programme`; `T-006-progress.md:20`) |
| T-013 | piper voice, `get-piper.ps1`, voice/speed settings | closed | macOS/Linux piper never run; only one voice tested (`T-013-verification.md:80-88`) |
| T-019 | wake word, ring buffer, hands-free policy | closed (AC-7/8 pending a human voice) | settings read once per session for hands-free policy (`hands_free.rs:173-210`); mic cached across takes |
| T-015 | assistant speed | closed | read `console/.cache/` before building (memory `assistant-slowness-was-configuration`) |
| T-020/T-021 | agents/worktrees, docs agreement | active, uncommitted work in `settings.js` etc. | edit shared files surgically |
| INV-2026-10-05 | Mic Drop adoption dossier | approved | design decision: downloader in console (`dossier §4`) |

### Relevant commits / PRs
- `4338cb1` Let console agents call console verbs, gate the overriding ones (HEAD).
- `02a6816` Hear the wake word instead of reading it back from a transcript (T-019).
- `eacca0a` Stop it talking like a robot (T-013).

### Known incidents / regressions in this area
- 2026-09-07: STT client hung on keep-alive; "two" transcribed as "too" (memory `desktop-assistant-programme`).
- 2026-09-10: assistant slowness was a stored setting, not missing code (memory `assistant-slowness-was-configuration`).
- 2026-09 (T-005): concurrent OS-resource access corrupted the heap; run Rust tests `--test-threads=1` first on a crash (memory `windows-native-threading-traps`).
- 2026-09-07: five defects only the 3-OS CI found (RGBA icons, Linux libs, bypassed seam, relpath, job-object breakaway) (memory `cross-platform-defects-only-ci-finds`).

## 4. External Systems in the Loop

- Hugging Face: `ggerganov/whisper.cpp` (commit `5359861c739e955e79d9a303bcbc70fb988958b1`), `rhasspy/piper-voices` (commit `c10ece1aade47bb51c153c893d14e5bf8e5b7117`); LFS served via `us.aws.cdn.hf.co` after a 302 (observed 2026-10-05).
- GitHub releases: `ggml-org/whisper.cpp` tag `b4938`, `rhasspy/piper` tag `2023.11.14-2` (engines; out of scope unless Q1 says otherwise).
- cpal 0.16 (WASAPI/CoreAudio/ALSA) for device enumeration (`Cargo.toml:44`).
- Mic Drop repo (read-only reference): `D:\Workspace\noble-workspace\mic-drop`.

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- Naive live swap holds `ENGINE` for up to 30 s and freezes the single-threaded bridge (`stt.rs:246`, `bridge.rs:199-204,415`).
- The two shell `.rs` fixes and the UI both depend on the settings-refresh poke; without it "(live)" is wrong for up to 30 s, and indefinitely in armed hands-free.
- Deleting a model the engine has open fails on Windows (file lock); "in use" must include the engine's loaded model, not only the configured one.
- Hash catalog goes stale if a pinned commit is later removed or HF changes hosting; manual refresh procedure needed.
- A licence-restricted voice (ryan, NC) in a reusable template.
- Linux/macOS: enumeration returns noisy pseudo-devices; no hardware to verify; no engine installer.
- Shared dirty files (`settings.js`, `styles.css`) can be clobbered by a whole-file rewrite.

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source.

- Engine memory footprint for small.en/medium.en and swap time for medium.en: not measured (only base.en cold start, `host.log`).
- Whether a device name is unique on one host (two identical headsets): not tested; cpal returns names only.
- cpal 0.16 device enumeration from the bridge thread under WASAPI/COM: precedent exists (`record_phrase` opens a `Mic` on the bridge thread, `bridge.rs:259-260`) but enumeration specifically is untested.
- Behaviour on Linux/macOS (enumeration naming, piper/OS-voice routing): no hardware here.
- Licence of `en_US-amy-medium` ("See URL" -> mimic3-voices) and `en_US-lessac-medium` (Blizzard 2013 page): text not read, only the MODEL_CARD pointers.
- Whether the hosting HF commits stay available indefinitely.

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-05 | Bash | `python console/kanban.py context T-031` | trace-context (first run crashed on cp1252 `\u2192`; rerun with `PYTHONUTF8=1`) |
| 2026-10-05 | Read | `T-031-summary.md`, dossier, all T-031 stubs | scope + approved design |
| 2026-10-05 | Read | `desktop/src-tauri/src/{stt,audio,piper,cue,tts,listen,hands_free,bridge,console_settings,main}.rs`, `Cargo.toml` | device claim, `ensure()` bug, settings reads |
| 2026-10-05 | Read | `console/server/{assistant_config,native_bridge}.py`, `features/assistant_feature.py`, `httpd.py`, `paths.py`, `jobs.py` | schema, routes, bridge client, error mapping |
| 2026-10-05 | Read/Grep | `console/static/settings.js` (+`git diff -U0`), `core.js` | UI structure, other tickets' hunks |
| 2026-10-05 | Read | `console/.cache/assistant/settings.json`, `console/.cache/desktop/host.log`, listing of `console/.cache/` | per-machine state |
| 2026-10-05 | Read | `desktop/get-whisper.ps1`, `get-piper.ps1`, `desktop/README.md`, `console/README.md`, `.gitignore`, `.github/workflows/verify.yml` | download path, CI constraints |
| 2026-10-05 | Read | Mic Drop `download.rs`, `models.rs`, `catalog.rs`, `audio.rs` | mechanics to port |
| 2026-10-05 | Grep | `get-whisper\|get-piper`, `speak_voices\|native_bridge.capabilities`, `urlretrieve\|hashlib\|\.part` | existing references and callers |
| 2026-10-05 | Python (urllib) | HF tree API, resolve HEAD, 16-byte Range GETs, MODEL_CARDs; GitHub releases API | hashes, sizes, Range behaviour, licences, engine assets |
| 2026-10-05 | Python (hashlib) | local `ggml-base.en.bin`, `en_US-amy-medium.onnx(.json)` | legacy files vs upstream |
| 2026-10-05 | pytest `--collect-only` | `console/tests desktop/tests` | baseline 2297 |
| 2026-10-05 | Read | memory files (programme, slowness, threading, rust build, cross-platform, subagent) | lessons applied |

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements-draft]] · [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-requirements]] · [[T-031-critique-report]] · [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
