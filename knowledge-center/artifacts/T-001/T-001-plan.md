---
ticket: "T-001"
artifact: plan
---

# Plan: T-001

## Approach

Phase 1 is a wrapper, not a new server. Sidecar logic is stdlib Python so it
can be tested on any OS and so the console stays drop-in. The window is
**Tauri 2** (`desktop/src-tauri/`), loading the sidecar loopback URL. WinForms
was a temporary host (superseded — [[T-001-decision-log]] `host-tauri-2`).
Caption buttons live in the existing Console `.brandrow`, hidden in a browser.
One layer: `desktop/`.

## Tasks

### [x] T-001-01 — Sidecar start/reuse/stop (2 h)
- [x] `desktop/sidecar.py` stdlib: find repo root, read host/port, probe `/api/config`, spawn `kanban.py serve`, kill only owned pid (POSIX: process group)
- **Done-criteria:** `python -m pytest desktop/tests` covers spawn, reuse-without-kill, stop, toml parse, and `console/` has no Cargo/npm/requirements.txt
- **Basis:** AC spawn / reuse / stop / stdlib
- **Depends on:** —

### [x] T-001-02 — Native window host (re-validate → Tauri) (4 h)
- [x] Tauri 2 loads the sidecar URL; on close calls stop only if owned; Windows job object on owned pid
- **Done-criteria:** `cargo build --manifest-path desktop/src-tauri/Cargo.toml` succeeds; README states the run command
- **Basis:** AC native window + live UI + no stacked caption
- **Depends on:** T-001-01
- **Re-validate:** 2026-09-05 evolve — was WinForms WebView2

### [x] T-001-03 — Wire docs and gitignore (0.5 h)
- [x] `desktop/README.md`, root `.gitignore` for host build dirs, pytest.ini includes `desktop/tests`
- **Done-criteria:** files exist; `python -m pytest` still discovers console tests
- **Basis:** NFR tree layout
- **Depends on:** T-001-01

### [x] T-001-04 — Integrated chrome (2 h)
- [x] `console/static/desktop-chrome.js` + `.win-controls` in `.brandrow`; `initialization_script` adds `in-shell`; Mac overlay vs Win/Linux HTML buttons
- **Done-criteria:** Browser has no window buttons; shell min/max/close/drag work
- **Basis:** FR6 / AC one header
- **Depends on:** T-001-02

### [x] T-001-05 — Remove C# host after smoke (0.5 h)
- [x] Delete `desktop/host/` once Windows smoke of Tauri passes
- **Done-criteria:** no csproj; README points at `cargo run --manifest-path desktop/src-tauri/Cargo.toml`
- **Depends on:** T-001-02, T-001-04

## Effort

- T-001-01 Sidecar — 2 h (done)
- T-001-02 Window host (Tauri) — 4 h
- T-001-03 Docs/gitignore — 0.5 h (done, needs README refresh)
- T-001-04 Integrated chrome — 2 h
- T-001-05 Remove C# — 0.5 h
- **Total remaining** ~7 h after the evolve

### Acceptance criterion coverage

- Native window, one header — T-001-02, T-001-04
- Process is `kanban.py serve` — T-001-01
- Close kills spawned sidecar — T-001-01, T-001-02
- Reuse existing serve, do not kill — T-001-01
- Browser serve still works, no window buttons — T-001-01, T-001-04
- `console/` no new runtime deps — T-001-01
- Automated sidecar tests — T-001-01
- Min/max/close/drag on Windows — T-001-04

## Risks

- Incomplete VS C++ workload (headers/libs missing) — High / High — rustc + link.exe exist; may need `xwin` or a full Native Desktop install. Do not fall back to WinForms. Owner: Builder.
- Loopback is a remote origin so window IPC is denied by default — High / High — capability `remote.urls` for 127.0.0.1; if minimize is a no-op, fix that before deleting C#. Owner: Builder.
- WebView2 runtime missing — Low / High — ships with Edge on this Windows. Owner: Builder.
- Integration test hits a live :8790 — Med / Med — tests bind an ephemeral port. Owner: Builder.

## Dependencies
- Blocks: later desktop-assistant phases
- Blocked by: MSVC CRT headers for compiling WebView2 bindings

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
