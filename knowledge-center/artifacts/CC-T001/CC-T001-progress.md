---
ticket: "CC-T001"
artifact: progress
---

# Progress: CC-T001

## Status Summary
Stage: TEMPLATE — building Phase 0 tasks in plan order.

## Dated Log

### 2026-08-29

**CC-T001-01 — config defects — done (1.5 h actual vs 1 h est).**

- D1 `.claude/settings.json` rewritten: `permissions.ask` gates on `git push`,
  `git push --force`, `git commit`, `git reset --hard`, `gh pr create`, `gh pr merge`,
  `WebFetch`, `WebSearch`; `permissions.deny` on `.env`, `*.key`, `credentials.json`.
  The five non-schema keys removed. Verified: file parses, keys are `['permissions','hooks']`.
- D1 partial — **blocked**: moving `defaultMode: acceptEdits` and the sibling-repo
  `additionalDirectories` into `.claude/settings.local.json` was denied by the permission
  classifier (it is a permissions file). Left for the user to apply by hand.
- D2 `knowledge-center/investigations/` created.
- D3 **scope grew, for a real reason.** The `[agents.backends]` block in `console.toml` was
  not dead config — `server/agents.py` (the `kanban agents *` CLI path) was reading it, while
  the Agents tab read `agents.toml`. Two registries for one concept; deleting the block made
  `agents backends` return `{}`. Fixed properly instead of reverting: `agents.py` now sources
  `agent_backends.registry()`, uses `Backend.compose_prompt()`/`turn_argv()`, and inherits the
  Windows `.CMD` path resolution the legacy path lacked. Added `oneshot_args` to the claude
  row (it had only `session_args`, so one-shot launch had no argv at all).
  Evidence: `kanban agents backends` lists both rows with `installed: true, launchable: true`;
  unknown-backend error names the configured set.
- `.gitignore`: `.claude/settings.local.json` was **not** ignored — personal settings were
  committable. Added, with `.claude/logs/`, `knowledge-center/agent-runs/`, pytest caches.
- README structure comment corrected (it described settings.json as an agents/skills roster).

**CC-T001-02 — console unit tests — done (2 h actual vs 3 h est).**

- `console/tests/` with a `repo` fixture building a throwaway workspace root under
  `tmp_path`; config-loader caches cleared per test. 5 files, 104 cases at this point:
  `tomlio` (round-trip, escaping, comma-in-array regression, concurrent-writer safety),
  `tickets` (id pattern, duplicate refusal, lane validation, patch atomicity),
  `trackers` (id formats, status filters, the three blocker rules),
  `boards` (lane flags, enabled-vs-present), `agent_backends` (argv expansion,
  optional-flag drop, transport capabilities, prompt-prefix styles).
- Root `pytest.ini` (testpaths `console/tests`) + `console/requirements-dev.txt`.
  pytest is dev-only; the console runtime stays stdlib.
- **Found and fixed a real defect while writing them:** `trackers._next_id` derived the
  next id from the current item list, so removing `D-2` handed `D-2` straight back to the
  next bug. Tracker ids are cited in durable markdown, so a reused id silently re-points
  an existing citation. Replaced with a monotonic `meta.seq`, floored by the highest
  existing id so pre-existing files can't collide either. 4 cases cover it.

**CC-T001-03 — skill lint — done (2 h, on estimate).**

- `console/server/harness_lint.py` + `kanban harness lint [--strict] [--json]`.
  Errors: missing/mismatched frontmatter name, missing description, dead
  `.claude/skills|agents/...` paths, empty skill dir. Warnings: orphan skill, agent with
  no `tools:`, CLAUDE.md roster counts that disagree with disk. Non-zero exit on errors
  only — warnings need `--strict`, because a lint that fails CI on a maybe gets disabled.
- **The first run found three things, two of which were bugs in the linter**, which is the
  useful outcome: (a) the skill-path regex stopped at the first slash, reporting the
  *directory* `template/scripts` as a missing file; (b) `challenge-standards/` has no
  SKILL.md because it is a shared reference bundle, not an invocable skill — counting it
  made the roster 40 and contradicted CLAUDE.md's 39. Both fixed; bundles are now a
  recognised category. Real harness now: **39 skills, 7 agents, 0 errors, 0 warnings** —
  matching CLAUDE.md exactly.
- Orphan detection initially matched bare words and therefore cleared every skill
  (`plan`, `verify`, `fix` are ordinary English). Tightened to real invocation forms
  (`/id`, `` `id` ``, `[[id]]`, explicit path). 24 tests prove each check both fires on a
  planted fault and stays quiet on a clean tree — a linter reporting zero is otherwise
  indistinguishable from one that cannot report.

**CC-T001-06 — CI and pre-commit — done (1 h vs 2 h est). Pulled ahead of 04/05**
(its dependencies 02 and 03 were met, and having it in place guarded the telemetry work).

- `.github/workflows/verify.yml`: tests on py3.11/3.13, harness lint, and a read-only CLI
  smoke job covering the verbs the session hooks call on every start.
- `.githooks/pre-commit`: lint only, and only when the commit touches `.claude/` or
  CLAUDE.md. Opt-in via `git config core.hooksPath .githooks`. No pytest — a slow hook
  gets `--no-verify`'d and then gates nothing.
- Verified: workflow YAML parses, both hook branches behave, jobs run the same commands
  as local.

**CC-T001-04 + 05 — telemetry and skill usage — done (3 h vs 5 h est).**

- `console/server/telemetry.py`: one JSONL record per **turn** (not per session — a
  session-level total cannot answer "which stage cost that"), monthly files under
  `knowledge-center/telemetry/`. Records carry tokens, model, backend, mode, ticket,
  skill, persona, duration — and no prompt text, tool arguments, or file content.
- **Cost is never invented.** Backend-reported cost wins; otherwise
  `console/config/pricing.toml` (exact match, then longest prefix, so a dated release
  needs no row of its own); otherwise `null`. Unpriced turns are counted and every total
  containing one is marked partial with a `*`. Substituting 0.0 would make an incomplete
  total look cheap — wrong in exactly the direction that matters.
- Wired at `BaseSession._observe`'s `turn.end`, so it is transport-agnostic and will cover
  the future OpenRouter backend without change. Wrapped so a telemetry failure can never
  kill the chat it is measuring; a test asserts that.
- `ticket` threaded through `agent_manager.create` → `agent_session.build` → session, and
  accepted by the HTTP chat route. **The Agents tab UI does not send it yet** — logged as
  TD-1, not silently skipped.
- CLI: `telemetry [--by ticket|model|skill|persona|backend|day] [--ticket] [--skill]
  [--since] [--until] [--json]` and `telemetry skills`. The skills report partitions the
  roster into fired / never-fired and states in its own output that never-fired is a
  candidate for review, not a verdict — a hand-typed `/skill` in a terminal leaves no
  record here.
- 32 tests, including 5 that drive a real `agent_session` through `turn.end` to prove the
  wiring, not just the module.

**Task 01 follow-up:** docs updated where the harness says docs live — `console/README.md`
verb list, `console/SKILL.md` usage block and config map, README structure comment.

- Done: all six plan tasks. **160 tests passing; harness lint clean.**
- Blocked: `.claude/settings.local.json` edit — permission classifier denied it (TD-2).
- Next: VERIFY — reconcile plan checkboxes, write verification, then Phase 1 (Body).

## Links
- [[CC-T001-summary]] · [[CC-T001-analysis]] · [[CC-T001-requirements]] · [[CC-T001-decision-log]] · [[CC-T001-plan]] · [[CC-T001-progress]] · [[CC-T001-verification]]

