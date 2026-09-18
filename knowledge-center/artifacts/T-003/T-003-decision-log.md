---
ticket: "T-003"
artifact: decision-log
---

# Decisions: T-003

## Unconditional GUI subsystem + file logger + `--console` escape hatch
**Decision:** `desktop/src-tauri/src/main.rs:1` changes from `#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]` to an unconditional `#![windows_subsystem = "windows"]` (both debug and release). A new `logger.rs` (using the already-lock-resolved `log` crate, `0.4.34`) writes `console/.cache/desktop/host.log`, rotating at 1 MiB. A `--console`/`DESKTOP_CONSOLE=1` escape hatch (`AttachConsole`/`AllocConsole`, `#[cfg(windows)]`) lets a terminal user opt back into a visible console.
**Rationale:** Phase 0 smoke (`T-003-verification.md § Ground truth (before)`, rows 1/3/7) confirmed the stray console is the host process's own window, caused by the debug-only subsystem gate — a genuine, confirmed defect (cause A). The file logger replaces the swallowed `let _ = ...` error handling in `tray.rs:32-34,45,55,162-163` with real auditability now that stdout/console output is gone.
**Impact:** `desktop/README.md:26`'s `cargo run` guidance updated; no behavior change for release builds (already GUI-subsystem); debug builds lose their implicit console unless `--console` is passed.

## Cause B scope: defensive hygiene, not a defect fix
**Decision:** The `console/server/procs.py` no-window flags applied at 6 spawn sites (`agent_session.py:375,507-512`, `agents.py:209-217`, `agent_tools.py:247-249`, `onboarding.py:70-71`, `worktrees.py:57-59`) are framed as **defensive hygiene**, not a fix for an observed defect.
**Rationale:** Phase 0 smoke checks #5/#6 (`T-003-verification.md`) found claude/cursor-agent chats spawn no new visible console window — children inherit the server's already-hidden console (`sidecar.py:131-139` already sets `CREATE_NO_WINDOW`). Cause B did not reproduce live. Applying the flags anyway guards against a windowless-parent scenario the probe didn't hit, without overclaiming a fix.
**Impact:** Requirements/ACs and PR description must never claim cause B was "fixed" — see [[T-003-requirements]] FR-5, BR-4.

## Single-instance dependency pick
**Decision:** `tauri-plugin-single-instance = "2"` (programme plan line 99), callback `tray::show_main` (existing function). Net-new dependency — requires a builder-stage `tech-select` pass (topic `single-instance`, confirm-existing mode) before it is added to `Cargo.toml`. If it fails to link on this machine's xwin/MSVC toolchain (`desktop/msvc-env.ps1`), the ticket **descopes** FR-4, not blocks the ticket.
**Rationale:** Not in `Cargo.lock` today (grep-confirmed). Single-instance behavior is a real UX gap (duplicate tray icons on relaunch) worth fixing, but not worth blocking the rest of T-003 on an unproven crate/toolchain combination.
**Impact:** [[T-003-requirements]] FR-4, BR-3; descope path recorded here if it triggers.

## tech-single-instance-confirm-existing
**Decision:** Confirmed as-is: `tauri-plugin-single-instance = "2"` (resolved to `2.4.4`).
**Topic:** single-instance
**Date:** 2026-09-06
**Approved-by:** user-in-chat (the crate + version were named directly in the user-approved programme plan, `our-project-is-in-optimized-treasure.md` line 99/line 73's platform table — this pass ratifies the pick against this machine's toolchain rather than re-deriving it from a fresh candidate search).
**Mode:** confirm-existing
**Constraints honored:** must link on the xwin/MSVC toolchain (`desktop/msvc-env.ps1`, Rust 1.98.1) without CMake/LLVM; must work across Windows/Linux/macOS per the platform table (`tauri-plugin-single-instance` is cross-platform, not `#[cfg(windows)]`-only, so it lives in `[dependencies]` not the Windows-only target section); no other new tray/window dependency already covers this.
**Rationale:** This is the tauri-apps org's own official plugin for exactly this problem (single-instance guard + focus-existing-window callback), already the pick baked into the approved programme plan before this ticket existed — there was no live "which of several options" decision to make, only a toolchain-compatibility gate to clear. That gate is now clear: added to `Cargo.toml`, `cargo build --manifest-path desktop/src-tauri/Cargo.toml` (after `msvc-env.ps1`) resolved it to `2.4.4`, pulled ~48 new transitive crates (mostly `windows-*`/`zbus`/`async-*` for the Linux D-Bus and Windows named-mutex backends), and **compiled clean** — `Finished dev profile [unoptimized + debuginfo] target(s) in 2m 15s`, no linker errors. No descope needed; FR-4 proceeds.
**Alternatives considered:**
  - Hand-rolled named-mutex/lock-file guard (`windows-sys` `CreateMutexW` + a `#[cfg(not(windows))]` file-lock fallback) — rejected: reinvents what the plugin already does cross-platform, and the plugin's callback wiring (second-instance argv/cwd delivered to the running app) is exactly the `tray::show_main` hook this ticket needs; hand-rolling would cost more than the 2h already budgeted in `T-003-task-breakdown.md` task 2a-2.
  - No guard at all (accept duplicate tray icons on relaunch) — rejected: FR-4 exists precisely because this is a real, reported UX gap (programme plan `Decisions taken` / platform strategy table row "Single instance").
**Risks accepted:** None newly introduced — the pre-recorded risk ("fails to link on the xwin/MSVC toolchain") is now resolved false (it links); the only remaining risk is ordinary dependency-maintenance drift, not elevated to `plan.md § Risks`.
**Revisit-trigger:** If a future Rust/xwin toolchain upgrade breaks the build for this crate specifically (isolate via `cargo build -p tauri-plugin-single-instance`), or if `tauri-plugin-single-instance` is yanked/abandoned upstream.
**Sources:** `cargo build --manifest-path desktop/src-tauri/Cargo.toml` output, this session, 2026-09-06 (empirical toolchain-link confirmation — no web research performed this pass since the builder role has no WebFetch/WebSearch tool available; the crate identity and cross-platform scope were already established at requirements/analysis time from the approved programme plan, which is itself a primary, user-provided source).

## Installer packaging deferred
**Decision:** NSIS (Windows) / DMG (macOS) / AppImage (Linux) via `cargo tauri build` are explicitly out of scope for T-003. Only unpackaged per-OS launch scripts (`install-shortcut.ps1`, `install-launcher.sh`) are built now.
**Rationale:** Programme plan line 111 records installers as a future `installer` tech-select topic (backlog, after T-007). T-003's job is removing the stray console and standing up CI, not packaging.
**Impact:** [[T-003-requirements]] Out of Scope, BR-5.

## `sidecar.py` stays standalone-importable (no cross-import from `procs.py`)
**Decision:** `sidecar.py:152-159`'s Windows taskkill call keeps its own inline `CREATE_NO_WINDOW`-equivalent constant rather than importing `console/server/procs.py`.
**Rationale:** `sidecar.py` is invoked as a Tauri-shelled script and must keep working without `console/` on `sys.path`. This is a deliberate, small duplication, not an oversight.
**Impact:** [[T-003-requirements]] FR-6, BR-6.

## CI apt-prerequisite scope: today's build only, not the full platform table
**Decision:** The new `.github/workflows/verify.yml` `desktop` job's `ubuntu-latest` leg installs only `desktop/README.md:38-41`'s existing Tauri-build prerequisites (`libwebkit2gtk-4.1-dev build-essential libssl-dev librsvg2-dev patchelf pkg-config`) — not the programme plan's fuller platform-strategy table rows (`libasound2-dev`, `libxcb*`, `libayatana-appindicator3-dev`), which belong to T-005/T-006's cpal/xcap/arboard dependencies.
**Rationale:** T-003's own `Cargo.toml` diff (`log`, `tauri-plugin-single-instance`) needs none of the audio/tray-indicator/xcb libraries. Installing unused prerequisites now would be scope creep on the CI job. Raised as challenge finding CR-1, closed at requirements iteration 1.
**Impact:** [[T-003-requirements]] FR-8. Future tickets (T-005/T-006) extend the job's apt-install list themselves when their own crates land.

## CI Rust toolchain: rely on runner-preinstalled version, no pin
**Decision:** The new `desktop` CI job adds no explicit Rust toolchain setup/pin step.
**Rationale:** Confirmed via `actions/runner-images` (`Ubuntu2404-Readme.md`, fetched 2026-09-06): the Ubuntu 24.04 GitHub-hosted runner image preinstalls Rust 1.98.0/Cargo 1.98.0, well above this project's `rust-version = "1.77"` (`desktop/src-tauri/Cargo.toml`). Pinning is a future hardening item, not required for this ticket's minimal scope. Raised as challenge finding CR-4, closed at requirements iteration 1.
**Impact:** [[T-003-requirements]] FR-8, § 10 External Dependencies.

## `serve.log` rotation: accepted limitation, out of scope
**Decision:** `serve.log` (new, `console/.cache/desktop/serve.log`) gets no rotation/retention policy in T-003, unlike `host.log`'s explicit 1 MiB rotation.
**Rationale:** The programme plan does not specify a policy for this file; adding one would be undiscussed scope expansion. Explicitly stating the limitation (rather than leaving it a silent gap) satisfies the honesty gate. Raised as gap G1, closed at requirements iteration 1 via new BR-8.
**Impact:** [[T-003-requirements]] FR-6, BR-8; unbounded growth tracked as a follow-up `todo`, not new T-003 scope.

## Phase 5 (T-001/T-002 close) deferred to VERIFY, not executed by the builder
**Decision:** Tasks 5a-1 (`close-work T-001`) and 5a-2 (T-002 manual click-through + `close-work T-002`) are the only 2 of 17 task-breakdown rows left `pending` at TEMPLATE/SIMPLIFY handoff. This is by design, not an incomplete build: both were planned "for traceability only" (`T-003-task-breakdown.md` Phase 5 notes) and their execution is explicitly reserved for the verifier/harness at the VERIFY stage, per the ticket's own top-level instruction ("close-work T-001 may proceed... do not run close-work T-002" until its manual smoke is recorded).
**Rationale:** Closing a ticket is a VERIFY-stage action (harness protocol table) gated on evidence the builder doesn't produce (T-002's dated manual click-through against the just-built release exe). Requiring the builder to also do this would blur the TEMPLATE/SIMPLIFY → VERIFY boundary.
**Impact:** `handoff T-003 from=TEMPLATE to=SIMPLIFY` and `from=SIMPLIFY to=VERIFY` pass with 15/17 tasks `[x]`/`done`; the remaining 2 are VERIFY-stage work items, tracked at [[T-003-task-breakdown]] Phase 5 and executed under `@verifier`/harness next.

## T-003 closes with FR-8 and FR-10 accepted PENDING, not FAIL
**Decision:** T-003 is closed (`close-work`) with FR-8 ("desktop CI job green on all 3 runners") and FR-10 ("close T-002") both status `PENDING`, not `PASS` and not `FAIL`.
**Rationale:** FR-8's remaining gap is proving the new CI job green on `ubuntu-latest`/`macos-latest`/`windows-latest`, which requires a push — an ASK-gated action never taken this session; the job is verified "defined correctly" (`yaml.safe_load`, correct 3-OS matrix, isolated from existing jobs) per [[T-003-verification]]. FR-10's remaining gap is T-002's own manual click-through, which per this ticket's explicit top-level instruction is a user action ("do not run close-work T-002"); the verifier attempted one bounded UIA drive, found no drivable tray element (stronger negative than T-002's prior finding), and wrote the dated manual-smoke checklist instead of blocking or faking a pass.
**Impact:** Both are genuinely user/ASK-gated follow-ups, not silently dropped criteria — tracked here and in [[T-003-verification]] § Acceptance Criteria (FR-8, FR-10) and § T-001/T-002 closure. T-002 stays in the `verify` lane until the user completes the checklist; the CI job's 3-OS-green claim stays unmade until a push happens.
**Revisit-trigger:** User pushes the branch (proves/disproves FR-8) or completes the T-002 manual click-through (closes FR-10, unblocks `close-work T-002`).

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
