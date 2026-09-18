---
ticket: "T-003"
artifact: implementation-plan
---

# Implementation Plan: T-003

**Synthesized by:** `breakdown-tasks`, from [[T-003-requirements]] + [[T-003-plan]] + [[T-003-components]] + [[T-003-task-breakdown]]. Ready for `challenge-plan`.

## Ticket summary

Kill the stray console window at shell launch (confirmed cause A — debug-only `windows_subsystem`), add a rotating file logger + `--console` escape hatch + descope-safe single-instance guard, apply defensive no-window hygiene to 6 Python spawn sites (cause B did not reproduce), define a per-OS launch path (Windows shortcut/launcher, macOS `.app` skeleton, Linux `.desktop`), add a 3-OS CI build, and close T-001/T-002. Grounded in `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md § T-003 — Shell hygiene`. 10 FRs, 17 tasks, 21h dev effort, 5 phases across 5 toolchain layers.

---

## Phase 1: Host logging & Python spawn hygiene foundation (8h)

Rust host cause-A fix + logger + tray wiring, and Python `procs.py` + spawn-site edits + `sidecar.py` log capture. No cross-slice dependency inside this phase — all three slices can build in parallel.

### Slice 1a: Rust logger + cause-A fix (5.5h)
Files touched: `desktop/src-tauri/src/logger.rs` (new), `desktop/src-tauri/src/main.rs`, `desktop/src-tauri/src/tray.rs`, `desktop/README.md`.

- **1a-1** (2h) — New `logger.rs`: `log` crate direct dep, rotating file writer to `console/.cache/desktop/host.log` (1 MiB → `.1`), UTC timestamps. Component: A2. Requirement: FR-3. AC: `cargo test` rotation unit test; `cargo test` UTC conversion unit test.
- **1a-2** (2h) — `main.rs:1` unconditional GUI subsystem; `--console`/`DESKTOP_CONSOLE=1` hatch (`AttachConsole`/`AllocConsole`); panic hook logs cross-platform, display path unchanged; `find_repo_root` reordered before the builder. Component: A1. Requirement: FR-1, FR-2. AC: PE subsystem `2` (debug); zero console windows; `--console` prints to terminal on Windows, no-op elsewhere.
- **1a-3** (1h) — `tray.rs` swallowed-error sites → `log::warn!`. Component: A3. Requirement: FR-3. AC: `host.log` has warn lines after launch.
- **1a-4** (0.5h) — `desktop/README.md:26` doc update. Component: A1. Requirement: FR-1. AC: doc matches actual `cargo run` behavior.

### Slice 1b: Python spawn hygiene (4.5h)
Files touched: `console/server/procs.py` (new), `console/server/agent_session.py`, `console/server/agents.py`, `console/server/agent_tools.py`, `console/server/onboarding.py`, `console/server/worktrees.py`, `desktop/sidecar.py`, `console/tests/test_procs.py` (new), `desktop/tests/test_sidecar.py`.

- **1b-1** (1h) — New `procs.py`: `CREATE_NO_WINDOW`, `no_window_flags`, `popen_kwargs`. Component: B1. Requirement: FR-5.
- **1b-2** (2h) — Apply flags at the 6 named spawn sites; hygiene-not-fix wording. Component: B2. Requirement: FR-5. AC: `test_procs.py` asserts flags on `nt`, absent on POSIX, all 6 sites.
- **1b-3** (1.5h) — `sidecar.py` serve-output redirect to `serve.log`; taskkill inline constant (no cross-import). Component: B3. Requirement: FR-6. AC: `test_sidecar.py` new assertions; existing standalone tests still pass.

### Slice 1c: sidecar.rs plumbing (0.5h)
Files touched: `desktop/src-tauri/src/sidecar.rs`.

- **1c-1** (0.5h) — `ensure` gains `extra_env` map (unused here, consumed by T-005). Component: A5.

**Phase 1 effort: 8h. Components: A1, A2, A3, A5, B1, B2, B3.**

---

## Phase 2: Single-instance guard (3h)

Gated by a **builder-stage** `tech-select` pass before any dependency is added.

### Slice 2a: dependency add
Files touched: `desktop/src-tauri/Cargo.toml`, `desktop/src-tauri/src/main.rs`.

- **2a-1** (1h) — `tech-select T-003 single-instance --mode confirm-existing`: validate `tauri-plugin-single-instance = "2"` against the xwin/MSVC toolchain. Not run by the planner; recorded to `T-003-decision-log.md` by whoever runs it (builder). Requirement: FR-4.
- **2a-2** (2h) — Add the crate; register in `main.rs` builder, callback `tray::show_main`. Component: A4. Requirement: FR-4. AC: second launch = one tray icon; quit-race handled cleanly. **If 2a-1 finds a link failure: descope — FR-4's ACs marked N/A citing the decision-log entry, ticket proceeds without it.**

**Phase 2 effort: 3h. Component: A4. Depends on: Phase 1 slice 1a (main.rs, tray.rs).**

---

## Phase 3: Release build & per-OS launch path (6h)

### Slice 3a: release build (2.5h)
- **3a-1** (2.5h) — `cargo build --release` (after `msvc-env.ps1`). **Long-running, multi-minute — its own task, not interleaved with other Rust edits.** Component: A6. Requirement: FR-1, FR-3, FR-4, FR-7 (verification path). AC: `test_pe_subsystem.py` against the release exe asserts subsystem `2`; Phase 0 smoke rows 1-8 rerun. (Effort bumped from 1.5h→2.5h per `challenge-plan` CR-5 — build wait + 8-row manual re-verification.)

### Slice 3b: per-OS launch scripts (4.5h)
Files touched: `desktop/install-shortcut.ps1` (new), `desktop/launch.ps1` (new), `desktop/install-launcher.sh` (new), `.claude/launch.json` (new).

- **3b-1** (2h) — Windows: `install-shortcut.ps1` (Start-menu `.lnk`, idempotent) + `launch.ps1` (terminal launcher, `--console` passthrough). Component: C1. Requirement: FR-7. AC: manual smoke — shortcut launches console-free, `--console` still works.
- **3b-2** (2h) — macOS `.app` skeleton + Linux `.desktop` via one `install-launcher.sh`. Component: C2. Requirement: FR-7. AC: shell-script test on Ubuntu CI validates structure; build-only coverage stated (no macOS/Linux hardware).
- **3b-3** (0.5h) — `.claude/launch.json`: `desktop-shell` + `console-serve` entries. Component: C3. Requirement: FR-7.

**Phase 3 effort: 7h. Components: A6, C1, C2, C3. Depends on: Phase 1 slice 1a + Phase 2 (or its descope).**

---

## Phase 4: CI (1.5h)

### Slice 4a: desktop CI job
Files touched: `.github/workflows/verify.yml`.

- **4a-1** (1.5h) — New `desktop` job, 3-OS matrix, scoped apt prerequisites, no Rust pin, `cargo build --release`/`cargo test` + `pytest desktop/tests` per runner. Component: D1. Requirement: FR-8. AC: job defined correctly (static/YAML review) claimed now; **"green on all 3 runners" stays PENDING until an ASK-gated push — never claimed as PASS without it.**

**Phase 4 effort: 1.5h. Component: D1. No hard dependency on other phases (references their test files, not code-coupled).**

---

## Phase 5: Close T-001/T-002 (1.5h)

**Execution belongs to the verifier/harness at VERIFY stage, not the builder** — planned here only for traceability.

- **5a-1** (0.5h) — `close-work T-001`, all ACs already PASS, note the cause-A fix under T-003. Component: E1. Requirement: FR-9. Depends on: 1a-2.
- **5a-2** (1h) — Manual click-through (Phase 0 smoke rows 4/6/7/8/9) on the release build, recorded in `T-002-verification.md` under a dated "Manual smoke" header, then `close-work T-002`. Component: E2. Requirement: FR-10. Depends on: 3a-1. **If UIA automation of the tray menu fails (T-002's known PENDING limitation), degrades to a manual checklist — does not block close.**

**Phase 5 effort: 1.5h.**

---

## Totals

| Phase | Effort (h) | Components | Requirements |
|-------|-----------:|-------------|---------------|
| 1 — Host logging & Python hygiene | 8 | A1, A2, A3, A5, B1, B2, B3 | FR-1, FR-2, FR-3, FR-5, FR-6 |
| 2 — Single-instance guard | 3 | A4 | FR-4 |
| 3 — Release build & launch path | 7 | A6, C1, C2, C3 | FR-1, FR-3, FR-4, FR-7 |
| 4 — CI | 1.5 | D1 | FR-8 |
| 5 — Close T-001/T-002 | 1.5 | E1, E2 | FR-9, FR-10 |
| **Total** | **21** | **15** | **10** |

Reconciled with [[T-003-task-breakdown]] § Effort summary (21h, exact match, after `challenge-plan` CR-5's effort bump to 3a-1) and within [[T-003-effort-estimate]]'s upfront envelope (well under Dev lower bound 32.2h — see that artifact's Recommendations for why).

## Cross-links
- Requirements ↔ Plan: every FR-1..FR-10 traced above and in [[T-003-plan]] § Acceptance criterion coverage.
- Components ↔ Tasks: every component (A1-A6, B1-B3, C1-C3, D1, E1-E2) appears in ≥1 task above.
- Tasks ↔ Implementation plan: this document is the master synthesis; no task exists only in `{T}-task-breakdown.md` without appearing here.

## Links
- [[T-003-summary]] · [[T-003-requirements]] · [[T-003-plan]] · [[T-003-components]] · [[T-003-task-breakdown]] · [[T-003-implementation-plan]] · [[T-003-effort-estimate]]
