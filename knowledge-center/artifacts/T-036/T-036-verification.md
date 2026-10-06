---
ticket: "T-036"
artifact: verification
status: partial
---

# Verification: T-036

**State: plan by the builder (T-036-21); [PY] and [DOC] results filled by the verifier 2026-10-05 (§ Acceptance Criteria, § Test Results). Disposition `needs_human`: 49 of 81 ACs PASS, 1 PARTIAL (AC-62), 0 FAIL, 31 [BROWSER] ACs PENDING.** Every [BROWSER] row stays **NOT VERIFIED (browser): not verified in a browser**; the build pipeline and the verifier have no browser and CI has no Node. The [PY] rows below were filled from the verifier's own pytest runs. The build gates (task 22) are in [[T-036-progress]]; they are a gate on the tree, **not** a claim that the [BROWSER] criteria pass.

## Verification plan

### One-time relaunch (AC-64, NFR-11)
Pages open before this ticket ships have no version check. Before any [BROWSER] procedure: restart the console server (so `/api/prefs`, `ui_version`, `prefs_rev`, `workspace` exist), **quit the desktop app from the tray and relaunch it** (F5/Ctrl+R in the Tauri window is UNVERIFIED), hard-refresh every browser tab. Check: `GET /api/config` shows `ui_version`; Settings shows "Shared by the desktop app and every browser tab on this machine...". Same text in [[T-036-release]].

### Unverified assumptions (recorded, none checked)
A-6 WebView2 reports `document.hidden` for a Tauri-hidden window (AC-18) · A-7 `location.reload()` works in the Tauri webview and the Rust init script runs again (AC-22) · A-8 the live page heap was not probed · the 64 KiB `keepalive` budget (AC-71) is recalled, not verified · A-5 accepted risks (shared `voice`, pixel `layout`).

### Tools for the procedures (never committed)
- **AC-20 test server:** a throwaway Python script (session scratchpad, not in the repo) that serves `console/static` like the console but returns a new random `ui_version` on every `GET /api/config`; point the page at it. Do not commit it.
- **Force a version change on the real server:** `touch console/static/styles.css` (or edit a comment); the stamp includes size and mtime.
- **Observe requests:** browser DevTools Network, filter `/api/`.

### [PY] criteria (verifier runs; file named is where the tests live, by test names; confirm)
Command: `PYTHONUTF8=1 python -m pytest -o addopts="" <files> -q`.
- `console/tests/test_ui_version.py`: AC-2, 3, 4, 5, 6, 7, 67 (and AC-1)
- `console/tests/test_config_payload.py`: AC-1, 35, 57, 67 (BR-7)
- `console/tests/test_prefs_store.py`: AC-24..31, 44, 46..49, 75, 80
- `console/tests/test_prefs_routes.py`: AC-24, 25, 32, 33, 34, 36
- `console/tests/test_prefs_client_source.py`: AC-37, 38, 39, 53, 66, 74 (source regexps; AC-44 also)
- `console/tests/test_reload_source.py`: AC-8, 9, 17, 19, 69, 66
- `console/tests/test_prefs_wording.py`: AC-54, 55
- `console/tests/test_ui_constraints.py`: AC-61 (no `=>`, no statement-leading `let`/`const`); `console/requirements-dev.txt` unchanged
- `console/tests/test_stylesheet.py`, `console/tests/test_plugins.py`: AC-62, AC-33 (the one `test_stylesheet.py` failure at build time is `onboarding-wizard.js: .ob-count`, another pipeline's missing rule)
- `desktop/tests/test_sidecar.py`: AC-58, 59 (fake `http.server` on a loopback port)

### [BROWSER] criteria: 31, every one "not verified in a browser"
Run in (a) the Tauri desktop window and (b) Chrome/Edge on `http://127.0.0.1:8790` unless noted. After the one-time relaunch.

| # | AC | Procedure | Status |
|---|----|-----------|--------|
| 1 | AC-10 | Open the page, note the notice is absent. `touch console/static/styles.css`. Within one 15 s heartbeat the notice "A new version of the console is ready..." appears; keep the window untouched (no key, pointer, wheel) for 60 s while busy (e.g. type in a textarea first) and confirm the notice is still shown. | NOT VERIFIED (browser) |
| 2 | AC-11 | Run the page against a server without `ui_version` (a throwaway proxy that deletes the field, or the old server). Wait 2 heartbeats, 60 s idle: no notice, no reload. | NOT VERIFIED (browser) |
| 3 | AC-12 | With the notice shown and text typed in a composer, click **Reload now**: the page reloads at once. Before clicking, confirm the notice reads that unsaved text will be lost (busy wording). | NOT VERIFIED (browser) |
| 4 | AC-13 | Export the static site (`kanban.py export`), open `index.html` from `file://`. DevTools: no heartbeat request, no notice, no reload, `C.prefs.mode()` is `local`. | NOT VERIFIED (browser) |
| 5 | AC-14 | Idle and not busy for 30 s after a served file changes: the page reloads by itself and the new JS/CSS is in effect (change a visible CSS value to see it). | NOT VERIFIED (browser) |
| 6 | AC-15 | Repeat 5 once per blocker: typed text in the Assistant composer, in the Agents composer, in a Settings input; a drawer open; the setup wizard open; the command palette open; dictation active; read-aloud active; a registered hold (a half-typed todo). Each must keep the page from reloading while it holds, for > 60 s. | NOT VERIFIED (browser) |
| 7 | AC-16 | Type half a message in an Agents chat and half a todo; change a static file; confirm no reload. Send the message and clear the todo; the reload follows within one check. | NOT VERIFIED (browser) |
| 8 | AC-18 | Desktop app: hide the window with its close button (`main.rs:517-528`), change a file, wait one heartbeat; with nothing dirty it should reload without the 30 s wait. Record which of the two outcomes is observed: reloaded without waiting (A-6 true), or WebView2 did not report hidden and the idle rule reloaded it (A-6 false, also a valid outcome). | NOT VERIFIED (browser) |
| 9 | AC-20 | Point the page at the AC-20 test server. Count reloads over 5 minutes: at most 3 automatic reloads, then notice and **Reload now** only with the "paused" wording; automatic reload resumes after the window slides; **Reload now** works while paused. | NOT VERIFIED (browser) |
| 10 | AC-21 | With files unchanged, stop and start the console server 5 times within 60 s. Zero reloads (a restart alone must not trigger one). | NOT VERIFIED (browser) |
| 11 | AC-22 | In the Tauri window repeat 5, 6 and 8, then after the reload check the window still has `in-shell` on `<html>`/`<body>` (A-7; if it does not, that is a defect to fix page-side before ship). | NOT VERIFIED (browser) |
| 12 | AC-23 | In the static export, confirm the version check, notice and any reload never run (no requests, no timers added). | NOT VERIFIED (browser) |
| 13 | AC-40 | Console: `var o = C.prefs.get("layout"); o.x = 1; C.prefs.get("layout")` has no `x` (a deep clone). | NOT VERIFIED (browser) |
| 14 | AC-41 | Set `theme=dark` on the server. Load a fresh tab (or relaunch the app). **Pass condition (CR-31, plan task 10):** the first render of the tab, once it is drawn, is already themed dark (`C.prefs.get("theme")`/`data-theme` correct at first tab render). A static-shell flash (the HTML shell painted before JS runs) is **recorded, not failed**. **Flagged for the owner:** AC-41's literal wording says "no default-theme flash"; this plan reads it per CR-31 (hydration before `applyTheme`, flash of the pre-JS shell is pre-existing), not as "no flash of any kind". | NOT VERIFIED (browser) |
| 15 | AC-42 | Wizard: type 40 characters quickly while watching Network: at most 3 `POST /api/prefs`; then change a pref and close the tab at once: the value is on the server (`GET /api/prefs`). | NOT VERIFIED (browser) |
| 16 | AC-43 | (a) Static export uses `localStorage["console.*"]`. (b) New JS against a server without `/api/prefs` (404): no console error, mode `local`. (c) Stop the server, load the page from cache/restart: renders from `localStorage`/defaults; start the server: server prefs are picked up. | NOT VERIFIED (browser) |
| 17 | AC-45 | In one client `C.prefs.set("layout", {a: 1})`; reload that client: `layout` survives; reload the other client: it shows `layout` too. | NOT VERIFIED (browser) |
| 18 | AC-50 | Browser with `theme=dark` in `localStorage` and an app with none: open both (either first). Whoever loads first imports; the second never overwrites; both end on dark; the local `console.*` keys are gone after the acknowledgement; a conflict toasts the key and the browser's value. | NOT VERIFIED (browser) |
| 19 | AC-51 | Reset in the app (Settings), then load a stale browser that still has `console.*` keys: it deletes them without importing, shows defaults and the closed-window info toast. | NOT VERIFIED (browser) |
| 20 | AC-52 | Change the theme in a browser; the app follows within one heartbeat with no reload and no re-render of the active tab (type in a field on that tab to see it stay). Same for `hiddenTabs`. With unflushed local changes, the refresh is blocked until flushed. | NOT VERIFIED (browser) |
| 21 | AC-56 | Settings -> Saved preferences: server-mode sentence and (with `/api/prefs` blocked) the local-mode sentence read as specified; Reset asks for confirmation, Cancel changes nothing, OK clears; both clients show defaults after their next heartbeat or reload; the key list shows server keys and values. | NOT VERIFIED (browser) |
| 22 | AC-68 | Start with an old/un-restarted server (no `ui_version`, no `/api/prefs`); load the page (local mode). Restart the server with the new code: the page shows the notice and reloads when idle, then runs in server mode. | NOT VERIFIED (browser) |
| 23 | AC-70 | Open Settings, touch nothing: it reloads after the idle window. Repeat typing in a Settings input: the reload is blocked. | NOT VERIFIED (browser) |
| 24 | AC-71 | Change one key and close the tab: on the server. Then set a delta larger than 60,000 bytes across keys: it goes one key per request, no exception (watch Network). The 64 KiB keepalive budget itself is unverified. | NOT VERIFIED (browser) |
| 25 | AC-72 | Stop the server; `C.prefs.set("theme","dark")` stays in memory; start the server: it is sent. A value > 32 KB is refused locally with one toast and never queued. | NOT VERIFIED (browser) |
| 26 | AC-73 | Delay `/api/prefs` by 10 s (a proxy or DevTools throttle): first paint within 4 s from `localStorage`/defaults; the late result applies through live pickup. | NOT VERIFIED (browser) |
| 27 | AC-76 | Seed `localStorage` with a conflicting key, an over-32 KB value, and an unparsable value; reload after Reset and before: the skipped, rejected and closed toasts read as specified; the unparsable value vanishes with no toast. | NOT VERIFIED (browser) |
| 28 | AC-77 | Pick up `hiddenTabs` changes five times: one `ArrowRight` on `#tabs` moves exactly one tab (one `keydown` handler); an equal pickup does not rebuild; a tab newly hidden while shown stays displayed. | NOT VERIFIED (browser) |
| 29 | AC-78 | Put text into a textarea without typing (dictation, or the `/ @ #` picker, or `ta.value = "x"` in the console): the reload is blocked until the text is sent or cleared. | NOT VERIFIED (browser) |
| 30 | AC-79 | Two clients each change a different key inside one heartbeat: after one more heartbeat both clients show both changes. | NOT VERIFIED (browser) |
| 31 | AC-81 | Change a key then confirm Reset within 250 ms: the server is empty afterwards. During the migration import, a `set` made meanwhile is still present afterwards. | NOT VERIFIED (browser) |

**T-037 docked-drawer interaction (extra observation, tied to AC-15/AC-22):** the busy rule blocks the reload while an element with class `.drawer` exists (decision D-24, drawer by DOM). T-037 may dock the drawer so it stays open. With the dock open and nothing else dirty, change a file and observe: expected is that the automatic reload is blocked for as long as the dock keeps a `.drawer` element, with the notice and **Reload now** still available. Record whether the dock keeps the page from ever reloading automatically; if so that is a finding for the owner (T-037), not a pass.

### [DOC] criteria (the verifier reads artifacts, not code)

| AC | Procedure | Builder's record (verifier re-checks) |
|----|-----------|----------------------------------------|
| AC-60 | Confirm no plan task and no file in the ticket's changed-files list is under `desktop/src-tauri/` (the working-tree diff is not evidence: T-031 edits Rust concurrently). Use the per-task progress entries. | see [[T-036-progress]] task 22 |
| AC-63 | For `app.js`, `settings.js`, `index.html`, `styles.css`, `shell_feature.py`, `audit.py`: `git diff --no-index console/.cache/t036-prebuild/<name>.orig <file>` and `git diff -U0 -- <file>`; every foreign hunk in `<name>.diff` is present, byte-identical, or attributed through `<name>.pre-<NN>`. | see [[T-036-progress]] task 22 |
| AC-64 | This file and [[T-036-release]] state the one-time relaunch/hard-refresh step and how to check it (quit from the tray, relaunch). | present in both (§ One-time relaunch above; release § First deploy) |
| AC-65 | Mean of 200 `UiVersion.value()` calls on the real `console/static`, beside the 0.144 ms baseline; the NFR-4 ceiling is reported, not asserted. | recorded in [[T-036-release]] § Measured numbers and [[T-036-progress]] task 22 |

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | `/api/config` has `ui_version`, 12 lowercase hex, old keys keep shape | PASS | `console/tests/test_ui_version.py:46,50`; `console/tests/test_config_payload.py:99,103,117,123,130,137` |
| AC-2 | two calls, no change, same value | PASS | `console/tests/test_ui_version.py:55` |
| AC-3 | size, mtime-only, add/remove each move the stamp | PASS (mutation-checked) | `console/tests/test_ui_version.py:60` (parametrised), `:77`; mutation M2 below fails `:60[mtime]` and `:77` |
| AC-4 | non-matching file never moves it | PASS | `console/tests/test_ui_version.py:87,101` |
| AC-5 | manifest half follows tabs/routes, computed once | PASS | `console/tests/test_ui_version.py:109,122,131,135,149`; `console/tests/test_config_payload.py:144` |
| AC-6 | `compute()` opens no file | PASS | `console/tests/test_ui_version.py:157,166` |
| AC-7 | stamp file set equals the export copy set, export has no `ui_version` | PASS | `console/tests/test_ui_version.py:173,182,186` |
| AC-67 | vanishing file / unlistable dir tolerated | PASS | `console/tests/test_ui_version.py:194,209,226,233,239`; `console/tests/test_config_payload.py:170,177` |
| AC-8 | `app.js` reads `ui_version` from boot and heartbeat | PASS (source text only) | `console/tests/test_reload_source.py:237` |
| AC-9 | comparison wired to `onConnection` and `visibilitychange`, skipped when static | PASS (source text only) | `console/tests/test_reload_source.py:258` |
| AC-69 | notice has `Reload now`, `role: "status"`, no toast, new class in CSS | PASS (source text only) | `console/tests/test_reload_source.py:301,317,330`; `.ui-notice` is defined once in `styles.css` (`grep -c` = 1) |
| AC-17 | `holdReload` defined once in `core.js`, called from `agents.js` and `todos.js`, `core.js` loads first | PASS (source text only) | `console/tests/test_reload_source.py:152,180,198`; `console/static/core.js:36`, `console/static/agents.js:53`, `console/static/todos.js:26` |
| AC-19 | guard keeps timestamps in `sessionStorage["console-reload"]`, 3 in 5 min, no target stamp | PASS (source text only; mutation-checked) | `console/tests/test_reload_source.py:488,498,506,517`; mutation M4 below fails `:488` |
| AC-24 | no file gives `{prefs:{}, rev:0, import_open:true}` | PASS | `console/tests/test_prefs_store.py:40`; `console/tests/test_prefs_routes.py:102`; observed on the probe server |
| AC-25 | set/del returns `{rev, prev}`; equal set leaves rev == prev | PASS | `console/tests/test_prefs_store.py:68,78,85`; `console/tests/test_prefs_routes.py:106`; probe: `(201, {'rev': 1, 'prev': 0})` then `{'rev': 1, 'prev': 1}` |
| AC-26 | key regexp | PASS | `console/tests/test_prefs_store.py:97,102,111`; probe: `1x` gives 400 |
| AC-27 | 32768 ok, 32769 refused, 129th key, 256 KB, NaN, non-object set, non-list del | PASS (mutation-checked) | `console/tests/test_prefs_store.py:116,124,130,140,151,160,165`; probe: 32768-byte value 201, 32769 400; mutation M1 fails `:116` |
| AC-28 | one bad key writes neither | PASS | `console/tests/test_prefs_store.py:169` |
| AC-29 | missing/corrupt file reads empty, next write replaces | PASS | `console/tests/test_prefs_store.py:59` |
| AC-30 | concurrent writers keep all keys, valid JSON, via `tomlio._replace` | PASS | `console/tests/test_prefs_store.py:183,204`; probe: 8 concurrent POSTs all 201, revs 3..10, keys k0..k7 present, file valid JSON |
| AC-31 | store under `console/.cache/`, ignored by git | PASS | `console/tests/test_prefs_store.py:219,230`; `.gitignore:66` has `console/.cache/` |
| AC-32 | `prefs.reset`/`prefs.import` audited by names and counts; routine set not | PASS | `console/tests/test_prefs_routes.py:283,294,315,322,340` |
| AC-33 | shipped `plugins.toml` row, `PLUGIN`, four routes, no tab; `test_plugins` green | PASS | `console/tests/test_prefs_routes.py:141,155,161`; `test_plugins.py` alone: `22 passed in 0.47s` |
| AC-34 | POST without header 403, with it 201 | PASS | `console/tests/test_prefs_routes.py:232,244`; probe: `(403, {'error': 'missing X-Console-Request header'})`, valid POST 201 |
| AC-35 | `prefs_rev` in config when the plugin is loaded, absent when disabled | PASS | `console/tests/test_config_payload.py:152,162`; probe: `prefs_rev` 0 then 1 |
| AC-36 | only store, plugin and `shell_feature` read prefs | PASS (source text only) | `console/tests/test_prefs_routes.py:175` |
| AC-37 | `C.prefs` keeps get/set/del, adds hydrate/refresh/all/keys/reset/mode/rev | PASS (source text only) | `console/tests/test_prefs_client_source.py:40,48,56` |
| AC-38 | boot is `Promise.all([C.get("/api/config"), C.prefs.hydrate()])`, `applyTheme` in its `.then` | PASS (source text only) | `console/tests/test_prefs_client_source.py:363`; `console/static/app.js:670-678` |
| AC-39 | page-hide flush uses `fetch` + `keepalive` + CSRF header; no `sendBeacon` | PASS (source text only) | `console/tests/test_prefs_client_source.py:158,168` |
| AC-44 | 32 KB `layout` stored, returned, deletable | PASS | `console/tests/test_prefs_store.py:237`; `console/tests/test_prefs_client_source.py:76` (source) |
| AC-46 | empty server: all valid keys imported; repeat is a no-op | PASS | `console/tests/test_prefs_store.py:251` |
| AC-47 | server value wins, new key imported | PASS | `console/tests/test_prefs_store.py:263,273`; probe: `imported ['voice'], skipped ['theme']`, theme stayed `dark` |
| AC-48 | after reset import is closed and stores nothing | PASS | `console/tests/test_prefs_store.py:282`; probe: after reset `import_open: false`, import returns `closed: true`, `imported: []` |
| AC-49 | reset empties, bumps rev, closes window, audited | PASS | `console/tests/test_prefs_store.py:361,369`; `console/tests/test_prefs_routes.py:322`; probe: rev 11 to 12 |
| AC-53 | heartbeat compares `prefs_rev` with `!==`; own rev adopted only under a `prev` check | PASS (source text only; the adoption rule also executed in a Node harness, `core.js` with stubs: `rev()` 5 to 6) | `console/tests/test_prefs_client_source.py:343,377` |
| AC-54 | Settings, About, README, plugins.toml, registry wording | PASS (source text only) | `console/tests/test_prefs_wording.py:53,63,69,90,98,157,165,178,190,228,252,257,274` |
| AC-55 | `settings.js` has no `localStorage`; uses `C.prefs.all()`/`reset()` | PASS (source text only) | `console/tests/test_prefs_wording.py:77,83,152,202`; `grep localStorage console/static/settings.js` empty |
| AC-57 | `workspace` 12 hex, constant per root, different per root, no path | PASS | `console/tests/test_config_payload.py:198,205,213,220`; probe: `'5c94074c11ef'` |
| AC-58 | differing workspace refused, equal/absent attaches, `is_up`/`probe` unchanged | PASS (mutation-checked) | `desktop/tests/test_sidecar.py:288,297,303,309,314,324`; mutation M3 below fails 4 tests |
| AC-59 | duplicated hash equals the server's; sidecar imports nothing from `console/` | PASS | `desktop/tests/test_sidecar.py:335,344` |
| AC-61 | no `=>`, no statement-leading `let`/`const`, no manifest, dev requirements unchanged | PASS | `console/tests/test_ui_constraints.py:45,54,64,75,82` |
| AC-62 | `test_stylesheet.py` and `test_plugins.py` pass | PARTIAL: `test_plugins.py` green; `test_stylesheet.py` red only for the foreign `.ob-count` | `test_stylesheet.py` alone: `1 failed, 2 passed`; failure text is `onboarding-wizard.js: .ob-count` only (an untracked onboarding file, also red at the task-00 baseline); `.ui-notice` is not in the text. This ticket adds no failure, but the literal AC ("pass") is not met while the foreign rule is missing |
| AC-66 | no new timer or request for the version check; `GET /api/prefs` only from `hydrate()`/`refresh()` | PASS (source text only) | `console/tests/test_prefs_client_source.py:131,202,391`; `console/tests/test_reload_source.py:351,470` |
| AC-74 | hydration bound, retry triggers, mirrored regexp and 32 KB cap in `core.js` | PASS (source text only) | `console/tests/test_prefs_client_source.py:60,68,106,179`; bound also executed in the Node harness: never-answering `/api/prefs` resolves `local` at 3001 ms |
| AC-75 | import: valid kept, others rejected with reasons, overflow rejects overflow keys | PASS | `console/tests/test_prefs_store.py:291,304,309,318`; probe: `rejected: [{'key': '1x', 'reason': ...}]` |
| AC-80 | two interleaved imports end in one state, rev bumped once | PASS | `console/tests/test_prefs_store.py:333`; probe: second identical import left rev 2 |
| AC-10 | notice within one heartbeat, still shown after 60 s | NOT VERIFIED (browser) | procedure 1 |
| AC-11 | no `ui_version` server: no notice, no reload | NOT VERIFIED (browser) | procedure 2 |
| AC-12 | Reload now reloads at once, busy wording | NOT VERIFIED (browser) | procedure 3 |
| AC-13 | static export inert | NOT VERIFIED (browser) | procedure 4 |
| AC-14 | idle and not busy reloads | NOT VERIFIED (browser) | procedure 5 |
| AC-15 | each blocker blocks | NOT VERIFIED (browser) | procedure 6 |
| AC-16 | drafts survive, reload after cleared | NOT VERIFIED (browser) | procedure 7 |
| AC-18 | hidden Tauri window reloads (A-6) | NOT VERIFIED (browser) | procedure 8 |
| AC-20 | loop guard, 3 in 5 minutes | NOT VERIFIED (browser) | procedure 9 |
| AC-21 | 5 server restarts, zero reloads | NOT VERIFIED (browser) | procedure 10 |
| AC-22 | Tauri webview (A-7) | NOT VERIFIED (browser) | procedure 11 |
| AC-23 | static export, none of this runs | NOT VERIFIED (browser) | procedure 12 |
| AC-40 | `get` deep clone | NOT VERIFIED (browser) | procedure 13 |
| AC-41 | first tab render themed (CR-31 reading) | NOT VERIFIED (browser) | procedure 14 |
| AC-42 | 40 keystrokes, at most 3 POSTs | NOT VERIFIED (browser) | procedure 15 |
| AC-43 | local mode and unreachable server | NOT VERIFIED (browser) | procedure 16 |
| AC-45 | `layout` survives and shows in the other client | NOT VERIFIED (browser) | procedure 17 |
| AC-50 | first import wins, conflict toasts | NOT VERIFIED (browser) | procedure 18 |
| AC-51 | stale browser after Reset | NOT VERIFIED (browser) | procedure 19 |
| AC-52 | live pickup of theme and hiddenTabs | NOT VERIFIED (browser) | procedure 20 |
| AC-56 | Settings panel and Reset | NOT VERIFIED (browser) | procedure 21 |
| AC-68 | un-restarted server then restart | NOT VERIFIED (browser) | procedure 22 |
| AC-70 | Settings idle reload / typing blocks | NOT VERIFIED (browser) | procedure 23 |
| AC-71 | flush on hide, large delta | NOT VERIFIED (browser) | procedure 24 |
| AC-72 | server down, queued write | NOT VERIFIED (browser) | procedure 25 |
| AC-73 | hydration delayed 10 s | NOT VERIFIED (browser) | procedure 26 |
| AC-76 | toast wording | NOT VERIFIED (browser) | procedure 27 |
| AC-77 | one keydown handler after pickups | NOT VERIFIED (browser) | procedure 28 |
| AC-78 | text without typing blocks | NOT VERIFIED (browser) | procedure 29 |
| AC-79 | two clients, different keys | NOT VERIFIED (browser) | procedure 30 |
| AC-81 | change then Reset; set during import | NOT VERIFIED (browser) | procedure 31 |
| AC-60 | no `desktop/src-tauri/` file changed by this ticket | PASS (DOC; read from artifacts, not the tree) | plan names no `src-tauri` file as a task output (`T-036-plan.md:54` lists T-031's Rust files as do-not-touch, `:295` "no Rust change"); [[T-036-progress]] task 19/20/22 changed-file lists name only `desktop/sidecar.py` and `desktop/tests/test_sidecar.py` under `desktop/`. The working tree does show nine modified `.rs` files, which belong to T-031 and are not evidence either way |
| AC-63 | foreign hunks unchanged | PASS (DOC; line-level, not a hunk-level diff) | script (session scratchpad, not committed) took every `+` line of `console/.cache/t036-prebuild/{app.js,settings.js,index.html,styles.css,shell_feature.py,audit.py}.diff` and counted it in the live file: **0 missing** in all six (`app.js` 13, `settings.js` 90, `index.html` 2, `styles.css` 80, `shell_feature.py` 5, `audit.py` 3 added lines). Lines of the task-00 `.orig` that are gone now are accounted for: `app.js` 28 are T-037's drawer/dock rewrite (`console/static/app.js:17-132`), `settings.js` 61 are this ticket's wording and Saved-preferences edits (`.pre-11`, `.pre-12`) plus T-031 reworking its own voice/assets rows after `.pre-12` (`loadAssets`, `speak_voice` etc. still present, reformatted: `console/static/settings.js:1175,1214`), `styles.css` 1 is `flex: 1 1 auto; min-height: 0;` now followed by `position: relative;` (T-037). Limit: line-level counts cannot prove a foreign owner's later edit is not also this ticket's; attribution rests on the `.pre-NN` copies and the builder's per-task entries |
| AC-64 | relaunch step present in both artifacts | PASS (DOC) | this file § One-time relaunch (line 13) and [[T-036-release]] § First deploy (steps 1-3 plus "How to check it took"): quit from the tray, relaunch, hard-refresh tabs, `GET /api/config` shows `ui_version` |
| AC-65 | `ui_version` timing recorded | PASS (DOC; re-timed) | `UiVersion(STATIC_DIR, ...).value()` mean of 200 calls, three runs on the real `console/static` (30 files): **1.032, 1.037, 1.002 ms** (min 0.77 ms); builder recorded 1.31 ms, baseline 0.144 ms for 29 files; the 2 ms NFR-4 figure is reported, not asserted. Cause of the 7x gap to the baseline is not established (load, or the earlier method) |

31 [BROWSER] rows: AC-10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 40, 41, 42, 43, 45, 50, 51, 52, 56, 68, 70, 71, 72, 73, 76, 77, 78, 79, 81. None is passed.

## Test Results

**Verifier run, 2026-10-05, independent of the builder's numbers. What ran: pytest (Python 3.14.x, Windows), `node --check`, a throwaway HTTP server and a Node harness around the real `core.js`. What did NOT run: no browser, no Tauri/WebView2 window, no Python 3.11 (CI runs it), no JS test runner in CI.** Static-only checks verify code, not the feature.

| Scope | Command | Result |
|-------|---------|--------|
| unit + integration, nine ticket files | `PYTHONUTF8=1 python -m pytest -o addopts="" console/tests/test_ui_version.py console/tests/test_config_payload.py console/tests/test_prefs_client_source.py console/tests/test_ui_constraints.py console/tests/test_prefs_store.py console/tests/test_prefs_routes.py console/tests/test_prefs_wording.py console/tests/test_reload_source.py desktop/tests/test_sidecar.py -q -p no:cacheprovider` | `261 passed in 73.09s (0:01:13)` |
| plugins | same flags, `console/tests/test_plugins.py` | `22 passed in 0.47s` |
| stylesheet | same flags, `console/tests/test_stylesheet.py` | `1 failed, 2 passed`; failing id `test_every_class_the_js_styles_actually_exists`, text `onboarding-wizard.js: .ob-count` only (foreign, also red at task-00); `.ui-notice` not in the text |
| full suite, once | `PYTHONUTF8=1 python -m pytest -o addopts="" -q -p no:cacheprovider` | `1 failed, 2865 passed, 1 skipped in 419.95s (0:06:59)`; the one failure is the foreign `.ob-count` test above; no `test_run_watchdog.py` failure this run, so no flake to separate |
| syntax | `node --check` on `core.js app.js settings.js about.js agents.js todos.js` (Node v24.11.0) | all six exit 0 (syntax only, not a CI check) |
| mutation resistance, scratch copy `%TEMP%\t036-mut`, repo tree untouched | M1 `MAX_VALUE_BYTES` 32768 to 32769 in `prefs_store.py`; M2 mtime dropped from the stamp in `ui_version.py`; M3 `theirs != mine` flipped to `==` in `sidecar.py`; M4 `RELOAD_LIMIT` 3 to 4 in `app.js` | M1: 2 failed (`test_ac27_value_size_boundary_is_32768_bytes`, `test_ac75_...`); M2: 2 failed (`test_ac3_...[mtime]`, `test_ac3_mtime_only_change_keeps_size`); M3: 4 failed (`test_different_workspace_is_refused_with_both_ids` and 3 more); M4: 1 failed (`test_ac19_the_guard_counts_three_in_five_minutes_in_session_storage`); restored copy `152 passed` |
| JS logic, not a browser | Node harness loading the real `core.js` in a `vm` context with stubbed `window`/`document`/`fetch`/`localStorage` (scratchpad, not committed) | hydrate gives server mode and reads `theme`; 3 sets inside 250 ms make 1 POST `{"set":{"a":2,"b":3}}` and `rev()` 5 to 6; a never-answering `GET /api/prefs` resolves `local` after 3001 ms and later sets land in `localStorage`; a never-answering POST stalls later writes and `refresh()` (CR-38) until `pagehide` re-sends |

**`verify cases` decision:** no separate `T-036-test-cases.md` was created: the AC to test map above already carries the AC, test and line, and a second file would duplicate it (CANONICAL gate).

**Counts.** [PY] 46 ACs: **45 PASS** (of which 15 are "source text only": they prove the string exists in the file, not the behaviour; AC-8, 9, 17, 19, 36, 37, 38, 39, 53, 54, 55, 66, 69, 74 and AC-61's scan, with AC-44's client half also source text) and **1 PARTIAL** (AC-62, red only for the foreign `.ob-count`). [DOC] 4 ACs: **4 PASS** (AC-60, 63, 64, 65). [BROWSER] 31 ACs: **0 PASS, 31 not verified in a browser**. Total 81: 49 PASS, 1 PARTIAL, 0 FAIL, 31 PENDING (browser). A source-regexp test existing for a [BROWSER] AC proves only that the surface exists.

## Edge Cases Probed
None probed in a browser. Server-side probes run by the verifier against a **scratch workspace** (`%TEMP%\t036-probe-ws`: a copy of `console/` with an empty `knowledge-center/`, served by `python console/kanban.py serve --port 18797`; no write reached the real `console/.cache/`):

| Probe | Observed |
|-------|----------|
| `GET /api/config` | `ui_version` `c95ad98c934e` (12 hex), `prefs_rev` 0, `workspace` `5c94074c11ef`; keys `title, subtitle, tabs, boards, stale_days, workspace, ui_version, prefs_rev` |
| `GET /api/prefs` (empty) | `200 {'prefs': {}, 'rev': 0, 'import_open': True}` |
| POST without `X-Console-Request` | `403 {'error': 'missing X-Console-Request header'}` |
| POST valid delta | `201 {'rev': 1, 'prev': 0}`; same value again `201 {'rev': 1, 'prev': 1}` |
| malformed JSON `{not json` | `400 {'error': 'invalid JSON body'}` |
| JSON array body, `set` as a list, `del` as a string, key `1x`, literal `NaN` | all `400` with a sentence |
| empty body | `201`, a no-op (`rev` unchanged) |
| 32768-byte value / 32769-byte value | `201` / `400 ... 32769 bytes and the limit is 32768` |
| 5 MB value (a 5,242,882-byte body) | read in full, `400`, 0.09 s, server stayed up, store unchanged (CR-42: no body cap exists, `httpd.py` not changed by this ticket) |
| 8 concurrent writers, distinct keys | all `201`, revs 3..10, keys `k0..k7` all present, `prefs.json` valid JSON |
| import: `theme` (conflict), `voice`, `1x`; repeat | `imported ['voice'], skipped ['theme'], rejected [1x + reason]`, theme stayed `dark`; repeat: `imported ['voice']`, rev unchanged |
| reset, then import, then set | reset `rev` 12 `closed: True`; `GET` `import_open: False`; import `closed: True, imported: []`; a later `set` is stored (rev 13), window stays closed |
| stamp stable | two calls equal; mtime of `styles.css` moved +5 s: `ui_version` changed on the next call (`c95ad98c934e` to `583568bfbc17`); a `.swp` file added: unchanged |
| truncated body (`Content-Length: 1000`, 7 bytes sent) | the handler thread waits until the client closes, then logs a traceback (client gone before the 400 could be sent); server stayed up (pre-existing `httpd.py` behaviour) |
| live server `127.0.0.1:8790` (older process), GET only | `GET /api/prefs` `404 {"error": "no route for GET /api/prefs"}`; `/api/config` keys `title, subtitle, tabs, boards, stale_days`, no `ui_version`, `prefs_rev` or `workspace`. That is the server a new page would meet before a restart: it stays in local mode (browser behaviour not observed) |

Cleanup: the probe server (PID 22888) was stopped; nothing listens on port 18797; `console/.cache/prefs.json` does **not** exist in the real checkout (`ls: cannot access`).

## Notes
- **Disposition: `needs_human`.** No [PY] or [DOC] criterion FAILS (AC-62 is PARTIAL for a foreign reason). The 31 [BROWSER] criteria cannot be verified without a browser, so the ticket is not `ready_to_close`. `close-check` answers not ok (PENDING/NOT VERIFIED rows are non-pass) as expected. No `review-round` was recorded; `close-work` was not run; the lane stays `verify`.
- AC-41: **the frozen text and the plan's reading differ** (CR-41 in [[T-036-critique-report]]). Frozen AC-41: "paints dark with no default-theme flash". Plan task 10 and CR-31: "first tab render is already themed; a static-shell flash is recorded, not failed". Needs the owner (`evolve` the AC wording, or accept the plan's reading) or a browser observation. Procedure 14 above uses the plan's reading.
- Implementation critique: [[T-036-critique-report]] § Implementation critique, CR-38..CR-46: 0 critical, 1 major (CR-38, a hung POST stalls write-through and live pickup; not data-losing), 8 minor.
- Open questions still at their defaults: Q1 live pickup, Q2 sidecar check (included, Python only), Q3 30 s idle, Q4 delete local keys after import, Q5 all 16 keys shared. The optional sidecar check is built and tested over fake HTTP servers plus one live spawn (`desktop/tests/test_sidecar.py:350`); not exercised against the real desktop app.
- Unverified assumptions (none checked): A-6 WebView2 reports `document.hidden` for a Tauri-hidden window (AC-18); A-7 `location.reload()` re-runs the Rust init script so `in-shell` survives (AC-22); A-8 the live page heap was not probed; the 64 KiB `keepalive` budget (AC-71) is recalled; a queued pref write relies on `pagehide` at reload time (CR-45); Python 3.11 not run (CI matrix).
- Known accepted risks: all 16 keys shared (voice, pixel layout); a write made while the server is down is lost if the page reloads first (AC-72); no automatic reload when `sessionStorage` is blocked; two clients editing one object-valued key are last-writer-wins as a whole; the HUD overlay has no heartbeat; macOS/Linux webviews not verified; Reset clears every `console.*` localStorage key (CR-39).
- Traceability drift for the fixer (report only, nothing edited): the cross-links in the ticket's artifacts are incomplete and one-directional in places, e.g. [[T-036-task-breakdown]] and [[T-036-effort-estimate]] do not link back to [[T-036-verification]]/[[T-036-release]], and [[T-036-requirements]] lists [[T-036-context-snapshot]], [[T-036-iteration-log]] and [[T-036-plan-iteration-log]] without being listed by them (28 one-way pairs by a script over each `## Links` block; 0 broken wikilinks; 81/81 ACs of the requirements appear in this file, 51 by name before this fill and all by the per-AC rows plus the [BROWSER] table). [[T-036-release]] reads as verified in its "What shipped" bullets (CR-46).
- The 31 [BROWSER] criteria, A-6, A-7 and the keepalive budget are handed off to the parent session as "not verified in a browser". Suggested order, by risk: (1) AC-14/10/15/70/78 reload fires when idle and is blocked by each blocker, incl. the open `.drawer` dock (CR-40); (2) AC-22 and AC-18 in the Tauri window (A-6, A-7: `in-shell` survives the reload); (3) AC-41 first render themed (AC wording question, CR-41); (4) AC-50/51/81 migration and Reset ordering; (5) AC-52/79 live pickup between app and browser; (6) AC-20/21 loop guard and server restarts; (7) AC-43/68/73 older server, local fallback, slow hydrate; (8) AC-42/71/72 flush on hide and offline queue (and CR-38 hung POST); (9) the rest (AC-11, 12, 13, 16, 23, 40, 45, 56, 76, 77).

## Browser run by the parent session (2026-10-05, in-app browser, console on :8790 restarted onto this code)

Not the verifier's work: run afterwards by hand against the live server. **The Tauri/WebView2 window was NOT tested** (A-6, A-7 and every in-window row remain not verified).

- **PASS: version change reloads the page by itself.** `touch console/static/about.js` changed `ui_version` (`d5ef98797026` to `19076ccd5d9b`); within about a minute the page reloaded with no action (a `window.__marker` set before was gone; `sessionStorage["console-reload"]` holds the loop-guard stamp).
- **PASS: an unsent draft blocks the reload.** With text in the Assistant composer and a new version, the page did not reload; the notice "A new version of the console is ready. Unsaved text will be lost if you reload now; it reloads by itself when you are done." and a **Reload now** button appeared; the draft stayed intact.
- **PASS: shared store.** `/api/prefs` returns the layout dragged in this browser (`layout.agents.list`, `layout.vault.side`), and the value survives a reload. Reset layout removes it from the server.
- **Not exercised here:** migration with differing old values, the 5-restart loop guard, the older-server and slow-hydrate cases, flush on hide, and AC-41's default-theme flash (needs your wording call). The ticket stays `needs_human` for those and for the app window.

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]]
- [[T-036-context-snapshot]] · [[T-036-effort-estimate]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-plan-iteration-log]] · [[T-036-requirements-draft]]
