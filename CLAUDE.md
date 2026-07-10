# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this workspace.

## Workspace Overview

**control-center-workspace** is a project-independent agentic harness for structured software development. It pairs Claude Code's agent pipeline with an Obsidian knowledge vault and a structured ticket lifecycle. It is a reusable template — nothing in it is coupled to any specific company, product, or tech stack.

Add sub-projects as VS Code workspace folders. Each project gets its own ticket IDs and artifact subtree under `knowledge-center/artifacts/`.

**Always-on core (Claude Code auto-imports):** @.claude/skills/harness-standards/core.md — the 6 gates, BE HONEST, default voice. Full norms (evidence, communication, scope, token discipline, test policy, orchestration): `.claude/skills/harness-standards/SKILL.md`.

## Workspace Layout

| Path | Purpose |
|------|---------|
| `knowledge-center/` | Obsidian vault — all artifacts, wiki, and the artifact map |
| `knowledge-center/artifacts/{TICKET}/` | Per-ticket work artifacts |
| `knowledge-center/artifacts/_template/` | Source templates `kickoff` scaffolds from |
| `knowledge-center/wiki/` | Durable reference docs and ADRs |
| `knowledge-center/logs/{YYYY-MM}/` | Per-author daily activity logs — `log-work` / `work-summary` |
| `.claude/agents/` | Agent definitions (harness, analyst, planner, builder, verifier, fixer) |
| `.claude/skills/<name>/SKILL.md` | Skill definitions invoked by agents and `/do` |
| `.claude/projects/control-center/memory/` | Persistent memory across sessions |
| `.cursor/` | Cursor Agent: `CURSOR.md`, `AGENTS.md`, `.cursor/rules/`, `.cursor/hooks.json` — see `CURSOR.md` (agents/skills stay under `.claude/`) |

## Agentic Pipeline

Pipeline stages: **GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY**

| Agent | Stages | Role |
|-------|--------|------|
| `harness` | All | Orchestrator — routes to specialists, runs `/do` dispatch |
| `analyst` | GROUND, CLARIFY | Context analysis, pre-freeze requirements pipeline |
| `planner` | CANONICAL | Components, tasks, effort, risk → plan.md |
| `builder` | TEMPLATE, SIMPLIFY | Implements plan tasks one at a time |
| `verifier` | VERIFY | Validates against acceptance criteria |
| `fixer` | Any | Root-cause diagnosis and minimal patch |

Exactly 6 agents — no additions without explicit user intent.

### Free-form entry point

`/do {request}` — autonomous dispatch: classifies a free-form request into a lane (deliver / skill / role / investigate / cross-repo), matches skill(s)/agent(s) from the live catalog, drives an iterate-until-done loop, and logs work on completion. See `.claude/skills/do/SKILL.md`. Pair with `/caveman` for terse output on long sessions.

### Skills (`.claude/skills/<name>/SKILL.md`)

- **Setup/state:** `kickoff`, `trace-context`, `template`, `consolidate`
- **Pre-freeze requirements:** `draft-requirements` → `analyze-context` → `identify-gaps` (also covers existing-feature overlap/conflict/reuse) → `enrich-requirements` → `iterate-requirements` → `challenge-requirements` → `freeze-requirements` → `extract-stories`
- **Decisions:** `tech-select` — pick a language/framework/library/package/pattern/architecture/API/UI/DB/etc.; researches the web, gates on user approval, records to `decision-log.md`
- **Planning:** `plan` (umbrella), `plan-effort` (flat case), `analyze-components` (includes dependency graph), `breakdown-tasks`, `create-implementation-plan`, `estimate-development`, `generate-effort-forecast`, `replan`, `risk-scan`, `challenge-plan`
- **Build/fix:** `progress-tracker`, `fix`, `evolve`
- **Verification:** `verify`, `challenge-implementation`, `criticize` (router), `validate-artifacts`, `check-artifact-links` (includes requirements traceability), `trace`, `generate-test-cases`
- **Tracking (lightweight, audit-trail):** `questions`, `bugs`, `todos`, `clarify`
- **Stage gates:** `handoff`, `reconcile`
- **Workspace/ops:** `standup`, `close-work`, `log-work`, `work-summary`, `optimize-cursor-artifacts`, `project-layout`

### Rules

- For multi-step work, delegate to `harness`. It routes to specialists which invoke skills. For a free-form/unscoped request, use `/do` instead.
- One artifact directory per ticket: `knowledge-center/artifacts/{TICKET}/`
- Use `kickoff` (not manual copy) to seed a new ticket from `_template/`. It also adds the artifact-map row.
- Cross-file refs use Obsidian `[[wikilinks]]`.
- Every agent starts every turn with `trace-context`.
- Every stage transition goes through `handoff`.
- Any artifact change post-freeze goes through `evolve` (never silent rewrite).
- Memory lives at `.claude/projects/control-center/memory/`.

### Filename and linking convention

- Every artifact file inside a ticket directory MUST be named `{TICKET}-{artifact}.md`. Example for ticket `T013`: `T013-summary.md`, `T013-analysis.md`, `T013-requirements.md`, `T013-decision-log.md`, `T013-questions.md`, `T013-plan.md`, `T013-progress.md`, `T013-verification.md`.
- This makes filenames globally unique across the vault, so Obsidian wikilinks like `[[T013-summary]]` resolve unambiguously from anywhere.
- Every artifact ends with a `## Links` block listing every sibling artifact in the ticket. This forms a fully-connected cluster in Obsidian's graph view.
- Skills that reference artifact files conceptually (e.g., "write to analysis.md") implicitly mean `{TICKET}-analysis.md` inside the ticket directory.
- Artifact-map rows use `[[{TICKET}-summary]]`, not `[[{TICKET}/summary]]`.
- Full detail (structure rules, anti-patterns, migration for scattered tickets): `.claude/skills/consolidate/SKILL.md`.

## Rule reference

| Topic | Canonical path |
|-------|----------------|
| Harness gates, comms, evidence, token/test policy | `.claude/skills/harness-standards/SKILL.md` |
| Free-form autonomous dispatch | `.claude/skills/do/SKILL.md` |
| Terse output mode | `.claude/skills/caveman/SKILL.md` |
| Artifact layout, naming, wikilinks | `.claude/skills/consolidate/SKILL.md` |
| Workspace/git conventions, multi-project routing | `.claude/skills/project-layout/SKILL.md` |
| Adversarial critique (requirements/plan/implementation) | `.claude/skills/challenge-standards/rules.md` |
| Open question lifecycle | `.claude/skills/clarify/question-templates.md` |
| Test-case design (pre-verify) | `.claude/skills/generate-test-cases/SKILL.md` |
| Templates registry | `.claude/skills/template/template-manifest.json` |
| Activity log (append) | `.claude/skills/log-work/SKILL.md` |
| Timesheet (read-only recap) | `.claude/skills/work-summary/SKILL.md` |
| Config/skill token-reduction | `.claude/skills/optimize-cursor-artifacts/SKILL.md` |