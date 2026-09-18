---
ticket: "T-003"
artifact: analysis
---

# Analysis: T-003

## Context

T-003 is the first ticket of a user-approved 5-ticket programme (T-003–T-007, [[our-project-is-in-optimized-treasure]] — `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md`, hereafter "programme plan") that turns the Delivery Console's Tauri tray (T-001, T-002) into a voice assistant. T-003 itself carries no assistant scope — it is shell hygiene: kill the stray console window the user hits today, define the per-OS launch path, add a file logger and single-instance guard, stand up a 3-OS CI build, and close out T-001/T-002. Phase 0 smoke already ran (`T-003-verification.md § Ground truth (before)`) and is treated as fixed evidence, not re-derived here.

## Current State

**Cause A — confirmed live.** `desktop/src-tauri/src/main.rs:1` reads `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` — the GUI subsystem applies only to release builds. `desktop/README.md:26` documents `cargo run --manifest-path desktop/src-tauri/Cargo.toml`, i.e. a debug build, as the run command. Phase 0 check #1 read the debug exe's PE header and got subsystem `3` (CONSOLE); check #3 found exactly one visible console-class window (`CASCADIA_HOSTING_WINDOW_CLASS`, WindowsTerminal.exe) titled with the exe path — the host process's own window (`T-003-verification.md` rows 1, 3). Check #7 confirms closing it detaches/kills the host.

**Cause B — did not reproduce.** Phase 0 checks #5 (claude chat) and #6 (cursor-agent chat) found child processes spawned under the already-hidden serve console with **no new visible console window** (`T-003-verification.md` rows 5, 6). The spawn sites the programme plan names as lacking `CREATE_NO_WINDOW` are real:
- `console/server/agent_session.py:370-376` (`LiveSession.start`, `creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)` only)
- `console/server/agent_session.py:507-512` (`_deliver` turn spawn, no creationflags at all)
- `console/server/agents.py:209-217` (onboarding/background job spawn)
- `console/server/agent_tools.py:247` (`shell=True` command tool)
- `console/server/onboarding.py:70-71`
- `console/server/worktrees.py:57-59` (`_git`)

but none produced an observed new window in the live probe, because they inherit the parent server process's console handle, and that console is already hidden (`desktop/sidecar.py:131-139` already sets `CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB` when spawning `serve` itself). This is the load-bearing fact that shapes scope: the `procs.py` flags for these six sites are **defensive hygiene**, not a fix for an observed defect.

**Sidecar chain is already correct.** `desktop/sidecar.py:114-145` (`spawn_serve`) and `:148-184` (`kill_tree`) are already OS-aware (Windows creationflags / POSIX `start_new_session` + `killpg`). `desktop/sidecar.py:153` taskkill uses an inline PID kill, not the flags constant — it needs its own inline constant per the plan (the file must stay importable standalone, i.e. no import from a new `procs.py`).

**No dependency for single-instance today.** `desktop/src-tauri/Cargo.toml` lists `tauri`, `serde`, `serde_json`, `url`, and Windows-only `windows-sys 0.59` (features: Foundation, Security, JobObjects, Threading, UI_WindowsAndMessaging — no `Win32_System_Console` yet). `tauri-plugin-single-instance` does not appear anywhere in `Cargo.lock` (grep confirmed) — it is a net-new dependency requiring a `tech-select` pass before it is added at build time. `log` **is** already in `Cargo.lock` at `0.4.34` (line 1765), pulled in transitively (tao/wry), but not yet a direct dependency in `Cargo.toml` — adding `log = "0.4"` directly resolves to the existing lock entry (zero new compile).

**CI is Python-only, Ubuntu-only.** `.github/workflows/verify.yml` runs three jobs (`tests` matrix py3.11/3.13, `harness` lint, `cli` smoke), all on `ubuntu-latest`, none touching `desktop/` or `cargo`. No `desktop` job exists yet.

**Swallowed `let _ =` sites confirmed** in `desktop/src-tauri/src/tray.rs`: lines 32-34 (`show_main`: show/unminimize/set_focus), 45 (`eval_tray`), 55 (`request_quit`'s window close), 162-163 (session-backend header + mute checkbox sync). These are the `log::warn!` targets the plan specifies.

**Identifier for macOS bundle** is already set: `desktop/src-tauri/tauri.conf.json:5` `"identifier": "com.noble.deliveryconsole"`.

**Test scaffolding**: `pytest.ini` `testpaths = console/tests desktop/tests`; neither `console/tests/test_procs.py` nor `console/server/procs.py` exist yet (both net-new). `desktop/tests/` currently holds `test_features.py`, `test_sidecar.py` (no `test_pe_subsystem.py` yet).

**Baseline**: `python -m pytest` = 758 passed (`T-003-verification.md` row 9), before any change in this ticket.

**T-001/T-002 status**: T-001 all ACs PASS, not yet closed. T-002: 9 PASS / 4 PENDING / 1 PARTIAL (native tray-menu clicks aren't automatable) — per programme plan line 28, sourced from `knowledge-center/artifacts/T-00{1,2}/*-verification.md` and `knowledge-center/artifact-map.md`.

## Key Findings

- **Finding: the debug/release subsystem split is the only confirmed defect.** Significance: the fix (unconditional `windows_subsystem = "windows"`) is a one-line, high-confidence change; everything else in this ticket is hygiene/hardening, not defect remediation, and requirements/ACs must say so honestly.
- **Finding: `procs.py`'s six call sites are real but the risk they guard against did not reproduce live.** Significance: requirements must frame this as defensive hygiene (future-proofing against a windowless-parent scenario the Phase 0 probe didn't hit, e.g. a future execution context), not "fixes cause B" — matching the ticket brief's explicit instruction.
- **Finding: `sidecar.py` must stay import-standalone.** Significance: the taskkill flag at `sidecar.py:153` cannot import from the new `console/server/procs.py` (which lives in a different package layout reachable only when `console/` is on `sys.path`); it needs its own inline constant, an explicit non-DRY decision to record.
- **Finding: `tauri-plugin-single-instance` is unproven on this toolchain (xwin/MSVC via `msvc-env.ps1`).** Significance: the plan itself calls this "descope, not block" if it fails to link — this must be stated as an explicit AC/requirement condition, and a `tech-select` pass (topic `single-instance`) is required before the builder adds it, per the ticket brief.
- **Finding: CI has no cross-platform coverage at all today.** Significance: the 3-OS `desktop` job is net-new infrastructure, not an extension of an existing job; "green" can only be proven after a push, which is ASK-gated — the AC must be phrased as "job added and correctly defined," with actual tri-OS green honestly deferred.
- **Finding: T-001/T-002 closing criteria are concrete and already partially known** (T-002 needs one recorded manual click-through). Significance: requirements can state unambiguous closing criteria now without new investigation.
- **Finding: the platform-strategy table's "No stray console" / "Launch path" / "Single instance" / "Build prerequisites" rows are the only rows in scope for T-003** — the trait/registry pattern (`Capture`, `Ocr`, `Tts`, etc.) belongs to T-004–T-007 and must not be built here, only respected as a pattern for future cfg-gating in this ticket's own code (main.rs `#[cfg(windows)]` gating of `--console`/`AllocConsole`, `procs.py` returning `{}` on POSIX).

## Research

- Programme plan: `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md` §§ "Ground truth established this session", "Decisions taken", "Platform strategy", "## T-003 — Shell hygiene".
- Phase 0 evidence: `knowledge-center/artifacts/T-003/T-003-verification.md § Ground truth (before)`.
- Source files read: `desktop/src-tauri/src/main.rs`, `desktop/README.md`, `desktop/sidecar.py`, `desktop/src-tauri/src/tray.rs`, `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/Cargo.lock` (lines 1764-1766, single-instance absent), `desktop/src-tauri/tauri.conf.json`, `.github/workflows/verify.yml`, `pytest.ini`, `console/server/agent_session.py` (:360-419, :495-519), `console/server/agents.py` (:200-224), `console/server/agent_tools.py` (:240-254), `console/server/onboarding.py` (:60-79), `console/server/worktrees.py` (:48-67).

## Recommended Path

Transcribe the programme plan's "## T-003 — Shell hygiene" section as-is into requirements, organized as: (1) Host changes — unconditional GUI subsystem, `logger.rs`, `--console`/`AllocConsole` escape hatch, single-instance plugin (descope-safe), `sidecar.rs::ensure` `extra_env` map; (2) Python changes — `procs.py` + six call-site patches + `sidecar.py` inline constant + serve log redirect; (3) per-OS launch path — `install-shortcut.ps1` / `launch.ps1` (Windows), `install-launcher.sh` (macOS `.app` + Linux `.desktop`), `.claude/launch.json`; (4) CI — new 3-OS `desktop` job; (5) tests — `test_procs.py`, `test_pe_subsystem.py`, sidecar flag assertions, `cargo test` for logger; (6) T-001/T-002 closing criteria. No new scope beyond the plan; challenge-requirements next to surface any gaps the plan left implicit (testability of cross-platform NFRs, explicit descope wording for single-instance, honest CI-AC phrasing).

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
