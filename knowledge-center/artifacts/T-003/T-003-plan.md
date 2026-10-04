---
ticket: "T-003"
artifact: plan
structure: multi-layer
---

# Plan: T-003

## Approach

Multi-layer: T-003 spans five layers with genuinely different toolchains and verification methods — Rust host (`cargo build`/`test` under MSVC), Python server (`pytest`), per-OS shell scripts (PowerShell + Ubuntu-runner shell-script tests), CI (YAML, provable "defined" now / "green" only after an ASK-gated push), and closing T-001/T-002 (a VERIFY-stage action, planned here but executed later). This exceeds the single-layer thresholds (>6 tasks, real cross-layer dependency chain: logger → main.rs → tray.rs → single-instance → release build → launch scripts/T-002 close) per [[T-003-decision-log]]'s single-instance and CI-scope decisions. Chaining `analyze-components` → `breakdown-tasks` → `challenge-plan` keeps each layer's tasks traceable to its own FRs without collapsing distinct toolchains into one flat list. No unmade tech choice needs `tech-select` at planning time: `log 0.4` is already lock-resolved (no gate); `tauri-plugin-single-instance` is net-new but its `tech-select` (topic `single-instance`, `confirm-existing` mode) is explicitly a **builder-stage** gate per [[T-003-decision-log]] § "Single-instance dependency pick" — planned as task 2a-1, not run now.

## Slices

### Slice 1 — Host logging & Python spawn hygiene foundation
Rust host cause-A fix + logger + tray wiring (independent of single-instance), and Python `procs.py` + 6 call-site edits + `sidecar.py` log capture. No cross-slice dependency; both can build in parallel.

### Slice 2 — Single-instance guard
Gated by builder-stage `tech-select(single-instance, confirm-existing)`; descopes (not blocks) FR-4 if the plugin fails to link on the xwin/MSVC toolchain.

### Slice 3 — Release build & per-OS launch path
Long-running release build (multi-minute, plan as its own task) feeding Windows shortcut/launcher scripts and the macOS/Linux `install-launcher.sh`; `.claude/launch.json` is independent.

### Slice 4 — CI
New `desktop` job in `.github/workflows/verify.yml`, 3-OS matrix. "Defined correctly" is provable now; "green on 3 runners" is PENDING until an ASK-gated push.

### Slice 5 — Close T-001/T-002
T-001 close-work is a short, low-risk task (all ACs already PASS). T-002 close requires the release build to exist first and a recorded manual click-through (rows 4/6/7/8/9) before `close-work` — sequenced last. Execution of this slice belongs to the verifier/harness at VERIFY stage, not the builder; planned here for traceability only.

Full breakdown: [[T-003-components]] (dependency graph + critical path) · [[T-003-task-breakdown]] (atomic tasks) · [[T-003-implementation-plan]] (synthesis) · [[T-003-effort-estimate]] (upfront sizing).

## Tasks / Effort

Not duplicated here — see [[T-003-task-breakdown]] § Effort summary and [[T-003-implementation-plan]] for the full phase → slice → task tree. Total: **21h** (17 tasks across 5 phases, after `challenge-plan` CR-5's effort bump to task 3a-1) — comfortably under [[T-003-effort-estimate]]'s upfront Dev lower bound (32.2h); see that artifact's Recommendations for why (programme plan already resolved most of the uncertainty a generic estimate assumes).

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| FR-1 PE subsystem 2 (debug+release), zero visible console | 1a-2, 1a-4, 3a-1 |
| FR-2 `--console`/`DESKTOP_CONSOLE=1` hatch + cross-OS compile | 1a-2 |
| FR-3 `cargo test` rotation/UTC + `host.log` lines | 1a-1, 1a-3 |
| FR-4 single-instance guard (descope-safe) | 2a-1, 2a-2 |
| FR-5 `test_procs.py` no-window flags, hygiene wording | 1b-1, 1b-2 |
| FR-6 `serve.log` capture + standalone-import safety | 1b-3 |
| FR-7 per-OS launch scripts, idempotent re-run | 3b-1, 3b-2, 3b-3 |
| FR-8 3-OS CI job (defined vs. green split) | 4a-1 |
| FR-9 close T-001 | 5a-1 |
| FR-10 close T-002 (manual click-through) | 5a-2 |

All 10 FRs mapped to ≥1 task — see [[T-003-task-breakdown]] for the full AC-level trace.

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| `tauri-plugin-single-instance` fails to link on the xwin/MSVC toolchain | Med | Low | Pre-agreed descope path (FR-4 N/A, recorded in decision-log) — not a blocker | Builder | [[T-003-decision-log]] § Single-instance dependency pick |
| Release build (task 3a-1) is multi-minute; blocks 3 downstream tasks (C1, C2, E2) | Med | Med | Sequence as its own task, start early in Phase 3, don't interleave with other Rust edits once building | Builder | [[T-003-components]] § Dependency graph (bottleneck) |
| CI `desktop` job claimed "green" without an actual push | Low | High | AC split enforced: "defined correctly" (static/YAML review) vs. "green on 3 runners" (PENDING, ASK-gated push) — never conflate | Builder/Verifier | [[T-003-requirements]] BR-4, FR-8 |
| T-002 close blocked indefinitely if UIA automation of the tray menu is attempted and fails | Low | Low | Pre-agreed degrade path: manual checklist recorded in `T-002-verification.md`, not blocking | Verifier | [[T-003-requirements-draft]] FR-10, T-002's own PENDING rows |
| Windows-only Rust code accidentally not `#[cfg(windows)]`-gated, breaking Linux/macOS CI compile | Low | High | Code-review gate on every new Windows API call; only provable by CI or review here (no Linux/macOS hardware) — stated plainly, not claimed as executed | Builder/Verifier | [[T-003-requirements]] Portability NFR |

All top risks (none rated high×high) carry an explicit mitigation — no unmitigated high×high present.

## Dependencies
- Blocks: T-004 (assistant brain) — programme plan ordering, T-004 depends on T-003
- Blocked by: —

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements]] · [[T-003-user-stories]] · [[T-003-critique-report]] · [[T-003-plan-iteration-log]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-components]] · [[T-003-task-breakdown]] · [[T-003-implementation-plan]] · [[T-003-effort-estimate]] · [[T-003-progress]] · [[T-003-verification]]
