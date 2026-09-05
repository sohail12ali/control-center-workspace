---
ticket: "T-001"
artifact: progress
---

# Progress: T-001

## Status Summary
Stage: VERIFY — Tauri 2 host with integrated chrome. Sidecar tests green. `cargo build` succeeds. Force-kill of the host stops owned serve.

## Dated Log

### 2026-09-05
- Done: Seeded artifacts from `_template`, console `ticket create`, folded the confirmed shell-spike draft into summary and requirements.
- Started: GROUND
- Blocked: —
- Next: Freeze T-001 requirements (or iterate), then plan the Tauri sidecar tasks. Do not scaffold `desktop/` until the plan exists.

### 2026-09-05 (build)
- Done: Frozen requirements. Flat plan. `desktop/sidecar.py` + 10 pytest. WinForms WebView2 host (`dotnet build` 0 errors). GUI smoke: `/api/config` 200 while host ran; force-killing the host left `serve_up=false`.
- Started: TEMPLATE / SIMPLIFY / VERIFY
- Blocked: Tauri 2 not built. No `rustc` on this machine. See `host-webview2-not-tauri`.
- Next: close-work if the ACs are accepted. Phases 2–6 stay out of this ticket.

### 2026-09-05 (evolve)
- Done: Amended requirements, plan, decision-log (`host-tauri-2`, `portable-shell-windows-smoke`). Sidecar POSIX `killpg`. Console `.win-controls` + `desktop-chrome.js`. Tauri tree under `desktop/src-tauri/`.
- Started: T-001-02 Tauri host, T-001-04 chrome
- Blocked: VS Native Desktop UAC was cancelled; MSVC headers (`vcruntime.h`) missing. rustc 1.98 + `link.exe` present. Fetching CRT via xwin release binary (no admin).
- Next: `cargo build` the Tauri host, Windows smoke, then delete `desktop/host/`.

### 2026-09-05 (tauri)
- Done: T-001-02 Tauri host, T-001-04 chrome, T-001-05 removed C#. `pytest desktop/tests` 10 passed. `cargo build` Finished `dev`. Smoke: owned serve, job assign ok, force-kill left :8790 down. Browser `#winControls` stays `hidden`.
- Started: —
- Blocked: —
- Next: close-work if ACs are accepted. Phases 2–6 stay out of this ticket.

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
