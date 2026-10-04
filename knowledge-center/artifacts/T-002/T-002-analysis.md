---
ticket: "T-002"
artifact: analysis
---

# Analysis: T-002

GROUND survey of the Tauri host vs the tray skeleton. Product rules are
already locked in [[desktop-assistant]] and `desktop/features.toml`. This
ticket does not invent listen, clipboard, capture, or actuation.

## Context

T-002 is the first tray code. The tray is a remote control of the **live
Agents chat**, not a second orchestrator. Scope is the six `skeleton = true`
rows in `desktop/features.toml`: header `session_backend`, `show_window`,
`new_chat`, `mute_replies`, `interrupt`, `quit`. Every other row stays
`available = false`.

The window already exists ([[T-001-summary]]). This ticket adds a tray
projection of that window plus four UI-owned Agents actions.

## Current State

Verified in-repo 2026-09-05:

- **No tray.** `desktop/src-tauri/src/main.rs` builds one frameless (or macOS
  overlay) window (`open_window`, lines 64–86) and stops an owned sidecar
  only on `WindowEvent::Destroyed` (lines 128–136, `stop_owned` 56–61).
  `desktop/src-tauri/tauri.conf.json` has window-chrome IPC only; no tray
  config.
- **`tray-icon` is not enabled.** `desktop/src-tauri/Cargo.toml` line 15:
  `tauri = { version = "2", features = [] }`. Crate `tray-icon` appears in
  `Cargo.lock` as a Tauri transitive dependency; the host never constructs
  a tray.
- **Loopback capability is chrome-only.**
  `desktop/src-tauri/capabilities/loopback-chrome.json` grants
  `core:window:*` to `http://127.0.0.1:*/*` and `http://localhost:*/*`. No
  `shell` / `fs`. `withGlobalTauri` is true (`tauri.conf.json` line 10).
  `console/static/desktop-chrome.js` calls `window.__TAURI__.window` only;
  close is `win.close()` (line 72), which destroys the window.
- **New chat is private.** `console/static/agents.js` `newChat()` (759–766)
  sets `st.mode = "new"`. The only public hook is
  `window.ConsoleAgents.compose` (1366–1370). Tab leave stops dictation and
  speaking (1375–1380). Tab switch is `ConsoleApp.go` (`app.js` 106–136).
- **Interrupt already has HTTP.** Agents header posts
  `/api/agents/chats/{id}/interrupt` when `s.busy` (`agents.js` 949–953).
  Server: `agents_feature.py` `chat_interrupt` → `agent_manager.interrupt`.
- **Mute is `autoRead`.** `voice.js` stores `C.prefs` key `voice` (52–59);
  default `autoRead: false` (43). Composer checkbox writes
  `Voice.setPrefs({ autoRead })` (`agents.js` 1197–1207). Missing
  capabilities stay visible and say why (`voice.js` 1–7).
- **Registry is on disk, all `available = false`.** 25 `[[features]]` rows
  in `desktop/features.toml`. `[projection]` defaults: left-click
  `show_window`, close `hide_to_tray`. `[meta].webview_speech_from_tray =
  false`.
- **Header backend lives in the chat chrome.** `paintHead` shows
  `meta.agent` (`agents.js` 937). There is no tray header today.
- **T-001 close contract.** Frozen [[T-001-requirements]] FR 4 / AC: closing
  the shell stops an owned sidecar and must not kill a reused
  `kanban.py serve`. Hide-to-tray must not fire `Destroyed` until Quit.
- **`desktop/` is not in git history yet** (`git log -- desktop/` is empty;
  tree is working copy from T-001).

## Key Findings

- Finding: UI-owned skeleton actions already exist in the Agents tab
  (`newChat`, interrupt POST, `Voice.setPrefs` / `autoRead`). Significance:
  the tray should emit webview events and call those paths; it must not
  reimplement `/send` or a second backend picker.
- Finding: `ConsoleAgents` does not expose `newChat`, interrupt, mute, or
  current-backend. Significance: T-002 needs a small public desktop
  listener on the existing IIFE, not a new Agents runtime.
- Finding: HTML close and OS close currently destroy the window, which
  stops an owned sidecar. Significance: hide-to-tray is a behaviour change
  vs T-001’s “close = quit”; Quit must keep the T-001 stop/reuse rule.
- Finding: Enabling Tauri’s `tray-icon` feature is a host change inside
  `desktop/src-tauri/`; `loopback-chrome.json` must stay chrome-only.
  Significance: native tray/hotkeys live in Rust; JS stays event handlers.
- Finding: Projecting every `available = false` row into the menu would
  list listen/clipboard/capture as grey clutter on day one. Significance:
  skeleton ticket should show header + five actions; other rows stay out of
  the menu until `available = true` (Settings hide-unavailable vs disabled
  applies when those phases land).

## Research

- [[desktop-assistant]] — tray control surface, Settings projection, icon
  states, menu-by-phase, “never one-click”.
- [[T-001-summary]] / [[T-001-requirements]] — window, sidecar ownership,
  no `shell`/`fs` from loopback JS.
- [[T-002-decision-log]] `skeleton-five-actions`.
- Tauri 2.11.5 in `desktop/src-tauri/Cargo.lock`; `tray-icon` crate already
  in the lockfile.

## Recommended Path

Enable the Tauri `tray-icon` feature. Build a native tray whose menu is
header `session_backend` plus Show / New chat / Mute / Interrupt / Quit.
Left-click Show window (projection default). Close (HTML and OS) hides to
tray and does **not** stop the sidecar; Quit stops an owned sidecar and
leaves a reused serve running. Rust emits events into the webview; JS
switches to the Agents tab and calls new public `ConsoleAgents` handlers
that wrap existing `newChat`, interrupt, and `autoRead`. Flip those six
registry rows to `available = true`. Do not parse a TOML crate into the
host this ticket — hardcode the six ids so they match `features.toml`.
Do not add `shell`/`fs` to `loopback-chrome.json`. Defer listen,
clipboard, capture, watch, actuation, saved prompts, global-shortcut
chords, and Settings clutter toggles.

## Open questions (non-blocking)

None that change skeleton scope. Defaults above match
[[desktop-assistant]] `[projection]` and `skeleton-five-actions`.

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- [[T-002-context-snapshot]]
- Design: [[desktop-assistant]]
- Shell spike: [[T-001-summary]]
