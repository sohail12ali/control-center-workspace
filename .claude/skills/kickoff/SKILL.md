---
name: kickoff
description: Seed a new ticket. Creates artifacts/{ID}/ from _template, renames each file to {ID}-{name}.md, fills frontmatter (id, date, owner), and adds a row to artifact-map.md under Active. Use at the start of any new work item, before any analysis or planning.
---

# Inputs
- `id` (required): ticket id (e.g. `T013`, `FEATURE-AUTH`)
- `title` (required): short title
- `owner` (optional): defaults to git user
- `slice`, `phase` (optional): for nested hierarchy

# Steps
1. Resolve target dir: `knowledge-center/artifacts/{id}[/{slice}[/{phase}]]/`. Refuse if it exists.
2. For every file `{name}.md` in `knowledge-center/artifacts/_template/`, copy it to the target as `{id}-{name}.md`. Example: `summary.md` → `T013-summary.md`.
3. In every copied file, replace `{ID}` with the ticket id and `{DATE}` with today (YYYY-MM-DD).
4. In `{id}-summary.md`: also replace `{Title}` and set Owner.
5. Append to `knowledge-center/artifact-map.md` under `## Active`:
   `- [[{id}-summary]] — {title} — Open — {owner}`

# Output
Path of created `{id}-summary.md`. Caller decides next stage (usually `analyze`).

# Filename convention
Every artifact file inside a ticket directory MUST be named `{ID}-{artifact}.md`. This makes filenames globally unique across the vault, so Obsidian wikilinks like `[[T013-summary]]` resolve unambiguously from anywhere — wiki pages, the artifact-map, sibling tickets, or other artifacts.

Standard files seeded:
- `{id}-summary.md`
- `{id}-analysis.md`
- `{id}-requirements.md`
- `{id}-decision-log.md`
- `{id}-questions.md`
- `{id}-plan.md`
- `{id}-progress.md`
- `{id}-verification.md`

# Linking convention
Every artifact ends with a `## Links` block listing every sibling artifact in the ticket. This forms a fully-connected cluster in Obsidian's graph view — each ticket renders as a tight node group. The template already includes this block; do not strip or shorten it.

# Rules
- Never overwrite an existing artifact directory.
- Don't create code yet; this is artifact scaffolding only.
- Always rename files on copy — `_template/summary.md` becomes `{id}-summary.md`, not `summary.md` inside the new directory.
