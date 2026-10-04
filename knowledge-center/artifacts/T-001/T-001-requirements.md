---
ticket: "T-001"
artifact: requirements
status: frozen
freeze_status: frozen
frozen_at: 2026-09-05
amended_at: 2026-09-05
---

# Requirements: T-001

Frozen 2026-09-05. Amended 2026-09-05 (`evolve`, user request): host is Tauri 2, portable shell, integrated chrome. Scope stays phase 1 of [[desktop-assistant]]. See [[T-001-decision-log]] Amendment 2026-09-05.

**Intent:** A native desktop window that hosts the existing Delivery Console UI, starts `python console/kanban.py serve` when needed, and stops only the process it started. On Windows/Linux the window has no OS caption; min/max/close live in the Console header. On macOS, native traffic lights overlay that header.

## Functional Requirements
1. A native desktop window is the main frame for the existing Delivery Console UI (Windows, macOS, or Linux; this ticket smokes Windows).
2. On launch the shell starts `python console/kanban.py serve` as a sidecar if that host/port is not already serving.
3. The window loads `http://127.0.0.1:{port}` (port from `console/config/console.toml`, overridable).
4. Closing the window stops the sidecar the shell started, and does not leave an orphan serve process.
5. `python console/kanban.py serve` in a normal browser still works without the shell. Window controls are not shown in the browser.
6. In the shell, drag / double-click-to-maximize / min / max / close work from the Console header (macOS: native traffic lights instead of HTML buttons).

## Non-Functional Requirements
1. `console/` stays stdlib-only: no pip, no Cargo.toml, no npm inside `console/`.
2. The shell lives in `desktop/` beside `console/`. The host is Tauri 2 (`desktop/src-tauri/`).
3. Bind remains loopback. The shell does not change the console's no-auth model.
4. Sidecar start/stop is testable without a GUI.
5. Loopback pages get window-chrome IPC only (no `shell` / `fs` from JS).

## Acceptance Criteria
- [x] Launching the Tauri shell opens one window that shows the live Console UI with **one** header (no stacked OS caption).
- [x] The Console process is `python console/kanban.py serve` (or equivalent invocation of that CLI), not a reimplementation of the HTTP server.
- [x] Closing the shell ends the sidecar it spawned; a second launch still works.
- [x] An already-running serve on that port is reused and is **not** killed when the shell closes.
- [x] Serving from a terminal and opening the URL in a browser still works with the shell not running, and does not show window buttons.
- [x] `console/` has no new runtime dependencies.
- [x] Automated tests cover spawn, reuse, and stop of the sidecar.
- [x] Minimize, maximize/restore, close, drag, and double-click-to-maximize work in the shell on Windows.

## Out of Scope
- Multimodal `/send` (screenshot or image parts)
- whisper.cpp / local STT, barge-in, always-on mic
- WinRT OCR, UIA snapshot, clipboard read/write tools
- OS actuation (mouse, keyboard, app launch)
- Phases 2–6 of [[desktop-assistant]]
- Bundling Python, installers, or a Mac/Linux CI matrix
- Pixel-perfect Win11 snap-layouts overlay on the maximize button

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
- Design: [[desktop-assistant]]
