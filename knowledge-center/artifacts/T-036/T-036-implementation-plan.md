---
ticket: "T-036"
artifact: implementation-plan
---

# Implementation plan: T-036

Master plan: phases, slices, tasks, files, effort. Synthesised from [[T-036-requirements]] (scope and AC), [[T-036-plan]] (approach, rules, canonical Done-criteria, risks), [[T-036-components]] (graph) and [[T-036-task-breakdown]] (atomic tasks). Those are inputs; this file does not repeat their evidence commands. No template exists for this artifact (not in `knowledge-center/artifacts/_template/` or the template manifest); it follows the content spec in `.claude/skills/breakdown-tasks/SKILL.md` step 4 and the precedent of [[T-031-implementation-plan]].

## Ticket summary

The desktop app is a bare long-lived webview on the live server, and the app and each browser keep separate `localStorage`, so on 2026-10-05 the app showed a UI loaded at 08:21:59 while `console/static` changed 09:43-10:02 ([[T-036-analysis]] §1, §3). Fix, as the owner decided: (1) the server stamps the served UI (`ui_version` on `/api/config`) and the page reloads itself when idle and nothing is unsaved; (2) preferences move from per-browser `localStorage` to one server file behind the unchanged synchronous `C.prefs` interface, with a per-key never-overwrite migration, a Reset that reaches every client, live pickup of `theme` and `hiddenTabs`, Settings wording that tells the truth, and the `layout` contract [[T-037-summary]] needs. Optional and droppable: the sidecar refuses to attach to a different workspace's server (Q2). Scope: S1-S7 (8 FRs, 81 ACs: PY 46 / BROWSER 31 / DOC 4, 12 NFRs, 16 BRs). Out: Rust shell, HUD overlay, chat state, content-hash versions, consolidating the five tmp+replace writers, detecting an older-than-code server.

**Totals:** 8 phases, 23 tasks (00-22), **44.5 h** build effort (task-level PERT expected 43.8 h, range 31.2-53.8 h, confidence Low); envelope Development 64.2 h [46.1, 77.6] ([[T-036-effort-estimate]], reconciled there). Critical path 30.5 h by tasks (00, 01, 02, 03, 07, 08, 09, 10, 16, 17, 18, 21, 22; 30.0 h of component work, step zero excluded), i.e. K1 → K2 → U1 → U3 → U4 → X2. The plan is serial: one builder, and six shared files carry other tickets' uncommitted hunks. The shared-file rules, evidence conventions and build protocol in [[T-036-plan]] bind every task below. Q1-Q5 are planned at their recorded defaults.

## Phase 0: Step zero (0.5 h)

Move the lane and fix the yardsticks the later tasks are judged against: the pytest baseline and the pre-build copies of the shared files (AC-63's "pre-build snapshot named in the plan").

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 0a | 00 | `ticket move`, baseline pytest, `.orig` + `.diff` of each shared file | none in the product tree (`console/.cache/t036-prebuild/` is gitignored); `T-036-progress.md` | 0.5 | AC-63 (enabler) |

## Phase 1: Preference store, server (9 h)

The server half of the prefs contract first, because [[T-037-summary]]'s `layout` depends on it and the client half builds on its routes. A pure module (validation, import, reset, locked atomic write) is proven by unit tests before any route exists; then the plugin and routes with the repo's first real-HTTP test; the `audit.ACTIONS` edit last because that file has another ticket's hunk.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 1a | 01 | store core: read (corrupt reads empty), validation, set/del with `{rev, prev}`, lock + `.tmp` + `tomlio._replace` | `console/server/prefs_store.py` (new), `console/tests/test_prefs_store.py` (new) | 3 | AC-24..31, 44 |
| 1a | 02 | `import_values` and `reset` | `prefs_store.py`, `test_prefs_store.py` | 2 | AC-46, 47, 48, 49, 75, 80 |
| 1b | 03 | plugin, four routes, provider, `plugins.toml` row, router and real-HTTP tests | `console/server/features/prefs_feature.py` (new), `console/config/plugins.toml` (one row), `console/tests/test_prefs_routes.py` (new) | 3 | AC-24, 25, 32, 33, 34, 36, 49 |
| 1b | 04 | register the two audit actions | `console/server/audit.py` (foreign hunk), `test_prefs_routes.py` | 1 | AC-32 |

Requirements satisfied: FR-4, FR-6 (server half), BR-2, BR-3, BR-4, BR-10; NFR-7, NFR-8. Components: K1, K2, K3.

## Phase 2: UI version stamp, server (3.5 h)

Small and pure. After this phase every heartbeat carries both `ui_version` and `prefs_rev`, before any page code reads them.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 2a | 05 | stat-only digest, once-per-process manifest digest, vanish/unlistable rules | `console/server/ui_version.py` (new), `console/tests/test_ui_version.py` (new) | 2 | AC-2..7, 67 |
| 2a | 06 | `ui_version` and `prefs_rev` on `/api/config` | `console/server/features/shell_feature.py` (foreign hunk), `console/tests/test_config_payload.py` (new) | 1.5 | AC-1, 35, 67 |

Requirements satisfied: FR-1, BR-5 (server side), BR-7; NFR-4. Components: K4, K5.

## Phase 3: Client preferences (11 h)

The page side of the contract, in three steps in `core.js` and then the router. The read side and local fallback first (it must behave exactly like today when there is no server), then write-through and the page-hide flush, then migration, Reset and refresh. The boot chain and live pickup in `app.js` come last because they consume all of it.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 3a | 07 | map, deep-clone `get`, local mode, `hydrate()` 3 s bound, `all/keys/mode/rev/onChange`; constraint test | `console/static/core.js`, `console/tests/test_prefs_client_source.py` (new), `console/tests/test_ui_constraints.py` (new) | 3 | AC-37, 43, 44, 61, 74 |
| 3a | 08 | 250 ms debounce, key/size mirror, keepalive flush, retry, 400 rule, `post` `.status` | `core.js`, `test_prefs_client_source.py` | 3 | AC-39, 42, 71, 72, 74 |
| 3a | 09 | migration import, closed window, `reset()`, `refresh()`, own-rev adoption | `core.js`, `test_prefs_client_source.py` | 3 | AC-50, 51, 53, 76, 79, 81 |
| 3b | 10 | boot `Promise.all`, heartbeat prefs pickup, nav listener bound once | `console/static/app.js` (foreign hunks), `test_prefs_client_source.py` | 2 | AC-38, 52, 53, 66, 77, 79 |

Requirements satisfied: FR-5, FR-6 (client half), BR-1, BR-3, BR-8, BR-13, BR-16; NFR-5, NFR-6. Components: U1, U3. After this phase the prefs half is complete and T-037 can store `layout`.

## Phase 4: Settings and wording (4.5 h)

Settings and every statement that stopped being true. The panel is rewritten around the real API; scattered stale sentences are fixed one line at a time; docs and comments follow.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 4a | 11 | "Saved preferences" panel, mode sentences, confirmed Reset, key list from `C.prefs.all()` | `console/static/settings.js` (foreign hunks), `console/tests/test_prefs_wording.py` (new) | 2 | AC-54, 55, 56 |
| 4a | 12 | stale statements: `settings.js` comments/help, `about.js`, `core.js:256-258` | `settings.js`, `console/static/about.js`, `core.js` (comment only), `test_prefs_wording.py` | 1.5 | AC-54, 55 |
| 4b | 13 | README table, `plugins.toml` header comment, `registry.py` docstring | `console/README.md`, `console/config/plugins.toml` (comment only), `console/server/plugins/registry.py` (docstring), `test_prefs_wording.py` | 1 | AC-54 |

Requirements satisfied: FR-7, BR-4, BR-9. Components: U6, X1. `onboarding-wizard.js:4` stays deferred (SHOULD, untracked file).

## Phase 5: Reload when safe (9.5 h)

The reload half. The notice's style lands first (a JS class without a rule fails the stylesheet test), then the hold registry and its two registrants, then the `app.js` logic in three reviewed steps: compare and notice, idle and busy, loop guard. No new timer anywhere: every decision runs from the existing heartbeat, the connection listener or `visibilitychange`.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 5a | 14 | one hyphenated notice class mid-file next to `.toast` | `console/static/styles.css` (foreign hunk at the END) | 0.5 | AC-62, 69 |
| 5a | 15 | `Console.holdReload`; `"agents.drafts"`, `"todos.new"` | `core.js`, `console/static/agents.js`, `console/static/todos.js`, `console/tests/test_reload_source.py` (new) | 1.5 | AC-16, 17 |
| 5b | 16 | boot version, compare on three triggers, notice with **Reload now**, version rules | `app.js`, `test_reload_source.py` | 3 | AC-8..13, 21, 23, 68, 69 |
| 5b | 17 | idle tracker, busy predicate, hidden shortcut, scheduler | `app.js`, `test_reload_source.py` | 3 | AC-14, 15, 16, 18, 22, 70, 78 |
| 5b | 18 | loop guard in `sessionStorage["console-reload"]` | `app.js`, `test_reload_source.py` | 1.5 | AC-19, 20 |

Requirements satisfied: FR-2, FR-3, BR-5, BR-6, BR-12, BR-15; NFR-3, NFR-10. Components: U7, U2, U5, U4.

## Phase 6: Sidecar workspace identity (3 h, SHOULD, droppable together)

Python only, no Rust. Dropping both tasks (Q2) changes nothing in Phases 1-5.

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 6a | 19 | `workspace` on `/api/config` | `shell_feature.py` (foreign hunk), `test_config_payload.py` | 1 | AC-57 |
| 6a | 20 | `ensure()` attach check, duplicated hash, fake-server tests | `desktop/sidecar.py`, `desktop/tests/test_sidecar.py` | 2 | AC-58, 59, 60 |

Requirements satisfied: FR-8, BR-14. Components: K5, K6. No task and no recorded changed file is under `desktop/src-tauri/` (AC-60).

## Phase 7: Release and verification (3.5 h)

| Slice | Task | Scope | Files | Effort | ACs |
|-------|------|-------|-------|-------:|-----|
| 7a | 21 | release note with the first-deploy relaunch step; verification plan listing every [BROWSER] criterion as "not verified in a browser" | `T-036-release.md`, `T-036-verification.md`, `T-036-progress.md` | 1.5 | AC-60, 63, 64, 65 |
| 7a | 22 | full pytest, CI-parity checks, snapshot diff, `ui_version` timing | none in the product tree; `T-036-progress.md`, `T-036-verification.md` | 2 | AC-61, 62, 63, 65, 66 |

Requirements satisfied: NFR-1, NFR-2, NFR-3, NFR-9, NFR-11, NFR-12. Components: X2.

## Reconciliation

Phase effort: 0.5 + 9 + 3.5 + 11 + 4.5 + 9.5 + 3 + 3.5 = **44.5 h**, equal to the task-breakdown summary and to the plan's Effort table. Shared-file touch map (each foreign-dirty file and the tasks that edit it): `app.js` 10, 16, 17, 18 · `settings.js` 11, 12 · `shell_feature.py` 06, 19 · `audit.py` 04 · `styles.css` 14. `index.html` is not edited by this ticket (no new script). Clean files this ticket edits: `core.js` (07, 08, 09, 12, 15), `agents.js`, `todos.js` (15), `about.js` (12), `plugins.toml` (03, 13), `registry.py`, `README.md` (13), `sidecar.py` (20).

## Links
- [[T-036-summary]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-effort-estimate]] · [[T-036-critique-report]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]]
- Related: [[T-037-summary]] · [[T-031-summary]] · [[T-031-implementation-plan]] (format precedent)
- [[T-036-analysis]]
