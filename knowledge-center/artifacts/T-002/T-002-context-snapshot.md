---
ticket: "T-002"
artifact: context-snapshot
status: draft
created: "2026-09-05"
last_updated: "2026-09-05"
scope: codebase + history
---

# Context Snapshot: T-002

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-002 context`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

Ship a native tray that remote-controls the live Agents chat: Show window, New chat, Mute replies, Interrupt, Quit — not a second agent product.

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Native window + sidecar | `desktop/src-tauri/src/main.rs` `open_window` / `sidecar::ensure` | Tauri host, Python serve | Keep; tray sits beside the window | `main.rs` 64–127 |
| HTML window chrome | `console/static/desktop-chrome.js` | loopback JS, `__TAURI__.window` | Close must change from destroy to hide | `desktop-chrome.js` 7–72 |
| New chat UI | `agents.js` `newChat()` | Agents tab IIFE | Call from a new `ConsoleAgents` method | `agents.js` 759–766 |
| Interrupt turn | `POST /api/agents/chats/{id}/interrupt` | JS, `agents_feature.py`, `agent_manager` | Same POST from tray handler | `agents.js` 949–953; `agents_feature.py` 141–213 |
| Mute / read-aloud | `Voice.prefs().autoRead` | `voice.js`, `C.prefs` `voice` | Tray toggles the same pref | `voice.js` 42–59; `agents.js` 1197–1207 |
| Tab navigation | `ConsoleApp.go("agents")` | `app.js` | Show + New chat should focus Agents | `app.js` 106–136, 342 |
| Honesty for missing features | `voice.js` support why-text | Agents composer | Later-phase tray rows; not T-002 menu | `voice.js` 1–7 |
| Feature catalog | `desktop/features.toml` | desktop tree | Flip `available` on skeleton rows | `desktop/features.toml` |
| Capability allowlist | `loopback-chrome.json` | Tauri | Do not add shell/fs | `loopback-chrome.json` 8–16 |

### Existing patterns to reuse
- Sidecar ownership: stop only if `owned` — `main.rs` 56–61, `sidecar.rs` `Handle.owned`
- Init class `html.in-shell` — `main.rs` 19–27
- Public tab hook pattern — `window.ConsoleAgents.compose` (`agents.js` 1366–1370)
- Prefs in `localStorage` via `C.prefs` (`core.js` 348–353)

### Naming and architectural conventions in play
- Feature ids in `desktop/features.toml` are the tray/hotkey keys — [[desktop-assistant]]
- No pip/Cargo/npm inside `console/` — [[T-001-requirements]] NFR 1
- Voice is an adapter on the current Agents chat — [[desktop-assistant]]

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| [[T-001-summary]] | Tauri 2 window, sidecar ensure/stop, integrated chrome | VERIFY, still open | Close currently equals destroy; Quit in T-002 must preserve reuse |
| — | Tray plan / wiki lock 2026-09-05 | Registry + menu IA on disk | Do not grow tray outside `features.toml` |

### Relevant commits / PRs
- `desktop/` has no git commits yet (`git log -- desktop/` empty). Host is uncommitted T-001 work.
- Agents tab history (unrelated to tray): `f8ffbc2`, `6f468c4` — chat list and lanes.

### Known incidents / regressions in this area
- T-001: inherited stdout + `CREATE_NO_WINDOW` hung sidecar spawn until `close_fds=True` (working copy / verification notes). Tray must not re-open that pipe.
- T-001 AC: reused serve on 8790 must survive host exit.

## 4. External Systems in the Loop

- Tauri 2 / WebView2 (Windows smoke) — existing host
- `python console/kanban.py serve` on loopback — existing sidecar
- OS notification area (Windows tray / macOS menu bar / Linux status icon) — new this ticket
- No new vendor STT, capture, or cloud API

## 5. Preliminary Risks Spotted

- Hide-to-tray vs T-001 “close stops sidecar”: users who expect X to quit will leave serve running when the shell owned it. Quit must be obvious in the tray.
- Agents tab `onLeave` stops speaking (`agents.js` 1378–1379): navigating away after Mute/New chat can surprise. Tray actions should `go("agents")` before calling handlers.
- `newChat()` is not exported: a tray event with no listener is a silent no-op.
- Hardcoded ids can drift from `features.toml` if a later phase edits the catalog only.

## 6. Open Confirmations

- Tauri 2.11 `tray-icon` feature name and menu API — confirmed in crate lock (`tray-icon` dep of `tauri` 2.11.5); not yet compiled with the feature on in this package.
- Linux/macOS tray behaviour not smoked on this machine (T-001 Windows smoke OS). Portable code, Windows verify.

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-09-05 | `kanban.py context T-002` | ticket digest | trace-context |
| 2026-09-05 | Read | `desktop/src-tauri/src/main.rs` | window/sidecar/no tray |
| 2026-09-05 | Read | `desktop/src-tauri/Cargo.toml`, `tauri.conf.json`, `loopback-chrome.json` | features and IPC |
| 2026-09-05 | Grep | `tray` under `desktop/` | no host tray usage |
| 2026-09-05 | Read | `console/static/agents.js` 759–766, 949–953, 1197–1207, 1366–1380 | newChat / interrupt / mute / exports |
| 2026-09-05 | Read | `console/static/voice.js` 1–59 | autoRead prefs |
| 2026-09-05 | Read | `console/static/desktop-chrome.js` | HTML close |
| 2026-09-05 | Read | `console/static/app.js` 106–136 | tab go |
| 2026-09-05 | Grep | `interrupt` in `console/server` | HTTP interrupt |
| 2026-09-05 | Read | `desktop/features.toml` | skeleton flags |
| 2026-09-05 | Read | [[T-001-requirements]], [[desktop-assistant]] | contracts |
| 2026-09-05 | `git log -- desktop/` | empty | host uncommitted |

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements-draft]] · [[T-002-context-snapshot]] · [[T-002-gap-analysis]] · [[T-002-iteration-log]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- Design: [[desktop-assistant]]
- Shell spike: [[T-001-summary]]
