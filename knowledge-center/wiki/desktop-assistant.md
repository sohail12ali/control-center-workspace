# Delivery Console as a local multimodal desktop assistant

Feasibility and architecture for a native shell around the Delivery Console:
screen capture, local speech, clipboard, and gated OS control, with every
spoken turn routed through the **existing** Agents backends.

This is durable design, not a ticket. Implementation is phased. Phase 1 is [[T-001-summary]] — the shell lives in `desktop/` (Tauri 2).

**Status:** evaluation, 2026-09-05. Phase-1 host on [[T-001-summary]] is Tauri 2 (`desktop/src-tauri/`). Tray registry and menu IA locked the same day; first tray code is [[T-002-summary]].
**Locked choices:** native desktop shell as the main window; local-first
default (Ollama / LM Studio + local STT/TTS); shell is portable, Windows is
the smoke OS for T-001; tray is a remote control of the live Agents chat, not
a second product.
**Reasoning backends:** user-selectable per chat — `ollama`, `lm-studio`,
`claude`, `cursor-agent`, `openrouter`. Picking a hosted or vendor CLI
backend **is** the cloud opt-in for that turn’s transcript and screenshot.

## Verdict

Feasible as a **new native shell around the existing console**, not as
features bolted into `console/`. A browser tab cannot capture other apps,
inject mouse and keyboard, or keep an always-on microphone private. The
console already owns the agent work: one Agents tab, four transports, gated
approvals, MCP.

Voice chat is not a second product. It is an input adapter on the live Agents
session. Local STT turns speech into text; the shell optionally attaches a
screenshot; that turn goes to whichever backend the user already picked; the
existing SSE stream comes back; TTS reads the finished reply (the Agents tab
already does this with `autoRead`).

The stdlib-only `python console/kanban.py serve` path keeps working without
the shell. OS **actuation** stays behind the existing Permission needed gate.

## What already exists

Do not rebuild these. Cite them when implementing.

- **Stdlib-only console.** `console/README.md`: no pip, no frontend build,
  bind `127.0.0.1:8790`. Capture, OCR, and input must not grow a
  `requirements.txt` inside `console/`.
- **Backends are config.** `console/config/agents.toml` already ships
  `claude` (`stream_json`), `cursor-agent` (`resume`), `openrouter` /
  `ollama` / `lm-studio` (`openai_api`). The composer already picks backend
  and model. Voice reuses that picker.
- **Send path is text-only.** Live chat posts `{ text, mode }` to
  `/api/agents/chats/{id}/send` (`console/static/agents.js`).
  `LiveSession._deliver` in `console/server/agent_session.py` writes only
  `{"type":"text"}` blocks. `ApiSession` in
  `console/server/agent_api_session.py` appends
  `{"role":"user","content": text}` as a string. Screenshots need a
  multimodal send.
- **Plugin contract.** New HTTP surfaces are a module plus a row in
  `console/config/plugins.toml`. `httpd.py` is never edited.
- **Safety pattern.** `gated_tools` plus in-chat Allow / Deny.
  `run_command` is already “the shell, therefore gated.” Desktop actuation
  is the same class of danger with a larger blast radius.
- **Voice today.** Local whisper.cpp in the shell (T-006), with
  `console/static/voice.js`'s Web Speech dictation as the browser-only
  fallback, and local `speechSynthesis` for finished replies. Hands-free
  landed in T-008: a loop over the same take, with the wake-word check sitting
  between local transcription and the send, so unaddressed speech never leaves
  the machine. The reply path (speak `text.done`) is correct for every backend.
- **Clipboard today.** Ticket-id copy in the board UI only.

```text
User --speak--> whisper.cpp --transcript--+
User --snip---> DXGI capture --png-------+--> /send (existing Agents chat)
                                              |
                         agents.toml picker --+
                                              v
                    ollama | lm-studio | claude CLI | cursor-agent | openrouter
                                              |
                                              v
                                    normalized SSE --> TTS
```

The Python console stays the ticket and agent brain. The shell owns pixels,
mic, and speakers. Do not invent a second orchestrator (no LangGraph, no
CrewAI, no Hugging Face speech-to-speech as the agent).

## Voice turn routing

One user action: talk, optionally attach what is on screen, hear the answer.
The destination is the **current Agents chat’s backend**, not a hidden VLM.

| Backend | Transcript | Screenshot | Reply |
| --- | --- | --- | --- |
| Ollama / LM Studio (`openai_api`) | User text in the existing loop | OpenAI `image_url` content parts (data-URL). Needs a vision model (`qwen2.5vl`, etc.). Text-only models get OCR + UIA text instead, and the UI says so. | Same SSE → TTS |
| OpenRouter (`openai_api`) | Same loop | Same `image_url` parts. Model must be vision-capable. Pixels leave the machine. | Same SSE → TTS |
| Claude Code CLI (`stream_json`) | Extend `_deliver` so the user message is transcript plus image | Primary: write PNG under `console/.cache/desktop-captures/` (gitignored) and put the path in the prompt — the method that works on Windows. Try Anthropic image content blocks on stdin if the installed CLI accepts them; fall back to path. | Existing stream-json → TTS |
| Cursor Agent CLI (`resume`) | Transcript is `{prompt}` | CLI takes a string `-p`. Write the PNG, append `Screenshot saved at {path} — open and inspect it.` Cursor’s file tools read the image. | Existing per-turn stream → TTS |

**Fallback ladder** (every backend, fail visibly):

1. Native image (API vision parts, or a Claude image block if supported).
2. Workspace PNG path in the prompt (Claude and Cursor). API backends cannot
   use `read_file` for pixels; they must use `image_url`.
3. WinRT OCR plus UIA snapshot as text — always works, including text-only
   local models.

**Composer / API change (when building):** `/send` grows optional
`image_path` (workspace-relative, confined) or a capture id minted by the
shell. The UI shows a chip: this turn includes a screenshot → {backend}. No
silent attach.

**Hands-free:** STT commits a phrase → same `/send` as typing. TTS already
speaks finished assistant text; turn it on for voice mode. Barge-in =
interrupt the current turn (`/interrupt`, already exists on steerable CLIs)
then send the new transcript.

## Privacy

Local-first is the **default backend**, not a wall.

- Ollama / LM Studio: transcript and pixels stay on the machine.
- Claude CLI / Cursor Agent / OpenRouter: transcript and any attached
  screenshot go to that vendor. The voice bar must name the destination
  **before** send.
- Do not add a second “cloud flag” that can disagree with the backend
  picker. The picker is the consent.
- Telegram must not approve screenshot, clipboard-read, or input tools.
  Today Telegram can approve `run_command`
  (`console/server/telegram_bot.py`). A parked approval that ships a
  screenshot of a bank app to a phone is a different product.

## Capability feasibility

| Capability | Feasible? | What done means |
| --- | --- | --- |
| On-demand full / region screenshot | Yes | DXGI / Windows Graphics Capture in the shell; exclude the assistant window |
| Voice → any existing backend → spoken reply | Yes | STT text + optional PNG on `/send`; reuse SSE + `autoRead` |
| Screenshot on Claude / Cursor CLI | Yes, via file path | Windows paste-into-CLI is unreliable; path-in-prompt is the method that works |
| Screenshot on OpenRouter / local VLM | Yes | Extend `ApiSession` from string `content` to multimodal parts; pick a vision model |
| Real-time visual awareness | Partial | Capture can be 30 fps. Model analysis cannot. Ship on-demand plus optional ~0.5–1 Hz watch with a visible indicator |
| OCR | Yes, cheap | `Windows.Media.Ocr` (WinRT) as the text fallback when the model cannot take images |
| Mouse / keyboard / app launch | Yes, high risk | Prefer UI Automation (invoke / set-value) over click-at-coordinates. Pixel-click is the fallback for owner-drawn apps. App launch is allowlist-only, fail-closed |
| Clipboard read / write | Yes | Native APIs. Read is sensitive (passwords); treat as gated. Write of drafts is the easy win |
| End-to-end chain (see → explain → draft → clipboard) | Yes | Tool-calling the console already does. No new agent framework |
| Autonomous multi-app GUI workflows | Weak locally | Industry computer-use success on novel UIs is unreliable. Later phase with a measured success-rate budget, not a launch claim |

## Recommended stack

Picks below are recommendations until a ticket records them in a
decision-log. Shell + local-first + per-chat backend picker are already
locked (see top).

### Desktop shell

| Rank | Choice | Why | Why it could be wrong |
| --- | --- | --- | --- |
| Primary | **Tauri 2** (WebView2 on Windows, WKWebView on macOS, WebKitGTK on Linux) | Small binary, capability-based IPC. Spawn `kanban.py serve` and load the loopback URL. T-001 ships this host. | Native webviews differ across OS; chrome is HTML on Windows/Linux and overlay traffic lights on macOS |
| Runner-up | Electron | Mature packaging; identical Chromium everywhere | Heavy. The reason to pick it (Chrome Web Speech) dies once STT is local |
| Reject | pywebview / a Python GUI | Weak capability model; fights stdlib-only `console/`; poor fit for DXGI / UIA | — |

Sources: Tauri sidecar docs; Tauri 2 vs Electron comparisons retrieved 2026-09-05.

### OS control (inside the Tauri Rust host, not pip)

| Rank | Choice | Why | Why it could be wrong |
| --- | --- | --- | --- |
| Primary | Windows UI Automation + Win32 `SendInput` via the `windows` crate; clipboard via `arboard`; capture via `windows-capture` or DXGI Desktop Duplication; OCR via WinRT `Windows.Media.Ocr` | Observation and action on the same machine without a Python GPU sidecar. OCR needs no extra model | UIA trees are empty on owner-drawn apps; those need OCR / pixel-click later |
| Runner-up | Copy the **ladder** from wincrust (UIA first, OCR fallback, allowlisted launch) — not the repo as a dependency | Same policy, less vendor lock | Research-shaped repos rot |
| Reject as the product | UI-TARS Desktop, OmniParser-in-process, pyautogui | Competitor Electron app; YOLO+Florence extra GPU sidecar; pixel-only and the wrong language layer | — |

Later / optional perception: OmniParser or UI-TARS-1.5 only if UIA coverage
is measured and wanting. Cua VMs are for **safe eval**, not for driving the
user’s real desktop.

Sources: microsoft/OmniParser, bytedance/UI-TARS-desktop, trycua/cua,
nhatvu148/wincrust, crates.io `forepaw` / `dxgi-capture-rs` — retrieved
2026-09-05.

### STT / TTS

| Rank | Choice | License / notes |
| --- | --- | --- |
| STT primary | [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | MIT. Windows, CUDA or CPU, no Python. `small` / `turbo` for live dictation |
| STT runner-up | faster-whisper | Easier, but a Python dep — lives in the desktop sidecar, never in `console/` |
| VAD | Silero VAD | Always-on / barge-in |
| TTS primary | Keep `speechSynthesis` until quality hurts, then Kokoro-82M | Kokoro is Apache-2.0 |
| TTS caution | Piper (OHF-Voice/piper1-gpl) | GPL-3. Fine as a **separate process** for internal use; flag before a distributed binary |
| Reject | Hugging Face `speech-to-speech` as the orchestrator | Duplicates the console loop |
| Reject | Web Speech STT | Vendor audio; `voice.js` already warns. Contradicts local-first |

### Reasoning

The rows already in `agents.toml`. Do not add a parallel model client.

- Local: Ollama or LM Studio. Attach a vision model (`qwen2.5vl:7b`, ~6–8 GB
  VRAM at Q4) when a screenshot is attached. A vision model that cannot call
  tools can *describe* a screenshot but cannot chain “draft email →
  clipboard” — that still needs a tool-capable text model in the same loop,
  which the console already documents.
- Claude CLI / Cursor Agent: existing transports; multimodal turn = path +
  transcript.
- OpenRouter: existing `openai_api` plus a vision model id from the picker
  or paste box.

CPU-only machines: skip the VLM; use OCR + UIA text. Do not pretend the
model saw the pixels.

### Orchestration

Existing console loop plus gated desktop **actuation** tools later
(`desktop_screenshot`, `desktop_ocr`, `desktop_clipboard_{get,set}`,
`desktop_snapshot`, `desktop_act`, `desktop_launch`). Same tools on MCP so
Cursor / Claude Code can use them when the shell is running.

Reject LangGraph, AutoGen, CrewAI, Agent-S as the runtime.

## Safety (non-negotiable)

Ship without these and the feature should stay off.

- Desktop actuation tools are **gated by default**. No full-bypass button in
  the UI (already the `agents.toml` policy).
- Telegram must not approve screenshot, clipboard-read, or input tools.
- Clipboard **read** and always-on mic are gated and visually indicated.
- App launch: allowlist in config, fail-closed.
- UIA actions prefer control patterns; coordinate-click requires a second
  confirmation.
- Capture skips the assistant’s own windows.
- Sending a screenshot to Claude / Cursor / OpenRouter is explicit in the
  composer, never implied.

## Where code lives (when building)

- Keep `console/` stdlib-only.
- Thin plugin (for example `desktop_feature`) that proxies to the shell when
  a localhost native token is present; disabled when the user is on a plain
  browser.
- New tree: `desktop/` (Tauri 2) beside `console/`, not inside it.
- Capture files: `console/.cache/desktop-captures/` (already gitignored via
  `console/.cache/` in `.gitignore`).
- Do not put Cargo or npm into the console test story.

## Tray as the desktop control surface

The tray (and hotkeys) are a **remote control for the live Agents session**.
They must not invent a second orchestrator, a second backend picker, or a
second cloud flag. “Tell an agent to do something” is not a free-text box in
the tray: show the window and focus the composer, run a short take into the
current chat, or pick a saved prompt. New session = existing `newChat()` in
`console/static/agents.js`.

Canonical list: `desktop/features.toml` (desktop tree, not `console/` pip or
Cargo). Every tray row and every hotkey uses the same `id`.

### Schema (`desktop/features.toml`)

Each `[[features]]` row:

| Field | Values |
| --- | --- |
| `id` | Stable key. Tray rows and hotkeys share it. |
| `label` | Menu text. |
| `phase` | `1` shell · `2` capture / multimodal · `3` local STT · `4` clipboard / OCR · `5` actuation · `6` watch |
| `group` | `window` · `listen` · `session` · `clipboard` · `capture` · `speak` · `watch` · `quit` |
| `risk` | `none` · `gated` · `dangerous` |
| `requires` | `live_chat` · `stt_local` · `webview_speech` · `clipboard_read` · `capture` (array, may be empty) |
| `tray` | `show` · `hide` · `submenu` · `header` |
| `available` | Host can perform this from the tray **today** |
| `enabled_default` | Off for mic, clipboard-read, capture, actuation |
| `skeleton` | `true` only for the first tray ticket’s wired rows |
| `never_one_click` | Tray must not approve this; in-chat Permission needed only |
| `parent` | Submenu owner `id` (optional) |
| `reason_unavailable` | Shown when `available = false` (same honesty as `voice.js`) |
| `hotkey` | Empty = unbound. Settings stores `desktop.hotkey.{id}` |

`[projection]` holds Settings keys and defaults (`left_click`, close-to-tray
vs quit, hide-unavailable). `[meta].webview_speech_from_tray` stays `false`
until we explicitly accept vendor STT from the tray.

Skip (not root-menu features): pixel-click, always-on 30 fps VLM,
Telegram-approved capture. `act_uia_click` and `act_app_launch` exist in the
registry with `tray = hide` and `never_one_click = true`.

### Settings projection

The Console **Settings** tab grows a **desktop-only** section, visible when
`html.in-shell` (the Tauri init script already sets that class). A normal
browser hides the section. User clutter lives in `C.prefs` under the keys in
`[projection]`; the registry file is the catalog, not per-user state.

Projection rules (tray is a view of the registry):

1. **Never one-click:** if `never_one_click = true` or `risk = dangerous`,
   the tray may **open the window** (or start a listen mode) but must not
   approve screenshot-to-cloud, clipboard-read, UIA click, or app launch.
   Those stay behind the existing Permission needed gate, in-chat.
2. **Unavailable:** default `unavailable = "disabled"` — keep the row
   visible and show `reason_unavailable` (matches `voice.js`: missing stays
   visible and says why). Settings may set `desktop.tray.hide_unavailable`
   to hide instead.
3. **Clutter:** applies only when `available = true`. If
   `enabled_default = false`, hide from the tray until the user enables
   `desktop.feature.{id}` in Settings. Default **off**: mic (short take,
   hands-free, dictate), clipboard-read, capture, actuation, watch.
   Unavailable rows follow rule 2, not this one.
4. **`tray = hide`:** omit from the root menu unless Settings opts that id
   in. Submenu children follow the parent.
5. **`tray = header`:** a label, not a button. `session_backend` is the
   current chat backend name — that line **is** the cloud consent reminder.
6. **Close-to-tray vs Quit** is `desktop.window.close_action` (default
   hide-to-tray). **Quit** still must not kill a reused `kanban.py serve`.
7. **Left-click** is `desktop.tray.left_click`: `show_window` (default) or
   `listen_toggle` (last-used listen mode). Right-click always opens the
   menu. Left-click never approves actuation.
8. **Hotkeys** bind to the same `id`s. One native implementation, two
   surfaces. Unbound until Settings writes `desktop.hotkey.{id}`.

### Menu groups and order

Icon is **state**; menu is **actions**.

Always (after [[T-002-summary]] tray skeleton):

- Header: current chat backend name (not a button)
- Show window
- New chat
- Mute replies (`autoRead`)
- Interrupt current turn
- Quit

When listen exists (phase 3; Web Speech stub from the tray only if we
explicitly accept vendor STT):

- Listening: Off · Short take · Hands-free (do not collapse these)
- Dictate (composer only; do not `/send`)

When clipboard exists (phase 4):

- Clipboard: Copy last reply · Send clipboard… (gated confirm)

When capture exists (phase 2+):

- This turn includes screenshot · Region (grey until wired; destination
  chip still required)

Same registry, not all in the root menu: pause listening when a permission
card is open; open last chat / Agents tab; saved prompt snippets; DND /
quiet hours; mic muted vs listening-off (two states); attach clipboard as
context without sending; watch on/off (phase 6) with a hard visual
indicator.

Three listen modes (keep them separate):

| Mode | What it does |
| --- | --- |
| **Dictate** | Fill the composer, do not send. Exists today as Web Speech in the Agents tab (`voice.js`); audio leaves the machine. Tray dictate waits for local STT unless vendor STT is explicitly accepted. |
| **Voice turn / short take** | Push-to-talk one phrase → STT → `/send` on the live chat. Hands-free “commits a phrase,” kept short on purpose. |
| **Hands-free listen** | VAD, barge-in, interrupt (`/interrupt` already exists). Phase 3 after whisper.cpp. Off by default; tray icon must show listening. |

### Icon states

| State | Meaning |
| --- | --- |
| idle | Not listening, not speaking, no pending approval |
| listening | Dictate, short-take armed, or hands-free on |
| speaking | TTS playing (`autoRead`) |
| needs-approval | Permission needed card open (dot overlay). Pause listening while this is showing |

Watch-on (phase 6) must be visually obvious; never a silent extra state.

### Native vs webview

Tray and hotkeys are native (Tauri `tray-icon`, already in the lockfile).
They emit events into the webview (`new-chat`, `dictate-toggle`, mute,
interrupt) for UI-owned work. Native STT, clipboard, and capture stay in
Rust and call `/send` (or a thin `desktop_feature` plugin with a localhost
token). Do **not** add `shell` / `fs` to
`desktop/src-tauri/capabilities/loopback-chrome.json`.

## Phased build

Do not attempt every capability in one ticket.

1. **Shell spike** — Native **Tauri 2** window, spawn `kanban.py serve`,
   load the UI, prove shutdown. No new tools. Ticket: [[T-001-summary]].
   The tray is **not** a seventh pile of features; it is the control
   surface for phases 2–6. First tray code is [[T-002-summary]] (registry
   already on disk; skeleton only: Show / New chat / Mute / Interrupt /
   Quit; every other row `available = false`).
2. **Multimodal `/send`** — transcript + optional PNG on the live chat;
   wire Claude (path), Cursor (path), OpenRouter / Ollama (image parts);
   OCR text fallback; destination chip. This is the voice-chat spine and
   does not wait for UIA.
3. **Local voice I/O** — whisper.cpp push-to-talk replacing Web Speech; TTS
   on `text.done`; then barge-in.
4. **Read-only awareness extras** — region capture, UIA snapshot, clipboard
   write.
5. **Actuation** — allowlisted launch + UIA invoke / type, still gated; no
   pixel-click yet.
6. **Watch + chain demos** — 1 Hz window watch; “explain this and put a
   draft on the clipboard.” Pixel-click / UI-TARS only if phase 5 coverage
   is measured and wanting.

## Non-goals

- Turning the stdlib console into an Electron/Tauri app in place.
- pip dependencies in `console/`.
- Replacing the Agents tab with UI-TARS Desktop or Agent TARS.
- Continuous 30 fps VLM analysis.
- Telegram approval of screen or input tools.
- A second “cloud vs local” flag beside the backend picker.
- A free-text “tell an agent” box in the tray.
- One-click tray approval of screenshot-to-cloud, clipboard-read, UIA, or
  app launch.
- Cross-platform v1 (macOS / Linux after Windows works).

## Links

- `console/README.md` — stdlib console this shell wraps
- `console/config/agents.toml` — backend rows voice turns reuse
- `console/static/voice.js` — current Web Speech dictation (vendor STT)
- `console/server/agent_session.py` — CLI user-message delivery
- `console/server/agent_api_session.py` — OpenAI-compatible loop (string content today)
- [[reset-to-clean-slate]] — wiki sibling; reset does not touch this page
- [[T-001-summary]] — phase 1 shell spike (open)
- [[T-002-summary]] — tray skeleton (open); control surface for phases 2–6
- `desktop/features.toml` — tray / hotkey / Settings feature registry
