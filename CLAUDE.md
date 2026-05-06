# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working in this workspace.

## Workspace Overview

**control-center-workspace** is a project-independent agentic harness for structured software development. It pairs Claude Code's agent pipeline with an Obsidian knowledge vault and a structured ticket lifecycle.

Add sub-projects as VS Code workspace folders. Each project gets its own ticket IDs and artifact subtree under `knowledge-center/artifacts/`.

## Workspace Layout

| Path | Purpose |
|------|---------|
| `knowledge-center/` | Obsidian vault — all artifacts, wiki, and the artifact map |
| `knowledge-center/artifacts/{TICKET}/` | Per-ticket work artifacts |
| `knowledge-center/wiki/` | Durable reference docs and ADRs |
| `.claude/agents/` | Agent definitions (harness, analyst, planner, builder, verifier, fixer) |
| `.claude/skills/` | Skill scripts invoked by agents |
| `.claude/projects/control-center/memory/` | Persistent memory across sessions |
| `.cursor/` | Cursor Agent: `CURSOR.md`, `AGENTS.md`, `.cursor/rules/`, `.cursor/hooks.json` — see `CURSOR.md` (agents/skills stay under `.claude/`) |

## Agentic Pipeline

Pipeline stages: **GROUND → CLARIFY → CANONICAL → TEMPLATE → SIMPLIFY → VERIFY**

| Agent | Stages | Role |
|-------|--------|------|
| `harness` | All | Orchestrator — routes to specialists |
| `analyst` | GROUND, CLARIFY | Context analysis, requirements |
| `planner` | CANONICAL | Approach, slices, risks → plan.md |
| `builder` | TEMPLATE, SIMPLIFY | Implements plan tasks one at a time |
| `verifier` | VERIFY | Validates against acceptance criteria |
| `fixer` | Any | Root-cause diagnosis and minimal patch |

Skills (`.claude/skills/`):

- **Setup/state:** `kickoff`, `trace-context`
- **Analysis:** `analyze`, `manage-questions`, `clarify`
- **Spec:** `requirements`, `validate`
- **Decisions:** `tech-select` — pick a language/framework/library/package/pattern/architecture/API/UI/DB/etc.; researches the web, gates on user approval, records to `decision-log.md`
- **Planning:** `plan`, `risk-scan`, `plan-effort`
- **Build/fix:** `progress-tracker`, `fix`, `evolve`
- **Stage gates:** `handoff`, `reconcile`
- **Workspace:** `graph-sync`, `standup`, `close-work`

### Rules

- For multi-step work, delegate to `harness`. It routes to specialists which invoke skills.
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