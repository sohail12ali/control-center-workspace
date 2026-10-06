---
ticket: "T-031"
artifact: critique-report
---

# Critique report: T-031

## Requirements critique

**Last run:** 2026-10-05 · `challenge-requirements` pass 3 (after iteration 2): 0 new findings. Pass 1 raised CR-1..CR-13 (closed in iteration 1, CR-11 accepted); pass 2 raised CR-14..CR-19 (closed in iteration 2, CR-14 accepted)

| Severity | Count |
|---|---|
| critical | 3 |
| major | 9 |
| minor | 7 |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|---|---|---|---|---|---|
| CR-1 | major | contradiction | draft §3 A-1 / §7 BR-1 vs snapshot §2 | "Installed list from `/health` caps" cannot work with the shell down and caps carry no STT model list (`bridge.rs:238-241`) | resolved: requirements iterate 2026-10-05 — A-1 refined, BR-1, FR-2 (D-1) |
| CR-2 | major | contradiction | draft §1 / §3 A-2 vs analysis finding 5 | "tiny ~100 MB … medium ~950 MB" are Mic Drop int8 sherpa sizes; ggml medium.en is 1.53 GB | resolved: requirements iterate 2026-10-05 — A-2, FR-1 AC-3 (D-13) |
| CR-3 | critical | unrealistic-constraint | draft §4 FR-3 vs `stt.rs:246`, `bridge.rs:199-204,415` | "Old engine keeps serving until new is ready" is not achievable while `ensure()` holds `ENGINE` for the whole start; the single-threaded bridge would freeze up to 30 s | resolved: requirements iterate 2026-10-05 — FR-11 AC-37..39 (D-6) |
| CR-4 | major | unrealistic-constraint | draft §3 A-3 / §4 FR-6 vs `bridge.rs:199-204` | A 2 s mic test that blocks the bridge call also blocks `/listen/state`, so the live level bar cannot move | resolved: requirements iterate 2026-10-05 — FR-21 AC-62, AC-63 (D-11) |
| CR-5 | critical | untestable | draft §4 FR-1..FR-8 | Every acceptance criterion is a `〈TBD〉` stub; no observable outcome or verification method | resolved: requirements iterate 2026-10-05 — AC-1..AC-73 with verification tags |
| CR-6 | major | nfr-unmeasurable | draft §5 | Seven NFR rows have no target or measurement method | resolved: requirements iterate 2026-10-05 — NFR-1..NFR-14 (proposed numbers marked ⚠ [unrealistic?] and accepted) |
| CR-7 | major | ambiguity | draft §4 FR-1, FR-5, FR-7 | "in use", "hot-plug refresh", "(not connected)", "(live)/(restart needed)" are undefined; FR-7 "every key" has no source of truth | resolved: requirements iterate 2026-10-05 — BR-5..BR-8, FR-16, FR-20, FR-24 |
| CR-8 | critical | unstated-assumption | draft §4 FR-3, FR-5, FR-7 vs `console_settings.rs:132`, `hands_free.rs:313-357` | Assumes a Settings change reaches the shell at once; it takes up to 30 s and, in armed hands-free, never until the next take. "(live)" and live swap are false without a refresh path | resolved: requirements iterate 2026-10-05 — FR-12 AC-41..43, BR-14 (D-7) |
| CR-9 | major | unstated-assumption | draft §3 A-4, A-6 | Catalog contents and engine-binary scope are assumed, with no source and a platform asymmetry (no macOS whisper binary, no piper digests) | resolved: requirements iterate 2026-10-05 — FR-1, A-4, A-6; Q1 and Q2 opened (D-3, D-12) |
| CR-10 | major | unstated-assumption | draft §4 FR-4 vs `bridge.rs:491-519` | "Audible preview" of a not-yet-saved voice/speed assumes a per-request override that `/speak` does not have | resolved: requirements iterate 2026-10-05 — FR-15 AC-46, AC-47 |
| CR-11 | minor | spof | draft §10 | One download host (Hugging Face), no fallback source | accepted: pinned + hash-verified + resumable + hand placement possible; see draft §13 |
| CR-12 | major | untestable | draft §4 FR-5, FR-6 | "Chosen device is used", "mic test shows a peak", "tone plays" name no verification method; CI has no audio hardware | resolved: requirements iterate 2026-10-05 — tags [HL]/[HW] on AC-40, AC-58, AC-63, AC-65 with 'not verified on hardware' |
| CR-13 | minor | ambiguity | draft §4 FR-4 vs `tts.rs:172-198` | Voice picker, speed slider and device choice do not apply to the OS-voice fallback; unstated | resolved: requirements iterate 2026-10-05 — FR-14 OS-voice notice (AC-45) |
| CR-14 | minor | scope-creep | draft §4 FR-6, FR-9, FR-12, FR-24 | Verify action, custom-file rows, settings refresh and a third flag value are not literal brief items | accepted: each traces to A2, A3, D4 (draft §13); one FR/AC each, droppable by `evolve` |
| CR-15 | major | spec-gap | draft §4 FR-2, FR-7 | State of a `failed` job after restart was unstated; a delete refused by the OS (Windows lock, shell down) had no defined outcome | resolved: requirements iterate 2026-10-05 (iteration 2) — FR-2 text, AC-28 |
| CR-16 | minor | untestable | draft §4 FR-21 AC-63 | "No new file under console/.cache or desktop" is false by construction (logs rotate) | resolved: iteration 2 — AC-63 asserts no audio file created |
| CR-17 | minor | ambiguity | draft §4 FR-3 | Progress `done`/`total` for a two-file voice unstated | resolved: iteration 2 — FR-3 text |
| CR-18 | minor | ambiguity | draft §4 FR-19 AC-54 | Source scan scope would trip on the `audio_probe` example | resolved: iteration 2 — AC-54 scope |
| CR-19 | minor | unstated-assumption | draft §4 tags | `[HL]` criteria need the internet to install a second model, unlike `[PY]` | resolved: iteration 2 — tag definition |

## Plan critique

**Last run:** 2026-10-05 · `challenge-plan` pass 1 (planner, after `breakdown-tasks`): 20 findings, CR-20..CR-39 (the requirements section above ends at CR-19). **Unresolved critical: 0. Gate: clear** (4 critical findings were raised and resolved in the plan before build; 1 major is an accepted divergence; see Resolution).

**Artifacts walked:** [[T-031-requirements]], [[T-031-plan]], [[T-031-components]], [[T-031-task-breakdown]], [[T-031-implementation-plan]], [[T-031-effort-estimate]], read against the code they touch (`stt.rs`, `bridge.rs`, `listen.rs`, `hands_free.rs`, `audio.rs`, `piper.rs`, `cue.rs`, `console_settings.rs`, `assistant_config.py`, `assistant_feature.py`, `native_bridge.py`, `tomlio.py`, `test_plugins.py`, `settings.js`).

**Method note (deviation, stated):** the skill says findings only and no edits to plan artifacts. The brief asked for each finding to be resolved in the plan, so the findings were written first and the plan, breakdown and decision log were then amended in place; every amendment is named in the Resolution column and in [[T-031-plan-iteration-log]]. No finding needed an owner decision to block build, so none was mirrored to `{T}-questions.toml` (the planner has no CLI); CR-21 and CR-33 are flagged to the owner in the planner's report as non-blocking.

| Severity | Count |
|---|---|
| critical | 4 |
| major | 10 |
| minor | 6 |

| Plan kind | Count |
|---|---|
| traceability | 2 (CR-25, CR-30) |
| scope-drift | 1 (CR-33) |
| contradiction | 5 (CR-21, CR-26, CR-27, CR-36, CR-39) |
| sequencing-risk | 4 (CR-20, CR-22, CR-28, CR-38) |
| effort-unrealistic | 2 (CR-23, CR-34) |
| untestable | 2 (CR-24, CR-29) |
| layer-violation | 0 |
| rollback-gap | 1 (CR-32) |
| critical-path | 3 (CR-31, CR-35, CR-37) |

| ID | Severity | Kind | Pointer | Issue | Resolution |
|----|----------|------|---------|-------|------------|
| CR-20 | critical | sequencing-risk | requirements AC-37..39 vs `stt.rs:59,245-352` | AC-37..39 say "injected spawner", but `ENGINE` is a process-wide static and `ensure()` spawns a `Command` inline: there is no seam, so the mandatory swap test cannot be written as specified, and tests would share one global with `transcribes_a_spoken_command_from_a_fixture` | resolved: plan task 03 (behaviour-preserving `EngineSlot` + injectable spawner and readiness) precedes task 04; D-14 |
| CR-21 | major | contradiction | requirements AC-14 vs AC-16, FR-4, D-4 | AC-14 lists seven delays (0.5, 1, 2, 4, 8, 16, 16) while FR-4, AC-16 and D-4 allow six consecutive failures; the ported loop (`mic-drop download.rs:224,278,355`) sleeps 1, 2, 4, 8, 16, 16 then fails on the seventh | resolved: plan task 08 tests `backoff_delay(0..=6)` as a table (AC-14 literally) and the loop as six sleeps then failure (AC-16); D-19; the owner may `evolve` AC-14 if a 0.5 s first sleep is wanted |
| CR-22 | critical | sequencing-risk | FR-12, AC-42/43 vs `bridge.rs:199-204`, `console_settings.rs:123-126`, brief order (5 before 6) | a synchronous refresh would fetch settings on the single-threaded bridge, whose console GET stalls about 3 s one request in fifteen, freezing every bridge call and missing the console's 1 s poke timeout; the re-apply also sets device preferences, so it depends on the device core, which the suggested order built later | resolved: plan task 20 returns at once and re-applies on a short thread (D-15) and is ordered after tasks 04 and 16 (D-14) |
| CR-23 | major | effort-unrealistic | [[T-031-effort-estimate]] vs plan total | plan 83.5 h is 63% of the envelope's Development M (132.4 h) and 10.1% under its lower bound (92.9 h) | accepted: the envelope uses the skill's untuned human-team table; the plan is bottom-up with named evidence; both QC (72.7 h) and verifier work are outside the plan total; confidence Low stated; forecast checkpoints after task 05 and each phase with `replan` above 25% variance |
| CR-24 | critical | untestable | `stt.rs:511`, `listen.rs:366`, FR-13/AC-44 | both existing tests pin `get-whisper` on every OS; FR-13 removes the non-existent `get-whisper.sh` from the non-Windows hint, so `cargo test` would fail on the ubuntu and macOS CI jobs that this machine cannot run | resolved: plan task 05 rewrites both assertions per OS (`cfg!(windows)`), keeps "Settings" and "engine" assertions on all OSes, and states CI is not run locally (risk R-11) |
| CR-25 | major | traceability | `console/tests/test_plugins.py:204-224` | an exact `set(routes) == {...}` assertion pins the assistant plugin's routes; every route this ticket adds fails it, and no task listed the file | resolved: tasks 14 and 25 list and update `test_plugins.py` |
| CR-26 | major | contradiction | FR-16 ("console adds `match`") vs BR-6 ("one matcher; console never re-implements") | read literally, the console would have to compute the verdict | resolved: D-17, the shell's `/audio/devices` returns the verdict for its applied preference and the console adds `configured` only (tasks 24, 25) |
| CR-27 | major | contradiction | D-10 (`tomllib`) vs `console/server/tomlio.py:1-13` | the console deliberately avoids `tomllib`; `tomlio` has no inline tables or multi-line strings, so a catalog written for `tomllib` would not parse | resolved: D-16, task 06 writes `[[stt]]`/`[[stt.file]]`/`[[voice]]`/`[[voice.file]]` and a test loads the committed file through `tomlio` |
| CR-28 | major | sequencing-risk | tasks 02-04, `stt.rs:246` | after task 02 alone a model change takes effect but `ensure()` still holds `ENGINE` for up to 30 s, freezing the bridge | resolved: tasks 02, 03, 04 are one gate in Phase 1; no headless run or ship between 02 and 04; task 04's lock-not-held test is the gate |
| CR-29 | minor | untestable | `hands_free.rs:382` | the loop stops only when a reason contains "microphone" or "engine"; two existing non-empty hint variants contain neither | resolved: task 05 pins "engine" in every non-empty hint with a test |
| CR-30 | minor | traceability | AC-22, AC-72 | each spans two tasks (fault matrix and inventory state; script-placed files and absent device keys) | resolved: both halves mapped in the plan's coverage table (09 and 11; 11 and 13) |
| CR-31 | major | critical-path | `console/static/settings.js`, `styles.css` dirty with other tickets' hunks; tasks 26-32 | seven serial edits to a shared file; a whole-file write or reformat destroys uncommitted work that no commit protects | resolved: protocol in the plan (scratchpad snapshot, `git diff --no-index` after each task, re-read before each edit, surgical `Edit` only, one appended CSS block, no new JS file, `app.js`/`index.html` untouched); residual accepted: the byte-identical check is manual, not CI |
| CR-32 | minor | rollback-gap | new keys, `voice-assets.toml`, manifests | additive changes with no explicit rollback note | accepted: rollback is deleting the new file and keys; manifests sit in gitignored dirs and the shell ignores them; the two scripts are unchanged |
| CR-33 | minor | scope-drift | frozen Out-of-scope "changes to the two .ps1 scripts" vs plan task 34 | the user-instructed one-line fix to `get-whisper.ps1:103` contradicts frozen text | resolved: D-18 records the exception; the task is limited to one line and checks that `get-piper.ps1` is untouched; the owner may `evolve` the requirements wording |
| CR-34 | major | effort-unrealistic | 16 tasks at the 3 h cap (04, 06-11, 16, 17, 20, 22, 24, 25, 27, 28, 37) | a cap-sized task that overruns is the likeliest source of schedule error | accepted: stated cap rule (stop and `replan`, never stretch), ranges given per task, forecast checkpoints, risk R-13 |
| CR-35 | minor | critical-path | AC-43 (1 s) | when the console's settings GET stalls the re-apply can miss 1 s | accepted: the headless run repeats up to 3 times and reports the stall; risk R-12 |
| CR-36 | critical | contradiction | AC-37 ("old killed after the new answers") vs FR-11 ("a take never fails because of a swap"); `stt.rs:47,384-388` | `transcribe` gets the old port from `ensure()` and then runs an inference for up to `INFER_TIMEOUT` 60 s; killing the old process the moment the new one answers would fail any take mid-inference | resolved: plan task 04 hands out a `Lease` that `transcribe` holds; the old engine is killed when its lease count reaches zero (at once if none); test (9) pins it |
| CR-37 | major | critical-path | `audio::available()`/`device_name()` called from `/health` and `/listen/state` (voice panel polls 2 Hz, `settings.js:1120`); bridge `bridge.rs:199-204` | once these enumerate devices through the resolver, every poll enumerates twice on the single-threaded bridge | resolved: task 17 caches enumeration for about 1 s (injected clock, invalidated by a preference change); the Refresh route bypasses it; a TTL test |
| CR-38 | major | sequencing-risk | tasks 29, 30, 33, 35, 36 | declared dependencies missed real ones: 29 and 30 call the shared `loadAssets()` introduced in 27; 33's text check needs the old hints gone from 29 and 30; task 18 and 05 were depended on by no later task so the full cargo run could precede them | resolved: dependency lines corrected in [[T-031-plan]] and [[T-031-task-breakdown]] (29, 30 on 27; 33 on 29, 30; 35 and 36 on every Python- or Rust-touching task) |
| CR-39 | minor | contradiction | D-6 ("the next take pays at most the start time") vs D-6.2 / FR-11 ("old keeps serving") | a take right after a model change cannot both wait for the new engine and be served by the old one | resolved: the plan follows FR-11: a take never waits when an old engine is alive, so one issued in the first seconds may use the previous model; the `stt_model` `APPLIES` note says so (task 13); AC-40 waits for the swap |

## Implementation critique

**Run:** 2026-10-05 · verifier, `challenge-implementation` (read-only against code and tests; independent re-runs listed in [[T-031-verification]] § Test Results). **Result:** 0 critical, 0 major, 7 minor/info; gate clear for the verify scopes that ran. Both checkpoint-2 findings were confirmed fixed by reading code and tests (below).

**Confirmed fixed (checkpoint 2):**
- Symmetric mic-test guard: the bridge refuses a test while a take or hands-free runs (`desktop/src-tauri/src/bridge.rs:518-524` via `voice_test::refuse_reason`, tested by `the_guard_refuses_a_busy_microphone`), and the other direction holds too: a take refuses while a test runs (`listen.rs:413-417`, `take_refusal`), and the armed hands-free loop waits the test out, bounded, instead of opening a second stream (`hands_free.rs:334`, source-pinned at `hands_free.rs:633`).
- Voice-name traversal: `piper.rs:85-107` `is_safe_voice_name` (`[A-Za-z0-9._-]+`) gates the lookup; a path-like name falls back like a typo; test `a_voice_name_that_is_a_path_is_an_unknown_voice_and_never_leaves_the_directory` (`piper.rs:507-535`) tries `..\evil`, `../evil`, drive and absolute paths, NUL and space, and asserts the spoken file's parent is the voice directory. The Python side refuses the same names (`test_voice_devices_routes.py:218`, `test_voice_assets_delete.py:204`, `test_voice_assets_routes.py:343`).

| # | Severity | Class | Where | Finding | Disposition |
|---|----------|-------|-------|---------|-------------|
| IC-1 | minor | consistency | `console/static/settings.js:1732` (`Date.now() - t0 < 4000`) vs AC-63 as amended by D-20 (5 s bound) | The page stops watching the mic test at 4 s while the shell may take up to 5 s (a slow input such as Bluetooth opened in 2-4 s in unit runs). On such a device the page says "still running" and re-enables both buttons while the shell test runs; the next click gets the shell's "already running" sentence. Measured real runs ended at 2.7-3.3 s, so it did not show on this machine. | open; fixer or owner (raise the page cap to 5-6 s or poll to `running:false`) |
| IC-2 | minor | spec-drift | `console/server/voice_assets.py:240-250,431-436`; `requirements.md` AC-14 | AC-14's text lists a first delay of 0.5 s; the loop's first sleep is 1 s (D-19: Mic Drop's counter-first mechanics, table 0.5..16 tested separately). D-19 flags it for the owner but the frozen AC text was not amended (unlike AC-63 for D-20). Tests assert the D-19 reading (`test_voice_assets_transfer.py:245-257`). | open; owner decides (`evolve` AC-14 or accept) |
| IC-3 | minor | concurrency | `bridge.rs:518-524`, `voice_test.rs:147` | The take/hands-free check in `refuse_reason` and the `running = true` set are two separate steps; only `already_running` is re-checked under the state lock. A take starting inside that window can still open the device beside the test. A window of microseconds on a one-request-at-a-time bridge; not reproducible by test. | accepted risk; note only |
| IC-4 | minor | coverage | `bridge.rs:1178-1189` | `live_swap_is_visible_in_listen_state` returns early (prints `skipped:`) without tiny.en installed, so a green `cargo test` does not mean AC-40 ran (the verifier's re-run took 0.00 s: skipped). The AC-40 evidence is the builder's [HL] run (swap 1.0166 s, progress.md T-031-37) and was not re-run by the verifier. | recorded; AC-40 stays PASS-[HL] on the builder's number |
| IC-5 | minor | coverage | `test_voice_assets_catalog.py:177` | AC-26's online `x-linked-etag` check is opt-in (`CC_ONLINE_TESTS=1`) and was skipped in the verifier's run (the 1 targeted skip). The catalog hashes were checked against local files and the 78 MB tiny.en download (sha256 equals the catalog, T-031-37), not against Hugging Face headers in this pass. | recorded |
| IC-6 | info | traceability | `T-031-task-breakdown.md` | AC-3, AC-26, AC-52, AC-53 are not named in the breakdown (all four are in the plan's done-criteria). | recorded |
| IC-7 | info | robustness | todos TD-2..TD-6 on `stt.rs` | Known gaps in the mandatory swap code, tracked as todos and not ACs: TD-4 (a panic in the start path leaves `starting` true: later takes wait about 35 s), TD-5 (`shutdown` does not latch: a racing take can respawn an engine nobody stops), TD-2/TD-3 (no retry offer / back-off on a failed key), TD-6 (100 ms wall-clock bound in swap tests can flake on a slow runner, AC-38). | open todos; none blocks the ACs |

**Spot-checked AC to test (named test asserts what the AC says), 22 of 73:** AC-14/16 (`test_voice_assets_transfer.py:245-290`: table, six sleeps then fail, `.part` kept, second run sends `Range`), AC-21 (`test_voice_assets_install.py:71`: wrong bytes, right length, no final name, one GET), AC-22 (`:108-149`: four fault points, ordering), AC-23 (`:154-195`), AC-24 (`:200-238`), AC-25 (`transfer.py:192`, tracemalloc < 8 MiB), AC-30 (`install.py:243`), AC-31 (`transfer.py:397-423`), AC-35 (`stt.rs:1958`), AC-37 (`stt.rs:2115`, spawn < ready < kill order), AC-38 (`stt.rs:2147`, 20 calls under a blocked spawn), AC-39 (`stt.rs:2192`), AC-52/53 (`devices.rs:573-664`), AC-54 (`devices.rs:908`, scan plus a control that the scan can see real call sites), AC-60/61/64 (`voice_test.rs:253,309,325`), AC-51 and AC-67/68/70 (`test_assistant_commands.py:823-963`; AC-70 skips if `hands_free.rs` is absent, it ran). No test found that asserts less than its AC.

**Plan drift / scope creep:** none found in T-031 files. Forbidden-file check: no T-031 hunk in `onboarding*.py`, `audit.py`, `shell_feature.py`, `dotenv.py`, `agents.toml`, `app.js`, `index.html`; `settings.js` hunks from line 958 (`assistant()`) to its end are T-031, the earlier hunks (lines 4-619) and the ones after `assistant()` are other tickets' (prefs, layout); `styles.css` has the T-031 block at line 2406. D-19, D-20, D-21 are the only post-freeze deviations and each is recorded.

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-context-snapshot]] · [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
