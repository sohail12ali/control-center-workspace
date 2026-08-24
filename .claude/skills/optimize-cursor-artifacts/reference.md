# optimize-cursor-artifacts — extended notes

Optional read when the main skill is not enough context.

## Skill description vs body

- **Description (YAML)**: discovery surface; keep trigger terms (file types, tools, domain words). Third person, WHAT + WHEN, max length per the platform's skill-authoring docs.
- **Body**: procedural density; safe to aggressively trim if triggers stay in YAML.

## Rules (.mdc) frontmatter

Do not remove or break:

- `description`, `globs`, `alwaysApply`, or other keys the repo relies on.
- Tier / ordering comments only if they prevent wrong merge order (some harnesses depend on numeric prefixes like `00-`).

## Commands and agents

- **Commands**: user-visible; keep argument names and defaults exact; shorten explanatory paragraphs that duplicate linked rules.
- **Agent definitions**: preserve tool allowlists, readonly flags, and "return format" contracts; trim motivational or redundant system text that duplicates parent harness.

## Vault artifacts

- Keep identifiers (ticket id, object names, parameters) literal.
- Collapse narrative investigation into "Context / Decision / Steps" only when the user wants archival cleanup, not silent deletion of audit trail without confirmation.

## Token heuristics (imperfect)

- Removing duplicated paragraphs often beats micro-editing adjectives.
- Lists of 8+ similar items: consider grouping into categories with one example each.
