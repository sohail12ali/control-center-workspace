---
name: optimize-cursor-artifacts
description: Compresses and tightens Claude/Cursor agents, subagents, commands, rules (.mdc), skills, vault artifacts, and helper scripts for lower token use without changing intent or load-bearing structure. Use when refactoring .claude/ or .cursor/ config, trimming verbose skills/rules, deduplicating examples, or when the user asks to optimize, shorten, or token-reduce prompt-facing files.
---

# /optimize-cursor-artifacts

**When:** Refactoring `.claude/` or `.cursor/` config, trimming verbose skills/rules/agents/scripts, or any "optimize/shorten/token-reduce" ask on prompt-facing files (typical targets: `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, `.cursor/rules/*.mdc`).

**Goals, in order:** fewer tokens → drop noise → same meaning (behavior, constraints, authority order, outputs unchanged) → structure preserved (frontmatter, headings, checklists, layout — no flattening unless the user wants a merge).

## Steps

1. **Classify** the artifact (skill, rule, agent, command, script, vault note) and check the blocks below.
2. **Extract intent** — list non-negotiables: required outputs, forbidden actions, tool/order constraints, globs, `alwaysApply`, command args.
3. **Compress, two passes** — pass A delete duplication, stale examples, dead sections; pass B tighten wording. Tactics:
   - Imperatives over narrative; delete throat-clearing and repeated summaries.
   - Merge duplicates — one canonical copy (rules for repo law, skills for procedure); link elsewhere.
   - One example per pattern; extras → `reference.md`/`examples.md` (progressive disclosure — keep SKILL.md lean).
   - Tables → bullets when sparse; keep tables where alignment encodes meaning.
   - Scripts: keep non-obvious invariants, safety warnings, env vars; cut comments restating code.
   - Treat numbered rules, harness gates, and "read X before Y" lines as structure — shorten prose under anchors, never the sequence/gate list; keep stable section titles.
4. **Regression check** — would a subagent still know when to load this, what to do, and what to return? If not, restore the minimum clarifying line.
5. **Quality bar:** non-negotiables still loadable in one hop · frontmatter/schema/JSON valid · no orphaned links · purpose obvious in ~30s of skimming.

## Preserve/trim by type

| Type | Preserve | Trim |
|------|----------|------|
| Skill | YAML `name`/`description`, when-to-use, critical workflows | Duplicate anti-patterns, identical templates |
| Rule (.mdc) | Frontmatter, globs, authority tiers, must-not lists | Tutorial prose duplicated in skills |
| Agent/subagent | Role, boundaries, output shape, tool policy | Persona fluff, repeated system reminders |
| Command | Args, defaults, safety gates | Prose covered by linked rules/skills |
| Vault/ticket artifact | AC, repro, identifiers, decisions | Superseded exploratory notes (only with user OK) |
| Script | Usage header, destructive guards, idempotency notes | Comments repeating README |

## Blocks

- **Sensitive paths — never send to third-party compression APIs** (local-only edits; warn user): basenames `.env`, `credentials`, `secrets`, `appsettings.Production.json`, `*.pfx`, `*.pem`; globs `**/release-packages/**`, `**/.cursor/mcp.json`; content markers `Password=`, `Server=`, `X-API-Key`, `apikey`.
- **Don't optimize:** legal/compliance/security text (verbatim); skill `description` YAML (keep third person, WHAT+WHEN, trigger terms — trim body first unless user agrees to retune); generated/vendor-synced files without explicit approval; tests into obscurity (names and Arrange data stay explicit).
- **Don't introduce:** Windows-style paths in examples; option sprawl (one default procedure); time-sensitive rules (use current/deprecated); inconsistent terminology; vague descriptions; flattened harness gates, handoff limits, `alwaysApply`/globs.

## Output

Edits target files in place (small diffs; if intent might shift, add a one-line "Non-goals" instead of caveats). No new report files. Related: `create-skill` (authoring/progressive-disclosure patterns), `CLAUDE.md` (where standards vs skills belong).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
