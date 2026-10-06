---
ticket: "T-036"
artifact: decision-log
---

# Decisions: T-036

Recorded 2026-10-05 in GROUND by the analyst. These are defaults chosen from the evidence in [[T-036-analysis]]; none needed the user, because the summary's decisions (auto-reload plus server-side prefs) already settle direction. Items marked **confirm at review** are assumptions the requirements round should confirm, not blockers.

## ui-version-stamp
**Decision:** The server computes `ui_version` = first 12 hex of sha256 over (a) sorted `(name, size, mtime_ns)` of the regular files in `console/static` matching `*.html *.js *.css *.png` (the set `export._copy_frontend` copies, `export.py:90`, so editor temp files never count) and (b) a manifest digest of the tab rows (`ctx.tabs()`) and route table (`ctx.router.describe()`), computed lazily once per process because neither can change without a restart. It is exposed as a new `ui_version` field in `GET /api/config` (`shell_feature.py:60-70`), not a new endpoint. It is **not cached**: the static half is recomputed per call. A missing field (static export, older server) means "unknown" and never triggers a reload.
**Rationale:** `/api/config` is already the 15 s heartbeat (`app.js:274`) and the sidecar readiness probe (`sidecar.py:23`), so the stamp adds no request and no timer. Cost measured: 0.144 ms for 29 files (200-run mean); the response is 2031 bytes. Stat-based rather than content-hash: a hash needs reading ~all static bytes or a cache layer, and its only gain is avoiding one harmless reload after `git checkout`/`touch`. Including the route table makes a restart that adds an endpoint (for example `/api/prefs`) look like a change, which is what lets a page in local-fallback mode pick the new server up. A Python-only behaviour change that alters neither routes nor manifest correctly does not reload the UI. Residual race, accepted: the boot version is read from the first `/api/config` after scripts load, so a file saved during page load is missed until the next change; injecting the version into `index.html` would close it but puts templating in the transport layer (`httpd.py` is "transport only").
**Impact:** New `console/server/ui_version.py` (pure `compute()`, owns the asset pattern; `export.py` may import it, optional one-liner) and a small edit to `shell_feature.py` (dirty from the onboarding work, coordinate). Tests: Python only (digest changes when a file's size or mtime changes, ignores `*.swp`, stable across calls; `/api/config` carries the field via the `call()` helper, `test_ui_endpoints.py:69-75`).

## reload-policy
**Decision:** The page records `ui_version` from its boot `/api/config` and compares on (1) every heartbeat (`HEARTBEAT_MS` 15 s, `app.js:250,270`; the payload is currently discarded), (2) the offline-to-online transition (`C.onConnection`), (3) `visibilitychange` to visible. On a mismatch it shows a persistent notice (`role="status"`: "A new version of the console is ready. It reloads when you pause." with a **Reload now** button) and calls `window.location.reload()` (as `app.js:352` already does) only when **idle and not busy**.
- **Idle** = no `keydown`, `pointerdown`, `wheel` or `touchstart` for 30 s (`pointermove` excluded so a resting mouse does not count as activity). **Confirm at review:** 30 s.
- **Busy** (any one blocks): a dirty field (any `textarea` with non-blank text, or a text-like `input` whose `value !== defaultValue`, focused or not); the shared drawer open (`ConsoleApp.drawer`, `app.js:17-53`); the setup wizard (`.ob-scrim`) or command palette open; dictation listening or `speechSynthesis` speaking (`voice.js`); or any module hold registered through a new `ConsoleApp.holdReload(fn)`. First registrants, because their text lives **off the DOM**: `agents.js` (`st.drafts`, `agents.js:49,1296-1298`) and `todos.js` (`st.newText`, `todos.js:198`).
- A hidden window (`document.hidden`) that is not busy reloads at the next check without waiting out the idle timer. Assumption: WebView2 reports hidden for a Tauri-hidden window (**unverified**); the dirty-field and hold checks still apply either way.
- **Loop guard:** `sessionStorage["console-reload"] = {to, at, n}`. After a reload, if the new boot version still differs from `to` (unstable stamp), or there were 3 auto-reloads in 5 minutes, stop auto-reloading and keep only the notice and button.
- Not active when `C.IS_STATIC` (no heartbeat, `app.js:267`).
- **Bootstrap:** the pages open today run JS without this logic and cannot adopt it; the first deploy needs one manual relaunch (quit from the tray, start again) or hard refresh. State this in the release note and the verification plan.
**Rationale:** The user's decision is "reload when idle, with a visible notice". Enumerating inputs in `app.js` would be a list that rots (settings alone has 10+ text inputs), so the dirty-field test is generic and only off-DOM state needs a registry, which follows the codebase's own register-yourself pattern (`Console.tab`, `core.js:22`). Re-rendering the tab instead of reloading was rejected: it would not pick up new JS or CSS.
**Impact:** `app.js` (boot, `watchConnection`, export; dirty hunks from other tickets, coordinate), `agents.js` and `todos.js` (one `holdReload` call each), one banner style in `styles.css` (a new hyphenated class must exist in CSS and no bare single-class selector may repeat, `test_stylesheet.py:65-135`; add it mid-file, T-037 forbids appending at the end where `.ob-*` lives). Verification needs a real browser and the Tauri webview; there is no JS runner. A source-regexp test can pin the registry call sites and the heartbeat comparison (pattern `test_plugins.py:263-285`).

## prefs-store-file-and-api
**Decision:** One JSON file per machine, `console/.cache/prefs.json` (gitignored by `.gitignore:66`), path via `resolve_rel`, shape `{"v":1,"rev":N,"prefs":{key: any JSON},"import_closed":false}`. A new plugin `prefs` (`features/prefs_feature.py` plus one `plugins.toml` row, no `requires`) over a pure module `prefs_store.py`:
- `GET /api/prefs` returns `{prefs, rev, import_open}`.
- `POST /api/prefs` with `{set:{k:v}, del:[k]}` returns `{rev}`.
- `POST /api/prefs/import` with `{values:{k:v}}` returns `{prefs, rev, imported:[], skipped:[], closed}`.
- `POST /api/prefs/reset` returns `{prefs:{}, rev, closed:true}` and sets `import_closed`.
- Validation raises `ValueError` (becomes 400, `httpd.py:141-142`): key must match `^[A-Za-z][A-Za-z0-9_.-]{0,63}$`; value any JSON serialised with `allow_nan=False`, at most 32 KB per value, 128 keys, 256 KB for the file; `set` an object, `del` a list of valid keys. `httpd.py:190` does not cap the body, so limits are checked after parsing.
- Writes: a module `threading.Lock` around read-modify-write (the server is `ThreadingHTTPServer`, `httpd.py:303`), `json.dump` to `.tmp`, then `tomlio._replace` (Windows-safe retry, `tomlio.py:314-322`). A missing or corrupt file reads as empty (as `onboarding_setup._read_json`, `:36-42`). `rev` increments only when state actually changed. Read per call, no cache.
- Audit only `prefs.reset` and `prefs.import` (routine sets, especially `onboardingDraft` per keystroke, would flood `console/.cache/audit`).
- **The server never reads a pref to decide behaviour.** Prefs are view state, writable by any page that can send the CSRF header on an unauthenticated port; anything that must act on the server stays in its own validated setting (the `notify.py:55-102` stance).
**Rationale:** TOML cannot hold these values (`tomlio.py:232-271`: one table level, no `null`), so `tomlio.atomic_write` is out. JSON in `console/.cache/` matches the per-machine precedents (`assistant_config.py:39`, `provider_overrides.py:88-122`, `onboarding_setup.py:26-27`). A key **pattern** instead of a fixed allowlist, so adding a preference needs no server edit (the open/closed intent of `plugins/base.py:9-12`); a forgotten allowlist entry would otherwise fail silently as a 400 on a view setting. A separate plugin lets `enabled = false` fall back to local mode cleanly. Clients send deltas, so two clients editing different keys never overwrite each other; the same key is last-writer-wins.
**Impact:** New `prefs_store.py`, `features/prefs_feature.py`, `plugins.toml` row (the shipped-registry tests pick it up, `test_plugins.py:44-90`), new `console/tests/test_prefs_store.py` and route tests via the `call()` helper. Reuses `tomlio._replace` (private name, same package); five modules already hand-roll tmp+replace (`onboarding_setup.py:45-51`, `assistant_config.py:586-593`, `provider_overrides.py:115-122`, `jobs.py:119-123`, `runs.py:48-63`); **do not refactor them here**, log a todo. `audit.py` is dirty from other work; add the two action names only after it settles.

## prefs-client-contract
**Decision:** `C.prefs.get/set/del` keep their exact signatures and stay synchronous, backed by an in-memory map. `get` returns a deep clone (callers mutate then `set`, `core.js:276-278`, `agents.js:159-161`; absent key returns the fallback, a stored `null` returns `null`, as today). New members: `hydrate()` (never rejects), `refresh()`, `all()`, `keys()`, `reset()`, `mode()` (`"server"` or `"local"`), `rev()`.
- **Boot:** `app.js` waits on `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` so hydration completes before `applyTheme` (`app.js:337`), the first read. No code reads prefs at script-evaluation time today; keep it that way (T-037 included).
- **Server mode:** `set/del` update the map at once and queue a delta, flushed after a 250 ms trailing debounce, coalesced, skipped when the value is deep-equal. On `pagehide` and `visibilitychange` to hidden, flush with `fetch(..., {keepalive:true})` and the `X-Console-Request: 1` header; `navigator.sendBeacon` cannot send that header and would get 403 (`httpd.py:187-189`). A `set` made before hydration finishes is kept and re-applied over the hydrated map.
- **Local mode** (static export: `C.IS_STATIC`, `core.js:12`; or `/api/prefs` unreachable or 404, for example new JS on a server not yet restarted): behave exactly as today against `localStorage["console.*"]`. Hydration failure is silent; the version stamp (route table) makes the page reload into server mode once the server restarts with the new routes.
- A write that fails in server mode stays in memory for that page lifetime; the connection pill already reports the outage (`core.js:154-157`). Accepted: it is lost on reload.
- `settings.js` `storage()` uses `C.prefs.all()` and `C.prefs.reset()` instead of touching `localStorage` (`settings.js:1729-1731,1778,1787`).
**Rationale:** The summary requires callers unchanged and hydrate-before-first-render. Keeping `localStorage` as a live mirror in server mode was rejected (CANONICAL gate: one source of truth; a mirror brings back stale-origin divergence and a second reset path). The cost is the existing pre-paint theme flash staying as it is (theme is applied after `/api/config` today, `app.js:337`).
**Impact:** `core.js` (prefs block, export `:752`), `app.js` boot, `settings.js` `storage()`. Python tests cover the store; JS behaviour is verified by hand in a browser (mode server, mode local, server stopped) and in the Tauri webview.

## prefs-migration-rule
**Decision:** A one-time **move**, per client, per key, never overwriting.
- On first hydrate in server mode, a client that still holds `console.*` keys in `localStorage` posts them to `/api/prefs/import`. The server adds each key it does **not** already have (**first import wins per key**), and returns `imported`, `skipped` (server already had a different value) and `closed`.
- After the server acknowledges, the client **deletes** its local `console.*` keys (imported and skipped), so there is exactly one source of truth. If `skipped` is non-empty it shows one toast naming each key and the value this browser had, so nothing is lost silently.
- No marker is needed: no local keys means nothing to import. A failed or lost import retries on the next boot and is idempotent.
- **Reset closes the migration window** (`import_closed`). After a reset, a client that still holds old keys is told `closed:true` and deletes them without importing, so a stale browser cannot resurrect values the user deliberately cleared.
**Rationale:** The two clients were not symmetric: the app held none of `theme`, `hiddenTabs`, `disabledBackends`, so the meaningful values are in the browser. A single global "imported" flag consumed by the first, empty, client would discard them, hence per client. Last-writer-wins was rejected: localStorage values carry no timestamps, and it lets whichever client launches last overwrite the other and, later, a stale client clobber a choice made after migration. First-import-wins is deterministic, idempotent and loses nothing in the realistic case (the overlap is at most `agentLane`, `voice`, `modelByBackend`, `panelOpen`, `chatListHidden`, and only differing explicit values conflict). So this needs no user decision. **Confirm at review:** deleting the local copy after import (vs keeping it) trades rollback to the old UI for single source of truth; a rollback just sees defaults, and the data is on the server.
**Impact:** `prefs_store.import_values()` is pure and fully unit-testable (empty server, partial overlap, conflict, closed, repeated call, size caps); client side in `core.js`. A second origin (`localhost` vs `127.0.0.1`) now converges instead of diverging.

## prefs-live-pickup
**Decision:** `GET /api/config` also carries `prefs_rev` (present only when the prefs provider is loaded; `shell_feature` asks `ctx.has_provider("prefs")`, no hard `requires`). On a heartbeat where `prefs_rev` differs from the client's `rev` and there are no pending local deltas, the client calls `C.prefs.refresh()` and applies the two preferences with global visual effect: `theme` through `ConsoleApp.applyTheme` and `hiddenTabs` through `ConsoleApp.rebuildNav`. It does **not** re-render the active tab (that would wipe drafts); every other key takes effect the next time its tab renders. The client takes its own `rev` from each POST response so it does not re-pull its own change.
**Rationale:** The goal is "keep them showing the same UI". Without this, a theme chosen in the browser would reach the app only at its next reload, which is the original complaint in a smaller form. Cost: one integer in a response that is already fetched, plus a 1-2 KB GET only when something changed. **Assumption, confirm at review:** the summary says "keep them showing it" but does not explicitly require live propagation; the fallback if declined is hydrate at boot plus the version reload.
**Impact:** `prefs_store.rev()`, one line in `shell_feature.py`, a `watchConnection` branch in `app.js`.

## settings-reset-wording
**Decision:** The "Stored in this browser" panel (`settings.js:1726-1805`) becomes **Saved preferences**. In server mode it states: "Shared by the desktop app and every browser tab on this machine. Kept on the server in `console/.cache/prefs.json`; not committed." In local mode (static snapshot or server unreachable): "Stored in this browser only." The button stays **Reset all preferences**, now behind `window.confirm` (already used for a destructive Settings action, `settings.js:1313`): "Reset every saved preference for the app and all browser tabs? Tickets, chats and other data are not touched." Hint line: "Also clears the shared copy on the server, so the app and every open tab return to defaults." Behaviour: `C.prefs.reset()` (server reset, closes import, clears legacy local keys), then the existing `ConsoleApp.applyTheme("system")` and `rebuildNav()` (`settings.js:1788-1789`). The key list reads `C.prefs.all()`.
The other statements that become false are corrected in the same change: `settings.js:91-92,145-147,153-159,264-267,612,1800-1803`, `about.js:33`, `console/README.md:573-578`, `console/config/plugins.toml:14-16`, `console/server/plugins/registry.py:9-10`, `onboarding-wizard.js:4`. The "Agent CLIs" wording keeps its real distinction: this hides a CLI from the shared picker, it does not remove it from the server (`settings.js:153-159`).
**Rationale:** Reset now reaches every client, so the old "Affects this browser only. No server data is touched." would be a lie, and an unconfirmed click is a larger mistake than before.
**Impact:** `settings.js` (inside `storage()`, which also holds an uncommitted "Setup wizard" row from the onboarding work, `:1756-1768`, so sequence after that commits), `about.js`, README, config comments. `test_docs_agree_with_config.py` does not mention prefs (grep), so no existing test pins the old wording.

## sidecar-identity
**Decision:** Optional hardening, separable, Python only. `GET /api/config` also carries `workspace`: first 12 hex of sha256 of the normalised real path of the repo root the server serves (not the path itself, since the port can be non-loopback, `httpd.py:225-240`). `desktop/sidecar.py` keeps `is_up` as a pure liveness probe (also used by `probe` and the start-up wait loop, `sidecar.py:279-285,306-310`). `ensure()` gains an attach check: when it would attach to an already-running server (`owned=false`), it reads `/api/config`; if `workspace` is present and differs from its own root's id it raises `SidecarError` ("port 8790 is served by a different workspace; stop that server or change the port"); a missing field (older server) attaches as today. A server older than the current Python code is **not** detected or killed (killing would also stop agent sessions, `httpd.py:332-341`); the UI-version reload covers the visible symptom.
**Rationale:** `ensure` attaches to anything that answers (`sidecar.py:279-280`), and `.claude/worktrees/T-024/` shows another full copy of the repo exists, so showing a different checkout's UI is possible; it was **not** observed here. The Rust host surfaces `ensure` stderr as its error text (`sidecar.rs:109-123`) and its `Handle` ignores unknown JSON fields (`sidecar.rs:7-11`), so no Rust change is needed. `sidecar.py` must stay importable without `console/` on the path (`sidecar.py:27-31`), so the hash and normalisation (realpath, normcase) are duplicated in 3 lines and a test asserts both sides agree. Lower priority than the first two halves; the planner may drop it without affecting them.
**Impact:** `desktop/sidecar.py`, `shell_feature.py` (same edit as the stamp), `desktop/tests/test_sidecar.py` (fake server returning `/api/config`; the existing live-spawn tests are the pattern, `:135-165`). Python 3.11 compatible (CI, `verify.yml:23-48`).

## t037-layout-contract
**Decision:** [[T-037-summary]] stores pane sizes as one `layout` object through `C.prefs`, and this ticket guarantees: key `layout` is valid (pattern above), value up to 32 KB, writes are debounced (a drag may call `set` at high frequency), `get` returns a clone, no read at script-evaluation time (read at attach or render), and `C.prefs.del("layout")` is the "Reset layout" primitive. "Reset all preferences" also clears `layout`. Build order: this ticket's store first, or T-037 ships against the unchanged local `C.prefs` and is picked up by the move-import unchanged.
**Rationale:** Same convention as `panelOpen` (one object per concern, `core.js:254-258`); the summary of T-037 already depends on it.
**Impact:** No code beyond this ticket's; T-037's requirements should cite this contract rather than restate it.

## scope-boundaries
**Decision:** In scope as the summary states. Explicitly **not** covered and stated so nobody assumes otherwise: Rust shell changes; the HUD overlay (`hud.html`, a second long-lived page with its own inline script and no heartbeat; it stays as stale as the app did); assistant chat state; the by-design app/browser differences. Accepted risks, not questions: (1) `voice` is shared by the user's decision, so muting from the app tray (`Voice.setPrefs({autoRead})`, `agents.js:1580`) also changes browser read-aloud; (2) pixel-based `layout` and `chatListHidden` are shared across different window sizes, including a phone or laptop that reaches the console over a tailnet (`httpd.py:225-240`), since the store is per server, not per device; (3) a prefs write made while the server is down is lost on reload. Deferred follow-ups for a later ticket or todo: consolidating the five tmp+replace JSON writers; reloading the HUD page; content-hash versions.
**Rationale:** Matches the summary's out-of-scope list; the risks follow directly from the user's "voice and the like" decision and are cheap to revisit per key later.
**Impact:** Release note carries the relaunch step; requirements draft lists the three risks as assumptions.

## Amendments from CLARIFY (2026-10-05, `challenge-requirements` pass 1)

Added by the analyst (D-11..D-21) while resolving the findings in [[T-036-critique-report]] and the gaps in [[T-036-gap-analysis]]. None needed the user; where an entry below conflicts with an earlier one, **the entry below wins** and the earlier one is amended as named. The five confirm-at-review items above are tracked as non-blocking questions Q1-Q5 in `T-036-questions.toml`.

## D-11 reload-hold-registry-in-kernel
**Amends:** `reload-policy`. **Resolves:** CR-1.
**Decision:** The hold registry is `Console.holdReload(id, fn)` in `core.js` (idempotent by `id`: a second call with the same id replaces the first; `fn()` returns true while the module holds unsaved state), not `ConsoleApp.holdReload`. `agents.js` registers `"agents.drafts"` (any non-blank `st.drafts` value) and `todos.js` registers `"todos.new"` (non-blank `st.newText`) at their top level. `ConsoleApp` may re-export it; nothing may depend on that.
**Rationale:** `index.html:44-75` loads every tab before `app.js`, and `window.ConsoleApp` is created at `app.js:382`; a top-level `ConsoleApp.holdReload(...)` in `agents.js` or `todos.js` throws and aborts the tab module. `core.js` loads first and already hosts the register-yourself seam (`Console.tab`, `core.js:22`).
**Impact:** `core.js`, `agents.js`, `todos.js`, `app.js` (reads the registry). Source-regexp AC pins the definition in `core.js` and one call in each of the two tabs.

## D-12 dirty-field-rule
**Amends:** `reload-policy`. **Resolves:** CR-3.
**Decision (revised in iteration 2, CR-19):** (a) any `textarea` in the DOM with non-blank text is dirty, whatever put it there; (b) a text-like `input` or `[contenteditable]` is dirty when the **user** typed in it (a document-level capture `input` listener records `e.target` in a `WeakSet` only when `e.isTrusted`) and it is still in the DOM with non-blank text; (c) a focused field with non-blank text is dirty. `value !== defaultValue` is not used.
**Rationale:** Settings fills `input`s with `el.value = …` (`settings.js:325,329,340,832,988`), which makes `value !== defaultValue` true with no user input, so the Settings tab would never auto-reload; there is no `textarea` in `settings.js` (grep), so (a) cannot over-block there. The first version of this rule (typed-only for every field) missed text put into a textarea by dictation (`agents.js:695-709,1349`) or by the `/ @ #` picker (`composer-pick.js:187`), which assign `.value` without an `input` event; a textarea is a draft by nature. Off-DOM drafts are covered by the hold registry (D-11).
**Impact:** `app.js`. [BROWSER] check: Settings open and untouched for the idle window reloads; typing into any Settings input blocks.

## D-13 unknown-version-rule
**Amends:** `ui-version-stamp`, `reload-policy`. **Resolves:** CR-2, G6, G16.
**Decision:** Boot version absent and a later response carries one = **changed** (reload when idle and not busy). Boot version present and a later response lacks the field = ignored. Both absent = nothing. On the server a vanished file during the `stat` sweep is skipped, and if the static directory cannot be listed `ui_version` is omitted; the stamp never makes `/api/config` fail (it is the sidecar readiness probe, `sidecar.py:23`).
**Rationale:** New JS can be served by a server that has not restarted (static files are read per request, `httpd.py:94-115`); that page boots without a version and runs in local mode (`prefs-client-contract`). When the server restarts, the first response with a version must move it to server mode. Stable afterwards, so no loop.
**Impact:** `app.js` compare, `ui_version.py`, `shell_feature.py`.

## D-14 loop-guard-count-only
**Amends:** `reload-policy`. **Resolves:** CR-4.
**Decision:** `sessionStorage["console-reload"]` holds the timestamps of recent automatic reloads. At 3 automatic reloads inside a rolling 5 minutes, automatic reload pauses (notice and **Reload now** stay, the notice says auto-reload is paused) and re-arms by itself when the window slides past. The `to` comparison is dropped. A manual **Reload now** never counts.
**Rationale:** The stamp is server-side, so a reload that fetched stale JS still boots with the current version and cannot loop; the only loop is an unstable stamp, which the count bounds (3 per 5 minutes, at idle only). A `to` comparison trips on a legitimate edit that lands during the open-ended idle wait, and "stop" had no end in a webview that lives for days.
**Impact:** `app.js`; AC-19 and AC-20 reworded.

## D-15 prefs-write-failure-policy
**Amends:** `prefs-client-contract`. **Resolves:** CR-5, CR-6, G7, G8.
**Decision:** The client mirrors the key regex and the 32 KB cap; an invalid key or oversized value is kept in memory only (never queued) and toasted once per key per session. A failed flush keeps its deltas queued and retries on the next `set`, on `C.onConnection(true)` and on each successful heartbeat; a 400 drops that batch once with a toast; `refresh()` stays blocked only while deltas are pending and retryable. The page-hide flush uses `keepalive` only when the serialised body is ≤ 60,000 bytes; larger deltas go one key per request, and a single value over that goes without `keepalive` (best effort). The 64 KiB keepalive budget is from the Fetch standard as recalled, **not re-verified in this session** (web fetches of the spec did not return the step); the [BROWSER] check covers it.
**Rationale:** Without a retry rule one failed write freezes live pickup; without a 400 rule it retries forever; realistic prefs are well under 2 KB, so the split path is a guard, not a hot path.
**Impact:** `core.js` prefs block.

## D-16 prefs-import-outcomes
**Amends:** `prefs-migration-rule`. **Resolves:** CR-7, G3, G4.
**Decision:** `POST /api/prefs/import` returns `{prefs, rev, imported, skipped, rejected, closed}` where `rejected` is `[{key, reason}]` for an invalid key, an over-cap value or a full file. The client toasts each rejected key with its reason, then deletes it (it cannot live on the server). A local value that does not parse is treated as absent and deleted silently. When `closed` is true the client deletes its keys and shows one info toast: "Old settings in this browser were discarded because preferences were reset." Only keys the old `C.prefs` could have written (`console.` + a regex-valid key) are considered.
**Rationale:** Nothing may disappear without a sentence; "skipped" and "rejected" are different facts.
**Impact:** `prefs_store.import_values`, `core.js`, tests for each bucket.

## D-17 hydration-bound
**Amends:** `prefs-client-contract`. **Resolves:** CR-8, G18.
**Decision:** `hydrate()` resolves within 3 s (proposed, marked ⚠ [unrealistic?] in NFR-6) even if the request is still open. On timeout boot proceeds as for "server unreachable" (read `localStorage`/defaults) and the late result is applied through the live-pickup path (`theme`, `hiddenTabs`); `mode()` becomes `"server"` when it lands.
**Rationale:** the shared request timeout is 15 s (`core.js:50`); a hung `/api/prefs` must not blank the first render for that long.
**Impact:** `core.js`, `app.js` boot.

## D-18 live-pickup-nav-guard
**Amends:** `prefs-live-pickup`. **Resolves:** CR-10, G14, G22.
**Decision:** Pickup calls `rebuildNav` only when the new `hiddenTabs` differs (deep-equal) from the current value; the `keydown` listener in `buildNav` (`app.js:94-105`) is bound once, outside the rebuild. The active tab's content is never replaced by pickup, even if it is newly hidden.
**Rationale:** `C.clear` returns the same `#tabs` node (`core.js:193`), so each rebuild stacks another listener and one arrow key moves several tabs (from code; not reproduced). Pickup raises the call frequency, so the latent defect becomes reachable.
**Impact:** `app.js` (a change to existing code, inside the function this ticket already touches).

## D-19 audit-actions-registered
**Resolves:** CR-16, G20, G27.
**Decision:** `prefs.reset` and `prefs.import` are appended to `audit.ACTIONS` (`audit.py:44`, which feeds `kanban.py audit --action`, `kanban.py:977`, and the Work-tab filter, `work_feature.py:48`). Detail carries key names and counts, never values. Done only after the foreign hunk in `audit.py` settles (NFR-9).
**Impact:** `audit.py`, `prefs_feature.py`, a test (`test_notify_audit.py:268` is the pattern).

## D-20 manual-reload-is-consent
**Resolves:** G5.
**Decision:** **Reload now** reloads at once, regardless of the busy rules; while the page is busy the notice says unsaved text will be lost on reload. Automatic reload never overrides busy (BR-6).
**Rationale:** an explicit click is the user's decision; the busy rules protect against the page deciding for them.

## D-21 prefs-own-rev-adoption
**Amends:** `prefs-live-pickup`, `prefs-store-file-and-api`. **Resolves:** CR-20, CR-21, CR-24.
**Decision:** `POST /api/prefs` returns `{rev, prev}` (`prev` = rev before the call). After its own flush the client adopts `rev` only when `prev` equals the rev it last knew; otherwise another client changed prefs in between, the client keeps its older `rev`, and the next heartbeat's mismatch triggers `refresh()`. Import and reset return the full map and the client replaces its own. An absent `prefs_rev` in `/api/config` is ignored. In import, a key whose server value is already deep-equal is reported in `imported` and does not increment `rev`.
**Rationale:** "take your own rev from the POST response" (`prefs-live-pickup`) hides an intervening change: the response's `rev` already includes it, so the client would believe it is current. Equal-value imports make two tabs importing at once, or a retry, harmless.
**Impact:** `prefs_store`, `core.js`, ACs 25, 46, 53, 79, 80.

## Plan-stage decisions (2026-10-05, planner)

Made while planning; none changes a requirement. Where one amends an earlier entry it says so. Shared plan rules live in [[T-036-plan]]; these are the choices behind them.

## D-22 build-order
**Decision:** serial order 0 → prefs store (server) → UI version (server) → client prefs → Settings and wording → reload logic → sidecar (droppable) → release and gates. **Rationale:** [[T-037-summary]]'s `layout` needs the prefs contract first; the reload half reuses the heartbeat handler the prefs half creates in `app.js`; one builder and six shared dirty files forbid parallel edits. **Impact:** [[T-036-components]] § Suggested build order.

## D-23 css-before-js
**Decision:** the notice's one hyphenated class lands (task 14) before any JS names it, inserted mid-file next to `.toast` (`styles.css:~1851-1858`), never at the end where another ticket's `.ob-*` block sits; the print rule (which lists the foreign `.ob-scrim`) is not touched. **Rationale:** `test_stylesheet.py` fails a JS class with no rule, and T-037 forbids end-of-file appends.

## D-24 busy-drawer-by-dom
**Amends:** `reload-policy` (which cited `ConsoleApp.drawer`). **Decision:** the busy check tests `document.querySelector(".drawer")` rather than adding an accessor to the drawer IIFE (`app.js:17-53`). **Rationale:** T-037 rewrites that region into a docked panel; a DOM check means this ticket never edits it. **Impact:** hand-off note: T-037 must keep the `.drawer` class or update `isBusy`; a source test checks `class: "drawer"` exists in `app.js` (CR-37).

## D-25 no-new-timers
**Decision:** every reload decision runs from the existing heartbeat tick, `C.onConnection(true)` or `visibilitychange` visible; idleness is a timestamp comparison (`Date.now() - lastActive`), not a timer. The only new `setTimeout`s are in `core.js` (the 250 ms flush debounce and the one-shot 3 s hydrate bound). **Rationale:** NFR-5 and AC-66 (0 new timers and 0 new requests for the version check); a reload is therefore decided up to one heartbeat (15 s) after the idle window ends. The connection and visibility triggers call the same `C.get("/api/config")` the heartbeat already makes, which AC-66 allows.

## D-26 onchange-interface
**Decision:** live pickup reaches the page through `C.prefs.onChange(fn)`; `core.js` diffs the map and hands the listeners the changed key names after `refresh()`, an import or a late hydrate, and `app.js` applies `theme` and `hiddenTabs` (D-18 guard). **Rationale:** keeps key knowledge (`theme`, `hiddenTabs`) in the router that owns the effect and out of the generic prefs block; one interface for the three triggers.

## D-27 snapshots-and-attribution
**Decision:** task 00 saves `<name>.orig` and `<name>.diff` for the six shared files under `console/.cache/t036-prebuild/` (gitignored, survives a session change), and every shared-file task saves `<name>.pre-<NN>` before its first edit. **Rationale:** AC-63 needs a pre-build snapshot named in the plan; per-task copies attribute each hunk when another ticket's work advances the same file mid-build (CR-28).

## D-28 ui-version-object
**Decision:** `ui_version.py` owns the asset patterns and a small `UiVersion(static_dir, manifest_fn)` object created once in `shell_feature.apply`; the manifest digest is memoised lazily inside it, the static half is recomputed per call. `export.py` is not edited: a test asserts the stamp's file set equals what `_copy_frontend` copies. **Rationale:** AC-5 needs "once per process" to be testable without module-level state leaking between tests; avoids a second foreign-adjacent edit.

## D-29 post-error-status
**Decision:** one additive line in `core.js` `post` so the thrown `Error` carries `status`. **Rationale:** D-15 distinguishes a 400 (drop the batch with a toast) from a network failure (retry); `post` currently throws a bare `Error` (`core.js:151`).

## D-30 workspace-helper-location
**Decision:** `_workspace_id(repo_root)` lives in `shell_feature.py` (not `paths.py`), duplicated in three lines in `desktop/sidecar.py`, with a test asserting the two agree. **Rationale:** it is used in exactly one server place and the sidecar cannot import `console/` (`sidecar.py:27-31`).

## D-31 test-layout
**Decision:** new test files per slice (`test_prefs_store.py`, `test_prefs_routes.py`, `test_ui_version.py`, `test_config_payload.py`, `test_prefs_client_source.py`, `test_ui_constraints.py`, `test_prefs_wording.py`, `test_reload_source.py`), the `app` fixture and `call()` copied into `test_prefs_routes.py` rather than moved to `conftest.py`. **Rationale:** `conftest.py` is shared by every test and other tickets add tests concurrently; a 15-line copy is cheaper than a shared-file edit.

## Links
- Related: [[T-037-summary]] · [[T-031-summary]]
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-context-snapshot]] · [[T-036-requirements-draft]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-effort-estimate]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]]
