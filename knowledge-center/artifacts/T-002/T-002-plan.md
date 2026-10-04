---
ticket: "T-002"
artifact: plan
---

# Plan: T-002

## Approach

Native tray in the existing Tauri 2 host (`events-not-capability-widen`,
`skeleton-five-actions`). Rust owns the icon, hide-to-tray, and Quit.
JS owns New chat / mute / interrupt by wrapping code that already exists.
Do not parse `features.toml` in Rust; hardcode the six skeleton ids.
One layer: `desktop/src-tauri/` plus a thin Console JS listener.

## Tasks

### [x] T-002-01 — Enable tray-icon and skeleton menu (3 h)
- [x] `tauri` feature `tray-icon`; tray module; menu header + five actions; tooltip Delivery Console; idle bundled icon
- **Done-criteria:** `cargo build --manifest-path desktop/src-tauri/Cargo.toml` succeeds; menu has no listen/clipboard/capture items (code review)
- **Basis:** FR-1, US-1
- **Depends on:** —

### [x] T-002-02 — Hide to tray vs Quit (2 h)
- [x] Intercept close → hide; left-click / Show unhides `main`; Quit `stop_owned` then exit; HTML close still `win.close()` (host intercepts)
- **Done-criteria:** Documented smoke: hide leaves serve; Quit owned stops; Quit reused does not. Existing `python -m pytest desktop/tests` still green
- **Basis:** FR-2, FR-6, US-1, US-3
- **Depends on:** T-002-01

### [x] T-002-03 — Webview handlers for New chat / Mute / Interrupt / header (3 h)
- [x] `ConsoleAgents` desktop methods; listen or eval from tray; `go("agents")`; interrupt busy-chat rule + toast; mute `autoRead`; emit backend label to native header
- **Done-criteria:** Browser path still works (no tray). Loopback capability has no `shell`/`fs`
- **Basis:** FR-3, FR-4, FR-5, US-2
- **Depends on:** T-002-01

### [x] T-002-04 — Registry flags + docs (0.5 h)
- [x] Flip six skeleton `available = true`; pytest asserts catalog; README notes tray
- **Done-criteria:** `python -c` / pytest: skeleton true, others false
- **Basis:** FR-7, US-4
- **Depends on:** T-002-01

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-002-01 Tray menu | 3 h | Tauri feature + menu wiring |
| T-002-02 Hide vs Quit | 2 h | Close intercept + sidecar rules |
| T-002-03 JS handlers | 3 h | agents.js public API + header invoke |
| T-002-04 Registry/docs | 0.5 h | toml flags + one test |
| **Total** | **8.5 h** | |

### Acceptance criterion coverage

| AC | Tasks |
|----|-------|
| Tray icon (smoke) | T-002-01 |
| Skeleton menu only | T-002-01, T-002-04 |
| Header not a picker | T-002-01, T-002-03 |
| Header backend or dash | T-002-03 |
| Hide then Show | T-002-02 |
| New chat no send | T-002-03 |
| Mute autoRead | T-002-03 |
| Interrupt HTTP / toast | T-002-03 |
| Close vs Quit sidecar | T-002-02 |
| features.toml flags | T-002-04 |
| Browser unchanged | T-002-03 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| Loopback origin cannot invoke a new command | Med | High | Prefer `eval` Rust→JS; add only a narrow invoke for header if needed; never shell/fs | Builder | [[T-001-plan]] remote origin; decision `events-not-capability-widen` |
| Hide-to-tray leaves owned serve after user thinks they quit | Med | Med | Quit is explicit in the menu; README | Builder | [[T-002-analysis]] findings |
| `ConsoleAgents` not mounted when tray fires | Med | Med | Toast / ignore until ready; `go("agents")` first | Builder | snapshot risk |
| Incomplete CRT headers (T-001) | Low | High | Same `msvc-env.ps1` as T-001 | Builder | [[T-001-plan]] |

## Dependencies
- Blocks: later desktop-assistant tray rows (phases 2–6)
- Blocked by: [[T-001-summary]] host (exists in working tree)

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- [[T-002-user-stories]] · Design: [[desktop-assistant]]
