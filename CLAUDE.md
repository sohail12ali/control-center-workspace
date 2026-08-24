# CLAUDE.md

Guidance for Claude Code in this workspace. This file states only three things: the **layout** artifacts must land in, the **order** work must run in, and how everything stays **in sync with the Delivery Console**. Detail lives in the referenced skills — one fact, one file.

## Workspace Overview

**control-center-workspace** is a project-independent agentic harness for structured software development: Claude Code agent pipeline + Obsidian knowledge vault + a structured ticket lifecycle + the Delivery Console. Reusable template — nothing here is coupled to a company, product, or stack. Sub-projects join as VS Code workspace folders; each gets its own ticket IDs and artifact subtree.

**Always-on core (auto-imported):** @.claude/skills/harness-standards/core.md — the 6 gates, BE HONEST, default voice. Full norms: `.claude/skills/harness-standards/SKILL.md`.

## Layout

| Path | Purpose |
|------|---------|
| `knowledge-center/` | Obsidian vault — artifacts, wiki, artifact map |
| `knowledge-center/artifacts/{TICKET}/` | Per-ticket artifacts (`_template/` is the source; `_shared/` holds unscoped trackers) |
| `knowledge-center/investigations/` | Pre-ticket dossiers (`investigate`) |
| `knowledge-center/wiki/` · `logs/{YYYY-MM}/` | Durable docs/ADRs · per-author daily logs (`log-work`) |
| `console/` | Delivery Console — boards + tabs + CLI (`console` skill); editor-agnostic |
| `.claude/agents/` · `.claude/skills/` | 7 agents · 39 skills |
| `.claude/projects/control-center/memory/` | Persistent memory |
| `.cursor/` | Cursor Agent mirror — see `CURSOR.md` |

**Filename convention (canonical: `consolidate`):** every artifact is `{TICKET}-{artifact}.md`, flat in the ticket dir, ending with a `## Links` block listing all siblings. Exceptions: `ticket.toml` + `{TICKET}-{questions,bugs,todos}.toml` are **CLI-mutated only** via `console/kanban.py` — never hand-edited; optional `ticket-scripts/`. Artifact-map rows use `[[{TICKET}-summary]]`.

## Order — the pipeline

Stages: **GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY** (gates in core.md).

| Agent | Stages | Skill order it runs |
|-------|--------|---------------------|
| `harness` | all | orchestrates: `trace-context` → `handoff` per transition → delegate → `reconcile`/`close-work` |
| `analyst` | GROUND, CLARIFY | `analyze` → `requirements draft` → `challenge-requirements` → `requirements enrich` → `clarify`/`questions` → `requirements iterate`× → `requirements freeze` |
| `planner` | CANONICAL | `requirements stories` → `plan` (flat) or `analyze-components` → `breakdown-tasks` (+`estimate`) → `challenge-plan` |
| `builder` | TEMPLATE, SIMPLIFY | task-by-task from plan; `tech-select(confirm-existing)` before new deps; `progress-tracker` per task; `simplify` |
| `verifier` | VERIFY | `challenge-implementation` → `verify cases` → `verify {scope}` → `validate-artifacts` (+links) → `reconcile` → `close-work` |
| `fixer` | any | `fix` → `progress-tracker`; `evolve` on design shifts |
| `deployer` | after close-work | ASK-gated: `invoke-project-skill` → sub-project publish → `log-work` |

Exactly **7 agents** — no additions without explicit user intent. Free-form entry point: **`/do {request}`** (lanes, ACT/ASK boundary: `do` skill). Terse mode: `/caveman`.

## Skills

39 skills; the live catalog (`.claude/skills/*/SKILL.md` frontmatter) is the source of truth — each description carries its triggers, ops/modes, and chain position. Never invent ids; the pipeline order lives in the agent protocols above.

## Console sync

- Ticket + tracker state lives in TOML under the ticket dir, mutated **only** via `console/kanban.py` (directly or through `kickoff`/`questions`/`bugs`/`todos`/`close-work`).
- Stage → lane: `kickoff` → `open` · first build task → `in-progress` · blocker → `blocked` · verification → `verify` · `close-work` → `done` (via `ticket move`; mapping canonical in the `console` skill).
- The Work tab reads `log-work`'s daily files; the Agents tab launches backends from `console/config/agents.toml`; session hooks run `refresh --quiet`.

## Rules

- Multi-step work → delegate to `harness`; free-form/unscoped → `/do`.
- New ticket → `kickoff` (never manual copy); every agent turn starts with `trace-context`; every stage transition goes through `handoff`; post-freeze changes go through `evolve` (never silent rewrite).
- Cross-file refs are Obsidian `[[wikilinks]]`. Memory: `.claude/projects/control-center/memory/`.

## Rule reference

| Topic | Canonical path |
|-------|----------------|
| Gates, comms, evidence, token/test policy | `.claude/skills/harness-standards/SKILL.md` (+ `core.md`) |
| Autonomous dispatch / terse output | `.claude/skills/do/SKILL.md` · `.claude/skills/caveman/SKILL.md` |
| Artifact layout, naming, wikilinks | `.claude/skills/consolidate/SKILL.md` |
| Delivery Console (boards, CLI, TOML) | `.claude/skills/console/SKILL.md` · `console/README.md` |
| Workspace/git, multi-project routing | `.claude/skills/project-layout/SKILL.md` |
| Adversarial critique | `.claude/skills/challenge-standards/rules.md` |
| Open question lifecycle | `.claude/skills/clarify/question-templates.md` |
| Test-case design | `.claude/skills/verify/SKILL.md` (scope cases) |
| Templates registry | `.claude/skills/template/template-manifest.json` |
| Daily activity log / timesheet | `.claude/skills/log-work/SKILL.md` |
