---
name: kickoff
description: Seed a new ticket. Creates artifacts/{ID}/ from _template, renames each file to {ID}-{name}.md, fills frontmatter (id, date, owner), scaffolds ticket.toml + empty tracker .toml files via the console CLI, and adds a row to artifact-map.md under Active. Use at the start of any new work item, before any analysis or planning.
---

# /kickoff

**When:** Start of any new work item, before analysis or planning. Ticket-draft hands off here once id + scope are decided.

# Inputs
- `id` (required) · `title` (required) · `owner` (optional, defaults to git user)
- `kind` (optional, default `tickets`): console board kind (`tickets` | `investigations`; `migrations`/`releases` if a fork enabled them)
- `slice`, `phase` (optional): nested hierarchy

# Steps
1. Resolve target dir `knowledge-center/artifacts/{id}[/{slice}[/{phase}]]/`. Refuse if it exists.
2. Render every `{name}.md` in `knowledge-center/artifacts/_template/` to `{target}/{id}-{name}.md` via `template`'s `New-FromTemplate.ps1` (owns `{ID}`/`{DATE}`/`{TITLE}`/`{Title}` substitution — don't hand-roll it).
3. In `{id}-summary.md`: confirm placeholders resolved; set Owner.
4. Console sync: `python console/kanban.py ticket create {id} --title "{title}" --kind {kind} --owner {owner}` — writes `ticket.toml` (lane `open`) + empty `{id}-questions.toml`/`{id}-bugs.toml`/`{id}-todos.toml`. If `console/` is absent, skip and note it — don't fail kickoff.
5. Append to `knowledge-center/artifact-map.md` under `## Active`: `- [[{id}-summary]] — {title} — Open — {owner}`

# Output
Path of `{id}-summary.md`. Standard files seeded: `{id}-{summary,analysis,requirements,decision-log,plan,progress,verification}.md` + `ticket.toml` and tracker TOMLs (via `console`, not `_template/`). Caller decides next stage (usually `analyze`).

# Rules
- Never overwrite an existing artifact directory. Artifact scaffolding only — no code.
- Always rename on copy: `_template/summary.md` → `{id}-summary.md`, never bare `summary.md`.
- Filename + `## Links` block conventions are canonical in `consolidate/SKILL.md` — templates already include the Links block; don't strip it.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
