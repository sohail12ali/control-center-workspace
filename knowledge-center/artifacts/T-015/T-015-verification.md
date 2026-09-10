---
ticket: "T-015"
artifact: verification
---

# Verification: T-015

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | First message of a chat is no slower than the second | **PASS** | `agent_manager.create(open=False)` sends nothing; `TestOpeningWithNoMessage` asserts `sess.sent == []`. The `"Hello."` turn is gone. |
| 2 | Median conversational turn under 2s on a hosted talk model | **BLOCKED — needs `OPENROUTER_API_KEY`** | See *Not verified* below. The measurement path itself is in place (AC 9). |
| 3 | `GET /api/assistant/settings` opens no sockets | **PASS** | `TestSettingsReadTouchesNoNetwork::test_no_probe_is_ever_initiated` fails the test if `_probe` is called at all. |
| 4 | Backend resolution does not pay for probes it does not need | **PASS — measured** | Cold probe cache, stored choice `claude`: **8ms**, asking about zero other candidates. The previous behaviour (`installed` for every row up front): **3092ms** on this same machine. |
| 5 | The chain states why it passed a candidate over, never falls silently | **PASS — live** | With the stored choice cleared, on this machine: ollama *"nothing is listening on 127.0.0.1:11434"*, lm-studio *"192.168.1.14:1234 did not answer within 1.5s"*, openrouter *"OPENROUTER_API_KEY is not set"*. Plus `TestTalkReadyPreflight` for reachable-but-toolless and reachable-but-empty. |
| 6 | The tray menu shows every available row, unavailable ones disabled with a reason | **PASS — live** | Win32 drive of the release build: **15 rows** at root (13 items + 2 separators) where T-002 last recorded 10. `Dictate`, `Saved prompts` and `Watch` render disabled carrying their `reason_unavailable`. Submenus read: Listening → Off / Short take / Hands-free; Clipboard → Copy last reply / Send clipboard…. Startup log: `tray: 18 rows — …` with 3 marked `(unavailable)`. |
| 7 | Every wired row acts; gated rows never act from the menu | **PASS (gated: PASS by construction)** | Drove `Clipboard ▸ Copy last reply` on the live menu; console audit recorded `assistant.say tray {'command': 'copy_last'} handled`. Drove `Quit`: process gone, sidecar port 8790 closed. The three gated rows are routed by *reading* `never_one_click` from the registry, so they open the window — pinned by `the_gated_capture_and_clipboard_rows_refuse_one_click` and the Python counterpart. |
| 8 | A tray click responds with the console stopped | **PASS** | `click.rs` reads through the 30s cache (`console_settings::all` + `str_at`) and `string_or` — the only cache-bypassing reader, and the tray's only caller — is deleted. With no console the loopback connect is refused immediately; the read falls back to `"listen"`. |
| 9 | The fast path is measurable | **PASS** | `ApiSession` stamps a real `duration_ms` (was a hardcoded `0`) plus a new `ttft_ms`, both threaded through `telemetry.FIELDS` and `agent_session`'s recorder. |
| 10 | No event sequence strands the overlay; ✕ / Esc / drag work | **PASS** | `ApprovalResolved` now hides (it mapped to `{}`); a lost stream clears a stale card (`a_stale_card_is_cleared_when_the_stream_is_lost`); a 120s watchdog re-armed per state change is the backstop. In-browser drive: ✕ → `dismiss`, Esc → `dismiss`, and `data-tauri-drag-region` present on both `#panel` and `#top`. |
| 11 | A card is answerable from the overlay | **PASS (wiring); live card drive NOT done** | Allow → `{"action":"allow"}`, Deny → `{"action":"deny"}`, Stop → `{"action":"stop"}` all emitted, verified in the browser. Key capture: `a_card_is_remembered_by_tool_and_key_then_forgotten`. Route: `TestAnsweringACardOnTheAssistantsOwnChat`. Not driven against a real gated tool call — see *Not verified*. |
| 12 | T-002 closed | **PASS** | See *T-002* below. |

## Test Results

```
pytest -o addopts="" -q          1200 passed, 1 warning in 92.56s
cargo test (msvc-env sourced)     160 passed; 0 failed
cargo build --release             Finished in 1m 51s, zero warnings
```

Baseline before this ticket: **1175 python / 148 Rust**. Net **+25 python, +12 Rust**, no
regressions. The single pytest warning is pre-existing and present in the baseline: a
`PermissionError` inside `test_tomlio`'s own concurrent-writer thread, a Windows
`os.replace` race in the test, not in `tomlio`.

**Build note, load-bearing:** `cargo` cannot compile here without
`. ./desktop/msvc-env.ps1` first — `cc-rs` fails on a missing `excpt.h`. And piping cargo
through PowerShell's `Select-Object` returns exit 1 on a *clean* build, because PS treats
cargo's stderr as an error; redirect to a file and read it. Both cost a false failure
before being understood.

## Edge Cases Probed

- **A flagless backend opened with no message.** The persona would have been silently
  lost — there is no first message to prepend it to. Parked on the session and consumed by
  `BaseSession.send`, the one path every caller goes through: the assistant feature calls
  `send` directly rather than via `agent_manager.send`, so fixing either caller alone
  would have left the other dropping it. Covered both ways.
- **The prefix must not reach the transcript.** `turn.start` carries `text` = what was
  typed and `wire` = what was sent, the same split a resolved `#file` token already makes.
- **A stored backend that no longer exists in `agents.toml`.** Falls through rather than
  raising `KeyError`.
- **A reachable local server with nothing loaded**, and **a resident model that cannot
  call tools** — both real failures from `console/.cache/agent-chats/`, both now *skips*
  with a reason instead of a selection that dies mid-turn.
- **A server that reports neither.** `None` means "cannot say", not "nothing loaded", and
  the tool flag is documented as a hint — so silence gets the benefit of the doubt rather
  than ruling out every runtime without a residency endpoint.
- **A keyed provider must not be interrogated.** `test_a_keyed_provider_is_not_interrogated`
  raises if `loaded`/`capabilities` are called, which is what keeps OpenRouter off two
  extra round trips per resolution.
- **`is_local` was the wrong predicate** and was caught before shipping: LM Studio at
  `192.168.1.14` is a box that swaps models one at a time, and `is_local` calls it hosted
  because the host is not `127.0.0.1` — so it would have skipped exactly the checks it
  needs. `auth == "none"` is the correct class.
- **An unknown `tray` placement, and a row with no id.** Hidden and skipped respectively,
  rather than guessed at: a typo in the registry should cost a missing row, not an item
  whose behaviour nobody chose.
- **A registry with no header / mute / hands-free row.** Every `TrayUi` field is
  `Option`; the hands-free polling thread is not started when there is no tick to keep
  honest, using `if let` rather than an early return — an early return would have cost the
  tray its backend header, which is a bug this nearly shipped.
- **Overlay layout at the real 380×104.** Two defects found *in the browser, not in
  review*: a fourth row overflowed the window, and giving the buttons the meter's row hid
  the level meter during listening — the one thing the panel exists to show. Re-measured
  after moving them into the top row: **0px overflow in all four states**, meter present,
  correct controls per state, correct in light and dark.
- **The registry fields were nearly decorative.** `never_one_click` and `risk` were
  declared, tested, and not deciding anything — the three gated ids were re-listed in the
  match instead. The release build's `dead_code` warning caught it. `never_one_click` is
  now *read* to route those rows, which is the difference between the registry being the
  source of truth and merely describing one.

## T-002

Closed inside this ticket. Its remaining work was a tray-skeleton menu that Thread 2
supersedes: T-002's own verification recorded 8 rows (10 after T-009), and the menu now
carries 15. Its one outstanding human step — row 8, "Interrupt current turn" against a
live turn — is **not** verified here and is carried forward as a todo rather than being
marked passed. Everything else in its checklist was re-confirmed by the live drive above
(menu contents, Mute, Show window, Quit).

Its `ticket-scripts/tray-menu-lib.ps1` is what made criteria 6 and 7 verifiable at all —
the tray is invisible to UI Automation, and that helper's `MN_GETHMENU` route reads and
clicks it exactly. It was written to be reused and it was.

## Not verified — stated plainly

1. **Criterion 2, the latency number.** Needs `OPENROUTER_API_KEY` in the workspace
   `.env`. That is the user's to set — this repo neither holds a key nor should. Until it
   is set, `openrouter` reports *"OPENROUTER_API_KEY is not set in this environment"* and
   the chain falls to `claude`, which is correct behaviour and also still slow. **The
   speed win is configured, not yet demonstrated.** Once the key is set, the numbers to
   read are `duration_ms` and `ttft_ms` in `knowledge-center/telemetry/2026-09.jsonl`,
   which AC 9 put there.
2. **Criterion 11 against a real card.** The emit path, the key capture and the route are
   each tested, but no live gated tool call was driven end to end through the overlay's
   Allow button. It needs a chat that calls a gated tool while the shell is running.
3. **T-002 row 8**, as above.
4. **macOS and Linux.** Only Windows was built and driven here. The overlay's
   transparency is already per-platform in `hud.rs`, and CI builds all three — but the
   generated menu has not run on libappindicator, where the registry's own note says a
   left-click never reaches the app and the `Listening ▸ Short take` row is the only form
   the click-to-talk gesture has.

## Notes

The single most useful number in this ticket: **8ms against 3092ms** for backend
resolution on a cold probe cache. The 3-second figure was a guess written into a comment
in `console_settings.rs` ("stalls for ~3 seconds roughly one request in fifteen") by
whoever added the client-side cache to work around it. It was the settings endpoint asking
a switched-off LAN box whether it was there, twice, on the path a tray click took.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
