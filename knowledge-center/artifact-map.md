# Artifact Map

Index of all work artifacts. One row per ticket. Update when artifacts are created, change status, or close.

## Active

- [[T001-summary]] — Harness Kit: Portable Agent Harness (IDE Extension) — Active (VERIFY: kanban-first default-UI gap fixed, 164/164 tests; manual VSIX/GUI confirmation still pending) — Sohail Ali — 2026-07-05

## Blocked

## Completed

## Archived

---

## Schema

`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`

## Conventions

- **IDs:** `T###` (general), `BUG-###`, `FEATURE-NAME`, `EPIC-NAME`, `PROJ-XXX`. For multi-project workspaces, prefix per project: `NA-T001`, `BE-T012`, `ML-T003`.
- **Hierarchy:** `TICKET / SLICE / PHASE-{ENTITIES|DB|API|UI} / TASK` (only when needed; most tickets stay flat).
- **Filenames:** every artifact in a ticket directory is `{ID}-{artifact}.md` (globally unique across the vault).
- **Tags** (in `{ID}-summary.md` frontmatter): `[active]`, `[blocked]`, `[completed]`, `[urgent]`, `[waiting]`.
