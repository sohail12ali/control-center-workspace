---
ticket: "T-036"
artifact: release
status: draft
---

# Release: T-036

**Produced by:** `builder` (draft, task T-036-21); the `deployer` finalises it. **Status: draft, not shipped.** Nothing here was committed, pushed or published, and no [BROWSER] criterion has been run in a browser ([[T-036-verification]] § Verification plan). **Sources:** [[T-036-verification]], [[T-036-progress]], [[T-036-decision-log]]

| Field | Value |
|-------|-------|
| Shipped | not shipped (draft written 2026-10-05) |
| Sub-project(s) | control-center-workspace (`console/`, `desktop/sidecar.py`); no Rust change |
| Verify gate | [[T-036-verification]] (PY results to be filled by the verifier; every [BROWSER] row "not verified in a browser") |

## What shipped

- **UI version stamp.** `GET /api/config` carries `ui_version` (12 hex over the stat of `console/static` plus the tab and route table). The page compares it on every heartbeat, on reconnect and when it becomes visible, and shows a "new version is ready" notice with **Reload now**; it reloads itself only when idle (30 s) and not busy, at most 3 times in 5 minutes. *Not verified in a browser (source-level only).*
- **Shared preferences.** New `prefs` plugin: one server file `console/.cache/prefs.json` behind `GET/POST /api/prefs`, `/api/prefs/import`, `/api/prefs/reset`; `C.prefs` keeps its synchronous interface over an in-memory copy, hydrates before first render, writes through (250 ms debounce), imports each browser's old `console.*` keys once, and picks up `theme` and `hiddenTabs` from another client within a heartbeat. `/api/config` also carries `prefs_rev`. *Not verified in a browser (source-level only).*
- **Settings and wording.** "Saved preferences" panel with a confirmed **Reset all preferences**; every statement that said "this browser only" corrected (`settings.js`, `about.js`, `console/README.md`, `plugins.toml`, `registry.py`). *Not verified in a browser (source-level only).*
- **Reload safety.** `Console.holdReload` registry in `core.js` (Agents drafts and the new-todo field register holds); loop guard in `sessionStorage["console-reload"]`. *Not verified in a browser (source-level only).*
- **Sidecar workspace identity (SHOULD, Q2 default "include").** `/api/config` carries `workspace` (12 hex of the normalised real repo root, never the path); `desktop/sidecar.py` `ensure()` refuses to attach to a server whose `workspace` differs. Python only; absent field attaches as before.

## First deploy needs one manual relaunch (NFR-11, AC-64)

The pages that are open today (the desktop app window and any browser tab) run JavaScript that has **no version check**, so they cannot adopt this fix by themselves. Once, in this order:

1. **Restart the console server**, so it serves `/api/prefs`, `ui_version`, `prefs_rev` and `workspace`. Until it restarts, new pages run in local mode (below).
2. **Quit the desktop app from the tray** (the tray menu's quit entry, not the window close button, which only hides the window, `main.rs:517-528`) and **start it again**. Pressing F5 or Ctrl+R in the Tauri window may also work; that is **UNVERIFIED** (assumption A-7).
3. **Hard-refresh every open browser tab** (Ctrl+Shift+R, or Ctrl+F5).

After that, later UI changes are picked up by the page itself.

**How to check it took:** `GET /api/config` shows `ui_version` (12 hex), `prefs_rev` and `workspace`; Settings -> "Saved preferences" says "Shared by the desktop app and every browser tab on this machine. Kept on the server in console/.cache/prefs.json; not committed."; then edit any file in `console/static` (or `touch` it) and the open page shows the notice within one 15 s heartbeat and reloads once you pause for 30 s. *The Settings text is the shipped `MODE_SERVER` string (`settings.js:2392`); the notice and reload steps are not verified in a browser.*

**Interim state (until every client is relaunched):** a page that was relaunched but is served by an un-restarted server has no `/api/prefs`, so it runs in **local mode** (the old per-browser `localStorage` behaviour) and shows no notice; when the server is restarted with the field, that page sees a version it did not boot with, shows the notice and reloads when idle (AC-68), then runs in server mode. An old, un-relaunched page keeps its own `localStorage` and never joins the shared copy. *Not verified in a browser (source-level only).*

## Known limits and accepted risks

- All 16 preference keys are shared (Q5 default: none per-device), so: muting from the tray also mutes browser read-aloud (`voice`); the pixel `layout` (T-037) and `chatListHidden` are shared across window sizes and across devices that reach the console over a network.
- A preference written while the server is down is kept in memory and sent when it returns; if the page is reloaded first, the write is lost (AC-72).
- No automatic reload when `sessionStorage` is blocked (the loop guard cannot count, so it fails safe); the notice and **Reload now** still work.
- A change made in two clients to the same object-valued key (`layout`, `panelOpen`) is last-writer-wins as a whole.
- Migration deletes each browser's own `console.*` keys after the server accepts them (Q4 default), so one source of truth; rolling the UI back shows defaults while the data stays in `prefs.json`.
- `console/static/onboarding-wizard.js:4` still says drafts live in "localStorage": that file is another pipeline's untracked file, so this ticket did not edit it (SHOULD, after it lands).
- The comment above T-031's `assistant()` in `settings.js` ("the only panel here that writes SERVER state...") is loosely stale after this change; left alone because it sits in T-031's edit area. No test or AC covers it.
- Assumptions not verified: A-6 (WebView2 reports `document.hidden` for a Tauri-hidden window), A-7 (`location.reload()` works in the Tauri webview and the Rust init script runs again), A-8 (the live page heap was never probed), the 64 KiB `keepalive` budget (recalled, not re-verified).

## Not covered

- The HUD overlay (`hud.html`, `flash.html`) has its own inline script and no heartbeat: it stays stale until its next relaunch.
- macOS and Linux webviews are not verified (NFR-12).
- Python 3.11 was not run locally (`py -3.11` absent); the CI matrix is the evidence.
- A server older than the current Python code is not detected or restarted by this ticket.

## Measured numbers (AC-65, recorded not asserted)

- `ui_version` compute time: mean of 200 `UiVersion.value()` calls on the real `console/static` (30 matching files): **1.31 ms** (first measurement; three further runs 1.23, 1.11, 1.31 ms mean, 0.75-0.79 ms min). The analyst baseline was 0.144 ms for 29 files, so this machine now reads about 8-9 times higher. Both figures are below the NFR-4 ceiling of 2 ms, which is an analyst proposal (labelled unrealistic-until-confirmed), not a stakeholder requirement; the difference is likely machine load (other pipelines building concurrently) and the measurement method, which I did not establish. See [[T-036-progress]] task 22 for the full record.
- `/api/config` growth for the three new keys: 69 bytes (1290 -> 1359 bytes on this checkout), under the proposed 100-byte ceiling.

## Commands run

| Sub-project | Skill / command | Result |
|-------------|------------------|--------|
| control-center-workspace | `PYTHONUTF8=1 python -m pytest -o addopts="" -q` | see [[T-036-progress]] task 22 |
| (deployer) | publish | not run; nothing shipped |

## Artifacts / paths produced

- New: `console/server/prefs_store.py`, `console/server/features/prefs_feature.py`, `console/server/ui_version.py`, tests `console/tests/test_{prefs_store,prefs_routes,ui_version,config_payload,prefs_client_source,ui_constraints,prefs_wording,reload_source}.py`.
- Changed: `console/static/{core,app,settings,about,agents,todos}.js`, `console/static/styles.css`, `console/server/{audit.py,plugins/registry.py,features/shell_feature.py}`, `console/config/plugins.toml`, `console/README.md`, `desktop/sidecar.py`, `desktop/tests/test_sidecar.py`. Exact per-task ranges: [[T-036-progress]].
- Runtime file (gitignored, created on first write): `console/.cache/prefs.json`.

## Rollback

- Set `enabled = false` on the `prefs` row in `console/config/plugins.toml` and restart: the routes disappear and every client falls back to its own `localStorage` (local mode).
- Delete `console/.cache/prefs.json` to reset everyone (equivalent to Reset all preferences, except the import window is reopened).
- Each browser's own `console.*` keys were deleted after import (Q4 default): an old UI shows defaults while the data stays in `prefs.json`.
- To drop the sidecar check alone, remove task 19's payload line and task 20's `served_workspace` check in `ensure()`; nothing else depends on them.

## Links
- [[T-036-summary]] · [[T-036-requirements]] · [[T-036-plan]] · [[T-036-implementation-plan]] · [[T-036-task-breakdown]] · [[T-036-progress]] · [[T-036-decision-log]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]]
- [[T-036-analysis]] · [[T-036-components]] · [[T-036-gap-analysis]] · [[T-036-requirements-draft]] · [[T-036-user-stories]]
