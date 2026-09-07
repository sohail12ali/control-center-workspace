---
ticket: "T-003"
artifact: requirements
status: frozen
frozen_at: "2026-09-06"
frozen_iteration: 1
---

# Requirements: T-003 — Shell hygiene: no stray console, per-OS launch path, close T-001/T-002

**Frozen:** 2026-09-06 · iteration 1 · source [[T-003-requirements-draft]] (full detail, per-FR flows, cited sources) · history [[T-003-iteration-log]]

## Intent

Kill the stray console window at shell launch (a confirmed live defect — cause A), define a per-OS launch path with a file logger and single-instance guard, add cross-platform CI coverage, and close out T-001/T-002. Grounded in the user-approved programme plan `C:\Users\Sohail\.claude\plans\our-project-is-in-optimized-treasure.md § T-003 — Shell hygiene`.

## In Scope

- Cause A fix: unconditional `windows_subsystem = "windows"` (debug + release), `--console`/`DESKTOP_CONSOLE=1` escape hatch, panic-hook logging.
- Host file logger (`logger.rs`, 1 MiB rotation) instrumenting `main.rs`/`tray.rs` lifecycle + previously-swallowed errors.
- Single-instance guard (`tauri-plugin-single-instance`, tech-select gated, descope-safe).
- `sidecar.rs::ensure` `extra_env` map (plumbing only, consumed by a later ticket).
- Defensive `procs.py` no-window flags at 6 Python spawn sites — **hygiene, not a defect fix** (cause B did not reproduce in Phase 0).
- `sidecar.py` serve-output redirect to `serve.log`; standalone-import-safe inline kill constant.
- Per-OS launch path: Windows shortcut installer + terminal launcher; macOS `.app` skeleton; Linux `.desktop` file; `.claude/launch.json`.
- CI: new 3-OS `desktop` job (`cargo build`/`test` + `pytest desktop/tests`).
- Tests: `test_procs.py`, `test_pe_subsystem.py`, sidecar flag assertions, `cargo test` logger.
- Close T-001 (`close-work`) and T-002 (manual click-through + `close-work`).

## Out of Scope

- Assistant features, native bridge, voice/STT, multimodal send — T-004 through T-007.
- Building the `Capture`/`Ocr`/`Tts`/etc. trait system itself — only its cfg-gating *pattern* is followed here.
- Installer packaging (NSIS/DMG/AppImage) — deferred to backlog.
- macOS/Linux hardware smoke — no machine available; CI build-only coverage is the ceiling.
- Proving the new CI job green on all 3 runners in this analyst pass — requires an ASK-gated push; AC covers "defined correctly" only.

## Functional Requirements

| # | Title | Key AC | BR |
|---|---|---|---|
| FR-1 | Unconditional GUI subsystem (cause A fix) | PE subsystem `2` on debug + release; zero visible console at launch | BR-1 |
| FR-2 | `--console`/`DESKTOP_CONSOLE=1` escape hatch | Windows: prints to launching terminal; Linux/macOS: no-op, compiles clean | BR-2 |
| FR-3 | Host file logger | `cargo test` rotation + UTC unit tests; `host.log` has ensure/tray lines after launch | — |
| FR-4 | Single-instance guard (descope-safe) | Second launch = one tray icon; race during quit handled cleanly; descope path recorded if link fails | BR-3 |
| FR-5 | Defensive no-window hygiene (6 Python spawn sites) | `test_procs.py` asserts `creationflags & 0x08000000` on `nt`, absent on POSIX; wording states hygiene not a fix | BR-4 |
| FR-6 | `sidecar.py` log capture + standalone import safety | `serve.log` captures stdout/stderr; taskkill uses its own inline constant, no cross-import | BR-6, BR-8 |
| FR-7 | Per-OS launch path | `install-launcher.sh` produces valid `.app`/`.desktop` (CI-tested); Windows shortcut launches console-free; idempotent re-run | BR-5 |
| FR-8 | Cross-platform CI build | `desktop` job added with correct 3-OS matrix, scoped apt prereqs, no explicit Rust pin (relies on runner-preinstalled toolchain) | BR-4 |
| FR-9 | Close T-001 | T-001 in `done`, artifact-map row under Completed | BR-7 |
| FR-10 | Close T-002 | Dated Manual smoke section recorded; T-002 in `done`, artifact-map row under Completed | BR-7 |

Full flows, actors, triggers, and complete AC checklists: [[T-003-requirements-draft]] § 4.

## Non-Functional Requirements

| Category | Target |
|---|---|
| Portability (hard NFR) | `cargo build`+`test` succeed on ubuntu-latest/macos-latest CI runners; all Windows-only code `#[cfg(windows)]`-gated |
| Reliability | `host.log` rotates at 1 MiB to `.1` |
| Determinism | No-window flags unconditional on `nt`, every named spawn site |
| Auditability | Every host lifecycle event + swallowed error logged |
| Honesty (CI) | "Job defined correctly" (provable now) vs. "green on 3 runners" (PENDING until an ASK-gated push) kept explicitly separate |
| Compatibility | `python -m pytest` baseline (758 passed) does not regress |
| Security / Compliance | N/A — no new network surface, no regulated data |
| Performance / Scalability / Availability | N/A — single-user desktop shell hygiene, no latency/scale/uptime target applies |
| Usability | Second launch focuses the existing window; never a duplicate |

Full table with rationale: [[T-003-requirements-draft]] § 5.

## Data Entities

| Entity | Path | Lifecycle |
|---|---|---|
| `host.log` | `console/.cache/desktop/host.log` | append, rotate to `.1` at 1 MiB |
| `serve.log` | `console/.cache/desktop/serve.log` | append, no rotation in T-003 (BR-8, accepted) |
| `.claude/launch.json` | `.claude/launch.json` | static, hand-maintained |

## Business Rules

BR-1 unconditional GUI subsystem · BR-2 Windows-only APIs `#[cfg(windows)]`-scoped · BR-3 single-instance link failure = descope not blocker · BR-4 no "fixed"/"green" claims without evidence (cause B = hygiene, CI = defined-vs-proven) · BR-5 installer packaging out of scope · BR-6 `sidecar.py` stays standalone-importable · BR-7 T-001/T-002 close only after their stated criteria · BR-8 `serve.log` rotation explicitly out of scope.

## Edge Cases

- Windows-only code paths compile clean (cfg-excluded) on Linux/macOS CI runners.
- Single-instance plugin link failure → descope, recorded, not blocking.
- `--console` on non-Windows → no-op.
- `procs.py` flags on POSIX → no-op.
- `host.log` rotation mid-write → no data loss (unit-tested).
- Second-launch race during quit → handled by FR-4's explicit AC.
- CI apt prerequisites scoped to exactly what T-003's `Cargo.toml` diff needs.

Full list: [[T-003-requirements-draft]] § 8.

## Interactions with Existing Features

T-001 (`main.rs`/`sidecar.rs`) and T-002 (`tray.rs`) modified in place; `desktop/sidecar.py` and 6 `console/server/*` spawn sites modified; `.github/workflows/verify.yml` extended via an isolated new job (no edits to existing jobs); T-004–T-007's trait/registry pattern reused as a *shape* only, no shared code. Zero conflicts. Full table: [[T-003-requirements-draft]] § 9.

## Freeze Record

- Checklist: all 10 items ✓ (no 🔴 blocker gaps, 0 open ⚠, 0 open questions, every FR/NFR/entity covered, stakeholder sign-off via the approved programme plan).
- Challenge findings: 4 raised (CR-1, CR-2, CR-3, CR-4), all closed/accepted at iteration 1 — [[T-003-critique-report]].
- Gaps: 5 raised (G1-G5), all closed at iteration 1 — [[T-003-gap-analysis]].
- Handoff: `@planner → requirements T-003 stories`.

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements-draft]] · [[T-003-context-snapshot]] · [[T-003-gap-analysis]] · [[T-003-iteration-log]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-progress]] · [[T-003-verification]]
