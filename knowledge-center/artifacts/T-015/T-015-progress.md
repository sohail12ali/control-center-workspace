---
ticket: "T-015"
artifact: progress
---

# Progress: T-015

## 2026-09-10 — kickoff and baseline

- **Done:** Seeded artifacts from `_template`; `ticket create T-015` (lane `open`,
  priority high). Baseline captured before any change: **1175 python tests pass**
  (`pytest -o addopts=""`, 94.6s) and **148 Rust tests pass**.
- **Found:** `cargo` cannot compile in a plain shell — `cc-rs` fails on a missing
  `excpt.h`. `. ./desktop/msvc-env.ps1` must be sourced first; it is already in the
  repo for exactly this. Also worth knowing: piping cargo through PowerShell's
  `Select-Object` makes it exit 1 on a clean build, because PS treats cargo's
  stderr as an error. Redirect to a file and read that.
- **Done:** Landed the seven uncommitted Rust files that were in flight
  (`f66f79a`) before starting, per the plan's note — quit path, settings cache,
  hands-free "heard you" line. Both suites were green with them in place.
- **Started:** TEMPLATE.

## 2026-09-10 — Thread 1, latency (`37d1aef`)

- **Done:** T-015-01, T-015-02, T-015-03, T-015-04.
  - `agent_manager.create(..., open=False)` starts a session and sends nothing.
    The persona is parked on the session for the first real send when the backend
    has no system-prompt flag, via `BaseSession.defer_system_prefix` — consumed in
    `send`, which is the one place every caller goes through. The assistant
    feature calls `send` directly rather than through `agent_manager.send`, so a
    fix in either caller alone would have left the other dropping the persona.
  - `assistant_config.LOCAL_FIRST` puts `openrouter` ahead of the CLIs.
  - `assistant_config.talk_ready` preflights a keyless row on residency and tool
    support; `resolve_backend` asks candidates one at a time and reports every
    skip with a reason.
  - `ApiSession` records a real `duration_ms` and a new `ttft_ms`, threaded
    through `telemetry.FIELDS`.
  - `settings_get` no longer returns `installed`, so it opens no sockets;
    the Settings tab reads availability from `/api/agents/backends`.
- **Evidence:** 1195 python tests pass (20 new). Incidentally,
  `test_assistant.py` went from 12.5s to 2.9s — the probing was costing the
  tests too, which is the same 1.5s-per-provider cost the tray was paying.
- **Next:** Thread 2.

## 2026-09-10 — Thread 2, the tray (`b03a079`)

- **Done:** T-015-05, T-015-06, T-015-07.
  - `desktop/src-tauri/src/features.rs` parses `desktop/features.toml` from an
    `include_str!`, so a malformed registry is a failed build rather than a shell
    that starts with a silently defaulted menu.
  - `tray.rs` walks it. 15 rows where 8 were hand-written. Unavailable rows render
    disabled carrying their `reason_unavailable`. `never_one_click` is honoured —
    `clipboard_send`, `capture_this_turn` and `capture_region` open the window and
    never act.
  - `clipboard_copy_last` posts the sentence "copy that", so it goes through the
    same fast-command dispatch as typing it. New `console_api.rs` holds the one
    HTTP client for that; `listen.rs`'s private copy is gone.
  - `click.rs` reads its setting through the cached reader.
    `console_settings::string_or` is **deleted** — its only caller was the tray's
    UI thread and "fetch a single key" was the shape of the bug.
  - Drift is now checked from both directions: Rust warns at startup about an
    available row with no dispatch arm, and
    `test_features.py::TestTheTrayCarriesOutWhatTheRegistryOffers` fails on
    either half.
- **Correction to the plan:** the plan said "16, not 8". 16 features are marked
  available, but `pause_listen_on_permission` is `tray = "hide"` — a behaviour,
  not a row. **15 menu rows** is the right number, and it is pinned in
  `features.rs`'s tests.
- **Evidence:** 157 Rust tests pass (9 new), 29 desktop python tests pass.
- **Next:** Thread 3.

## 2026-09-10 — Thread 3, the overlay (`fba0a29`)

- **Done:** T-015-08, T-015-09.
  - `hud.rs` gains `dismiss`, `approval`, and a 120s `arm_watchdog` re-armed on
    every state change via a generation counter.
  - `tray_paint`: `Event::ApprovalResolved` used to map to `{}` — it now hides.
  - `tray_link`: a lost stream clears a stale **card**, not only a stale
    `Thinking`; the `reply` event reaches the panel; the card's tool and key are
    captured from the stream.
  - `hud.html`: ✕, Esc, `data-tauri-drag-region`, and state-dependent buttons
    (Allow/Deny, Send now, Stop). Every control **emits** a Tauri event and the
    shell acts, so the page still has no token and cannot reach the console. The
    `hud` window already held `core:event:default`.
  - New `POST /api/assistant/approve` answers a card on the Assistant's own chat,
    so the overlay needs no chat id.
- **Found by looking at it in a browser, not by review:** putting the buttons on
  their own row overflowed the 104px window, and giving them the meter's row hid
  the level meter during listening — the one thing the panel exists to show. They
  sit in the top row instead, replacing the hint they made redundant. Re-measured
  at 380×104: **zero overflow in all four states**, meter present, correct
  controls per state, correct in light and dark.
- **Evidence:** 160 Rust tests pass, 1200 python tests pass.
- **Next:** VERIFY — drive the live tray menu with T-002's Win32 helper, then
  close T-002.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
