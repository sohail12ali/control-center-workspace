---
ticket: "T-015"
artifact: plan
---

# Plan: T-015

## Approach

Three independent threads, ordered by value per unit of diff. Thread 1 is pure Python and
delivers the daily-felt win; Thread 2 and 3 are Rust plus one static page.

Nothing here builds a new agent loop, a new transport, or a new settings store. Every piece
reuses something already shipped and tested — the work is wiring, defaults, and removing I/O
from paths that must not block. Reuse list, canonical:

| Need | Reuse |
|------|-------|
| the fast agent loop | `console/server/agent_api_session.py` `ApiSession` |
| streaming + usage + cost | `console/server/openai_client.py` `Client.stream` |
| console verbs as tools | `console/server/agent_tools.py` `tool_definitions` |
| the approval gate | `console/server/agent_approvals.py` `REGISTRY.request` |
| "is a model loaded / tool-capable" | `console/server/model_catalog.py` `loaded` / `capabilities` |
| the tray-click decision table | `desktop/src-tauri/src/click.rs` `action` |
| cached settings reader | `desktop/src-tauri/src/console_settings.rs` `all` / `str_at` |
| per-machine provider config | `console/server/provider_overrides.py` |

## Slices

### Slice 1 — Latency (Python only)
The Assistant answers a conversational question in about a second, and it is measurable.

### Slice 2 — Tray truth (Rust)
The menu is generated from the one registry that already claims to be authoritative, and a
click never touches the network.

### Slice 3 — The overlay (Rust + `hud.html`)
It can always be dismissed, it can never stick, and it can answer a permission card in place.

## Tasks

### [x] T-015-01 — Start a chat without burning a turn (1 h)
- [x] `agent_manager.create(..., open=True)` — an `open=False` path starts the session and
      publishes `session.init` without calling `sess.send`
- [x] Defer the CLI-transport `system_append` wire-prefix (`create():110`) to the first real
      send, so a no-open session does not lose its persona
- [x] `assistant_feature._ensure_session` stops passing `"Hello."`
- **Done-criteria:** the first message of a new Assistant chat is the user's own, and its
  latency matches the second message's. A test asserts no `turn.start` is published between
  `create(open=False)` and the first `send`.
- **Basis:** `agent_manager.py:63,75,108-115`; `assistant_feature.py:239`
- **Depends on:** —

### [x] T-015-02 — Stop the settings endpoint probing the network (1 h)
- [x] `settings_get` returns settings without evaluating `Backend.installed` for every row
      (read the probe cache only; never initiate a probe)
- [x] Same for `assistant_config.resolve_backend`, which today probes every row before even
      checking the one that was requested
- [x] Availability stays available — on `GET /api/agents/backends`, which the Settings tab
      already polls and which is expected to be slow
- **Done-criteria:** `GET /api/assistant/settings` makes zero outbound sockets. A test with a
  provider pointed at a black-hole address asserts the endpoint returns without probing it.
- **Basis:** `assistant_feature.py` `settings_get`; `agent_backends.py:435` `installed`,
  `PROBE_TIMEOUT = 1.5`; `assistant_config.py:181`
- **Depends on:** —

### [x] T-015-03 — A backend chain with preflight, not a silent fall to `claude` (3 h)
- [x] Replace `LOCAL_FIRST` with a settings-driven ordered chain, defaulting to
      `("ollama", "lm-studio", "openrouter", "claude")` — moving `openrouter` ahead of
      `claude` is the actual default fix
- [x] Add a `usable_for_talk` preflight per candidate over `model_catalog.loaded` and
      `.capabilities`: reachable is not enough, it must have a loaded tool-capable model
- [x] A skipped candidate records a stated reason; the chosen backend and every skip reason
      are surfaced on `GET /api/assistant/settings`
- **Done-criteria:** with Ollama stopped and LM Studio pointed at a dead host, the Assistant
  lands on OpenRouter **and says why**, rather than silently choosing `claude`. Tests cover
  reachable-but-tool-less and reachable-but-nothing-loaded as *skips*, not selections.
- **Basis:** `assistant_config.py:42,173`; `model_catalog.py:299,343`
- **Depends on:** T-015-02

### [x] T-015-04 — Measure the fast path (1 h)
- [x] Real wall-clock `duration_ms` in `ApiSession._run_turn` (currently hardcoded `0`)
- [x] Time-to-first-token, since that is what decides whether it *feels* fast
- **Done-criteria:** an API-backed turn appears in `knowledge-center/telemetry/2026-09.jsonl`
  with a non-zero duration and a TTFT. Without this, Verify step 2 has nothing to read.
- **Basis:** `agent_api_session.py:276`
- **Depends on:** —

### [x] T-015-05 — Generate the tray from `features.toml` (4 h)
- [x] `toml` dependency, `include_str!("../../features.toml")`, parsed once in `tray::attach`
- [x] Honour the fields that exist and are ignored today: `tray`
      (`show`/`hide`/`submenu`/`header`), `parent`, `available`, `reason_unavailable`, `risk`,
      and the `hide_unavailable_pref` projection key
- [x] `available = false` renders **disabled with its `reason_unavailable`** (or hidden under
      `desktop.tray.hide_unavailable`) — never silently absent
- [x] `never_one_click = true` opens the window; it never performs the action
- [x] An id with no dispatch arm logs a warning at startup — the drift detector
- **Done-criteria:** the menu shows every `available = true`, `tray != "hide"` row — 16, not 8.
- **Basis:** `desktop/features.toml` (25 rows, 16 available); `tray.rs:113-165` (8 items)
- **Depends on:** —

### [x] T-015-06 — Wire the built-but-unreachable rows (3 h)
- [x] `clipboard_menu`, `clipboard_copy_last`, `clipboard_send`, `capture_this_turn`,
      `capture_region`, `listen_mode`, `listen_off`
- [x] The `risk = "gated"` ones (`clipboard_send`, both captures) route through the existing
      approval card, not straight through
- **Done-criteria:** every wired row performs its action, and each gated one raises a card.
- **Basis:** `clipboard.rs`, `capture.rs`, `ocr.rs`, `listen.rs`; `agent_approvals.LOCAL_ONLY`
- **Depends on:** T-015-05

### [x] T-015-07 — Never block the UI thread on a click (1 h)
- [x] Keep `tray_click_action` in `ShellState`, refreshed on a worker thread and invalidated by
      `console_settings::forget()`, so the click handler does zero I/O
- [x] Retire `string_or`, which bypasses the cache and has no other honest caller
- **Done-criteria:** with the console stopped entirely, a tray click responds instantly on its
  cached/default value. This is the frozen-menu regression.
- **Basis:** `click.rs:122-137`; `console_settings.rs:186-200` (`string_or` calls `fetch`)
- **Depends on:** T-015-02

### [x] T-015-08 — Make the overlay impossible to stick (3 h)
- [x] A visible ✕ and `Esc`, both invoking a new `hud::dismiss` command — the page gets no
      token and makes no console call, preserving the property `hud.rs`'s docstring argues for
- [x] `data-tauri-drag-region` on `#panel`, delivering the drag handle the page already claims
- [x] A watchdog ceiling in `hud.rs`: visible longer than N seconds with no state change → hide
- [x] `Event::ApprovalResolved` must `hide_soon`; `tray_link`'s reconnect path must clear a
      stale **approval**, not only a stale `Thinking`
- **Done-criteria:** kill the console mid-card and the panel clears rather than stranding. ✕,
  Esc and drag all work. No event sequence leaves it visible indefinitely.
- **Basis:** `hud.html` (no close control, no drag region); `hud.rs:63-74,161-177`;
  `tray_paint.rs:138`; `tray_link.rs:76-82`
- **Depends on:** —

### [x] T-015-09 — Make the overlay worth having on screen (3 h)
- [x] Map the existing `reply` event to `hud::text` — `assistant_reply` already publishes the
      trimmed spoken form and `tray_link::events_for` already drops it on the floor
- [x] Allow / Deny buttons on a permission card, invoking Tauri commands so the *shell* calls
      the console over loopback — the direction `console_settings::post` already goes.
      `agent_approvals.LOCAL_ONLY` stays desk-only
- [x] One Stop/Send button whose meaning follows state, reusing `click::action`'s table
- **Done-criteria:** the panel shows what was said, and a card can be answered without opening
  the main window.
- **Basis:** `assistant_reply.py:226`; `tray_link.rs:166-179`; `click.rs:50-86`
- **Depends on:** T-015-08

### [x] T-015-10 — Close T-002 (1 h)
- [x] `reconcile` + `close-work` on [[T-002-summary]], whose tray-skeleton scope Thread 2
      supersedes
- **Done-criteria:** T-002 lane is `done` and the artifact-map row moves to Completed.
- **Depends on:** T-015-06

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-015-01 — Start a chat without burning a turn | 1 h | one kwarg, one deferred prefix |
| T-015-02 — Stop the settings endpoint probing | 1 h | cache-only read path |
| T-015-03 — Backend chain with preflight | 3 h | new logic, but over existing catalog calls |
| T-015-04 — Measure the fast path | 1 h | two fields |
| T-015-05 — Generate the tray from features.toml | 4 h | new toml reader + menu builder in Rust |
| T-015-06 — Wire the unreachable rows | 3 h | 7 rows, 3 of them gated |
| T-015-07 — No blocking I/O on a click | 1 h | move a read to ShellState |
| T-015-08 — Overlay cannot stick | 3 h | new command + watchdog + 2 event fixes |
| T-015-09 — Overlay worth having | 3 h | 3 controls, one new loopback direction |
| T-015-10 — Close T-002 | 1 h | reconcile + close-work |
| **Total** | **21 h** | |

### Acceptance criterion coverage

Acceptance criteria are pinned in the approved plan's Verification section and restated in
[[T-015-verification]]. Mapping:

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| Median conversational turn under 2s | T-015-03, T-015-04 |
| First message of a chat no slower than the second | T-015-01 |
| `GET /api/assistant/settings` makes zero outbound sockets | T-015-02 |
| Chain lands on OpenRouter and states why, never silently on `claude` | T-015-03 |
| Menu shows 16 available rows, unavailable ones disabled with a reason | T-015-05 |
| Every wired row acts; gated rows raise a card | T-015-06 |
| A click responds with the console stopped | T-015-07 |
| No event sequence strands the overlay; ✕/Esc/drag work | T-015-08 |
| A card is answerable from the overlay | T-015-09 |
| T-002 closed | T-015-10 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
|------|-----------|--------|------------|-------|
| Rust cannot be compiled in a plain shell — `cc-rs` fails on a missing `excpt.h` | High | High | Source `. ./desktop/msvc-env.ps1` before every `cargo` invocation; it is already in the repo for this | Builder |
| OpenRouter needs a key this repo does not and must not hold | High | High | `OPENROUTER_API_KEY` is the user's to set in `.env`; the chain must degrade with a stated reason, not a stack trace, when it is absent | User |
| Slices 2/3 collide with 7 uncommitted Rust files already in flight | High | Med | Land that work first (see T-015-progress); do not begin Thread 2 on top of an unreviewed diff | Builder |
| A generated menu silently loses a row someone relied on | Med | Med | The startup drift warning plus the extended `test_features.py` correspondence check | Builder |
| Overlay buttons become a credential surface | Low | High | The page invokes Tauri commands only; the shell makes the loopback call. `LOCAL_ONLY` tools stay desk-only | Builder |
| A local model is chosen, then fails mid-turn on RAM | Med | Med | This is the observed failure the preflight exists to prevent; treat "reachable" as insufficient | Builder |

## Dependencies
- Blocks: [[T-002-summary]] (closed by T-015-10)
- Blocked by: — (T-015-03 needs `OPENROUTER_API_KEY` from the user to be *verified*, not to be *built*)

## Deltas from the approved plan

Recorded rather than silently rewritten. Three things the plan asserted turned out to be
wrong once the code was in front of me; each done-criterion above still reads as approved
so the change is visible.

1. **"16, not 8" menu rows (T-015-05) is wrong — it is 15.** 16 features are marked
   `available`, but `pause_listen_on_permission` is `tray = "hide"`: a behaviour, not
   something you click. The live drive found 15 rows, and `features.rs` pins that number.

2. **The gated rows do not "route through the approval card" (T-015-06).** They carry
   `never_one_click` in the registry, which means the tray must not act on them at all —
   so they open the window, where the destination and the gate are visible. That is
   stricter than the plan asked for and it is what the registry already said. It also made
   this task much smaller than its 3h estimate: no new gated actuation was written.

3. **`tray_click_action` did not need to live in `ShellState` (T-015-07).** The plan
   offered that as the better of two options. It was unnecessary once the settings endpoint
   stopped probing: the existing 30s cache is warmed by the startup thread that reads the
   mute state, so the click costs a lock. Deleting `string_or` — the only reader that
   bypassed the cache, and the tray's only caller — was the whole fix.

One thing the plan did not anticipate: `never_one_click` and `risk` were at first
re-stated in code rather than read from the registry, leaving both fields decorative. The
release build's `dead_code` warning caught it. `never_one_click` now decides the routing;
`risk` appears in the startup summary line, deliberately not as an invariant — see the
decision log.

## Links
- [[T-015-summary]] · [[T-015-analysis]] · [[T-015-requirements]] · [[T-015-decision-log]] · [[T-015-plan]] · [[T-015-progress]] · [[T-015-verification]]
