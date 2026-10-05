---
ticket: "T-024"
artifact: plan
---

# Plan: T-024

Structure: **single-layer / flat** (one component, the console server; 6 tasks; no cross-ticket dependency chain). Stories: [[T-024-user-stories]].

## Approach

Test-first, smallest change set that anchors console-managed state to the main repo while file edits stay in the worktree. A `CONSOLE_REPO_ROOT` locator is set at the one env seam both session types share (`procs.clean_env`, [[T-024-decision-log]] D2) and honoured by `paths.find_repo_root` only when valid (D4), then handed to the Claude MCP server through `.mcp.json` + `setup_editor` (D3). Telemetry/notify use `self.repo_root or self.cwd`. API sessions split the two roots with `dispatch(..., workspace_root=None)` and `REGISTRY.request(..., preview_root=None)` instead of a plain `cwd -> repo_root` swap that would let API agents edit the main tree (D1). Prompt/skill resolution stays on the worktree, docstring-only fix (D5). Markdown artifacts stay out of scope (D6, Q1). Every new parameter defaults to today's behaviour (BR-5).

## Slices

### Slice 1 — Anchor console state to main (single slice, tasks 01-06 in order)
Red tests (01) -> locator (02) -> MCP wiring (03) -> telemetry/notify (04) -> API split roots (05) -> regression pins, full suite, smoke, handoff (06). Tasks 02, 04 and 05 are independent of each other once 01 is done; they are listed in the order that turns tests green fastest (04 is a 2-line fix that flips AC-4a/4c).

## Lane mapping (`console` skill, "Stage -> lane sync")

The builder moves the board lane with the CLI, never by hand-editing TOML:
- Start of task 01 (first build task): `python console/kanban.py ticket move T-024 in-progress`
- A blocker is logged: `python console/kanban.py ticket move T-024 blocked`
- Task 06 done, verification starting: `python console/kanban.py ticket move T-024 verify`
- `close-work` (harness) moves to `done`; the builder does not.

## Tasks

Run from the workspace root. Test command: `python -m pytest -o addopts="" console` (root `pytest.ini` has `testpaths = console/tests desktop/tests`, `addopts = -q --strict-markers`; `console/tests/conftest.py` puts `console/` on `sys.path`). New tests go in **new** files so `test_paths.py`, `test_setup_editor.py`, `test_codex.py`, `test_telemetry.py` and the existing `test_api_session.py`/`test_agent_tools.py` tests stay unmodified (AC-2b, 3c, 4d, 5g, 6c), except the single fake at `test_api_session.py:608`.

### [x] T-024-01 — Reproduce first: failing tests + measured baseline (2 h)
- [x] BEFORE any edit: `git status --short` and `git diff --stat` into progress (tree is dirty with other tickets' work: `console/kanban.py`, `server/verb_handlers.py`, `tests/test_ui_endpoints.py`, ...). Do not touch or revert those.
- [x] Measure baseline: `python -m pytest -o addopts="" console` from the workspace root; record the exact passed/failed/skipped count as the **before** number (plan's ~1867 is unverified). If anything already fails, record names; they are not T-024's to fix.
- [x] `python console/kanban.py ticket move T-024 in-progress`
- [x] **AC-4a** (new file `console/tests/test_worktree_anchor.py`): reuse the `gitrepo` fixture from `test_agent_manager_worktree.py` (import or copy its 12 lines), `agent_manager._resolve_worktree(gitrepo, "T-024")` for a real worktree, `agent_backends.get(gitrepo, "alpha")` fake backend as in `test_telemetry.py:204-207`, `agent_session.build("sid", backend, wt, ticket="T-024", repo_root=gitrepo, model=...)`, one `sess._observe({"type": "turn.end", ...})`. Assert the record is in `telemetry.read_records(gitrepo)` and that `<wt>/knowledge-center/telemetry` does not exist (compare paths with `os.path.normcase(os.path.realpath(...))`).
- [x] **AC-4c**: same setup, `verb_handlers._telemetry_by_session(gitrepo)` contains the session with tokens/cost > 0.
- [x] **AC-5a / AC-5b**-style API tests (new class in new file `console/tests/test_api_session_roots.py`, reusing the `api`/`Provider`/`call_tool`/`run` helpers from `test_api_session.py`): a session with `cwd=<worktree-shaped dir>`, `repo_root=main`; `comment` verb mutates main's tracker, not the worktree copy (5a, expected red); `write_file("x.txt", ...)` lands in the worktree, not main (5b, expected green today: it is the guard against a naive swap).
- [x] Run only those tests; paste the failing output into progress via `progress-tracker` as evidence. Expected red: AC-4a, AC-4c, AC-5a. Expected green: AC-5b. State any deviation honestly.
- **Done-criteria:** failing pytest output captured for AC-4a, AC-4c, AC-5a (and AC-5b green) in `T-024-progress.md`; baseline count recorded with the exact command and `git status` snapshot; lane = in-progress.
- **Basis:** 3 new tests + fixture reuse, ~0.5 h each, 0.5 h for the baseline run and notes.
- **Split because:** hard dependency and gate; nothing else may start before the bug is reproduced and the baseline is fixed.
- **Depends on:** —

### [x] T-024-02 — FR-1 + FR-2: env seam and root locator (2.5 h)
- [x] `console/server/procs.py:58-64` `clean_env(repo_root)`: when `repo_root` is truthy set `env["CONSOLE_REPO_ROOT"] = os.path.abspath(repo_root)` after the strip (not strippable, AC-1d); `clean_env(None)` unchanged (AC-1b); overwrite a stale inherited value (AC-1c).
- [x] `console/server/paths.py:70-108` `find_repo_root`: candidate order explicit `start` > valid `CONSOLE_REPO_ROOT` > cwd > package dir. Valid = `os.path.isabs`, `os.path.isdir`, and `_is_repo_root(v)` or `workspace_config.resolve(v) is not None`. Invalid (empty, literal `${CONSOLE_REPO_ROOT:-}`, relative, nonexistent, non-root dir) silently ignored, no upward walk from it, never raises. One `isdir` + one `resolve` at most, only when set.
- [x] `console/tests/conftest.py`: add an autouse fixture that `monkeypatch.delenv("CONSOLE_REPO_ROOT", raising=False)`, so a run inside a console agent session (whose env now carries the variable) cannot change `find_repo_root()` results in unrelated tests. Tests that need the variable set it themselves.
- [x] New tests in new files: `test_procs_anchor.py` or a new class appended to a new file (AC-1a..1d); AC-1e with `subprocess.Popen` monkeypatched for `LiveSession.start` and `TurnSession._deliver` on a ticketed worktree chat; `test_repo_root_anchor.py` for AC-2a..2e (2e uses a `workspace.toml`-renamed layout).
- **Done-criteria:** AC-1a..1e and AC-2a..2e pass; `tests/test_paths.py` and `tests/test_procs.py` pass unmodified (AC-2b); no exception for any AC-2c input.
- **Basis:** 10 ACs, ~0.2 h each = 2 h, + 0.5 h conftest guard and a `workspace.toml` fixture.
- **Split because:** hard dependency; task 03 (and AC-3e) needs the locator, and this is the only task that changes shared helpers every other caller uses.
- **Depends on:** T-024-01

### [x] T-024-03 — FR-3: `.mcp.json` env block + `setup_editor('claude')` (1.5 h)
- [x] `.mcp.json` console entry becomes `{command: python, args: [console/mcp_server.py], env: {CONSOLE_REPO_ROOT: "${CONSOLE_REPO_ROOT:-}"}}` (AC-3a). Plain JSON edit; tracked file.
- [x] `console/server/setup_editor.py:103-113` (`entry_stdio`; Claude path only, `setup_editor.py:47-70` rewrite): write the same entry for `claude`; cursor/vscode entries unchanged (AC-3c); other servers preserved; second run reports `mcp_changed is False` (AC-3b).
- [x] New test file `console/tests/test_mcp_anchor.py`: AC-3a reads the committed `.mcp.json`; AC-3b runs `setup_editor('claude')` on a tmp repo and compares with it; AC-3e starts the MCP server as a subprocess (harness pattern at `tests/test_mcp.py:5`) with cwd = a worktree-shaped dir and `CONSOLE_REPO_ROOT` = main, and checks it serves main's tickets.
- **Done-criteria:** AC-3a, 3b, 3c, 3e pass; `tests/test_setup_editor.py` and `tests/test_mcp.py` pass unmodified. AC-3d is handled in task 06.
- **Basis:** 2 small edits + 3 tests, 0.5 h each.
- **Split because:** independently reviewed piece with an external uncertainty (Claude's env handling, R1); keeps the tracked-file edit separately reviewable and revertable.
- **Depends on:** T-024-02

### [x] T-024-04 — FR-4: telemetry and notify use the main root (1 h)
- [x] `console/server/agent_session.py:451` (`notify.send`) and `:473` (`telemetry.record_turn`): `self.repo_root or self.cwd`.
- [x] Fix the stale docstrings at `agent_session.py:463` (says `self.cwd` is the repo root) and `console/server/agent_manager.py:391` (calls `sess.cwd` "the workspace root"; docstring only, D5).
- [x] New tests: AC-4b (`notify.send` monkeypatched receives main root); AC-4d (`repo_root=""` falls back to `cwd`).
- **Done-criteria:** AC-4a and AC-4c (red in 01) now green; AC-4b, AC-4d pass; `tests/test_telemetry.py` unmodified and green.
- **Basis:** 2 one-line changes + 2 docstrings + 2 tests.
- **Split because:** self-contained deliverable that flips the first failing test; reviewable in isolation from the larger FR-5 change.
- **Depends on:** T-024-01

### [x] T-024-05 — FR-5: API session split roots (3 h)
- [x] `console/server/agent_tools.py:363` `dispatch(repo_root, name, arguments, workspace_root=None)`; `None` means `repo_root`. Console verbs and `tool_definitions` use `repo_root`; `_resolve(...)` file tools and `run_command` use `workspace_root` (`agent_tools.py:73-87,237-258`).
- [x] `console/server/agent_api_session.py`: `tool_definitions` (L178), `assistant_config.settings` (L366), `multimodal.after_capture` (L272), `REGISTRY.request` repo_root (L351) use `self.repo_root or self.cwd`; `dispatch(self.repo_root or self.cwd, name, args, workspace_root=self.cwd)` (L355); `prompt_build.build(self.cwd)` (L108) unchanged; `REGISTRY.request(..., preview_root=self.cwd)`.
- [x] `console/server/agent_approvals.py:87-145`: `request(..., preview_root=None)`; `tool_preview.build(preview_root or repo_root, ...)`; `notify` keeps `repo_root`. `features/agents_feature.py:278` (the Claude hook caller) and `tests/test_desktop_verbs.py:175,229` are unchanged by default (see CR-3).
- [x] `console/tests/test_api_session.py:608`: change the fake to `def fake(repo_root, name, arguments, workspace_root=None)` and forward to `real(repo_root, name, arguments, workspace_root)` (AC-5g; the only edit to that file).
- [x] Tests in `test_api_session_roots.py`: AC-5a flips green; AC-5b stays green; AC-5c (`../x` and an absolute outside path still error "outside the workspace"); AC-5d (`run_command` without `cwd` runs in the worktree); AC-5e (notify gets main root, diff preview reads the worktree file); AC-5f (`after_capture` finds a capture written under main).
- **Done-criteria:** AC-5a..5g pass; all other `test_api_session.py` and all `test_agent_tools.py` tests pass unmodified.
- **Basis:** 3 files of production code, 7 ACs, the one fake; the largest task (about 0.4 h per AC incl. a 0.2 h approvals read).
- **Split because:** different surface (API transport, approvals) and the only signature change; an independently reviewed piece with the highest regression risk (R4, R9).
- **Depends on:** T-024-01

### [x] T-024-06 — FR-6 regression pins, full suite, live smoke, handoff (2.5 h)
- [x] Pin tests (new file `console/tests/test_anchor_regressions.py`): AC-6a ticketless chat has env var == cwd == `repo_root` and telemetry in the same place as before; AC-6b non-git / `WorktreeError` fallback leaves all three roots equal; AC-6d `agent_manager.send` -> `compose_prompt(repo_root=sess.cwd)` and `prompt_build.build(self.cwd)` still resolve against `cwd`.
- [x] AC-6c: run `tests/test_codex.py` untouched.
- [x] Full suite: `python -m pytest -o addopts="" console`; passed count >= the task-01 baseline plus the new tests; compare names, not only totals; no previously passing test missing.
- [x] AC-3d manual smoke (passed 2026-10-05 on the second attempt, after T-025 D-1; see [[T-024-verification]]), after `.mcp.json` is committed by the owner (commit is an ASK-gate, not the builder's call): create a **fresh** worktree (`.mcp.json` only reaches worktrees made after the commit), start a Claude chat for a ticket, have it call a `console_*` write verb, confirm it lands in main's TOML; record in [[T-024-verification]]. Failure -> `evolve` (D3 fallback), not a silent change.
- [x] `progress-tracker` entry per task; `python console/kanban.py ticket move T-024 verify`; hand off to `@verifier`.
- **Done-criteria:** AC-6a..6d pass; full-suite count >= baseline (numbers cited); AC-3d recorded pass/fail in verification; lane = verify.
- **Basis:** 3 pin tests (1 h), full suite + count comparison (0.5 h), live smoke + notes (0.5 h), lane/progress (0.5 h).
- **Split because:** independently reviewed piece (verify gate) plus a manual step by a human-approved commit; last in order by hard dependency on 02-05.
- **Depends on:** T-024-02, T-024-03, T-024-04, T-024-05

## Effort

| Task | Estimate | Basis |
|------|----------|-------|
| T-024-01 — Reproduce first, baseline | 2 h | 3 new tests ~0.5 h each + 0.5 h baseline run/notes |
| T-024-02 — FR-1 + FR-2 env seam and locator | 2.5 h | 10 ACs ~0.2 h each + 0.5 h conftest guard / workspace fixture |
| T-024-03 — FR-3 `.mcp.json` + setup_editor | 1.5 h | 2 small edits + 3 tests ~0.5 h each |
| T-024-04 — FR-4 telemetry/notify | 1 h | 2 one-line changes, 2 docstrings, 2 tests |
| T-024-05 — FR-5 API split roots | 3 h | 3 production files, 7 ACs, one fake |
| T-024-06 — FR-6 pins, suite, smoke, handoff | 2.5 h | 3 pin tests, full-suite comparison, smoke, lane move |
| **Total** | **12.5 h** | sum; about 1.5 days; no `estimate(upfront)` envelope exists or was requested, so none to reconcile |

### Acceptance criterion coverage

30 ACs, all mapped. "red" = failing test written in 01; "green" = turned green by the named task.

| Acceptance Criterion | Covered by |
|----------------------|-----------|
| AC-1a, 1b, 1c, 1d | T-024-02 |
| AC-1e | T-024-02 |
| AC-2a, 2b, 2c, 2d, 2e | T-024-02 |
| AC-3a, 3b, 3c | T-024-03 |
| AC-3d (manual smoke) | T-024-06 |
| AC-3e | T-024-03 |
| AC-4a | T-024-01 (red), T-024-04 (green) |
| AC-4b, 4d | T-024-04 |
| AC-4c | T-024-01 (red), T-024-04 (green) |
| AC-5a | T-024-01 (red), T-024-05 (green) |
| AC-5b | T-024-01 (guard, green today), T-024-05 (stays green) |
| AC-5c, 5d, 5e, 5f, 5g | T-024-05 |
| AC-6a, 6b, 6d | T-024-06 |
| AC-6c | T-024-06 (and unmodified `test_codex.py` throughout) |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner | Source |
|------|-----------|--------|------------|-------|--------|
| R1 Claude CLI may not expand `${CONSOLE_REPO_ROOT:-}` or pass the parent env to the MCP server; not testable in the suite | Med | Med | Literal/empty value is ignored by FR-2, so failure degrades to today's behaviour; `clean_env` also puts the var in the parent env (inheritance route); AC-3d live smoke decides; failure -> `evolve` | Builder / owner | [[T-024-decision-log]] D3; [[T-024-analysis]] Key Findings |
| R2 `.mcp.json` is tracked: only worktrees created after it is committed get the env block | Med | Low | Inherited-env route covers older worktrees; smoke uses a fresh worktree; commit is an owner ASK-gate | Owner | [[T-024-analysis]] Key Findings |
| R3 `setup_editor('claude')` rewrites the entry and would erase an `.mcp.json`-only change | Med | Med | Task 03 changes both; AC-3b asserts equality with the committed entry and an idempotent re-run | Builder | [[T-024-analysis]] Key Findings |
| R4 The `test_api_session.py:608` fake rejects the new `workspace_root` argument | High | Low | Fixed in task 05 (AC-5g); `dispatch` is always called with the keyword; no other existing test edited | Builder | [[T-024-decision-log]] D1 |
| R5 Windows path comparison (case, `realpath`, 8.3/junction) makes locator or test asserts flaky | Med | Med | Implementation uses `abspath`; every test comparison uses `normcase(realpath(...))`; NFR Compatibility | Builder | [[T-024-requirements]] NFR |
| R6 A builder/tester run inside a console agent session inherits `CONSOLE_REPO_ROOT` and silently re-points `find_repo_root()` in unrelated tests | Med | High | Autouse `delenv` in `console/tests/conftest.py` (task 02); tests that need it set it explicitly | Builder | CR-1 |
| R7 Baseline taken on a dirty tree with other tickets' edits drifts before it is compared | Med | Med | Task 01 records `git status`/`git diff --stat` and the exact count before any edit; task 06 compares test names, not only totals | Builder | CR-2 |
| R8 API split-root change lets an API agent edit/run in the main tree | Low | High | AC-5b/5c/5d guard tests written in task 01/05 before the change; `workspace_root` default keeps all other callers | Builder | [[T-024-analysis]] Key Findings |
| R9 Agent-written markdown stays in the worktree while TOML now goes to main (split state) | Med | Low | Accepted; out of scope (D6, Q1 open, non-blocking); note in verification | Owner | [[T-024-decision-log]] D6 |
| R10 Second `REGISTRY.request` caller (`agents_feature.py:278`) previews the main file for a worktree Claude chat | Med | Low | Defaults leave it unchanged (BR-5); decision requested on CR-3 | Owner | CR-3 |

Mitigated: 10/10 (R9 accepted with rationale). High x high: 0.

## Dependencies
- Blocks: [[T-025-summary]], [[T-026-summary]] (later phases of [[T-023-summary]]; Q1 should be decided before them).
- Blocked by: — (requirements frozen 2026-10-04).

## Links
- [[T-024-summary]] · [[T-024-analysis]] · [[T-024-requirements]] · [[T-024-user-stories]] · [[T-024-decision-log]] · [[T-024-plan]] · [[T-024-progress]] · [[T-024-verification]] · [[T-024-critique-report]] · [[T-024-plan-iteration-log]]
