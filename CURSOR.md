# CURSOR.md

This file provides guidance to **Cursor Agent** when working in this workspace. It mirrors `CLAUDE.md` so you can switch between Claude Code and Cursor without changing ticket layout, vault conventions, or skill content.

## Workspace overview

**control-center-workspace** is a project-independent agentic harness for structured software development. It pairs an agent pipeline with an Obsidian knowledge vault and a structured ticket lifecycle. It is a reusable template — nothing in it is coupled to any specific company, product, or tech stack.

Add sub-projects as VS Code workspace folders. Each project gets its own ticket IDs and artifact subtree under `knowledge-center/artifacts/`.

**Always-on core:** `.claude/skills/harness-standards/core.md` — the 6 gates, BE HONEST, default voice. Full norms: `.claude/skills/harness-standards/SKILL.md`.

## Workspace layout

| Path | Purpose |
|------|---------|
| `knowledge-center/` | Obsidian vault — all artifacts, wiki, and the artifact map |
| `knowledge-center/artifacts/{TICKET}/` | Per-ticket work artifacts |
| `knowledge-center/artifacts/_template/` | Source templates `kickoff` scaffolds from |
| `knowledge-center/wiki/` | Durable reference docs and ADRs |
| `.claude/skills/` | **Canonical** skill definitions (`SKILL.md` per skill) — use these paths when a skill applies |
| `.claude/agents/` | Agent definitions (harness, analyst, planner, builder, verifier, fixer) — same files Cursor uses |
| `.cursor/rules/` | Cursor rules (always-on harness behavior) |
| `.cursor/hooks.json` + `.cursor/hooks/` | Session and other Cursor hooks |
| `.claude/projects/control-center/memory/` | Persistent memory across sessions (**shared**; do not fork a second memory store under `.cursor/`) |

## Agentic pipeline

Pipeline stages: **GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY**

| Agent | Stages | Role |
|-------|--------|------|
| `harness` | All | Orchestrator — routes to specialists, runs `/do` dispatch |
| `analyst` | GROUND, CLARIFY | Context analysis, pre-freeze requirements pipeline |
| `planner` | CANONICAL | Components, tasks, effort, risk → plan.md |
| `builder` | TEMPLATE, SIMPLIFY | Implements plan tasks one at a time |
| `verifier` | VERIFY | Validates against acceptance criteria |
| `fixer` | Any | Root-cause diagnosis and minimal patch |

Exactly 6 agents — no additions without explicit user intent. Free-form requests: `/do {request}` (`.claude/skills/do/SKILL.md`) classifies into a lane and dispatches; pair with `/caveman` for terse output.

Skills (read from **`.claude/skills/<name>/SKILL.md`** — single source of truth):

- **Setup/state:** `kickoff`, `trace-context`, `template`, `consolidate`
- **Pre-freeze requirements:** `draft-requirements` → `analyze-context` → `identify-gaps` → `enrich-requirements` → `iterate-requirements` → `challenge-requirements` → `freeze-requirements` → `extract-stories`
- **Planning:** `plan`, `plan-effort`, `analyze-components` (includes dependency graph), `breakdown-tasks`, `create-implementation-plan`, `estimate-development`, `generate-effort-forecast`, `replan`, `risk-scan`, `challenge-plan`
- **Build/fix:** `progress-tracker`, `fix`, `evolve`
- **Verification:** `verify`, `challenge-implementation`, `criticize`, `validate-artifacts`, `check-artifact-links` (includes requirements traceability), `trace`, `generate-test-cases`
- **Tracking:** `questions`, `bugs`, `todos`, `clarify`
- **Stage gates:** `handoff`, `reconcile`
- **Workspace/ops:** `standup`, `close-work`, `log-work`, `work-summary`, `optimize-cursor-artifacts`, `project-layout`

### Rules

- For multi-step work, follow the harness routing in `.claude/agents/harness.md`. In Cursor, use the **Task** tool where that file refers to delegating to another agent (Claude Code uses the Agent tool for the same step).
- One artifact directory per ticket: `knowledge-center/artifacts/{TICKET}/`
- Use `kickoff` (not manual copy) to seed a new ticket from `_template/`. It also adds the artifact-map row.
- Cross-file refs use Obsidian `[[wikilinks]]`.
- Every agent starts every turn with `trace-context` (read the skill file under `.claude/skills/trace-context/`).
- Every stage transition goes through `handoff`.
- Any artifact change post-freeze goes through `evolve` (never silent rewrite).
- Memory lives at `.claude/projects/control-center/memory/`.

### Filename and linking convention

- Every artifact file inside a ticket directory MUST be named `{TICKET}-{artifact}.md`. Example for ticket `T013`: `T013-summary.md`, `T013-analysis.md`, `T013-requirements.md`, `T013-decision-log.md`, `T013-questions.md`, `T013-plan.md`, `T013-progress.md`, `T013-verification.md`.
- This makes filenames globally unique across the vault, so Obsidian wikilinks like `[[T013-summary]]` resolve unambiguously from anywhere.
- Every artifact ends with a `## Links` block listing every sibling artifact in the ticket. This forms a fully-connected cluster in Obsidian's graph view.
- Skills that reference artifact files conceptually (e.g., "write to analysis.md") implicitly mean `{TICKET}-analysis.md` inside the ticket directory.
- Artifact-map rows use `[[{TICKET}-summary]]`, not `[[{TICKET}/summary]]`.

## Cursor-only notes

- **Hooks:** `sessionStart` runs `.cursor/hooks/session_context.py` to inject Active/Blocked lines from `knowledge-center/artifact-map.md` (requires Python 3 on `PATH` as `python`).
- **Skills and agents are not duplicated under `.cursor/`** — use `.claude/skills/` and `.claude/agents/` only.
