---
ticket: "T-036"
artifact: analysis
---

# Analysis: T-036

## Context

User report (2026-10-05): "the app and the web app UI is out of sync". Decision (user, same day): auto-reload on a new UI version **and** preferences shared through the server ([[T-036-summary]]). This GROUND pass re-verified the summary's root-cause leads against the repo and the machine, and inventoried everything the preference move touches. Descriptive only: no code was changed. Decisions and defaults are in [[T-036-decision-log]]; the grounding facts for requirements are in [[T-036-context-snapshot]].

## Current State

### 1. Root cause: CONFIRMED (mechanism); two links in the chain are inferred, not observed

| Claim | Evidence |
|---|---|
| The app is a bare webview on the live server, no bundled UI | `desktop/src-tauri/tauri.conf.json:6-8` (`frontendDist: ./placeholder`) and `:14` (`windows: []`); the placeholder is a 148-byte "Starting…" page (`desktop/src-tauri/placeholder/index.html`); the window is `WebviewUrl::External(handle.url)` at `desktop/src-tauri/src/main.rs:221`, with an init script that only adds `in-shell` (`main.rs:116-125`, `:226`) |
| Nothing ever reloads it | no `reload`/`navigate(` anywhere in `desktop/src-tauri/src` (grep: only `eval` in `hud.rs:117`, `tray.rs:137`); closing the window only hides it (`main.rs:517-528`), so the page lives until the process is quit |
| The page does not notice a new UI | heartbeat fetches `/api/config` and ignores the payload (`console/static/app.js:266-276`); `/api/config` returns only `title, subtitle, tabs, boards, stale_days` (`console/server/features/shell_feature.py:60-70`; live GET returned 2031 bytes with exactly those keys) |
| HTTP cache is not the cause, and there is no version signal either | static responses carry `Cache-Control: no-cache, must-revalidate` and nothing else of interest (`console/server/httpd.py:107-114`; live `GET /app.js` headers confirmed); grep for `ETag/Last-Modified/If-None-Match` over `console/server`, `console/static`, `desktop/sidecar.py` finds nothing; `index.html` has no `?v=` URLs (`console/static/index.html:13,45-74`); no service worker (grep) |
| The app's document predates the UI edits | App process `delivery-console-desktop.exe` PID 33828 created **08:21:57**; WebView2 History (copied, opened read-only): last load of `http://127.0.0.1:8790/` at **08:21:59** (visit 418), earlier loads 08:20:44 and 08:19:14, **no later load of `/`**; later visits are in-page `#hash` navigations up to 11:52:11 (visit 430), so the app was in use on that same document for ~3.5 h. Static edits: `index.html` 09:43:08, `app.js` 09:43:11, `overview.js` 09:43:11, `styles.css` 09:43:40, `settings.js` 09:46:44, `onboarding-wizard.js` 10:02:27 (a file that did not exist when the page loaded) |
| The server was restarted after the edits | Python server PID 5792 created **10:03:01** (`kanban.py serve --host 127.0.0.1 --port 8790`); Python-side routes and manifest are built once at start (`httpd.py:299`, `plugins/registry.py:78-102`) |
| Why the app attached instead of starting its own server | `host.log` lines for 02:49:13Z, 02:50:43Z, 02:51:58Z (= 08:19, 08:20, 08:21 IST): `ensure: sidecar owned=false`; `sidecar.ensure` returns on any answer from `/api/config` (`desktop/sidecar.py:273-280`, `is_up` at `:110-117`) |
| A browser tab opened later has the new UI | consistent with the above; the browser itself was **not** inspected |

Contributing factor (a), separate localStorage, is also confirmed for the app: its origin is `http://127.0.0.1:8790` (History URLs; `sidecar.server_url` uses the loopback view host, `sidecar.py:100-107`), and the WebView2 LevelDB log (copied, scanned) holds only `agentLane`, `voice`, `modelByBackend`, `panelOpen`, `chatListHidden`. There is **no** `theme`, `hiddenTabs` or `disabledBackends` key and no deletion marker for them, so the app was on defaults for those.

**Not observed (inferred):** (i) the JavaScript heap of the live page was not inspected, so "it runs the old JS" follows from the timeline, not from a probe; (ii) WebView2 History *probably* records a reload as a new visit, so "no reload after 08:21:59" is strong but indirect; (iii) the user's browser (which one, which origin `localhost` vs `127.0.0.1`, its localStorage) and whether they compare against a static export. None of these changes the fix.

### 2. Consequence for rollout: an already-open page cannot adopt the fix

The old JS has no version check, and the only existing reload-on-reconnect (`app.js:352`) runs only when **boot failed**. So the first time this ships, the app (and any open tab) needs one manual relaunch or hard refresh. Quit from the tray and relaunch is certain (the window's `Destroyed` path stops an owned sidecar only, `main.rs:529-540`); F5/Ctrl+R in the webview is **unverified**.

### 3. Preference inventory (`C.prefs`, `console/static/core.js:445-458`)

`get` parses `localStorage["console."+key]` per call, `set` writes JSON, `del` removes; all synchronous, exceptions swallowed. 16 keys are in use:

| Key | Shape | Default | Read | Written |
|---|---|---|---|---|
| `theme` | `"system"\|"light"\|"dark"\|"vsdark"\|"vslight"` (`settings.js:18-24`) | `"system"` | `app.js:337`, `settings.js:61` | `settings.js:80` |
| `hiddenTabs` | `string[]` tab ids | `[]` | `app.js:76,109`, `settings.js:97,111` | `settings.js:101` |
| `disabledBackends` | `string[]` backend ids | `[]` | `agents.js:1449`, `settings.js:185,212,251` | `settings.js:188` |
| `panelOpen` | `{panelId: bool}` (one object per concern, `core.js:254-258`) | `{}` | `core.js:261,276` | `core.js:278` |
| `agentLane` | `"cli"\|"api"` | `"cli"` | `agents.js:1457` | `agents.js:90` |
| `chatListHidden` | bool | `false` | `agents.js:1498,1503`, `settings.js:616` | `agents.js:132`, `settings.js:619` |
| `modelByBackend` | `{backendId: modelId}` | `{}` | `agents.js:154,159` | `agents.js:161` |
| `voice` | `{autoRead,announce,rate,pitch,voice,interim}`, merged over defaults (`voice.js:42-54`) | defaults | `voice.js:53` (`prefs()`; also `desktop-tray.js:12-13`, `agents.js:982,996,1361,1378`) | `voice.js:58` via `Voice.setPrefs` (`agents.js:1363,1380,1580`) |
| `hideOnboarding` | bool | `false` | `overview.js:47`, `settings.js:1738` | `overview.js:106`; `del` `settings.js:1748` |
| `onboardingOpen` | bool | `true` | `overview.js:50` | `overview.js:91` |
| `workAuditOpen` | bool | `false` | `work.js:161` | `work.js:207` |
| `pickSkills`, `pickAgents`, `pickFiles` | bool | `true` | `composer-pick.js:47` | `settings.js:616-619` (generic `toggle(key,…)`) |
| `onboardingDraft` | object `{step,name,title,slug,enabled{},editors[],backend,model,workBackend,workModel}` | `null` | `onboarding-wizard.js:447` | `onboarding-wizard.js:41` (also on **every keystroke**, `:235,:239`); `del` `:200` |
| `layout` (planned, [[T-037-summary]]) | one object | n/a | n/a | n/a |

- **Load-time reads that would break "hydrate before first render": none.** Every call is inside a function that runs after boot (render, event handler, or the boot `.then`). The first read is `app.js:337` (`applyTheme`) inside the `/api/config` `.then` (`app.js:329-346`), so hydration only has to finish before that line. `agents.js` reads at `:1449-1503` are inside the post-fetch `.then`. `ConsoleVoice.prefs()` is read lazily (`voice.js:96,180`).
- **Direct `localStorage` use that bypasses `C.prefs`:** only `settings.js:1729-1731` (key listing), `:1778` (value display), `:1787` (reset). Everything else (`onboarding-wizard.js:4`, `export.py:49`, `README.md:576`) is a comment or doc.
- **Callers mutate returned objects** (`core.js:276-278`, `agents.js:159-161`): today each `get` returns a fresh parse, so an in-memory cache must return a deep clone to keep that behaviour.
- Single caller of `del` for a real key besides the draft: `hideOnboarding` (`settings.js:1748`).
- `hud.html` and `flash.html` do not load `core.js` and never touch prefs (grep: one inline `<script>`, `hud.html:141`).

### 4. Server surface to build on

- Routing: a plugin is a module with `PLUGIN = Plugin(...)` plus one row in `console/config/plugins.toml`; routes are regexes registered with `ctx.get/ctx.post` (`plugins/base.py:143-147`); unknown `/api/` paths 404, other GETs fall back to static (`httpd.py:117-130`). Handler `ValueError`/`KeyError` becomes 400 (`httpd.py:141-142`); a POST success is sent as **201** (`httpd.py:154`).
- Writes require `X-Console-Request: 1` (`httpd.py:187-189`); `C.post` sets it (`core.js:142-158`). `navigator.sendBeacon` cannot set a custom header, so it cannot be used for a flush on page hide; `fetch(..., {keepalive:true})` can. The request body length is read with **no cap** (`httpd.py:190`), so size limits must be enforced in the handler.
- Per-machine storage: `console/.cache/` is gitignored (`.gitignore:66`, `git check-ignore` confirmed for `console/.cache/assistant/settings.json`). At least five modules each hand-roll "JSON to `.tmp` then `os.replace`": `onboarding_setup.py:45-51`, `assistant_config.py:586-593`, `provider_overrides.py:115-122`, `jobs.py:119-123`, `runs.py:48-63` (only the last retries on Windows `PermissionError`). `tomlio` has the Windows-hardened `_replace` (`tomlio.py:314-322`) and lock (`:279-297`), but **cannot store prefs**: `dumps` handles one level of tables with scalar/list values and stringifies anything deeper (`tomlio.py:232-271`), and TOML has no `null` (`onboardingDraft` default, nested `enabled{}`).
- There is no shared JSON helper, so the CANONICAL gate has nothing to reuse except `tomlio._replace`; see [[T-036-decision-log]] `prefs-store-file-and-api`.
- Precedent for server-side per-machine settings: notify prefs (`notify.py:55-102`, `ops_feature.py:78-89`, with the "narrowing only" safety stance), assistant settings (`assistant_config.py:39`), provider overrides (`provider_overrides.py:88-122`); [[T-004-analysis]] (l.159-166) and T-004 BR-8 record "never `localStorage`-only" for anything a headless caller needs.
- Version-stamp cost measured: stat of the 29 files in `console/static` (flat directory) hashed in **0.144 ms** (200-run mean). `/api/config` is 2031 bytes.

### 5. Reload-safety surfaces (what a reload would destroy)

- Text the user may be typing: `agents.js:690` (new-chat prompt, mirrored to `st.form.prompt`), `:1278` (live composer; per-chat drafts held **off-DOM** in `st.drafts`, `agents.js:49,1296-1298`), `assistant.js:101` (Assistant composer, DOM only), `board.js:321` (inline edit committing on blur) and `:449` (add tracker item), `todos.js:198` (new todo, `st.newText`), `palette.js:171`, `onboarding-wizard.js:217,250` (draft persisted via `C.prefs`), many `settings.js` text inputs (`:323-334,489-496,987,1659-1662,1870`), header search (`index.html:25`).
- Other transient state: the shared drawer (`app.js:17-53`), the setup wizard scrim, an active dictation (`voice.js` `state.listening`) or read-aloud, in-memory Vault graph sliders (`vault.js:586`, `st.forces`).
- Not at risk: assistant/agent chat content and approvals are server-side and re-attach by `seq` after a reload (`chat-store.js` header comment); the current tab survives via the URL hash (`app.js:134-136,341-343`).
- A hidden window still runs timers: `main.rs:517-528` hides rather than closes, so the page can sit for days; Chromium throttles background timers, so a visibility-change check is needed on top of the 15 s interval (assumption: WebView2 reports hidden state for a Tauri-hidden window, **unverified**).

### 6. Static export (`file://`)

`export.py:42-45` injects `window.__STATIC__`; `Console.IS_STATIC` (`core.js:12`) short-circuits `get` to `__CONSOLE_DATA__` (`:128-137`), makes `post` reject (`:143`), and stops the heartbeat (`app.js:267`). The exported manifest is built separately from `/api/config` (`export.py:61-83`), so it carries no new fields. Settings and About render from the manifest and localStorage (`export.py:49`), so prefs must stay in `localStorage` there, and the Settings panel is shared code between the two modes. Assets copied: `*.html *.js *.css *.png` (`export.py:90`), the same set the version stamp should cover.

### 7. Statements that become false when prefs move to the server

`settings.js:91-92` (theme "on this browser only"), `:145-147` (tabs "Stored in this browser"), `:153-159` and `:264-267` (agent CLIs), `:612` (composer), `:1770` (panel title), `:1794` ("Affects this browser only. No server data is touched."), `:1800-1803` (help); `about.js:33`; `console/README.md:573-578` (the "two off switches" table: "One person's browser" / "`localStorage`"); `console/config/plugins.toml:14-16`; `console/server/plugins/registry.py:9-10`; `onboarding-wizard.js:4` (comment). `export.py:49` stays true (static mode).

### 8. Conflict map and test constraints

- Uncommitted work in files this ticket must edit (git status at start): `console/static/app.js` (+13: boot `.then` `:346`, `setTitle` `:371-380`, export `:382-384`), `console/static/settings.js` (+90, including inside `storage()` the new "Setup wizard" row `:1756-1768`), `console/static/index.html` (the `onboarding-wizard.js` tag `:71-72`), `console/server/features/shell_feature.py` (+6: `display_title`), `console/server/audit.py`. Pipelines for T-031, T-037 and onboarding edit the tree concurrently; [[T-037-summary]] also wants `splitter.js`, `settings.js` and `styles.css`.
- Tests are Python only; CI runs `python -m pytest` on Python 3.11 and 3.13 (`.github/workflows/verify.yml:23-48`), so code must be 3.11-clean (local is 3.14). No JS runner exists (Node 24 is on this machine, but it is not a declared dependency and CI does not install it).
- Patterns to extend: router-level `call()` helper and `app` fixture (`console/tests/test_ui_endpoints.py:38-75`), shipped-registry checks (`test_plugins.py:44-90`, which will cover a new plugin row for free), JS source-regexp checks (`test_plugins.py:227-285`), stylesheet rules (`test_stylesheet.py:65-135`: no duplicate bare single-class selector, every hyphenated class used in a JS `class:"…"` literal must exist in `styles.css`), sidecar tests (`desktop/tests/test_sidecar.py:135-165`, which spawn a real server). No test instantiates `httpd.Handler`, so header/static behaviour has no existing test pattern.

## Key Findings

- **The cause is a missing mechanism, not a stale cache:** a long-lived webview never re-fetches, and nothing tells it the UI changed. Significance: the fix belongs in the page (JS), not Rust, and not in HTTP caching.
- **A cheap, deterministic version stamp exists:** names + sizes + mtimes of the 29 static files hash in 0.144 ms, so it can ride the existing `/api/config` heartbeat with no cache. Significance: no new endpoint, no new timer, no extra request.
- **The first deploy needs one manual relaunch.** Significance: must be in the release note and verification plan; otherwise "it still doesn't update" is expected, not a bug.
- **Prefs hydration has no load-time blockers:** all 16 keys are read after boot; the single gate is `app.js:337`. Significance: the synchronous `C.prefs` interface can be kept exactly; only `app.js` boot and `settings.js` `storage()` change.
- **`onboardingDraft` writes per keystroke and the heartbeat fetches every 15 s:** write-through must be coalesced and flushed on page hide with `fetch keepalive` (not `sendBeacon`, which cannot carry the CSRF header). Significance: naive write-through would POST per keypress.
- **TOML cannot hold these values** (`tomlio.py:232-271`); JSON with the established tmp+replace pattern is the fit, and the Windows-safe replace already exists in `tomlio._replace`. Significance: do not use `tomlio.atomic_write`; do not add yet another hand-rolled writer without saying why.
- **Migration has a real hazard:** the app held no `theme/hiddenTabs/disabledBackends`, so the browser holds the meaningful values. A single global "import once" flag consumed by the first (empty) client would discard them; a "reset" that a stale browser can re-import would resurrect old values. Significance: the rule must be per client, per key, never overwriting, and closed by Reset.
- **Reset now has a wider blast radius** (every client), and several help texts and the README table assert the opposite of the new behaviour (§7). Significance: wording and a confirm are part of the change, not polish.
- **`voice` is shared by decision, with a side effect:** the tray mute writes `voice.autoRead` (`agents.js:1580`, [[T-002-analysis]] l.49), so muting in the app would mute browser read-aloud too. Significance: accepted risk, flagged in the decision log, not a question (the user listed voice explicitly).
- **The sidecar will attach to any server on the port** (`sidecar.py:279-280`); `.claude/worktrees/T-024/` holds a full copy of the repo, so a wrong-workspace attach is plausible but **not observed**. Significance: optional hardening, kept separable.
- **The HUD overlay (`hud.html`) is a second long-lived page** that never reloads and has no heartbeat. Significance: out of scope for this ticket; stated so it is not assumed covered.

## Research

In-repo only; no external research was needed. Precedents: [[T-004-analysis]] (server-side settings, BR-8), `notify.py:55-102` (committed config plus gitignored overlay, "narrowing only"), `assistant_config.py:39,586-593`, `provider_overrides.py:88-122`, `tomlio.py:279-335`, `app.js:352` (reload on reconnect after failed boot), `agents.js:49,1296-1298` (existing per-chat draft protection across repaints, commit `3688816`). Machine evidence: process creation times via `Get-CimInstance Win32_Process`; WebView2 `History` and LevelDB `000003.log` read from **copies** in the scratchpad, never the originals; `GET /api/config` and `GET /app.js` against the live server.

## Recommended Path

Ship in two independent halves. First the version stamp: the server adds `ui_version` (hash of static names, sizes, mtimes plus a once-per-process digest of the tab and route manifest) to `/api/config`; the page records it at boot, compares on every heartbeat, on reconnect and on becoming visible, shows a persistent notice, and reloads only when idle with no dirty field, open drawer or wizard, active dictation, or registered unsaved draft, guarded against loops. Second the preference store: a new `prefs` plugin keeps one JSON file in `console/.cache/` behind `GET/POST /api/prefs` (plus import and reset), `C.prefs` stays synchronous against an in-memory copy hydrated in the boot chain before `applyTheme` and written through in coalesced deltas, `localStorage` remains the fallback for static export or an unreachable or older server, a per-client move-import (first import wins per key, never overwrites, closed by Reset) carries existing values across, the heartbeat carries `prefs_rev` so a change in the browser reaches the app, and Settings wording, a confirm on Reset and the stale docs are corrected. Optionally, make `desktop/sidecar.py` refuse to attach to a different workspace's server (Python only). Land the prefs contract before [[T-037-summary]] builds on `layout`, sequence `settings.js`/`app.js` edits after the other pipelines commit, and tell the user to relaunch the app once. No blocking open questions; confirm-at-review items are listed in [[T-036-decision-log]].

## Links
- Related: [[T-037-summary]] (stores `layout` through this contract) · [[T-031-summary]] (also edits `settings.js`) · [[T-004-analysis]] · [[T-002-analysis]]
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-context-snapshot]] · [[T-036-requirements-draft]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]]
- [[T-036-components]] · [[T-036-implementation-plan]]
