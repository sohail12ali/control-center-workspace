---
ticket: "T-036"
artifact: user-stories
created: "2026-10-05"
---

# User Stories: T-036

Extracted from the frozen [[T-036-requirements]] (iteration 3). AC ids are the stable ids used there; every one of the 81 appears in exactly one story's list below (cross-cutting NFR criteria sit in US-8). Task ids (`T-036-NN`) are those of [[T-036-plan]]; component ids (`K*` server, `U*` UI, `X*` docs/verification) are those of [[T-036-components]].

**Created by:** `requirements T-036 stories` · **Validated by:** `validate-artifacts T-036 links` · **Verified by:** `validate-artifacts T-036 links`

Verification tags: **[PY]** pytest (46) · **[BROWSER]** a person or driven browser, never CI (31) · **[DOC]** the verifier reads an artifact (4).

## Stories

### US-1: The open app and every browser tab pick up a new UI by themselves
**As a** person using the desktop app or a browser tab for days
**I want** the page to notice that the served UI changed and to tell me
**So that** the app and the web app never show different UIs again.

**Acceptance Criteria:**
- [ ] AC-1 [PY] · AC-2 [PY] · AC-3 [PY] · AC-4 [PY] · AC-5 [PY] · AC-6 [PY] · AC-7 [PY] · AC-67 [PY] (server stamp, FR-1)
- [ ] AC-8 [PY] · AC-9 [PY] · AC-69 [PY] (page compare, source checks, FR-2)
- [ ] AC-10 [BROWSER] · AC-11 [BROWSER] · AC-12 [BROWSER] · AC-13 [BROWSER] · AC-68 [BROWSER] (notice behaviour, FR-2)

**Business Rules:** BR-5 (no version means no reload, except absent-then-present), BR-7 (static export untouched), BR-15 (Reload now is consent).
**Edge Cases:** restart with changed routes but unchanged files (AC-5); new JS on an un-restarted server runs in local mode and moves to server mode after restart (AC-68); file saved during page load missed until the next change (accepted); a vanished file mid-sweep (AC-67).
**Related Components:** K4 `ui_version.py`, K5 `shell_feature.py`, U4 `app.js` compare + notice, U7 `styles.css`.
**Related Tasks:** T-036-05, T-036-06, T-036-14, T-036-16, T-036-22.
**Priority:** High · **Story Points:** 8

### US-2: A reload never costs me typed text or an open dialog
**As a** person mid-sentence in a composer, a Settings field, the wizard or a dictation
**I want** the automatic reload to wait until I have paused and nothing is unsaved
**So that** keeping the UI current never destroys my work.

**Acceptance Criteria:**
- [ ] AC-14 [BROWSER] · AC-15 [BROWSER] · AC-16 [BROWSER] · AC-18 [BROWSER] · AC-22 [BROWSER] · AC-70 [BROWSER] · AC-78 [BROWSER] (idle and busy rules, FR-3)
- [ ] AC-17 [PY] (hold registry lives in `core.js`, called from `agents.js` and `todos.js`)
- [ ] AC-19 [PY] · AC-20 [BROWSER] · AC-21 [BROWSER] · AC-23 [BROWSER] (loop guard, flapping server, static export)

**Business Rules:** BR-6 (never discard typed text, drawer, wizard, palette, dictation), BR-12 (modules register their own off-DOM state), BR-15.
**Edge Cases:** dictated or picker-inserted text with no `input` event (AC-78); Settings fields filled by the page must not block (AC-70); a Tauri window hidden by its close button (AC-18, A-6 unverified); reload must re-run the Rust init script (AC-22, A-7 unverified).
**Related Components:** U2 `Console.holdReload`, U4 `app.js` idle/busy/guard, U5 `agents.js` + `todos.js`.
**Related Tasks:** T-036-15, T-036-17, T-036-18, T-036-22.
**Priority:** High · **Story Points:** 8

### US-3: My preferences live on the server, so the app and every browser share them
**As a** person who uses both the desktop app and a browser
**I want** theme, hidden tabs, panel state, agent lane, voice and the rest stored on the server behind the same `C.prefs` calls
**So that** I set something once and see it everywhere.

**Acceptance Criteria:**
- [ ] AC-24 [PY] · AC-25 [PY] · AC-26 [PY] · AC-27 [PY] · AC-28 [PY] · AC-29 [PY] · AC-30 [PY] · AC-31 [PY] · AC-32 [PY] · AC-33 [PY] · AC-34 [PY] · AC-35 [PY] · AC-36 [PY] (store, API, plugin, audit, `prefs_rev`, FR-4)
- [ ] AC-37 [PY] · AC-38 [PY] · AC-39 [PY] · AC-44 [PY] · AC-74 [PY] (client contract source checks, `layout` contract, FR-5)
- [ ] AC-40 [BROWSER] · AC-41 [BROWSER] · AC-42 [BROWSER] · AC-43 [BROWSER] · AC-45 [BROWSER] · AC-71 [BROWSER] · AC-72 [BROWSER] · AC-73 [BROWSER] · AC-81 [BROWSER] (runtime behaviour, FR-5)

**Business Rules:** BR-1 (one store in server mode), BR-2 (server never reads a pref), BR-8 (deltas, last writer wins per key), BR-10 (no secrets), BR-11 (voice/layout shared, three accepted risks), BR-13 (`get` synchronous, no read at script-evaluation time, T-037 included).
**Edge Cases:** corrupt or missing `prefs.json` reads empty (AC-29); a write while the server is down is lost on reload unless it returns in the same page lifetime (AC-72); 40 wizard keystrokes cause at most 3 POSTs (AC-42); `/api/prefs` slow or 404 falls back to local mode (AC-43, AC-73).
**Related Components:** K1 `prefs_store.py`, K2 `prefs_feature.py` + `plugins.toml`, K3 `audit.py`, K5 `shell_feature.py`, U1 `core.js` prefs, U3 `app.js` boot.
**Related Tasks:** T-036-01, T-036-03, T-036-04, T-036-06, T-036-07, T-036-08, T-036-09, T-036-10, T-036-22.
**Priority:** High · **Story Points:** 13

### US-4: My existing browser settings are carried over, never lost and never overwriting
**As a** person with settings already in a browser's `localStorage`
**I want** them moved to the server once, per key, without clobbering what the server already has
**So that** switching to shared preferences does not reset my theme and tabs.

**Acceptance Criteria:**
- [ ] AC-46 [PY] · AC-47 [PY] · AC-48 [PY] · AC-49 [PY] · AC-75 [PY] · AC-80 [PY] (import and reset semantics, FR-4/FR-6)
- [ ] AC-50 [BROWSER] · AC-51 [BROWSER] · AC-76 [BROWSER] (per-client migration, toasts, closed window)
- [ ] AC-53 [PY] (a POST's `rev` is adopted only under a `prev` check; heartbeat compares with `!==`)

**Business Rules:** BR-3 (per client, per key, never overwrites, first import wins, local deleted after the ack), BR-4 (Reset closes the import window), BR-16 (nothing leaves `localStorage` without a sentence, except an unparsable value).
**Edge Cases:** the app held no `theme`/`hiddenTabs`/`disabledBackends`, the browser holds the real values (hence per client); a second tab importing at the same moment (AC-80); unreachable at boot, a change, server returns (accepted, skipped toast).
**Related Components:** K1 `prefs_store.py` import/reset, K2 routes, U1 `core.js` migration.
**Related Tasks:** T-036-02, T-036-03, T-036-09, T-036-22.
**Priority:** High · **Story Points:** 5

### US-5: A theme or tab change in one client shows up in the others without a reload
**As a** person who changes the theme in the browser
**I want** the desktop app to follow within one heartbeat, without losing its place
**So that** the two keep showing the same UI after the first load.

**Acceptance Criteria:**
- [ ] AC-52 [BROWSER] · AC-77 [BROWSER] · AC-79 [BROWSER]

**Business Rules:** BR-8; pickup never re-renders the active tab; `hiddenTabs` rebuilds the nav only on a real change; the `buildNav` keydown listener is bound once.
**Edge Cases:** pickup hides the shown tab, which stays displayed (AC-77); two clients change different keys inside one heartbeat (AC-79); unflushed local changes block the refresh (AC-52); `prefs.json` deleted by hand resets `rev` to 0 (`!==`).
**Related Components:** U3 `app.js` heartbeat pickup and nav once-guard, U1 `core.js` `refresh`/`rev`.
**Related Tasks:** T-036-09, T-036-10, T-036-22.
**Priority:** Medium · **Story Points:** 3

### US-6: Settings says what is shared and Reset really resets, after I confirm
**As a** person opening Settings
**I want** the preferences panel to say who shares them and to ask before clearing everything
**So that** I understand the reach of Reset and no stale sentence tells me otherwise.

**Acceptance Criteria:**
- [ ] AC-54 [PY] · AC-55 [PY] · AC-56 [BROWSER]

**Business Rules:** BR-4, BR-9 (Reset states its reach and asks for confirmation).
**Edge Cases:** static export shows "Stored in this browser only."; the "Agent CLIs" wording keeps its distinction (hides from the shared picker, does not remove from the server); the "Setup wizard" row in the same panel is another ticket's and must survive.
**Related Components:** U6 `settings.js` + `about.js`, X1 docs and comments (README, `plugins.toml`, `registry.py`).
**Related Tasks:** T-036-11, T-036-12, T-036-13, T-036-22.
**Priority:** Medium · **Story Points:** 5

### US-7: The desktop app refuses to attach to another workspace's server (SHOULD, droppable)
**As a** person with more than one checkout of this workspace
**I want** the app to stop with a sentence when port 8790 is served by a different workspace
**So that** it cannot silently show another checkout's UI.

**Acceptance Criteria:**
- [ ] AC-57 [PY] · AC-58 [PY] · AC-59 [PY] · AC-60 [DOC]

**Business Rules:** BR-14 (`is_up` stays a liveness probe); no Rust change.
**Edge Cases:** an older server without `workspace` attaches as today; the workspace id is a 12-hex hash, never the path.
**Related Components:** K5 `shell_feature.py` (`workspace`), K6 `desktop/sidecar.py`.
**Related Tasks:** T-036-19, T-036-20, T-036-22. Droppable together (Q2 default is include).
**Priority:** Low · **Story Points:** 3

### US-8: The first deploy, the shared-file safety and the constraints are stated and checkable
**As a** maintainer shipping this while other tickets edit the same files
**I want** the one-time relaunch step documented and every shared constraint checkable
**So that** "it still does not update" is expected on first deploy and no other ticket's work is clobbered.

**Acceptance Criteria:**
- [ ] AC-61 [PY] · AC-62 [PY] · AC-66 [PY]
- [ ] AC-63 [DOC] · AC-64 [DOC] · AC-65 [DOC]

**Business Rules:** NFR-1 (stdlib, ES5, no build step), NFR-3 (stylesheet and plugin tests green), NFR-9 (foreign hunks byte-identical), NFR-11 (first deploy needs one manual relaunch), NFR-12 (Windows/WebView2 only is checked).
**Edge Cases:** `kanban.py` cp1252 stdout crash needs `PYTHONUTF8=1` (not fixed here); local Python 3.14 is not evidence for 3.11.
**Related Components:** X1 docs, X2 release note and verification plan, every UI component (source rules).
**Related Tasks:** T-036-00, T-036-07, T-036-10, T-036-14, T-036-16, T-036-17, T-036-21, T-036-22.
**Priority:** High · **Story Points:** 3

---

## Story Status Summary

| Story ID | Title | Status | Priority | Points | Related Tasks |
|----------|-------|--------|----------|-------:|---|
| US-1 | New UI picked up by itself | Pending | High | 8 | 05, 06, 14, 16, 22 |
| US-2 | Reload never costs typed text | Pending | High | 8 | 15, 17, 18, 22 |
| US-3 | Preferences on the server | Pending | High | 13 | 01, 03, 04, 06-10, 22 |
| US-4 | Migration never loses or overwrites | Pending | High | 5 | 02, 03, 09, 22 |
| US-5 | Live pickup of theme and tabs | Pending | Medium | 3 | 09, 10, 22 |
| US-6 | Settings wording and confirmed Reset | Pending | Medium | 5 | 11, 12, 13, 22 |
| US-7 | Sidecar refuses a different workspace (SHOULD) | Pending | Low | 3 | 19, 20, 22 |
| US-8 | Rollout, shared-file safety, constraints | Pending | High | 3 | 00, 07, 10, 14, 16, 17, 21, 22 |

## Traceability Matrix

| Story | FRs | ACs (count) | Components | Tasks |
|-------|-----|------------:|-----------|-------|
| US-1 | FR-1, FR-2 | 16 | K4, K5, U4, U7 | 05, 06, 14, 16, 22 |
| US-2 | FR-3 | 12 | U2, U4, U5 | 15, 17, 18, 22 |
| US-3 | FR-4, FR-5 | 27 | K1, K2, K3, K5, U1, U3 | 01, 03, 04, 06, 07, 08, 09, 10, 22 |
| US-4 | FR-4, FR-6 | 10 | K1, K2, U1 | 02, 03, 09, 22 |
| US-5 | FR-6 | 3 | U1, U3 | 09, 10, 22 |
| US-6 | FR-7 | 3 | U6, X1 | 11, 12, 13, 22 |
| US-7 | FR-8 | 4 | K5, K6 | 19, 20, 22 |
| US-8 | NFR-1..12 | 6 | X1, X2, all | 00, 07, 10, 14, 16, 17, 21, 22 |

AC count check: 16 + 12 + 27 + 10 + 3 + 3 + 4 + 6 = 81, each AC listed under exactly one story (AC-53 under US-4, AC-44 and AC-74 under US-3). The authoritative AC to task table is in [[T-036-plan]] § Acceptance criterion coverage; `validate-artifacts T-036 links` should re-derive it.

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-requirements-draft]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-effort-estimate]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]] · [[T-036-critique-report]] · [[T-036-plan-iteration-log]]
- [[T-036-gap-analysis]]
