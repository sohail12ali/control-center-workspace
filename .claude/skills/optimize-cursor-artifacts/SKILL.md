---
name: optimize-cursor-artifacts
description: Compresses and tightens Claude/Cursor agents, subagents, commands, rules (.mdc), skills, vault artifacts, and helper scripts for lower token use without changing intent or load-bearing structure. Use when refactoring .claude/ or .cursor/ config, trimming verbose skills/rules, deduplicating examples, or when the user asks to optimize, shorten, or token-reduce prompt-facing files.
---

# Optimize Cursor artifacts

## Goals (in order)

1. **Fewer tokens** — shorter lines, fewer repeated ideas, smaller examples.
2. **Drop noise** — remove redundant comments, duplicate "why" prose, stacked examples that teach the same rule once.
3. **Same meaning** — behavior, constraints, authority order, and outputs unchanged for a competent reader.
4. **Structure preserved** — keep frontmatter, headings agents rely on, checklists, and file layout; do not flatten into an undifferentiated wall unless the user explicitly wants a merge.

## Sensitive paths (block external compress)

**Do not** send these paths to third-party compression APIs. **Block** and warn the user:

- Basenames: `.env`, `credentials`, `secrets`, `appsettings.Production.json`, `*.pfx`, `*.pem`
- Globs: `**/release-packages/**`, `**/.cursor/mcp.json`
- Content markers: connection strings (`Password=`, `Server=`), API keys (`X-API-Key`, `apikey`)

If compression is required, use local-only edits per this skill (no upload).

## When not to optimize

- **Legal / compliance / security** text that must stay verbatim.
- **Skill `description` YAML** — keep third person, WHAT+WHEN, and enough trigger terms for discovery; trim the *body* first, not discovery metadata, unless the user agrees to retune triggers.
- **Generated or vendor-synced** files — optimize only with explicit approval.

## Workflow

1. **Classify** the artifact (skill, rule, agent JSON/MD, command, script, vault note).
2. **Extract intent** — list non-negotiables: required outputs, forbidden actions, tool/order constraints, globs, `alwaysApply`, command args.
3. **Compress** using the tactics below (see **Suggestions** for two-pass discipline).
4. **Regression check** — would a subagent still know when to load this, what to do, and what format to return? If not, restore the minimum clarifying line.

## Compression tactics

- **Imperatives over narrative** — "Run X before Y" instead of paragraphs of motivation.
- **Merge duplicates** — one canonical rule; elsewhere use "See §X above" or a single link to `reference.md` / another rule.
- **One example per pattern** — keep the smallest example that disambiguates; move extra cases to [reference.md](reference.md).
- **Tables → bullets** when the table is mostly sparse; keep tables when alignment encodes meaning (matrices, mappings).
- **Delete throat-clearing** — "It is important to note…", "In today's world…", repeated summaries of the same checklist.
- **Comments in scripts** — keep: non-obvious invariants, safety warnings, env vars; remove: restating the function name or obvious control flow.
- **Progressive disclosure** — keep `SKILL.md` lean; park long templates, edge cases, and copy-paste blocks in `reference.md` / `examples.md` with one-level links per create-skill conventions.

## By artifact type

| Type | Preserve | Trim |
|------|----------|------|
| **Skill** | YAML `name` / `description`, "when to use", critical workflows | Duplicate anti-patterns, multiple identical templates |
| **Rule (.mdc)** | Frontmatter, globs, authority tiers, must-not lists | Tutorial prose duplicated in skills |
| **Agent / subagent** | Role, boundaries, output shape, tool policy | Persona fluff, repeated system reminders |
| **Command** | Args, defaults, safety gates | Long prose already covered by linked rules/skills |
| **Vault / ticket artifact** | AC, repro, identifiers, decisions | Exploratory notes superseded by conclusions (only if user agrees) |
| **Script** | Usage header, destructive guards, idempotency notes | Comment blocks that repeat README |

## Suggestions (recommended practices)

- **Two-pass edits** — pass A: delete duplication, stale examples, and dead sections; pass B: tighten wording. Keeps diffs readable and reduces the chance of silently dropping intent by mixing cuts and rewrites in one blur.
- **Load-order contract** — treat numbered rules, harness gates, and explicit "read X before Y" lines as structure: shorten the prose *under* those anchors, not the sequence or gate list itself.
- **Split over stuffing** — if the primary file is still long after cuts, link once to `reference.md` / `examples.md` (or a sibling rule) instead of growing the main file; pairs with **Progressive disclosure** above.
- **Diff discipline** — optimize in small commits; if intent might shift, add a one-line "Non-goals" or "Out of scope" instead of long caveats.
- **Measure loosely** — fewer lines and fewer repeated phrases usually track token savings better than exact counts.
- **Cross-file dedup** — if a rule and a skill both restate the same policy, keep the canonical copy in **one** place (prefer rules for repo law, skills for procedure).
- **Trigger hygiene** — after shortening a skill `description`, read it as another agent picking skills; if it sounds generic ("helps with documentation"), add back one concrete domain phrase so discovery still works.
- **Subagent skeleton** — smallest useful prompt is usually: role, inputs, expected outputs, tools or readonly policy, stop conditions. Drop repeated parent-system or harness text the parent already applies.
- **Don't "optimize" tests into obscurity** — test names and Arrange data stay explicit; token savings belong in helpers and duplicated setup, not in unreadable abbreviations.
- **Prefer stable section titles** — agents and humans grep for fixed headings; shorten body text under those headings instead of renaming them without cause.

## Anti-patterns (do not introduce while optimizing)

- **Windows-style paths** in examples (`scripts\validate.py`) — use forward slashes.
- **Too many options** — one default procedure; escape hatch only when necessary.
- **Time-sensitive rules** ("before August 2025…") — use stable "current / deprecated" sections instead.
- **Inconsistent terminology** — pick one term per concept (endpoint vs route) and match repo vocabulary.
- **Vague descriptions** after trimming — keep WHAT+WHEN trigger terms in skill YAML.
- **Flattening harness gates** — never delete numbered stages, handoff limits, or `alwaysApply` / globs to save lines.

## Quality bar (before done)

- [ ] Non-negotiables from step 2 still explicit somewhere loadable in one hop.
- [ ] Frontmatter / command schema / JSON still valid.
- [ ] No orphaned links after moving content to reference files.
- [ ] Original purpose obvious in under ~30 seconds of skimming for a maintainer.

## Related

- **Example paths to optimize:** `.claude/skills/*/SKILL.md`, `.claude/agents/*.md`, `.cursor/rules/*.mdc`.
- **`create-skill`** (Anthropic skills bundle) — authoring and progressive disclosure patterns.
- **`CLAUDE.md`** — where new standards vs skills belong for this workspace.
