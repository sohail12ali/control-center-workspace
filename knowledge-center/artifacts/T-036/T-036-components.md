---
ticket: "T-036"
artifact: components
---

# Components: T-036

Every component this ticket touches or creates, its dependencies and build status. Layers follow what this repo actually has: the Python console server, the browser UI (vanilla ES5 JS and one stylesheet), the desktop sidecar, and docs/verification artifacts. There is no data layer beyond one new gitignored JSON file (owned by K1).

**Produced by:** `analyze-components` (dependency graph included, same pass). **Consumed by:** `breakdown-tasks` ([[T-036-task-breakdown]], [[T-036-implementation-plan]]). Sources: [[T-036-requirements]], [[T-036-decision-log]] (D-11..D-21 win over earlier entries), [[T-036-analysis]] §8 (conflict map).

15 components, above the usual 5-12: they are 6 server, 7 UI, 2 docs. Four are one-hunk edits to an existing file (K3, K5, U5, U7) and one is droppable (K6). Merging them would hide the shared-dirty-file constraints, which are the point of listing them; scope itself is not in question.

---

## Service layer (Python, `console/server/`)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|--------------|-------|----------------|--------|
| K1 `prefs_store.py` (new) | pure module | read/validate/write `console/.cache/prefs.json`: set/del with `rev`+`prev`, import, reset; lock + `.tmp` + `tomlio._replace`; corrupt reads empty | `tomlio._replace`, `paths.resolve_rel` | A | FR-4, FR-6 server half: AC-24..31, 44, 46..49, 75, 80 | pending |
| K2 `features/prefs_feature.py` (new) + `console/config/plugins.toml` row (changed) | plugin | `GET/POST /api/prefs`, `POST /api/prefs/import`, `POST /api/prefs/reset`; publishes provider `prefs`; audits reset/import | K1, K3 (names only: `audit.record` does not validate), `plugins/base.py` | A | AC-32, 33, 34, 36 | pending |
| K3 `audit.py` `ACTIONS` (changed, **foreign hunk**) | constant | register `prefs.reset`, `prefs.import` | none | A | AC-32 | pending |
| K4 `ui_version.py` (new) | pure module | `compute(static_dir, manifest_digest)`: 12-hex over sorted `(name,size,mtime_ns)` of `*.html *.js *.css *.png` plus a once-per-process manifest digest; stat only; vanished file skipped, unlistable dir omits | stdlib only | D | FR-1: AC-1..7, 67 | pending |
| K5 `features/shell_feature.py` `config()` (changed, **foreign hunk**) | endpoint payload | adds `ui_version`, `prefs_rev` (only if provider `prefs` loaded), later `workspace` | K4, K1 (via `ctx.provider("prefs")`) | A/D/F | AC-1, 35, 57, 67 | pending |
| K6 `desktop/sidecar.py` (changed) **SHOULD, droppable** | CLI helper | `ensure()` reads `/api/config` when it would attach and raises `SidecarError` if `workspace` differs; duplicated 3-line hash | K5 (field), stdlib | F | FR-8: AC-58, 59 (+60 DOC) | pending |

## UI layer (`console/static/`)

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|--------------|-------|----------------|--------|
| U1 `core.js` `C.prefs` (changed) | kernel API | in-memory map, deep-clone `get`, `hydrate/refresh/all/keys/reset/mode/rev`, 250 ms debounced write-through, keepalive flush, retry, 3 s hydrate bound, migration import, local fallback, `post` error `.status` | K2 (runtime contract) | B | FR-5, FR-6 client half: AC-37..45, 53, 71..74, 81 | pending |
| U2 `core.js` `Console.holdReload` (changed) | registry | `holdReload(id, fn)` idempotent by id plus a reader the page uses | none | E | FR-3: AC-17 | pending |
| U3 `app.js` boot + live pickup + nav once-guard (changed, **foreign hunks**) | router | `Promise.all([config, hydrate])` before `applyTheme`; heartbeat `prefs_rev !== C.prefs.rev()` pickup; `buildNav` keydown bound once | U1, K5 | B | AC-38, 52, 53, 66, 77, 79 | pending |
| U4 `app.js` version compare, notice, idle/busy, loop guard (changed, **foreign hunks**) | router | record boot `ui_version`; compare on heartbeat, `C.onConnection`, `visibilitychange`; notice with **Reload now**; idle 30 s; busy predicate; hidden shortcut; `sessionStorage["console-reload"]` guard; no new timers | K5, U2, U3, U7 | E | FR-2, FR-3: AC-8..16, 18..23, 68..70, 78 | pending |
| U5 `agents.js` + `todos.js` (changed) | tab modules | one top-level `Console.holdReload` each: `"agents.drafts"` over `st.drafts`, `"todos.new"` over `st.newText` | U2 | E | AC-16, 17 | pending |
| U6 `settings.js` `storage()` + wording, `about.js`, `core.js` comment (changed, **foreign hunks in `settings.js`**) | tab | panel "Saved preferences", mode sentences, `window.confirm` Reset, key list from `C.prefs.all()`, no `localStorage`; stale statements corrected | U1 | C | FR-7: AC-54, 55, 56 | pending |
| U7 `styles.css` notice class (changed, **foreign hunk: ~80 `.ob-*` lines at the END**) | stylesheet | one hyphenated class for the notice, placed mid-file near `.toast` (~l.1851-1858) | none | E | AC-62, 69 | pending |

## Docs and verification

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|--------------|-------|----------------|--------|
| X1 docs and comments | text | `console/README.md:571-578`, `console/config/plugins.toml:13-15`, `console/server/plugins/registry.py:9-10` no longer call Settings toggles per-browser; `onboarding-wizard.js:4` comment deferred (SHOULD, file untracked) | U6 (same wording) | C | AC-54 | pending |
| X2 release note + verification plan (`T-036-release.md`, `T-036-verification.md`) | artifact | first-deploy relaunch step and how to check it; every [BROWSER] AC listed "not verified in a browser"; AC-63/65 procedures | all | G | AC-60, 63, 64, 65 (DOC) | pending |

Tests are not separate components: each component's tests live in new files under `console/tests/` and `desktop/tests/` named in [[T-036-task-breakdown]] and count toward that component's done-criteria.

---

## Dependency graph

```
Browser page (boot)
  app.js U3 boot ──waits on──> C.get("/api/config")  ──> K5 shell_feature.config ──> K4 ui_version
        │                                                        └──> K1 prefs_store.rev (provider "prefs")
        └──waits on──> U1 C.prefs.hydrate ──> K2 prefs_feature ──> K1 prefs_store ──> tomlio._replace
                                                    └──(names)──> K3 audit.ACTIONS
  app.js U4 compare/notice/idle/busy/guard ──reads──> K5 ui_version (heartbeat), U2 holdReload registry
        ├── registry filled by U5 agents.js / todos.js (top level, before app.js evaluates)
        └── notice styled by U7 styles.css
  settings.js U6 ──> U1 (all, reset, mode)        about.js / README / plugins.toml / registry.py X1 (wording only)
Desktop sidecar K6 ──GET /api/config──> K5 (workspace)            [SHOULD]
X2 release/verification: after every component
```

### Graph analysis

- **Edges ("depends on"): 15.** K2→K1, K2→K3 (soft), K5→K4, K5→K1, K6→K5, U1→K2, U3→U1, U3→K5, U4→K5, U4→U2, U4→U3, U4→U7, U5→U2, U6→U1, X1→U6 (wording). X2 follows all (not counted).
- **Root:** K1, K3, K4, U2, U7. **Leaf:** K6, U4, U5, X1, X2. **Middle:** K2, K5, U1, U3, U6.
- **Circular dependencies: none.** The one tempting loop (a page reload forced by `ui_version`, which includes the route table that includes `/api/prefs`) is not a build dependency: `ui_version` is computed, never stored.
- **Isolated components: none.** Every component maps to at least one AC (column above).
- **Critical path (by dependency count): K1 → K2 → U1 → U3 → U4 → X2** (6 components). By hours (task estimates in [[T-036-task-breakdown]]): K1 5 + K2 3 + U1 9 + U3 2 + U4 7.5 + X2 3.5 = **30 h of 44.5 h** (30.5 h counting step zero, task 00). U4 is also gated by K5 (1.5 h, plus K4 2 h), U2 (with U5, 1.5 h) and U7 (0.5 h), which sit off the path and are built earlier in the serial order.
- **Bottlenecks (most depended-on, still pending):** U1 `C.prefs` (U3, U6, and T-037's `layout`); K5 `shell_feature.config()` (U3, U4, K6; carries a foreign hunk); `app.js` as a file (U3 and U4 both edit it, with three foreign hunks). `core.js` is shared by U1, U2 and the `post` error tweak, so those tasks are strictly serial.
- **Parallelizable in principle (two builders):** {K1, K2, K3}, {K4}, {U2, U5, U7} touch disjoint files. **Not parallelizable in practice:** one builder, and the dirty shared files forbid concurrent edits by this ticket's own tasks (U1, U2 and U6 all hit `core.js`/`settings.js` neighbours). The plan is therefore serial.

### Suggested build order (reasons)

1. **Step zero** (task 00): lane move, baselines, pre-build snapshots of shared files (AC-63).
2. **Slice A first** (K1, K2, K3): [[T-037-summary]]'s `layout` needs the prefs contract; the store has no dependency and the rest of the prefs half builds on its routes.
3. **Slice D** (K4, then K5 `ui_version` and `prefs_rev` together): tiny, pure, and makes the heartbeat carry both signals before any page code reads them. Done after A so `prefs_rev` can read the provider in one edit of the foreign-dirty `shell_feature.py`.
4. **Slice B** (U1 in three steps, then U3): the page's boot chain and live pickup. Last file edits of `core.js` that the reload half then extends.
5. **Slice C** (U6, X1): Settings and wording follow the API they describe; sequenced after the other pipelines' `settings.js` hunks settle where possible (T-031 edits `assistant()` there).
6. **Slice E** (U7, U2+U5, then U4 in three steps): CSS first (a JS class without a rule fails `test_stylesheet.py`), registry before its registrants and before the busy predicate, compare/notice before idle/busy before the loop guard.
7. **Slice F** (K5 `workspace`, K6): droppable by Q2 without touching 1-6.
8. **Slice G** (X2 and the verification gates) last.

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Service (Python) | 6 | 6 | 0 | 0 |
| UI (JS/CSS) | 7 | 7 | 0 | 0 |
| Docs and verification | 2 | 2 | 0 | 0 |
| **Total** | **15** | **15** | **0** | **0** |

## Links
- [[T-036-summary]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-effort-estimate]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-critique-report]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]]
- Related: [[T-037-summary]] (consumes `layout`) · [[T-031-summary]] (edits `settings.js`)
- [[T-036-analysis]]
