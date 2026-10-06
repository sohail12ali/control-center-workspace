---
ticket: "T-036"
artifact: task-breakdown
---

# Task breakdown: T-036

Atomic tasks per slice. Task ID format `{phase}-{slice}-{task}`; the **Plan ID** column is the heading id in [[T-036-plan]] (`### [ ] T-036-NN`), which holds the full done-criteria, files and evidence commands (canonical there; not repeated here). Component ids are from [[T-036-components]]. "Split because" names the qualifying boundary of the task boundary rule in `.claude/skills/plan/SKILL.md`.

**Produced by:** `breakdown-tasks`. **Consumed by:** `breakdown-tasks` (implementation-plan synthesis), `estimate(mode=forecast)`, `challenge-plan`.

---

## Phase 0: Step zero

### Slice 0a: Lane, baselines, snapshots

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 0a-1 | 00 | `ticket move T-036 in-progress`; pytest baseline; pre-build copies and `git diff -U0` of the shared files | X2 | AC-63 (enabler) | lane `in-progress`; baseline total/failed and pre-existing failures recorded; `console/.cache/t036-prebuild/` holds `.orig` + `.diff` per shared file | 0.5 | done (actual ~0.4 h) | Split because: a process step that precedes every build task (hard handoff) and fixes what "foreign hunk" and "baseline failure" mean. |

## Phase 1: Preference store (server)

### Slice 1a: Pure store

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1a-1 | 01 | `prefs_store.py` read, validate, set/del with `{rev, prev}`, locked atomic write | K1 | AC-24..31, 44 (store half) | `test_prefs_store.py` covers each AC; no real-checkout write | 3 | done (actual ~1.25 h) | depends on 0a-1. Split because: a self-contained deliverable every later server task and the whole client builds on. |
| 1a-2 | 02 | `import_values` (imported/skipped/rejected/closed, equal = imported) and `reset` | K1 | AC-46..49 (store half), 75, 80 | tests per bucket, closed window, two-thread interleave | 2 | done (actual ~0.5 h incremental) | depends on 1a-1. Split because: independently reviewable semantics (migration rule) with its own tests. |

### Slice 1b: Plugin, routes, audit

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 1b-1 | 03 | `prefs_feature.py` four routes + provider + `plugins.toml` row; router-level and real-HTTP tests | K2 | AC-24, 25, 32 (route half), 33, 34, 36, 49 (audited) | 403 without header, 201 with it over a real in-process server | 3 | done (actual ~1 h) | depends on 1a-2. Split because: a different layer (routes/transport) with the repo's first real-HTTP test. |
| 1b-2 | 04 | register `prefs.reset`, `prefs.import` in `audit.ACTIONS` beside the foreign hunk | K3 | AC-32 | in `ACTIONS`; recorded with names/counts only; foreign lines byte-identical | 1 | done (actual ~0.4 h) | depends on 1b-1. Split because: a foreign-dirty file whose edit must wait for its hunk to settle (NFR-9); movable to the end of Phase 3. |

## Phase 2: UI version stamp (server)

### Slice 2a: Digest and payload

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 2a-1 | 05 | `ui_version.py`: stat-only 12-hex digest, once-per-process manifest digest, vanish and unlistable rules | K4 | AC-2..7, 67 (unit half), 1 (shape) | `test_ui_version.py`; opens no file; file set equals `_copy_frontend` | 2 | done (actual ~0.6 h) | no dependency (root). Split because: a pure self-contained module, parallelisable in principle. |
| 2a-2 | 06 | `shell_feature.config()` adds `ui_version` and `prefs_rev`; payload tests | K5 | AC-1, 35, 67 (route half) | `test_config_payload.py`; `prefs_rev` omitted when plugin disabled | 1.5 | done (actual ~0.5 h) | depends on 1b-1, 2a-1. Split because: a foreign-dirty file, one edit for both fields. |

## Phase 3: Client preferences

### Slice 3a: `C.prefs` in `core.js`

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3a-1 | 07 | in-memory map, deep-clone `get`, local mode (old behaviour), `hydrate()` with 3 s bound, `all/keys/mode/rev/onChange`; `test_ui_constraints.py` | U1 | AC-37, 40, 41 (enabler), 43, 44 (client), 61, 73 (enabler), 74 (part) | source tests green; server mode gated by `SERVER_PREFS = false` until 3a-3 (CR-27); `node --check` if available | 3 | done (actual ~1.25 h) | depends on 1b-1. Split because: first and riskiest client step: proves the contract before write-through builds on it. |
| 3a-2 | 08 | debounced write-through, key/size mirror, keepalive flush, retry, 400 rule, `post` error `.status` | U1 | AC-39, 42, 71, 72, 74 | source tests: `keepalive`, CSRF header, no `sendBeacon` in `console/static` | 3 | done (actual ~1 h) | depends on 3a-1. Split because: an independently reviewed piece (flood and data-loss risk). |
| 3a-3 | 09 | migration import, closed window, `reset()`, `refresh()`, own-rev adoption under `prev` | U1 | AC-50, 51, 53 (core half), 76, 79, 81 | import runs inside `hydrate()` (CR-29); source tests for import/reset strings and `prev` check; last step sets `SERVER_PREFS = true`; scratch Node smoke if available (CR-26) | 3 | done (actual ~1.25 h) | depends on 3a-2. Split because: a different behaviour (migration/Reset) with its own accepted-risk rules. |

### Slice 3b: Boot and live pickup in `app.js`

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 3b-1 | 10 | `Promise.all([config, hydrate])` before `applyTheme`; heartbeat `onHeartbeat` with `prefs_rev !== rev()` pickup; `buildNav` listener once-guard | U3 | AC-38, 52, 53, 66 (part), 77, 79 | exact boot string; no new `setInterval`; foreign hunks identical | 2 | done (actual ~0.6 h) | depends on 3a-3, 2a-2. Split because: a different component (router) in a file with three foreign hunks. |

## Phase 4: Settings and wording

### Slice 4a: Settings

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4a-1 | 11 | `storage()` becomes "Saved preferences": mode sentences, confirmed Reset, key list from `C.prefs.all()` | U6 | AC-54 (part), 55 (part), 56 | `test_prefs_wording.py`; "Setup wizard" row intact | 2 | done (actual ~0.75 h) | depends on 3a-3. Split because: a foreign-dirty function with another ticket's row inside it. |
| 4a-2 | 12 | stale statements in `settings.js`, `about.js`, `core.js:256` comment | U6 | AC-54, 55 | no `localStorage` left in `settings.js`; no "this browser only" for Settings toggles | 1.5 | done (actual ~0.5 h) | depends on 4a-1. Split because: many scattered one-line edits better reviewed apart from the panel rewrite. |

### Slice 4b: Docs

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 4b-1 | 13 | README two-switches table, `plugins.toml` comment, `registry.py` docstring | X1 | AC-54 | text checks green; `onboarding-wizard.js:4` deferred | 1 | done (actual ~0.5 h) | depends on 4a-2. Split because: a different owner type (docs and comments, no behaviour). |

## Phase 5: Reload when safe

### Slice 5a: Surface for the notice and holds

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 5a-1 | 14 | one hyphenated notice class mid-file next to `.toast` | U7 | AC-62, 69 | `test_stylesheet.py` green; nothing appended at the end | 0.5 | done (actual ~0.15 h) | no dependency. Split because: a foreign-dirty file with its own rule (never append) and it must land before the JS class. |
| 5a-2 | 15 | `Console.holdReload(id, fn)` in `core.js`; `"agents.drafts"` and `"todos.new"` at top level | U2, U5 | AC-16 (enabler), 17 | defined once in `core.js`, one call in each tab, `core.js` before tabs | 1.5 | done (actual ~0.5 h) | depends on 3a-3 (same file, serial). Split because: a hard dependency of the busy predicate. |

### Slice 5b: `app.js` reload logic

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 5b-1 | 16 | record boot `ui_version`; compare on heartbeat, `C.onConnection`, `visibilitychange`; notice with **Reload now**; version rules | U4 | AC-8, 9, 10, 11, 12, 13, 21 (surface), 23, 68, 69 | `test_reload_source.py`; notice is `role: "status"`, not a toast | 3 | done (actual ~1.25 h) | depends on 2a-2, 3b-1, 5a-1. Split because: the largest new behaviour, reviewed alone. |
| 5b-2 | 17 | idle tracker, busy predicate, hidden shortcut, reload scheduler with no new timers | U4 | AC-14, 15, 16, 18, 22, 70, 78 | source tests for each busy source; zero new `setInterval`/`setTimeout` in the block | 3 | done (actual ~1 h) | depends on 5b-1, 5a-2. Split because: safety logic (data-loss risk) reviewed independently. |
| 5b-3 | 18 | loop guard in `sessionStorage["console-reload"]`, pause wording, manual reload never counts | U4 | AC-19, 20 | source test: 3 in a rolling 5 minutes, no `to` comparison | 1.5 | done (actual ~0.5 h) | depends on 5b-2. Split because: an independently reviewed safety net. |

## Phase 6: Sidecar identity (SHOULD, droppable together)

### Slice 6a: Workspace id

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 6a-1 | 19 | `workspace` (12 hex, never the path) on `/api/config` | K5 | AC-57 | constant per root, different per root, no path text | 1 | done (actual ~0.4 h) | depends on 2a-2. Split because: separable by Q2; dropping it must not touch Phases 1-5. |
| 6a-2 | 20 | `sidecar.ensure()` attach check, duplicated hash, fake-server tests | K6 | AC-58, 59, 60 (DOC) | `desktop/tests/test_sidecar.py` extended; no import from `console/` | 2 | done (actual ~0.9 h) | depends on 6a-1. Split because: a different component and repo area (`desktop/`). |

## Phase 7: Release and verification

### Slice 7a: Documents and gates

| Task ID | Plan ID | Description | Component | Requirement/AC | Acceptance criteria | Effort (h) | Status | Notes |
|---------|---------|-------------|-----------|-----------------|----------------------|-----------:|--------|-------|
| 7a-1 | 21 | `T-036-release.md` (relaunch step, check, rollback) and `T-036-verification.md` plan (31 [BROWSER] rows "not verified in a browser") | X2 | AC-60, 63, 64, 65 (DOC) | both files contain the relaunch step and how to check it | 1.5 | done (actual ~0.9 h) | depends on every build task. Split because: a different artifact owner type (deployer/verifier handoff). |
| 7a-2 | 22 | full pytest, CI-parity checks (3.11-clean text scan, `=>`/`let`/`const`, stylesheet, plugins), snapshot diff, `ui_version` timing, optional `node --check` | X2 | AC-61, 62, 63, 65, 66 | counts recorded; foreign hunks identical; [BROWSER] list handed off | 2 | done (actual ~0.8 h) | depends on 7a-1. Split because: an independently reviewed gate (verify). |

---

## Effort summary

| Phase | Estimated (h) | Completed (h) | In-progress (h) | Remaining (h) | % complete |
|-------|--------------:|---------------:|-----------------:|---------------:|-----------:|
| Phase 0 Step zero | 0.5 | 0 | 0 | 0.5 | 0% |
| Phase 1 Preference store | 9.0 | 0 | 0 | 9.0 | 0% |
| Phase 2 UI version stamp | 3.5 | 0 | 0 | 3.5 | 0% |
| Phase 3 Client preferences | 11.0 | 0 | 0 | 11.0 | 0% |
| Phase 4 Settings and wording | 4.5 | 0 | 0 | 4.5 | 0% |
| Phase 5 Reload when safe | 9.5 | 0 | 0 | 9.5 | 0% |
| Phase 6 Sidecar (droppable) | 3.0 | 0 | 0 | 3.0 | 0% |
| Phase 7 Release and verification | 3.5 | 0 | 0 | 3.5 | 0% |
| **Total** | **44.5** | **0** | **0** | **44.5** | **0%** |

By layer (for `estimate(mode=forecast)`): service 15.5 h (tasks 01-06, 19, 20) · UI 24.0 h (07-12, 14-18) · docs 3.0 h (00, 13, 21) · test/verification 2.0 h (22). Total 44.5 h; 23 tasks (22 numbered 01-22 plus step zero); 8 phases.

## Conventions

**Status:** pending · in-progress · done · blocked (see Notes for why).
**Effort:** 0.5 / 1 / 1.5 / 2 / 3 h buckets; a task that will not fit stops, is logged in progress.md and goes to `replan`.
**Dependencies:** in Notes, "depends on {id}". Suggested serial build order is the table order; see [[T-036-components]] § Suggested build order.

## Links
- [[T-036-summary]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-effort-estimate]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-critique-report]] · [[T-036-plan-iteration-log]]
- [[T-036-decision-log]] · [[T-036-progress]] · [[T-036-release]] · [[T-036-verification]]
