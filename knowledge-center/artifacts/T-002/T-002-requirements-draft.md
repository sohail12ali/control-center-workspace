---
ticket: "T-002"
artifact: requirements-draft
status: frozen
freeze_status: frozen
iteration: 1
created: "2026-09-05"
last_updated: "2026-09-05"
---

# Requirements Draft: T-002

> Working requirements document. **Not frozen.** Expect revisions each iteration until `requirements T-002 freeze` passes.

**Command reference:**
- **Created by:** `requirements T-002 draft`
- **Grounded by:** `analyze T-002` → writes [[T-002-context-snapshot]]
- **Gaps surfaced by:** `challenge-requirements T-002` (gaps dimension)
- **Challenged by:** `challenge-requirements T-002` (adds ⚠ markers below)
- **Enriched by:** `requirements T-002 enrich`
- **Cross-checked by:** `challenge-requirements T-002` (overlap/conflict/reuse dimension)
- **Iterated by:** `requirements T-002 iterate`
- **Frozen by:** `requirements T-002 freeze` → produces [[T-002-requirements]]

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** A system-tray remote control for the live Agents chat, skeleton only.

**Business driver:** The desktop shell has a window (T-001) but no control surface for phases 2–6. The tray is that surface; first code must not become a second product.

**Raw intent verbatim:**
> Tray as the desktop control surface. First code drop is the registry + tray skeleton + Show / New chat / Mute / Interrupt / Quit, with every other row available=false. The tray is a remote control for the live Agents session, not a second orchestrator.

## 2. Context Summary

(Condensed from [[T-002-context-snapshot]])

- **Similar existing features:** Tauri window + sidecar ([[T-001-summary]]); `newChat` / interrupt POST / `autoRead` in `agents.js` + `voice.js`; feature catalog `desktop/features.toml`
- **Affected code areas:** `desktop/src-tauri/` (tray, close/hide, Quit); `console/static/desktop-chrome.js` (close); `console/static/agents.js` (public handlers); `desktop/features.toml` (`available` flags)
- **Known risks from history:** T-001 close stops owned sidecar; hide must not; Agents `onLeave` stops speech

## 3. Scope

### In scope
- Native tray icon and menu: header `session_backend`, `show_window`, `new_chat`, `mute_replies`, `interrupt`, `quit`
- Left-click Show window
- Close (HTML X and window close) hides to tray; Quit matches T-001 sidecar stop/reuse
- Webview events + `ConsoleAgents` handlers wrapping existing UI/HTTP
- Flip those six `desktop/features.toml` rows to `available = true`
- Enable Tauri `tray-icon` feature in `desktop/src-tauri`

### Out of scope (explicit)
- Listen modes, dictate, Web Speech from tray (`webview_speech_from_tray` stays false)
- Clipboard, capture, watch, UIA, app launch, saved prompts, DND
- Settings clutter toggles and hide-unavailable UI
- Global-shortcut chords (handlers may be id-keyed; no default hotkeys)
- Parsing `features.toml` in Rust; widening `loopback-chrome.json`
- Multimodal `/send`, whisper.cpp, installers

### Assumptions
- Stakeholder confirmed skeleton-five-actions ([[T-002-decision-log]]) — treated as signed intent, not a silent extra FR
- Windows is the smoke OS (same as T-001); code stays portable

## 4. Functional Requirements

### FR-1: Tray icon and skeleton menu
**Description:** While the desktop shell is running, the OS notification area shows an icon. Right-click (or platform menu-open) shows: a non-clickable header with the current Agents chat backend name (or a dash if none), then Show window, New chat, Mute replies, Interrupt current turn, Quit.

**Actor:** Desktop user

**Trigger:** Host `setup` after the main window exists

**Preconditions:**
- Tauri host started ([[T-001-requirements]] window)

**Flow:**
1. Host creates a tray icon using bundled `desktop/src-tauri/icons/`
2. Menu is built from the six skeleton ids only; tooltip is “Delivery Console”
3. Header text starts as `—`; JS emits the current chat `meta.agent` (empty → `—`) when Agents selection changes; native menu updates the header
4. User activates a row → native handler runs

**Postconditions / observable outcomes:**
- Tray is visible while the process runs, including when the window is hidden
- Menu has no listen/clipboard/capture rows

**Acceptance criteria (testable):**
- [ ] After launching the shell, a tray icon is present (manual smoke; no GUI test runner in-repo)
- [ ] Menu labels match skeleton rows; no `listen_*`, `clipboard_*`, `capture_*`, or `watch_toggle` items
- [ ] Header line is not an action (click does not change backend)
- [ ] Opening a chat updates the header to that chat’s backend id; with no chat it is `—`

**Business rules invoked:** BR-1, BR-2

### FR-2: Show window
**Description:** `show_window` (and left-click on the icon) shows and focuses the existing main window.

**Actor:** Desktop user

**Trigger:** Left-click tray icon, or menu Show window

**Preconditions:**
- Main window id `main` exists (`main.rs` `WebviewWindowBuilder`)

**Flow:**
1. Unhide if hidden
2. Focus / unminimize

**Postconditions / observable outcomes:**
- Window is visible and focused
- Sidecar process unchanged

**Acceptance criteria (testable):**
- [ ] Hiding the window then left-clicking the tray shows the same Console UI (not a second window)
- [ ] Left-click does not start listen, send, or approve tools

**Business rules invoked:** BR-1

### FR-3: New chat
**Description:** `new_chat` switches to the Agents tab and opens the existing new-chat form (`agents.js` `newChat()`).

**Actor:** Desktop user

**Trigger:** Tray menu New chat

**Preconditions:**
- Agents plugin enabled (existing Console)

**Flow:**
1. `ConsoleApp.go("agents")`
2. `ConsoleAgents` handler calls existing `newChat()`

**Postconditions / observable outcomes:**
- Agents tab visible; main pane is the New chat form
- No message is sent

**Acceptance criteria (testable):**
- [ ] Tray New chat shows the New chat form without posting `/send`
- [ ] Browser without the shell is unchanged (no tray; `ConsoleAgents` extra methods are unused)

**Business rules invoked:** BR-1

### FR-4: Mute replies
**Description:** `mute_replies` toggles existing `Voice.prefs().autoRead`. Checked/muted means `autoRead === false`. Unmute sets `autoRead` true. Muting stops current `speechSynthesis` via existing `Voice.stopSpeaking()`.

**Actor:** Desktop user

**Trigger:** Tray menu Mute replies

**Flow:**
1. Toggle `Voice.setPrefs({ autoRead })` as above
2. If muting, `Voice.stopSpeaking()`
3. Menu check state matches muted

**Postconditions / observable outcomes:**
- Composer “read aloud” checkbox matches the pref on the next Agents paint (`agents.js` 1197–1207)
- Pref persisted in `C.prefs` key `voice` even if the Agents tab is not mounted

**Acceptance criteria (testable):**
- [ ] Toggling Mute writes `console.voice` `autoRead`; after opening Agents, the checkbox matches
- [ ] Muting stops in-progress read-aloud

**Business rules invoked:** BR-1

### FR-5: Interrupt current turn
**Description:** `interrupt` posts the existing interrupt endpoint for the live busy chat, same as the Agents header button.

**Actor:** Desktop user

**Trigger:** Tray menu Interrupt current turn

**Preconditions:**
- Existing interrupt HTTP route (`agents.interrupt`)

**Flow:**
1. If Agents tab not active, `go("agents")`
2. Target chat: selected chat if `busy`; else the first `busy` entry in the existing chats list
3. If a target exists, `POST /api/agents/chats/{id}/interrupt`
4. If none, toast that nothing is running; do not POST; do not create a chat

**Postconditions / observable outcomes:**
- Same interrupt path as `agents.js` 949–953 when a busy chat exists

**Acceptance criteria (testable):**
- [ ] With a busy live chat, tray Interrupt causes the server interrupt path (`agents.interrupt`)
- [ ] With no busy chat, no new chat is created, `/send` is not called, and a toast explains that nothing is running

**Business rules invoked:** BR-1, BR-3

### FR-6: Hide to tray vs Quit
**Description:** Close from the HTML caption or window close hides the window to the tray and does not stop `kanban.py serve`. This **replaces** T-001 “caption close = quit” for the shell window. **Quit** (tray) is the T-001 close: stop sidecar only if `owned`.

**Actor:** Desktop user

**Trigger:** Close control / WM close; or tray Quit

**Flow:**
1. Close → hide window; process and tray remain; sidecar untouched
2. Quit → destroy window, `stop_owned` if `owned`, process exits

**Postconditions / observable outcomes:**
- Hide: port still serving; tray remains
- Quit owned: serve stops
- Quit reused: serve keeps running

**Acceptance criteria (testable):**
- [ ] Close then tray Show restores the window; owned serve still up
- [ ] Quit after the shell started serve leaves the port down (same as T-001 close)
- [ ] Quit after attaching to an already-running serve leaves the port up

**Business rules invoked:** BR-4

### FR-7: Registry flags
**Description:** After this ticket, `desktop/features.toml` sets `available = true` only on the six skeleton rows. All other rows remain `available = false`.

**Actor:** Maintainer / later phases

**Trigger:** T-002 implementation complete

**Acceptance criteria (testable):**
- [ ] `tomllib` load: skeleton ids `available` true; every non-skeleton `available` false

**Business rules invoked:** BR-2

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | Tray setup must not block sidecar ensure | Same launch path as T-001; tray after window | |
| Scalability | N/A — single local user | N/A — single desktop process | |
| Security / Auth | Loopback JS still has no `shell`/`fs` | `loopback-chrome.json` unchanged permissions set | [[T-001-requirements]] NFR 5 |
| Auditability | N/A — no new server audit stream | N/A — rationale: tray only drives existing UI/HTTP | |
| Availability | Hide-to-tray keeps serve reachable on loopback | Owned serve stays up while hidden | |
| Usability | Icon is idle state only this ticket; tooltip “Delivery Console” | Smoke for icon presence (no GUI runner); sidecar pytest still covers spawn/reuse/stop | [[desktop-assistant]] later icon states |
| Compliance | N/A | N/A — no new data leave the machine beyond existing Agents backends | |
| Portability | Same Tauri host matrix as T-001 | Windows smoke; macOS/Linux compile-time tray | |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| `desktop/features.toml` `available` | exists | bool per `[[features]]` | update on ship | `desktop/features.toml` |
| `C.prefs` `voice.autoRead` | exists | bool | toggle via mute | `voice.js` |
| Tray check state `mute_replies` | new (OS menu) | mirrors `autoRead === false` | process lifetime | FR-4 |

### Data flows
Tray menu click → Rust event → webview `ConsoleAgents.*` → existing prefs/HTTP → Agents UI.

Quit → `stop_owned` → `sidecar.py stop` if owned.

### Retention / archival
No new files. Voice pref remains browser `localStorage` (`core.js`).

## 7. Business Rules

- **BR-1:** The tray must not invent a second orchestrator, backend picker, or cloud flag. Actions operate on the current Agents session or open the existing new-chat form.
- **BR-2:** Menu growth is `desktop/features.toml`. T-002 only wires `skeleton = true` rows.
- **BR-3:** Tray must not approve actuation, clipboard-read, or screenshot-to-cloud (never-one-click).
- **BR-4:** Quit must not kill a reused `kanban.py serve`. Hide must not kill any serve.

## 8. Edge Cases

- Agents plugin disabled / tab hidden: New chat and Interrupt fail visibly (toast or disabled menu), no crash
- Multiple busy chats: interrupt selected-if-busy, else first busy in `st.chats`
- No live chat: Interrupt toasts; header shows dash
- Webview not yet loaded: events ignored until ready; no panic; header stays `—`
- Second Show: focus existing `main` window, do not create another
- Mute when Agents tab unmounted: still write `C.prefs` `voice` (prefs do not need the tab)
- Force-kill of host: Windows job object from T-001 still applies to owned serve

## 9. Interactions with Existing Features

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[T-001-summary]] window close / sidecar stop | conflict if hide-to-tray used Destroyed | high | isolate: hide ≠ quit; Quit keeps T-001 stop/reuse |
| `agents.js` `newChat()` | reuse | low | extend `ConsoleAgents` public API |
| `POST .../interrupt` | reuse | low | same HTTP from tray handler |
| `Voice.prefs` `autoRead` | reuse | low | mute toggles existing pref |
| `loopback-chrome.json` | isolation | high | do not add shell/fs |
| `desktop/features.toml` later-phase rows | overlap if shown grey | med | defer: omit until `available` |
| `agents.js` `onLeave` stops speech | overlap | med | `go("agents")` before interrupt/new chat |
| Telegram `/interrupt` | isolation | low | unchanged; tray is local UI |

## 10. External Dependencies

- Tauri 2 `tray-icon` feature (crate already in `Cargo.lock`)
- OS notification area
- Existing loopback Console (no new Python deps)

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Product / engineer | Irshad | Skeleton-only tray; no second product | yes — plan 2026-09-05 + continue 2026-09-05 |
| Implementer | Sohail Ali | Host + JS handlers | no |

## 12. Open Questions (mirrored)

None opened this draft. Scope locked in [[T-002-decision-log]].

## 13. Challenge Findings (⚠)

- ⚠ [ambiguity] §FR-5: “no-op or toast” is two behaviours — **resolution:** `accepted: toast only; iterate 2026-09-05`
- ⚠ [unstated-assumption] §FR-1: backend header text has no JS→native update path — **resolution:** `resolved: requirements iterate 2026-09-05 — JS emits agent id`
- ⚠ [untestable] §FR-1 AC “tray icon is present”: no automated GUI runner in repo — **resolution:** `accepted: smoke AC + sidecar pytest still owns hide/quit process rules`
- ⚠ [contradiction] §FR-6 vs [[T-001-requirements]] FR 4: close used to stop owned sidecar — **resolution:** `accepted: hide-to-tray-not-destroy; Quit keeps T-001 FR 4`
- ⚠ [ambiguity] §FR-4: checkbox sync if Agents tab not mounted — **resolution:** `resolved: requirements iterate 2026-09-05 — prefs always; checkbox on next paint`

## 14. Draft History

See [[T-002-iteration-log]]. Current iteration: **1**

---

## Freeze Checklist (run by `requirements freeze`)

- [ ] All `〈TBD〉` placeholders replaced or explicitly deferred
- [ ] All ⚠ findings resolved or explicitly accepted with rationale
- [ ] All blocker open questions answered
- [ ] Every FR has at least one testable acceptance criterion
- [ ] Every NFR has a concrete target or documented reason for absence
- [ ] Every new/changed entity has a canonical reference or creation plan
- [ ] Out-of-scope list is non-empty
- [ ] Stakeholder sign-off recorded
- [ ] `{ID}-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-002-summary]] · [[T-002-analysis]] · [[T-002-requirements-draft]] · [[T-002-context-snapshot]] · [[T-002-gap-analysis]] · [[T-002-iteration-log]] · [[T-002-decision-log]] · [[T-002-plan]] · [[T-002-progress]] · [[T-002-verification]]
- Design: [[desktop-assistant]]
