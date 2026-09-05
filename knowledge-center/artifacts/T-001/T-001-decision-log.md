---
ticket: "T-001"
artifact: decision-log
---

# Decisions: T-001

Locked before kickoff (evaluation 2026-09-05, confirmed id T-001). Copied
here so the ticket carries its own premises.

## product-shape-native-shell

**Decision:** Native desktop shell (Tauri 2) hosts the Console as the main window. The stdlib web+CLI path stays.

**Rationale:** Browser pages cannot capture other apps, inject input, or keep a private mic. The console already owns the agent loop.

**Impact:** New `desktop/` tree. Do not turn `console/` into an Electron/Tauri app in place.

## phase-1-is-shell-only

**Decision:** This ticket is the shell spike only (spawn serve, load UI, clean shutdown).

**Rationale:** User confirmed T-001 against the phase-1 ticket-draft. Multimodal `/send`, voice, UIA, and actuation are later phases on [[desktop-assistant]].

**Impact:** Requirements and plan must not grow screenshot or STT work under this id.

## windows-first

**Decision:** Windows-first. macOS/Linux after Windows works.

**Rationale:** Development machine is Windows; WebView2 is the v1 engine.

**Impact:** No cross-platform CI requirement on T-001.

## host-webview2-not-tauri

**Decision:** Ship the v1 window as WinForms + Microsoft.Web.WebView2 on `net10.0-windows`, not Tauri 2.

**Rationale:** This machine has no `rustc`/`cargo` and vswhere reports no MSVC C++ tools. `dotnet` 10.0.301 is installed and `winforms` templates exist. User asked to implement end to end with tests if possible. Sidecar stay in stdlib Python so tests do not need a GUI or NuGet.

**Impact:** `desktop/host/` is C#. Tauri remains the wiki recommendation. Revisit when `rustc` and `link.exe` are on PATH.

**Rejected:** Electron (plan runner-up) — heavier download, extra Node runtime beside an existing .NET host. pywebview — pip, fights stdlib-only console.

## Amendment 2026-09-05 — Tauri 2 + integrated chrome

**Trigger:** User request. The WinForms caption stacked a Windows title bar on the Console `.brandrow` and cannot ship on macOS/Linux. Stakeholder asked to change the host so the shell runs on Windows, macOS, and Linux, with min/max/close in the existing header.

### Before
- `host-webview2-not-tauri`: v1 window is WinForms + WebView2; Tauri out of scope until `rustc`/`link.exe`.
- `windows-first`: no Mac/Linux requirement on T-001.
- Requirements FR1 / AC1: Windows-only native window. Out of scope included “Shipping a Tauri binary”.
- Plan T-001-02: WinForms host.

### After
- **host-tauri-2** (below) supersedes `host-webview2-not-tauri`.
- **portable-shell-windows-smoke** (below) supersedes `windows-first` for this ticket’s remaining work.
- Requirements: native window on the host OS; Tauri in scope; integrated chrome in `.brandrow`; browser path unchanged.
- Plan: T-001-02 becomes Tauri; T-001-04 chrome; T-001-05 remove C# after smoke.

## host-tauri-2

**Decision:** The shell host is Tauri 2 under `desktop/src-tauri/`. The window loads the sidecar’s loopback URL (`WebviewUrl::External`). Window min/max/close/drag are the only IPC permissions granted to that origin.

**Rationale:** Matches [[desktop-assistant]] and `product-shape-native-shell`. Frameless/overlay chrome can share the Console header. Same codebase for Windows (WebView2), macOS (WKWebView), Linux (WebKitGTK). `rustc` 1.98 is on this machine; `link.exe` exists under VS 18 Community.

**Impact:** `desktop/host/` (C#) is removed after Windows smoke. `console/` stays stdlib; vanilla `desktop-chrome.js` uses `withGlobalTauri`. Sidecar spawn/stop stays in Rust wrapping `desktop/sidecar.py` — not a Tauri `shell` permission.

**Rejected:** Stay on WinForms (no Mac/Linux, stacked chrome). Electron unless the MSVC toolchain cannot link (user must be asked first).

## portable-shell-windows-smoke

**Decision:** The shell is portable (Windows / macOS / Linux). This development machine verifies Windows only. macOS uses overlay traffic lights; Windows/Linux use HTML caption buttons.

**Rationale:** Stakeholder asked for all three OSes. No Mac/Linux test farm here.

**Impact:** No cross-platform CI matrix on T-001. README documents per-OS toolchain. `cfg(target_os)` in the host.

## Links
- [[T-001-summary]] · [[T-001-analysis]] · [[T-001-requirements]] · [[T-001-decision-log]] · [[T-001-plan]] · [[T-001-progress]] · [[T-001-verification]]
- Design: [[desktop-assistant]]
