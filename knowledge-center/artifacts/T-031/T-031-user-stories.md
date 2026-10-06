---
ticket: "T-031"
artifact: user-stories
created: "2026-10-05"
---

# User Stories: T-031

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-031 stories` (frozen iteration 2, [[T-031-requirements]]) · **Validated by:** `validate-artifacts T-031 links` · **Verified by:** `validate-artifacts T-031 links`

Acceptance criteria are cited by their frozen ids (AC-n) with the tag that says how each is proven: [PY] pytest · [RS] cargo test · [HL] headless run on this machine · [UI] manual browser check · [HW] needs a person or a second device (**not verified on hardware** until someone does it). Components are from [[T-031-components]]; tasks are `T-031-NN` from [[T-031-plan]].

Eight stories, no AC listed in two stories.

## Stories

### US-1: Manage speech models and voices from Settings

**As a** workspace user setting up voice
**I want to** see which speech models and voices exist, install one with a click, and pause, resume, cancel, verify or delete it
**So that** I never need a PowerShell script, and a flaky connection or a closed laptop does not cost me a 1.5 GB download.

**Acceptance Criteria:**
- [ ] AC-1 [PY] catalog: pinned, hashed, sized entries (4 models, 5 voices)
- [ ] AC-3 [PY] size, hint and licence shown; hints agree with the real sizes
- [ ] AC-4, AC-5, AC-6 [PY] inventory: empty dirs, installed/verified/partial, uncatalogued files listed as custom
- [ ] AC-7, AC-8 [PY] "in use" and "loaded"; works with the shell down; no outbound call
- [ ] AC-9, AC-10, AC-11 [PY] a download runs to installed, shows progress at least every 500 ms, and a second click is the same job
- [ ] AC-18, AC-19, AC-20 [PY] pause, cancel, and recovery from a console restart
- [ ] AC-27, AC-28 [PY] delete, and its refusals (in use, loaded, downloading, OS lock)
- [ ] AC-12 [PY] only catalog ids are accepted from a request
- [ ] AC-33 [PY] each action is audited

**Business Rules:** BR-1 (console downloads, no download without a click) · BR-3 (hashes never invented) · BR-7 (no delete while in use) · BR-8 (in use = configured or loaded) · BR-9 (ids only) · BR-11 (audited)

**Edge Cases:** console restarts mid-download · double click · hand-installed and extra files · delete of a configured or locked model · shell down · licence of the non-commercial `en_US-ryan-medium` shown, not decided for the user (D-12)

**Related Components:** K1, K3, S3, S5, U1
**Related Tasks:** T-031-06, 10, 11, 12, 14, 27, 28

**Priority:** High
**Story Points:** 8

---

### US-2: Switch the speech model and have it take effect

**As a** user who changed `stt_model` in Settings
**I want to** pick from the models I actually have installed and see the change take effect without restarting the shell
**So that** the model I chose is the one transcribing my voice, and a bad model never leaves me with no engine.

**Acceptance Criteria:**
- [ ] AC-34 [UI] installed-model picker with size and in-use marker; a missing configured model stays visible as "(not installed)"; saves with the "(live)" chip
- [ ] AC-35, AC-36 [RS] `ensure()` compares the model (regression: running base.en, wanted tiny.en)
- [ ] AC-37, AC-38, AC-39 [RS] live swap: one replacement, the old engine serves until the new answers, **no engine lock held across the start**, a failed model keeps the old one and is not retried per take
- [ ] AC-40 [HL] real engine, model installed through the manager, `/listen/state.model` shows the new file and the fixture still transcribes
- [ ] AC-41 [PY], AC-42 [RS], AC-43 [HL] the console tells the shell, which re-applies and shows the new model on `/health` within 1 s
- [ ] AC-44 [RS] the "no engine" hint names only things that exist

**Business Rules:** BR-4 (name to `ggml-{name}.bin`, fallback with a warning) · BR-14 (a live key reaches a running engine without a restart)

**Edge Cases:** new model fails to start · swap while a take is running · armed hands-free never re-reads settings · memory with two engines during a swap (unmeasured for small.en and medium.en)

**Related Components:** R1, R4, S5, U1
**Related Tasks:** T-031-02, 03, 04, 05, 15, 20, 24, 29, 37

**Priority:** High
**Story Points:** 8

---

### US-3: Choose and preview a voice and its speed

**As a** user who hears replies read aloud
**I want to** pick an installed voice, set the speed on a slider, and hear a sample before saving
**So that** I can tune how the assistant sounds without editing a file name.

**Acceptance Criteria:**
- [ ] AC-45 [UI] voice dropdown (first option "Automatic - first installed"), speed slider 50-200, notice and disabled state when the backend is not piper
- [ ] AC-46 [PY] preview validates (400 outside 50-200 or for an uninstalled voice), forwards the overrides, saves nothing
- [ ] AC-47 [RS] the shell's `/speak` accepts per-request `voice` and `rate_percent`; unknown voice falls back like `piper::voice`
- [ ] AC-48 [HW] the preview is audibly the chosen voice and speed (**not verified on hardware**)

**Business Rules:** BR-13 (preview saves nothing)

**Edge Cases:** OS-voice fallback ignores voice, speed and device · configured voice no longer installed

**Related Components:** R3, S5, U1
**Related Tasks:** T-031-21, 25, 30, 39

**Priority:** Medium
**Story Points:** 3

---

### US-4: Pick the microphone and speaker by name

**As a** user with more than one audio device
**I want to** choose the input and output by name and see when a chosen device is not connected
**So that** the assistant listens through my headset and speaks through the right speakers instead of whatever the OS default is today.

**Acceptance Criteria:**
- [ ] AC-49 [RS][HL] the shell lists devices per direction with the OS defaults, and on this machine at least one input and one output
- [ ] AC-50 [PY] the console route shape, with the shell down handled
- [ ] AC-51 [PY] `input_device` and `output_device` keys (validation, defaults, committed default)
- [ ] AC-52, AC-53 [RS] one matcher: exact, then unique substring, ambiguous is no match, never a device lacking the direction
- [ ] AC-54 [RS] exactly one `default_*_device()` call site
- [ ] AC-55, AC-56, AC-57 [RS] unresolved falls back to the default with one warning; the open mic reopens when the preference changes; the open error still says "microphone" and `microphone` reports the resolved name
- [ ] AC-58 [HW] two physical inputs: selection changes the source, unplugging shows "(not connected)" while capture continues on the default (**not verified on hardware**)
- [ ] AC-59 [UI] pickers: "System default (name)" first, "NAME (not connected)", refresh every 3 s while visible and on a button; real plug or unplug within one poll is [HW]

**Business Rules:** BR-5 (devices by name, empty = default) · BR-6 (one matcher, fall back and say so)

**Edge Cases:** identical or ambiguous names · a device unplugged mid-hands-free is not detected (unchanged from today) · shell down · Linux and macOS pseudo-devices (unverified)

**Related Components:** R2, R4, S4, S5, U1
**Related Tasks:** T-031-13, 16, 17, 18, 19, 24, 25, 31, 37, 39

**Priority:** High
**Story Points:** 8

---

### US-5: Test the microphone and the speaker

**As a** user who just chose a device
**I want to** press a button and see my microphone level move, and hear a short tone from the speaker
**So that** I know the choice works before I rely on it.

**Acceptance Criteria:**
- [ ] AC-60 [RS] `peak_of` is correct and always within 0..1
- [ ] AC-61 [RS] the mic test is refused while a take or hands-free is active
- [ ] AC-62 [PY] the console route forwards without waiting and `mic_test` is in the voice state
- [ ] AC-63 [HL] `/listen/state` answers in under 500 ms during the test, the test ends within 3 s, the peak is within 0..1, the device is the resolved one, and no audio file is created; the bar tracking a real voice is [HW] (**not verified on hardware**)
- [ ] AC-64 [RS] the tone is finite, quiet, soft at both ends and 400-800 ms long
- [ ] AC-65 [PY] the speaker route forwards; an unresolved output returns a reason; audibility is [HW] (**not verified on hardware**)
- [ ] AC-66 [UI] buttons disable while running, the bar moves, errors are sentences

**Business Rules:** BR-15 (refused while listening, keeps no audio)

**Edge Cases:** mic test during a take · speaker test with no output · the bridge is single-threaded, so the test must return at once

**Related Components:** R3, R4, S5, U1
**Related Tasks:** T-031-22, 23, 24, 25, 32, 37, 39

**Priority:** Medium
**Story Points:** 5

---

### US-6: Know whether a setting applies now

**As a** user changing a setting
**I want to** see on each row whether it is "(live)", "(restart needed)" or "(next chat)"
**So that** I do not wonder why nothing changed, or restart for a setting that was already live.

**Acceptance Criteria:**
- [ ] AC-67 [PY] every writable key has a valid classification; a new key without one fails a test
- [ ] AC-68 [PY] the settings read returns the classification
- [ ] AC-69 [UI] a chip on each Assistant row; the page keeps no list of its own
- [ ] AC-70 [PY] (SHOULD) keys classified restart for hands-free are the ones the hands-free policy reads once

**Business Rules:** BR-14

**Edge Cases:** `hands_free_wake_word` is read per take for the decoder prompt and once for the policy (the stricter label is shown)

**Related Components:** S4, U1
**Related Tasks:** T-031-13, 26

**Priority:** Medium
**Story Points:** 3

---

### US-7: Existing setups keep working and the docs agree

**As a** user who installed models with the PowerShell scripts
**I want to** have those files recognised and the instructions to match what the product does
**So that** upgrading costs nothing and the README does not send me to a script that no longer tells the whole story.

**Acceptance Criteria:**
- [ ] AC-71 [PY] README, `assistant.toml` and Settings strings describe the manager
- [ ] AC-72 [PY] script-placed files read installed and not verified; a machine with no device keys uses the system default as before
- [ ] AC-73 [PY] `Cargo.toml` `[dependencies]` and `console/requirements-dev.txt` are unchanged

**Business Rules:** BR-12 (port the mechanics, not the code; stdlib only)

**Edge Cases:** the stale `desktop-listen-state` line at the end of `get-whisper.ps1` is corrected (one line, by the owner's instruction, D-18)

**Related Components:** D1, S3, S4
**Related Tasks:** T-031-11, 13, 33, 34, 36

**Priority:** Medium
**Story Points:** 2

---

### US-8: Trust what lands in `desktop/stt` and `desktop/tts`

**As a** owner of a reusable workspace
**I want to** know that a downloaded model is the exact file that was pinned, that a partial file is never mistaken for a model, and that nothing outside the two folders can be touched
**So that** a bad network, a hostile mirror or a wrong click cannot give the shell a corrupt model or delete something else.

**Acceptance Criteria:**
- [ ] AC-2 [PY][RS] the filename contract is pinned on both sides
- [ ] AC-13, AC-15, AC-17 [PY] Range resume, a server that ignores Range restarts, a changed upstream fails and removes the partial
- [ ] AC-14, AC-16 [PY] retry and backoff; 404 fails at once; 429 and 503 retry; six failures keep the partial resumable
- [ ] AC-21, AC-22, AC-23, AC-24 [PY] wrong bytes never reach the final name; a four-point fault matrix; voice config before voice model; Verify for hand-placed files
- [ ] AC-25 [PY] 32 MiB streams in under 8 MiB
- [ ] AC-26 [PY] catalog hashes equal the real files; an opt-in online check
- [ ] AC-29 [PY] names validated, traversal rejected, deletes confined to the two folders
- [ ] AC-30, AC-31, AC-32 [PY] short disk refused before connecting; https and host policy, no credentials; a write error keeps the partial

**Business Rules:** BR-2 (shell-visible name only for complete verified bytes) · BR-10 (https, catalog, commit-pinned, https-only redirects, no credentials)

**Edge Cases:** disk full · hash mismatch · Hugging Face rate limit (429, 503) · a look-alike host

**Related Components:** K1, K3, S1, S2, S3
**Related Tasks:** T-031-02, 06, 07, 08, 09, 12, 21

**Priority:** High
**Story Points:** 8

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|-------:|---|
| US-1 | Manage speech models and voices from Settings | Pending | High | 8 | 06, 10, 11, 12, 14, 27, 28 |
| US-2 | Switch the speech model and have it take effect | Pending | High | 8 | 02, 03, 04, 05, 15, 20, 24, 29, 37 |
| US-3 | Choose and preview a voice and its speed | Pending | Medium | 3 | 21, 25, 30, 39 |
| US-4 | Pick the microphone and speaker by name | Pending | High | 8 | 13, 16, 17, 18, 19, 24, 25, 31, 37, 39 |
| US-5 | Test the microphone and the speaker | Pending | Medium | 5 | 22, 23, 24, 25, 32, 37, 39 |
| US-6 | Know whether a setting applies now | Pending | Medium | 3 | 13, 26 |
| US-7 | Existing setups keep working and the docs agree | Pending | Medium | 2 | 11, 13, 33, 34, 36 |
| US-8 | Trust what lands in `desktop/stt` and `desktop/tts` | Pending | High | 8 | 02, 06, 07, 08, 09, 12, 21 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | K1, K3, S3, S5, U1 | T-031-06, 10, 11, 12, 14, 27, 28 |
| US-2 | R1, R4, S5, U1 | T-031-02, 03, 04, 05, 15, 20, 24, 29, 37 |
| US-3 | R3, S5, U1 | T-031-21, 25, 30, 39 |
| US-4 | R2, R4, S4, S5, U1 | T-031-13, 16, 17, 18, 19, 24, 25, 31, 37, 39 |
| US-5 | R3, R4, S5, U1 | T-031-22, 23, 24, 25, 32, 37, 39 |
| US-6 | S4, U1 | T-031-13, 26 |
| US-7 | D1, S3, S4 | T-031-11, 13, 33, 34, 36 |
| US-8 | K1, K3, S1, S2, S3 | T-031-02, 06, 07, 08, 09, 12, 21 |

Every AC from AC-1 to AC-73 appears in exactly one story (checked by number: US-1 has 17, US-2 11, US-3 4, US-4 11, US-5 7, US-6 4, US-7 3, US-8 16, total 73). The authoritative AC to task table is in [[T-031-plan]] § Acceptance criterion coverage.

## Links
- [[T-031-summary]] · [[T-031-analysis]] · [[T-031-context-snapshot]] · [[T-031-requirements-draft]] · [[T-031-requirements]] · [[T-031-gap-analysis]] · [[T-031-iteration-log]] · [[T-031-decision-log]]
- [[T-031-user-stories]] · [[T-031-components]] · [[T-031-effort-estimate]] · [[T-031-task-breakdown]] · [[T-031-implementation-plan]] · [[T-031-plan]] · [[T-031-plan-iteration-log]] · [[T-031-critique-report]] · [[T-031-progress]] · [[T-031-verification]] · [[T-031-release]]
