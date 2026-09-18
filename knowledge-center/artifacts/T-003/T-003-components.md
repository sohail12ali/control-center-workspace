---
ticket: "T-003"
artifact: components
---

# Components: T-003

Tracks every component this ticket touches, its dependencies, and its build status. Layers here reflect T-003's actual toolchain split (Rust host / Python server / per-OS launch scripts / CI / ticket closure) rather than a generic data/service/UI split.

**Produced by:** `analyze-components`. **Consumed by:** `breakdown-tasks` (tasks + implementation-plan synthesis).

---

## Rust host layer (`desktop/src-tauri`)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| A1 main.rs | entry point | Unconditional GUI subsystem, `--console`/`DESKTOP_CONSOLE=1` hatch, panic-hook logging, `find_repo_root` reorder | A2 | 1 | FR-1, FR-2 | done |
| A2 logger.rs | module (new) | Rotating file logger (`log` crate, 1 MiB rotation, UTC) | — (root) | 1 | FR-3 | done |
| A3 tray.rs | module (existing) | `log::warn!` wiring at swallowed-error sites | A2 | 1 | FR-3 | done |
| A4 single-instance integration | Cargo.toml dep + main.rs wiring | `tauri-plugin-single-instance` registration, callback = `tray::show_main` | A1, A3, tech-select(single-instance) | 2 | FR-4 | done |
| A5 sidecar.rs extra_env | module (existing) | `ensure` gains an `extra_env` map (plumbing only, consumed by T-005) | — (root) | 1 | scope note (no direct FR) | done |
| A6 release build artifact | build output | `cargo build --release` (multi-minute) | A1, A2, A3, A4 | 3 | FR-1, FR-3, FR-4, FR-7 (verification) | done |

## Python server layer (`console/server`, `desktop/sidecar.py`)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| B1 procs.py | module (new) | `CREATE_NO_WINDOW`, `no_window_flags`, `popen_kwargs` | — (root) | 1 | FR-5 | done |
| B2 six spawn-site edits | call-site edits | Apply flags at `agent_session.py` (×2), `agents.py`, `agent_tools.py`, `onboarding.py`, `worktrees.py` | B1 | 1 | FR-5 | done |
| B3 sidecar.py | module (existing) | `serve.log` stdout/stderr redirect; inline taskkill constant (no cross-import) | — (root, deliberately not on B1) | 1 | FR-6 | done |

## Launch path layer (per-OS scripts)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| C1 Windows scripts | script (new) | `install-shortcut.ps1` (Start-menu `.lnk`) + `launch.ps1` (terminal launcher, `--console` passthrough) | A6 | 3 | FR-7 | done |
| C2 install-launcher.sh | script (new) | macOS `.app` skeleton + Linux `.desktop` file | A6 (conceptually; script itself buildable without the binary, verification needs it) | 3 | FR-7 | done |
| C3 .claude/launch.json | config (new) | `desktop-shell` + `console-serve` launch entries | — (root) | 3 | FR-7 | done |

## CI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| D1 verify.yml desktop job | CI config | New 3-OS matrix job (`cargo build`/`test` + `pytest desktop/tests`), scoped apt, no Rust pin | — (root; references B2/A2 test files but not code-coupled) | 4 | FR-8 | done |

## Ticket-closure layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| E1 Close T-001 | process action | `close-work T-001` (all ACs already PASS) | A1 (cause-A fix landed) | 5 | FR-9 | pending |
| E2 Close T-002 | process action | Manual click-through (rows 4/6/7/8/9) recorded, then `close-work T-002` | A6 | 5 | FR-10 | pending |

---

## Dependency graph

```
A2 logger.rs (root)
  └─ A1 main.rs (subsystem, --console, panic hook; init logger first)
       ├─ A3 tray.rs (log::warn! wiring)
       │    └─ A4 single-instance integration (tech-select-gated; callback = tray::show_main)
       │         └─ A6 release build artifact
       │              ├─ C1 Windows scripts
       │              ├─ C2 install-launcher.sh
       │              └─ E2 Close T-002 (manual click-through on release build)
       └─ E1 Close T-001 (cause-A fix landed)

A5 sidecar.rs extra_env (root, isolated — plumbing only)

B1 procs.py (root)
  └─ B2 six spawn-site edits

B3 sidecar.py (root, isolated by design — no import of B1)

C3 .claude/launch.json (root, isolated)

D1 verify.yml desktop job (root, isolated — references test files, not code-coupled)
```

---

## Dependency graph analysis

- **Root components:** A2, A5, B1, B3, C3, D1 (6 of 15 — no upstream dependency, all can start Phase 1 in parallel).
- **Leaf components:** E1, E2, C1, C2, B2, D1 (nothing depends on them).
- **Circular dependencies:** none detected.
- **Critical path:** A2 → A1 → A3 → A4 → A6 → E2 (6 components, longest chain). Effort-weighted (per `{T}-task-breakdown.md`, post-`challenge-plan`): 1a-1(2h) → 1a-2(2h) → 1a-3(1h) → 2a-1 gate(1h) → 2a-2(2h) → 3a-1(2.5h) → 5a-2(1h) ≈ **11.5h** critical-path effort, longest of any chain.
- **Bottleneck:** A6 (release build artifact) — 3 direct dependents (C1, C2, E2), plus it's explicitly a long-running (multi-minute wall-clock) task per the ticket's constraints. Flag: don't interleave other Rust edits with this build; start it as soon as A1–A4 land.
- **Secondary bottleneck:** A1 (main.rs) — 2 dependents (A3, E1).
- **Parallelizable:** yes — three independent chains run alongside the main Rust chain: {A5}, {B1→B2}, {B3}, {C3}, {D1}.

---

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Rust host | 6 | 0 | 0 | 6 |
| Python server | 3 | 0 | 0 | 3 |
| Launch path | 3 | 0 | 0 | 3 |
| CI | 1 | 0 | 0 | 1 |
| Ticket closure | 2 | 2 | 0 | 0 |
| **Total** | **15** | **2** | **0** | **13** |

Component count (15) sits just above the typical 5-12 band; retained as-is rather than merged further — the count is driven by five genuinely distinct toolchains (Rust/Python/shell-script/YAML/process), not by over-decomposition within any one layer (each layer stays at 1-6 components).

## Links
- [[T-003-summary]] · [[T-003-requirements]] · [[T-003-plan]] · [[T-003-components]] · [[T-003-task-breakdown]] · [[T-003-implementation-plan]]
