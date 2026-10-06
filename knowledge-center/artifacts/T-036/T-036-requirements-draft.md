---
ticket: "T-036"
artifact: requirements-draft
status: frozen
freeze_status: frozen
frozen_at: "2026-10-05"
frozen_iteration: 3
iteration: 3
created: "2026-10-05"
last_updated: "2026-10-05"
---

# Requirements Draft: T-036

> Requirements draft. **Frozen 2026-10-05 at iteration 3** — see [[T-036-requirements]]; further change only through `evolve`.

**Command reference:**
- **Created by:** `requirements T-036 draft`
- **Grounded by:** `analyze T-036` → writes `T-036-context-snapshot.md`
- **Gaps surfaced by:** `challenge-requirements T-036 (gaps dimension)`
- **Challenged by:** `challenge-requirements T-036` (adds ⚠ markers below)
- **Enriched by:** `requirements T-036 enrich [source]`
- **Cross-checked by:** `challenge-requirements T-036 (overlap/conflict/reuse dimension)`
- **Iterated by:** `requirements T-036 iterate "feedback"`
- **Frozen by:** `requirements T-036 freeze` → produces `T-036-requirements.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

**Verification tags (every acceptance criterion carries one):** **[PY]** pytest, no browser, no internet (includes Python tests of routes/validation and source-regexp checks of JS/HTML/TOML/Markdown files in the repo; CI runs Python 3.11 and 3.13, `.github/workflows/verify.yml:23-48`) · **[BROWSER]** needs a real browser and the Tauri webview; there is no JS runner and CI does not install Node, so the build pipeline **cannot** run these and they stay *not verified* until a person (or a driven browser) does them · **[DOC]** the verifier reads a ticket artifact (release note, verification plan).

---

## 1. Intent

**Stakeholder (one line):** Make the desktop app and any browser tab show the same UI, and keep them showing it.

**Business driver:** On 2026-10-05 the desktop app ran a UI loaded at 08:21:59 while `console/static` was edited 09:43-10:02 and the server restarted at 10:03:01; a browser tab opened later showed the new UI ([[T-036-analysis]] §1, root cause confirmed by timeline; the live page's JS heap and the user's browser were not inspected).

**Raw intent verbatim:**
> "the app and the web app UI is out of sync" (user, 2026-10-05)
>
> Decision (user, 2026-10-05): "auto-reload on a new UI version **and** shared preferences through the server" ([[T-036-summary]] Overview)

**Interpretation:** (1) a long-lived page notices that the served UI changed and reloads itself when that is safe; (2) preferences that today live in each browser's `localStorage` live on the server so the app and every browser read and write the same ones.

## 2. Context Summary

(Condensed from [[T-036-context-snapshot]]; evidence in [[T-036-analysis]]; defaults in [[T-036-decision-log]].)

- **Similar existing features:** heartbeat that ignores its payload (`console/static/app.js:250-276`); reload-on-reconnect after a failed boot (`app.js:347-362`, reload at `:352`); `/api/config` nav manifest and sidecar readiness probe (`console/server/features/shell_feature.py:53-70`, `desktop/sidecar.py:23`); `C.prefs` (`console/static/core.js:444-458`); per-machine settings in `console/.cache/` (`notify.py:55-102`, `assistant_config.py:39`, `provider_overrides.py:88-122`); Windows-safe replace (`console/server/tomlio.py:314-322`); per-chat draft kept across repaints (`agents.js:49,1296-1298`); static export with `IS_STATIC` fallbacks (`export.py:42-45`, `core.js:12,128-143`).
- **Affected code areas:** server (`shell_feature.py`, new `ui_version.py`, `prefs_store.py`, `features/prefs_feature.py`, `plugins.toml`, `audit.py`); JS (`core.js`, `app.js`, `settings.js`, `about.js`, `agents.js`, `todos.js`, `styles.css`, `index.html` only if a tag is needed); `desktop/sidecar.py` (optional); docs/comments (`console/README.md:571-578`, `plugins.toml:14-16`, `registry.py:9-10`).
- **Known risks from history:** a reload mid-typing loses DOM-only text; a reload loop if the stamp is unstable; a first migration consumed by an empty client loses the browser's real values; per-keystroke `onboardingDraft` writes (`onboarding-wizard.js:235,239`); `sendBeacon` cannot carry the CSRF header (`httpd.py:187-189`); shared `voice` couples tray mute to browser read-aloud (`agents.js:1580`); concurrent uncommitted edits in `app.js`, `settings.js`, `index.html`, `shell_feature.py`, `audit.py` ([[T-036-analysis]] §8).

## 3. Scope

### In scope
- **S1 UI version stamp and auto-reload:** server `ui_version`; page compares on heartbeat, reconnect and visibility; persistent notice; reload only when idle and not busy; loop guard (summary scope 1).
- **S2 Server-side preferences:** store, API, synchronous `C.prefs` kept, hydrate before first render, write-through, local fallback (summary scope 2).
- **S3 Migration, Reset and live pickup:** one-time move of existing `localStorage` values; "Reset all preferences" clears the server copy; a change in one client reaches the others (summary scope 3; live pickup is assumption A-2).
- **S4 Settings wording and stale statements** that become false once prefs move to the server ([[T-036-analysis]] §7).
- **S5 T-037 `layout` contract:** the `layout` key works through this store ([[T-037-summary]], decision `t037-layout-contract`).
- **S6 Sidecar workspace identity (SHOULD, separable, "Phase 3"):** Python only (decision `sidecar-identity`; assumption A-4, Q2).
- **S7 Rollout:** the first deploy needs one manual relaunch or hard refresh (open pages have no version check); stated in the release note and verification plan.

### Out of scope (explicit)
- Rust shell changes: the page reloads itself ([[T-036-summary]] Scope).
- The HUD overlay `hud.html`/`flash.html`: a second long-lived page with its own inline script and no heartbeat (`hud.html:141`); it stays as stale as the app did.
- Assistant/agent chat state: already server-side, re-attaches by `seq` after a reload (`chat-store.js` header comment).
- By-design app/browser differences: the app lands on Assistant, shows window chrome, speaks through piper (`app.js:59-71`).
- Content-hash versions, reloading the HUD, consolidating the five hand-rolled tmp+replace JSON writers (`onboarding_setup.py:45-51`, `assistant_config.py:586-593`, `provider_overrides.py:115-122`, `jobs.py:119-123`, `runs.py:48-63`): deferred follow-ups.
- Detecting or restarting a server older than the current Python code (killing it would also stop agent sessions, `httpd.py:332-341`).

### Assumptions
- **A-1:** idle window is 30 s with no `keydown`, `pointerdown`, `wheel`, `touchstart` (Q3).
- **A-2:** live pickup of `theme` and `hiddenTabs` across clients is wanted; the summary says "keep them showing it" but not explicitly live (Q1).
- **A-3:** after the server accepts a client's import, that client deletes its local `console.*` keys (Q4).
- **A-4:** the sidecar workspace check is wanted in this ticket as a SHOULD (Q2).
- **A-5:** all 16 keys are shared, including `voice` and pixel `layout`; accepted risks: tray mute also mutes browser read-aloud; pixel layout is shared across window sizes and devices; a write made while the server is down is lost on reload (Q5; decision `scope-boundaries`).
- **A-6:** WebView2 reports `document.hidden` for a Tauri-hidden window (`main.rs:517-528`); **unverified** ([[T-036-context-snapshot]] §6).
- **A-7:** `location.reload()` works in the Tauri webview and the Rust initialization script (`main.rs:116-125`) runs again on reload; **unverified**.
- **A-8:** the root cause is the timeline-confirmed one; the live page's heap was not probed.

## 4. Functional Requirements

Each FR is independently verifiable. Acceptance criteria are numbered globally (`AC-n`, stable ids) and tagged.

### FR-1: UI version stamp on `/api/config`
**Description:** `GET /api/config` returns `ui_version`: first 12 hex of sha256 over (a) the sorted `(name, size, mtime_ns)` of the regular files in `console/static` matching `*.html *.js *.css *.png` (the set `export._copy_frontend` copies, `export.py:90`) and (b) a digest of the tab manifest (`ctx.tabs()`) and route table (`ctx.router.describe()`, `plugins/base.py:93-97`) computed lazily once per process. The static half is recomputed per call (no cache). Python stdlib only; stat only, no file reads. A file that vanishes during the sweep (editor save-rename) is skipped; if the static directory cannot be listed, `ui_version` is omitted and `/api/config` still answers (it is the sidecar readiness probe). Decisions `ui-version-stamp`, D-13.

**Actor:** any page or probe calling `/api/config`. **Trigger:** every call, including the 15 s heartbeat and the sidecar readiness probe (`sidecar.py:23`).

**Preconditions:** `console/static` is a flat directory of 29 files today ([[T-036-analysis]] §4).

**Flow:** handler builds the existing payload, adds `ui_version`; no new endpoint, no new request, no new timer.

**Postconditions / observable outcomes:** the value changes exactly when the served UI files or the route/tab manifest change.

**Acceptance criteria (testable):**
- [ ] AC-1 [PY] `/api/config` via the router-level `call()` helper (`console/tests/test_ui_endpoints.py:69-75`) returns `ui_version` as 12 lowercase hex characters, and `title, subtitle, tabs, boards, stale_days` keep their shape.
- [ ] AC-2 [PY] two calls with no file change return the same value.
- [ ] AC-3 [PY] the value changes when a matching file's size changes, when only its mtime changes (`os.utime`), and when a matching file is added or removed.
- [ ] AC-4 [PY] the value does not change when a non-matching file (`*.swp`, `*.txt`) is added, touched or removed.
- [ ] AC-5 [PY] the manifest half changes when the tab set or route table changes, and is computed once per process (a second call does not recompute it).
- [ ] AC-6 [PY] `compute()` opens no static file (a test that makes `open` raise still passes): stat only.
- [ ] AC-7 [PY] the stamp's file set equals the set `export._copy_frontend` copies for the shipped static dir; the static export manifest (`export.py:75-82`) carries no `ui_version`.
- [ ] AC-67 [PY] a matching file that vanishes between listing and `stat` is skipped without an exception; when the static directory cannot be listed `/api/config` still returns its other keys and omits `ui_version`.

**Business rules invoked:** BR-5, BR-7

### FR-2: The page records the version and compares it
**Description:** the page records `ui_version` from its boot `/api/config` and compares it on (1) every heartbeat (`HEARTBEAT_MS` 15 s, `app.js:250,270-275`, whose payload is discarded today), (2) the offline-to-online transition (`C.onConnection`, `core.js:86-99`), (3) `visibilitychange` to visible. On a mismatch it shows a persistent notice (`role="status"`: "A new version of the console is ready. It reloads when you pause.") with a **Reload now** button. The notice is a non-modal element visible on every tab, **not a toast** (toasts auto-dismiss, `core.js:508-522`), and must not cover the drawer's close button. Version rules (D-13): boot version absent and a later response carries one = changed; boot version present and a later response lacks it = ignored; both absent = nothing. **Reload now** reloads at once regardless of the busy rules and, while the page is busy, the notice says unsaved text will be lost (D-20). Inactive when `C.IS_STATIC`. Decisions `reload-policy`, D-13, D-20.

**Actor:** the person using the app or a browser tab. **Trigger:** a heartbeat, reconnect or the page becoming visible.

**Preconditions:** server mode (`C.IS_STATIC` false); the boot response may or may not carry `ui_version` (rules above).

**Flow:** compare → on mismatch show the notice (once) → hand over to FR-3's safety rules.

**Postconditions / observable outcomes:** the notice stays until the page reloads.

**Acceptance criteria (testable):**
- [ ] AC-8 [PY] source: `app.js` reads `ui_version` from the boot result and from the heartbeat result; `watchConnection` no longer discards the heartbeat payload.
- [ ] AC-9 [PY] source: the comparison is also wired to `C.onConnection` and to a `visibilitychange` listener, and is skipped when `C.IS_STATIC`.
- [ ] AC-10 [BROWSER] after a served static file changes, the notice (`role="status"`, with a "Reload now" button) appears within one heartbeat (15 s plus the request) and is still shown after 60 s with no interaction (it is not a toast, `core.js:508-522`).
- [ ] AC-11 [BROWSER] against a server whose `/api/config` never has `ui_version`, no notice appears and no reload ever happens.
- [ ] AC-12 [BROWSER] "Reload now" reloads at once, also while a field holds typed text; in that state the notice says unsaved text will be lost.
- [ ] AC-13 [BROWSER] in a static export opened from `file://` there is no heartbeat, no notice, no reload.
- [ ] AC-68 [BROWSER] a page that booted against a server without `ui_version` (old server, new JS) shows the notice and reloads when idle once the server restarts with the field, and then runs in server mode; a later response without the field is ignored.
- [ ] AC-69 [PY] source: `app.js` contains the strings `Reload now` and `role: "status"` for the notice, and any new hyphenated class used from JS exists in `styles.css` (`test_stylesheet.py` rule, NFR-3). That it is not a toast is checked by AC-10 [BROWSER].

**Business rules invoked:** BR-5, BR-6, BR-15

### FR-3: Reload only when idle and not busy
**Description:** after a mismatch, `window.location.reload()` (the primitive `app.js:352` already uses) runs only when the page is **idle** (no `keydown`, `pointerdown`, `wheel` or `touchstart` for 30 s; `pointermove` excluded) and **not busy**. Busy (any one blocks): a **dirty field**: (a) any `textarea` in the DOM with non-blank text, whatever put it there (typed, dictated or picker-inserted: `agents.js:695-709,1349` and `composer-pick.js:187` assign `.value` without an `input` event; a textarea is a draft by nature and none in Settings is prefilled, `grep textarea settings.js` is empty); (b) a text-like `input` or `[contenteditable]` the user typed in (a document-level capture `input` listener records `e.target` in a `WeakSet` only when `e.isTrusted`) while it is still in the DOM with non-blank text; (c) a focused field with non-blank text. `value !== defaultValue` is **not** used, because Settings fills `input`s with `.value = …` (`settings.js:325,329,340,832,988`) and would never auto-reload; the shared drawer open (`ConsoleApp.drawer`, `app.js:17-53`); the setup wizard (`.ob-scrim`) or command palette (`.cp-scrim`) open; dictation listening or read-aloud speaking (`voice.js:25,142,201`); or any module hold registered through `Console.holdReload(id, fn)`, defined in `core.js` (idempotent by id; `fn()` returns true while the module holds unsaved state), because `agents.js` and `todos.js` load before `app.js` creates `ConsoleApp` (`index.html:44-75`, `app.js:382`). First registrants, because their text is held off the DOM: `agents.js` (`"agents.drafts"` over `st.drafts`, `agents.js:49,1296-1298`) and `todos.js` (`"todos.new"` over `st.newText`, `todos.js:22,200-201`). A hidden window (`document.hidden`) that is not busy reloads at the next check without waiting out the idle timer. **Loop guard:** `sessionStorage["console-reload"]` holds the timestamps of recent automatic reloads; at 3 automatic reloads inside a rolling 5 minutes automatic reload pauses (the notice and button stay and the notice says auto-reload is paused) and re-arms by itself when the window slides past; a manual **Reload now** never counts. Must work in the Tauri webview via `location.reload()`; must not loop if the server flaps. Decisions `reload-policy`, D-11, D-12, D-14.

**Actor:** the page. **Trigger:** a pending mismatch plus any of the idle/visibility checks.

**Postconditions / observable outcomes:** no automatic reload ever discards typed text, an open drawer/wizard/palette, or an active dictation.

**Acceptance criteria (testable):**
- [ ] AC-14 [BROWSER] idle and not busy: the page reloads by itself and the new JS/CSS is in effect afterwards (a changed label or colour is visible).
- [ ] AC-15 [BROWSER] each of these blocks the automatic reload for as long as it holds, and the notice stays: typed text in the Assistant composer, in the Agents composer, in a Settings text input; the drawer open; the setup wizard open; the palette open; dictation active; read-aloud active; a registered hold.
- [ ] AC-16 [BROWSER] a half-typed Agents message (held in `st.drafts`) and a half-typed todo (`st.newText`) survive: no reload while they exist, reload within one check after they are sent or cleared.
- [ ] AC-17 [PY] source: `holdReload` is defined once, in `core.js`; `agents.js` and `todos.js` each call it at top level; `app.js` does not call a `ConsoleApp.holdReload`; `index.html` still loads `core.js` before the tabs.
- [ ] AC-18 [BROWSER] a window hidden by its close button (Tauri hides rather than closes, `main.rs:517-528`) with nothing dirty reloads without waiting the 30 s idle timer. Pass condition (A-6 unverified): either that is observed, or WebView2 is observed not to report hidden and the idle rule alone reloads it; the verifier records which, and "A-6 false" is a valid recorded outcome, not a failure.
- [ ] AC-19 [PY] source: the guard stores recent automatic-reload timestamps under `sessionStorage["console-reload"]`, pauses at 3 within a rolling 5 minutes and has no `to` comparison.
- [ ] AC-20 [BROWSER] against a test server that returns a different `ui_version` on every call, at most 3 automatic reloads happen in 5 minutes, then only the notice and button remain (with the paused wording), and automatic reload resumes once the window slides past; a manual **Reload now** still works while paused.
- [ ] AC-21 [BROWSER] stopping and starting the server 5 times in 60 s with the files unchanged causes zero reloads.
- [ ] AC-22 [BROWSER] inside the Tauri webview: AC-14, AC-15 and AC-18 hold, and after the reload the window still has the `in-shell` class (window chrome, Assistant-first nav) because the Rust initialization script runs again (A-7, unverified; if it does not, that is a defect to fix before ship, not a recorded outcome; no Rust change is in scope, so the fix would be page-side).
- [ ] AC-23 [BROWSER] none of this runs in a static export.
- [ ] AC-70 [BROWSER] the Settings tab open and untouched (inputs filled by the page, nothing typed) reloads after the idle window; typing in any Settings text input blocks the reload until it is cleared.
- [ ] AC-78 [BROWSER] text placed in a textarea without typing (dictation into the Agents composer or the new-chat prompt; a `/ @ #` pick into an otherwise empty box) blocks the automatic reload until it is sent or cleared.

**Business rules invoked:** BR-6, BR-12

### FR-4: Server-side preference store and API
**Description:** a new `prefs` plugin (`console/server/features/prefs_feature.py` over a pure `prefs_store.py`, plus one row in `console/config/plugins.toml`, no `requires`) keeps one JSON file `console/.cache/prefs.json` (gitignored, `.gitignore:66`), shape `{"v":1,"rev":N,"prefs":{key: any JSON},"import_closed":false}`. Routes: `GET /api/prefs` → `{prefs, rev, import_open}`; `POST /api/prefs` `{set:{k:v}, del:[k]}` → `{rev, prev}` (`prev` = the rev before this call, so a client can tell whether anyone else changed prefs in between, D-21); `POST /api/prefs/import` `{values:{k:v}}` → `{prefs, rev, imported, skipped, rejected, closed}` (`rejected` = `[{key, reason}]`, D-16); `POST /api/prefs/reset` → `{prefs:{}, rev, closed:true}`. Writes need `X-Console-Request: 1` (`httpd.py:187-189`). Validation raises `ValueError` (becomes 400, `httpd.py:141-142`): key matches `^[A-Za-z][A-Za-z0-9_.-]{0,63}$`; value any JSON serialised with `allow_nan=False`, at most 32 KB per value, 128 keys, 256 KB for the file; `set` an object, `del` a list of valid keys (limits are checked after parsing because `httpd.py:190` does not cap the body). Write = module `threading.Lock` around read-modify-write, `json.dump` to `.tmp`, then `tomlio._replace`. A missing or corrupt file reads as empty. `rev` increments only when state actually changed. Audit only `prefs.reset` and `prefs.import`, both registered in `audit.ACTIONS` (D-19), detail = key names and counts, never values. The lock is process-local: one server per checkout is the supported setup (accepted, G12); each write is atomic so the file never corrupts, and a single corrupt `prefs.json` resets all clients to defaults with no backup (accepted, view state is re-settable). Decisions `prefs-store-file-and-api`, D-16, D-19.

**Actor:** any client of the console. **Trigger:** hydrate, write-through, import, reset.

**Preconditions:** plugin enabled in `plugins.toml`; with `enabled = false` the routes do not exist and clients fall back to local mode (FR-5).

**Postconditions / observable outcomes:** two clients editing different keys never overwrite each other (deltas); the same key is last-writer-wins; the file is always valid JSON.

**Acceptance criteria (testable):**
- [ ] AC-24 [PY] `GET /api/prefs` with no file returns `{prefs:{}, rev:0, import_open:true}`.
- [ ] AC-25 [PY] `POST /api/prefs` stores a set and applies a del, returns `{rev, prev}` with `prev` equal to the rev before the call; a set equal to the stored value leaves `rev` unchanged (`rev == prev`).
- [ ] AC-26 [PY] keys `theme` and `a.b-c_d` are accepted; empty, `1x`, `a b`, `../x` and a 65-character key are refused with `ValueError` (400) and nothing is written.
- [ ] AC-27 [PY] a 32768-byte value is accepted and a 32769-byte one refused; the 129th key is refused; a write that would take the file past 256 KB is refused; NaN and Infinity are refused; a non-object `set` and a non-list `del` are refused.
- [ ] AC-28 [PY] a request with one valid and one invalid key writes neither.
- [ ] AC-29 [PY] a missing, empty or corrupt `prefs.json` reads as empty; the next write replaces it.
- [ ] AC-30 [PY] N threads setting distinct keys concurrently leave every key present and the file valid JSON; the write goes through `tomlio._replace`.
- [ ] AC-31 [PY] the store path is under `console/.cache/` and `.gitignore` contains `console/.cache/`.
- [ ] AC-32 [PY] `prefs.reset` and `prefs.import` are in `audit.ACTIONS` and are recorded by `audit.record` with key names and counts only, never values; a routine `set` records nothing (pattern `console/tests/test_notify_audit.py:268`).
- [ ] AC-33 [PY] the shipped `plugins.toml` has a `prefs` row (no `requires`); its module imports and exposes `PLUGIN`; the four routes exist; the plugin registers no tab; `console/tests/test_plugins.py` and `console/tests/test_stylesheet.py` stay green.
- [ ] AC-34 [PY] over HTTP (in-process server), a `POST /api/prefs` without `X-Console-Request: 1` returns 403 and with it returns 201.
- [ ] AC-35 [PY] `/api/config` carries `prefs_rev` equal to the store's rev when the provider is loaded and omits it when the plugin is disabled (`ctx.has_provider("prefs")`, `plugins/base.py:129`).
- [ ] AC-36 [PY] source: no server module other than `prefs_store`, `prefs_feature` and `shell_feature` reads preferences (the server never reads a pref to decide behaviour).

**Business rules invoked:** BR-2, BR-8, BR-10

### FR-5: Client preference contract (`C.prefs`)
**Description:** `C.prefs.get/set/del` keep their exact signatures and stay synchronous, backed by an in-memory map; `get` returns a deep clone (callers mutate then `set`, `core.js:276-278`, `agents.js:159-161`; absent key returns the fallback, a stored `null` returns `null`). New members: `hydrate()` (never rejects), `refresh()`, `all()`, `keys()`, `reset()`, `mode()` (`"server"` or `"local"`), `rev()`. **Boot:** `app.js` waits on `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` so hydration completes before `applyTheme` (`app.js:337`). **Server mode:** `set/del` update the map at once and queue a delta, flushed after a 250 ms trailing debounce, coalesced, skipped when deep-equal; on `pagehide` and `visibilitychange` to hidden, flush with `fetch(..., {keepalive:true})` and the `X-Console-Request: 1` header (`navigator.sendBeacon` cannot send it); a `set` made before hydration finishes is re-applied over the hydrated map, and queued deltas are likewise re-applied over the map an import returns; `reset()` discards queued deltas (the person asked for defaults, so a change queued a moment earlier must not resurrect); `refresh()` only runs with none pending. **Local mode** (static export `C.IS_STATIC`, or `/api/prefs` unreachable or 404): exactly the old behaviour against `localStorage["console.*"]`; hydration failure is silent; if the server is unreachable at boot the page renders from `localStorage`/defaults and retries. **Write failures (D-15):** the client mirrors the key regex and the 32 KB cap; an invalid key or oversized value is kept in memory only (never queued) and toasted once per key per session; a failed flush keeps its deltas queued and retries on the next `set`, on `C.onConnection(true)` and on each successful heartbeat; a 400 drops that batch once with a toast; the page-hide flush uses `keepalive` only when the serialised body is ≤ 60,000 bytes (the 64 KiB keepalive budget is from the Fetch standard as recalled, not re-verified in this session), otherwise one request per key, and a single value above that goes without `keepalive` (best effort). **Hydration bound (D-17):** `hydrate()` resolves within 3 s ⚠ [unrealistic?] (NFR-6) even if the request is still open; on timeout boot proceeds as for "server unreachable" and the late result is applied through the live-pickup path. Decisions `prefs-client-contract`, D-15, D-17.

**Actor:** every tab module. **Trigger:** any `C.prefs` call.

**Postconditions / observable outcomes:** no caller changes; the 16 existing keys ([[T-036-analysis]] §3) and T-037's `layout` work unchanged.

**Acceptance criteria (testable):**
- [ ] AC-37 [PY] source: `core.js` `C.prefs` still defines `get`, `set`, `del` with their old signatures and adds `hydrate`, `refresh`, `all`, `keys`, `reset`, `mode`, `rev`.
- [ ] AC-38 [PY] source: `app.js` boot is `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` and `applyTheme` is called inside the `.then` of that chain.
- [ ] AC-39 [PY] source: the page-hide flush uses `fetch` with `keepalive` and the `X-Console-Request` header; `sendBeacon` does not appear in `console/static`.
- [ ] AC-40 [BROWSER] mutating the object returned by `get` and calling `get` again returns the stored value unchanged.
- [ ] AC-41 [BROWSER] hydrated before first render: with `theme=dark` stored on the server, a fresh load paints dark with no flash of the default theme.
- [ ] AC-42 [BROWSER] 40 keystrokes in the setup wizard produce at most 3 `POST /api/prefs` requests, and a change made just before closing the tab is on the server afterwards (keepalive flush).
- [ ] AC-43 [BROWSER] local mode: a static export still reads and writes `localStorage`; new JS against a server without `/api/prefs` runs without a console error; with the server unreachable at boot the page renders from `localStorage`/defaults and picks up server prefs once it returns.
- [ ] AC-44 [PY] the key `layout` holding a 32 KB object is stored and returned (T-037 contract); `del` of `layout` works.
- [ ] AC-45 [BROWSER] a `layout`-shaped object set in one client survives a reload and shows in the other client after its reload.
- [ ] AC-71 [BROWSER] flush on hide: a one-key change followed at once by closing the tab is on the server (small delta, `keepalive`); a delta whose serialised size exceeds 60,000 bytes is sent one key per request and does not throw.
- [ ] AC-72 [BROWSER] with the server stopped, a `set` stays in memory and is sent after the server returns (retry on reconnect); a value over 32 KB is refused locally with one toast and never queued.
- [ ] AC-73 [BROWSER] with `/api/prefs` delayed by 10 s, the first paint happens within 4 s (the 3 s bound plus render) from `localStorage`/defaults and the late result is applied through the live-pickup path.
- [ ] AC-81 [BROWSER] a preference changed and then "Reset all preferences" confirmed within 250 ms leaves the server empty (the queued delta was discarded); a `set` made while the migration import is in flight is still present afterwards.
- [ ] AC-74 [PY] source: the hydration bound and the retry triggers (`C.onConnection`, heartbeat) exist in the `core.js` prefs block and the key regex and 32 KB cap are mirrored there.

**Business rules invoked:** BR-1, BR-8, BR-11, BR-13

### FR-6: Migration of existing values and live pickup
**Description:** **Migration** is a one-time move, per client, per key, never overwriting. On first hydrate in server mode a client that still holds `console.*` keys in `localStorage` posts them to `/api/prefs/import`; the server adds each key it does not already have (first import wins per key) and returns `imported`, `skipped` (server already had a different value), `rejected` (`[{key, reason}]`: invalid key, over-cap value or full file) and `closed`. Only keys the old `C.prefs` could have written are considered (`console.` + a regex-valid key); a local value that does not parse is treated as absent and deleted silently, as `C.prefs.get` already does (`core.js:449-450`). After the server acknowledges, the client deletes its local `console.*` keys (imported, skipped and rejected); it shows a toast naming each skipped key with the value this browser had, and a toast naming each rejected key with its reason. A failed import retries on the next boot. **Reset closes the import window** (`import_closed`): afterwards a client still holding old keys is told `closed:true`, deletes them without importing and shows one info toast: "Old settings in this browser were discarded because preferences were reset." (the window never reopens except by deleting `prefs.json`; intended, BR-4). **Live pickup:** `/api/config` carries `prefs_rev`; on a heartbeat where it differs (`!==`, never `>`: the integer resets to 0 if the file is deleted) from the client's `rev` and there are no pending retryable local deltas, the client calls `C.prefs.refresh()` and applies `theme` through `ConsoleApp.applyTheme` and, only when it actually changed (deep-equal check), `hiddenTabs` through `ConsoleApp.rebuildNav`; the `keydown` listener in `buildNav` is bound once, outside the rebuild, because each rebuild otherwise stacks another on the same `#tabs` node (`app.js:94-105`, `core.js:193`); pickup never re-renders the active tab, even one it newly hides; every other key takes effect at the next render of its tab; after its own flush the client adopts the POST response's `rev` **only when `prev` equals the rev it last knew**; otherwise someone else changed prefs in between, the client keeps its older `rev`, and the next heartbeat's mismatch triggers `refresh()` (D-21); an absent `prefs_rev` (plugin disabled, older server) is ignored; a key whose server value is already deep-equal to the imported one is reported in `imported` without incrementing `rev` (so a second tab importing the same values at the same moment, or a repeated call, is harmless). Object-valued keys (`panelOpen`, `voice`, `modelByBackend`, `layout`) are last-writer-wins as a whole; the refresh within one heartbeat bounds the loss (accepted, G10). Decisions `prefs-migration-rule`, `prefs-live-pickup`, D-16, D-18.

**Actor:** each client on first load; each client on every heartbeat. **Trigger:** hydrate; heartbeat.

**Acceptance criteria (testable):**
- [ ] AC-46 [PY] `import_values` on an empty server imports every valid key with `skipped` and `rejected` empty; repeating the same call returns the same `imported` list, `skipped` empty and an unchanged `rev` (idempotent; equal values count as imported, not skipped).
- [ ] AC-47 [PY] with `theme=dark` already stored, importing `theme=light` and `voice={...}` returns `voice` in `imported` and `theme` in `skipped`, and the stored `theme` is unchanged.
- [ ] AC-48 [PY] after `reset`, `import` returns `closed:true`, imports nothing, and `GET /api/prefs` reports `import_open:false`.
- [ ] AC-49 [PY] `reset` empties the prefs, increments `rev`, sets `import_closed`, and is audited.
- [ ] AC-50 [BROWSER] migration: a browser holding `theme=dark` and the app holding none: whichever loads first imports; the second never overwrites; both end on `dark`; local `console.*` keys are gone after the acknowledgement; a conflicting value produces one toast naming the key and the browser's value.
- [ ] AC-51 [BROWSER] after Reset in the app, a stale browser reloading deletes its old keys without importing and shows defaults.
- [ ] AC-52 [BROWSER] live pickup: changing the theme in a browser switches the app's theme within one heartbeat (15 s) with no reload and no re-render of the active tab; `hiddenTabs` likewise; a client with unflushed local changes does not refresh until they are sent.
- [ ] AC-53 [PY] source: the heartbeat compares `prefs_rev` with `C.prefs.rev()` using `!==` (no `>`/`<` on `rev`), skips the comparison when `prefs_rev` is undefined, and the POST response's `rev` is adopted only under a `prev` check.
- [ ] AC-75 [PY] import with an invalid key (`1x`), an over-cap value (32769 bytes) and a valid key in one call returns the valid key in `imported`, the other two in `rejected` with a reason each, and stores only the valid one; an import that fills the file past 256 KB rejects the overflow keys, not the earlier ones.
- [ ] AC-76 [BROWSER] migration copy: a conflicting value shows one toast naming the key and the browser's value; a rejected key shows a toast naming the key and the reason; the closed case shows the one-sentence info toast; a local value that is not valid JSON vanishes without a toast.
- [ ] AC-79 [BROWSER] two clients change different keys inside one heartbeat (A sets `theme`, B sets `hiddenTabs`, both flush): after one more heartbeat both clients show both changes; neither client's own POST hides the other's change.
- [ ] AC-80 [PY] two imports of the same values interleaved from two threads end with the same stored state, each reporting the same `imported` list, and `rev` incremented once.
- [ ] AC-77 [BROWSER] repeated live pickups of `hiddenTabs` (change it five times from another client) leave exactly one `keydown` handler on `#tabs`: one ArrowRight moves exactly one tab; a pickup that leaves `hiddenTabs` equal does not rebuild the nav; a tab hidden by pickup while shown stays displayed.

**Business rules invoked:** BR-3, BR-4, BR-8

### FR-7: Settings panel, Reset, and corrected statements
**Description:** the "Stored in this browser" panel (`settings.js:1770`) becomes **Saved preferences**. Server mode: "Shared by the desktop app and every browser tab on this machine. Kept on the server in `console/.cache/prefs.json`; not committed." Local mode: "Stored in this browser only." The button stays **Reset all preferences**, now behind `window.confirm` (precedent `settings.js:1313`): "Reset every saved preference for the app and all browser tabs? Tickets, chats and other data are not touched."; hint "Also clears the shared copy on the server, so the app and every open tab return to defaults." Behaviour: `C.prefs.reset()` (server reset, closes import, clears legacy local keys), then `ConsoleApp.applyTheme("system")` and `rebuildNav()` (`settings.js:1788-1789`). The key list reads `C.prefs.all()` and no longer touches `localStorage`. The statements that become false are corrected in the same change: `settings.js:4-5,91-92,145-147,153-159,264-267,612,1770,1794,1800-1803`; `about.js:33,158-159`; `console/README.md:573-578`; `console/config/plugins.toml:14-16`; `console/server/plugins/registry.py:9-10`; the `core.js:256-258,444` comments; `onboarding-wizard.js:4` (a SHOULD, done only after that still-untracked file lands, NFR-9). The "Agent CLIs" wording keeps its distinction: it hides a CLI from the shared picker, it does not remove it from the server (`settings.js:153-159`). `export.py:49` stays true (static mode). Decision `settings-reset-wording`.

**Acceptance criteria (testable):**
- [ ] AC-54 [PY] text checks: `settings.js` contains "Saved preferences", the confirm text and the server-mode and local-mode sentences, and no longer contains "Affects this browser only. No server data is touched."; `about.js`, `console/README.md` (two-switches table), `plugins.toml` and `registry.py` no longer describe Settings toggles as "one browser"/`localStorage`.
- [ ] AC-55 [PY] source: `settings.js` has no `localStorage` access; the panel uses `C.prefs.all()` and `C.prefs.reset()`.
- [ ] AC-56 [BROWSER] server mode shows the shared-prefs sentence; local mode (static export) shows "Stored in this browser only."; Reset asks for confirmation, and after confirming both the app and a browser show defaults after their next heartbeat/reload; cancelling changes nothing; the key list shows the server's keys and values.

**Business rules invoked:** BR-4, BR-9

### FR-8: Sidecar workspace identity (SHOULD, separable, Phase 3)
**Description:** Python only. `GET /api/config` also carries `workspace`: first 12 hex of sha256 of the normalised real path of the repo root (not the path itself; the port can be non-loopback, `httpd.py:203-240`). `desktop/sidecar.py` keeps `is_up` as a pure liveness probe (used by `probe` and the start-up wait, `sidecar.py:110-117,279-285,306-310`). `ensure()` gains an attach check: when it would attach to an already-running server (`owned=false`) it reads `/api/config`; if `workspace` is present and differs from its own root's id it raises `SidecarError` ("port 8790 is served by a different workspace; stop that server or change the port"); a missing field (older server) attaches as today. The hash and normalisation (realpath, normcase) are duplicated in a few lines because `sidecar.py` must stay importable without `console/` (`sidecar.py:27-31`). No Rust change (`sidecar.rs:7-11,109-123`). The planner may drop this FR without affecting FR-1..FR-7. Decision `sidecar-identity`; Q2.

**Acceptance criteria (testable):**
- [ ] AC-57 [PY] `workspace` is 12 lowercase hex, constant for one root, different for two roots, and contains no path text.
- [ ] AC-58 [PY] with a fake server answering `/api/config`: a differing `workspace` makes `ensure()` raise `SidecarError`; an equal or absent one attaches with `owned=false`; `is_up` and `probe` behave as before.
- [ ] AC-59 [PY] the duplicated hash in `sidecar.py` agrees with the server's for the same root; `sidecar.py` imports nothing from `console/`.
- [ ] AC-60 [DOC] no task in the plan and no file in the ticket's recorded changed-files list is under `desktop/src-tauri/` (the working-tree diff is not usable evidence: T-031 edits the Rust shell concurrently).

**Business rules invoked:** BR-14

## 5. Non-Functional Requirements

| ID | Category | Requirement | Target | Verified by |
|---|---|---|---|---|
| NFR-1 | Dependencies / style | No new runtime dependency: stdlib Python, vanilla ES5 IIFE JS, DOM built with `C.el` (no `innerHTML` templates), no build step (`console/requirements-dev.txt:1-9`, `index.html:44-75`) | zero new dependencies | AC-61 |
| NFR-2 | Compatibility | Python 3.11-clean (CI runs 3.11 and 3.13; local is 3.14) | CI green on both | CI matrix |
| NFR-3 | Tests | `test_stylesheet.py` and `test_plugins.py` stay green; any new hyphenated class used from JS exists in `styles.css`, no bare single-class selector is defined twice, CSS is inserted mid-file (T-037 forbids appending at the end) | green | AC-62 |
| NFR-4 | Performance | per-request cost of the stamp (measured 0.144 ms for 29 files, 200-run mean, [[T-036-analysis]] §4); growth of the `/api/config` payload | stat only, no file reads (AC-6); ≤ 2 ms per call on this checkout ⚠ [unrealistic?] (proposed, ~14× the measured value; recorded by the verifier, not asserted in CI because wall-time is flaky); response grows by ≤ 100 bytes on today's 2031 ([[T-036-analysis]] §4) ⚠ [unrealistic?] | AC-6, AC-65 |
| NFR-5 | Performance | `/api/prefs` request volume; no new timer and no extra request for the version check | version check rides the existing 15 s `/api/config` call (`app.js:270-275`): 0 new timers, 0 new requests; at most 1 `POST /api/prefs` per client per 250 ms; `GET /api/prefs` once at boot plus once per `prefs_rev` change; handler < 50 ms for a 256 KB file ⚠ [unrealistic?] (proposed) | AC-42, AC-66 |
| NFR-6 | Availability | hydration must not hold the first render hostage when `/api/prefs` is slow | hydration bound 3 s ⚠ [unrealistic?] (proposed; the shared request timeout is 15 s, `core.js:50`), then boot proceeds as for "server unreachable" | AC-43 |
| NFR-7 | Security | prefs are view state writable by any page that can send the CSRF header on an unauthenticated port; the server never reads a pref to decide behaviour; keys are pattern-checked, no user-supplied path, no secret is stored | 0 server modules besides the store, its plugin and `shell_feature` read prefs (AC-36); every write needs `X-Console-Request: 1` (AC-34); every key outside the regex is refused (AC-26) | AC-26, AC-34, AC-36 |
| NFR-8 | Reliability | atomic writes, Windows-safe replace, corrupt file reads as empty, a failed prefs write never breaks the UI | corrupt or missing file → empty set with 0 exceptions (AC-29); concurrent writers → 0 lost keys and valid JSON (AC-30); a failed flush leaves the UI usable (AC-72) | AC-29, AC-30, AC-72 |
| NFR-9 | Change safety | `settings.js`, `app.js`, `index.html`, `shell_feature.py`, `audit.py`, `styles.css` carry uncommitted hunks from other tickets: edits are surgical, the file is re-read before every edit, foreign hunks stay byte-identical, no reformat; the stale-comment fix in `onboarding-wizard.js:4` (a still-untracked file) is a SHOULD done only after that file lands; `audit.ACTIONS` is edited only after its foreign hunk settles ([[T-036-analysis]] §8, G30) | foreign hunks unchanged | AC-63 |
| NFR-10 | Usability / accessibility | notice is `role="status"`, buttons are keyboard-operable, all failures are sentences with the cause | notice has `role="status"` and a keyboard-operable **Reload now** button (AC-10, AC-69); every toast added by this ticket is a sentence naming the key or the cause (AC-76) | AC-10, AC-69, AC-76 |
| NFR-11 | Rollout / documentation | first deploy needs one manual relaunch or hard refresh because open pages have no version check; stated in the release note and verification plan | both artifacts contain the step and how to check it (AC-64) | AC-64 |
| NFR-12 | Platform coverage | verified path is Windows (WebView2); macOS/Linux webviews are not verified | Windows/WebView2 checked by AC-22; macOS and Linux are reported as "not verified" | AC-22 |

Additional ACs for the NFRs:
- [ ] AC-61 [PY] `console/requirements-dev.txt` and any package manifest are unchanged; `console/static/*.js` contain no `=>` and no statement-leading `let`/`const`.
- [ ] AC-62 [PY] `console/tests/test_stylesheet.py` and `console/tests/test_plugins.py` pass with the change.
- [ ] AC-63 [DOC] the verifier diffs each shared file against the pre-build snapshot named in the plan and reports any foreign hunk that moved (manual; not CI).
- [ ] AC-64 [DOC] `T-036-release.md` and `T-036-verification.md` state the one-time relaunch/hard-refresh step and how to check it (quit the app from the tray, relaunch).
- [ ] AC-65 [DOC] the verifier times `ui_version` computation on the shipped static dir (mean of 200 calls) and records it next to the 0.144 ms baseline; the NFR-4 ceiling is reported, not asserted in CI.
- [ ] AC-66 [PY] source: the new heartbeat code adds no `setInterval`/`setTimeout` loop and no request besides the existing `C.get("/api/config")`; `GET /api/prefs` is called from `hydrate()`/`refresh()` only.

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Preferences file `console/.cache/prefs.json` | new | `v`, `rev`, `prefs{key:any JSON}`, `import_closed` | created on first write; reset empties it and sets `import_closed`; deleting the file resets everything | `.gitignore:66`; decision `prefs-store-file-and-api` |
| `ui_version` | new field on `/api/config` | 12 hex | recomputed per call (static half) | `shell_feature.py:60-70` |
| `prefs_rev` | new field on `/api/config` | integer, present only if the prefs provider is loaded | changes on each state change | decision `prefs-live-pickup` |
| `workspace` (SHOULD) | new field on `/api/config` | 12 hex | constant per repo root | decision `sidecar-identity` |
| Reload guard | new, `sessionStorage["console-reload"]` | timestamps of recent automatic reloads | rolling 5-minute window, per browsing session | decisions `reload-policy`, D-14 |
| Import result | new response shape | `imported`, `skipped`, `rejected[{key,reason}]`, `closed` | per call | decision D-16 |
| Legacy `localStorage["console.*"]` | exists | the 16 keys | deleted after import acknowledgement | `core.js:445-458` |
| Hold registry | new, in memory, `Console.holdReload(id, fn)` in `core.js` | id → function returning true while unsaved state exists | per page | decisions `reload-policy`, D-11 |
| `audit.ACTIONS` | changed | adds `prefs.reset`, `prefs.import` | n/a | `console/server/audit.py:44` |
| `plugins.toml` | changed | one `prefs` row | n/a | `console/config/plugins.toml` |

### Data flows
Boot: `/api/config` + `/api/prefs` → in-memory map → render. Write: `set` → map → 250 ms debounce → `POST /api/prefs` → file (+ `rev`). Heartbeat: `/api/config` → compare `ui_version` / `prefs_rev` → notice+idle reload / `refresh()`. Migration: legacy keys → `POST /api/prefs/import` → delete local on ack.

### Retention / archival
Prefs live until Reset or until the file is deleted; no history, no backup. `sessionStorage` guard dies with the browsing session.

## 7. Business Rules

- **BR-1:** in server mode the server is the only store; `localStorage` is not kept as a mirror (CANONICAL).
- **BR-2:** the server never reads a preference to decide behaviour; anything that must act on the server stays in its own validated setting.
- **BR-3:** migration is per client, per key, never overwrites, first import wins; the local copy is deleted only after the server acknowledges.
- **BR-4:** Reset closes the import window, so a stale browser cannot resurrect cleared values.
- **BR-5:** a response that lacks `ui_version` never triggers a reload by itself; a page that booted without a version treats the first later response that has one as changed (D-13).
- **BR-6:** no automatic reload discards typed text, an open drawer/wizard/palette, or an active dictation or read-aloud.
- **BR-7:** a static export stays local and read-only; its manifest gets no new fields.
- **BR-8:** clients send deltas; the same key is last-writer-wins.
- **BR-9:** Reset states its reach in plain words and asks for confirmation.
- **BR-10:** no credential or secret is stored through `C.prefs`.
- **BR-11:** `voice`, `layout`, `chatListHidden` and the rest are shared by the user's decision; the three accepted risks stand (A-5).
- **BR-12:** a tab module registers its own off-DOM unsaved state through `Console.holdReload` (the register-yourself pattern of `Console.tab`, `core.js:22`); `app.js` does not enumerate inputs or modules it does not own.
- **BR-13:** `C.prefs.get` stays synchronous and nothing reads a preference at script-evaluation time (T-037 included).
- **BR-14:** `desktop/sidecar.py` `is_up` stays a pure liveness probe.
- **BR-15:** an explicit **Reload now** click is consent and reloads at once; an automatic reload never overrides the busy rules (BR-6).
- **BR-16:** nothing leaves a browser's `localStorage` without a sentence: skipped, rejected and closed-window outcomes each surface a toast, except an unparsable value, which `C.prefs.get` already treats as absent.

## 8. Edge Cases

- Server restarted with a new route/tab set but unchanged static files → the manifest half changes the stamp (AC-5).
- New JS served by a server that has not restarted: no `/api/prefs` route → local mode, no crash (AC-43).
- A file saved during page load is missed until the next change (accepted residual, decision `ui-version-stamp`).
- `git checkout` or `touch` on a static file causes one harmless reload when idle (stat-based stamp, decision `ui-version-stamp`).
- Two clients race on the same key → last writer wins (BR-8); two clients edit different keys → both kept.
- A prefs write while the server is down stays in memory and is lost on reload (A-5).
- Corrupt `prefs.json` → reads as empty (AC-29).
- Page hidden for days (Tauri hides on close, `main.rs:517-528`) → visibility check on show (AC-9, AC-18).
- The same browser on `localhost` and `127.0.0.1` are two origins: both converge on the server copy (decision `prefs-migration-rule`).
- Skipped import values surface in a toast, never silently (AC-50, AC-76).
- Server unreachable at boot (local mode), a pref is changed, the server returns in the same page lifetime: the page moves to server mode and the value is imported; if the server already has that key it is reported as skipped with the key and value (accepted, G11).
- Two clients toggle different panels within one heartbeat: `panelOpen` is one object, last writer wins; the next refresh converges (accepted, G10).
- `prefs.json` deleted by hand: `rev` returns to 0, clients compare for inequality, pick up the empty set and the import window reopens (BR-4 closes it only through Reset).
- Live pickup hides the tab being shown: the content stays until navigation (AC-77).
- A request in flight when an automatic reload fires is aborted by navigation; the server still completes it (accepted, G13).
- A hidden Tauri window may throttle or freeze timers for days: the `visibilitychange` check on show covers it (AC-18).
- Tray mute (`voice.autoRead`) changed from another client is not pushed to the tray indicator until the app emits its next session state (`agents.js:1534-1543`; accepted with A-5, G25).
- A static file removed between listing and `stat` is skipped; an unlistable static directory omits `ui_version` (AC-67).

## 9. Interactions with Existing Features

(Populated by `challenge-requirements T-036 (overlap/conflict/reuse dimension)`, pass 1.) 23 rows: overlap 12 · conflict 1 · reuse 5 · isolation 5.

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| Connection heartbeat, `app.js:250-276` | overlap: carries `ui_version` and `prefs_rev` on the same call; payload no longer discarded | low | extend |
| Reload on reconnect after a failed boot, `app.js:347-362` | isolation: that path handles a failed boot; the new compare runs only after a good boot | low | isolate |
| `/api/config` and the sidecar probe, `shell_feature.py:53-70`, `sidecar.py:23,110-117` | overlap: new fields; `is_up` ignores the payload | low | extend |
| `C.prefs`, `core.js:444-458` | overlap: implementation replaced behind an unchanged interface; 16 keys, no load-time readers ([[T-036-analysis]] §3) | med | modify |
| `collapsible` / `panelOpen`, `core.js:254-298` | reuse: one object per concern; whole-object last-writer-wins (G10) | low | reuse |
| Settings storage panel, `settings.js:1726-1805` | overlap: retitled, reads `C.prefs.all()`, Reset reaches every client; holds foreign hunks (`:1756-1768`) | med | modify |
| Static export, `export.py:42-104`, `core.js:12,128-143` | isolation: prefs stay in `localStorage`; manifest gets no new field | low | isolate |
| Per-machine JSON settings (`assistant_config.py:39,586-593`, `provider_overrides.py:88-122`, `onboarding_setup.py:45-51`) | reuse: location and pattern; five hand-rolled writers are not refactored | low | reuse |
| `tomlio._replace`, `tomlio.py:314-322` | reuse: Windows-safe replace (private name, same package) | low | reuse |
| Plugin registry and tests, `plugins.toml`, `test_plugins.py:44-90` | overlap: one new row; shipped-registry tests cover it | low | extend |
| Audit, `audit.py:44`, `kanban.py:977`, `work_feature.py:48` | overlap: two new action names; file has a foreign hunk | med | extend |
| [[T-037-summary]] layout and docked drawer (`app.js:17-53`) | overlap: `layout` stored through this contract; "drawer open" busy check must follow the docked panel | med | coordinate |
| Foreign uncommitted hunks in `app.js`, `settings.js`, `index.html`, `shell_feature.py`, `audit.py`, `styles.css` | overlap: same files, concurrent pipelines | high | modify surgically (NFR-9) |
| Tab script load order, `index.html:44-75`, `app.js:382` vs the v0 `ConsoleApp.holdReload` | **conflict** (resolved in iteration 1): `agents.js`/`todos.js` evaluate before `ConsoleApp` exists (CR-1); the registry moved to `Console.holdReload` in `core.js` | high → closed | modify (D-11) |
| `agents.js` `st.drafts` (`:49,1296-1298`), `todos.js` `st.newText` (`:22,200-201`) | reuse: off-DOM text a reload would lose becomes the first holds | low | reuse |
| Setup wizard draft, `onboarding-wizard.js:41,235,239` | reuse: per-keystroke `set` is why writes are debounced; wizard open is a busy state | low | reuse |
| `voice` prefs and tray mute, `voice.js:42-58`, `agents.js:1534-1543,1580`, `desktop-tray.js:7-19` | overlap: shared `voice` couples tray mute to browser read-aloud (accepted A-5, G25) | med | defer |
| `buildNav` listener, `app.js:94-105` | overlap: repeated `rebuildNav` stacks listeners (CR-10); the listener is bound once and pickup rebuilds only on a real change | med | modify (D-18) |
| HUD overlay, `hud.html:141`, `flash.html` | isolation: own inline script, no heartbeat, out of scope | low | isolate |
| `desktop/sidecar.py` `ensure`/`is_up`, `sidecar.rs:7-11` | overlap: attach check (SHOULD); Rust untouched | low | extend |
| Tauri window hide and init script, `main.rs:116-125,517-528` | isolation: no Rust change; reload must re-run the init script (A-7) | med | isolate |
| Chat state, `chat-store.js` | isolation: server-side, re-attaches by `seq` | low | isolate |
| `test_stylesheet.py:65-135` | overlap: a new hyphenated class must exist in CSS, no duplicate bare selector, insert mid-file | low | extend |

## 10. External Dependencies

- Tauri 2 shell on Microsoft Edge WebView2 154.0 for the app (`tauri.conf.json:2`; [[T-036-context-snapshot]] §4); any other browser for tabs. No new external service.
- CI: GitHub Actions `python -m pytest` on Python 3.11 and 3.13 (`.github/workflows/verify.yml:23-48`).
- Sibling tickets: [[T-037-summary]] stores `layout` through this contract; [[T-031-summary]] and the onboarding work edit `settings.js`.

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| Owner / user | Sohail Ali | app and browser show the same UI and keep showing it; decision 2026-10-05 recorded in [[T-036-summary]] | yes (freeze) |
| Consumer | [[T-037-summary]] pipeline | `layout` key contract, no read at script load | no (contract in BR-13, AC-44) |
| Co-editor | [[T-031-summary]] and onboarding pipelines | `settings.js`, `app.js`, `styles.css`, `index.html` edits must not collide | no (NFR-9) |
| Builder / verifier | harness agents | testable criteria; BROWSER criteria cannot run in CI | no |

## 12. Open Questions (mirrored)

Mirrored from `T-036-questions.toml` (`console/kanban.py tracker list T-036 questions`). None is a blocker: each has a recorded default.

- Q1: live pickup of `theme`/`hiddenTabs` across clients — status: open (medium)
- Q2: sidecar workspace check in this ticket — status: open (medium)
- Q3: idle window 30 s — status: open (low)
- Q4: delete the local copy after import — status: open (low)
- Q5: any key that should stay per-device — status: open (low)

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements T-036`. Each must be resolved or explicitly accepted before freeze.) Pass 1 raised 18 findings (critical 2 · major 7 · minor 9); iteration 1 closed 15 by fixing the original section and accepted 3. Pass 2 (after iteration 1) raised 6 more (CR-19..CR-24: major 2 · minor 4), all closed in iteration 2 by fixing the original section. Pass 3 (after iteration 2) raised 1 more (CR-25, minor), closed in iteration 3. Pass 4 raised none. The 3 accepted findings below are the only ⚠ left. Rows and resolutions in [[T-036-critique-report]]; gaps in [[T-036-gap-analysis]].

- ⚠ accepted: [scope-creep] §4 FR-8: the sidecar workspace check is not one of the summary's three scope items — CR-11 — accepted: it traces to contributing factor (b) in [[T-036-summary]] (attach to whatever answers on port 8790), is a SHOULD, Python only, separable, and Q2 asks the owner; the planner may drop it without touching FR-1..FR-7.
- ⚠ accepted: [spof] §4 FR-4: single `prefs.json`, a corrupt file silently resets every client to defaults — CR-14 — accepted: prefs are re-settable view state; the write is atomic, a corrupt file reads as empty instead of failing, and a backup would add a second store (CANONICAL).
- ⚠ accepted: [unstated-assumption] §4 FR-4: the write lock is process-local — CR-18 — accepted: one server per checkout is the supported setup (`sidecar.py:273-292`); writes are atomic, so the worst case is a lost update or a repeated `rev`, never a corrupt file.

## 14. Draft History

See [[T-036-iteration-log]] for per-iteration diff + rationale.

Current iteration: **3** (iteration 1 applied challenge pass 1: D-11..D-20, AC-67..AC-77, BR-15, BR-16; iteration 2 applied pass 2: D-12 revised, D-21, AC-78..AC-80; iteration 3 applied pass 3: AC-81, FR-5 pending-delta rules)

---

## Freeze Checklist (run by `requirements freeze`)

- [x] All `〈TBD〉` placeholders replaced or explicitly deferred (0 left outside the legend and this checklist)
- [x] All ⚠ findings resolved or explicitly accepted with rationale (25 raised; 22 resolved, CR-11, CR-14, CR-18 accepted)
- [x] All blocker open questions answered (no critical or high question exists; Q1-Q5 medium/low stay open by design, each with a recorded default; `tracker blockers T-036` is empty)
- [x] Every FR has at least one testable acceptance criterion (8 FRs, 81 ACs: PY 46 · BROWSER 31 · DOC 4)
- [x] Every NFR has a concrete target or documented reason for absence (12; the proposed numbers in NFR-4..NFR-6 are marked ⚠ [unrealistic?] until the owner confirms)
- [x] Every new/changed entity has a canonical reference or creation plan (§6)
- [x] Out-of-scope list is non-empty
- [x] Stakeholder sign-off recorded (scope/design: owner decision 2026-10-05 in [[T-036-summary]]; freeze-level APPROVED requested in the analyst report)
- [x] `T-036-requirements.md` generated for `requirements stories` consumption

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements-draft]] · [[T-036-context-snapshot]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]]
- [[T-036-requirements]] · [[T-036-critique-report]] · [[T-036-user-stories]] · [[T-036-release]]
- Related: [[T-037-summary]] · [[T-031-summary]] · [[T-004-analysis]] · [[T-002-analysis]]
