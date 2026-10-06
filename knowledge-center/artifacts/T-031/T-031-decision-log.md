---
ticket: "T-031"
artifact: decision-log
---

# Decisions: T-031

Status key: **approved** = made by the user before this ticket (cited); **analyst default** = low-risk default chosen in GROUND/CLARIFY, revisable through `evolve` or a user veto before planning.

## D-1 — The downloader lives in the console (Python), not the shell (approved)

**Decided:** `console/server/voice_assets.py` (stdlib only) downloads, verifies, installs and deletes speech models and voices into `desktop/stt/` and `desktop/tts/`. The Settings UI and `assistant_config.py` are already in the console, it is cross-platform, and it closes the "missing `get-whisper.sh`, Windows-only `get-piper.ps1`" gap **for models and voices** (engines: D-3).

**Approval:** dossier §4 (`INV-2026-10-05-micdrop-adoption-dossier.md:123`, status `approved`) and the user's "start implementing" on the plan (`T-031-progress.md:14`); restated in the analyst brief. Not re-litigated.

**Refinement (flag for the user):** the dossier says "the shell only reports installed assets through the existing bridge `/health` caps". Kept for everything the shell alone knows: what it can actually use (`speak_voices`, resolved `stt_model`), what is loaded, devices. But the console also scans the two directories itself for **what exists and whether it was verified**, because (a) the console must show and manage assets when the shell is not running (first-run wizard, T-034; headless console), (b) only the console writes the verification manifest, and (c) the shell reports no list of installed STT models today (`bridge.rs:238-241` has only the resolved one). Both views are shown and a mismatch is surfaced. Filename rules are a shared contract (`ggml-{name}.bin`, `{voice}.onnx`) pinned by a test on each side.

**Rejected:** a Rust downloader (`stt.rs:23-27` rejects an HTTP client crate; would add TLS + resume code to the shell and still need a UI path through the console); keeping the PowerShell scripts as the only path (Windows-only, no resume, no hash).

## D-2 — Hash source for every catalog entry (values obtained 2026-10-05)

**Decided:** every catalog file carries `sha256`. Values below were read from Hugging Face's tree API (LFS `oid` is the SHA256 of the content) and independently confirmed by the `x-linked-etag` header of the resolve endpoint. No value was typed from memory or inferred. URLs in the catalog are pinned to the commit shown, so the bytes behind each hash cannot change.

Source URLs: `https://huggingface.co/api/models/ggerganov/whisper.cpp/tree/5359861c739e955e79d9a303bcbc70fb988958b1` and `https://huggingface.co/api/models/rhasspy/piper-voices/tree/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/{lang}/{name}/medium`; cross-check `HEAD https://huggingface.co/{repo}/resolve/{commit}/{path}`.

**STT, repo `ggerganov/whisper.cpp`, commit `5359861c739e955e79d9a303bcbc70fb988958b1` (lastModified 2024-10-29), licence tag `mit`**

| File | Bytes | SHA256 (hf-lfs-oid, confirmed by x-linked-etag) |
|---|---|---|
| `ggml-tiny.en.bin` | 77,704,715 | `921e4cf8686fdd993dcd081a5da5b6c365bfde1162e72b08d75ac75289920b1f` |
| `ggml-base.en.bin` | 147,964,211 | `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002` |
| `ggml-small.en.bin` | 487,614,201 | `c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d` |
| `ggml-medium.en.bin` | 1,533,774,781 | `cc37e93478338ec7700281a7ac30a10128929eb8f427dda2e865faa8f6da4356` |

**TTS, repo `rhasspy/piper-voices`, commit `c10ece1aade47bb51c153c893d14e5bf8e5b7117`.** Every `.onnx` is 63,201,294 bytes (identical size, different hashes).

| Voice | `.onnx` SHA256 (hf-lfs-oid, confirmed by x-linked-etag) | `.onnx.json` bytes / SHA256 (computed, see below) |
|---|---|---|
| `en_US-amy-medium` | `b3a6e47b57b8c7fbe6a0ce2518161a50f59a9cdd8a50835c02cb02bdd6206c18` | 4882 / `95a23eb4d42909d38df73bb9ac7f45f597dbfcde2d1bf9526fdeaf5466977d77` |
| `en_US-ryan-medium` | `abf4c274862564ed647ba0d2c47f8ee7c9b717d27bdad9219100eb310db4047a` | 4883 / `44034c056cb15681b2ad494307c7f3f2e4499d1253c700c711fa0a4607ffe78d` |
| `en_US-lessac-medium` | `5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f` | 4885 / `efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0` |
| `en_GB-alba-medium` | `401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b` | 4888 / `aa965a2f02ecced632c2694e1fc72bbff6d65f265fab567ca945918c73dd89f4` |
| `en_GB-northern_english_male-medium` | `57a219ae8e638873db7d18893304be5069c42868f392bb95c3ff17f0690d0689` | 4847 / `69557ed3d974463453e9b0c09dd99a7ed0e52b8b87b64b357dbeeb2540a97d47` |

**What could NOT be obtained from upstream:** the five `.onnx.json` files are small non-LFS files, so Hugging Face publishes only a git blob SHA-1 for them, not a SHA256. Their SHA256 above was **computed by us** from the commit-pinned download, and the computed git blob SHA-1 (`sha1("blob <n>\0" + bytes)`) was compared with the `oid` in the tree API and matched for all five (git oids: amy `5a1e0a2d94d3719de29a4771aa0e6c116552445f`, ryan `90e07066093f756cf2e0d7b973cbf176b586dddf`, lessac `c67cea2c9a7a6501d89f7b2cdff411bc49e54a28`, alba `c0969252c640fd7c2765baa62936a1106ca856d7`, northern_english_male `1e94f02fd642271570a935c813186aaa95b2ad13`). Catalog field `hash_source` is `hf-lfs-oid` for the nine large files and `computed-pinned` for these five, and the catalog keeps the git oid beside the latter. Engine archives are not catalogued (D-3): whisper.cpp publishes digests for its release assets, piper's `2023.11.14-2` assets publish none (`digest=None`).

**Local confirmation:** SHA256 of this machine's hand-installed `desktop/stt/ggml-base.en.bin` (147,964,211 B), `desktop/tts/en_US-amy-medium.onnx` (63,201,294 B) and `.onnx.json` (4,882 B) equal the catalog values above, so the legacy files from the PowerShell scripts verify.

**Not claimed:** nothing about what Hugging Face will serve after today; a catalog refresh procedure (re-run the tree API, update commit + hashes in one reviewed change) is a maintenance task, not code.

**Rejected:** trusting TLS alone (Mic Drop's approach); hashing only on first use without a pin (would bless whatever `resolve/main` serves today).

## D-3 — Catalog contents; engines out of scope (approved by user 2026-10-05, Q1 resolved: option A)

**Decided:** the catalog is exactly what the two scripts already offer: STT `tiny.en`, `base.en`, `small.en`, `medium.en` (English only, because `-l en` is hardcoded, `stt.rs:285-286`, and A7 is deferred) and voices `en_US-amy-medium`, `en_US-ryan-medium`, `en_US-lessac-medium`, `en_GB-alba-medium`, `en_GB-northern_english_male-medium` (`get-piper.ps1:27-29`). No quantised or multilingual rows. Stored in a committed `console/config/voice-assets.toml`, reviewed like `agents.toml` and `pricing.toml`, not hardcoded and not per machine.

**Engines (`whisper-server`, `piper`) are NOT downloaded by T-031.** Observed 2026-10-05: whisper.cpp `b4938` ships Windows and Ubuntu archives and no macOS binary; piper `2023.11.14-2` ships all three OSes but no digests; archives need extraction, an executable bit and flattening (`get-whisper.ps1:75-80`, `get-piper.ps1:90-98`). That is a separate feature with its own risks, and A1-A5 are about models and voices. Consequence stated plainly: on Linux/macOS the manager can fetch models but listening still needs `whisper-server` installed by hand. `stt::hint` must say so truthfully (D-6/FR-13) rather than name a script that does not exist. **Approved by the user 2026-10-05 (Q1 -> option A: models and voices only):** no `whisper-server` or `piper` download in T-031; Linux/macOS engine install stays manual and is a follow-up. Matches the default above, so no scope change and no `evolve`.

## D-4 — Download protocol and on-disk layout (port of Mic Drop mechanics, with a hash)

**Decided:**
- Bytes stream to `{final}.part` in 1 MiB chunks; a `.part` of N bytes is continued with `Range: bytes=N-`. Response 206 -> append; 200 -> truncate and restart (server ignored Range); 416 with N == size -> already complete, else delete `.part` and restart. `Content-Range` total or catalog size mismatch -> fail ("upstream file changed") and delete `.part`.
- Retry: up to 6 consecutive failures, delay 0.5 s x 2^min(n,5) (1, 2, 4, 8, 16, 16 s), counter reset whenever bytes arrive. Network errors, 5xx and 429 retry; other 4xx fail at once. Mic Drop retries only transport errors (`download.rs:274-303`); this adds 429/5xx, which anonymous Hugging Face downloads can return.
- Pause drops the connection and keeps `.part`; Resume reconnects with Range (Mic Drop `download.rs:311-315`). Cancel stops and deletes `.part`.
- After the last byte: size check, SHA256 over the whole `.part` (verifying phase), then `os.replace(part, final)`, then the manifest `{final}.manifest.json` (`{id, sha256, size, source_url, commit, installed_at}`) written last via temp + replace. The shell-visible name (`ggml-*.bin`, `*.onnx`) therefore never exists for unverified or incomplete bytes; the shell ignores `.part` and `.manifest.json` because it filters by extension (`stt.rs:171`, `piper.rs:104`).
- Voices: `.onnx.json` first (verified, replaced into place), `.onnx` last, so a voice never appears in `speak_voices` without its config.
- Hash mismatch: delete `.part`, state `failed` with expected/actual prefixes, **no automatic retry** (would loop on a bad mirror).
- Files with no manifest (hand-installed by the scripts) show as `installed`, `verified: false`; the Verify action hashes them and writes the manifest on a match.
- Disk: refuse to start when free space < remaining bytes; ENOSPC mid-write fails the job and keeps `.part`.
- Jobs are in-memory, one per asset id; a second Download for the same id returns the existing job. After a console restart, state is derived from the `.part` on disk (`partial`, Resume).
- URL policy: only catalog URLs, only `https`, initial host `huggingface.co`, redirects followed only to `https`, no credentials sent, CDN hostnames not allow-listed (they change; observed `us.aws.cdn.hf.co`, the hash guards integrity). Requests carry catalog ids only, never URLs or file names.
- No automatic downloads at startup or first use (`stt.rs:15-21`, `get-whisper.ps1:3-5`).

**Rejected:** a worker-pool/queue (`jobs.py` is for verbs, cannot cancel a running job, `jobs.py:220-241`); HEAD-for-size (HF answers the redirect, not the file); streaming the hash while downloading (resume would need rehash of the prefix anyway; one pass at the end is simpler and shows an honest "verifying" phase).

## D-5 — Device matching rule and fallback (analyst default)

**Decided:** `input_device` / `output_device` store a device **name**, empty = system default. One pure function in Rust (`pick_by_name`) resolves a name against the enumerated names of that direction: (1) case-insensitive, trimmed **exact** match; (2) else a **unique** case-insensitive substring match; (3) else no match. Several substring candidates is *no match* with a message listing them (Mic Drop takes the first, `audio.rs:140-145`; for a microphone, guessing is the wrong failure). No match -> **fall back to the system default device, log a warning once per change, and report `fallback: true`** so the UI shows "NAME (not connected)" and which device is actually in use. The UI and console never re-implement matching; they show the verdict the shell returns.

**Why:** names survive re-enumeration where indices shift (dossier B1); fallback-and-warn is the repo convention for a named asset that is missing (`stt.rs:143-162`, `piper.rs:65-94`) and the pre-T-031 behaviour is "always the default", so a missing chosen device degrades to what the user has today instead of a dead assistant. Duplicate identical names cannot be told apart by name; accepted, documented as an edge case.

**Not routable:** the OS-voice fallback (`tts.rs:172-198`) always uses the system default device and ignores voice and speed; the UI says so.

## D-6 — Live-swap semantics for the speech model (analyst default)

**Decided:**
1. Extract `engine_is_stale(running_model, running_prompt, wanted_model, wanted_prompt) -> Option<Stale>` (pure, unit-testable). `wanted_model` is the **resolved file name** from `model_file()` (so a fallback is compared like a choice), not the raw preference string.
2. On a stale engine: start the replacement on a new port **without holding the `ENGINE` mutex while waiting** (`stt.rs:246` today), keep serving with the old one, and only when the new process answers, swap the slot and kill the old. Bounded by `START_TIMEOUT` (30 s, `stt.rs:43`).
3. If the replacement fails to start or does not answer: keep the old engine, record the error (reported in `/listen/state`), and do not retry that model name until the preference changes, so a broken file costs one wait, not 30 s per take.
4. A prompt-only change takes the same path (today it kills first, `stt.rs:259-268`).
5. `model_file()`'s per-call warning is emitted once per distinct (wanted, fallback) pair, because `ensure()` and `/health` now call it constantly.
6. Peak memory while swapping is old + new model resident; accepted, unmeasured for small/medium.

**Pre-warm (SHOULD):** the settings poke (D-7) triggers the replacement in the background so the swap is usually done before the next take; if it is not, the next take pays at most the start time. Measured baseline: base.en cold start to first transcript 792-1592 ms (`host.log`); small.en/medium.en not measured.

**Rejected:** killing first (a failed new model leaves no engine); whisper-server's runtime `/load` (not investigated, no need).

## D-7 — Console-to-shell settings poke (analyst default)

**Decided:** after a successful `POST /api/assistant/settings`, the console makes a best-effort `POST /settings/refresh` to the shell bridge (timeout <= 1 s, failure never fails the settings write). The shell drops its 30 s cache (`console_settings.rs:137`), re-reads the merged settings and re-applies model, prompt, voice/rate and device preferences to its statics. **Why:** without it every "(live)" claim is false for up to 30 s (`console_settings.rs:132`), and false indefinitely for the input device in armed hands-free (the loop never re-reads settings, `hands_free.rs:313-357`); it also fixes `/health` reporting a stale model until the next take (`prefer_model` only runs in a take, `listen.rs:241`). No loop: the shell's own `set_bool` POST (`tray.rs:98`) triggers a poke whose handler only GETs.

## D-8 — "(live)" / "(restart needed)" classification (analyst default)

**Decided:** one map, `APPLIES` in `assistant_config.py`, next to `WRITABLE`, giving each key `{when, note}` with `when` in `live | restart | next_chat`; `GET /api/assistant/settings` returns it as `applies`; the UI renders chips from it and keeps no list of its own. A test fails when a `WRITABLE` key has no entry. **Extension of D4:** a third value `next_chat` (label "(next chat)") because `backend`, `model`, `mode` genuinely mean "next new chat" (`assistant_feature.py:328-330`); calling those "(restart needed)" would be false.

Initial classification, from reading the readers (not from running anything):

| Class | Keys | Evidence |
|---|---|---|
| live | `listen_max_seconds`, `listen_silence_ms`, `listen_first_pause_ms` | per take, `listen.rs:238-240,161-178` |
| live (after D-6/D-7) | `stt_model` | per take `listen.rs:241`; engine restart currently missing (the bug) |
| live | `speak`, `speak_voice`, `speak_rate_percent` | per `/speak`, `bridge.rs:500-506`; `speak` also read by the console per reply |
| live | `tray_click_action` | per click, `click.rs:148` |
| live | `reply_chars`, `session_idle_minutes`, `ticket_prefix`, `work_backend`, `work_model`, `backend_chain` | read by the console per use (`assistant_feature.py:221,400`, `assistant_config.py:364,383,460`) |
| live (new) | `input_device`, `output_device` | via D-7 poke and Mic reopen |
| restart (hands-free off/on) | `hands_free_require_wake`, `hands_free_wake_word`, `hands_free_listen_while_speaking`, `hands_free_max_minutes`, `wake_sensitivity`, `listen_preroll_ms` | policy read once at start, `hands_free.rs:173-210` |
| restart (shell) | `hud_dismiss_shortcut` | read at startup, `main.rs:344-349` |
| next_chat | `backend`, `model`, `mode` | chat created with them; `assistant_feature.py:260-276,328-330` |

`hands_free_wake_word` is also read per take for the decoder prompt (`listen.rs:246`); the table lists the stricter behaviour. Caveat recorded: classifications are by code reading; a SHOULD-level test scans the Rust sources so a reader moving from per-take to per-session is noticed.

## D-9 — Settings keys added or changed (analyst default)

**New in `DEFAULTS`, `WRITABLE` and `console/config/assistant.toml`:** `input_device` (`""`), `output_device` (`""`). Validation: stripped string, at most 200 characters, no control characters, `""` allowed; no path rules (not a filename). **New in `assistant_config.py`:** `APPLIES`. **Unchanged, deliberately:** `stt_model` and `speak_voice` keep shape-only validation (`assistant_config.py:563-575`): a name that is not installed is still accepted and the shell falls back with a warning, which keeps hand configuration, tests (`test_assistant_commands.py:385-387`) and the wizard's choose-then-download order working; the UI offers installed assets only and shows a missing one as "(not installed)". `speak_rate_percent` keeps its 50-200 validation; the slider is UI only.

## D-10 — tech-select (confirm-existing): no new dependency

Python: `urllib.request`, `hashlib`, `threading`, `shutil`, `tomllib` (3.11+, CI floor, `verify.yml:30`), `http.server` in tests; the console runtime stays stdlib-only. Rust: `cpal = "0.16"` already covers enumeration (`Cargo.toml:44`), `serde_json`, `std::sync::atomic` for the device generation. No crate, no `requirements-dev.txt` change. Any deviation needs a new decision here before it lands.

## D-11 — Mic test and speaker test mechanics (analyst default)

**Decided:** `POST /audio/test/mic` starts a thread that opens a **fresh** `Mic` on the resolved input device for 2.0 s, publishes `{running, peak, device}` through `/listen/state.mic_test` and drives the existing `audio::level()` for a live bar, then closes the device; the route returns immediately (the bridge is single-threaded, `bridge.rs:199-204`). Refused with 409 while a take or hands-free is active. Peak only; audio is never written or sent. `POST /audio/test/speaker` resolves the output device synchronously (fail fast with a reason), then plays a two-note tone on a thread via the `cue.rs` renderer, bypassing the reply-mute switch (an explicit test). **Verification limit:** a script can show the device opened and a peak in [0,1]; that the bar moves with a voice and the tone is audible are "not verified on hardware" until a person does it.

## D-12 — Voice licences are shown, not decided for the user (approved by user 2026-10-05, Q2 resolved: option A)

**Decided:** the catalog carries a `license` string per entry copied verbatim from the pinned MODEL_CARD and the UI shows it. MODEL_CARD text read 2026-10-05: amy "See URL" (github.com/MycroftAI/mimic3-voices); ryan "CC BY-NC-SA 4.0" (non-commercial); lessac "https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html"; alba "https://creativecommons.org/licenses/by/4.0/"; northern_english_male "CC-BY-SA 4.0 International"; whisper.cpp ggml models: repo licence tag `mit`. The five voices keep parity with `get-piper.ps1`. **Approved by the user 2026-10-05 (Q2 -> option A):** keep all five voices and show each licence in the UI; `en_US-ryan-medium` stays, labelled CC BY-NC-SA 4.0 non-commercial. Matches the default above, so no scope change and no `evolve`.

## D-13 — A4 size hints use measured ggml sizes, not the dossier's numbers

**Decided:** hints state the catalog byte sizes (tiny.en 74 MiB / 78 MB, base.en 141 MiB / 148 MB, small.en 465 MiB / 488 MB, medium.en 1.43 GiB / 1.53 GB) plus a one-line quality/speed note drawn from the existing text (`assistant_config.py:166-169`: base.en accurate on ticket ids, tiny.en faster and worse at exactly those; `get-whisper.ps1:18-20`: small.en better on accents and noise). The dossier's "tiny ~100 MB ... medium ~950 MB" are Mic Drop's sherpa-onnx int8 sizes (`catalog.rs:32-41`) and would understate medium.en by 38%. RAM and speed figures are **not** stated: not measured here.

## Plan-stage decisions (planner, 2026-10-05)

These are planning decisions made inside the frozen scope; none changes a requirement. D-18 and D-19 touch the wording of the frozen text and are flagged for the owner (an `evolve` if the owner disagrees). Findings: [[T-031-critique-report]] § Plan critique.

## D-14 — Build order refinements and one extra seam task (planner default)

**Decided:** (a) the shell model path (`ensure()` fix, engine-slot seam, mutex-free swap, hint) is built first, ahead of the Python downloader that the brief listed first: it is the riskiest design, the user-mandated item, isolated to `stt.rs`, and its first `cargo test` run proves the Windows toolchain early. (b) The settings-refresh route is built **after** the device core: its re-apply includes device preferences and the generation counter (AC-42), so it depends on them (an undeclared dependency in the suggested order). (c) The mandatory swap gets a preceding behaviour-preserving task that turns the process-wide `ENGINE` static into an `EngineSlot` with an injectable spawner: AC-37..39 say "injected spawner", and the code has no seam, so without it the mandatory test cannot be written. **Rejected:** keeping the brief's order (defers the riskiest work); folding the seam into the swap task (a 5 h task, and an unreviewable diff).

## D-15 — `/settings/refresh` answers at once and re-applies on a short thread (planner default)

**Decided:** the shell route returns `{"applying": true}` immediately and does `forget()`, a fresh settings fetch, the re-apply and any pre-warm on a short thread. **Why:** the bridge is single-threaded (`bridge.rs:199-204`), the console's settings GET "stalls for ~3 seconds roughly one request in fifteen" (`console_settings.rs:123-126`), and the console gives the poke 1 s (D-7); a synchronous fetch could freeze every bridge call and time the poke out. An unreachable console applies nothing (it must not reset every key to its default). **Consequence:** AC-43 (1 s) can miss on a stalled fetch; the headless run repeats and reports it (risk R-12). **Rejected:** carrying the changed values in the poke body (a second reader of settings and a trust boundary the requirement did not ask for).

## D-16 — The catalog is TOML in the `tomlio` subset, read with `tomlio` (refines D-10)

**Decided:** D-10 lists `tomllib`; the console's own convention is `console/server/tomlio.py`, which "claims no version floor" and supports only `[section]`, `[[array-of-tables]]` and scalars (no inline tables, no multi-line strings). The catalog therefore uses `[[stt]]`/`[[stt.file]]` and `[[voice]]`/`[[voice.file]]` and is loaded with `tomlio.load`. `tomllib` is not used. No dependency changes either way (AC-73).

## D-17 — Device verdict comes from the shell; the console adds only `configured` (clarifies FR-16 against BR-6)

**Decided:** FR-16 says the console route "adds `configured`, `resolved`, `match`, `fallback`", while BR-6 says one matcher exists and the console never re-implements it. Both hold if the shell's `GET /audio/devices` returns, per direction, the verdict for its **applied** preference (`configured`, `resolved`, `match`, `fallback`, `candidates`) from the one pure Rust function, and the console passes it through and adds the `configured` value from settings. **Consequence:** if a refresh poke failed, the verdict describes the previous preference until the next write or take (at most the 30 s cache); stated, not hidden (risk R-4 context).

## D-18 — One-line exception to "no changes to the two `.ps1` scripts" (user instruction)

**Decided:** by the user's instruction at planning time, `desktop/get-whisper.ps1:103` changes from `python console/kanban.py verb run desktop-listen-state` (no such verb exists; `console/config/verbs.toml` has only the `desktop-windows`, `-monitors`, `-screenshot`, `-ocr` and `-clipboard-*` verbs) to a line naming something that exists. One line, ASCII only, `get-piper.ps1` untouched. The frozen requirements' Out-of-scope text is not rewritten; this entry is the record. Owner: confirm or `evolve` the requirements wording.

## D-19 — Backoff: AC-14's delay list is a table, the retry loop is Mic Drop's (reconciles AC-14 with AC-16)

**Decided:** AC-14 lists seven delays (0.5, 1, 2, 4, 8, 16, 16 s); FR-4, AC-16 and D-4 cap consecutive failures at six. The ported mechanics (`mic-drop/crates/micdrop-core/src/download.rs:224,278,326,355`) increment `failures` first, give up when `failures > 6`, and sleep `500 ms x 2^min(failures, 5)`, so the sleeps actually taken are 1, 2, 4, 8, 16, 16 s and the seventh consecutive failure fails. The plan tests `backoff_delay(0..=6)` as a table (`0.5, 1, 2, 4, 8, 16, 16`, AC-14 literally) and the loop for six sleeps then failure (AC-16, D-4). If the owner wants a 0.5 s first sleep, that is an `evolve` of AC-14/D-4. Not blocking; one half-second.

## D-20 — AC-63 bound amended from 3 s to 5 s (post-freeze change, harness, 2026-10-05)

**Why:** the [HL] run on the real shell (T-031-37) measured `mic_test.running` going false after 3.26, 3.06, 2.69 and 2.77 s over four runs (input: "Microphone Array (Intel Smart Sound...)"). The test is 2.0 s (`voice_test.rs` `MIC_TEST`); the rest is stream open and shutdown. The 3 s figure in AC-63 was an unmeasured guess, so the code is not wrong. **Decided:** the bound is 5 s (2 s + open/close with headroom for slower inputs such as Bluetooth, which took 2-4 s to open in unit runs); everything else in AC-63 is unchanged (the four measured runs met `/listen/state` < 500 ms: max 39 ms, peak within 0..1, device = resolved, no audio file). Recorded here and in requirements.md AC-63 rather than silently rewritten.

## D-21 — Handoff to VERIFY with T-031-38 partly open (harness, 2026-10-05; coordinator asked to proceed)

**Gate:** TEMPLATE → SIMPLIFY needs every plan task `[x]`; T-031-38 is not: 24 of 33 [UI] items were observed in a real headless Chrome (own profile, random port) and 9 are partial or NOT RUN because they need a running shell with hardware, a real refusal/forced failure, or the in-app browser (list in progress.md, T-031-38 entry). **Decided:** advance to VERIFY with that gap disclosed, not hidden: T-031-38's heading stays `[ ]`, the 9 items stay unticked and are handed to the owner/coordinator as manual steps. This is a user-approved skip of the "all tasks [x]" row, limited to those items. **UI-59e** (device poll continues every 3 s while the shell is down): kept as built — FR-20 says "every 3 s while visible" and polling is how the picker recovers when the shell starts; the checklist wording was stricter than the requirement.

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[INV-2026-10-05-micdrop-adoption-dossier]] · [[T-031-requirements-draft]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-context-snapshot]]
- Also: [[T-031-release]]
