---
ticket: "T-002"
artifact: requirements
status: frozen
freeze_status: frozen
frozen_at: 2026-09-05
frozen_iteration: 1
---

# Requirements: T-002

Frozen 2026-09-05 (iteration 1). Source: [[T-002-requirements-draft]] · [[T-002-iteration-log]].

**Intent:** A system-tray remote control for the live Agents chat. Skeleton only: Show window, New chat, Mute replies, Interrupt, Quit, plus a backend-name header. Not a second orchestrator.

## Functional Requirements

1. **FR-1 Tray menu** — Notification-area icon (tooltip “Delivery Console”) with a non-clickable header (`session_backend`, default `—`, updated from JS `meta.agent`) and actions Show window, New chat, Mute replies, Interrupt, Quit. No listen/clipboard/capture/watch rows. Icon presence is manual smoke.
2. **FR-2 Show window** — Left-click and menu Show focus the existing `main` window; no second window; no send/listen/approve.
3. **FR-3 New chat** — Switch to Agents and call existing `newChat()`; do not `/send`.
4. **FR-4 Mute replies** — Toggle `Voice.prefs().autoRead` (muted ⇔ `autoRead === false`); muting calls `Voice.stopSpeaking()`; composer checkbox matches on next Agents paint.
5. **FR-5 Interrupt** — `POST /api/agents/chats/{id}/interrupt` for selected-if-busy else first busy chat; if none, toast and do not create a chat.
6. **FR-6 Hide vs Quit** — Caption/OS close hides to tray and does not stop serve. Quit stops owned sidecar only (T-001 reuse rule). Caption close no longer equals T-001 quit.
7. **FR-7 Registry** — Six skeleton rows `available = true`; every other `desktop/features.toml` row stays `available = false`.

## Non-Functional Requirements

- Loopback JS: no `shell`/`fs` (`loopback-chrome.json` permissions set unchanged aside from any invoke needed for the backend header).
- `console/` stays stdlib-only.
- Tray after window; do not block sidecar ensure.
- Windows smoke; portable host.
- Idle icon only; later icon states out of scope.

## Acceptance Criteria

- [ ] Tray icon present after shell launch (smoke)
- [ ] Menu is skeleton only
- [ ] Header is not a backend picker
- [ ] Header shows backend id or `—`
- [ ] Hide then left-click restores the same window
- [ ] New chat opens the New chat form without `/send`
- [ ] Mute writes `voice.autoRead` and stops speaking
- [ ] Interrupt hits existing HTTP when a chat is busy; toast when not
- [ ] Close leaves serve up; Quit owned stops serve; Quit reused leaves serve up
- [ ] `features.toml` skeleton `available` true, others false
- [ ] Browser path unchanged (no tray)

## Out of Scope

Listen, dictate, vendor STT from tray, clipboard, capture, watch, actuation, saved prompts, DND, Settings clutter UI, global-shortcut chords, Rust TOML parser, multimodal `/send`, whisper.cpp, installers.

## Business Rules

- **BR-1** No second orchestrator / backend picker / cloud flag
- **BR-2** Only `skeleton = true` rows this ticket
- **BR-3** Never one-click approve actuation / clipboard-read / screenshot-to-cloud
- **BR-4** Quit does not kill reused serve; hide kills no serve

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements]] · [[T-002-requirements-draft]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- Design: [[desktop-assistant]]
- Shell: [[T-001-summary]]
