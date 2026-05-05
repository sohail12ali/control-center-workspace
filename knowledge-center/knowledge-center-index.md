# Knowledge Center

Vault root. Use Obsidian graph + backlinks to navigate.

## Entry points

- [[artifact-map]] — all tickets
- `artifacts/_template/` — copy when creating a new ticket
- `wiki/` — long-lived reference docs

## Layout

```
artifacts/{TICKET}/{TICKET}-{artifact}.md  — work artifacts (filenames prefixed with ticket id)
wiki/                                      — durable knowledge
```

## Files per artifact (per ticket {T})

| File | Phase |
|---|---|
| `{T}-summary.md` | All |
| `{T}-analysis.md` | GROUND, CLARIFY |
| `{T}-requirements.md` | CLARIFY, CANONICAL |
| `{T}-decision-log.md` | CLARIFY, CANONICAL |
| `{T}-questions.md` | CLARIFY |
| `{T}-plan.md` | CANONICAL, TEMPLATE |
| `{T}-progress.md` | TEMPLATE → VERIFY |
| `{T}-verification.md` | VERIFY |

Optional: `{T}-architecture.md`, `{T}-risks.md`, `{T}-notes.md`, `{T}-test-plan.md`

## Filename convention

Every artifact in a ticket directory is named `{TICKET}-{artifact}.md`. Filenames are globally unique across the vault — wikilinks like `[[T013-summary]]` resolve from anywhere. Every artifact carries a `## Links` block referencing every sibling so the ticket renders as a tightly-connected cluster in Obsidian's graph view.
