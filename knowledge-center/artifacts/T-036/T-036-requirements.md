---
ticket: "T-036"
artifact: requirements
status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 3
---

# Requirements: T-036 — App and browser in sync: UI version reload and server-side preferences

**Frozen:** 2026-10-05 · iteration 3 · source of truth for planning. Full wording, flows and rationale: [[T-036-requirements-draft]]; history: [[T-036-iteration-log]]; decisions: [[T-036-decision-log]] (ten GROUND entries plus D-11..D-21); findings: [[T-036-critique-report]] (CR-1..CR-25); gaps: [[T-036-gap-analysis]] (G1..G33). Post-freeze changes go through `evolve`.

## Intent

The user reported on 2026-10-05 "the app and the web app UI is out of sync" and decided: **auto-reload on a new UI version and shared preferences through the server** ([[T-036-summary]]). Cause (timeline-confirmed, heap not probed): the desktop app is a bare long-lived webview on the live server that never reloads, and the app and each browser keep separate `localStorage` ([[T-036-analysis]] §1, §3). Fix: a UI version the page checks on its heartbeat and a server-side preference store behind the unchanged `C.prefs` interface.

## Scope

**In:** S1 UI version stamp and reload only when safe · S2 server-side preferences (store, API, synchronous `C.prefs`, hydrate before first render, local fallback) · S3 one-time migration, Reset that reaches every client, live pickup of `theme`/`hiddenTabs` · S4 Settings wording and every statement that becomes false · S5 T-037 `layout` contract · S6 sidecar workspace identity (**SHOULD**, Python only, separable, "Phase 3") · S7 rollout (one manual relaunch for the first deploy).

**Out (explicit):** Rust shell changes · the HUD overlay `hud.html`/`flash.html` (own inline script, no heartbeat; stays as stale as the app did) · assistant/agent chat state (server-side, re-attaches by `seq`) · by-design app/browser differences (Assistant landing, window chrome, piper) · content-hash versions, reloading the HUD, consolidating the five hand-rolled tmp+replace JSON writers · detecting or restarting a server older than the current Python code.

**Assumptions (labelled, not verified):** A-1 idle 30 s (Q3) · A-2 live pickup wanted (Q1) · A-3 delete local copy after import (Q4) · A-4 sidecar check wanted as a SHOULD (Q2) · A-5 all 16 keys shared incl. `voice` and pixel `layout`; accepted risks: tray mute also mutes browser read-aloud, pixel layout shared across window sizes and devices, a write made while the server is down is lost on reload (Q5) · A-6 WebView2 reports `document.hidden` for a Tauri-hidden window (**unverified**) · A-7 `location.reload()` works in the Tauri webview and the Rust init script runs again (**unverified**) · A-8 the live page's JS heap was not probed.

**Verification tags:** **[PY]** pytest, no browser, no internet (route/validation tests and source-regexp checks of repo files; CI runs Python 3.11 and 3.13) · **[BROWSER]** needs a real browser and the Tauri webview; there is no JS runner and CI does not install Node, so the build pipeline **cannot** run these: they stay *not verified* until a person (or a driven browser) does them · **[DOC]** the verifier reads a ticket artifact or the plan.

## Functional Requirements

### Server: UI version
1. **FR-1 UI version stamp.** `GET /api/config` returns `ui_version` = first 12 hex of sha256 over (a) sorted `(name, size, mtime_ns)` of regular files in `console/static` matching `*.html *.js *.css *.png` (the set `export._copy_frontend` copies, `export.py:90`) and (b) a digest of `ctx.tabs()` + `ctx.router.describe()` computed once per process. Static half recomputed per call, no cache, stdlib only, stat only. A vanished file is skipped; an unlistable directory omits the field and `/api/config` still answers (it is the sidecar probe, `sidecar.py:23`). D-13.
   - [ ] AC-1 [PY] `/api/config` via `call()` (`test_ui_endpoints.py:69-75`) returns `ui_version` (12 lowercase hex); `title, subtitle, tabs, boards, stale_days` keep their shape.
   - [ ] AC-2 [PY] two calls with no change return the same value.
   - [ ] AC-3 [PY] changes when a matching file's size changes, when only its mtime changes, and when one is added or removed.
   - [ ] AC-4 [PY] does not change for a non-matching file (`*.swp`, `*.txt`) added, touched or removed.
   - [ ] AC-5 [PY] the manifest half changes when the tab set or route table changes and is computed once per process.
   - [ ] AC-6 [PY] `compute()` opens no static file (a test that makes `open` raise still passes).
   - [ ] AC-7 [PY] the stamp's file set equals what `export._copy_frontend` copies; the static export manifest has no `ui_version`.
   - [ ] AC-67 [PY] a file vanishing between listing and `stat` is skipped without an exception; an unlistable directory omits `ui_version` and `/api/config` still returns its other keys.

### Page: compare and notice
2. **FR-2 Record and compare.** The page records `ui_version` from its boot `/api/config` and compares on every heartbeat (15 s, `app.js:250,270-275`, payload no longer discarded), on offline-to-online (`C.onConnection`) and on `visibilitychange` to visible. Mismatch shows a persistent, non-modal, non-toast notice (`role="status"`: "A new version of the console is ready. It reloads when you pause.") with **Reload now**. Version rules (D-13): boot version absent and a later one present = changed; present then absent = ignored; both absent = nothing. **Reload now** reloads at once and, while busy, says unsaved text will be lost (D-20). Inactive when `C.IS_STATIC`.
   - [ ] AC-8 [PY] source: `app.js` reads `ui_version` from the boot and heartbeat results.
   - [ ] AC-9 [PY] source: comparison also wired to `C.onConnection` and `visibilitychange`, skipped when `C.IS_STATIC`.
   - [ ] AC-10 [BROWSER] after a served file changes the notice appears within one heartbeat and is still shown after 60 s with no interaction.
   - [ ] AC-11 [BROWSER] against a server that never has `ui_version`: no notice, no reload.
   - [ ] AC-12 [BROWSER] **Reload now** reloads at once, also with typed text; the notice then says unsaved text will be lost.
   - [ ] AC-13 [BROWSER] static export from `file://`: no heartbeat, notice or reload.
   - [ ] AC-68 [BROWSER] a page booted against a server without `ui_version` shows the notice and reloads when idle once the server restarts with the field, then runs in server mode.
   - [ ] AC-69 [PY] source: `app.js` has `Reload now` and `role: "status"`; any new hyphenated class used from JS exists in `styles.css`.

3. **FR-3 Reload only when idle and not busy.** `window.location.reload()` runs only when **idle** (30 s without `keydown`, `pointerdown`, `wheel`, `touchstart`) and **not busy**. Busy: a dirty field (a) any `textarea` with non-blank text, whatever put it there (dictation and the `/ @ #` picker assign `.value` without an `input` event, `agents.js:695-709,1349`, `composer-pick.js:187`; no Settings textarea exists), (b) a text-like `input`/`[contenteditable]` the user typed in (trusted `input` event recorded in a `WeakSet`) still in the DOM with non-blank text, (c) a focused non-blank field; **not** `value !== defaultValue` (Settings fills inputs with `.value =`, `settings.js:325,329,340,832,988`); the drawer open; the setup wizard or palette open; dictation or read-aloud active; any hold registered through **`Console.holdReload(id, fn)` in `core.js`** (idempotent by id; `agents.js` `"agents.drafts"` over `st.drafts`, `todos.js` `"todos.new"` over `st.newText`), because tab modules load before `app.js` creates `ConsoleApp` (`index.html:44-75`, `app.js:382`). A hidden, not-busy window reloads at the next check without waiting the idle timer. Loop guard: `sessionStorage["console-reload"]` keeps timestamps; at 3 automatic reloads in a rolling 5 minutes automatic reload pauses (notice and button stay, wording says paused) and re-arms itself; a manual reload never counts. D-11, D-12, D-14.
   - [ ] AC-14 [BROWSER] idle and not busy: reloads and the new JS/CSS is in effect.
   - [ ] AC-15 [BROWSER] each blocks the reload while it holds (typed text in the Assistant composer, the Agents composer, a Settings input; drawer; wizard; palette; dictation; read-aloud; a registered hold).
   - [ ] AC-16 [BROWSER] a half-typed Agents message (`st.drafts`) and todo (`st.newText`) survive; reload within one check after they are sent or cleared.
   - [ ] AC-17 [PY] source: `holdReload` defined once in `core.js`, called at top level from `agents.js` and `todos.js`; `app.js` calls no `ConsoleApp.holdReload`; `index.html` loads `core.js` before the tabs.
   - [ ] AC-18 [BROWSER] a Tauri window hidden by its close button (`main.rs:517-528`) with nothing dirty reloads without waiting 30 s; pass = that is observed, or WebView2 is observed not to report hidden and the idle rule reloads it; the verifier records which ("A-6 false" is a valid outcome).
   - [ ] AC-19 [PY] source: the guard stores timestamps under `sessionStorage["console-reload"]`, pauses at 3 in a rolling 5 minutes, no `to` comparison.
   - [ ] AC-20 [BROWSER] against a server returning a new `ui_version` every call: at most 3 automatic reloads in 5 minutes, then notice and button only (paused wording), automatic reload resumes after the window; manual reload works while paused.
   - [ ] AC-21 [BROWSER] stopping and starting the server 5 times in 60 s with files unchanged: zero reloads.
   - [ ] AC-22 [BROWSER] in the Tauri webview AC-14, AC-15, AC-18 hold and after the reload the window still has `in-shell` (A-7; if not, a defect to fix page-side before ship).
   - [ ] AC-23 [BROWSER] none of this runs in a static export.
   - [ ] AC-70 [BROWSER] Settings open and untouched reloads after the idle window; typing in a Settings input blocks it.
   - [ ] AC-78 [BROWSER] text placed in a textarea without typing (dictation, picker) blocks the reload until sent or cleared.

### Server: preference store
4. **FR-4 Store and API.** New `prefs` plugin (`features/prefs_feature.py` over pure `prefs_store.py`, one `plugins.toml` row, no `requires`), one JSON file `console/.cache/prefs.json` (gitignored, `.gitignore:66`) `{"v":1,"rev":N,"prefs":{...},"import_closed":false}`. `GET /api/prefs` → `{prefs, rev, import_open}`; `POST /api/prefs` `{set,del}` → `{rev, prev}` (D-21); `POST /api/prefs/import` `{values}` → `{prefs, rev, imported, skipped, rejected, closed}` (D-16); `POST /api/prefs/reset` → `{prefs:{}, rev, closed:true}`. `X-Console-Request: 1` on writes. `ValueError` → 400: key `^[A-Za-z][A-Za-z0-9_.-]{0,63}$`; value JSON with `allow_nan=False`, ≤ 32 KB, ≤ 128 keys, ≤ 256 KB file; `set` object, `del` list; checked after parsing (`httpd.py:190` has no cap). Lock + `.tmp` + `tomlio._replace`; missing/corrupt file reads empty; `rev` moves only on change; audit only `prefs.reset`/`prefs.import` (in `audit.ACTIONS`, key names and counts, D-19). Process-local lock accepted (one server per checkout).
   - [ ] AC-24 [PY] no file: `{prefs:{}, rev:0, import_open:true}`.
   - [ ] AC-25 [PY] set/del stored, returns `{rev, prev}` with `prev` = rev before; an equal set leaves `rev == prev`.
   - [ ] AC-26 [PY] `theme`, `a.b-c_d` accepted; empty, `1x`, `a b`, `../x`, 65 chars refused (400), nothing written.
   - [ ] AC-27 [PY] 32768-byte value accepted, 32769 refused; 129th key refused; > 256 KB file refused; NaN/Infinity refused; non-object `set`, non-list `del` refused.
   - [ ] AC-28 [PY] one valid + one invalid key in a request writes neither.
   - [ ] AC-29 [PY] missing/empty/corrupt file reads empty; next write replaces it.
   - [ ] AC-30 [PY] N threads setting distinct keys leave all keys and valid JSON; write goes through `tomlio._replace`.
   - [ ] AC-31 [PY] store path under `console/.cache/`; `.gitignore` contains `console/.cache/`.
   - [ ] AC-32 [PY] `prefs.reset`, `prefs.import` in `audit.ACTIONS` and recorded with key names/counts only; routine `set` records nothing.
   - [ ] AC-33 [PY] shipped `plugins.toml` has the `prefs` row (no `requires`); module exposes `PLUGIN`; four routes; no tab; `test_plugins.py` and `test_stylesheet.py` green.
   - [ ] AC-34 [PY] over HTTP: POST without `X-Console-Request: 1` → 403, with it → 201.
   - [ ] AC-35 [PY] `/api/config` carries `prefs_rev` = store rev when the provider is loaded, omits it when the plugin is disabled (`ctx.has_provider("prefs")`).
   - [ ] AC-36 [PY] source: no server module except `prefs_store`, `prefs_feature`, `shell_feature` reads preferences.

### Page: preference contract, migration, live pickup, Settings
5. **FR-5 `C.prefs` contract.** `get/set/del` keep their signatures, stay synchronous over an in-memory map, `get` deep-clones. New: `hydrate()` (never rejects), `refresh()`, `all()`, `keys()`, `reset()`, `mode()`, `rev()`. Boot: `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` before `applyTheme` (`app.js:337`). Server mode: 250 ms trailing debounce, coalesced, skipped when deep-equal; flush on `pagehide`/`visibilitychange` hidden with `fetch` `keepalive` + `X-Console-Request` (no `sendBeacon`); pre-hydration `set` and queued deltas re-applied over hydrate/import maps; `reset()` discards queued deltas; `refresh()` only with none pending. Local mode (static export, or `/api/prefs` unreachable/404): exact old `localStorage["console.*"]` behaviour; unreachable at boot renders from `localStorage`/defaults and retries. D-15: client mirrors key regex and 32 KB cap (invalid/oversize kept in memory, toasted once); failed flush retried on next `set`, `C.onConnection(true)`, successful heartbeat; a 400 drops the batch with a toast; keepalive only for bodies ≤ 60,000 bytes (the 64 KiB figure is recalled, not re-verified here), else one request per key, a single larger value without `keepalive`. D-17: hydration bound 3 s ⚠ [unrealistic?] (proposed), then boot proceeds as for "unreachable" and the late result goes through live pickup.
   - [ ] AC-37 [PY] source: `C.prefs` keeps `get/set/del` and adds `hydrate, refresh, all, keys, reset, mode, rev`.
   - [ ] AC-38 [PY] source: boot is `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` and `applyTheme` runs in its `.then`.
   - [ ] AC-39 [PY] source: page-hide flush uses `fetch` with `keepalive` and the CSRF header; `sendBeacon` absent from `console/static`.
   - [ ] AC-40 [BROWSER] mutating the object from `get` then `get` again returns the stored value.
   - [ ] AC-41 [BROWSER] with `theme=dark` on the server a fresh load paints dark with no default-theme flash.
   - [ ] AC-42 [BROWSER] 40 wizard keystrokes → ≤ 3 `POST /api/prefs`; a change just before closing the tab is on the server.
   - [ ] AC-43 [BROWSER] local mode: static export still uses `localStorage`; new JS against a server without `/api/prefs` runs without a console error; server unreachable at boot renders from `localStorage`/defaults and picks up server prefs on return.
   - [ ] AC-44 [PY] `layout` holding a 32 KB object is stored and returned; `del("layout")` works.
   - [ ] AC-45 [BROWSER] a `layout` object set in one client survives reload and shows in the other after its reload.
   - [ ] AC-71 [BROWSER] flush on hide: a one-key change then closing the tab is on the server; a delta > 60,000 bytes goes one key per request without throwing.
   - [ ] AC-72 [BROWSER] server stopped: a `set` stays in memory and is sent after it returns; a value > 32 KB is refused locally with one toast and never queued.
   - [ ] AC-73 [BROWSER] with `/api/prefs` delayed 10 s, first paint within 4 s from `localStorage`/defaults; the late result applies via live pickup.
   - [ ] AC-74 [PY] source: hydration bound, retry triggers (`C.onConnection`, heartbeat), mirrored key regex and 32 KB cap exist in `core.js`.
   - [ ] AC-81 [BROWSER] a change then a confirmed Reset within 250 ms leaves the server empty; a `set` during the migration import is still present afterwards.

6. **FR-6 Migration and live pickup.** Migration is a per-client, per-key move that never overwrites: first import wins; keys considered = `console.` + a regex-valid key; an unparsable local value is deleted silently; after the server's acknowledgement the client deletes imported, skipped and rejected keys, toasting each skipped key (with the browser's value) and each rejected key (with the reason); a failed import retries next boot; a closed window (after Reset) deletes without importing and shows one info toast ("Old settings in this browser were discarded because preferences were reset."). Equal values count as imported without bumping `rev`. Live pickup: `prefs_rev` on `/api/config`; on a heartbeat where it differs (`!==`) from the client's rev with nothing pending, `refresh()`, apply `theme` via `applyTheme` and, only if changed, `hiddenTabs` via `rebuildNav`; the `buildNav` `keydown` listener is bound once (`app.js:94-105`; `core.js:193` returns the same node); never re-render the active tab; the client adopts its POST response's `rev` only when `prev` equals its last known rev (D-21); absent `prefs_rev` ignored; object-valued keys are last-writer-wins as a whole (accepted). D-16, D-18, D-21.
   - [ ] AC-46 [PY] empty server: all valid keys imported, `skipped`/`rejected` empty; repeating returns the same `imported`, unchanged `rev`.
   - [ ] AC-47 [PY] server `theme=dark`, import `theme=light` + `voice`: `voice` imported, `theme` skipped and unchanged.
   - [ ] AC-48 [PY] after `reset`, `import` returns `closed:true`, imports nothing; `GET` shows `import_open:false`.
   - [ ] AC-49 [PY] `reset` empties prefs, bumps `rev`, sets `import_closed`, audited.
   - [ ] AC-50 [BROWSER] browser with `theme=dark` and an app with none: whoever loads first imports, the second never overwrites, both end on `dark`, local keys gone after the ack, a conflict toasts key and browser value.
   - [ ] AC-51 [BROWSER] after Reset in the app a stale browser deletes its keys without importing and shows defaults.
   - [ ] AC-52 [BROWSER] theme changed in a browser reaches the app within one heartbeat with no reload and no re-render of the active tab; `hiddenTabs` likewise; unflushed local changes block the refresh.
   - [ ] AC-53 [PY] source: heartbeat compares `prefs_rev` with `C.prefs.rev()` using `!==`, skips when undefined; the POST `rev` is adopted only under a `prev` check.
   - [ ] AC-75 [PY] import with `1x`, a 32769-byte value and a valid key: valid imported, other two in `rejected` with reasons, only the valid stored; file overflow rejects the overflow keys, not earlier ones.
   - [ ] AC-76 [BROWSER] skipped, rejected and closed toasts read as specified; a non-JSON local value vanishes without a toast.
   - [ ] AC-77 [BROWSER] five `hiddenTabs` pickups leave one `keydown` handler on `#tabs` (one ArrowRight moves one tab); an equal pickup does not rebuild; a newly hidden shown tab stays displayed.
   - [ ] AC-79 [BROWSER] two clients change different keys within one heartbeat: after one more heartbeat both show both changes.
   - [ ] AC-80 [PY] two interleaved imports of the same values end in the same state, same `imported`, `rev` bumped once.

7. **FR-7 Settings, Reset, statements.** Panel "Stored in this browser" → **Saved preferences**; server mode: "Shared by the desktop app and every browser tab on this machine. Kept on the server in `console/.cache/prefs.json`; not committed."; local mode: "Stored in this browser only."; **Reset all preferences** behind `window.confirm` ("Reset every saved preference for the app and all browser tabs? Tickets, chats and other data are not touched."), hint "Also clears the shared copy on the server, so the app and every open tab return to defaults."; behaviour `C.prefs.reset()` then `applyTheme("system")` and `rebuildNav()`; key list from `C.prefs.all()`, no `localStorage` in `settings.js`. Corrected statements: `settings.js:4-5,91-92,145-147,153-159,264-267,612,1770,1794,1800-1803`; `about.js:33,158-159`; `console/README.md:573-578`; `plugins.toml:14-16`; `registry.py:9-10`; `core.js:256-258,444` comments; `onboarding-wizard.js:4` (SHOULD, after that untracked file lands). "Agent CLIs" wording keeps its distinction (hides from the shared picker, not removed from the server).
   - [ ] AC-54 [PY] text checks: "Saved preferences", the confirm and both mode sentences present; "Affects this browser only. No server data is touched." gone; `about.js`, README table, `plugins.toml`, `registry.py` no longer call Settings toggles "one browser"/`localStorage`.
   - [ ] AC-55 [PY] source: `settings.js` has no `localStorage`; the panel uses `C.prefs.all()` and `reset()`.
   - [ ] AC-56 [BROWSER] server and local mode sentences; Reset confirms, cancel changes nothing, after confirming both clients show defaults after their next heartbeat/reload; key list shows server keys and values.

### Optional (SHOULD, separable)
8. **FR-8 Sidecar workspace identity.** `/api/config` carries `workspace` (12 hex of sha256 of the normalised real repo-root path, never the path); `desktop/sidecar.py` `ensure()`, when it would attach (`owned=false`), reads `/api/config` and raises `SidecarError` if `workspace` is present and differs; absent attaches as today; `is_up` stays a liveness probe; hash duplicated in a few lines (`sidecar.py:27-31`); no Rust change. The planner may drop FR-8 without touching FR-1..FR-7. Q2.
   - [ ] AC-57 [PY] `workspace` is 12 lowercase hex, constant per root, different per root, no path text.
   - [ ] AC-58 [PY] fake server: differing `workspace` → `ensure()` raises `SidecarError`; equal or absent attaches with `owned=false`; `is_up`/`probe` unchanged.
   - [ ] AC-59 [PY] the duplicated hash agrees with the server's; `sidecar.py` imports nothing from `console/`.
   - [ ] AC-60 [DOC] no plan task and no file in the ticket's recorded changed-files list is under `desktop/src-tauri/` (the working-tree diff is not evidence: T-031 edits Rust concurrently).

## Non-Functional Requirements

Targets marked ⚠ are analyst proposals with no stakeholder source, kept `⚠ [unrealistic?]` until the owner confirms (measurable, none blocks).

| ID | Requirement | Target | Verified by |
|---|---|---|---|
| NFR-1 | No new dependency: stdlib Python, vanilla ES5 IIFE JS, `C.el` (no `innerHTML` templates), no build step | zero new dependencies | AC-61 |
| NFR-2 | Python 3.11-clean (CI 3.11 and 3.13; local 3.14) | CI green on both; local 3.14 only is *not* evidence for 3.11 | CI matrix |
| NFR-3 | `test_stylesheet.py`, `test_plugins.py` stay green; new hyphenated classes exist in `styles.css`; no duplicate bare single-class selector; CSS inserted mid-file | green | AC-62 |
| NFR-4 | Stamp cost and payload growth | stat only (AC-6); ≤ 2 ms per call ⚠ (measured 0.144 ms; recorded, not asserted in CI); ≤ 100 bytes added to a 2031-byte response ⚠ | AC-6, AC-65 |
| NFR-5 | Request volume | 0 new timers and 0 new requests for the version check; ≤ 1 POST per client per 250 ms; `GET /api/prefs` once at boot + once per `prefs_rev` change; handler < 50 ms for a 256 KB file ⚠ | AC-42, AC-66 |
| NFR-6 | Hydration must not hold first render hostage | bound 3 s ⚠, then boot proceeds as for "unreachable" | AC-73 |
| NFR-7 | Security | 0 server modules besides store/plugin/`shell_feature` read prefs (AC-36); writes need the CSRF header (AC-34); keys outside the regex refused (AC-26); no secret stored | AC-26, AC-34, AC-36 |
| NFR-8 | Reliability | corrupt/missing file → empty, 0 exceptions (AC-29); concurrent writers → 0 lost keys, valid JSON (AC-30); a failed flush leaves the UI usable (AC-72) | AC-29, AC-30, AC-72 |
| NFR-9 | Change safety: `settings.js`, `app.js`, `index.html`, `shell_feature.py`, `audit.py`, `styles.css` carry other tickets' uncommitted hunks: surgical edits, re-read before every edit, foreign hunks byte-identical, no reformat; `audit.ACTIONS` edited only after its hunk settles; `onboarding-wizard.js:4` only after that file lands | foreign hunks unchanged | AC-63 |
| NFR-10 | Usability / accessibility | notice has `role="status"` and a keyboard-operable **Reload now**; every toast added is a sentence naming the key or cause | AC-10, AC-69, AC-76 |
| NFR-11 | Rollout: first deploy needs one manual relaunch or hard refresh (open pages have no version check) | release note and verification plan both contain the step and how to check it | AC-64 |
| NFR-12 | Platform coverage | Windows/WebView2 checked by AC-22; macOS and Linux webviews reported "not verified" | AC-22 |

- [ ] AC-61 [PY] `console/requirements-dev.txt` and any package manifest unchanged; `console/static/*.js` contain no `=>` and no statement-leading `let`/`const`.
- [ ] AC-62 [PY] `test_stylesheet.py` and `test_plugins.py` pass with the change.
- [ ] AC-63 [DOC] the verifier diffs each shared file against the pre-build snapshot named in the plan and reports any foreign hunk that moved (manual; not CI).
- [ ] AC-64 [DOC] `T-036-release.md` and `T-036-verification.md` state the one-time relaunch/hard-refresh step and how to check it (quit from the tray, relaunch).
- [ ] AC-65 [DOC] the verifier times `ui_version` (mean of 200 calls) and records it beside the 0.144 ms baseline; the NFR-4 ceiling is reported, not asserted.
- [ ] AC-66 [PY] source: no new `setInterval`/`setTimeout` loop and no new request for the version check; `GET /api/prefs` only from `hydrate()`/`refresh()`.

## Data Entities

Preferences file `console/.cache/prefs.json` (new; gitignored; created on first write; Reset empties it and closes the import window; deleting it resets everything) · `ui_version`, `prefs_rev`, `workspace` (SHOULD) on `/api/config` (new) · import result `imported/skipped/rejected[{key,reason}]/closed` (new) · POST result `{rev, prev}` (new) · reload guard `sessionStorage["console-reload"]` (new, rolling 5 minutes) · hold registry `Console.holdReload` in `core.js` (new, in memory) · legacy `localStorage["console.*"]` (exists; deleted after import acknowledgement) · `audit.ACTIONS` + `prefs.reset`, `prefs.import` (changed) · `plugins.toml` + `prefs` row (changed). New files: `console/server/prefs_store.py`, `console/server/features/prefs_feature.py`, `console/server/ui_version.py`. Fields and lifecycles: [[T-036-requirements-draft]] §6.

## Business Rules

BR-1 the server is the only store in server mode, no `localStorage` mirror · BR-2 the server never reads a pref to decide behaviour · BR-3 migration per client, per key, never overwrites, first import wins, local deleted only after the ack · BR-4 Reset closes the import window · BR-5 a response lacking `ui_version` never triggers a reload by itself; a page that booted without one treats the first later one as changed · BR-6 no automatic reload discards typed text, an open drawer/wizard/palette, or active dictation/read-aloud · BR-7 static export stays local and read-only, manifest gets no new field · BR-8 clients send deltas, same key last-writer-wins · BR-9 Reset states its reach and asks for confirmation · BR-10 no secret in `C.prefs` · BR-11 `voice`, `layout`, `chatListHidden` etc. shared by the owner's decision, three accepted risks (A-5) · BR-12 tab modules register their own off-DOM unsaved state through `Console.holdReload`; `app.js` enumerates nothing it does not own · BR-13 `C.prefs.get` synchronous, no read at script-evaluation time (T-037 included) · BR-14 `sidecar.is_up` stays a liveness probe · BR-15 an explicit **Reload now** is consent, an automatic reload never overrides BR-6 · BR-16 nothing leaves a browser's `localStorage` without a sentence (skipped, rejected, closed toasts), except an unparsable value.

## Edge Cases

Restart with changed routes/tabs but unchanged files (AC-5) · new JS on an un-restarted server → local mode (AC-43, AC-68) · file saved during page load missed until the next change (accepted) · `git checkout`/`touch` → one harmless idle reload · two clients, same key → last writer wins; different keys → both kept (AC-79) · write while the server is down lost on reload unless it returns in the same page lifetime (AC-72) · corrupt `prefs.json` (AC-29) · hidden window for days (AC-9, AC-18) · `localhost` vs `127.0.0.1` converge on the server copy · skipped/rejected values surface in toasts (AC-76) · unreachable at boot, a change, server returns: imported, skipped with toast if the key exists (accepted) · `panelOpen` whole-object last-writer-wins (accepted) · `prefs.json` deleted by hand: `rev` back to 0, clients compare for inequality · pickup hides the shown tab: stays displayed (AC-77) · request in flight at an automatic reload aborted (accepted) · tray mute not pushed on `voice` pickup (accepted, `agents.js:1534-1543`) · static file vanishes mid-sweep (AC-67).

## Interactions with Existing Features

23 rows (overlap 12, conflict 1, reuse 5, isolation 5): draft §9. Must-modify: `core.js` (`C.prefs`, `holdReload`), `app.js` (boot, `watchConnection`, `buildNav` listener, export), `settings.js` `storage()`, `shell_feature.py` (`ui_version`, `prefs_rev`, `workspace`), `plugins.toml`, `audit.py`, `agents.js`/`todos.js` (one `holdReload` call each), `styles.css` (one notice class), comments/docs listed in FR-7, `desktop/sidecar.py` (SHOULD). Isolate: Rust shell, HUD pages, chat state, static export, the five other tmp+replace writers. Resolved conflict: the v0 `ConsoleApp.holdReload` could not be called by `agents.js`/`todos.js` at load (CR-1, D-11). Constraints: foreign uncommitted hunks (NFR-9); `test_stylesheet.py` hyphenated-class rule; T-037's docked drawer must keep `ConsoleApp.drawer` for the busy check.

## Out of Scope
- See Scope above (Rust shell, HUD overlay, chat state, by-design differences, content-hash versions, consolidating the five JSON writers, detecting an older-than-code server).

## Open questions (non-blocking, defaults recorded)
Q1 live pickup (medium) · Q2 sidecar check (medium) · Q3 idle 30 s (low) · Q4 delete the local copy after import (low) · Q5 any key per-device (low). Each answer changes one default, not the shape of the requirements.

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements]] · [[T-036-requirements-draft]] · [[T-036-iteration-log]] · [[T-036-gap-analysis]] · [[T-036-critique-report]] · [[T-036-context-snapshot]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]]
- [[T-036-user-stories]] · [[T-036-release]] · [[T-036-components]] · [[T-036-effort-estimate]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-plan-iteration-log]] · Related: [[T-037-summary]] (stores `layout` through this contract) · [[T-031-summary]] (also edits `settings.js`) · [[T-004-analysis]] · [[T-002-analysis]]
