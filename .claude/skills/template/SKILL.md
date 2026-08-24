---
name: template
description: List and apply ticket-artifact and harness templates (Harness Stage 3 — template gate)
---

# /template

**When:** `/template` | `/template list` (show locations) | `/template use <name>` (path + placeholders for one template). Any new file type must derive from a template — stop if none exists.

## Steps

1. **CANONICAL** — use the on-disk template: `knowledge-center/artifacts/_template/*.md` for ticket artifacts; fall back to a skill-owned `.claude/skills/<id>/template.md`. Never invent template bodies in chat. Registry: `.claude/skills/template/template-manifest.json`.
2. **Render** — single file via `.claude/skills/template/scripts/New-FromTemplate.ps1`; full new-ticket scaffold via `kickoff` (copies every `_template/*.md` in one pass).
3. Ticket-scoped markdown: set frontmatter (`tags`, `status`, `ticket`) and link `{TICKET}` per the filename/linking convention (`consolidate`).
4. Replace every placeholder occurrence — never leave one raw in a saved file:

| Placeholder | Value |
|---|---|
| `{ID}` / `{T}` | ticket id |
| `{DATE}` / `{YYYY-MM-DD}` | today |
| `{TITLE}` / `{Title}` | ticket title |

## Locations

| Area | Path |
|---|---|
| Ticket artifact templates | `knowledge-center/artifacts/_template/*.md` — `summary`, `analysis`, `requirements`, `decision-log`, `questions`, `plan`, `progress`, `verification` |
| Skill-owned workflow templates | `.claude/skills/<id>/template.md` |
| Render script | `.claude/skills/template/scripts/New-FromTemplate.ps1` |
| Registry | `.claude/skills/template/template-manifest.json` |
| Full ticket scaffold | `kickoff` skill |

## Output

Chat: markdown table of template paths + one-line purpose; for `use <name>`, print the template path and key placeholders. Files created from templates follow `{TICKET}-{name}.md` naming per `consolidate`. End with:

```text
── Harness stages ──
CLARIFY: (any questions before scaffolding?)
CANONICAL: template path chosen from table above
TEMPLATE: copied structure from disk, not retyped from memory
SIMPLIFY: single template per artifact type
TRACE: output paths for created files + links to `{TICKET}` hub if applicable
```

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
