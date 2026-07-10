# control-center-workspace

A **project-independent agentic harness** for **Claude Code** and **Cursor**. Pair the same agent pipeline (definitions under `.claude/`) with an Obsidian knowledge vault and a structured ticket lifecycle, so every piece of work — feature, bug, refactor — produces a paper trail you can navigate, audit, and resume months later.

This workspace doesn't contain your project's source code. It sits *next to* your projects and tracks them: their requirements, plans, decisions, progress, and verification — all as plain Markdown the agents read and write.

---

## Table of contents

1. [Workspace structure](#workspace-structure)
2. [The agent pipeline](#the-agent-pipeline)
3. [Agents in detail — step by step](#agents-in-detail--step-by-step)
4. [The role of Obsidian](#the-role-of-obsidian)
5. [Adding a project to the workspace](#adding-a-project-to-the-workspace)
6. [Working on a new project](#working-on-a-new-project)
7. [Working on an existing project](#working-on-an-existing-project)
8. [Creating and working a ticket — step by step](#creating-and-working-a-ticket--step-by-step)
9. [Anatomy of a ticket](#anatomy-of-a-ticket)
10. [Worked example: end-to-end](#worked-example-end-to-end)
11. [Common operations](#common-operations)
12. [Conventions](#conventions)
13. [Where to read more](#where-to-read-more)

---

## Workspace structure

```
control-center-workspace/
├── .claude/
│   ├── agents/                    # 6 agent definitions
│   │   ├── harness.md             # Orchestrator
│   │   ├── analyst.md             # GROUND, CLARIFY
│   │   ├── planner.md             # CANONICAL
│   │   ├── builder.md             # TEMPLATE, SIMPLIFY
│   │   ├── verifier.md            # VERIFY
│   │   └── fixer.md               # Any stage
│   ├── skills/                    # Skill scripts the agents call
│   │   ├── kickoff/               # Seeds a new ticket
│   │   ├── trace-context/         # Loads ticket state at turn start
│   │   ├── harness-standards/     # Always-on gates + comms/evidence/test norms
│   │   ├── do/                    # Free-form autonomous dispatch entry point
│   │   ├── analyze/               # → analysis.md
│   │   ├── draft-requirements/    # → requirements-draft.md (v0)
│   │   ├── analyze-context/       # Grounds the draft in codebase + prior artifacts
│   │   ├── identify-gaps/         # Surfaces missing stakeholders/rules/edge cases/NFRs + existing-feature overlap
│   │   ├── enrich-requirements/   # Replaces placeholders with concrete facts
│   │   ├── iterate-requirements/  # Applies a feedback round, bumps iteration
│   │   ├── challenge-requirements/# Adversarial pre-freeze check
│   │   ├── freeze-requirements/   # Final gate → requirements.md
│   │   ├── extract-stories/       # → user stories with acceptance criteria
│   │   ├── tech-select/           # Gated stack/library/pattern decision → decision-log.md
│   │   ├── clarify/               # Resolves open questions into decisions
│   │   ├── questions/             # → questions.md (open-question lifecycle)
│   │   ├── bugs/                  # → open-bugs.md (defects/regressions)
│   │   ├── todos/                 # → open-todos.md (misc tasks)
│   │   ├── plan/                  # → plan.md (Approach/Slices; chains deeper skills)
│   │   ├── plan-effort/           # → plan.md (Tasks/Effort, flat case)
│   │   ├── analyze-components/    # Maps ticket scope to components + dependency graph/critical path
│   │   ├── breakdown-tasks/       # Slices → atomic tasks with AC + effort
│   │   ├── create-implementation-plan/ # Synthesizes phases → slices → tasks
│   │   ├── estimate-development/  # Upfront T-shirt sizing / envelope estimate
│   │   ├── generate-effort-forecast/   # Mid-build variance + remaining-effort forecast
│   │   ├── replan/                # Re-break-down on scope/architecture change
│   │   ├── risk-scan/             # → plan.md (Risks)
│   │   ├── challenge-plan/        # Adversarial pre-build check
│   │   ├── progress-tracker/      # → progress.md (every step)
│   │   ├── fix/                   # Root-cause + patch
│   │   ├── evolve/                # Amend frozen artifacts
│   │   ├── reconcile/             # Detect artifact drift
│   │   ├── handoff/               # Stage gate
│   │   ├── verify/                # Scoped unit/integration/e2e/review/ready checks
│   │   ├── challenge-implementation/ # Adversarial pre-verify check
│   │   ├── criticize/             # Routes to challenge-* by stage
│   │   ├── generate-test-cases/   # → traceable test-case artifact
│   │   ├── validate-artifacts/    # Confirms all ticket artifacts are well-formed
│   │   ├── check-artifact-links/  # Bidirectional cross-artifact links + requirements traceability
│   │   ├── trace/                 # UP/DOWN link report for one file
│   │   ├── template/              # Lists/applies vault + Cursor templates
│   │   ├── consolidate/           # Artifact layout/naming migration
│   │   ├── caveman/               # Terse output mode
│   │   ├── log-work/              # Appends per-author daily activity log
│   │   ├── work-summary/          # Read-only timesheet recap
│   │   ├── optimize-cursor-artifacts/ # Token-reduction pass on config/skills
│   │   ├── project-layout/        # Workspace/git conventions, multi-project routing
│   │   ├── standup/               # Cross-ticket digest
│   │   └── close-work/            # Finalize and archive
│   ├── projects/control-center/
│   │   └── memory/                # Persistent memory across sessions
│   ├── hooks/
│   │   └── session-context.sh     # Claude Code SessionStart: artifact map context
│   ├── settings.json              # Workspace config
│   └── settings.local.json        # Per-machine permissions (gitignored)
├── .cursor/                       # Cursor-only wiring (same harness; no duplicate agents/skills)
│   ├── rules/
│   │   └── control-center-harness.mdc   # always-on rules for this repo
│   ├── hooks/
│   │   └── session_context.py     # sessionStart: same artifact-map idea as Claude hook
│   ├── hooks.json                 # Registers Cursor hooks (e.g. sessionStart)
│   ├── skills/
│   │   └── README.md              # Points here: canonical skills stay under .claude/skills/
│   └── projects/control-center/
│       └── README.md              # Notes shared memory path (.claude/.../memory/)
├── knowledge-center/              # The Obsidian vault
│   ├── artifact-map.md            # Index of every ticket
│   ├── knowledge-center-index.md  # Vault entry point
│   ├── artifacts/
│   │   ├── _template/             # Files copied + renamed when a ticket is seeded
│   │   ├── T001/                  # One directory per ticket
│   │   │   ├── T001-summary.md    # Every artifact prefixed with the ticket id
│   │   │   ├── T001-analysis.md
│   │   │   └── ...
│   │   ├── T002/
│   │   └── ...
│   └── wiki/                      # Long-lived reference docs (ADRs, guides)
├── .obsidian/                     # Obsidian's own config
├── CLAUDE.md                      # Instructions Claude Code reads on every session
├── CURSOR.md                      # Same harness story for Cursor (paths, hooks, conventions)
├── AGENTS.md                      # Short Cursor entry point → CURSOR.md + .claude/
└── control-center-workspace.code-workspace   # VS Code multi-folder workspace
```

**The deal:** agent and skill definitions live only in **`.claude/`** (both products use those files). Knowledge — every ticket's plan, progress, decisions — lives in **`knowledge-center/`**. Your project source code lives in a sibling directory you add as a workspace folder.

### Using Cursor

- Read **`CURSOR.md`** (mirrors `CLAUDE.md` for Cursor-specific paths and behavior).
- **`AGENTS.md`** points at the same harness: skills and agents under **`.claude/skills/`** and **`.claude/agents/`** — this repo does **not** copy them under `.cursor/`.
- **`.cursor/rules/`** supplies always-on project rules; **`.cursor/hooks.json`** + **`.cursor/hooks/`** run Cursor lifecycle hooks (e.g. `sessionStart` injects Active/Blocked lines from `artifact-map.md`, parallel to the Claude Code `SessionStart` hook).
- Where **`.claude/agents/harness.md`** says to delegate to another agent, Claude Code uses the **Agent** tool; in Cursor use the **Task** tool with the same specialist roles (`harness`, `analyst`, `planner`, `builder`, `verifier`, `fixer`, etc.).

---

## The agent pipeline

Six stages, six agents. Each stage produces a specific artifact and hands off through a gate to the next. The specialist definitions live under `.claude/agents/` and apply whether you drive the harness from **Claude Code** or **Cursor** (see [Using Cursor](#using-cursor) above for delegation differences).

```
GROUND ──→ CLARIFY ──→ CANONICAL ──→ TEMPLATE ──→ SIMPLIFY ──→ VERIFY ──→ Closed
analyst    analyst     planner       builder      builder      verifier
                                                                    │
                                                              fixer ◄┘ (on failure)
```

| Stage | Agent | Output artifact | What "done" means |
|-------|-------|-----------------|-------------------|
| GROUND | analyst | `analysis.md` | Findings, current state, recommended path |
| CLARIFY | analyst | `requirements.md`, `decision-log.md`, `questions.md` | Frozen requirements with no open questions |
| CANONICAL | planner | `plan.md` | Slices, tasks, effort, risks, AC coverage |
| TEMPLATE | builder | Source code + `progress.md` | Each task implemented to its done-criteria |
| SIMPLIFY | builder | Refined source + `progress.md` | Code reviewed for reuse and clarity |
| VERIFY | verifier | `verification.md` | Every acceptance criterion has cited evidence |

The **harness** agent orchestrates the flow: it reads the ticket state, picks the next stage, and routes to the right specialist. The **fixer** can be invoked at any stage when something fails.

---

## Agents in detail — step by step

This section walks through each agent in the order it gets used during a ticket lifecycle, with concrete examples. Six agents, one job each.

### 0. Harness — the orchestrator

**Role.** Entry point and traffic cop. The harness never writes code, never writes requirements. It reads the current state of a ticket, decides which stage is next, and delegates to the specialist agent for that stage.

**When it runs.** Every time you invoke a multi-step task or are unsure which stage to run. Whenever you say *"work on T013"* without specifying a stage, the harness picks up.

**Inputs.** The ticket id. Optionally a stage hint.

**Skills used.** `kickoff`, `trace-context`, `handoff`, `reconcile`, `standup`, `close-work`. Also owns two entry points: `do` for free-form autonomous dispatch (`/do {request}` — classifies the request into a lane, routes it, and drives an iterate-until-done loop without you naming a stage), and `criticize` for adversarial-review routing (sends a request to `challenge-requirements` / `challenge-plan` / `challenge-implementation` depending on the stage).

**Routing logic** (simplified — full table is in `.claude/agents/harness.md`):

| Ticket state | Agent it routes to |
|--------------|--------------------|
| New ticket, no analysis yet | analyst |
| Analysis exists, no requirements | analyst |
| Requirements frozen, no plan | planner |
| Plan with unchecked tasks | builder |
| All tasks `[x]`, no verification | verifier |
| Verification has unmet criteria | fixer |
| Verification clean | itself → `close-work` |

**Example interaction:**

> **You:** Work on T013.
>
> **Harness output:**
> ```
> ── Harness ──
> Ticket: T013
> Stage: GROUND → CLARIFY
> Active artifacts: [T013-summary, T013-analysis]
> Handoff: GROUND → CLARIFY
> Gate: ready (analysis.md exists; recommended path stated)
> Routed to: analyst
> Next: analyst T013
> ```
>
> Then the harness invokes the analyst with ticket id `T013`.

**Rule.** The harness states the stage on every turn. It never skips stages. If requirements are ambiguous after one analyst pass, it stops and asks you.

---

### 1. Analyst — GROUND + CLARIFY

**Role.** The only agent that reads code purely for understanding. Produces `analysis.md` (what's there) via GROUND, then drives a granular pre-freeze pipeline through CLARIFY that ends in a frozen `requirements.md`, a `decision-log.md`, and a clean `questions.md` queue.

**When it runs.** Right after `/kickoff`, and again whenever requirements need to be re-validated.

**Inputs.** Ticket id, your intent (the title and any extra context you give).

**Skills used.** `trace-context`, `analyze`, `draft-requirements`, `identify-gaps`, `enrich-requirements`, `iterate-requirements`, `challenge-requirements`, `freeze-requirements`, `extract-stories`, `clarify`, `questions`.

**Protocol:**

1. **GROUND** — runs `analyze`: surveys the relevant code with Glob+Grep, cites file:line for every claim, writes `T013-analysis.md` with Context / Current State / Key Findings / Research / Recommended Path.
2. **CLARIFY** — drives the requirements pipeline, each stage a separate skill:
   - `draft-requirements` writes a v0 `T013-requirements-draft.md` from your intent (functional, non-functional, business rules, edge cases — placeholders marked `〈TBD〉`).
   - `identify-gaps` surfaces missing stakeholders, rules, edge cases, NFRs, data flows, integrations, compliance — plus, in the same pass, cross-checks the draft against existing features in the codebase for overlap/conflict/reuse.
   - `enrich-requirements` replaces placeholders with concrete facts from the codebase.
   - `iterate-requirements` applies a round of your feedback and bumps the iteration counter — repeat as needed.
   - `questions`/`clarify` — anything still ambiguous goes into `T013-questions.md`; each resolved question gets a slug entry in `T013-decision-log.md`.
   - `challenge-requirements` — adversarial pass for ambiguity/contradictions/untestable criteria. If any `block` items, loops back to the relevant step above.
   - `freeze-requirements` — final gate; on pass, finalizes `T013-requirements.md` and hands off to `extract-stories`.

**Example interaction:**

> **You:** Kickoff T013 — add a dark-mode toggle to my-app, persistent across sessions.
>
> **Harness** seeds the ticket via `kickoff`, then routes to **analyst**.
>
> **Analyst output (after GROUND pass):**
> ```
> ── Analyst ──
> Ticket: T013
> Phase: drafting
> Iteration: 1
> Draft status: v1
> Freeze gate: open
> Open blockers: 0
> Gaps: stakeholders=0 rules=0 edge=2 NFR=1 data=0 integration=0 compliance=0
> Artifacts: T013-analysis.md
> Next: draft-requirements T013
> ```
>
> `T013-analysis.md` now contains:
> ```
> ## Current State
> - main.dart:42 hardcodes ThemeData.light()
> - No theme service exists
> - Material 3 supports dark via ColorScheme.fromSeed(brightness:)
>
> ## Key Findings
> - SharedPreferences is already used for locale persistence — same pattern fits theme
> - Existing widgets read ThemeData.of(context) — no refactor needed
>
> ## Open questions
> - Should the system-theme option be the default?
> - Does the app need a smooth transition animation?
> ```
>
> The analyst surfaces the open questions to you. After you answer, it runs `clarify` to record them in `decision-log.md`, folds them back into the draft via `enrich-requirements`, then runs `challenge-requirements` and `freeze-requirements` to finalize `requirements.md`.

**Rule.** Cite file:line for every claim. Never invent unstated requirements. Never write `plan.md` or code.

---

### 2. Planner — CANONICAL

**Role.** Turns frozen requirements into an executable plan. Writes `plan.md` with approach, slices, tasks, effort, AC coverage, and risks.

**When it runs.** Only after the analyst's `freeze-requirements` gate has passed (no `block` items).

**Inputs.** Ticket id. Reads `T013-requirements.md`, `T013-analysis.md`, `T013-decision-log.md`.

**Skills used.** `trace-context`, `extract-stories`, `plan`, `risk-scan`, `plan-effort`, `challenge-plan` — plus, for multi-layer tickets, `analyze-components` (includes dependency graph), `breakdown-tasks`, `create-implementation-plan`, `estimate-development`, `generate-effort-forecast`, `replan`.

**Protocol:**

1. Confirm requirements frozen — if not, route back to analyst.
2. `extract-stories` — pull user stories + acceptance criteria from frozen requirements.
3. `plan` — write Approach + Slices, then decide structure using a concrete tiebreaker (1 component and ≤6 tasks → single-layer; otherwise multi-layer):
   - **Single-layer** ticket (like the dark-mode example below): hand off directly to `plan-effort` — decompose into tasks (1–4 h each), every task gets done-criteria + basis + dependencies.
   - **Multi-layer** ticket (spans several components, e.g. data + service + UI): chain `analyze-components` (maps components and builds the dependency graph/critical path in one pass) → `breakdown-tasks` → `estimate-development` → `create-implementation-plan` instead of the flat `plan-effort` list.
4. `risk-scan` — fill the Risks table (Likelihood × Impact × Mitigation). Reject any high×high without a mitigation.
5. `challenge-plan` — adversarial self-check: every AC mapped to ≥1 task, every effort has a basis, dependencies are real. Unresolved critical findings block handoff to builder; re-run after `replan` if scope shifts, and re-check totals with `generate-effort-forecast` mid-build.

**Example interaction:**

> **You:** Plan T013.
>
> **Planner output:**
> ```
> ── Planner ──
> Ticket: T013
> Artifacts: T013-summary.md, T013-plan.md (updated)
> Slices: 2
> Tasks: 6 total
> Effort: 9h estimated
> Risks: 3/3 mitigated (high×high: 0)
> AC coverage: 5/5 acceptance criteria mapped to tasks
> Next: builder on slice-1
> ```
>
> `T013-plan.md` now contains:
> ```
> ## Approach
> Introduce ThemeService extends ChangeNotifier, persist via SharedPreferences,
> wire into MaterialApp.themeMode. Reuses the LocaleService pattern (analysis §3).
>
> ## Slices
> ### Slice 1 — Theme service + persistence (4h)
> ### Slice 2 — Settings UI + animation (5h)
>
> ## Tasks
> ### [ ] T013-01 — Add ThemeMode enum + ThemeService (1.5h)
> - **Done-criteria:** ThemeService extends ChangeNotifier, exposes mode getter
> - **Basis:** Mirrors LocaleService at lib/core/locale_service.dart:18
> - **Depends on:** —
> ...
> ```

**Rule.** No task without done-criteria. No effort without basis. Every AC must be covered. Doesn't write code.

---

### 3. Builder — TEMPLATE + SIMPLIFY

**Role.** The only agent that writes source files. Picks the next unchecked task in `plan.md`, implements it to its done-criteria, marks it `[x]`, logs progress, then refines.

**When it runs.** When `plan.md` exists with unchecked tasks. **One task per turn** — you stay in control.

**Inputs.** Ticket id. Optionally a specific task id.

**Skills used.** `trace-context`, `progress-tracker`, `simplify`, `evolve(plan)`.

**Protocol:**

**TEMPLATE** (per task):
1. Pick the next `[ ]` task in `plan.md`.
2. Implement the **minimum** that meets the done-criteria. No scope drift.
3. Run analyzer / type-check / unit tests on the changed files.
4. `progress-tracker` with `done: T013-01`, files touched, test status.
5. Mark `[x]` in `plan.md`.

**SIMPLIFY** (after a slice or significant change):
6. Run `simplify` on changed files: dedupe, drop dead code, tighten names.
7. Log a progress entry if simplification was non-trivial.

**Example interaction:**

> **You:** builder T013.
>
> **Builder output (turn 1):**
> ```
> ── Builder ──
> Ticket: T013
> Slice: slice-1
> Layers: UI (theme service)
> Task: T013-01 — Add ThemeMode enum + ThemeService
> Tasks done: 1/4 in slice
> Files: 2 modified — [lib/core/theme_service.dart (new), lib/main.dart]
> Done-criteria met: yes (ThemeService extends ChangeNotifier, exposes mode getter)
> Progress: T013-plan.md ([x] T013-01) + T013-progress.md updated
> Next: T013-02
> ```
>
> Next turn:
>
> ```
> ── Builder ──
> Ticket: T013
> Slice: slice-1
> Task: T013-02 — Persist ThemeMode to SharedPreferences
> Tasks done: 2/4 in slice
> Files: 1 modified — [lib/core/theme_service.dart]
> Done-criteria met: yes (theme survives app restart in unit test)
> Progress: T013-plan.md ([x] T013-02) + T013-progress.md updated
> Next: T013-03
> ```
>
> **What happens if a task can't be done as planned?** Builder runs `evolve(target=plan)` with a reason and routes back to planner. No silent rewrites.

**Rule.** One task per turn. No backwards-compat shims unless the plan calls for them. No fix to unrelated code (that's the fixer's job).

---

### 4. Verifier — VERIFY

**Role.** Confirms every acceptance criterion has cited evidence. Walks `requirements.md` AC by AC, runs tests, fills `verification.md`. Doesn't write source.

**When it runs.** When all plan tasks are `[x]` and the slice is built.

**Inputs.** Ticket id. Reads `T013-requirements.md` (acceptance criteria), `T013-plan.md` (done-criteria), code, test output.

**Skills used.** `trace-context`, `challenge-implementation`, `generate-test-cases`, `verify`, `check-artifact-links`, `reconcile`, `validate-artifacts`, `progress-tracker`, `close-work`.

**Protocol:**

1. `challenge-implementation` — adversarial pass for plan/trace drift before formal verify; unresolved critical findings block further verify.
2. `generate-test-cases` — produce or refresh the traceable test-case artifact if it's missing or stale vs. current acceptance criteria; this becomes the test plan verify consumes.
3. `verify` — run the scoped checks (unit/integration/e2e/review/ready). Capture pass/fail with file:line.
4. For each acceptance criterion, walk the code path — write a row in `T013-verification.md` with Status (PASS / FAIL / PENDING) and Evidence (cited file:line, test name, screenshot link).
5. Probe edge cases: empty input, large input, concurrent calls, malformed data.
6. `check-artifact-links` — confirm the full requirements-to-evidence traceability chain and bidirectional links.
7. Run `reconcile` to catch artifact drift (plan ↔ progress ↔ verification).
8. `validate-artifacts` — confirm all ticket artifacts are complete and correctly structured. Fails any green-by-default row.
9. **Clean** → invoke `close-work`. **Unmet** → log a blocker in `progress.md` and route to **fixer**.

**Example interaction:**

> **You:** verifier T013.
>
> **Verifier output:**
> ```
> ── Verifier ──
> Ticket: T013
> Scope: all
> Tests: 387 | Passing: 386 | Failing: 1
> Acceptance Criteria: 4/5 PASS (1 FAIL: AC-3 system-theme follow on desktop)
> Static-only: no
> Blockers: 1 (theme_service.dart:88 — Platform.brightness is null on Linux desktop)
> Issues by class: arch=0 security=0 perf=0 style=0
> Artifacts: T013-verification.md, T013-progress.md updated
> Next: fixer T013 (AC-3 blocker)
> ```
>
> `T013-verification.md` now contains a full AC table:
> ```
> | # | Criterion                    | Status | Evidence                                   |
> | 1 | Toggle visible in Settings   | PASS   | settings_screen.dart:88                    |
> | 2 | Persists across restart      | PASS   | theme_service_test.dart:42                 |
> | 3 | System-theme option works    | FAIL   | theme_service.dart:88 — null on Linux      |
> | 4 | WCAG AA contrast             | PASS   | manual audit (screenshots in progress.md)  |
> | 5 | Smooth animation on toggle   | PASS   | theme_animation_test.dart:18 (golden)      |
> ```

**Rule.** Every criterion needs cited evidence. Type checks/tests verify code, not features — say so explicitly when only static checks ran. Never green-by-default.

---

### 5. Fixer — any stage

**Role.** Diagnose, root-cause, minimal patch. Only invoked when something is broken: a failing test, an unmet acceptance criterion, a build error, or a blocker logged in `progress.md`.

**When it runs.** Whenever the verifier flags a FAIL, or whenever you yourself spot a broken test or bug.

**Inputs.** Ticket id, the symptom (failing test name, unmet AC, error message).

**Skills used.** `trace-context`, `fix`, `progress-tracker`, `evolve`, `simplify` (only if cleanup is incidental to the fix).

**Protocol** (the `fix` skill formalizes this):

1. **Reproduce.** Run the failing command. Capture exact output. No fix without reproduction.
2. **Diagnose.** Identify the root cause. Reject any explanation that requires `--no-verify`, exception swallowing, or mock-to-pass.
3. **Patch.** Minimal change to fix the root cause.
4. **Validate.** Add or update a test that would have caught this. Re-run.
5. **Log.** `progress-tracker` with a four-line entry: Symptom / Cause / Fix / Verification.
6. **Escalate if scope expands.** If the fix implies a design shift, run `evolve(target=plan)` or `evolve(target=requirements)` and route back to planner. Don't expand silently.

**Example interaction:**

> **You:** fixer T013 — AC-3 fails on Linux.
>
> **Fixer output:**
> ```
> ── Fixer ──
> Ticket: T013
> Mode: bug
> Issue: AC-3 system-theme follow fails on Linux desktop
> Reproduction: flutter test --no-pub test/services/theme_service_test.dart
>   → Expected: ThemeMode.dark, Actual: null (theme_service.dart:88)
> Root cause: WidgetsBinding.instance.platformDispatcher.platformBrightness
>   returns Brightness? on Linux until first frame; service read it synchronously
>   in the constructor.
> Files modified: [lib/core/theme_service.dart]
> Patch: theme_service.dart:88 — wrap initial read in addPostFrameCallback,
>   default to ThemeMode.system until resolved
> Validation test: theme_service_test.dart:71 — new test "system theme on Linux
>   defaults to system before first frame"
> Status: fixed
> Next: verifier T013 (re-run AC-3)
> ```
>
> The fixer hands control back to the **verifier**, who re-runs AC-3, sees PASS, and proceeds to `close-work`.

**Rule.** No fix without reproduction. No suppression to make CI pass. If the fix expands scope, stop and route to planner.

---

### Putting it together

A typical end-to-end sequence for ticket T013:

```
You:        /kickoff T013 "Add dark-mode toggle"
Harness:    seeds ticket → routes to analyst
Analyst:    GROUND → writes T013-analysis.md
Analyst:    CLARIFY → draft-requirements → identify-gaps → asks 2 questions
You:        answers questions
Analyst:    records in T013-decision-log.md → enrich/challenge → freeze-requirements
Harness:    handoff CLARIFY→CANONICAL → routes to planner
Planner:    writes T013-plan.md (2 slices, 6 tasks, 9h, 5/5 AC, 0 high×high risk)
Harness:    handoff CANONICAL→TEMPLATE → routes to builder
Builder:    T013-01 [x] → T013-02 [x] → T013-03 [x]  (slice 1 done)
Builder:    SIMPLIFY pass on slice 1
Builder:    T013-04 [x] → T013-05 [x] → T013-06 [x]  (slice 2 done)
Harness:    handoff SIMPLIFY→VERIFY → routes to verifier
Verifier:   4/5 AC PASS, AC-3 FAIL → routes to fixer
Fixer:      reproduces → root-causes → patches → adds test → marks fixed
Verifier:   re-runs → 5/5 AC PASS → invokes close-work
Harness:    close-work → ticket archived in artifact-map under Completed
```

Every step leaves a trail in the ticket directory. Months later you `grep T013 knowledge-center/` and the entire reasoning chain is in eight files.

---

## The role of Obsidian

The `knowledge-center/` directory is an **Obsidian vault**. Open it in Obsidian and you get:

- **Backlinks** — see every artifact that references this ticket.
- **Graph view** — visualize ticket dependencies and wiki cross-links.
- **Tag search** — `#active`, `#blocked`, `#completed` filter the artifact map instantly.
- **Wiki-style links** — `[[T012-summary]]` jumps straight there.

You don't *need* Obsidian — every file is plain Markdown — but it's the intended reading interface. Treat Claude Code as the **writer** of artifacts and Obsidian as the **reader/navigator**.

**Setup:**
1. Install Obsidian.
2. *Open folder as vault* → select `D:\Workspace\control-center-workspace\knowledge-center`.
3. Optional: enable the **Backlinks**, **Graph**, and **Tag pane** core plugins.

---

## Adding a project to the workspace

The workspace is multi-root: it tracks tickets for any number of sibling projects.

### One-time setup

1. Clone or create your project as a sibling directory:

   ```
   D:\Workspace\
   ├── control-center-workspace\        ← this repo
   ├── my-app\                          ← your project
   └── another-service\                 ← another project
   ```

2. Open `control-center-workspace.code-workspace` in VS Code and add a folder entry:

   ```json
   {
     "folders": [
       { "path": "." },
       { "path": "../my-app" },
       { "path": "../another-service" }
     ]
   }
   ```

3. Open VS Code → **File → Open Workspace from File** → pick `control-center-workspace.code-workspace`. You now see both the harness and your project in the same window.

That's it. Claude Code launched from this workspace can read both your project source and the harness artifacts.

---

## Working on a new project

You're starting from scratch. The workspace helps you go from "I have an idea" to "I have a working slice" without losing the trail.

```
1. Create the project directory     →  cd ../ && mkdir my-new-app
2. Add it to .code-workspace         →  edit folders array (above)
3. Kickoff the bootstrap ticket      →  /kickoff T001 "Bootstrap my-new-app"
4. analyst writes analysis.md        →  surveys the empty repo, recommends stack
5. analyst drafts requirements.md    →  what the v0 must do
6. planner writes plan.md            →  slices: scaffolding → first feature → CI
7. builder implements slice 1        →  code lands in ../my-new-app
8. verifier confirms acceptance      →  verification.md with evidence
9. close-work archives the ticket    →  ticket moves to "Completed" in artifact-map
10. /kickoff T002 ...                →  next feature
```

Tell Claude: *"Kickoff a ticket to bootstrap my-new-app — Flutter mobile app, offline-first, with location services"* — and the harness routes it through the pipeline.

---

## Working on an existing project

You already have a codebase and want to track work in this harness.

```
1. Move/clone the project as a sibling   →  D:\Workspace\my-existing-app
2. Add it to .code-workspace             →  edit folders array
3. (Optional) /kickoff T001 "Onboard"    →  ticket whose only purpose is to
                                              survey the existing code, capture
                                              architecture in wiki/, log known
                                              issues
4. /kickoff T002 "Fix login crash"        →  start tracking real work
```

Tickets reference the project by **path**, not by import. The artifact files live in `knowledge-center/artifacts/T002/`; the code they describe lives in `../my-existing-app/lib/...`. The verifier cites `../my-existing-app/lib/auth/login_screen.dart:142` directly.

---

## Creating and working a ticket — step by step

### Step 1 — Seed the ticket

```
/kickoff T013 "Add dark-mode toggle"
```

This invokes the `kickoff` skill, which:
- Creates `knowledge-center/artifacts/T013/` from `_template/`.
- Fills frontmatter (id, date, owner) in every file.
- Adds a row to `artifact-map.md` under `## Active`.

Files seeded — every filename is **prefixed with the ticket id** so wikilinks resolve unambiguously across the vault:
```
T013/
├── T013-summary.md         # status, owner, links
├── T013-analysis.md        # empty — analyst will fill
├── T013-requirements.md    # empty — analyst will fill
├── T013-decision-log.md    # empty — populated as decisions are made
├── T013-questions.md       # empty — populated when ambiguity surfaces
├── T013-plan.md            # empty — planner will fill
├── T013-progress.md        # empty — every agent appends here
└── T013-verification.md    # empty — verifier will fill
```

Every artifact ends with a `## Links` block referencing every sibling — this makes each ticket render as a tightly-connected cluster in Obsidian's graph view.

### Step 2 — GROUND (analyze)

```
analyst T013
```

The analyst reads the ticket, surveys the relevant code with Glob+Grep, and writes `analysis.md`:
- Context (why this matters)
- Current state (file:line citations)
- Key findings
- Recommended path

**Output you'll see:**
```
── Analyst ──
Ticket: T013
Phase: drafting
Iteration: 1
Draft status: v1
Freeze gate: open
Open blockers: 0
Gaps: stakeholders=0 rules=0 edge=2 NFR=1 data=0 integration=0 compliance=0
Artifacts: analysis.md
Next: draft-requirements T013
```

### Step 3 — CLARIFY (requirements pipeline + open questions)

```
draft-requirements T013
```

Requirements aren't a single-shot draft — they move through a granular, gated pipeline, each stage its own skill:

```
draft-requirements → analyze-context → identify-gaps
  → enrich-requirements → iterate-requirements → challenge-requirements → freeze-requirements
  → extract-stories
```

1. `draft-requirements` writes a v0 `requirements-draft.md` from your intent — functional, non-functional, business rules, edge cases, with `〈TBD〉` placeholders and open questions for every assumption.
2. `analyze-context` / `identify-gaps` ground the draft in the codebase and surface missing stakeholders, rules, edge cases, NFRs, data flows, integrations, and compliance gaps — the same `identify-gaps` pass also cross-checks the draft against existing features for overlap, conflict, and reuse.
3. `enrich-requirements` replaces placeholders with concrete facts — never invents data.
4. Anything ambiguous adds a row to `questions.md` and asks you; `iterate-requirements` folds your answers back into the draft and bumps the iteration counter (repeat as needed).
5. `challenge-requirements` red-teams the draft (ambiguity, contradictions, untestable criteria) — any `block` finding loops back to the relevant step above.
6. `freeze-requirements` runs the final gate; on pass it writes `requirements.md` and hands off to `extract-stories`, which pulls user stories with acceptance criteria.

### Step 4 — CANONICAL (plan)

```
planner T013
```

The planner confirms requirements are frozen, runs `extract-stories` if not already done, then writes `plan.md`:
- Approach (one paragraph)
- Slices (vertical, deliverable units)
- Tasks — `plan-effort` for a flat, single-layer ticket, or `analyze-components` (maps components and the dependency graph in one pass) → `breakdown-tasks` → `create-implementation-plan` for a multi-layer one (numbered, sized 1–4 h, with done-criteria and basis)
- Effort table (optionally sanity-checked with `estimate-development` / `generate-effort-forecast`)
- AC coverage table (every AC mapped to ≥1 task)
- Risks table (likelihood × impact, mitigation)
- `challenge-plan` — adversarial self-check before handoff to builder; unresolved critical findings block build

```
── Planner ──
Ticket: T013
Slices: 2
Tasks: 6 total
Effort: 9h estimated
Risks: 3/3 mitigated (high×high: 0)
AC coverage: 5/5
Next: builder on slice-1
```

### Step 5 — TEMPLATE (build, one task at a time)

```
builder T013
```

The builder picks the first unchecked task in `plan.md`, implements it, marks `[x]`, and appends to `progress.md`. **One task per turn** — you keep control.

```
── Builder ──
Ticket: T013
Slice: slice-1
Task: T013-01 — Add ThemeMode enum and provider wiring
Tasks done: 1/4 in slice
Files: 2 modified — [lib/core/theme_service.dart, lib/main.dart]
Done-criteria met: yes
Progress: plan.md ([x] T013-01) + progress.md updated
Next: T013-02
```

Repeat until the slice is green.

### Step 6 — SIMPLIFY

After the slice lands, builder runs the `simplify` skill on changed files: dedupe, tighten, drop dead code, then logs a progress entry.

### Step 7 — VERIFY

```
verifier T013
```

The verifier first runs `challenge-implementation` (adversarial pass for plan/trace drift) and `generate-test-cases` (refresh the test-case artifact if stale), then walks every acceptance criterion, runs the scoped `verify` checks, cites file:line evidence, and fills `verification.md`. `check-artifact-links` confirms the full requirements-to-evidence traceability chain before `validate-artifacts` gives the final all-clear:

```
── Verifier ──
Ticket: T013
Scope: all
Tests: 387 | Passing: 387 | Failing: 0
Acceptance Criteria: 5/5 PASS
Static-only: no
Blockers: 0
Issues by class: arch=0 security=0 perf=0 style=0
Next: close-work T013
```

If anything fails, the verifier hands off to the **fixer**, who reproduces, root-causes, patches, and routes back. No green-by-default.

### Step 8 — Close

```
close-work T013
```

Sets `Status: Complete`, moves the row in `artifact-map.md` to `## Completed`, optionally archives.

---

## Anatomy of a ticket

Every ticket directory has the same files. Each file has one job.

For ticket `T013`:

| File | Purpose | Filled by |
|------|---------|-----------|
| `T013-summary.md` | One-page status: title, stage, owner, current state | Every agent updates Current State |
| `T013-analysis.md` | Findings + recommended path | analyst |
| `T013-requirements.md` | Functional, non-functional, acceptance criteria, out-of-scope | analyst |
| `T013-decision-log.md` | Each significant decision: slug, decision, rationale, impact | analyst, planner |
| `T013-questions.md` | Open questions with status (open / resolved / deferred) | analyst |
| `T013-plan.md` | Approach, slices, tasks, effort, risks, AC coverage | planner |
| `T013-progress.md` | Status summary + dated log of every action | every agent |
| `T013-verification.md` | AC table with PASS/FAIL/PENDING + evidence | verifier |

Cross-references use Obsidian wikilinks with the prefixed filename: `[[T013-summary]]`, `[[T013-plan]]`. Every artifact carries a `## Links` block listing every sibling, so each ticket appears as a fully-connected cluster in Obsidian's graph.

---

## Worked example: end-to-end

You want a dark-mode toggle in `my-app`. Here's the full trail.

**1. You:**
> Kickoff a ticket for a dark-mode toggle in my-app, with persistence across sessions.

**Harness routes to kickoff:** creates `T013/`, adds artifact-map row, hands to analyst.

**2. analyst writes `T013/T013-analysis.md`:**
> Current state: app uses hardcoded `ThemeData.light()` at `../my-app/lib/main.dart:42`. No theme service exists. Material 3 supports dark scheme via `ColorScheme.fromSeed(brightness:)`. Recommended path: introduce `ThemeService extends ChangeNotifier`, wire via Provider, persist with SharedPreferences.

**3. analyst writes `T013/T013-requirements.md`:**
- FR1: User can toggle theme from Settings.
- FR2: Theme persists across app restarts.
- FR3: System theme option follows OS.
- AC: 5 criteria covering toggle, persistence, system mode, accessibility contrast, animation.

No open questions → frozen.

**4. planner writes `T013/T013-plan.md`:**
- Slice 1 — Theme service + persistence (3 tasks, 4 h)
- Slice 2 — Settings UI + animation (3 tasks, 5 h)
- Total: 9 h, 5/5 AC covered, 0 high×high risks.

**5. builder works through tasks:**

```
T013-01 [x] Add ThemeMode enum + ThemeService                  (2026-05-06)
T013-02 [x] Persist ThemeMode to SharedPreferences             (2026-05-06)
T013-03 [x] Wire ThemeService into MaterialApp.themeMode       (2026-05-06)
T013-04 [x] Add toggle widget to Settings screen               (2026-05-07)
T013-05 [x] Add system-theme option                            (2026-05-07)
T013-06 [x] AnimatedTheme transition + golden test             (2026-05-07)
```

`T013-progress.md` accumulates one entry per task, with files touched and analyzer/test status.

**6. verifier writes `T013/T013-verification.md`:**

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Toggle visible in Settings | PASS | `lib/features/settings/settings_screen.dart:88` |
| 2 | Persists across restart | PASS | `theme_service_test.dart:42` test |
| 3 | System theme option works | PASS | `theme_service_test.dart:71` |
| 4 | Contrast ratios pass WCAG AA | PASS | manual audit, screenshots in progress.md |
| 5 | Smooth animation on toggle | PASS | `theme_animation_test.dart:18` golden |

387/387 tests pass. No blockers.

**7. close-work:**
- `T013-summary.md` → Status: Complete.
- Row moved to `## Completed` in artifact-map.

Months later, you grep `artifact-map.md` for "dark-mode" and have the entire reasoning trail in seven files.

---

## Common operations

### Start each session
- **Claude Code:** `SessionStart` runs `.claude/hooks/session-context.sh` and injects active and blocked ticket rows from `knowledge-center/artifact-map.md`.
- **Cursor:** `sessionStart` runs `.cursor/hooks/session_context.py` (see `.cursor/hooks.json`) for the same artifact-map excerpt as `additional_context` (requires `python` on your PATH).

In both cases the goal is the same: the agent sees what’s in flight without you re-pasting the map.

### Multi-project work
The artifact-map can hold tickets for several projects. Suggested ID prefix per project:

```
- [[NA-T001-summary]] — Noble App — login fix
- [[BE-T012-summary]] — Backend — migration
- [[ML-T003-summary]] — ML pipeline — eval harness
```

### Long-form reference docs
Stable knowledge (architecture, ADRs, runbooks) goes in `knowledge-center/wiki/`, not under `artifacts/`. Tickets link to wiki pages; wiki pages don't have a stage.

### Amending a frozen artifact
Don't silently rewrite. Use:

```
/evolve T013 target=requirements reason="user added a new persistence requirement"
```

`evolve` snapshots the change in `decision-log.md` under `## Amendment {DATE}`, applies the edit, then runs `reconcile` to flag downstream artifacts that need re-validation.

### Cross-ticket digest
```
/standup
```
Active / blocked / at-risk / closed-this-period across the whole map. Useful at the start of a week.

### Tracking questions, bugs, and todos
Three lightweight, parallel skills — none block a stage unless a question/bug is explicitly `critical`/blocking:
- `/questions T013` — open-question lifecycle (`open → answered → resolved → closed`) in `T013-questions.md`.
- `/bugs T013` — QA failures, regressions, UAT defects in `T013-open-bugs.md`.
- `/todos T013` — misc tasks, chores, follow-ups in `T013-open-todos.md` (or a shared file when not tied to a ticket).

### Terse output
```
/caveman lite|full|ultra
```
Drops filler and hedging from chat responses (not from code, commits, or artifacts) while keeping paths, ids, and errors exact. `/do` defaults to `lite`. `stop caveman` returns to normal voice.

### Free-form autonomous work
```
/do "add a retry to the sync job in my-app"
```
Skips manual stage-picking: classifies the request, matches skill(s)/agent(s), executes an iterate-until-done loop, and logs work on completion — still bound by the same 6 gates and ACT/ASK boundary as the rest of the harness.

### Housekeeping skills
- `/template` — list or apply a vault/Cursor template (the TEMPLATE gate's backing skill).
- `/consolidate` — migrate a scattered multi-folder ticket to the flat `{TICKET}-{artifact}.md` convention.
- `/log-work` / `/work-summary` — append to and read back per-author daily activity logs under `knowledge-center/logs/`.
- `/optimize-cursor-artifacts` — trims verbose agents/skills/rules for token use without changing intent.
- `project-layout` — the canonical reference for workspace/git conventions and multi-project routing (loaded by agents, not usually invoked directly).

### Resuming a stale ticket
```
trace-context T013
```
Loads every artifact for the ticket and surfaces the current stage, unchecked plan tasks, latest progress entry, and any open blockers — so the next agent works from current state, not stale memory.

---

## Conventions

**Ticket IDs.** `T###` for general tickets; `BUG-###`, `FEATURE-NAME`, `EPIC-NAME`, `PROJ-XXX` for typed work. For multi-project workspaces, prefix: `NA-T001`, `BE-T012`.

**Hierarchy.** Multi-layer work nests as `TICKET / SLICE / PHASE / TASK`. Most tickets stay flat (no nesting). Use slices when one ticket spans entities → DB → API → UI.

**Tags.** In `summary.md` frontmatter: `[active]`, `[blocked]`, `[completed]`, `[urgent]`, `[waiting]`. The hook reads tags to surface what's blocked.

**Filenames.** Every artifact in a ticket is `{TICKET}-{artifact}.md` — globally unique across the vault.

**Wikilinks.** Always `[[{TICKET}-{artifact}]]` style — e.g. `[[T013-plan]]`, never `[[plan]]` or `[[T013/plan]]`. Obsidian resolves them; agents (Claude Code or Cursor) read them.

**Cross-linking.** Every artifact ends with a `## Links` block listing every sibling in the ticket. This is mandatory — it's what makes each ticket appear as a connected cluster in Obsidian's graph view.

**Memory vs artifacts.** User-specific facts (preferences, role, feedback) go in `.claude/projects/control-center/memory/`. Project facts (decisions, requirements) go in artifacts. Memory survives across all sessions; artifacts belong to one ticket.

**Never silently rewrite.** Frozen requirements/plans change only through `evolve`, which logs the delta. The decision-log entry is mandatory.

---

## Where to read more

- `CLAUDE.md` — what Claude Code reads at session start.
- `CURSOR.md` — same workspace harness for Cursor (shared `.claude/` paths; Cursor-only hooks/rules).
- `AGENTS.md` — brief Cursor entry point.
- `.cursor/rules/control-center-harness.mdc` — always-on Cursor rules for this repo.
- `.claude/agents/*.md` — agent definitions (view, skills, protocol, output contract); used by both Claude Code and Cursor.
- `.claude/skills/*/SKILL.md` — skill definitions (inputs, steps, output, rules); single canonical copy for both tools.
- `knowledge-center/artifacts/_template/` — the seven files every new ticket starts with.
- `knowledge-center/artifact-map.md` — the live index of all tickets.
