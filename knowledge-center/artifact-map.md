# Artifact Map

Index of all work artifacts. One row per ticket. Update when artifacts are created, change status, or close.

## Active

## Blocked

## Completed

- [[T01-summary]] — Prayer, Alarm & Quran Feature Enhancements — Complete — Noble Wave — 2026-05-06

## Archived

---

## Schema

`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`

## Conventions

- **IDs:** `T###` (general), `BUG-###`, `FEATURE-NAME`, `EPIC-NAME`, `PROJ-XXX`. For multi-project workspaces, prefix per project: `NA-T001`, `BE-T012`, `ML-T003`.
- **Hierarchy:** `TICKET / SLICE / PHASE-{ENTITIES|DB|API|UI} / TASK` (only when needed; most tickets stay flat).
- **Filenames:** every artifact in a ticket directory is `{ID}-{artifact}.md` (globally unique across the vault).
- **Tags** (in `{ID}-summary.md` frontmatter): `[active]`, `[blocked]`, `[completed]`, `[urgent]`, `[waiting]`.
