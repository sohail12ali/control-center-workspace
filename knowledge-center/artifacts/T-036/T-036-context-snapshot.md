---
ticket: "T-036"
artifact: context-snapshot
status: draft
created: "2026-10-05"
last_updated: "2026-10-05"
scope: codebase + history
---

# Context Snapshot: T-036

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only — no speculation. Every bullet cites a source. Full evidence, the preference inventory and the root-cause table live in [[T-036-analysis]]; this file indexes them for the requirements draft and does not restate them.

**Command reference:**
- **Created/refreshed by:** `analyze T-036 [scope]`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

**Scopes:** `codebase` (existing code relevant to intent) · `history` (prior tickets / git log / past incidents) · `all` (default)

---

## 1. Intent (echo)

The user reported "the app and the web app UI is out of sync" (2026-10-05) and decided: auto-reload on a new UI version **and** preferences shared through the server ([[T-036-summary]] Overview). Root cause: the desktop app is a bare long-lived webview on the live server that never reloads ([[T-036-analysis]] §1, confirmed by timeline), plus per-browser `localStorage` that the app and a browser do not share (§3).

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Connection heartbeat (15 s, ignores payload) | `watchConnection` | JS only | carry `ui_version` / `prefs_rev` on the same `/api/config` call | `console/static/app.js:250-276` |
| Reload when the server returns after a failed boot | boot `.catch` | JS only | same `window.location.reload()` primitive | `console/static/app.js:347-362` (reload at `:352`) |
| Nav manifest served as `/api/config` | `shell_feature.config` | server plugin | add fields; also the sidecar readiness probe | `console/server/features/shell_feature.py:53-70`, `desktop/sidecar.py:23` |
| Per-machine settings overlay in `console/.cache/` | notify prefs | server plugin, JSON/TOML, `POST /api/notify/prefs` | file location, "view-only, narrowing" stance | `console/server/notify.py:55-102`, `console/server/features/ops_feature.py:78-89` |
| Per-machine JSON settings | assistant settings, provider overrides, wizard state | server module, tmp+`os.replace` | write pattern (no shared helper exists, five copies) | `assistant_config.py:39,586-593`, `provider_overrides.py:88-122`, `onboarding_setup.py:26-27,45-51`, `jobs.py:119-123`, `runs.py:48-63` |
| Windows-safe atomic replace and lock | `tomlio` | server | reuse `_replace`; TOML itself cannot hold prefs | `console/server/tomlio.py:279-335` (limits `:232-271`) |
| Preference store | `C.prefs` | JS kernel | the interface to keep | `console/static/core.js:445-458` |
| Collapsible panel open state in one object | `collapsible` | JS kernel | "one object per concern" convention | `console/static/core.js:254-298` |
| Settings "Stored in this browser" panel | `storage()` | JS tab | must read/clear the server copy | `console/static/settings.js:1726-1805` |
| Static export with `IS_STATIC` fallbacks | `export_static` | server + JS | prefs stay in `localStorage` there | `console/server/export.py:42-45,61-104`, `console/static/core.js:12,128-143` |
| Draft kept across repaints | `st.drafts` | JS tab | model for "unsaved state" a reload would lose | `console/static/agents.js:49,1296-1298` (commit `3688816`) |
| Plugin registration | `PLUGIN` + `plugins.toml` row | server | how a `prefs` plugin is added | `console/server/plugins/base.py:34-47,143-147`, `console/config/plugins.toml` |
| Sidecar attach-or-spawn | `ensure` | `desktop/sidecar.py` | where an identity check would sit | `desktop/sidecar.py:110-117,273-292`; Rust consumer `desktop/src-tauri/src/sidecar.rs:7-11,92-125` |

### Existing patterns to reuse
- Plugin = module with `PLUGIN` + one row in `plugins.toml`; routes via `ctx.get/ctx.post` — `plugins/base.py:143-147`, `plugins.toml` header comments.
- Router-level endpoint tests with the `app` fixture and `call()` — `console/tests/test_ui_endpoints.py:38-75`.
- JS source-regexp tests for wiring (script order, calls present) — `console/tests/test_plugins.py:227-285`.
- Errors as `ValueError` for a 400 — `console/server/httpd.py:141-142`.
- CSRF header on every write — `console/server/httpd.py:187-189`, sent by `console/static/core.js:146`.

### Naming and architectural conventions in play
- Client mirrors server plugins: a tab registers itself, the router knows none by name — `console/static/core.js:1-8`, `console/static/app.js:1-8`.
- "Do not unify" deployment switches with per-user preferences — `console/server/plugins/registry.py:5-13`, `console/config/plugins.toml:12-16`; this ticket changes where the per-user half is stored, so both comments and `console/README.md:571-578` need correcting.
- Stdlib-only runtime, vanilla ES5 IIFE JS, no build step, no JS test runner — `console/requirements-dev.txt:1-9`, `console/static/index.html:44-75`.
- `desktop/sidecar.py` stays importable without `console/` on the path — `desktop/sidecar.py:27-31`.
- Artifact rules — `CLAUDE.md` Layout; `.claude/skills/consolidate/SKILL.md` (flat names, `## Links`).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| [[T-004-analysis]] | Assistant settings backend | Server-side file for anything a headless caller needs; BR-8 "never `localStorage`-only" (`T-004-requirements.md:135`) | server-side per-machine settings are accepted practice here; other Settings panels were left browser-local (`T-004-analysis.md:155-166`) |
| [[T-002-analysis]] | Desktop tray and voice | Mute is `voice.autoRead` (`T-002-analysis.md:49`) | sharing `voice` couples tray mute to browser read-aloud |
| [[T-037-summary]] | Resizable layout (parallel) | Stores `layout` through `C.prefs`; depends on this ticket | contract in [[T-036-decision-log]] `t037-layout-contract` |
| [[T-031-summary]] | Voice assets and devices (parallel) | Also edits `settings.js`; requirements frozen | serialise edits to `settings.js` |

### Relevant commits / PRs
- `3688816` Remove the skill and agent dropdowns; keep a draft from being wiped — origin of `st.drafts` protection.
- `f8ffbc2` Two kinds of agent, inline / @ # references, and a foldable chat list — origin of the `chatListHidden` and `pick*` preferences.
- `6f468c4` Split the Agents tab into a CLI lane and a console lane — origin of `agentLane`.
- `b4d41a8` Start the server even where breakaway from a job object is forbidden — last sidecar spawn change (`sidecar.py:140-171`).
- `9455478` Add workspace check and secret path management — last commit touching `console/static` (2026-10-05 08:18).

### Known incidents / regressions in this area
- 2026-10-05 ([[T-036-summary]]): the desktop app ran a UI loaded at 08:21:59 while `console/static` was edited 09:43-10:02 and the server restarted at 10:03:01; a browser tab showed the new UI. Evidence in [[T-036-analysis]] §1.
- `host.log`: all five launches since 2026-09-17 12:21Z (the last three at 02:49:13Z, 02:50:43Z, 02:51:58Z on 2026-10-05) logged `ensure: sidecar owned=false`, i.e. the app attached to whatever already answered on port 8790 (`console/.cache/desktop/host.log`; earlier launches up to 2026-09-16 17:00Z were `owned=true`).

## 4. External Systems in the Loop

- Tauri 2 shell (`desktop/src-tauri/tauri.conf.json:2`) on Microsoft Edge WebView2 154.0 (process command line): profile at `%LOCALAPPDATA%\com.noble.deliveryconsole\EBWebView` holds the app origin's `localStorage` (LevelDB) and `History`.
- Any other browser the user opens at `localhost:8790` (not inspected).
- CI: GitHub Actions `python -m pytest` on Python 3.11 and 3.13 (`.github/workflows/verify.yml:23-48`); desktop tests job `desktop/tests`.

## 5. Preliminary Risks Spotted

(Not exhaustive — `challenge-requirements` (gaps dimension) expands these.)

- A reload mid-typing loses text: composers and inline edits are DOM-only, the per-chat drafts are in memory (`agents.js:49`), `todos.js:198`. Bites when the idle test misses a surface.
- A reload loop if the version stamp is unstable (two servers answering one port, or a value that changes per call). Needs a guard.
- The first migration consumed by an empty client loses the browser's real values (the app held none of `theme/hiddenTabs/disabledBackends`). Bites with a global "imported" flag.
- A stale browser re-importing old values after a deliberate Reset.
- Per-keystroke `onboardingDraft` writes (`onboarding-wizard.js:235,239`) flooding the server or the audit log if not coalesced; `sendBeacon` cannot carry the CSRF header.
- Shared `voice` couples tray mute (`agents.js:1580`) to browser read-aloud; shared pixel `layout`/`chatListHidden` across window sizes.
- New JS on a server that has not restarted (no `/api/prefs` route) must degrade to local mode, not crash.
- Concurrent edits: `app.js`, `settings.js`, `index.html`, `shell_feature.py`, `audit.py` have uncommitted hunks from other pipelines.
- Python 3.11 compatibility on CI vs local 3.14.

## 6. Open Confirmations

Facts treated as true but **not** verified with a primary source. None blocks drafting; each is labelled in [[T-036-decision-log]] where it matters.

- The live page runs the pre-09:43 JS: inferred from the timeline; the page's heap was not probed (would need devtools or the WebView2 debug port, deliberately not used on the user's live window).
- WebView2 `History` records reload navigations, so "no reload after 08:21:59" is strong but indirect.
- F5 / Ctrl+R works inside the Tauri window (relaunch is the certain route).
- WebView2 reports `document.hidden` for a Tauri-hidden window (`main.rs:517-528`); the immediate-reload-when-hidden rule depends on it.
- The user's browser, its origin (`localhost` vs `127.0.0.1`) and its `localStorage` contents; whether they compare against a static export.
- Whether any other Edge/Chromium WebView2 setting keeps a stale in-memory copy of `index.html` (no ETag or service worker exists; `Cache-Control: no-cache, must-revalidate` is sent).
- A wrong-workspace server has ever been attached (plausible via `.claude/worktrees/T-024/`, not observed).
- Which of the 16 preference keys the user considers per-device rather than shared (the summary lists voice explicitly).

---

## Source Log

Record every command / file / grep lookup used to build this snapshot.

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-05 | Bash | `PYTHONUTF8=1 python console/kanban.py context T-036` | trace-context digest (lane Open, no blockers, 0/2 placeholder tasks, no open trackers) |
| 2026-10-05 | Read | `T-036-summary.md`, `.claude/skills/analyze/SKILL.md`, `requirements/SKILL.md`, `progress-tracker`, `questions` skills | scope, decision, skill contracts |
| 2026-10-05 | Read | `tauri.conf.json`, `main.rs:116-125,205-245,505-540`, `sidecar.rs`, `placeholder/index.html` | webview wiring, close behaviour, Rust handle |
| 2026-10-05 | Grep | `desktop/src-tauri/src` for `reload`, `navigate(`, `eval(` | nothing reloads the webview |
| 2026-10-05 | Read | `httpd.py` (all), `plugins/base.py`, `plugins/registry.py`, `plugins.toml`, `shell_feature.py`, `export.py`, `paths.py` | transport, routing, manifest, export |
| 2026-10-05 | Read | `core.js:1-300,400-500,735-766`, `app.js` (all), `index.html`, `voice.js:1-110`, `composer-pick.js:1-90`, `desktop-chrome.js`, `desktop-tray.js`, `onboarding-wizard.js` (parts), `agents.js` (parts), `settings.js` (parts) | `C.prefs` and boot sequence |
| 2026-10-05 | Grep | `console` for `localStorage\|sessionStorage`, `prefs\.(get\|set\|del)\(`, `prefs`, textarea/input creation, cookie/IndexedDB/serviceWorker | complete key inventory, direct storage use, draft surfaces |
| 2026-10-05 | Grep | `console/server`, `console/static`, `desktop/sidecar.py` for `etag\|last-modified\|if-none-match` | no validators exist |
| 2026-10-05 | Read | `tomlio.py:160-364`, `onboarding_setup.py:1-110`, `assistant_config.py:540-594`, `provider_overrides.py:85-130`, `runs.py:30-75`, `jobs.py:114-126`, `notify.py:55-110`, `audit.py:1-140` | persistence helpers and precedents |
| 2026-10-05 | Read | `desktop/sidecar.py` (all), `desktop/tests/test_sidecar.py` (outline) | attach logic and test patterns |
| 2026-10-05 | Read | `console/tests/test_plugins.py`, `test_stylesheet.py`, `test_ui_endpoints.py:1-120`, `conftest.py`, `.github/workflows/verify.yml:1-48`, `pytest.ini` | test constraints and CI matrix |
| 2026-10-05 | Bash | `Get-CimInstance Win32_Process` filtered to the desktop exe, WebView2 and `kanban.py serve` | process creation times (app 08:21:57; server 10:03:01) |
| 2026-10-05 | Bash | `ls --time-style=full-iso console/static` | static file mtimes (09:43-10:02) |
| 2026-10-05 | Bash | copy WebView2 `History` to the scratchpad, `sqlite3` read-only on the **copy** | page load times (last `/` load 08:21:59) |
| 2026-10-05 | Bash | copy WebView2 `Local Storage/leveldb/*.log` to the scratchpad, regex scan of the **copy** | app `localStorage` keys (no theme/hiddenTabs/disabledBackends) |
| 2026-10-05 | Bash | `grep` of `console/.cache/desktop/host.log`; `cat console/.cache/desktop/bridge.json` | `owned=false` launches (bridge file holds a bearer token; it was read for the pointer only and is not recorded anywhere) |
| 2026-10-05 | Bash | Python timing of stat+sha256 over `console/static`; `GET /api/config` and `GET /app.js` on `127.0.0.1:8790` | version-stamp cost 0.144 ms; response size 2031 B; live headers |
| 2026-10-05 | Bash | `git check-ignore -v console/.cache/assistant/settings.json`; `git log --grep`; `git status` | gitignore line 66, prior commits, dirty files |
| 2026-10-05 | Read | `T-037-summary.md`, `T-031-summary.md`, `T-004-analysis.md:155-166`, `T-002-analysis.md:45-52`, `wiki/desktop-assistant.md:276-292` | sibling tickets and prior decisions |
| 2026-10-05 | Read/Grep/Bash | `app.js:1-250,240-385`, `index.html:40-80`, `core.js:1-120,120-180,250-300,435-465,508-522`, `settings.js:1-14,55-125,1715-1805`, `about.js:150-165`, `console/README.md:560-590`, `desktop-tray.js`, `voice.js` grep, `agents.js`/`todos.js` greps, `plugins/base.py:28-150`, `shell_feature.py` (all), `export.py:36-105`, `httpd.py:85-260`, `tomlio.py:275-335`, `sidecar.py:15-330`, `audit.py:40-135`, `test_plugins.py`, `test_ui_endpoints.py:36-75`, `main.rs:110-246,512-542`, `tray.rs:128-142`, `onboarding-wizard.js:36-56,195-245`; `grep` of `.value =` and `=>` over `console/static` | `requirements enrich` (2026-10-05): confirmed anchors still hold on the current tree; found script-order conflict for `holdReload`, programmatic `.value =` fills in Settings, `buildNav` listener stacking, `audit.ACTIONS` consumers, extra stale statements (`settings.js:4-5`, `about.js:158-159`, `core.js:256-258,444`) |

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements-draft]] · [[T-036-context-snapshot]] · [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-critique-report]]
- Related: [[T-037-summary]] · [[T-031-summary]] · [[T-004-analysis]] · [[T-002-analysis]]
- [[T-036-requirements]]
