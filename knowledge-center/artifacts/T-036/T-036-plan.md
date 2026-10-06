---
ticket: "T-036"
artifact: plan
---

# Plan: T-036

Source of truth for scope: [[T-036-requirements]] (frozen iteration 3; 8 FRs, 81 ACs tagged [PY] 46 · [BROWSER] 31 · [DOC] 4, 12 NFRs, 16 BRs). Q1-Q5 are open and non-blocking; this plan uses their recorded defaults (live pickup on, sidecar check included as a droppable SHOULD, idle 30 s, delete the local copy after import, every key shared). Plan-stage decisions are D-22..D-31 in [[T-036-decision-log]].

## Approach

1. **Two independent halves, prefs first.** The preference store is built before the version reload because [[T-037-summary]]'s `layout` depends on the `C.prefs` contract and because the reload half reuses the heartbeat handler the prefs half creates (D-22; analysis § Recommended Path).
2. **Server pure, page thin.** Validation, import, reset and the version digest are pure Python modules proven by unit tests (`prefs_store.py`, `ui_version.py`); the plugin and `shell_feature.py` only wire them. Every JS behaviour sits behind a source-regexp test because there is no JS runner and CI installs no Node (D-1..D-21 in the decision log fixed the shapes).
3. **Safety by construction.** No automatic reload discards typed text (generic dirty-field rule plus `Console.holdReload` for off-DOM state, D-11, D-12); no new timer for the version check (D-25); prefs writes are debounced deltas that never overwrite another key (D-15, D-21).
4. **Shared dirty tree.** Six files carry other tickets' uncommitted hunks; every task that touches one carries the surgical-edit rule and a diff check against the step-zero snapshot (NFR-9, D-27).
5. **Honest verification.** [PY] criteria are proven by named tests with exact counts; the 31 [BROWSER] criteria get a testable surface from a builder task and stay "not verified in a browser" until a person runs them (task 21 hands them off).

**tech-select:** none required. Every choice the slices imply is `confirm-existing`: stdlib `json`, `hashlib`, `threading`, `glob`, `os.stat`; `tomlio._replace`; browser `fetch` with `keepalive`; vanilla ES5. AC-61 pins that `console/requirements-dev.txt` and any package manifest stay unchanged.

## Structure

**Multi-layer.** Reason: 15 components across the Python server, the browser UI, the desktop sidecar and docs; 23 tasks; a real dependency chain (store → plugin → payload → client contract → router → reload logic). Chain run: `analyze-components` ([[T-036-components]]) → `estimate` upfront ([[T-036-effort-estimate]]) → `breakdown-tasks` ([[T-036-task-breakdown]], [[T-036-implementation-plan]]) → `challenge-plan` ([[T-036-critique-report]] § Plan critique, [[T-036-plan-iteration-log]]).

## Build protocol (binding on the builder)

- **First action (task 00):** run `PYTHONUTF8=1 python console/kanban.py ticket move T-036 in-progress`. The builder runs it, not the planner or harness-at-plan-time. Every `console/kanban.py` call uses `PYTHONUTF8=1`: `console/kanban.py context` crashes on cp1252 `→` without it, and that crash belongs to a separate session. **Do not fix `kanban.py` here.** Tracker files (`*.toml`) change only through `console/kanban.py`, never by hand.
- **After every task:** `progress-tracker` with `task_id`, the evidence line (test files and `N passed`, or "source tests only; JS not run") and the files actually changed. A delegated agent's status line is a claim, not evidence (memory `subagent-status-not-evidence`): check `git status`, the named files and the pytest count before marking `[x]`.
- **Cap rule:** a task is 0.5 to 3 h. If it will not fit, stop, record it in progress.md and run `replan`; never stretch.
- **Never:** commit, push, stash, checkout, revert, `git add`, or use worktree isolation. The tree is shared and dirty. `git diff`/`git status` are read-only and allowed.
- **No new dependency:** stdlib Python; vanilla ES5 IIFE JS (`var`/`function`, `C.el`, no `=>`, no statement-leading `let`/`const`, no `innerHTML` templates, no build step); comments say why.
- **Python 3.11-clean** (CI runs 3.11 and 3.13; local is 3.14, which is **not** evidence for 3.11): no PEP 695 `type`/generic syntax, no nested same-quote f-strings, no `datetime.UTC`, no 3.12+ stdlib names. Task 22 scans for these and says "3.11 not run locally" unless `py -3.11` exists.

## Evidence conventions (used by every Done-criteria below)

- **PY** = from the repo root, `PYTHONUTF8=1 python -m pytest -o addopts="" <files> -q`; record the final `N passed` line. (`pytest.ini` sets `-q`, which prints bare dots; `-o addopts=""` gives a trustworthy count, memory `subagent-status-not-evidence`.) "At least N tests" means N named tests exist and pass; the builder records the real count. Tests build a throwaway workspace with the `repo` fixture (`console/tests/conftest.py`); **no test writes the real checkout's `console/.cache/prefs.json`**.
- **JS** = Python source-regexp tests (pattern `test_plugins.py:227-285`). Where `node` is on PATH, `node --check console/static/<file>.js` is run for syntax only and reported as "not a CI check"; if absent say "not run". A scratch Node smoke of the pure prefs logic in the session scratchpad may supplement evidence but is never committed and never replaces a [BROWSER] check.
- **[BROWSER]** criteria cannot be run by the build pipeline. A builder task creates the testable surface; the criterion stays "not verified in a browser" until a person or a driven browser runs it (task 21 lists all 31).
- **Test files by slice** (new, none touches `conftest.py`, D-31): `test_prefs_store.py` (01, 02) · `test_prefs_routes.py` (03, 04) · `test_ui_version.py` (05) · `test_config_payload.py` (06, 19) · `test_prefs_client_source.py` (07-10) · `test_ui_constraints.py` (07) · `test_prefs_wording.py` (11-13) · `test_reload_source.py` (15-18) · `desktop/tests/test_sidecar.py` (20, extended).
- **Always green:** `console/tests/test_stylesheet.py` and `console/tests/test_plugins.py` after every task that touches CSS, JS class names or `plugins.toml` (AC-62).

## Shared-file rules (plan rules; repeated in each affected task's Done-criteria)

The tree has about 15 uncommitted files from other tickets (git status at plan time). Foreign hunks are listed here by anchor; task 00 snapshots them and the verifier diffs against the snapshot (AC-63).

| File | Foreign hunks (line numbers as read at plan time, will drift) | This ticket's tasks | Rule |
|------|------|------|------|
| `console/static/app.js` | boot `.then` incl. `ConsoleOnboarding.maybeOpen()` (~l.329-346); `setTitle` (~l.371-380); `ConsoleApp` export (~l.382-384) | 10, 16, 17, 18 | edit AROUND them; new functions go between `watchConnection` and `/* global keys */`; do not rewrite or reformat the export (nothing needs adding to it) |
| `console/static/settings.js` | "Setup wizard" `again` row in `storage()` (~l.1756-1768); `identity()` panel (~l.1652-1725); `render()` push; T-031 edits `assistant()` (~l.952-1555) | 11, 12 | keep `again` and `restore` byte-identical; touch only the lines named; T-031 also edits this file: re-read before every Edit, retry on conflict |
| `console/server/features/shell_feature.py` | `from .. import onboarding_setup` (l.13) and `onboarding_setup.display_title(...)` (l.59) | 06, 19 | edit only inside `apply()`/`config()` payload lines; foreign lines untouched |
| `console/server/audit.py` | `"onboarding.setup", "onboarding.complete"` (l.85-86) | 04 | insert the two names after `"workspace.clean",` and before the foreign "Setup wizard" lines; edit only after the hunk matches the snapshot (settled) |
| `console/static/styles.css` | ~80 `.ob-*` lines appended at the END (~l.2201+) | 14 | **never append**; insert mid-file next to `.toast` (~l.1851-1858); no duplicate bare single-class selector |
| `console/static/index.html` | the `onboarding-wizard.js` tag (~l.71-72) | none | this ticket adds no script; T-037 adds `splitter.js` |

**Do not touch** (other tickets): T-031 owns `desktop/src-tauri/src/stt.rs`, `audio.rs`, `piper.rs`, `cue.rs`, `bridge.rs`, `console/server/assistant_config.py`, `native_bridge.py`, `features/assistant_feature.py`; no task and no changed file is under `desktop/src-tauri/` (AC-60). T-037 owns `splitter.js` and its `agents.js`/`vault.js`/`board.js`/`index.html` edits; this ticket's `agents.js` change is one top-level call (task 15). Also foreign: `console/static/onboarding-wizard.js`, `console/server/onboarding*.py`, `setup_editor.py`, `dotenv.py`, `console/config/agents.toml`, `console/kanban.py`, `console/static/overview.js`.

**Builder rule for every edit of a shared or clean-but-contended file:** re-Read the file immediately before each Edit; keep edits small and local; retry on conflict; no reformatting; never revert, stash, checkout, `git add` or commit; no worktree isolation. After the task, `git diff -U0 <file>` must still contain every foreign hunk recorded by task 00, byte-identical.

**Attributing hunks (CR-28):** other tickets keep editing these files while this one builds, so a single end-of-ticket comparison cannot tell a hunk this ticket moved from one its owner legitimately advanced. Therefore, before the first Edit of every task that touches a shared file, copy the file to `console/.cache/t036-prebuild/<name>.pre-<NN>` (NN = the task number); after the task, `git diff --no-index <name>.pre-<NN> <file>` must show only this task's hunks, and the changed line ranges are written into that task's progress entry. A foreign hunk that differs from the task-00 snapshot is then reported as "changed since snapshot, not by this ticket" only if no per-task diff touches it.

**Checkpoint (CR-30):** seven tasks sit at the 3 h cap with no slack. After task 10 (end of the prefs half) run `estimate(mode=forecast)`; at any task that will not fit, stop and `replan` rather than stretch.

## Slices

| Phase | Slice | Tasks | Delivers |
|-------|-------|-------|----------|
| 0 Step zero | 0a | 00 | lane move, baselines, pre-build snapshots |
| 1 Preference store | 1a-1b | 01-04 | pure store, import/reset, plugin and routes, audit actions |
| 2 UI version stamp | 2a | 05-06 | digest, `ui_version` + `prefs_rev` on `/api/config` |
| 3 Client preferences | 3a-3b | 07-10 | `C.prefs` read side, write-through, migration/Reset, boot and live pickup |
| 4 Settings and wording | 4a-4b | 11-13 | Saved preferences panel, stale statements, docs |
| 5 Reload when safe | 5a-5b | 14-18 | notice style, hold registry, compare/notice, idle/busy, loop guard |
| 6 Sidecar identity (droppable) | 6a | 19-20 | `workspace` field, `ensure()` attach check |
| 7 Release and verification | 7a | 21-22 | relaunch note, verification plan, gates |

## Tasks

### [x] T-036-00 — Step zero: move the ticket to in-progress, record baselines, snapshot the shared files (0.5 h)
- [x] `PYTHONUTF8=1 python console/kanban.py ticket move T-036 in-progress` (the builder runs this)
- [x] baseline `PYTHONUTF8=1 python -m pytest -o addopts="" -q` (about 4 min, memory `subagent-status-not-evidence`); record total, failed and the names of any pre-existing failures (the tree carries other tickets' untracked tests such as `console/tests/test_onboarding_setup.py` and `test_voice_assets_*.py`)
- [x] for each of `console/static/app.js`, `settings.js`, `index.html`, `styles.css`, `console/server/features/shell_feature.py`, `console/server/audit.py`: copy to `console/.cache/t036-prebuild/<name>.orig` and write `git diff -U0 -- <file>` to `<name>.diff` (later tasks add `<name>.pre-<NN>` copies before each shared-file edit, § Shared-file rules); record each file's sha256 and `git status --short` (the foreign-dirty set) in progress.md; confirm the directory is gitignored (`git check-ignore -v console/.cache/t036-prebuild/app.js.orig`)
- [x] record `python --version`, whether `py -3.11` exists, and whether `node --version` works (used for `node --check` and the scratch smokes in tasks 08, 09, 17, else "not run"); record the plan-time counts of `setInterval(` (expected 2) and `setTimeout(` (expected 1) in `console/static/app.js`, which tasks 10, 16, 17 pin
- **Files may touch:** none in the product tree; `console/.cache/t036-prebuild/` (gitignored); `T-036-progress.md` via `progress-tracker`
- **Done-criteria:** `ticket move` output shows lane `in-progress` and `PYTHONUTF8=1 python console/kanban.py context T-036` no longer reports a stale lane; progress.md holds baseline pytest total/failed and the pre-existing failure list (or "none"), six file hashes, the foreign-dirty list and the tool versions; every number is copied from command output, none estimated; `git status --short` shows no change to any product file made by this task.
- **Basis:** one long command (pytest about 4 min) plus six copies and diffs; no code. Range 0.4-0.75 h.
- **Split because:** a process step that must precede every build task (hard handoff) and fixes the yardstick for "baseline failure" and "foreign hunk" (AC-63 names a pre-build snapshot in the plan).
- **Depends on:** —

### [x] T-036-01 — `prefs_store.py`: read, validate, set/del with `{rev, prev}`, locked atomic write (3 h)
- [x] new pure module `console/server/prefs_store.py`: store path `console/.cache/prefs.json` via `paths.resolve_rel`; constants for the key pattern `^[A-Za-z][A-Za-z0-9_.-]{0,63}$`, 32768 bytes per value (UTF-8 length of the `json.dumps(..., allow_nan=False)` text), 128 keys, 262144 bytes for the file
- [x] `read(repo_root)`: missing, empty, non-UTF-8, non-JSON or wrong-shape file reads as `{v:1, rev:0, prefs:{}, import_closed:false}`; never raises
- [x] `snapshot(repo_root)` returns `{prefs, rev, import_open}`; `rev(repo_root)` returns the integer
- [x] `apply(repo_root, set=None, delete=None)`: validates every key and value first (all-or-nothing, `ValueError` with a sentence naming the key and the cause), then under one module `threading.Lock` reads, applies, and writes JSON to `prefs.json.tmp` then `tomlio._replace`; returns `{rev, prev}`; `rev` increments only when stored state actually changed (deep equality); `set` must be an object, `del` a list of valid keys
- [x] Python 3.11-clean; no new import beyond `json`, `os`, `re`, `threading`, `tomlio`, `paths`
- **Files may touch:** `console/server/prefs_store.py` (new), `console/tests/test_prefs_store.py` (new)
- **Done-criteria:** PY `test_prefs_store.py` at least 16 tests, 0 failed, each named for its AC: AC-24 (no file gives `{prefs:{}, rev:0, import_open:true}`); AC-25 (set stored, del applied, `prev` equals the rev before the call, an equal set leaves `rev == prev`); AC-26 (`theme` and `a.b-c_d` accepted; empty, `1x`, `a b`, `../x`, a 65-character key refused with `ValueError`, nothing written); AC-27 (32768-byte value accepted, 32769 refused; 129th key refused; a write taking the file past 262144 bytes refused; `NaN` and `Infinity` refused; non-object `set` and non-list `del` refused); AC-28 (one valid plus one invalid key writes neither); AC-29 (missing, empty, corrupt file reads empty, the next write replaces it); AC-30 (8 threads each setting a distinct key leave all 8 keys and valid JSON, and `tomlio._replace` is the call that lands the file, asserted with a recording wrapper); AC-31 (store path is under `console/.cache/` and `.gitignore` contains `console/.cache/`); AC-44 store half (`layout` holding a 32 KB object is stored and returned, `del` removes it). No test touches the real checkout. `grep -n "tomllib\|match \|type " console/server/prefs_store.py` shows no 3.12-only construct.
- **Basis:** about 170 production lines and 220 test lines; the threaded and boundary tests dominate. Range 2.25-3.75 h.
- **Split because:** a self-contained deliverable that every later server task and the whole client builds on, with its own unit tests (AC-24..31).
- **Depends on:** T-036-00

### [x] T-036-02 — `prefs_store.py`: `import_values` and `reset` (2 h)
- [x] `import_values(repo_root, values)` returns `{prefs, rev, imported, skipped, rejected, closed}`: when the import window is closed import nothing and return `closed:true`; per key: invalid key or over-cap value goes to `rejected` as `{key, reason}`; a key past the file or key-count cap rejects the overflow keys and keeps the earlier ones; an absent key is stored (`imported`); a key whose stored value is deep-equal is reported in `imported` without a `rev` change; a different stored value goes to `skipped` and stays unchanged; one `rev` bump per call at most
- [x] `reset(repo_root)` returns `{prefs:{}, rev, closed:true}`: empties prefs, sets `import_closed`, bumps `rev` when anything changed
- [x] both under the same lock and atomic write as `apply`
- **Files may touch:** `console/server/prefs_store.py`, `console/tests/test_prefs_store.py`
- **Done-criteria:** PY `test_prefs_store.py` grows by at least 8 tests, 0 failed: AC-46 (empty server imports every valid key, `skipped` and `rejected` empty; repeating returns the same `imported`, unchanged `rev`); AC-47 (stored `theme=dark`, import `theme=light` plus `voice`: `voice` imported, `theme` skipped and unchanged); AC-48 (after `reset`, `import` returns `closed:true`, imports nothing, `GET` snapshot shows `import_open:false`); AC-49 store half (`reset` empties, bumps `rev`, sets `import_closed`); AC-75 (`1x`, a 32769-byte value and a valid key in one call: valid imported, the other two in `rejected` with a reason each, only the valid one stored; an import that fills the file past the cap rejects the overflow keys, not earlier ones); AC-80 (two threads importing the same values interleaved end with the same stored state, the same `imported` list each, `rev` bumped once). Total `test_prefs_store.py` count recorded.
- **Basis:** about 90 production lines and 130 test lines. Range 1.5-2.75 h.
- **Split because:** an independently reviewable piece (the migration rule, BR-3/BR-4) whose semantics the client's migration (task 09) must match exactly.
- **Depends on:** T-036-01

### [x] T-036-03 — `prefs_feature.py`: four routes, provider, `plugins.toml` row; router-level and real-HTTP tests (3 h)
- [x] new `console/server/features/prefs_feature.py` with `PLUGIN = Plugin(id="prefs", apply=apply, summary=...)`, no `requires`, no `register_tab`; routes `GET ^/api/prefs/?$` (`prefs.get`), `POST ^/api/prefs/?$` (`prefs.post`), `POST ^/api/prefs/import/?$` (`prefs.import`), `POST ^/api/prefs/reset/?$` (`prefs.reset`); `ctx.provide("prefs", prefs_store)` so `shell_feature` can read `rev` without importing the module
- [x] handlers read `req.body`; `prefs.import` and `prefs.reset` call `audit.record(req.repo_root, "prefs.import" | "prefs.reset", actor=audit.actor_of(req), detail={key names and counts only})`; a routine `POST /api/prefs` records nothing
- [x] one `[[plugin]]` row in `console/config/plugins.toml` (after `workspace`, before `shell`): `id = "prefs"`, `module = "features.prefs_feature"`, `enabled = true`, with a why-comment (view state shared by the app and every browser; no tab; `enabled = false` makes clients fall back to `localStorage`)
- [x] real-HTTP test: a subclass `class H(httpd.Handler)` with `repo_root` and `router` set on the subclass, `ThreadingHTTPServer(("127.0.0.1", 0), H)` in a daemon thread, `urllib.request` calls, and `shutdown()`/`server_close()` in a `finally` (no existing test instantiates `httpd.Handler`)
- **Files may touch:** `console/server/features/prefs_feature.py` (new), `console/config/plugins.toml` (one row only), `console/tests/test_prefs_routes.py` (new; carries a local copy of the 15-line `app` fixture and `call()` helper from `test_ui_endpoints.py:38-75`, because fixtures there are module-local and `conftest.py` is shared)
- **Done-criteria:** PY `test_prefs_routes.py` at least 10 tests, 0 failed, and `test_plugins.py` plus `test_stylesheet.py` still pass: the four routes resolve (`app.router.resolve`); AC-24 and AC-25 through `call()` (response shapes `{prefs, rev, import_open}` and `{rev, prev}`); AC-33 (shipped `plugins.toml` has the `prefs` row without `requires`, the module imports and exposes `PLUGIN`, no `register_tab` in its source, the plugin id equals the row id); AC-34 over a real in-process server (POST without `X-Console-Request: 1` returns 403, with it returns 201); AC-36 (a source scan of `console/server/**/*.py` finds `prefs_store`, `".cache/prefs.json"` or `provider("prefs")` only in `prefs_store.py`, `prefs_feature.py` and `shell_feature.py`); AC-32 route half and AC-49 audited (a monkeypatched `audit.record` sees exactly one `prefs.import` and one `prefs.reset` call, detail has key names and counts and no value text; a routine set sees none); `enabled = false` in a scratch `plugins.toml` removes the routes (`routed()` false). `git diff -U0 console/config/plugins.toml` shows one added row block and nothing else.
- **Basis:** about 110 production lines and 200 test lines; the real-HTTP harness is first of its kind here (adder noted in [[T-036-effort-estimate]]). Range 2.25-3.75 h.
- **Split because:** a different layer (routes and transport) with its own harness, and the first real-HTTP test in the repo.
- **Depends on:** T-036-02

### [x] T-036-04 — Register `prefs.reset` and `prefs.import` in `audit.ACTIONS` (1 h)
- [x] re-Read `console/server/audit.py` and compare its `git diff -U0` with `console/.cache/t036-prebuild/audit.py.diff`; proceed only if the foreign hunk is unchanged (settled, NFR-9); if it moved, note it in progress.md and defer this task to just before task 11 (nothing depends on it)
- [x] insert `"prefs.reset", "prefs.import",` with a why-comment (view-state reset and migration, key names and counts only) as new lines after `"workspace.clean",` and before the foreign "Setup wizard" comment lines, leaving every foreign line byte-identical
- **Files may touch:** `console/server/audit.py` (foreign hunk), `console/tests/test_prefs_routes.py`
- **Done-criteria:** PY `test_prefs_routes.py` grows by at least 3 tests, 0 failed (pattern `test_notify_audit.py:268`): AC-32 both names are in `audit.ACTIONS`; a real `audit.record` into the scratch workspace's audit directory writes lines whose `detail` holds key names and counts and whose raw text contains none of the stored values; a routine `POST /api/prefs` writes no audit line. `git diff -U0 console/server/audit.py` differs from the snapshot only by the added names and their comment; the foreign `onboarding.setup`/`onboarding.complete` lines are unchanged.
- **Basis:** one tuple edit and three tests; the check against the snapshot is the careful part. Range 0.75-1.5 h.
- **Split because:** a foreign-dirty file whose edit must wait for its hunk to settle (NFR-9, D-19), so it is a separate, movable step.
- **Depends on:** T-036-03

### [x] T-036-05 — `ui_version.py`: stat-only digest, once-per-process manifest digest, vanish and unlistable rules (2 h)
- [x] new pure module `console/server/ui_version.py`: `ASSET_PATTERNS = ("*.html", "*.js", "*.css", "*.png")` enumerated with `glob.glob` exactly like `export._copy_frontend` (`export.py:90`) so the two sets cannot drift; regular files only; `(basename, st_size, st_mtime_ns)` sorted; per-file `OSError` (a vanished file) skips that file; `compute(static_dir, manifest_digest)` returns the first 12 lowercase hex of sha256, or `None` when the directory cannot be listed
- [x] `manifest_digest(tabs, routes)`: sha256 of canonical JSON (`sort_keys=True`) of the tab rows and the route `(method, pattern, name)` list
- [x] `class UiVersion(static_dir, manifest_fn)` with `value()`: calls `manifest_fn` lazily once and memoises it (the manifest cannot change without a restart), recomputes the static half on every call, no caching of it, opens no file
- [x] `export.py` is **not** edited (D-28); parity is asserted by a test
- **Files may touch:** `console/server/ui_version.py` (new), `console/tests/test_ui_version.py` (new)
- **Done-criteria:** PY `test_ui_version.py` at least 11 tests, 0 failed: AC-1 shape (12 lowercase hex); AC-2 (two calls, no change, same value); AC-3 (size change, mtime-only change via `os.utime`, file added, file removed each change the value); AC-4 (`*.swp` and `*.txt` added, touched, removed leave it unchanged); AC-5 (different tab set or route table gives a different `manifest_digest`; a counting `manifest_fn` runs once over repeated `value()` calls); AC-6 (with `builtins.open` monkeypatched to raise, `value()` still returns a value); AC-7 (the stamp's name set for the shipped `console/static` equals the names `export._copy_frontend` copies into a temp dir, and `"ui_version"` does not appear in `export.py` source, BR-7); AC-67 (one file made to raise `FileNotFoundError` on `stat` is skipped without an exception; a nonexistent directory gives `None`). `grep -n "open(" console/server/ui_version.py` is empty.
- **Basis:** about 70 production lines and 160 test lines. Range 1.5-2.75 h.
- **Split because:** a pure self-contained module with no dependency (a root), parallelisable in principle and reviewed apart from the foreign-dirty payload file.
- **Depends on:** T-036-00

### [x] T-036-06 — `shell_feature.config()` adds `ui_version` and `prefs_rev`; payload tests (1.5 h)
- [x] re-Read `console/server/features/shell_feature.py` first; in `apply(ctx)` build one `UiVersion(STATIC_DIR, lambda: manifest_digest(ctx.tabs(), ctx.router.describe()))` (static dir constant owned by `ui_version.py`, the same directory `httpd.py:25` and `export.py:35` point at)
- [x] in `config()` add `"ui_version": value` only when `value()` is not `None`; add `"prefs_rev": ctx.provider("prefs").rev(ctx.repo_root)` only when `ctx.has_provider("prefs")`; `title, subtitle, tabs, boards, stale_days` unchanged
- [x] foreign lines (`from .. import onboarding_setup`, the `onboarding_setup.display_title(...)` title expression) untouched
- **Files may touch:** `console/server/features/shell_feature.py` (foreign hunk), `console/tests/test_config_payload.py` (new)
- **Done-criteria:** PY `test_config_payload.py` at least 6 tests, 0 failed, with `test_ui_endpoints.py`, `test_plugins.py`, `test_stylesheet.py` still green (record each count): AC-1 through the `call()` pattern (`ui_version` present and 12 lowercase hex, the five existing keys keep their shape); AC-35 (`prefs_rev` equals the store `rev` after a set, and is absent when a scratch `plugins.toml` sets the `prefs` row `enabled = false`); AC-67 route half (with the static directory pointed at a nonexistent path the other keys are still returned and `ui_version` is absent); the static export manifest (`export._export_manifest`) has no `ui_version` or `prefs_rev` (BR-7). Measured payload growth in bytes is written to progress.md (NFR-4, recorded, not asserted). `git diff -U0` of the file differs from the snapshot only inside `apply()`/`config()`.
- **Basis:** about 15 production lines and 110 test lines; most of the time is the scratch-workspace fixtures and the careful edit. Range 1-2 h.
- **Split because:** a foreign-dirty file edited once for both fields (fewest touches); separate from the pure module so a collision costs one small retry.
- **Depends on:** T-036-03, T-036-05

### [x] T-036-07 — `core.js`: in-memory `C.prefs`, deep-clone `get`, local mode, `hydrate()` with a 3 s bound, `all/keys/mode/rev/onChange` (3 h)
- [x] re-Read `console/static/core.js`; replace the `prefs` object at `core.js:444-458` (and its "browser-local" comment) with a block that keeps `get(key, fallback)`, `set(key, val)`, `del(key)` exactly (synchronous; absent key gives the fallback, a stored `null` gives `null`; `get` returns a deep clone via `JSON.parse(JSON.stringify(v))`)
- [x] **local mode** (`C.IS_STATIC`, or `/api/prefs` unreachable or 404): the exact old behaviour against `localStorage["console." + key]` (keep the old try/catch bodies); **server mode**: reads and writes go to a private map; add `hydrate()` (never rejects), `all()` (clone of the map; in local mode the parsed `console.*` entries), `keys()`, `mode()`, `rev()` (number or `null`), `onChange(fn)` (listeners get an array of changed key names; used by `refresh()` and a late hydrate)
- [x] `hydrate()`: static returns a resolved promise with mode `"local"`; otherwise `C.get("/api/prefs")` raced with a one-shot 3 s bound (`HYDRATE_BOUND_MS = 3000`, D-17); success stores `prefs`, `rev`, `import_open` and sets mode `"server"`; a 404 or error leaves local mode silently; on timeout it resolves as unreachable and a late success is applied through `onChange` (changed keys computed against the map); a `set`/`del` made before hydration completes is re-applied over the hydrated map
- [x] mirror constants the server enforces: key pattern `^[A-Za-z][A-Za-z0-9_.-]{0,63}$` and `32768` (used by task 08)
- [x] **safe intermediate state (CR-27):** static files are served per request (`httpd.py:94-115`) and the route from task 03 exists in the tree, so a server restart between tasks 07 and 09 would put a half-built client in server mode with no write-through. Until task 09 flips it, an internal constant `SERVER_PREFS = false` makes `hydrate()` resolve as unreachable (local mode, exact old behaviour); task 09's last step sets it to `true`
- [x] no read of a preference at script-evaluation time (BR-13); `C.prefs` stays exported unchanged in the return object
- **Files may touch:** `console/static/core.js`, `console/tests/test_prefs_client_source.py` (new), `console/tests/test_ui_constraints.py` (new)
- **Done-criteria:** PY `test_prefs_client_source.py` at least 5 tests and `test_ui_constraints.py` at least 4 tests, 0 failed: AC-37 part (`core.js` prefs block defines `get: function (key, fallback)`, `set`, `del` with their old signatures and adds `hydrate`, `all`, `keys`, `mode`, `rev`, `onChange`; `refresh` and `reset` are added by task 09, where the same test is extended to the full list); AC-74 part (the 3000 ms bound constant, the key pattern text and `32768` exist in `core.js`); AC-44 client contract (`get` clones: the source uses a JSON round trip, and `layout` is not special-cased); AC-61 (no `=>` and no statement-leading `let`/`const` in any `console/static/*.js`, no `package.json` under the repo root or `console/`, `console/requirements-dev.txt` has no added lines versus the task-00 hash); `grep -n "prefs\.\(get\|set\)(" console/static/core.js` shows reads only inside functions. Where `node` exists, `node --check console/static/core.js` passes (reported as not a CI check). [BROWSER] AC-40, AC-43, AC-73 have their testable surface; they stay "not verified in a browser". `test_stylesheet.py` and `test_plugins.py` green. `core.js` diff outside the prefs block is empty.
- **Basis:** about 130 lines of JS replacing 15, plus about 100 test lines; deep-clone and hydrate-race semantics dominate. Range 2.25-3.75 h.
- **Split because:** the first and riskiest client step: it proves the unchanged-interface contract (BR-13) and the local fallback before write-through builds on it.
- **Depends on:** T-036-03

### [x] T-036-08 — `core.js`: debounced write-through, key and size mirror, keepalive flush, retry, 400 rule, `post` error status (3 h)
- [x] server-mode `set`/`del`: update the map at once, then queue a delta (a later set wins, set then del becomes del, a set equal to the current value queues nothing); invalid key or value over 32768 UTF-8 bytes stays in memory only, is never queued, and toasts once per key per session with a sentence naming the key and the cause (`C.toast(..., "err")`)
- [x] 250 ms trailing debounce (`FLUSH_MS = 250`) coalescing into one `C.post("/api/prefs", {set, del})`; success adopts the response `rev` only when `res.prev` equals the rev the client last knew (D-21), otherwise keeps its older rev so the next heartbeat's mismatch triggers `refresh()`; entries re-set while a request is in flight stay pending
- [x] failure keeps deltas queued and retries on the next `set`, on `C.onConnection(true)` (registered once at module init) and through a public `flush()` the heartbeat calls (task 10); `pending()` returns true while deltas are queued; a 400 drops that batch once with a toast
- [x] `core.js` `post`: one additive line so the thrown `Error` carries `status` (`res.status`), letting the client tell a 400 from a network failure (D-29)
- [x] page hide: `pagehide` and `visibilitychange` to hidden call a keepalive flush: `fetch("/api/prefs", {method: "POST", keepalive: true, headers: {"Content-Type": "application/json", "X-Console-Request": "1"}, body})` when the serialised body is at most 60,000 bytes; otherwise one request per key; a single value above 60,000 bytes goes without `keepalive` (best effort). `sendBeacon` is never used (it cannot carry the CSRF header)
- [x] pre-hydration sets are flushed after hydration; static mode makes every flush path a no-op
- **Files may touch:** `console/static/core.js`, `console/tests/test_prefs_client_source.py`
- **Done-criteria:** PY `test_prefs_client_source.py` grows by at least 6 tests, 0 failed: AC-39 (`keepalive: true`, the `X-Console-Request` header and `pagehide`/`visibilitychange` in the prefs block; the string `sendBeacon` appears in no file under `console/static`); AC-74 (`onConnection(` registered inside the prefs block, `60000`, `FLUSH_MS = 250`, key pattern, `32768`, `res.prev` adoption check, `err.status` or equivalent in `post`); no `setInterval` is added in `core.js`; `post`'s existing signature and behaviour for callers is unchanged (the only diff in that function is the added status line). `node --check console/static/core.js` passes where available. Source tests pin that strings exist, not that coalescing works, so when `node` exists a scratch smoke (session scratchpad, **not committed**, stub `window`/`localStorage`/`fetch`/timers) exercises: 40 sets of one key within 250 ms produce one POST body; set-then-del coalesces to del; a failed flush keeps the delta and a later `set` retries it; an oversize value is never queued; `res.prev !== lastRev` leaves `rev()` unchanged. Its result line is recorded ("N checks passed" or "node not available"; CR-26). [BROWSER] AC-42, AC-71, AC-72 have their surface and stay "not verified in a browser". `test_stylesheet.py` and `test_plugins.py` green.
- **Basis:** about 150 lines of JS and 90 test lines; the in-flight/coalescing rules and the keepalive split dominate. Range 2.25-3.75 h.
- **Split because:** an independently reviewed piece carrying the write-flood and data-loss risks (R-3, R-4 in § Risks).
- **Depends on:** T-036-07

### [x] T-036-09 — `core.js`: migration import, closed window, `reset()`, `refresh()` (3 h)
- [x] **migration runs inside the `hydrate()` chain, before it resolves, whenever local keys exist** (CR-29: a browser holding `theme=dark` against an empty server must paint dark on that first load, not default and then correct itself; an app with no local keys pays nothing), under the same 3 s bound: collect `localStorage` keys starting `console.` whose remainder matches the key pattern; an unparsable value is removed silently (BR-16); if there are none, skip; if the server reported `import_open === false`, delete them without importing and show one info toast "Old settings in this browser were discarded because preferences were reset."; otherwise `C.post("/api/prefs/import", {values})`; if the bound expires first, the late result is applied through `onChange` with the changed key names
- [x] on the response: replace the map and `rev` with the returned ones and re-apply any queued deltas over it; delete the imported, skipped and rejected local keys only after the acknowledgement; toast one sentence per skipped key naming the key and this browser's value (truncated), one per rejected key naming the key and the reason; `closed:true` deletes and shows the info toast; a failed import keeps the keys and retries on the next boot; a `set` made while the import is in flight survives it (AC-81)
- [x] `reset()` (returns a promise): discard queued deltas and the debounce timer, `C.post("/api/prefs/reset", {})`, then clear the map, adopt `rev`, mark the window closed and remove legacy `console.*` local keys; local mode removes every `console.*` key; a failure rejects with an `Error` the caller can toast
- [x] `refresh()`: only when `mode()` is `"server"` and `pending()` is false, `C.get("/api/prefs")`, replace map and `rev`, call `onChange` listeners with the changed key names; with deltas pending it resolves with no request
- [x] **last step:** set `SERVER_PREFS = true` (introduced as `false` in task 07, CR-27); from here a restarted server puts the page in server mode with write-through, migration and Reset all present
- **Files may touch:** `console/static/core.js`, `console/tests/test_prefs_client_source.py`
- **Done-criteria:** PY `test_prefs_client_source.py` grows by at least 6 tests, 0 failed: `SERVER_PREFS = true` is asserted (and the same test file's task-07 expectation is updated, not deleted); the strings `"/api/prefs/import"`, `"/api/prefs/reset"`, the closed-window sentence, the skipped and rejected toast handling, and the `res.prev` check (AC-53 core half) are present; `reset` discards pending deltas before posting (source order check); `refresh` returns without a request when `pending()` is true; AC-37 now fully green (all of `get, set, del, hydrate, refresh, all, keys, reset, mode, rev`). `node --check` passes where available, plus a scratch Node smoke (uncommitted, same stubs) when `node` exists: an import into an empty server stub applies `theme` before `hydrate()` resolves; a skipped key yields one toast naming the key; `closed:true` deletes local keys without a POST; `reset()` discards a queued delta; a `set` during an in-flight import survives it; result line recorded (CR-26). [BROWSER] AC-50, AC-51, AC-76, AC-79 (core half), AC-81, AC-45 have their surface and stay "not verified in a browser". `test_stylesheet.py` and `test_plugins.py` green.
- **Basis:** about 140 lines of JS and 80 test lines; the ordering rules (deltas versus import/reset/refresh) are the hard part (CR-25). Range 2.25-3.75 h.
- **Split because:** a different behaviour (migration and Reset) governed by its own accepted-risk rules (BR-3, BR-4, BR-16), reviewed apart from write-through.
- **Depends on:** T-036-08

### [x] T-036-10 — `app.js`: boot waits on hydration, heartbeat live pickup, `buildNav` keydown bound once (2 h)
- [x] re-Read `console/static/app.js`; replace only the opening `C.get("/api/config").then(function (cfg) {` of the boot with `Promise.all([C.get("/api/config"), C.prefs.hydrate()]).then(function (res) { var cfg = res[0];`; leave the function body, the `.catch` and the foreign `ConsoleOnboarding.maybeOpen()` line byte-identical
- [x] add `onHeartbeat(cfg)` as a new function between `watchConnection` and `/* global keys */`; the heartbeat becomes `C.get("/api/config").then(onHeartbeat).catch(function () {})`: when `C.prefs.pending()` call `C.prefs.flush()`; otherwise, when `cfg.prefs_rev !== undefined && cfg.prefs_rev !== C.prefs.rev()`, call `C.prefs.refresh()` (comparison with `!==` only, no `<` or `>`)
- [x] register `C.prefs.onChange` once at boot: a `theme` change calls `applyTheme(C.prefs.get("theme", "system"))`; a `hiddenTabs` change rebuilds the nav only when the value differs (deep-equal against the value `buildNav` last used); never `go()`, so the active tab is not re-rendered even if it was just hidden
- [x] `buildNav`: bind the `keydown` listener once behind a marker attribute on the `#tabs` node (`C.clear` returns the same node, `core.js:193`), so repeated rebuilds do not stack handlers (D-18)
- [x] nothing is added to the `ConsoleApp` export; `setTitle` untouched
- **Files may touch:** `console/static/app.js` (foreign hunks), `console/tests/test_prefs_client_source.py`
- **Done-criteria:** PY `test_prefs_client_source.py` grows by at least 6 tests, 0 failed: AC-38 (the exact string `Promise.all([C.get("/api/config"), C.prefs.hydrate()])` occurs once and `applyTheme(` is called after it and before the `.catch` of that chain); AC-53 (`prefs_rev` compared against `C.prefs.rev()` with `!==`, guarded for `undefined`, and no relational operator on rev); AC-66 part (`app.js` still has exactly the two `setInterval(` calls it had at task 00, and `GET /api/prefs` appears in `core.js` only inside `hydrate`/`refresh`); AC-77 source half (the marker-guarded single `addEventListener("keydown"` for the nav, and no `addEventListener("keydown"` inside the body of `buildNav` outside the guard); the foreign hunks recorded in `console/.cache/t036-prebuild/app.js.diff` (boot `maybeOpen` line, `setTitle`, export) are all still present in `git diff -U0 console/static/app.js`, byte-identical. `node --check console/static/app.js` where available. [BROWSER] AC-41, AC-52, AC-77, AC-79 have their surface and stay "not verified in a browser". AC-41 pass condition (CR-31): the first tab render is already themed because `applyTheme` runs after hydration and before `buildNav`/`go`; the static shell (header, skeleton) is default-themed until JS runs, exactly as today (decision `prefs-client-contract` accepts that cost), and the verifier records what is observed rather than treating that pre-existing flash as a failure. `test_stylesheet.py` and `test_plugins.py` green.
- **Basis:** about 60 lines of JS and 90 test lines; the careful part is editing around three foreign hunks. Range 1.5-2.75 h.
- **Split because:** a different component (the router) in a file with three foreign hunks; it consumes everything in tasks 06-09, so it is its own review.
- **Depends on:** T-036-09, T-036-06

### [x] T-036-11 — `settings.js` `storage()`: "Saved preferences" panel, mode sentences, confirmed Reset, key list from `C.prefs.all()` (2 h)
- [x] re-Read `console/static/settings.js` immediately before editing; rewrite only the body of `storage(repaint)` (~l.1726-1805); keep the `restore` ("Getting started card") block and the `again` ("Setup wizard", "Run setup again") block byte-identical
- [x] panel title **Saved preferences**; key list from `Object.keys(C.prefs.all())` sorted, each row the key and `JSON.stringify` of its value; no `localStorage` access in the function
- [x] server mode (`C.prefs.mode() === "server"`) shows one plain-text sentence: "Shared by the desktop app and every browser tab on this machine. Kept on the server in console/.cache/prefs.json; not committed."; local mode shows "Stored in this browser only." (each sentence is one string, not split across nodes, so a text check can find it)
- [x] **Reset all preferences** behind `window.confirm("Reset every saved preference for the app and all browser tabs? Tickets, chats and other data are not touched.")`; cancel changes nothing; confirm calls `C.prefs.reset()` then `window.ConsoleApp.applyTheme("system")`, `window.ConsoleApp.rebuildNav()`, `C.toast("Preferences reset", "ok")`, `repaint()`; a rejected reset toasts "Could not reset preferences: <cause>" and does not claim success; hint "Also clears the shared copy on the server, so the app and every open tab return to defaults." (server mode; local mode says it clears this browser's saved preferences)
- [x] the panel help note describes the shared copy and that tickets, chats and other data are untouched (replaces `settings.js:1800-1803`)
- **Files may touch:** `console/static/settings.js` (foreign hunks), `console/tests/test_prefs_wording.py` (new)
- **Done-criteria:** PY `test_prefs_wording.py` at least 7 tests, 0 failed (text and source checks on the extracted `storage()` body): AC-54 part ("Saved preferences", the confirm sentence, the server and local sentences, the hint all present; "Affects this browser only. No server data is touched." and the panel title "Stored in this browser" absent); AC-55 part (the `storage()` body has no `localStorage`, calls `C.prefs.all()` and `C.prefs.reset()`, and `window.confirm(` precedes the reset call); the foreign rows' strings "Setup wizard", "Run setup again", "Getting started card", "Show again" are all still present. `git diff -U0 console/static/settings.js` against the task-00 snapshot shows the foreign hunks (`again` row, `identity()`, `render()` push) unchanged and T-031's `assistant()` hunks untouched. `node --check` where available. [BROWSER] AC-56 has its surface and stays "not verified in a browser". `test_stylesheet.py` and `test_plugins.py` green (no new class was added).
- **Basis:** about 70 lines replaced and 90 test lines; the surgical edit inside a function that holds another ticket's row is the care point. Range 1.5-2.75 h.
- **Split because:** a foreign-dirty function with another ticket's row inside it, edited once and reviewed apart from the one-line wording fixes.
- **Depends on:** T-036-09

### [x] T-036-12 — Stale statements: remaining `settings.js` lines, `about.js`, `core.js` comment (1.5 h)
- [x] one line or phrase at a time, re-Read before each Edit: `settings.js:4-9` header comment (the toggles are saved preferences shared through the server; `plugins.toml` stays the committed deployment switch); `:91-92` theme help ("on this browser only — nobody else sees it and no server state changes" is no longer true); `:145-147` tabs help (drop the `localStorage` code node and "invisible to everyone else"); `:153-159` Agent CLIs comment (keep the real distinction: it hides a CLI from the shared picker, it does not remove it from the server); `:264-267` backends help ("is stored in this browser"); `:612` composer comment ("Browser-local")
- [x] `about.js:33` (Settings blurb "stored in this browser only") and `:158-159` ("they hide a tab in your browser only"): say they are saved preferences shared by the app and every browser, and that they only hide a tab from view
- [x] `core.js:256-258` comment ("One localStorage object rather than a key per panel"): one object rather than a key per panel, with no `localStorage` mention
- [x] `export.py:49` is **not** touched (still true in a static export)
- **Files may touch:** `console/static/settings.js` (foreign hunks; only the lines named), `console/static/about.js`, `console/static/core.js` (comment only), `console/tests/test_prefs_wording.py`
- **Done-criteria:** PY `test_prefs_wording.py` grows by at least 4 tests, 0 failed: AC-55 final (`settings.js` contains no `localStorage` anywhere); AC-54 (after removing the single allowed local-mode sentence "Stored in this browser only.", none of "this browser only", "stored in this browser", "Browser-local", "invisible to everyone else", "browser only" remain in `settings.js`; `about.js` has none of "stored in this browser only" or "in your browser only"); the Agent CLIs comment still says it does not remove the CLI from the server. `git diff -U0` per file shows only the named lines changed and every foreign hunk unchanged; `core.js` diff for this task is comment lines only. `test_stylesheet.py`, `test_plugins.py` green.
- **Basis:** about 12 one-line edits across 3 files and 50 test lines; re-reading before each edit is the cost. Range 1-2 h.
- **Split because:** many scattered one-line edits, reviewed apart from the panel rewrite, so a foreign-hunk collision is a small retry.
- **Depends on:** T-036-11

### [x] T-036-13 — Docs and comments: README table, `plugins.toml` header comment, `registry.py` docstring (1 h)
- [x] `console/README.md:571-578` ("Two different off switches"): the Settings column becomes "One person's saved preferences, shared by the app and every browser on this machine" / stored on the server in `console/.cache/prefs.json` (gitignored; `localStorage` only in a static export); keep the rows' structure and the paragraph below it
- [x] `console/config/plugins.toml:13-15` comment: the Settings toggles are per-user saved preferences kept on the server and shared by the app and every browser on this machine, and only hide a tab from view; this file is committed and applies to everyone who pulls the checkout (comment lines only; task 03's `prefs` row is elsewhere in the file)
- [x] `console/server/plugins/registry.py:9-10` docstring: same correction ("per-user, browser-local" is no longer true)
- [x] `onboarding-wizard.js:4` ("Draft answers live in localStorage") is a SHOULD: change it only if `git ls-files console/static/onboarding-wizard.js` shows the file is now tracked and unmodified by others; otherwise write "deferred, file still untracked" in progress.md and the release note
- **Files may touch:** `console/README.md`, `console/config/plugins.toml` (comment lines only), `console/server/plugins/registry.py` (docstring only), optionally `console/static/onboarding-wizard.js` (line 4 only, under the condition above), `console/tests/test_prefs_wording.py`
- **Done-criteria:** PY `test_prefs_wording.py` grows by at least 3 tests, 0 failed: AC-54 (the README two-switches table no longer contains "One person's browser" or a `localStorage` cell as the Settings storage; `plugins.toml` no longer says "stored in one browser"; `registry.py` no longer says "browser-local"); `test_plugins.py` green (the shipped-registry tests re-read `plugins.toml`). `git diff -U0` for each file shows comment or doc lines only. progress.md states whether `onboarding-wizard.js:4` was changed or deferred.
- **Basis:** four text edits and 40 test lines. Range 0.75-1.5 h.
- **Split because:** a different kind of work (docs and comments, no behaviour) owned by the same wording decision as task 12.
- **Depends on:** T-036-12

### [x] T-036-14 — `styles.css`: one hyphenated notice class, inserted mid-file next to `.toast` (0.5 h)
- [x] re-Read `console/static/styles.css`; add one block `.ui-notice` (non-modal bar, fixed to the top edge below the header, `z-index` below the toasts at `styles.css:1851`, uses existing colour tokens, wraps text, keeps the **Reload now** `.btn sm` control reachable; must not cover the drawer's close button) immediately after `.toast.ok` (~l.1858), before the narrow-screen block; no other class is added (the button uses the existing `btn sm`)
- [x] do **not** append anywhere near the end of the file (the ~80 `.ob-*` lines there are another ticket's) and do not edit the print rule at ~l.2129 (it lists the foreign `.ob-scrim`)
- **Files may touch:** `console/static/styles.css` (foreign hunk at the end)
- **Done-criteria:** PY `test_stylesheet.py` passes (record `N passed`; `.ui-notice` is not defined twice at the top level); `grep -n "ui-notice" console/static/styles.css` shows the definition at a line number lower than the first `.ob-scrim` line; `git diff -U0 console/static/styles.css` against the snapshot shows one new hunk in the middle of the file and the `.ob-*` block unchanged. [BROWSER] part of AC-10 and AC-69 get their style here.
- **Basis:** about 12 CSS lines and a diff check. Range 0.4-0.75 h.
- **Split because:** a foreign-dirty file with its own rule (never append) that must land before the JS uses the class (`test_stylesheet.py` fails the other way round).
- **Depends on:** T-036-00

### [x] T-036-15 — `Console.holdReload` in `core.js` and its two registrants in `agents.js` and `todos.js` (1.5 h)
- [x] `core.js`: `holdReload(id, fn)` stores `fn` by `id` (a second call with the same id replaces the first), and `reloadHeld()` returns true when any registered function returns true (a throwing function counts as not holding); both exported on `Console` (D-11)
- [x] `agents.js`: one top-level call after `st` is defined: `"agents.drafts"` is true while any `st.drafts` value is non-blank (`agents.js:49,1296-1298`); `todos.js`: one top-level call: `"todos.new"` is true while `st.newText` is non-blank (`todos.js:22,200-201`). Both at IIFE top level, not inside a function (tab scripts load before `app.js` creates `ConsoleApp`)
- **Files may touch:** `console/static/core.js`, `console/static/agents.js`, `console/static/todos.js`, `console/tests/test_reload_source.py` (new)
- **Done-criteria:** PY `test_reload_source.py` at least 5 tests, 0 failed: AC-17 (`holdReload` is defined exactly once, in `core.js`; `agents.js` and `todos.js` each contain exactly one `holdReload(` call, at IIFE top level, with the ids `"agents.drafts"` and `"todos.new"`; `app.js` contains no `ConsoleApp.holdReload`; `index.html` lists `core.js` before `agents.js`, `todos.js` and `app.js`, read from the `<script src>` tags); the registry reader treats a throwing hold as not held (source check). `git diff -U0` of `agents.js` and `todos.js` is one added call each (T-037 edits `agents.js` too: re-read first). `node --check` where available. [BROWSER] AC-16 has its surface and stays "not verified in a browser". `test_stylesheet.py`, `test_plugins.py` green.
- **Basis:** about 25 lines of JS and 60 test lines. Range 1-2 h.
- **Split because:** a hard dependency of the busy predicate (task 17) and the only edit to tab modules this ticket makes.
- **Depends on:** T-036-09

### [x] T-036-16 — `app.js`: record the boot `ui_version`, compare on heartbeat, reconnect and visibility, show the notice with **Reload now** (3 h)
- [x] re-Read `console/static/app.js`; add new functions between `watchConnection` and `/* global keys */` (not inside the boot `.then`, so its foreign line is untouched): the boot version is read lazily from `state.cfg.ui_version` (`state.cfg` is set once at boot); `checkVersion(cfg)` does nothing when `C.IS_STATIC` or `state.cfg` is not yet set, when the response has no `ui_version` (present then absent is ignored, both absent is nothing); a boot version that was absent followed by a present one counts as changed (D-13, AC-68); a present, different one counts as changed
- [x] `probe()` = `C.get("/api/config").then(onHeartbeat).catch(noop)`, the same request the heartbeat already makes (no new endpoint, no new timer); the heartbeat uses it; `watchVersion()` (called from `watchConnection` after its static early return, so a static export registers nothing) adds `C.onConnection(function (online) { if (online) probe(); })` and one `visibilitychange` listener that calls `probe()` when `document.hidden` is false
- [x] notice: a non-modal element appended to `document.body` once, built with `C.el` as `class: "ui-notice"`, `role: "status"`, a text span and a `button` labelled **Reload now** (keyboard-operable by being a real `button`); **not** a toast (no `C.toast`); three text states held in constants and selected by `setNoticeText(mode)`: ready ("A new version of the console is ready. It reloads when you pause."), busy (says unsaved text will be lost if you reload now, D-20) and paused (says automatic reload is paused; used by task 18)
- [x] `reloadNow()` calls `window.location.reload()` at once regardless of busy rules (BR-15) and never touches the loop guard
- **Files may touch:** `console/static/app.js` (foreign hunks), `console/tests/test_reload_source.py`
- **Done-criteria:** PY `test_reload_source.py` grows by at least 7 tests, 0 failed: AC-8 (`app.js` reads `ui_version` from the boot config and from the heartbeat payload, and the heartbeat no longer discards it); AC-9 (`C.onConnection(` and a `visibilitychange` listener drive `probe()`, registered only after the `C.IS_STATIC` early return); AC-69 (the strings `Reload now`, `role: "status"` and `class: "ui-notice"` are in `app.js`, and the notice code path does not call `C.toast`); the absent-then-present branch exists (a test on the comparison source names both cases); the `.ui-notice` rule precedes the first `.ob-` rule in `styles.css`; no new `setInterval(` or `setTimeout(` in `app.js`: counts stay at the plan-time values 2 and 1 (the builder re-counts at task 00 and records them); `test_stylesheet.py` passes (the class exists in CSS). Foreign hunks in `app.js` are byte-identical to the task-00 snapshot. `node --check` where available. [BROWSER] AC-10, AC-11, AC-12, AC-13, AC-21, AC-23, AC-68 have their surface and stay "not verified in a browser".
- **Basis:** about 90 lines of JS and 110 test lines; the version rules and the no-new-timer/no-new-endpoint constraints are the care points. Range 2.25-3.75 h.
- **Split because:** the largest new behaviour of the ticket, reviewed alone before the safety logic that gates it (tasks 17, 18).
- **Depends on:** T-036-06, T-036-10, T-036-14

### [x] T-036-17 — `app.js`: idle tracker, busy predicate, hidden-window shortcut, reload scheduler with no new timers (3 h)
- [x] activity: a capture-phase listener on `keydown`, `pointerdown`, `wheel`, `touchstart` sets `lastActive = Date.now()` (`pointermove` excluded); a capture-phase `input` listener records `e.target` in a `WeakSet` only when `e.isTrusted` (D-12); `IDLE_MS = 30000`
- [x] `isBusy()` is true when any of: (a) a `textarea` in the DOM has non-blank text, however it got there (dictation and the `/ @ #` picker assign `.value` with no `input` event, `agents.js:695-709,1349`, `composer-pick.js:187`); (b) a text-like `input` or `[contenteditable]` the user typed in (member of the `WeakSet`) is still in the DOM with non-blank text; (c) the focused element is such a field with non-blank text; (d) `document.querySelector(".drawer")` (a DOM check, D-24: no edit to the drawer IIFE, which T-037 rewrites into a dock); (e) `.ob-scrim` present (the setup wizard); (f) `.cp-scrim.on` (the palette); (g) `window.ConsoleVoice` reports `listening()` or `speaking()`; (h) `C.reloadHeld()`. `value !== defaultValue` is **not** used (Settings fills inputs with `.value = ...`, `settings.js:325,329,340,832,988`)
- [x] `maybeReload()` runs only from `onHeartbeat` (every tick) and after the `probe()` that the connection and visibility triggers issue: with a pending version change it sets the notice text to busy or ready, and calls `autoReload()` when not busy and (idle for `IDLE_MS` or `document.hidden`); `autoReload()` is `window.location.reload()` here and gains its guard in task 18. **No `setTimeout` or `setInterval` is added**: the existing 15 s heartbeat is the only clock (D-25)
- **Files may touch:** `console/static/app.js` (foreign hunks), `console/tests/test_reload_source.py`
- **Done-criteria:** PY `test_reload_source.py` grows by at least 9 tests, 0 failed: the idle constant 30000 and the four activity event names (and not `pointermove`); `isTrusted` and `WeakSet` in the typed-input record; the textarea rule does not depend on the `WeakSet` (AC-78 surface); no `defaultValue` comparison anywhere in `app.js` (AC-70 surface); each busy source is referenced in `isBusy` (`".drawer"`, `".ob-scrim"`, `".cp-scrim.on"`, `ConsoleVoice`, `listening()`, `speaking()`, `reloadHeld()`); `document.hidden` appears in the reload decision (AC-18 surface); the reload primitive is `window.location.reload()` (AC-22 surface); AC-66 (counts of `setInterval(` and `setTimeout(` in `app.js` unchanged from task 16's, and no request other than `C.get("/api/config")` added). Foreign hunks byte-identical to the snapshot. `node --check` where available, plus a scratch Node smoke (uncommitted, stub DOM) of `isBusy()` and the version rules when `node` exists: non-blank textarea with no `input` event is busy; an untouched pre-filled text `input` is not; a registered hold that returns true is busy; absent-then-present, present-then-absent and both-absent behave as specified; result line recorded (CR-26). **Selector ownership (CR-37):** each selector the busy predicate reads is checked against its owner's source so a rename fails a test, not a user: `class: "ob-scrim"` in `onboarding-wizard.js` (skipped with a stated reason if that file is absent), `cp-scrim` and the `on` class toggle in `palette.js`, `class: "drawer"` in `app.js`. [BROWSER] AC-14, AC-15, AC-16, AC-18, AC-22, AC-70, AC-78 have their surface and stay "not verified in a browser" (A-6 and A-7 remain unverified).
- **Basis:** about 110 lines of JS and 130 test lines; getting the busy rule right without enumerating inputs (BR-12) is the design care. Range 2.25-3.75 h.
- **Split because:** safety logic against data loss (risk R-4), reviewed independently of the notice it drives.
- **Depends on:** T-036-15, T-036-16

### [x] T-036-18 — `app.js`: loop guard in `sessionStorage["console-reload"]` (1.5 h)
- [x] `autoReload()` reads recent automatic-reload timestamps from `sessionStorage["console-reload"]` (corrupt or missing reads as none), drops those older than 5 minutes, and when 3 remain does **not** reload: it sets the notice text to the paused wording (the notice and **Reload now** stay) and returns; the next heartbeat re-evaluates, so automatic reload re-arms by itself when the window slides past (D-14)
- [x] otherwise it appends `Date.now()`, writes the list back, then calls `window.location.reload()`; if `sessionStorage` is unavailable (throws) it does **not** reload automatically (fail safe: a guard that cannot count cannot bound a loop)
- [x] no comparison with a target version (`to`); a manual **Reload now** never reads or writes the guard and works while paused
- **Files may touch:** `console/static/app.js` (foreign hunks), `console/tests/test_reload_source.py`
- **Done-criteria:** PY `test_reload_source.py` grows by at least 4 tests, 0 failed: AC-19 (`sessionStorage` with the key `"console-reload"`, the constants 3 and 300000, pruning of old entries, the pause branch before `location.reload()`, no `.to` property or `to:` in the guard code, and the storage-failure branch does not reload); `reloadNow` does not reference the guard key; paused wording exists in the notice constants. Foreign hunks byte-identical to the snapshot. `node --check` where available. [BROWSER] AC-20 has its surface (and AC-21) and stays "not verified in a browser". `test_stylesheet.py`, `test_plugins.py` green.
- **Basis:** about 35 lines of JS and 60 test lines. Range 1-2 h.
- **Split because:** an independently reviewed safety net against reload loops (risk R-5); a defect here is a loop, so it gets its own review.
- **Depends on:** T-036-17

### [x] T-036-19 — SHOULD, droppable with 20: `workspace` on `/api/config`, 12 hex of the normalised real repo-root path (1 h)
- [x] re-Read `console/server/features/shell_feature.py`; add a helper `_workspace_id(repo_root)` = first 12 hex of sha256 of `os.path.normcase(os.path.realpath(repo_root))` (UTF-8), and `"workspace": _workspace_id(ctx.repo_root)` in the `config()` payload; the id is a hash, never the path (D-30)
- **Files may touch:** `console/server/features/shell_feature.py` (foreign hunk), `console/tests/test_config_payload.py`
- **Done-criteria:** PY `test_config_payload.py` grows by at least 3 tests, 0 failed: AC-57 (12 lowercase hex; constant for one root across calls; different for two scratch roots with distinct names; the serialised payload contains neither the root path nor its directory name); the static export manifest still has no `workspace` (BR-7). Existing payload tests still green. Foreign lines of `shell_feature.py` unchanged versus the snapshot.
- **Basis:** about 8 lines and 50 test lines. Range 0.75-1.5 h.
- **Split because:** separable by Q2: dropping it must not touch Phases 1-5 (the planner's drop right in FR-8).
- **Depends on:** T-036-06

### [x] T-036-20 — SHOULD, droppable with 19: `desktop/sidecar.py` `ensure()` refuses to attach to a different workspace (2 h)
- [x] a module-level `workspace_id(root)` that duplicates the three-line hash and normalisation of task 19 (`sidecar.py` must stay importable with no `console/` on the path, `sidecar.py:27-31`); no import from `console/`
- [x] in `ensure()`, where it would attach (`is_up(...)` true, `owned=false`): GET `/api/config` with `urllib.request`; when the JSON has a `workspace` string different from `workspace_id(root)` raise `SidecarError("port <port> is served by a different workspace; stop that server or change the port")`; an absent field, a non-JSON answer or any error attaches as today; `is_up` and `probe` stay pure liveness probes (BR-14)
- [x] no Rust change; nothing under `desktop/src-tauri/` is touched (AC-60)
- **Files may touch:** `desktop/sidecar.py`, `desktop/tests/test_sidecar.py`
- **Done-criteria:** PY `desktop/tests/test_sidecar.py` grows by at least 6 tests, 0 failed (record the file's total; existing live-spawn tests unchanged and green): with a fake `http.server` answering `/api/config` on a free loopback port, AC-58 (differing `workspace` makes `ensure()` raise `SidecarError`; equal or absent attaches with `owned` false; `is_up` and `probe` unchanged); AC-59 (`sidecar.workspace_id(root)` equals `shell_feature._workspace_id(root)` for the same root, and `sidecar.py` source has no `import server`/`from server`/`console` import). AC-60 DOC: the files changed by this task are `desktop/sidecar.py` and the test only; `git status --short desktop/src-tauri` shows nothing attributable to this ticket (T-031's edits there are excluded by the per-task changed-files lists in progress.md).
- **Basis:** about 35 production lines and 120 test lines; the fake server and the real `ensure()` wait loop are the care points. Range 1.5-2.75 h.
- **Split because:** a different component in a different repo area (`desktop/`), separable by Q2 from everything else.
- **Depends on:** T-036-19

### [x] T-036-21 — Release note with the first-deploy relaunch step, and the verification plan (1.5 h)
- [x] `T-036-release.md`: replace the kickoff placeholders honestly (status "draft, not shipped", the deployer finalises); **What shipped** one line per component group; **First deploy needs one manual relaunch** (NFR-11): the pages open today have no version check, so quit the desktop app from the tray and start it again (F5/Ctrl+R in the webview is unverified), hard-refresh browser tabs, and restart the console server so it serves `/api/prefs` and `ui_version`; **How to check**: `GET /api/config` shows `ui_version` and `prefs_rev`; Settings shows "Shared by the desktop app and every browser tab on this machine..." in server mode; editing any file in `console/static` then shows the notice within one heartbeat; **Behaviour on an un-restarted server** (local mode until restart, then one idle reload, AC-68); **Not covered**: HUD overlay (`hud.html`, `flash.html`) stays stale until its next relaunch, macOS/Linux webviews not verified; **Rollback**: `enabled = false` on the `prefs` row returns clients to local mode, deleting `console/.cache/prefs.json` resets everyone, the browser's local copy was deleted after import (Q4 default) so an old UI shows defaults while the data stays in `prefs.json`; `onboarding-wizard.js:4` status
- [x] `T-036-verification.md`: add a "Verification plan" section and the Acceptance Criteria table rows for the 31 [BROWSER] criteria, each `NOT VERIFIED (browser)` with its procedure, and the four [DOC] rows (AC-60, AC-63, AC-64, AC-65) with their procedure; PY rows are left for the verifier to fill from the pytest evidence; record A-6, A-7 and the keepalive 64 KiB budget as unverified assumptions; the AC-41 pass condition is the one in task 10 (first tab render themed; a pre-existing shell flash is recorded, not failed); procedures include the AC-20 test server (a throwaway script returning a new `ui_version` each call, never committed), AC-65 timing (mean of 200 `UiVersion.value()` calls against 0.144 ms), AC-63 (diff each shared file against `console/.cache/t036-prebuild/`)
- [x] both artifacts keep a `## Links` block that lists the new siblings
- **Files may touch:** `knowledge-center/artifacts/T-036/T-036-release.md`, `knowledge-center/artifacts/T-036/T-036-verification.md`, `T-036-progress.md` via `progress-tracker`
- **Done-criteria:** DOC AC-64: both files state the one-time relaunch or hard-refresh step and how to check it (quit from the tray, relaunch). The verification file lists every one of the 31 [BROWSER] ACs as "not verified in a browser" and no BROWSER row says passed: AC-10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 22, 23, 40, 41, 42, 43, 45, 50, 51, 52, 56, 68, 70, 71, 72, 73, 76, 77, 78, 79, 81 (31 ids; check the count). No `*.toml` is edited by hand.
- **Basis:** two documents, about 120 lines total, from facts already in the artifacts. Range 1-2 h.
- **Split because:** a different owner type (the deployer and verifier consume it) and a different artifact kind; it is the hand-off the BROWSER criteria rely on.
- **Depends on:** T-036-18, T-036-20 (or T-036-18 and T-036-13 if Q2 drops the sidecar)

### [x] T-036-22 — Verification gates: full pytest, CI-parity checks, snapshot diff, `ui_version` timing, hand-off list (2 h)
- [x] full `PYTHONUTF8=1 python -m pytest -o addopts="" -q`: record total, failed and names; every failure is classified pre-existing (in the task-00 list) or new (blocking, route to `fix`); also record the per-file counts of the nine test files this ticket added or extended, and whether `console/.cache/prefs.json` exists in the real checkout before and after the run (R-16: no test may create it; if the owner's own server wrote it earlier, say so and compare its hash instead)
- [x] CI-parity: scan every new or changed `.py` file for 3.12+ constructs (nested same-quote f-strings, `type X =`, `def f[T]`, `datetime.UTC`, `override`); run `py -3.11 -m pytest -o addopts="" <this ticket's test files> -q` if `py -3.11` exists, else write "Python 3.11 not run locally; CI matrix is the evidence" (NFR-2); AC-61, AC-62 (`test_stylesheet.py`, `test_plugins.py`), AC-66 named tests pass
- [x] AC-63: for each of `app.js`, `settings.js`, `index.html`, `styles.css`, `shell_feature.py`, `audit.py` run `git diff --no-index console/.cache/t036-prebuild/<name>.orig <file>` and `git diff -U0 -- <file>`; every foreign hunk recorded in `<name>.diff` must still be present, byte-identical; `index.html` must show no diff from this ticket; report any hunk that moved, and attribute it with the per-task `<name>.pre-<NN>` diffs recorded in progress.md (a foreign hunk its owner advanced since task 00 is reported as such, not as this ticket's defect); also confirm `audit.ACTIONS` still contains both `prefs.reset` and `prefs.import` (CR-32, in case task 04 was deferred); `node --check` on each changed JS file where `node` exists
- [x] AC-65: time `UiVersion.value()` over 200 calls on the shipped `console/static` and record the mean beside the 0.144 ms baseline; measured `/api/config` growth in bytes (NFR-4 ceilings reported, not asserted)
- [x] AC-60: list the ticket's changed files from the per-task progress entries and confirm none is under `desktop/src-tauri/`
- [x] hand off: write the 31 [BROWSER] criteria, A-6, A-7 and the keepalive budget as "not verified in a browser" in progress.md; suggest `validate-artifacts T-036 links`
- **Files may touch:** none in the product tree; `T-036-progress.md`, `T-036-verification.md` only
- **Done-criteria:** progress.md holds the full-suite line (`N passed, M failed`) with the failure classification, the per-file counts, the AC-63 result per file, the timing and size numbers, the AC-60 list and the "not verified in a browser" list; every number is copied from command output; the report states plainly that the 31 [BROWSER] criteria are not verified and that the gate is **not** a claim they pass.
- **Basis:** the full suite (about 4 min) plus six diffs, a timing snippet and a scan. Range 1.5-2.75 h.
- **Split because:** an independently reviewed gate (verify), run after everything else so it judges the final tree.
- **Depends on:** T-036-21

## Effort

Build effort only. QC and reserve live in [[T-036-effort-estimate]]; the 31 [BROWSER] checks are executed by a person after build (not a task here). Task-level PERT: expected 43.8 h, range 31.2-53.8 h, confidence Low (0 actuals); envelope Development 64.2 h [46.1, 77.6], reconciled in the estimate file.

| Task | Estimate | Basis |
|------|----------|-------|
| T-036-00 Step zero | 0.5 h | one 4-minute command plus six copies |
| T-036-01 `prefs_store` core | 3 h | about 170 prod lines, 220 test lines, threaded and boundary tests |
| T-036-02 import and reset | 2 h | about 90 prod, 130 test lines |
| T-036-03 plugin, routes, real-HTTP test | 3 h | about 110 prod, 200 test lines, first real-HTTP harness |
| T-036-04 audit actions | 1 h | one tuple edit, three tests, snapshot check |
| T-036-05 `ui_version.py` | 2 h | about 70 prod, 160 test lines |
| T-036-06 `/api/config` fields | 1.5 h | about 15 prod, 110 test lines |
| T-036-07 `C.prefs` read side | 3 h | about 130 JS lines replacing 15, 100 test lines |
| T-036-08 write-through and flush | 3 h | about 150 JS, 90 test lines |
| T-036-09 migration, reset, refresh | 3 h | about 140 JS, 80 test lines |
| T-036-10 boot and live pickup | 2 h | about 60 JS, 90 test lines, three foreign hunks |
| T-036-11 Settings panel | 2 h | about 70 JS replaced, 90 test lines |
| T-036-12 stale statements | 1.5 h | about 12 one-line edits, 50 test lines |
| T-036-13 docs and comments | 1 h | four text edits, 40 test lines |
| T-036-14 notice style | 0.5 h | about 12 CSS lines and a diff check |
| T-036-15 hold registry and registrants | 1.5 h | about 25 JS, 60 test lines |
| T-036-16 compare and notice | 3 h | about 90 JS, 110 test lines |
| T-036-17 idle, busy, scheduler | 3 h | about 110 JS, 130 test lines |
| T-036-18 loop guard | 1.5 h | about 35 JS, 60 test lines |
| T-036-19 `workspace` field (SHOULD) | 1 h | about 8 prod, 50 test lines |
| T-036-20 sidecar attach check (SHOULD) | 2 h | about 35 prod, 120 test lines |
| T-036-21 release note and verification plan | 1.5 h | two documents from existing facts |
| T-036-22 verification gates | 2 h | full suite, six diffs, timing, scan |
| **Total** | **44.5 h** | sum of the rows; equals [[T-036-task-breakdown]] and [[T-036-implementation-plan]]; 23 tasks; dropping 19-20 (Q2) leaves 41.5 h |

By layer: service 15.5 h · UI 24.0 h · docs 3.0 h · test/verification 2.0 h.

### Acceptance criterion coverage

All 81 acceptance criteria of [[T-036-requirements]] map to at least one task: **81/81** (PY 46, BROWSER 31, DOC 4). **[PY]**: proven by a named test in the task(s) listed. **[BROWSER]**: the listed builder task creates the testable surface; the check itself is a person's, its procedure is written by task 21 and it stays "not verified in a browser" until run. **[DOC]**: read by the verifier from the artifact or the plan.

| AC | Tag | Built / proven by | Check owner |
|----|-----|-------------------|-------------|
| AC-1 | PY | 05, 06 | test |
| AC-2 | PY | 05 | test |
| AC-3 | PY | 05 | test |
| AC-4 | PY | 05 | test |
| AC-5 | PY | 05 | test |
| AC-6 | PY | 05 | test |
| AC-7 | PY | 05 | test |
| AC-8 | PY | 16 | test |
| AC-9 | PY | 16 | test |
| AC-10 | BROWSER | 14, 16 | person (21) |
| AC-11 | BROWSER | 16 | person (21) |
| AC-12 | BROWSER | 16 | person (21) |
| AC-13 | BROWSER | 16 | person (21) |
| AC-14 | BROWSER | 17 | person (21) |
| AC-15 | BROWSER | 17 | person (21) |
| AC-16 | BROWSER | 15, 17 | person (21) |
| AC-17 | PY | 15 | test |
| AC-18 | BROWSER | 17 | person (21); "A-6 false" is a valid outcome |
| AC-19 | PY | 18 | test |
| AC-20 | BROWSER | 18 | person (21) |
| AC-21 | BROWSER | 16 | person (21) |
| AC-22 | BROWSER | 17 | person in the Tauri webview (21); A-7 unverified |
| AC-23 | BROWSER | 16 | person (21) |
| AC-24 | PY | 01, 03 | test |
| AC-25 | PY | 01, 03 | test |
| AC-26 | PY | 01 | test |
| AC-27 | PY | 01 | test |
| AC-28 | PY | 01 | test |
| AC-29 | PY | 01 | test |
| AC-30 | PY | 01 | test |
| AC-31 | PY | 01 | test |
| AC-32 | PY | 03, 04 | test |
| AC-33 | PY | 03 | test |
| AC-34 | PY | 03 | test (real in-process HTTP) |
| AC-35 | PY | 06 | test |
| AC-36 | PY | 03 | test (source scan) |
| AC-37 | PY | 07, 09 | test |
| AC-38 | PY | 10 | test |
| AC-39 | PY | 08 | test |
| AC-40 | BROWSER | 07 | person (21) |
| AC-41 | BROWSER | 07, 10 | person (21) |
| AC-42 | BROWSER | 08 | person (21) |
| AC-43 | BROWSER | 07 | person (21) |
| AC-44 | PY | 01, 07 | test |
| AC-45 | BROWSER | 07, 08, 09 | person (21) |
| AC-46 | PY | 02 | test |
| AC-47 | PY | 02 | test |
| AC-48 | PY | 02 | test |
| AC-49 | PY | 02, 03 | test |
| AC-50 | BROWSER | 09 | person (21) |
| AC-51 | BROWSER | 09 | person (21) |
| AC-52 | BROWSER | 10 | person (21) |
| AC-53 | PY | 09, 10 | test |
| AC-54 | PY | 11, 12, 13 | test |
| AC-55 | PY | 11, 12 | test |
| AC-56 | BROWSER | 11 | person (21) |
| AC-57 | PY | 19 (SHOULD) | test |
| AC-58 | PY | 20 (SHOULD) | test |
| AC-59 | PY | 20 (SHOULD) | test |
| AC-60 | DOC | plan rule; 20, 21, 22 | verifier (changed-files list) |
| AC-61 | PY | 07, 22 | test |
| AC-62 | PY | 03, 06, 07-18 (each runs both files), 22 | test |
| AC-63 | DOC | 00 (snapshots), 22 | verifier (manual, not CI) |
| AC-64 | DOC | 21 | verifier |
| AC-65 | DOC | 21 (procedure), 22 (measurement) | verifier |
| AC-66 | PY | 10, 16, 17 | test |
| AC-67 | PY | 05, 06 | test |
| AC-68 | BROWSER | 16 | person (21) |
| AC-69 | PY | 14, 16 | test |
| AC-70 | BROWSER | 17 | person (21) |
| AC-71 | BROWSER | 08 | person (21) |
| AC-72 | BROWSER | 08 | person (21) |
| AC-73 | BROWSER | 07, 10 | person (21) |
| AC-74 | PY | 07, 08 | test |
| AC-75 | PY | 02 | test |
| AC-76 | BROWSER | 09 | person (21) |
| AC-77 | BROWSER | 10 | person (21) |
| AC-78 | BROWSER | 17 | person (21) |
| AC-79 | BROWSER | 09, 10 | person (21) |
| AC-80 | PY | 02 | test |
| AC-81 | BROWSER | 09 | person (21) |

NFR traceability: NFR-1 AC-61 (07, 22) · NFR-2 CI matrix (22 scan, `py -3.11` if present) · NFR-3 AC-62 (14 and every JS task) · NFR-4 AC-6, AC-65 (05, 06, 22) · NFR-5 AC-42, AC-66 (08, 10, 16, 17) · NFR-6 AC-73 (07, 10) · NFR-7 AC-26, 34, 36 (01, 03) · NFR-8 AC-29, 30, 72 (01, 08) · NFR-9 AC-63 (00, each shared-file task, 22) · NFR-10 AC-10, 69, 76 (14, 16, 09) · NFR-11 AC-64 (21) · NFR-12 AC-22 (17; macOS and Linux "not verified" in 21).

## Risks

Scored low / med / high per axis, each tied to the artifact line that surfaced it. Rows whose likelihood and impact are high-high or high-med/med-high carry an explicit mitigation. `challenge-plan` found structural plan issues separately ([[T-036-critique-report]] § Plan critique); its critical-path and rollback findings are pulled forward below by CR id.

| ID | Risk | Likelihood | Impact | Mitigation | Owner | Source |
|----|------|-----------|--------|------------|-------|--------|
| R-1 | Concurrent-edit collision on shared files: `app.js`, `settings.js`, `shell_feature.py`, `audit.py`, `styles.css` carry other tickets' uncommitted hunks; `core.js`, `agents.js`, `todos.js` are contended (T-031, T-037) | High | High | task 00 snapshots (`.orig` + `.diff`); re-Read before every Edit; small local hunks; retry on conflict; never revert, stash, checkout, `git add`, commit; CSS mid-file only; `audit.ACTIONS` edited only when its hunk matches the snapshot (movable); a `git diff -U0` check against the snapshot in every affected task and in 22 (AC-63) | Builder, Verifier | NFR-9; [[T-036-analysis]] §8 |
| R-2 | Hydration-before-render regression: waiting on `hydrate()` blanks or delays first paint, or breaks the static export | Med | High | `hydrate()` never rejects; 3 s bound then local mode (D-17); static short-circuits to the old `localStorage` path kept verbatim; exact boot string pinned (AC-38); [BROWSER] AC-41, 43, 73 handed off | Builder | D-17; CR-8; NFR-6 |
| R-3 | Write-through flood: `onboardingDraft` writes per keystroke, `layout` per drag | Med | Med | 250 ms trailing debounce, coalesced deltas, skip-equal; `FLUSH_MS` pinned by test; AC-42 [BROWSER] | Builder | [[T-036-analysis]] §3; decision `prefs-client-contract` |
| R-4 | Reload data loss: typed text, dictated text, open dialogs or off-DOM drafts lost to an automatic reload | Med | High | generic dirty-field rule (textarea non-blank, typed `WeakSet`, focused field) plus `Console.holdReload` for `st.drafts` and `st.newText`; drawer, wizard, palette, voice busy; hidden shortcut never bypasses busy; manual reload is consent (BR-15); source tests pin every busy source; [BROWSER] AC-14..16, 70, 78 stay unverified and are handed off | Builder, Verifier | CR-1, CR-3, CR-19; BR-6 |
| R-5 | Reload loop: an unstable stamp or a flapping server | Low | High | stamp is stat-only and deterministic (restart with unchanged files gives the same value, AC-21); guard pauses at 3 automatic reloads in a rolling 5 minutes and fails safe when `sessionStorage` is unusable; manual reload never counts | Builder | CR-4; D-14 |
| R-6 | Voice and layout sharing side effects: tray mute also mutes browser read-aloud; pixel `layout` shared across window sizes and devices; a write made while the server is down is lost on reload | High | Med | accepted by the owner (A-5, Q5 default "no key per-device"); stated in the release note; a per-key local override is cheap to add later and is not planned here | Owner | decision `scope-boundaries`; A-5 |
| R-7 | Store format: TOML versus JSON | Low | Med | JSON decided (`tomlio.py:232-271` cannot hold nested values or `null`); atomic write through `tomlio._replace`; AC-29 and AC-30 | Builder | [[T-036-analysis]] §4 |
| R-8 | Python 3.11 compatibility: local interpreter is 3.14, CI runs 3.11 and 3.13 | Med | Med | stdlib only; task 22 scans for 3.12+ constructs and runs `py -3.11` if present, else says "3.11 not run locally"; CI matrix is the evidence | Builder, Verifier | NFR-2 |
| R-9 | 31 [BROWSER] criteria cannot be run by the pipeline | High | Med | surface built by tasks 07-18; procedures written by task 21; reported "not verified in a browser"; never claimed passing; owner or verifier runs them | Verifier, Owner | requirements verification tags |
| R-10 | `C.post` throws an `Error` with no HTTP status, so a 400 cannot be told from a network failure | Med | Med | additive `err.status` line in `core.js` `post` (D-29); source test | Builder | `core.js:142-158`; plan-time finding |
| R-11 | The real-HTTP test is the repo's first to instantiate `httpd.Handler`; class attributes could leak between tests | Med | Low | subclass `H(Handler)` with its own `repo_root` and `router`, port 0, `shutdown()` and `server_close()` in `finally` | Builder | [[T-036-analysis]] §8 |
| R-12 | T-037 consumes `layout` and rewrites the drawer into a dock, which the busy check reads | Med | Med | `layout` contract pinned by AC-44; busy check reads the DOM `.drawer` (D-24) so this ticket never edits the drawer IIFE; hand-off note: T-037 must keep `.drawer` or update `isBusy` | Builder, T-037 owner | decision `t037-layout-contract` |
| R-13 | The keepalive 64 KiB body budget is recalled, not verified | Low | Med | 60,000-byte guard, per-key split, single oversize value without `keepalive`; [BROWSER] AC-71 | Verifier | D-15; CR-5 |
| R-14 | A-6 (WebView2 reports hidden for a Tauri-hidden window) and A-7 (reload re-runs the Rust init script) are unverified | Med | Med | AC-18 accepts "A-6 false" as a recorded outcome; AC-22 says a missing `in-shell` after reload is a defect to fix page-side before ship; both listed in the hand-off | Verifier | A-6, A-7; CR-12, CR-13 |
| R-15 | A delegated builder's status line mis-reports | Med | Med | verify from the tree, `git status` and the `pytest -o addopts=""` count before marking `[x]` | Harness, Verifier | memory `subagent-status-not-evidence` |
| R-16 | Tests write the real checkout's `console/.cache/prefs.json` (`test_plugins.py` runs against the real root) | Med | Med | every new test uses the `repo` fixture's scratch workspace; task 22 checks the real file is absent or unchanged after the full suite | Builder | `test_plugins.py:27-41` |
| R-17 | `console/kanban.py` crashes on cp1252 stdout without `PYTHONUTF8=1` | Med | Low | every call sets the variable; the crash is **not** fixed here (a separate session owns it) | Builder | build protocol |
| R-18 | Windows `os.replace` raises `PermissionError` on a briefly open target | Low | Med | `tomlio._replace` retries 10 times at 20 ms; AC-30 asserts it is the write path | Builder | `tomlio.py:307-322` |
| R-19 | A server not yet restarted serves new JS without `/api/prefs` or `ui_version` | Med | Low | page runs in local mode (AC-43); absent-then-present counts as changed so one idle reload moves it to server mode (D-13, AC-68); the release note says to restart the server | Builder | D-13 |
| R-20 | Sidecar check is outside the summary's three scope items (scope creep, CR-11 accepted) | Low | Low | SHOULD, Python only, tasks 19-20 droppable together without touching Phases 1-5 | Owner | CR-11; Q2 |
| R-21 | The mid-build tree is live: static files are served per request (`httpd.py:94-115`), so a server restart between tasks exposes a half-built client (server mode with no write-through) | Med | Med | `SERVER_PREFS = false` until the last step of task 09 (CR-27); the new route exists from task 03 but a page ignores it until then; the user's own open app showing the new notice while the builder edits files is the feature working, not a defect | Builder | CR-27 |
| R-22 | A foreign owner advances a shared file while this ticket builds, so an end-of-ticket snapshot diff misattributes hunks | High | Med | per-task `<name>.pre-<NN>` copies and `git diff --no-index` with changed ranges in progress.md; task 22 attributes any moved foreign hunk before reporting (CR-28) | Builder, Verifier | CR-28; AC-63 |
| R-23 | Busy detection reads class names owned by other files (`.ob-scrim`, `.cp-scrim.on`, `.drawer`); a rename silently disables a guard | Low | Med | source tests check each selector against its owner file (CR-37); wizard draft is also persisted through `C.prefs`, so an un-detected wizard reload resumes rather than loses | Builder | CR-37 |

**Totals: 23 risks, 23 mitigated, 1 high×high (R-1, mitigated), 0 without mitigation.** High×med rows (R-6, R-9, R-22) each carry an explicit mitigation or an explicit owner acceptance.

## Dependencies
- Blocks: [[T-037-summary]] storing `layout` through `C.prefs` is safe after task 10 (the prefs half); until then it runs against the unchanged local `C.prefs` and its values are picked up by the migration unchanged (decision `t037-layout-contract`).
- Blocked by: nothing. **Concurrent, not blocking:** [[T-031-summary]] and the onboarding pipeline edit `settings.js`, `app.js`, `index.html`, `shell_feature.py`, `audit.py`, `styles.css` in the same tree; T-037 edits `agents.js`, `styles.css`, `index.html`. The shared-file rules above are how this plan lives with that.

## Links
- [[T-036-summary]] · [[T-036-analysis]] · [[T-036-context-snapshot]] · [[T-036-requirements-draft]] · [[T-036-requirements]] · [[T-036-user-stories]] · [[T-036-decision-log]] · [[T-036-plan]] · [[T-036-components]] · [[T-036-effort-estimate]] · [[T-036-task-breakdown]] · [[T-036-implementation-plan]] · [[T-036-critique-report]] · [[T-036-plan-iteration-log]] · [[T-036-progress]] · [[T-036-verification]] · [[T-036-release]]
- Related: [[T-037-summary]] · [[T-031-summary]] · [[T-031-plan]] (format precedent)
- [[T-036-gap-analysis]] · [[T-036-iteration-log]]
