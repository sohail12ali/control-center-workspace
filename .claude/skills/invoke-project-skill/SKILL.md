---
name: invoke-project-skill
description: Resolve which sub-project owns a ticket's code and invoke that sub-project's own build/test/publish procedure. The single cross-repo delegation primitive used by builder, verifier, and deployer — already referenced by those agents/skills; this file is its canonical definition.
---

# /invoke-project-skill

**When:** Any build/test/publish command a ticket needs — the umbrella owns process, never product code (see `project-layout`), so execution is always delegated here. Called by `builder`, `verifier`, `deployer`, and `verify` (scope cases, framework-specific test scaffolding).

**Inputs:** `id` (required — ticket id, for sub-project hints); `skill_id` (optional — e.g. `build`, `publish`; otherwise resolved here).

## Steps

1. **Identify the sub-project** from the ticket's artifacts (`{T}-plan.md`, `{T}-task-breakdown.md`, touched file paths) and the user's message.
2. **Use the registry if one exists** — a sub-project registry note under `knowledge-center/wiki/` (see `project-layout`); otherwise infer from the workspace folder list. Ambiguous → ask, don't guess.
3. **Read that sub-project's own `CLAUDE.md` first** — authoritative for its repo's commands; never guess or reuse another sub-project's commands.
4. **Load `{sub-project}/.claude/skills/{skill_id}/SKILL.md` if present**; if absent, run the command its `CLAUDE.md` documents directly.
5. **Execute from that repo's root**, not from `control-center-workspace`.
6. **Report** skill id (or raw command), repo, and result — callers record it in their `Skills:` footer as `invoke-project-skill → {id}`.

## Output

No files. Chat report:

```
── invoke-project-skill ──
Sub-project: {repo}
Ran:         {skill_id | raw command}
Result:      {✅ success | ⛔ failed} — {one line}
```

## Rules

- Resolve-and-delegate only — no product-specific logic, tech stack, or repo table in this file.
- Terminal: delegates to the sub-project's own tooling, nothing else.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
