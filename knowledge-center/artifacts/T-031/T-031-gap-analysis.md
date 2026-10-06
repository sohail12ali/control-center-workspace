---
ticket: "T-031"
artifact: gap-analysis
status: closed
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Gap Analysis: T-031

**Sources:** [[T-031-requirements-draft]] · [[T-031-context-snapshot]]

**Severity rule used in this pass (stated because it is a judgement):** 🔴 is reserved for a gap whose resolution needs a stakeholder decision that the approved scope/design does not already give, and which would change scope or an FR's behaviour. Gaps resolved by a grounded fact or by the approved design are 🟡 with the resolution recorded. Two stakeholder-owned questions exist and are deliberately **not** 🔴 (G6 -> Q1 `high`, G25 -> Q2 `medium`): the listed scope A1-A5, B, D4 is complete under the recorded default either way, and the default is reversible through `evolve`.

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 1  | 0   | 1     |
| Business rules  | 0  | 4  | 0   | 4     |
| Edge cases      | 0  | 10 | 1   | 11    |
| NFRs            | 0  | 2  | 0   | 2     |
| Data / entities | 0  | 3  | 0   | 3     |
| Integrations    | 0  | 3  | 1   | 4     |
| UX / UI         | 0  | 3  | 1   | 4     |
| Compliance      | 0  | 2  | 1   | 3     |
| Cross-cutting   | 0  | 3  | 0   | 3     |
| **Total**       | **0** | **31** | **4** | **35** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-05 | — | Initial pass from `challenge-requirements` (gaps) | analyst |
| 2026-10-05 | G1 | Closed: FR-16..FR-23 define the route contract; T-034 named stakeholder (draft §11) | analyst |
| 2026-10-05 | G2, G3, G4, G5 | Closed: BR-5..BR-8, FR-2, FR-18, D-1 refinement, D-5 | analyst |
| 2026-10-05 | G6 | Closed with default (engines out of scope), Q1 `high` open for the owner; D-3, FR-13 | analyst |
| 2026-10-05 | G7..G12 | Closed: AC-11, AC-15..17, AC-20, AC-21, AC-30, AC-32, AC-5/AC-6/AC-24 | analyst |
| 2026-10-05 | G13 | Accepted as out of scope (unchanged from today); listed in draft §3 and edge cases | analyst |
| 2026-10-05 | G14, G15 | Closed: AC-61, AC-57 | analyst |
| 2026-10-05 | G16 | Accepted: not verified off Windows, labelled | analyst |
| 2026-10-05 | G17, G18 | Closed: NFR-1..NFR-14; proposed numbers marked ⚠ [unrealistic?], accepted; swap time unmeasured, said so | analyst |
| 2026-10-05 | G19, G20, G21 | Closed: draft §6 entities; AC-26; FR-1 AC-3, D-13 | analyst |
| 2026-10-05 | G22, G23, G24 | Closed: FR-4 retry rules, FR-12, FR-11, FR-21 | analyst |
| 2026-10-05 | G25 | Closed with default (show licence), Q2 `medium` open; D-12 | analyst |
| 2026-10-05 | G26..G29 | Closed: FR-14, FR-20, NFR-6, NFR-11; G29 mechanism stated (poll + Refresh) | analyst |
| 2026-10-05 | G30, G31 | Closed: AC-33, AC-63 | analyst |
| 2026-10-05 | G32, G33, G34 | Closed: FR-25, NFR-8 + tags, plan constraints carried to the planner via the requirements links | analyst |
| 2026-10-05 | G35 | Accepted: proxy/TLS error text shown as is | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | T-034 consumes this ticket's downloads, device list, mic test and (for D3) the device keys; no requirement fixes the route shapes it will code against. | Name T-034 as stakeholder; FR for a documented, stable route contract; routes take ids/names only, no UI-only logic. |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟡 | "In use" is undefined. Deleting the configured model is obviously wrong, but the engine may still hold a previously chosen model open (Windows file lock) and a blank `speak_voice` resolves to the first installed voice. | BR: in use = configured (resolved as the shell resolves it) ∪ loaded by the engine; delete refused with the reason. |
| G3 | 🟡 | A-1 (installed list = `/health` caps) cannot work with the shell down (first-run wizard, headless console), and caps contain no STT model list (`bridge.rs:238-241`). | Console scans the two dirs for existence/verification; shell caps supply "usable/loaded". Decision D-1 refinement, flagged to the owner. |
| G4 | 🟡 | A-5: what the shell records with when a chosen device is absent is unstated (fail the take vs OS default). | Fall back to the system default, warn once, report `fallback` (D-5). |
| G5 | 🟡 | Matching ambiguity: two devices whose names both contain the configured substring; identical names. | Exact, then unique substring; ambiguous = no match with candidates listed (D-5). Identical names documented as unresolvable by name. |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G6 | 🟡 | A-6: engine binaries not covered; on Linux/macOS a model download does not make STT work, and `stt::hint` names a script that does not exist (`stt.rs:203`). | Default: engines out of scope (D-3); hint made truthful; Q1 (`high`) asks the owner. |
| G7 | 🟡 | Console restarts or crashes mid-download: in-memory job gone, `.part` remains. | State derived from `.part` (`partial`), Download resumes with Range. |
| G8 | 🟡 | Double click / two browser tabs start the same download twice. | One job per asset id; second request returns the existing job. |
| G9 | 🟡 | Disk full or too small. | Check free space before connecting; ENOSPC mid-write fails the job and keeps `.part`. |
| G10 | 🟡 | Server ignores Range (200), answers 416, closes early, or serves a different size than the catalog (upstream changed). | Port Mic Drop's 200/206/416 handling; size/`Content-Range` mismatch fails with "upstream file changed". |
| G11 | 🟡 | Hash mismatch: retry loop on a bad mirror; leaving a corrupt `.part`. | Delete `.part`, fail with expected/actual prefix, no automatic retry. |
| G12 | 🟡 | Hand-installed legacy files and extra `ggml-*.bin`/`*.onnx` the catalog does not know (`assistant_config.py:166-169`). | Show as installed/unverified and as custom rows; Verify action; never hide them from the picker. |
| G13 | 🟡 | A device is chosen, then unplugged mid-hands-free: stream error is only logged (`audio.rs:568`), loop never notices. Same as today for the OS default. | Not changed by T-031; recorded as a known gap and handed to T-033/T-034 (todo), not silently claimed fixed. |
| G14 | 🟡 | Mic test while a take or hands-free is active; two streams on one device. | 409 while listening/hands-free (D-11). |
| G15 | 🟡 | Error text pinned by `hands_free.rs:382` (`contains("microphone")`/`contains("engine")` stops the loop). New device and swap errors must keep or avoid those words deliberately. | AC: device-open error still contains "microphone"; a swap failure never surfaces as an `Err` from `transcribe`. |
| G16 | 🟢 | Linux/macOS enumeration returns noisy pseudo-devices; names unverified there. | Not verified off Windows; labelled so. |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G17 | 🟡 | Seven NFR rows have no target (performance, scalability, security, audit, availability, usability, compliance). | Enrich with measurable targets grounded in the snapshot; mark proposed numbers `⚠ [unrealistic?]` until the owner confirms. |
| G18 | 🟡 | Swap time and memory for small.en/medium.en are unmeasured (only base.en: 792-1592 ms cold start). | Bound by `START_TIMEOUT` 30 s; say "not measured" instead of promising a number. |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G19 | 🟡 | Catalog, install marker, job entities have no fields, location or canonical home. | Catalog in `console/config/voice-assets.toml` (committed); manifest beside the asset (gitignored dirs); job in memory. |
| G20 | 🟡 | Catalog staleness: pinned commits and hashes need a refresh procedure and a test that ties catalog values to real bytes. | Test compares the catalog hashes with the local legacy files when present; opt-in online check; procedure in decision log D-2. |
| G21 | 🟡 | A4 numbers in the brief (~100 MB … ~950 MB) are Mic Drop's int8 sherpa sizes, not ggml sizes. | Use catalog byte sizes (D-13). |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G22 | 🟡 | Hugging Face is a single host with anonymous rate limits (429/5xx), signed CDN redirects, hostnames that change. | Retry 429/5xx with backoff; follow https redirects only; do not allow-list CDN hosts; hash guards integrity. |
| G23 | 🟡 | Console-to-shell propagation: 30 s settings cache and no re-read in armed hands-free make "(live)" false; `/health` shows a stale model until a take. | `settings/refresh` poke (D-7). |
| G24 | 🟡 | Single-threaded bridge: a blocking route or a swap under the engine mutex stalls `/state`, `/health`, `/listen/state`. | Mic test returns at once; swap never holds `ENGINE` while waiting (D-6, D-11). |
| G35 | 🟢 | Corporate proxy/TLS interception surfaces as an SSL error from `urllib`. | Show the exception text; no custom CA handling. |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G26 | 🟡 | The OS-voice fallback ignores voice, speed and output device; controls would look broken on machines without piper. | UI states it when `speak_backend` is not piper. |
| G27 | 🟡 | Download states, errors, offline and accessibility are unspecified (a progress bar without `role`; errors as raw exceptions). | States listed; errors as one sentence with the cause; `role="progressbar"` + `aria-valuenow`. |
| G28 | 🟡 | `C.get` is concurrency-gated (`core.js:128-138`); polling downloads, devices and the voice panel could queue behind each other. | One poll per panel, 1 s only while a download is active, 3 s for devices only while visible. |
| G29 | 🟢 | "Hot-plug refresh" has no mechanism (cpal 0.16 has no callback). | Re-enumerate on a visible-panel poll and a Refresh button; state the latency. |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G25 | 🟡 | Voice licences differ, one non-commercial (CC BY-NC-SA 4.0, ryan); template is reusable. | Show licence text per entry; Q2 (`medium`). |
| G30 | 🟡 | Downloads, cancels and deletes are state changes with outbound network and disk effects; no audit requirement. | `audit.record` on each, like `settings_post`. |
| G31 | 🟢 | Privacy of the mic test: audio must not persist or leave the machine. | Peak only; AC asserts no file is written. |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G32 | 🟡 | Rollback/compat: the `.ps1` scripts must keep working and their output must be recognised; new keys must be additive. | Same filenames; absent keys behave as today. |
| G33 | 🟡 | CI has no audio hardware and no internet; Rust device code is hard to test. | Pure functions (`pick_by_name`, `peak_of`, `engine_is_stale`, tone render) carry the tests; hardware ACs labelled "not verified on hardware"; online test opt-in. |
| G34 | 🟡 | Shared dirty files (`settings.js`, `styles.css`) and a CLI capture ctx that supports only `get/post/register_tab` (`assistant_feature.py:657-690`). | Plan constraint: surgical edits; no new `ctx.*` calls in `apply()` without extending `_CaptureCtx`. |

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-requirements-draft]] · [[T-031-context-snapshot]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]] · [[T-031-plan]] · [[T-031-progress]] · [[T-031-verification]]
- [[T-031-requirements]] · [[T-031-critique-report]] · [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan-iteration-log]] · [[T-031-release]]
