---
ticket: "CC-T001"
artifact: plan
---

# Plan: CC-T001

## Approach

Flat mode — six independent tasks, one dependency edge (telemetry writes records that the
skill-usage report reads). No slicing; nothing here needs a component graph.

Order is cheapest-and-safest first: config defects, then the test harness, then CI to hold
it, then the two new capabilities (skill lint, telemetry).

Constraint carried from the dossier: **zero new runtime dependencies**. The console runs on
stdlib Python today; tests use `pytest` as a dev-only dependency, and CI installs it there.

## Tasks

> **Amendment 2026-08-29 (post-build):** task 01's D3 line below is understated. The
> `[agents.backends]` block was not dead config — the `kanban agents *` CLI path read it
> while the Agents tab read `agents.toml`. The fix was to collapse the two registries into
> one, not merely to delete a block. Rationale and evidence:
> [[CC-T001-verification]] § Scope changes. Left as written rather than rewritten, so the
> plan still shows what was believed at planning time.

### [x] CC-T001-01 — Fix the three config defects (1 h)

- [x] D1 — `.claude/settings.json`: add a real `permissions` block (ask-gates on
      `git push`, `git commit`, `gh pr create`, `WebFetch`, `WebSearch`); remove the
      non-schema keys `workspace`, `agents`, `skills`, `claudeCode.defaultMode`,
      `claudeCode.permissions.allow`, preserving any content still wanted in a file
      something reads
- [x] D2 — `knowledge-center/investigations/` exists (done at dossier time)
- [x] D3 — delete the superseded `[agents.backends]` block from `console/config/console.toml`,
      keeping `agent_backends._from_legacy` intact as the fallback code path
- **Done-criteria:** `settings.json` parses and contains only schema keys; a `git push`
  attempt is gated; console still serves with `agents.toml` present and with it absent.
- **Basis:** dossier §1 DEFECTS
- **Depends on:** —

### [x] CC-T001-02 — Console unit tests (3 h)

- [x] `console/tests/` with pytest, fixture repo root under `tmp_path`
- [x] `tomlio` — round-trip, atomic write, malformed input
- [x] `tickets` — create / move / set, id-pattern rejection, duplicate refusal
- [x] `trackers` — add / list / update / blockers across questions, bugs, todos
- [x] `boards` — lane mapping, enabled-board filtering
- [x] `agent_backends` — placeholder expansion, empty-placeholder arg dropping, legacy fallback
- **Done-criteria:** `pytest console/tests` green; every test uses a temp fixture root and
  never touches the real vault.
- **Basis:** dossier §2 item #5 layer 1
- **Depends on:** —

### [x] CC-T001-03 — Skill lint (2 h)

- [x] `console/kanban.py harness lint` — frontmatter schema (`name`, `description` present;
      `name` matches directory), referenced-skill existence across all SKILL.md bodies,
      orphan detection (skill referenced by no agent and no other skill), agent→skill graph
      validity
- [x] Report-only; non-zero exit on error-level findings so CI can gate on it
- **Done-criteria:** runs clean or reports real findings on the current 39 skills / 7 agents;
  exit code is 0 only when there are no errors.
- **Basis:** dossier §2 item #5 layer 3; ports the fork's `verify_harness.py` idea generically
- **Depends on:** —

### [x] CC-T001-04 — Token and cost telemetry (4 h)

- [x] Capture per-turn usage from the normalized agent event stream (input, output, cached,
      model, backend, ticket, skill/persona)
- [x] Persist one record per run under a configured `telemetry_dir`; never commit transcripts
- [x] `kanban telemetry` CLI — totals by ticket, by stage, by model, by skill
- [x] Cost derived from a `console/config/pricing.toml` table, missing entries reported as
      unknown rather than silently zero
- **Done-criteria:** a completed chat writes a record; `kanban telemetry --ticket CC-T001`
  reports non-zero tokens; a model absent from pricing shows `cost: unknown`, not `0`.
- **Basis:** dossier §3 addition #1 — gates roadmap items #2 and #6
- **Depends on:** CC-T001-02 (test fixtures reused)

### [x] CC-T001-05 — Skill usage report (1 h)

- [x] `kanban telemetry skills` — invocation count per skill from telemetry records, with
      never-fired skills listed explicitly
- **Done-criteria:** lists all 39 skills, partitioned into fired / never-fired.
- **Basis:** dossier §3 addition #5 — the evidence input for roadmap item #6
- **Depends on:** CC-T001-04

### [x] CC-T001-06 — CI and pre-commit (2 h)

- [x] `.github/workflows/verify.yml` — pytest + skill lint on push and PR
- [x] `.githooks/pre-commit` — skill lint only (fast); documented opt-in via
      `git config core.hooksPath .githooks`
- **Done-criteria:** workflow file valid; both jobs pass locally via the same commands CI runs.
- **Basis:** dossier §2 item #5
- **Depends on:** CC-T001-02, CC-T001-03

## Effort

| Task | Estimate | Basis |
| --- | --- | --- |
| CC-T001-01 — Config defects | 1 h | 3 known edits, all located |
| CC-T001-02 — Console unit tests | 3 h | 5 modules, ~25 cases |
| CC-T001-03 — Skill lint | 2 h | frontmatter + 2 graph checks |
| CC-T001-04 — Telemetry | 4 h | new capture path + storage + CLI |
| CC-T001-05 — Skill usage report | 1 h | read-only over 04's records |
| CC-T001-06 — CI and pre-commit | 2 h | 1 workflow, 1 hook |
| **Total** | **13 h** | flat-mode estimate, no cone applied |

### Acceptance criterion coverage

| Acceptance Criterion | Covered by |
| --- | --- |
| Permission gates exist and fire | CC-T001-01 |
| Console has a green test suite | CC-T001-02 |
| Harness wiring is machine-checked | CC-T001-03 |
| Token and cost are measurable per ticket | CC-T001-04 |
| Skill pruning has an evidence base | CC-T001-05 |
| Regressions are caught before merge | CC-T001-06 |

## Risks

| Risk | Likelihood | Impact | Mitigation | Owner |
| --- | --- | --- | --- | --- |
| Telemetry capture couples to one backend's event shape | Med | High | Capture at the normalized-event layer, not per backend; assert with a fixture stream per transport | Builder |
| Removing settings.json keys breaks something that silently read them | Low | Med | Grep the repo for each key before deleting; the keys are non-schema, so only our own code could be reading them | Builder |
| Pricing table drifts from provider reality | High | Low | Report `unknown` for missing entries; never guess a rate | Builder |
| pytest as a new dev dependency | Low | Low | Dev-only, not imported by console runtime; CI installs it | Builder |

## Dependencies

- Blocks: Phase 1 (Body) — verbs, MCP server, worktrees, job queue
- Blocked by: —

## Links
- [[CC-T001-summary]] · [[CC-T001-analysis]] · [[CC-T001-requirements]] · [[CC-T001-decision-log]] · [[CC-T001-plan]] · [[CC-T001-progress]] · [[CC-T001-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
