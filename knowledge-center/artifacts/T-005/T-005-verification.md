---
ticket: "T-005"
artifact: verification
---

# Verification: T-005

Verified 2026-09-07 against the release build on Windows 11.
**pytest 992 passed** (949 before T-005), **cargo test 47 passed** (3 before),
harness lint clean (39 skills, 7 agents).

`-o addopts=""` is needed for a trustworthy pytest count — `pytest.ini` sets
`-q`, under which this suite prints only progress dots with no summary line.
Every number here came from a run with the summary visible.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | New crates build on this toolchain | PASS | Spiked BEFORE any code was written against them, because this was the programme plan's biggest risk. `cargo build` exit 0 in 2m46s; arboard 3.6.1, tiny_http 0.12.0, xcap 0.9.8, image 0.25.10, windows 0.61.3 beside xcap's own 0.62.2. No CMake, no LLVM |
| 2 | Tray icon per assistant state | PASS | 20 committed PNGs from `desktop/icons/gen_tray_icons.py`; five states x approval badge x colour and macOS template renderings. `icons.rs` embeds them with `include_bytes!` so a missing asset is a build failure, not a wrong icon in a shipped binary |
| 3 | State machine is testable without hardware | PASS | `tray_state.rs` is pure; 14 tests cover a full voice turn, a permission card pausing listening, mute never entering the speaking state, the mute glyph never hiding an open mic, and the approval badge surviving a state change |
| 4 | Loopback bridge with auth | PASS | `bridge.rs` on an ephemeral port; bearer token in `console/.cache/desktop/bridge.json`; `/health` deliberately unauthenticated so a stale pointer is distinguishable from a wrong token; loopback peers only; 1 MB body cap |
| 5 | Screenshot: screen / monitor / window / region | PASS | Live: region capture produced an exact 240x120 PNG (4,081 bytes, valid magic); an 800x400 request with `max_side=200` returned 200x100. Own window excluded; a minimized window is reported rather than returning its blank frame |
| 6 | Clipboard read, write and peek | PASS | Live round-trip through the real Windows clipboard: write 15 chars -> peek reported `text_len: 15` with a 40-char-capped preview -> read matched the probe exactly |
| 7 | OCR | PASS | Live: `engine=winrt language=en-GB`, 5 lines of real on-screen text out of a 600x200 capture. Unit test renders "HELLO" as block glyphs and reads it back. `tesseract` is the macOS/Linux substitute — written, **not exercised** (not installed here) |
| 8 | Capabilities are probed, not claimed | PASS | `caps.ocr` comes from `ocr::available()`, which asks whether an engine answers on THIS machine. `speak` and `stt` report false rather than being omitted, so the console can say why a tool is unavailable |
| 9 | Verbs reachable on both transports | PASS | Seven `desktop-*` verbs. `console_desktop_*` present in `agent_tools.tool_definitions`; all seven listed over MCP by driving `mcp_server.py` as a real subprocess over stdio |
| 10 | Screenshot and clipboard-read are desk-only | PASS | `agent_approvals.LOCAL_ONLY` under both spellings a model can see them by. Telegram approval refused; `allow-session` downgraded to a single `allow`; any recorded session-allow skipped; the phone gets a card with no buttons and a line saying to answer at the console. A DENY is still accepted from anywhere |
| 11 | The gate names actually match | PASS | A test compiles the claude hook's regex and asserts it matches `mcp__console__desktop-screenshot` and `-clipboard-read` but NOT `-windows`. The prefix was checked against real `session.init` events in `console/.cache/agent-chats/` and `.mcp.json`, not assumed — a wrong name compiles fine and gates nothing |
| 12 | Confinement on capture ids | PASS | `path_for` refuses `../../.env`, `a/b`, `..`, `""`, `x.png`, ids with spaces. Live: `ocr("../../.env")` -> `not a capture id` |
| 13 | Tray follows live turn events | PASS | A real assistant turn drove **idle -> thinking -> idle**, polled through `GET /state`; `host.log` shows `tray-link: following the assistant stream` |
| 14 | Honest when the shell is down | PASS | Every verb returns `{"ok": false, "reason": "shell not running"}`. A stale pointer (force-kill leaves one) reads identically, because availability is a `/health` probe |
| 15 | Nothing breaks the other platforms | PARTIAL | Compiles and tests green on Windows; the per-OS backends (tesseract OCR, xcap's CoreGraphics/X11 paths) are written but **unexercised** — no macOS or Linux hardware. The 3-OS CI job from T-003 is defined but still unproven, pending a push |

## Test Results

```
python -m pytest -o addopts="" -q     ->  992 passed
cargo test                            ->   47 passed
python console/kanban.py harness lint ->  39 skills, 7 agents | 0 error(s), 0 warning(s)
```

Live, release build:

```
caps: {capture: true, clipboard_read: true, clipboard_write: true,
       ocr: true, speak: false, stt: false, windows: true}

region capture 600x200 -> capture_id 18d2f37dae92cdbc
ocr -> engine=winrt language=en-GB, 5 lines
ocr("../../.env") -> {ok: false, reason: 'not a capture id: "../../.env"'}

clipboard: write 15 -> peek {has_text: true, text_len: 15} -> read matched

assistant turn -> tray state: idle -> thinking -> idle
host.log: tray-link: following the assistant stream
```

## Edge Cases Probed

- **Two threads opening the clipboard at once** corrupted the heap. Now
  serialised by a mutex in `clipboard.rs`. Found by test-filter isolation
  after three wrong diagnoses — see Notes.
- **WinRT on a caller's thread** crashed once `arboard` had put that thread in
  a single-threaded apartment. OCR now owns one long-lived thread with one
  apartment.
- A **minimized** window is refused with its title, not captured blank.
- A **window title matching several windows** picks the largest non-minimized
  one rather than the first.
- **`max_side=0`** means no downscaling; a tall image scales on its longest
  edge.
- A **corrupt or absent bridge pointer** both read as "shell not running".
- **A window list** returns titles and geometry only — never a process path.

## Notes

### The crash, and three wrong diagnoses

Worth recording because the wrong turns cost more than the fix. The test
binary died with an access violation, then heap corruption, then an access
violation again. I twice concluded WinRT apartment handling was at fault and
restructured OCR around it — a thread per call with paired
`RoInitialize`/`RoUninitialize`, then a single long-lived worker. Isolating by
test filter found the actual cause: `-- clipboard` matched both a clipboard
test and an OCR test that deliberately touches COM first, and those two
opening the clipboard concurrently corrupted the heap. The whole suite passed
single-threaded, which was the clue I should have taken first.

The single-worker OCR design was kept — it is the right shape for WinRT
whatever caused this — but its docstring no longer claims it fixed the crash.

### What this feature reads

The OCR verification captured a region of a real screen and read browser tab
titles out of it. Captures were deleted afterwards. That is the feature
working as intended, and it is exactly why the capture feeding it is gated and
answerable only at the desk.

### Not verified

- **macOS and Linux**: no hardware. The `tesseract` OCR backend and xcap's
  non-Windows capture paths compile but have never run. Recorded as PARTIAL on
  AC 15 rather than claimed.
- **The 3-OS CI job** (added in T-003) is still unproven — proving it needs a
  push, which is ASK-gated.
- **A gated screenshot answered through a real card in the UI**: the
  approval machinery is covered by tests driving `Approvals` directly, but the
  full click-through in a browser was not performed.

## Links
- [[T-005-summary]] · [[T-005-analysis]] · [[T-005-requirements]] · [[T-005-decision-log]] · [[T-005-plan]] · [[T-005-progress]] · [[T-005-verification]]
