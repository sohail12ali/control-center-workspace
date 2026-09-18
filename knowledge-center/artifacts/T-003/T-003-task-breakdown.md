---
ticket: "T-003"
artifact: task-breakdown
---

# Task breakdown: T-003

Atomic tasks per slice, with acceptance criteria and effort. Task ID format: `{phase}-{slice}-{task}`.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis step), `estimate(mode=forecast)`.

---

## Phase 1: Host logging & Python spawn hygiene foundation

### Slice 1a: Rust logger + cause-A fix

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1a-1 | New `desktop/src-tauri/src/logger.rs`: `log` crate direct dep, writes `console/.cache/desktop/host.log`, append, UTC timestamps, rotate to `.1` at 1 MiB | A2 | FR-3 | `cargo test` rotation unit test (synthetic writes past 1 MiB trigger rotation); `cargo test` UTC date-conversion unit test | 2 (actual 1.5) | done | root, no deps |
| 1a-2 | `main.rs:1` → unconditional `#![windows_subsystem = "windows"]` (`#[cfg(windows)]`-scoped); `--console`/`DESKTOP_CONSOLE=1` → `AttachConsole`/`AllocConsole` (`windows-sys` feature `Win32_System_Console`); panic hook logs via `logger.rs` on every OS, `alert()` display path unchanged; `find_repo_root` called before the Tauri builder | A1 | FR-1, FR-2 | `test_pe_subsystem.py` asserts subsystem `2` on debug exe; manual smoke: zero console windows both profiles; `--console` prints to launching terminal (Windows); no-op on Linux/macOS — **cross-OS compile-clean claim is actually confirmed by 4a-1's CI job, not locally (no Linux/macOS hardware here)** | 2 (actual 1.5) | done | depends on 1a-1. Live-smoked on the DEBUG exe: `test_pe_subsystem.py` passes (subsystem 2), `list-console-windows.ps1` shows zero visible console windows on a plain launch, `--console` allocates a visible `ConsoleWindowClass` window owned by the host pid. Release-profile smoke deferred to 3a-1. |
| 1a-3 | `tray.rs:32-34,45,55,162-163` — replace `let _ = ...` with `log::warn!` on each swallowed error | A3 | FR-3 | `host.log` contains warn lines for each named site after a real launch (manual smoke) | 1 | done | depends on 1a-1. Code-reviewed and live-confirmed for the ensure/job/window/tray lifecycle lines (host.log); the specific swallowed-error `warn!` sites (show_main/eval_tray/request_quit/desktop-session listener) are only reachable via tray-menu clicks, which need UI automation this pass didn't attempt (matches T-002's own known tray-menu-automation limitation) — recorded as code-verified, not live-exercised. |
| 1a-4 | `desktop/README.md:26` update (`cargo run` no longer implies a console) | A1 | FR-1 | doc reviewed, matches actual behavior | 0.5 | done | depends on 1a-2 |

### Slice 1b: Python spawn hygiene

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1b-1 | New `console/server/procs.py`: `CREATE_NO_WINDOW = 0x08000000`; `no_window_flags(extra=0)`; `popen_kwargs()` | B1 | FR-5 | module importable, no-op on POSIX (returns `extra` unchanged) | 1 (actual 0.5) | done | root, no deps |
| 1b-2 | Apply flags at `agent_session.py:375,507-512`, `agents.py:209-217`, `agent_tools.py:247-249` (keep `shell=True`, add `stdin=DEVNULL`), `onboarding.py:70-71`, `worktrees.py:57-59`; wording states hygiene, not a fix | B2 | FR-5 | `console/tests/test_procs.py`: monkeypatch `Popen`/`run`, assert `creationflags & 0x08000000` on `nt`, absent on POSIX, for all six sites | 2 (actual 1.5) | done | depends on 1b-1 |
| 1b-3 | `sidecar.py:124-130` redirect stdout/stderr to append handle on `console/.cache/desktop/serve.log`; `sidecar.py:152-159` taskkill keeps its own inline `CREATE_NO_WINDOW`-equivalent constant (no import of `procs.py`) | B3 | FR-6 | `desktop/tests/test_sidecar.py`: popen kwargs include a file handle (not `DEVNULL`); taskkill flag assertion on the inline constant; existing sidecar tests still pass standalone | 1.5 (actual 1) | done | root, deliberately isolated from 1b-1 |

### Slice 1c: sidecar.rs plumbing

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1c-1 | `sidecar.rs::ensure` gains an `extra_env` map (unused by T-003 itself, consumed by a later ticket) | A5 | scope note (no direct FR) | compiles clean, map threaded through `ensure`'s signature, no behavior change | 0.5 (actual 0.3) | done | root, no deps |

**Phase 1 total: 8h**

---

## Phase 2: Single-instance guard (tech-select gated)

### Slice 2a: dependency add

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2a-1 | `tech-select T-003 single-instance --mode confirm-existing` — validate `tauri-plugin-single-instance = "2"` (programme plan pick) against the xwin/MSVC toolchain before adding it | — (gate, no code) | FR-4 | decision recorded in `T-003-decision-log.md` (already has the pick pre-staged; this run confirms it links, or records the descope) | 1 (actual 0.4) | done | **builder-stage task**, run before 2a-2. Confirmed: resolves to `2.4.4`, `cargo build` compiles clean (~48 new transitive crates, mostly `windows-*`/`zbus` for the Linux/Windows backends) — no link failure, no descope. `## tech-single-instance-confirm-existing` appended to decision-log. |
| 2a-2 | Add `tauri-plugin-single-instance = "2"` to `Cargo.toml`; register in `main.rs` builder with callback `tray::show_main` | A4 | FR-4 | manual smoke: second launch = one tray icon; quit-race: callback no-ops cleanly, no crash, no orphaned duplicate; **if 2a-1 reports a link failure: this task descopes — mark N/A with the decision-log citation, not a blocker** | 2 (actual 0.5) | done | depends on 2a-1, 1a-2 (main.rs), 1a-3 (tray.rs callback target). Live-smoked: launched twice — second launch logs `single-instance: second launch detected, focusing the existing window` and exits immediately; `Get-Process` shows exactly one `delivery-console-desktop` host throughout. Quit-race not separately exercised (no crash observed across two full launch/quit cycles this session). |

**Phase 2 total: 3h**

---

## Phase 3: Release build & per-OS launch path

### Slice 3a: release build

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3a-1 | `cargo build --release --manifest-path desktop/src-tauri/Cargo.toml` (after `. .\desktop\msvc-env.ps1`) — **long-running, multi-minute; do not interleave with other Rust edits** | A6 | FR-1, FR-3, FR-4, FR-7 (verification) | `test_pe_subsystem.py` against the release exe asserts subsystem `2`; rerun Phase 0 smoke rows 1-8 on the release build per the programme plan table | 2.5 (actual 1.5) | done | depends on 1a-1, 1a-2, 1a-3, 2a-2 (or its descope). Release build: 3m42s. `test_pe_subsystem.py` passes (subsystem 2). Rows re-verified live: row 1 (subsystem 2 ✓), row 3 (window+tray, zero visible console/conhost ✓ via `list-console-windows.ps1`+`probe-processes.ps1`), row 4 (`api/config` ok ✓), row 7-equivalent (`CloseMainWindow()` → process stays alive, window hidden, port stays up ✓), row 8/9-equivalent (force-kill host → job object also kills the owned serve process, port goes down ✓). Rows 5/6 (agent-chat-spawns-no-console) and the literal tray-menu Quit click not automated this pass (needs UI automation / configured agent CLIs — same class of limitation as T-002's own PENDING tray-menu rows). |

### Slice 3b: per-OS launch scripts

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3b-1 | New `desktop/install-shortcut.ps1` (Start-menu `.lnk`, `-Desktop`/`-Startup` switches, idempotent overwrite) + `desktop/launch.ps1` (`Start-Process`, `--console` passthrough) | C1 | FR-7 | manual smoke on Windows: shortcut launches, no console, `--console` works via `launch.ps1`; re-run overwrites cleanly | 2 (actual 1.2) | done | depends on 3a-1 (release exe must exist to point the shortcut at). `install-shortcut.ps1`'s `.lnk`-writing logic (COM `WScript.Shell`, TargetPath/WorkingDirectory, idempotent overwrite) verified against a scratch path — not run against the real Start Menu/Desktop/Startup this pass (writes outside the repo, ASK-gated; ready for the user to run directly). `launch.ps1` live-smoked twice on the release exe: default launch shows a visible `ConsoleWindowClass` window (`--console` passthrough confirmed); `-NoConsole` launches silently. **Bug found and fixed during smoke**: `Start-Process -ArgumentList @()` (empty array) throws on PowerShell 5.1 — switched to a splatted hashtable that only adds the `ArgumentList` key when non-empty. |
| 3b-2 | New `desktop/install-launcher.sh`: macOS `.app` skeleton (`Info.plist` with `CFBundleIdentifier`, `NSMicrophoneUsageDescription`, `LSUIElement` off; `Contents/MacOS/` symlink) + Linux `~/.local/share/applications/delivery-console.desktop` + icon | C2 | FR-7 | shell-script test on the Ubuntu CI runner validates `.app`/`.desktop` structure; build-only coverage stated explicitly — no macOS/Linux hardware smoke claimed | 2 (actual 1.3) | done | depends on 3a-1 conceptually. Added a `--target=macos\|linux` override so one runner (incl. this Windows machine's Git Bash) can validate both code paths' file structure — the `.app` skeleton is pure file/plist writing, no macOS-only syscall. 4 new tests in `desktop/tests/test_install_launcher.py`, all pass under Git Bash on this machine (real `ubuntu-latest` execution deferred to 4a-1's CI job). **Bug found and fixed during test-writing**: a bare `"bash"` handed to Python's `subprocess.run` on Windows resolved to the WSL launcher stub (`System32\bash.exe`), not Git Bash, even though `shutil.which("bash")` finds Git Bash first — fixed by resolving the full path once via `shutil.which` and passing that instead of the bare name. |
| 3b-3 | New `.claude/launch.json`: `desktop-shell` (release binary) + `console-serve` (`python console/kanban.py serve`, port 8790) entries | C3 | FR-7 | file reviewed, both entries resolve to correct paths/commands | 0.5 (actual 0.2) | done | root, no deps. VS Code-`launch.json`-shaped (`configurations` array, name/description/program/args/cwd); validated as well-formed JSON. Not consumed by any code path yet — descriptive/for future editor or agent launchers. |

**Phase 3 total: 7h**

---

## Phase 4: CI

### Slice 4a: desktop CI job

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4a-1 | Extend `.github/workflows/verify.yml` with new `desktop` job: matrix `windows-latest`/`ubuntu-latest`/`macos-latest`; `ubuntu-latest` apt-installs only today's Tauri-build prerequisites (`libwebkit2gtk-4.1-dev build-essential libssl-dev librsvg2-dev patchelf pkg-config`); no Rust-toolchain pin/setup step; each runner: `cargo build --release` + `cargo test` + `python -m pytest desktop/tests` | D1 | FR-8 | job added with correct 3-OS matrix and steps, verified by static review/YAML lint — **"defined correctly" claimed now; "green on all 3 runners" stays PENDING until an ASK-gated push, never claimed as PASS without it** | 1.5 (actual 0.7) | done | root; references test files from 1a-1/1b-2/1b-3/3a-1 but not code-coupled. Existing `tests`/`harness`/`cli` jobs untouched. `yaml.safe_load` confirms well-formed YAML + exact 3-OS matrix. apt list matches decision-log verbatim; no Rust-toolchain step (runner-preinstalled version, per decision-log). All new/changed Python tests reviewed for cross-OS safety (monkeypatched `os.name`, graceful skip with no built exe, portable POSIX shell). **"Defined correctly" is what's claimed here — "green on all 3 runners" stays PENDING until an ASK-gated push.** |

**Phase 4 total: 1.5h**

---

## Phase 5: Close T-001/T-002

### Slice 5a: close tickets

| Task ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|--------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 5a-1 | `close-work T-001` — all ACs already PASS; add one line noting the debug-subsystem defect is tracked/fixed under T-003 | E1 | FR-9 | T-001 lane = `done`; artifact-map row moved to Completed | 0.5 | pending | depends on 1a-2 (cause-A fix landed); **execution belongs to verifier/harness at VERIFY stage, planned here for traceability only** |
| 5a-2 | 5-minute manual click-through of Phase 0 smoke rows 4/6/7/8/9 on the release build, recorded under a dated "Manual smoke" header in `T-002-verification.md`; then `close-work T-002` | E2 | FR-10 | dated "Manual smoke" section exists covering rows 4/6/7/8/9; T-002 lane = `done`; artifact-map row moved to Completed; **if UIA automation of the tray menu fails (T-002's known PENDING limitation), degrade to the manual checklist — does not block close** | 1 | pending | depends on 3a-1 (release build must exist); **execution belongs to verifier/harness at VERIFY stage, planned here for traceability only** |

**Phase 5 total: 1.5h**

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 1 — Host logging & Python spawn hygiene | 8 | 8 (actual 7.8) | 0 | 0 | 100% |
| Phase 2 — Single-instance guard | 3 | 3 (actual 0.9) | 0 | 0 | 100% |
| Phase 3 — Release build & launch path | 7 | 7 (actual 4.2) | 0 | 0 | 100% |
| Phase 4 — CI | 1.5 | 1.5 (actual 0.7) | 0 | 0 | 100% |
| Phase 5 — Close T-001/T-002 | 1.5 | 0 | 0 | 1.5 | 0% |
| **Total** | **21** | **19.5 (actual 13.6)** | **0** | **1.5** | **93%** |

Cross-check: 17 tasks total 21h dev-authored effort (8+3+7+1.5+1.5=21h, after `challenge-plan` CR-5 bumped 3a-1 from 1.5h→2.5h). 21h sits comfortably under the upfront estimate's Dev Lower bound of 32.2h — no `>10% over upper bound` flag, no `replan` trigger.

## Links
- [[T-003-summary]] · [[T-003-plan]] · [[T-003-components]] · [[T-003-task-breakdown]] · [[T-003-implementation-plan]] · [[T-003-effort-estimate]]
