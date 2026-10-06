---
tags: [active]
status: Open
ticket: "T-036"
---

# T-036: App and browser in sync: UI version reload and server-side preferences

**Status:** Open  
**Stage:** VERIFY  
**Owner:** Sohail Ali  
**Created:** 2026-10-05  
**Due:**  

## Overview

The user reported on 2026-10-05: "the app and the web app UI is out of sync". Make the desktop app and any browser tab show the same UI, and keep them showing it.

**Decision (user, 2026-10-05):** auto-reload on a new UI version **and** shared preferences through the server.

Scope:
1. **UI version stamp + auto-reload.** The server exposes a version for the served UI (static files and API manifest). The page compares it on the existing 15 s heartbeat (`console/static/app.js:266-270`, which today only flips the live/offline pill) and reloads when the user is idle, with a visible notice. The desktop webview never reloads on its own today.
2. **Server-side preferences.** Theme, hidden tabs, panel open state, agent lane, chat-list fold, voice and the like move from per-browser `localStorage["console.*"]` (`console/static/core.js:444-458`, `C.prefs`) to the server, so the app and every browser share them. Keep the `C.prefs` get/set/del interface unchanged and synchronous (hydrate before first render, write-through after) so callers need no change. The `layout` object that [[T-037-summary]] adds is stored the same way.
3. One-time import of existing localStorage values, a safe fallback to `localStorage` when there is no server (static export `file://`, `console/server/export.py`), and "Reset all preferences" (`console/static/settings.js`, the "Stored in this browser" panel) must clear the server copy too.

Out of scope: Rust shell changes (the page reloads itself), assistant chat state (already server-side), the by-design differences (the app lands on Assistant, shows window chrome, speaks through piper).

## Current State

**TEMPLATE build complete (2026-10-05, builder): 23 of 23 plan tasks `[x]` (00-22), stage stays TEMPLATE until the harness hands off to the verifier.** Full suite after task 22: 1 failed (the foreign `onboarding-wizard.js: .ob-count` stylesheet failure), 2865 passed, 1 skipped; this ticket added the sidecar workspace check (`/api/config` `workspace`, `desktop/sidecar.py` `ensure()` refusal) as its last build tasks, plus the draft [[T-036-release]] (first deploy needs one manual relaunch) and the verification plan in [[T-036-verification]]. **All 31 [BROWSER] acceptance criteria are NOT verified in a browser** (none run; the gate is not a claim they pass); AC-41 is read per CR-31 and flagged for the owner. Details and evidence: [[T-036-progress]] task 22.

**Earlier snapshot (task 07):** TEMPLATE in progress (2026-10-05, builder), 8 of 23 tasks done (00-07):** step zero, the server-side preference store (`prefs_store.py`, `prefs_feature.py`, the `prefs` plugin row, the `prefs.reset`/`prefs.import` audit actions), the UI version stamp (`ui_version.py`; `ui_version` and `prefs_rev` now on `/api/config`, +50 bytes) and the read side of `C.prefs` in `core.js` (in-memory map, deep-clone `get`, local mode unchanged, `hydrate()` with a 3 s bound). Server mode is gated off by `SERVER_PREFS = false` until task 09, so the page behaves exactly as before; no [BROWSER] criterion is verified yet. Baseline suite before the build: 1 failed (a foreign `.ob-count` stylesheet failure from the onboarding work), 2451 passed, 1 skipped. Next: tasks 08-09 (write-through, migration, Reset). See [[T-036-progress]].

**CANONICAL done (2026-10-05, planner):** multi-layer plan in [[T-036-plan]] (23 tasks, 8 phases, 44.5 h build effort; [[T-036-components]], [[T-036-task-breakdown]], [[T-036-implementation-plan]], [[T-036-effort-estimate]]); 8 user stories ([[T-036-user-stories]]); all 81 acceptance criteria mapped to tasks (31 [BROWSER] criteria need a person and stay "not verified in a browser"); 23 risks, 1 high×high, all mitigated; plan critique 12 findings (0 critical), see [[T-036-critique-report]]. Awaiting owner APPROVED to build; first build task is T-036-00 (it moves the lane).

**CLARIFY done (2026-10-05):** requirements frozen at iteration 3 in [[T-036-requirements]] (8 FRs, 81 acceptance criteria, 12 NFRs); 5 non-blocking questions open (Q1-Q5), none critical; hand-off to the planner pending. Freeze-level approval from the owner is requested, not yet given.

**GROUND done (2026-10-05):** root cause CONFIRMED by timeline (app process 08:21:57, last page load 08:21:59, UI edited 09:43-10:02, server restarted 10:03:01) and the app's `localStorage` really lacks `theme`/`hiddenTabs`/`disabledBackends`; no blocking questions; the first deploy needs one manual app relaunch. See [[T-036-analysis]], [[T-036-decision-log]], [[T-036-context-snapshot]]. The leads below were re-verified there.

**Most likely cause (strong, not proven):** the app is a bare webview on the live server with no bundled UI (`desktop/src-tauri/tauri.conf.json:6-8`, `desktop/src-tauri/src/main.rs:219-245`) and nothing ever reloads it; closing the window only hides it (`main.rs:517-528`). Its page loaded 2026-10-05 08:21:59 (WebView2 `History` DB); `console/static/*` was edited 09:43-10:02; the server restarted 10:03. The app therefore runs the old JS/CSS. A browser tab opened later has the new UI. Restarting the app brings it level.

**Contributing:** (a) the app and a browser keep separate localStorage; the app profile held no `theme`, `hiddenTabs` or `disabledBackends`, so it was on defaults (`localhost:8790` and `127.0.0.1:8790` are also different origins); (b) `desktop/sidecar.py:110-117` attaches to anything answering `/api/config` on port 8790 with no repo, version or process-age check; recent launches were all `owned=false`; (c) Python-side code (routes, manifest) is loaded only at server start.

**Ruled out:** bundled/copied UI, a `dist/`, HTTP cache (`httpd.py:94-115` sends `Cache-Control: no-cache, must-revalidate`), service workers, ETags, versioned asset URLs.

**Not verified:** whether the user reloaded the app after 08:21:59; the browser's own localStorage and origin; whether they compare against a static export.

## Links
- Related: [[T-037-summary]] (layout sizes persist through this ticket's preference store; build this first or agree the `C.prefs` contract) · [[T-031-summary]] (also edits `settings.js`)
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-context-snapshot]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-effort-estimate]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]]
- [[T-036-gap-analysis]] · [[T-036-iteration-log]] · [[T-036-requirements-draft]]
