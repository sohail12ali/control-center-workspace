---
ticket: "T-003"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
frozen_at: "2026-09-06"
frozen_iteration: 1
created: "2026-09-06"
last_updated: "2026-09-06"
---

# Requirements Draft: T-003

> Working requirements document. **Not frozen.** Expect revisions each iteration until `requirements T-003 freeze` passes.

**Command reference:**
- **Created by:** `requirements T-003 draft`
- **Grounded by:** `analyze T-003` → writes `T-003-context-snapshot.md`
- **Gaps surfaced by:** `challenge-requirements T-003 (gaps dimension)`
- **Challenged by:** `challenge-requirements T-003` (adds ⚠ markers below)
- **Enriched by:** `requirements T-003 enrich [source]`
- **Cross-checked by:** `challenge-requirements T-003 (overlap/conflict/reuse dimension)`
- **Iterated by:** `requirements T-003 iterate "feedback"`
- **Frozen by:** `requirements T-003 freeze` → produces `T-003-requirements-summary.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** Kill the stray console window at shell launch, define a per-OS launch path with a file logger and single-instance guard, add cross-platform CI coverage, and close out T-001/T-002.

**Business driver:** The stray terminal is a live defect the user hits on every launch of the debug build, and closing it kills the shell — reported this session. T-001/T-002 are functionally complete but open, blocking the rest of the assistant programme (T-004–T-007) from starting cleanly.

**Raw intent verbatim:**
> "A second complaint: a terminal window appears when the shell starts, and closing it kills everything." — programme plan `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md § Context`, line 7. Full scope for this ticket: programme plan `§ T-003 — Shell hygiene` (lines 93-139).

## 2. Context Summary

(Condensed from [[T-003-context-snapshot]])

- **Similar existing features:** `desktop/sidecar.py` spawn/kill lifecycle (already OS-aware, `sidecar.py:114-184`) — the pattern `procs.py` and the new launch scripts should follow. Existing `#[cfg(windows)]` / `#[cfg(target_os = "macos")]` gating in `main.rs` — the pattern the new `--console` code follows.
- **Affected code areas:** `desktop/src-tauri/src/{main.rs,logger.rs*,tray.rs,sidecar.rs}` (`*` = new file); `console/server/{procs.py*,agent_session.py,agents.py,agent_tools.py,onboarding.py,worktrees.py}`; `desktop/{sidecar.py,install-shortcut.ps1*,launch.ps1*,install-launcher.sh*}`; `.github/workflows/verify.yml`; `.claude/launch.json*`; `console/tests/test_procs.py*`, `desktop/tests/test_pe_subsystem.py*`, `desktop/tests/test_sidecar.py`.
- **Known risks from history:** T-001 all ACs PASS but not closed; T-002 has 4 PENDING/1 PARTIAL AC blocked on a manual click-through that hasn't been recorded yet ([[T-003-context-snapshot]] § 3).

## 3. Scope

### In scope
- Cause A fix: unconditional `windows_subsystem = "windows"` (both debug and release), `--console`/`DESKTOP_CONSOLE=1` escape hatch, panic-hook logging.
- Host file logger (`logger.rs`) with 1 MiB rotation, `log::info!`/`log::warn!` instrumentation of `main.rs`/`tray.rs` swallowed-error sites.
- Single-instance guard via `tauri-plugin-single-instance` (tech-select gated; descope-safe if it fails to link).
- `sidecar.rs::ensure` gains an `extra_env` map (consumed by a later ticket; T-003 only adds the plumbing).
- Defensive `procs.py` no-window flags applied at the six named Python spawn sites (framed as hygiene, not a defect fix — cause B did not reproduce).
- `sidecar.py` serve-output redirect to `console/.cache/desktop/serve.log`; inline taskkill flag constant (no cross-import from `procs.py`).
- Per-OS launch path: Windows Start-menu shortcut installer + terminal launcher; macOS `.app` skeleton; Linux `.desktop` file; shared `.claude/launch.json`.
- CI: new 3-OS `desktop` job in `.github/workflows/verify.yml` (`cargo build`/`cargo test` + `pytest desktop/tests` on windows-latest/ubuntu-latest/macos-latest).
- Tests: `console/tests/test_procs.py`, `desktop/tests/test_pe_subsystem.py`, sidecar flag assertions, `cargo test` for logger rotation/date conversion.
- Closing T-001 (`close-work`) and T-002 (manual click-through + `close-work`).

### Out of scope (explicit)
- Any assistant feature (persona, `/api/assistant`, fast commands, memory) — T-004.
- Native bridge, tray icon states, screenshot/OCR/clipboard, spoken replies — T-005.
- Microphone capture, VAD, STT engines, hotkey, listen toggle — T-006.
- Multimodal `/send`, region crop UI — T-007.
- Building the `Capture`/`Ocr`/`Tts`/`Stt`/`Clipboard`/`Chime`/`Hotkey` trait system itself — T-003 only respects the *pattern* (cfg-gating + no-op-on-POSIX shape) in its own code (`procs.py`, `main.rs`).
- Installers (NSIS/DMG/AppImage via `cargo tauri build`) — deferred to backlog per programme plan line 111.
- Actual hardware smoke on macOS/Linux — no such machine is available; CI build-only coverage is the ceiling for this ticket (programme plan § "Verification reality").
- Proving the new CI `desktop` job green on all 3 runners inside this analyst/requirements pass — that requires a push, which is ASK-gated; the AC only covers "job added and defined correctly."

### Assumptions
- `tauri-plugin-single-instance = "2"` will resolve and link on the xwin/MSVC toolchain already in use (`desktop/msvc-env.ps1`); if not, T-003 proceeds without it and records the descope in `T-003-decision-log.md` — confirm with stakeholder: **no** — already answered by programme plan line 99 ("Descope (not block) if it fails to link on the xwin toolchain"), not a residual open question.
- The GitHub-hosted `ubuntu-latest`/`macos-latest`/`windows-latest` runners ship a Rust toolchain (confirmed via `actions/runner-images` for Ubuntu: 1.98.0, § 10) and the FR-8 job only apt-installs the subset of `desktop/README.md:38-41`'s existing Tauri-build prerequisites T-003's own `Cargo.toml` diff needs (not the fuller platform-strategy table, which belongs to T-005/T-006) — resolved at iteration 1 (closed CR-1/CR-4/G5), no longer a residual assumption.

## 4. Functional Requirements

### FR-1: Unconditional GUI subsystem (cause A fix)
**Description:** The shell must never present a visible console window, in debug or release builds.

**Actor:** Windows user launching the shell (any build profile).

**Trigger:** Process start.

**Preconditions:**
- None — applies to every launch.

**Flow:**
1. `desktop/src-tauri/src/main.rs:1` changes from `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` to an unconditional `#![windows_subsystem = "windows"]`, itself `#[cfg(windows)]`-scoped so non-Windows builds are unaffected.
2. `desktop/README.md:26` guidance updated so `cargo run` no longer implies a visible console.

**Postconditions / observable outcomes:**
- PE header subsystem field reads `2` (GUI) for both `cargo build` (debug) and `cargo build --release` outputs.
- No visible console-class window appears at launch on either profile.

**Acceptance criteria (testable):**
- [ ] `desktop/tests/test_pe_subsystem.py` reads the PE header of the built debug exe and asserts subsystem `2`; skips if not built.
- [ ] Same assertion against the release exe.
- [ ] Manual smoke (`ticket-scripts/list-console-windows.ps1`) shows zero visible console-class windows on launch, both profiles.

**Business rules invoked:** BR-1

### FR-2: `--console` / `DESKTOP_CONSOLE=1` escape hatch
**Description:** A terminal user can still opt into a visible console for debugging.

**Actor:** Developer/operator launching from a terminal.

**Trigger:** `--console` CLI flag or `DESKTOP_CONSOLE=1` environment variable present at launch.

**Preconditions:** Windows only; on POSIX this flag is a no-op (terminals already show output there).

**Flow:**
1. On Windows, if the flag/env var is set: `AttachConsole(ATTACH_PARENT_PROCESS)`; if that fails (no parent console), `AllocConsole()` (`windows-sys` feature `Win32_System_Console`, new feature addition to the existing `windows-sys` dependency — not a new crate).
2. Panic hook logs to `host.log` via `logger.rs` (FR-3) **on every OS** — the `log` crate itself is cross-platform, so the log write is not gated — then shows the fatal-path UI, which stays exactly as coded today: `alert()`'s existing `#[cfg(windows)]` `MessageBoxW` branch on Windows, `eprintln!` on non-Windows (`main.rs:32-56`, unchanged). Only the *display* mechanism is platform-gated; the *log write* is not. (Resolves CR-2.)
3. `find_repo_root` (`sidecar::find_repo_root`, called from `main.rs:93`) is called before the Tauri builder so logging can start first.

**Postconditions / observable outcomes:**
- `--console` on Windows: launcher's terminal shows the shell's stdout/stderr.
- `--console` on Linux/macOS: no-op, no error, build unaffected (`#[cfg(windows)]`-gated).

**Acceptance criteria (testable):**
- [ ] Manual smoke: `desktop/launch.ps1` passing `--console` prints to the launching terminal (programme plan line 135).
- [ ] `cargo build`/`cargo test` succeed on Linux/macOS CI runners with this code present (proves the cfg-gating compiles clean, not just "doesn't crash").

**Business rules invoked:** BR-2

### FR-3: Host file logger
**Description:** The shell writes a rotating log file recording lifecycle events and previously-swallowed errors.

**Actor:** System (host process).

**Trigger:** Every host lifecycle event: ensure, job-object attach, window open, tray attach, close, quit; every previously `let _ = ...`-discarded Result in `tray.rs` (`tray.rs:32-34,45,55,162-163`).

**Preconditions:** None.

**Flow:**
1. New `desktop/src-tauri/src/logger.rs` using the `log` crate (already resolved in `Cargo.lock` at `0.4.34` via tao/wry — adding it as a direct dependency costs zero new compile).
2. Writes to `console/.cache/desktop/host.log`, append mode, UTC timestamps (no `chrono` dependency), rotates to `.1` at 1 MiB.
3. `log::info!` at: ensure, job, window, tray, close, quit. `log::warn!` at each swallowed `let _ =` site named above.

**Postconditions / observable outcomes:**
- `host.log` exists after any launch and contains at least one `info` line per lifecycle event exercised.
- File never exceeds 1 MiB before rotating (verified by unit test, not by growing a real file to that size in CI).

**Acceptance criteria (testable):**
- [ ] `cargo test` — logger rotation unit test (synthetic writes past 1 MiB trigger rotation to `.1`) — first `#[test]`s in the crate (programme plan line 119).
- [ ] `cargo test` — UTC date-conversion unit test.
- [ ] Manual smoke: `host.log` has ensure/tray lines after a real launch (programme plan line 135).

**Business rules invoked:** — (none directly; governed by the Reliability/Auditability NFR rows, § 5)

### FR-4: Single-instance guard (descope-safe)
**Description:** Launching the shell a second time focuses the existing window instead of opening a duplicate instance.

**Actor:** User double-launching the shell (shortcut click, `cargo run`, etc.).

**Trigger:** Second process start while a first instance is already running.

**Preconditions:** `tauri-plugin-single-instance = "2"` successfully added and linked (see Assumptions — descope if not).

**Flow:**
1. Register the plugin with callback `tray::show_main` (existing function, `tray.rs:30-36`).
2. Second launch: plugin detects the running instance, invokes the callback, new process exits.

**Postconditions / observable outcomes:**
- Second launch results in exactly one tray icon and the existing window shown/focused, never a duplicate process.

**Acceptance criteria (testable):**
- [ ] Manual smoke: second launch = one tray icon (programme plan line 135).
- [ ] Second launch attempted while the first instance is mid-`quitting` (`main.rs:135-145` `CloseRequested`/`Destroyed` race — closes G2): the callback is a no-op if `main` no longer exists, the second process still exits cleanly, no crash, no orphaned duplicate — builder/verifier design the concrete test; requirement states the expected behavior so it isn't dropped.
- [ ] If the plugin fails to link on this toolchain: `T-003-decision-log.md` records the descope decision and both ACs above are marked N/A with that citation — not a freeze blocker either way.

**Business rules invoked:** BR-3

### FR-5: Defensive no-window hygiene for Python-spawned children
**Description:** Every Python subprocess spawn in the console server that could run under a windowless parent gets `CREATE_NO_WINDOW` on Windows, framed explicitly as defensive hygiene — Phase 0 smoke found no observed defect here (cause B did not reproduce).

**Actor:** Console server (any agent/git/onboarding spawn).

**Trigger:** Any of the six named call sites spawning a child process.

**Preconditions:** None.

**Flow:**
1. New `console/server/procs.py`: `CREATE_NO_WINDOW = 0x08000000`; `no_window_flags(extra=0)` returns `extra` unchanged on POSIX (i.e. `{}`/`0` no-op), returns `extra | CREATE_NO_WINDOW` on `nt`; `popen_kwargs()` returns only `creationflags` so callers keep their own stdio wiring.
2. Apply at: `agent_session.py:375` (keep existing `CREATE_NEW_PROCESS_GROUP`, OR it with the new flag), `agent_session.py:507-512` (currently no creationflags — add), `agents.py:209-217`, `agent_tools.py:247-249` (keep `shell=True`, add `stdin=DEVNULL`), `onboarding.py:70-71`, `worktrees.py:57-59`.
3. Decision recorded: flags are unconditional on `nt` for deterministic tests — the `CTRL_BREAK_EVENT` fallback at `agent_session.py:428` was already moot (only reached after stdin died; `stop()` uses `kill()`) — this fact goes to `T-003-decision-log.md`, not re-derived here.

**Postconditions / observable outcomes:**
- On Windows: every named spawn carries `creationflags & 0x08000000`.
- On POSIX: `no_window_flags`/`popen_kwargs` are no-ops; behavior unchanged.

**Acceptance criteria (testable):**
- [ ] `console/tests/test_procs.py`: monkeypatch `Popen`/`run`, drive each of the six spawn sites, assert `creationflags & 0x08000000` present on `nt`, absent on POSIX.
- [ ] Requirement wording (and the resulting AC/PR description) states this is defensive hygiene, not a fix for an observed defect — no claim that a bug was "fixed" here.

**Business rules invoked:** BR-4

### FR-6: `sidecar.py` log capture + standalone import safety
**Description:** The serve process's stdout/stderr survive for debugging, and `sidecar.py` keeps working when imported/run without `procs.py` on the path.

**Actor:** System (sidecar spawn/kill).

**Trigger:** `spawn_serve` (already exists, `sidecar.py:114-145`) and `kill_tree`'s Windows taskkill branch (`sidecar.py:152-159`).

**Preconditions:** None.

**Flow:**
1. `sidecar.py:124-130` (`popen_kw` construction in `spawn_serve`): redirect `stdout`/`stderr` from `subprocess.DEVNULL` to an append-mode file handle on `console/.cache/desktop/serve.log`, so `httpd.py:298`-style startup lines and tracebacks survive (currently discarded).
2. `sidecar.py:152-159` (Windows taskkill call) keeps its own inline `CREATE_NO_WINDOW`-equivalent constant rather than importing from `console/server/procs.py`, because `sidecar.py` must stay importable standalone (it is invoked as a Tauri-shelled script, not necessarily with `console/` on `sys.path`).

**Postconditions / observable outcomes:**
- `console/.cache/desktop/serve.log` contains server stdout/stderr after any shell-started `serve` session.
- `sidecar.py` still passes its existing tests (`desktop/tests/test_sidecar.py`) run in isolation, with no import of `procs.py`.
- `serve.log` has **no rotation policy in this ticket** — unlike `host.log` (FR-3, 1 MiB rotation), it grows unbounded across sessions. This is an accepted, documented limitation for T-003 (closes G1); rotation for `serve.log` is a follow-up `todo`, not new scope here.

**Acceptance criteria (testable):**
- [ ] `desktop/tests/test_sidecar.py` — new assertion that `spawn_serve`'s popen kwargs include a file handle (not `DEVNULL`) for stdout/stderr.
- [ ] `desktop/tests/test_sidecar.py` — flag assertion on the taskkill call path (mirrors `test_procs.py`'s assertion, inline constant, no cross-import).

**Business rules invoked:** BR-6, BR-8

### FR-7: Per-OS launch path
**Description:** Each target OS gets a documented, scripted way to install/launch the shell without a stray console and with the right permission/identity plumbing for later tickets.

**Actor:** User installing/launching the shell on Windows, macOS, or Linux.

**Trigger:** Running the per-OS installer/launcher script.

**Preconditions:** Release build exists (`cargo build --release --manifest-path desktop/src-tauri/Cargo.toml`).

**Flow:**
1. **Windows:** new `desktop/install-shortcut.ps1` writes a Start-menu `.lnk` (`TargetPath` = release exe, `WorkingDirectory` = repo root; `-Desktop`, `-Startup` switches). No `.cmd` launcher (its own console would flash). New `desktop/launch.ps1` for terminal users (`Start-Process`, passes through `--console`).
2. **macOS:** new `desktop/install-launcher.sh` writes a minimal `.app` skeleton (`Contents/Info.plist` with `CFBundleIdentifier = com.noble.deliveryconsole` — matches `tauri.conf.json:5` — plus `NSMicrophoneUsageDescription`, `LSUIElement` off; `Contents/MacOS/` symlink to the release binary). Needed now so mic/Screen Recording permission prompts (T-006/T-005) attach to a stable bundle identity, even though T-003 does not use the mic.
3. **Linux:** same `install-launcher.sh` also writes `~/.local/share/applications/delivery-console.desktop` + icon.
4. New `.claude/launch.json` (net-new file, no collision with `.vscode/launch.json`): `desktop-shell` (release binary) and `console-serve` (`python console/kanban.py serve`, port 8790) entries.
5. Installers (NSIS/DMG/AppImage via `cargo tauri build`) explicitly deferred — recorded as a future `installer` tech-select topic (programme plan line 111), not built here.
6. Re-running any installer/launcher script (`install-shortcut.ps1`, `install-launcher.sh`) **overwrites** the existing shortcut/`.desktop`/`.app` files rather than erroring or duplicating (closes G4) — idempotent by construction, not by an explicit "already exists" check.

**Postconditions / observable outcomes:**
- Windows: a Start-menu shortcut launches the release exe with no console.
- macOS: a `.app` skeleton exists with the correct bundle identifier and required `Info.plist` keys.
- Linux: a `.desktop` file exists pointing at the release binary.

**Acceptance criteria (testable):**
- [ ] `install-launcher.sh` produces a valid `.app` skeleton / `.desktop` file — shell-script test on the Ubuntu CI runner (programme plan line 139).
- [ ] Manual smoke on Windows: shortcut launches, no console window, `--console` still works via `launch.ps1`.
- [ ] macOS/Linux: build-only verification (CI compiles/tests the scripts); no hardware smoke claimed (out of scope, § 3).

**Business rules invoked:** BR-5

### FR-8: Cross-platform CI build
**Description:** A new CI job compiles and tests the Rust host and desktop Python tests on all three target OSes, so Linux/macOS never silently stop compiling while only Windows hardware is available for manual smoke.

**Actor:** CI (GitHub Actions).

**Trigger:** Push / PR to `main`/`development` (existing triggers in `.github/workflows/verify.yml`, unchanged).

**Preconditions:** None beyond the new job definition.

**Flow:**
1. Extend `.github/workflows/verify.yml` with a new `desktop` job, matrix `windows-latest`, `ubuntu-latest`, `macos-latest`. On `ubuntu-latest`: apt-install **only** the prerequisites `desktop/README.md:38-41` already names for a plain Tauri build (`libwebkit2gtk-4.1-dev build-essential libssl-dev librsvg2-dev patchelf pkg-config`) — **not** the fuller platform-strategy table's audio/appindicator/xcb rows (`libasound2-dev`, `libxcb*`, `libayatana-appindicator3-dev`), since T-003's own `Cargo.toml` diff (`log`, `tauri-plugin-single-instance`) needs none of those; they belong to T-005/T-006 when those crates land (resolves CR-1, scoped per [[T-003-gap-analysis]] resolution). No Rust-toolchain setup/pin step is added — all three runner images ship a preinstalled Rust toolchain (Ubuntu 24.04 confirmed: Rust 1.98.0/Cargo 1.98.0, `actions/runner-images` `Ubuntu2404-Readme.md`) comfortably above `rust-version = "1.77"`; relying on it unpinned is a deliberate minimal-scope choice for this ticket (resolves CR-4/G5).
2. Each runner: `cargo build --release` + `cargo test` with default features, plus `python -m pytest desktop/tests`.

**Postconditions / observable outcomes:**
- The workflow file defines the job correctly (valid YAML, correct matrix, correct steps) — verifiable by static review and a local `actionlint`/YAML-parse check if available.
- Whether the job is actually green on all three runners can only be confirmed after a push, which is ASK-gated (harness rule: push is not autonomous).

**Acceptance criteria (testable):**
- [ ] `desktop` job added to `.github/workflows/verify.yml` with the correct 3-OS matrix and steps (static review / YAML lint).
- [ ] ⚠ "CI `desktop` job green on all three runners" (programme plan line 139 AC wording) is honestly split: **defined-correctly** is an AC gated at freeze/build; **actually green** is PENDING until the user allows a push — never claimed as PASS without that push.

**Business rules invoked:** BR-4 (honesty framing)

### FR-9: Close T-001
**Description:** T-001 (native Tauri shell) moves to `done` now that its one open note (the debug-subsystem defect) is tracked here.

**Actor:** Analyst/verifier (via `close-work`).

**Trigger:** T-003's cause-A fix lands (FR-1).

**Preconditions:** All T-001 ACs already PASS (`knowledge-center/artifacts/T-001/T-001-verification.md`, per programme plan line 28).

**Flow:**
1. `close-work T-001` as-is — all ACs PASS.
2. One line added noting the debug-subsystem defect is tracked/fixed under T-003 (programme plan line 137).

**Postconditions / observable outcomes:**
- T-001 lane = `done`; artifact-map row moved to Completed.

**Acceptance criteria (testable):**
- [ ] T-001 in `done`, artifact-map row under Completed (programme plan line 139).

**Business rules invoked:** BR-7

### FR-10: Close T-002
**Description:** T-002 (tray remote) moves to `done` after its one remaining verification gap — a manual click-through of the native menu — is recorded.

**Actor:** Verifier (manual click-through) then `close-work`.

**Trigger:** Release build available with FR-1 through FR-4 applied.

**Preconditions:** T-002 currently 9 PASS / 4 PENDING / 1 PARTIAL — native menu clicks aren't automatable (programme plan line 28).

**Flow:**
1. 5-minute manual click-through of Phase 0 smoke rows 4/6/7/8/9 on the release build, recorded under a dated "Manual smoke" header in `T-002-verification.md` (programme plan line 137).
2. `close-work T-002`.

**Postconditions / observable outcomes:**
- T-002 lane = `done`; artifact-map row moved to Completed.

**Acceptance criteria (testable):**
- [ ] Dated "Manual smoke" section exists in `T-002-verification.md` covering rows 4/6/7/8/9.
- [ ] T-002 in `done`, artifact-map row under Completed (programme plan line 139).

**Business rules invoked:** BR-7

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Portability | Nothing in this ticket may break the Linux/macOS build | `cargo build` + `cargo test` succeed on ubuntu-latest and macos-latest CI runners (hard NFR) | `#![windows_subsystem]`/`--console`/`AllocConsole` code `#[cfg(windows)]`-gated; `procs.py` no-op on POSIX; launcher scripts are per-OS files, not one script branching internally |
| Reliability | Log file must not grow unbounded | Rotate `host.log` at 1 MiB to `.1` (single backup, no multi-generation retention) | `logger.rs`, unit-tested (FR-3) |
| Determinism | No-window flags must be unconditional, not probabilistic | `creationflags & 0x08000000` present on every named spawn site on `nt`, always, for deterministic tests | Avoids flaky "sometimes a console flashes" behavior (programme plan line 105) |
| Auditability | Every host lifecycle event and every previously-swallowed error is logged | `log::info!`/`log::warn!` at the 6 named sites in `tray.rs` + `main.rs` lifecycle points (FR-3) | Replaces silent `let _ = ...` |
| Honesty (CI) | CI job correctness is provable pre-push; actual tri-OS green is not | AC split: "job defined correctly" (provable now) vs. "green on all 3 runners" (PENDING until a user-approved push, per harness ASK gate) | Never claim green without evidence |
| Compatibility | Existing `python -m pytest` baseline (758 passed) must not regress | 758 passed (or more, if new tests are added) after this ticket, zero new failures | Baseline recorded `T-003-verification.md` row 9 |
| Security | N/A — no new network-facing surface | N/A | Single-instance plugin and file logger are local-only; no bridge/HTTP server is introduced in T-003 (that's T-005) |
| Compliance | N/A | N/A | No user data, no regulated data touched by this ticket |
| Performance | N/A — no latency/throughput target applies | N/A | Shell hygiene changes startup plumbing only; no user-facing operation is timed by this ticket (enriched per [[T-003-gap-analysis]] G3) |
| Scalability | N/A — single-user desktop process | N/A | Not a multi-tenant/concurrent-load system (enriched per [[T-003-gap-analysis]] G3) |
| Availability | N/A — no uptime SLA | N/A | Local desktop app; "available" = "process running," already covered by the single-instance/tray ACs (enriched per [[T-003-gap-analysis]] G3) |
| Usability | Second launch focuses the existing window instead of opening a duplicate | Exactly one tray icon, one window, after any number of relaunches | FR-4 (enriched per [[T-003-gap-analysis]] G3) |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `host.log` | new | UTC timestamp, level, message | append, rotate to `.1` at 1 MiB, never deleted automatically | `console/.cache/desktop/host.log` (FR-3) |
| `serve.log` | new | raw stdout/stderr lines from `kanban.py serve` | append, no rotation in this ticket — explicit accepted limitation, BR-8 | `console/.cache/desktop/serve.log` (FR-6) |
| `.claude/launch.json` | new | named launch configs (`desktop-shell`, `console-serve`) | static, hand-maintained, not runtime-mutated | (FR-7) |

### Data flows
Host lifecycle events / swallowed errors → `logger.rs` → `host.log` (append, local file, never transmitted). `kanban.py serve` stdout/stderr → OS pipe → `serve.log` (append, local file). No network transmission, no external system involved in either flow.

### Retention / archival
- `host.log`: single rotation generation (`.1`); no automatic deletion — operator/OS disk-management concern, out of scope.
- `serve.log`: unbounded growth across sessions — an accepted, explicit limitation for T-003 (BR-8), not a silent gap; rotation is a follow-up `todo`.

## 7. Business Rules

Number each `BR-{n}`. Each is atomic.

- **BR-1:** The GUI subsystem (`windows_subsystem = "windows"`) applies to every Windows build profile (debug and release) unconditionally — never gated on `debug_assertions`.
- **BR-2:** Every Windows-only API call (`AttachConsole`/`AllocConsole`, `windows_subsystem`) is `#[cfg(windows)]`-scoped; on POSIX these code paths compile out entirely, never run as a silent no-op at runtime that still costs a compile dependency.
- **BR-3:** A `tauri-plugin-single-instance` link failure on this toolchain is a descope (ticket proceeds without it, decision recorded), never a build blocker.
- **BR-4:** No claim of "fixed" or "green" is made without direct evidence: cause B is "defensive hygiene, not an observed-defect fix"; the CI `desktop` job is "defined correctly" pre-push and "green" only after a user-approved push confirms it.
- **BR-5:** Installer packaging (NSIS/DMG/AppImage) is out of scope for T-003; only unpackaged launch scripts are in scope.
- **BR-6:** `desktop/sidecar.py` must remain importable and functional standalone, with no import dependency on `console/server/procs.py` or any other `console/server/*` module.
- **BR-7:** T-001/T-002 close only after their respective closing criteria (FR-9, FR-10) are met — T-002 specifically requires the recorded manual click-through before `close-work`.
- **BR-8:** `serve.log` rotation/retention is explicitly out of scope for T-003 (unbounded growth is an accepted, documented limitation, not a silent gap); only `host.log` (FR-3) gets a rotation policy in this ticket.

## 8. Edge Cases

- `cargo build`/`cargo test` on ubuntu-latest/macos-latest CI runners must succeed with the Windows-only code paths (`--console`, single-instance callback wiring, `windows-sys` `Win32_System_Console` feature) present but `#[cfg(windows)]`-excluded — expected: clean compile, zero Windows-only symbols referenced.
- `tauri-plugin-single-instance` fails to link on the local xwin/MSVC toolchain — expected: ticket proceeds without it, `T-003-decision-log.md` records the descope, FR-4's AC is marked N/A with that citation (not a freeze or build blocker).
- `--console` flag/`DESKTOP_CONSOLE=1` passed on Linux/macOS — expected: no-op, no error, no console behavior change (there is no "hidden by default" state to escape from on those OSes per the platform table).
- `procs.py.no_window_flags(extra=...)` called with a non-zero `extra` on POSIX — expected: returns `extra` unchanged (no `CREATE_NO_WINDOW` bit ever set on POSIX, since the constant doesn't exist there).
- `host.log` growth mid-write exceeding 1 MiB — expected: rotates to `.1` without losing the in-flight write (verified by the `cargo test` rotation unit test, not a live multi-GB fixture).
- Second launch racing with the first instance's shutdown (`quitting` state, `main.rs:135-145`) — the plugin's callback (`tray::show_main`) is a no-op if no window exists; expected: second process still exits, no crash, no hung duplicate — closed via the explicit AC added to FR-4 (G2).
- CI `ubuntu-latest` runner missing an apt prerequisite — expected: the new `desktop` job's steps install exactly the subset of `desktop/README.md:38-41`'s prerequisites T-003's own `Cargo.toml` diff needs (not the fuller platform-strategy table, deliberately — see FR-8), so nothing beyond that stated list is assumed pre-installed.

## 9. Interactions with Existing Features

(Populated by `challenge-requirements T-003 (overlap/conflict/reuse dimension)`)

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[T-001]] native Tauri shell (`main.rs`, `sidecar.rs`) | modify (subsystem, logger, single-instance, extra_env) | low | modify |
| [[T-002]] tray remote (`tray.rs`) | modify (log::warn! wiring at 4 existing swallowed-error sites; single-instance callback = existing `show_main`) | low | modify |
| `desktop/sidecar.py` spawn/kill lifecycle | modify (log redirect, inline kill constant) | low | modify |
| `console/server/agent_session.py`, `agents.py`, `agent_tools.py`, `onboarding.py`, `worktrees.py` (six spawn sites) | modify (add `procs.py` flags) | low | modify |
| `.github/workflows/verify.yml` (existing `tests`/`harness`/`cli` jobs) | extend (add sibling `desktop` job) | medium — malformed YAML could break existing jobs if not isolated | isolate (new job block, no edits to existing jobs) |
| Platform-strategy trait/registry pattern (T-004–T-007's `Capture`/`Ocr`/`Tts`/etc.) | pattern reuse only — no shared code | low | isolate (T-003 respects the cfg-gating *shape*, builds none of the trait system) |
| `desktop/msvc-env.ps1` (existing MSVC env script) | reuse (unchanged, still required pre-build) | low | reuse |

## 10. External Dependencies

- `tauri-plugin-single-instance` crate (v2) — not yet in `Cargo.lock`; requires a `tech-select` pass (topic `single-instance`, confirm-existing mode) before the builder adds it; descope-safe if it fails to link (programme plan line 99, this draft's Assumptions).
- `windows-sys` crate, new feature `Win32_System_Console` — existing dependency (`Cargo.toml`, currently features: Foundation, Security, JobObjects, Threading, UI_WindowsAndMessaging), adding a feature flag, not a new crate.
- `log` crate (0.4) — already resolved transitively in `Cargo.lock` at `0.4.34`; adding as a direct dependency in `Cargo.toml` costs zero new compile.
- GitHub Actions hosted runners `windows-latest`, `ubuntu-latest`, `macos-latest` — needed for the new CI job; actual green-on-all-3 confirmation requires a push (ASK-gated, not exercised in this analyst pass). Confirmed (enrich, external source): GitHub's `actions/runner-images` Ubuntu 24.04 image ships Rust 1.98.0 / Cargo 1.98.0 preinstalled under "Rust Tools" — comfortably above this project's `rust-version = "1.77"` (`desktop/src-tauri/Cargo.toml`), so FR-8 relies on the runner's preinstalled toolchain with no explicit pin/setup step, a deliberate minimal-scope choice for this ticket (closes CR-4/G5).
- MSVC/xwin toolchain (`desktop/msvc-env.ps1`) — required locally to build/test the Rust host on this machine; no change needed, already in place.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Ticket owner / sole stakeholder | Sohail Ali | Stray console fixed, T-001/T-002 closed cleanly, no Linux/macOS build breakage | yes — given via the approved programme plan (`our-project-is-in-optimized-treasure.md`, user answers dated 2026-09-06); this draft is a faithful transcription, not new scope, so no additional sign-off round is required unless challenge-requirements surfaces a genuine deviation |

## 12. Open Questions (mirrored)

Mirrored from `T-003-questions.toml` (`console/kanban.py tracker list T-003 questions`). Blocker questions must be resolved before freeze.

- None open. The programme plan resolved scope, the descope conditions (single-instance, CI-green timing), and the cause-A/cause-B framing explicitly; no residual stakeholder-facing ambiguity was found during drafting. The one genuine implementation-level uncertainty — whether `tauri-plugin-single-instance` links on this toolchain — is captured as an edge case (§ 8) and covered by FR-4's descope-safe ACs, not a blocking question (its outcome is only known at build time, and either outcome is already an acceptable, planned path).

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements T-003`. Each must be resolved or explicitly accepted before freeze.)

All 4 findings from the 2026-09-06 `challenge-requirements` pass are closed as of iteration 1 — see [[T-003-critique-report]] for the CR-{n} table and [[T-003-iteration-log]] for the closing entry:
- CR-1 (ambiguity, FR-8 apt-prerequisite scope) — resolved: FR-8 now scopes to today's Tauri-build prerequisites only.
- CR-2 (ambiguity, FR-2 panic-hook cross-platform scope) — resolved: FR-2 now states the log write is cross-platform, the display path stays as already coded.
- CR-3 (nfr-unmeasurable, NFR Portability row) — accepted: governed by BR-4, called out in the NFR table.
- CR-4 (unstated-assumption, Rust-toolchain provisioning) — resolved: FR-8 and § 10 now cite the confirmed GH-runner Rust version.

No open findings remain.

## 14. Draft History

See [[T-003-iteration-log]] for per-iteration diff + rationale.

Current iteration: **1**

---

## Freeze Checklist (run by `requirements freeze`)

- [ ] All `〈TBD〉` placeholders replaced or explicitly deferred
- [ ] All ⚠ findings resolved or explicitly accepted with rationale
- [ ] All blocker open questions answered
- [ ] Every FR has at least one testable acceptance criterion
- [ ] Every NFR has a concrete target or documented reason for absence
- [ ] Every new/changed entity has a canonical reference or creation plan
- [ ] Out-of-scope list is non-empty
- [ ] Stakeholder sign-off recorded
- [ ] `T-003-requirements-summary.md` generated for `requirements stories` consumption

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements-draft]] · [[T-003-context-snapshot]] · [[T-003-gap-analysis]] · [[T-003-iteration-log]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
