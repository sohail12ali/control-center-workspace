---
ticket: "T-003"
artifact: user-stories
created: "2026-09-06"
---

# User Stories: T-003

User stories describe features from the user perspective with clear acceptance criteria and links to implementation tasks.

**Created by:** `requirements T-003 stories` · **Validated by:** `validate-artifacts T-003 links` · **Verified by:** `validate-artifacts T-003 links`

## Stories

### US-1: No stray console at launch, with an opt-in escape hatch

**As a** Windows user launching the shell (debug or release build)
**I want to** never see a console window pop up, but still be able to opt into one from a terminal
**So that** closing an accidental terminal window never kills my running shell

**Acceptance Criteria:**
- [ ] `desktop/tests/test_pe_subsystem.py` reads the PE header of the built debug exe and asserts subsystem `2`; skips if not built
- [ ] Same assertion against the release exe
- [ ] Manual smoke: zero visible console-class windows on launch, both profiles
- [ ] `--console`/`DESKTOP_CONSOLE=1` on Windows prints to the launching terminal (`desktop/launch.ps1`)
- [ ] `--console` on Linux/macOS is a no-op; `cargo build`/`cargo test` succeed on those CI runners with the gated code present

**Business Rules:** BR-1, BR-2

**Edge Cases:**
- Windows-only APIs (`AttachConsole`/`AllocConsole`, `windows_subsystem`) are `#[cfg(windows)]`-scoped and compile out entirely on POSIX

**Related Components:** A1 main.rs
**Related Tasks:** 1a-2, 1a-4

**Priority:** High
**Story Points:** 3

---

### US-2: Auditable host lifecycle logging

**As a** developer debugging the shell
**I want to** see every host lifecycle event and previously-swallowed error in a rotating log file
**So that** losing the console window doesn't mean losing all diagnostic output

**Acceptance Criteria:**
- [ ] `cargo test` — logger rotation unit test (synthetic writes past 1 MiB trigger rotation to `.1`)
- [ ] `cargo test` — UTC date-conversion unit test
- [ ] Manual smoke: `host.log` has ensure/tray lines after a real launch

**Business Rules:** — (governed by Reliability/Auditability NFRs)

**Edge Cases:**
- `host.log` growth mid-write exceeding 1 MiB rotates to `.1` without losing the in-flight write

**Related Components:** A2 logger.rs, A3 tray.rs
**Related Tasks:** 1a-1, 1a-3, 1a-4

**Priority:** High
**Story Points:** 3

---

### US-3: Single-instance guard, descope-safe

**As a** user who double-launches the shell (shortcut click, `cargo run`, etc.)
**I want to** have the second launch focus the existing window instead of opening a duplicate
**So that** I never end up with two tray icons or two owned server processes

**Acceptance Criteria:**
- [ ] Manual smoke: second launch = one tray icon, existing window shown/focused
- [ ] Second launch during first-instance quit race: callback no-ops cleanly, no crash, no orphaned duplicate
- [ ] If `tauri-plugin-single-instance` fails to link on this toolchain: descope recorded in `T-003-decision-log.md`, both ACs above marked N/A with that citation — not a freeze or build blocker

**Business Rules:** BR-3

**Edge Cases:**
- Plugin link failure on the local xwin/MSVC toolchain → ticket proceeds without it, decision recorded

**Related Components:** A4 single-instance integration
**Related Tasks:** 2a-1, 2a-2

**Priority:** Medium (descope-safe — never blocks the ticket)
**Story Points:** 3

---

### US-4: Defensive no-window hygiene for Python-spawned children

**As a** console server maintainer
**I want to** apply `CREATE_NO_WINDOW` at every named Python spawn site on Windows
**So that** a windowless-parent scenario never surfaces a stray console, even though cause B did not reproduce live

**Acceptance Criteria:**
- [ ] `console/tests/test_procs.py`: monkeypatch `Popen`/`run`, drive each of the six spawn sites, assert `creationflags & 0x08000000` present on `nt`, absent on POSIX
- [ ] Requirement wording (and resulting AC/PR description) states this is defensive hygiene, not a fix for an observed defect

**Business Rules:** BR-4

**Edge Cases:**
- `no_window_flags(extra=...)` on POSIX returns `extra` unchanged (no-op)

**Related Components:** B1 procs.py, B2 six spawn-site edits
**Related Tasks:** 1b-1, 1b-2

**Priority:** Medium
**Story Points:** 2

---

### US-5: Serve output survives, sidecar stays standalone

**As a** developer debugging a shell-started server session
**I want to** find `serve` stdout/stderr in a log file, and have `sidecar.py` keep working without `console/` on `sys.path`
**So that** startup tracebacks aren't silently discarded and the sidecar script stays independently invokable

**Acceptance Criteria:**
- [ ] `desktop/tests/test_sidecar.py` — new assertion that `spawn_serve`'s popen kwargs include a file handle (not `DEVNULL`) for stdout/stderr
- [ ] `desktop/tests/test_sidecar.py` — flag assertion on the taskkill call path (inline constant, no cross-import from `procs.py`)

**Business Rules:** BR-6, BR-8

**Edge Cases:**
- `serve.log` has no rotation policy in T-003 (accepted limitation, BR-8); unbounded growth tracked as a follow-up `todo`

**Related Components:** B3 sidecar.py
**Related Tasks:** 1b-3

**Priority:** Medium
**Story Points:** 2

---

### US-6: A per-OS launch path

**As a** user on Windows, macOS, or Linux
**I want to** install/launch the shell through a documented, scripted path with the right permission/identity plumbing
**So that** later tickets (mic, screenshot permissions) have a stable bundle identity to attach to

**Acceptance Criteria:**
- [ ] `install-launcher.sh` produces a valid `.app` skeleton / `.desktop` file — shell-script test on the Ubuntu CI runner
- [ ] Manual smoke on Windows: shortcut launches, no console window, `--console` still works via `launch.ps1`
- [ ] Re-running any installer/launcher script overwrites existing shortcut/`.desktop`/`.app` files rather than erroring or duplicating

**Business Rules:** BR-5

**Edge Cases:**
- macOS/Linux get CI build-only coverage — no hardware smoke claimed (no machine available)

**Related Components:** C1 Windows scripts, C2 install-launcher.sh, C3 .claude/launch.json
**Related Tasks:** 3b-1, 3b-2, 3b-3

**Priority:** Medium
**Story Points:** 3

---

### US-7: Cross-platform CI build

**As a** maintainer
**I want to** a CI job that compiles and tests the Rust host and desktop Python tests on all three target OSes
**So that** Linux/macOS never silently stop compiling while only Windows hardware exists for manual smoke

**Acceptance Criteria:**
- [ ] `desktop` job added to `.github/workflows/verify.yml` with the correct 3-OS matrix and steps (static review / YAML lint)
- [ ] "Job defined correctly" is claimed now; "green on all three runners" stays PENDING until a user-approved push — never claimed as PASS without that push

**Business Rules:** BR-4 (honesty framing)

**Edge Cases:**
- `ubuntu-latest` leg installs only today's Tauri-build apt prerequisites, not the fuller future-platform table

**Related Components:** D1 verify.yml desktop job
**Related Tasks:** 4a-1

**Priority:** High
**Story Points:** 2

---

### US-8: Close T-001 and T-002

**As a** ticket owner
**I want to** close T-001 and T-002 once their respective completion criteria are met
**So that** the board accurately reflects done work and the assistant programme (T-004+) starts clean

**Acceptance Criteria:**
- [ ] T-001 in `done`, artifact-map row under Completed (all ACs already PASS)
- [ ] Dated "Manual smoke" section exists in `T-002-verification.md` covering rows 4/6/7/8/9 on the release build
- [ ] T-002 in `done`, artifact-map row under Completed

**Business Rules:** BR-7

**Edge Cases:**
- If UIA automation of the native tray menu fails (T-002's known PENDING limitation), the click-through degrades to a manual checklist rather than blocking close

**Related Components:** E1 Close T-001, E2 Close T-002
**Related Tasks:** 5a-1, 5a-2

**Priority:** High
**Story Points:** 2

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|--------|---|
| US-1 | No stray console + escape hatch | Pending | High | 3 | 1a-2, 1a-4 |
| US-2 | Auditable host lifecycle logging | Pending | High | 3 | 1a-1, 1a-3, 1a-4 |
| US-3 | Single-instance guard (descope-safe) | Pending | Medium | 3 | 2a-1, 2a-2 |
| US-4 | Defensive Python spawn hygiene | Pending | Medium | 2 | 1b-1, 1b-2 |
| US-5 | Serve output + standalone sidecar | Pending | Medium | 2 | 1b-3 |
| US-6 | Per-OS launch path | Pending | Medium | 3 | 3b-1, 3b-2, 3b-3 |
| US-7 | Cross-platform CI build | Pending | High | 2 | 4a-1 |
| US-8 | Close T-001/T-002 | Pending | High | 2 | 5a-1, 5a-2 |

## Traceability Matrix

| Story | Components | Tasks |
|-------|-----------|-------|
| US-1 | A1 | 1a-2, 1a-4 |
| US-2 | A2, A3 | 1a-1, 1a-3, 1a-4 |
| US-3 | A4 | 2a-1, 2a-2 |
| US-4 | B1, B2 | 1b-1, 1b-2 |
| US-5 | B3 | 1b-3 |
| US-6 | C1, C2, C3 | 3b-1, 3b-2, 3b-3 |
| US-7 | D1 | 4a-1 |
| US-8 | E1, E2 | 5a-1, 5a-2 |

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements-draft]] · [[T-003-user-stories]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
