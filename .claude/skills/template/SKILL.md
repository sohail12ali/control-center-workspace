---
name: template
description: List and apply ticket-artifact and harness templates (Harness Stage 3 — template gate)
---

# /template

## Usage

```
/template
/template list
/template use <name>
```

- **`/template`** or **`list`** — Show available template locations and how to pick one.
- **`use <name>`** — Open/copy guidance for a specific template (by short name below).

## Canonical locations (SSOT)

Ticket artifact shapes live under `knowledge-center/artifacts/_template/` — one file per artifact type, copied and renamed to `{TICKET}-{name}.md` by `kickoff`. Render single files with `.claude/skills/template/scripts/New-FromTemplate.ps1`. Registry: `.claude/skills/template/template-manifest.json`.

| Area | Path | Notes |
|------|------|-------|
| Ticket artifact templates | `knowledge-center/artifacts/_template/*.md` | `summary`, `analysis`, `requirements`, `decision-log`, `questions`, `plan`, `progress`, `verification` |
| Skill-owned workflow templates | `.claude/skills/<id>/template.md` | Skills that need a bespoke file shape (e.g. `log-work`) keep their own template next to the skill |
| Render script | `.claude/skills/template/scripts/New-FromTemplate.ps1` | Placeholder substitution for a single file |
| Full ticket scaffold | `kickoff` skill | Copies every `_template/*.md` into a new ticket directory in one pass — see `.claude/skills/kickoff/SKILL.md` |

## Behavior

1. **CANONICAL** — Prefer the ticket-artifact template on disk (`knowledge-center/artifacts/_template/*.md`); fall back to a skill-owned `template.md` for skills that define their own artifact shape. Do not invent template bodies in chat.
2. **Render** — Use `.claude/skills/template/scripts/New-FromTemplate.ps1` for single files; use the `kickoff` skill for a full new-ticket tree.
3. When creating **ticket-scoped** markdown, set frontmatter (`tags`, `status`, `ticket`) and link `{TICKET}` per the filename and linking convention in `CLAUDE.md`.
4. Placeholders: `{ID}` / `{T}` (ticket id), `{DATE}` / `{YYYY-MM-DD}` (today), `{TITLE}` / `{Title}` (ticket title). Replace all occurrences — never leave a raw placeholder in a saved file.
5. Output: markdown table of paths + one-line purpose; if `use` requested, print the template path and key placeholders to replace.

## Harness

End with:

```text
── Harness stages ──
CLARIFY: (any questions before scaffolding?)
CANONICAL: template path chosen from table above
TEMPLATE: copied structure from disk, not retyped from memory
SIMPLIFY: single template per artifact type
TRACE: output paths for created files + links to `{TICKET}` hub if applicable
```

## Related

| Command / doc | Purpose |
|----------------|---------|
| `kickoff` | Full ticket scaffold from `_template/` |
| `consolidate` | Canonical naming, wikilink, and structure rules for artifacts once created |
| `.claude/skills/template/template-manifest.json` | Registry of template paths and scripts |
