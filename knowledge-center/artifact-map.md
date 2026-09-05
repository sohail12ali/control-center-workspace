# Artifact Map

Index of all work artifacts. One row per ticket. Update when artifacts are created, change status, or close.

## Active

- [[T-001-summary]] — Native desktop shell spike wrapping the Delivery Console — Verify — Sohail Ali — 2026-09-05
- [[T-002-summary]] — Desktop tray skeleton as the Agents control surface — Verify — Sohail Ali — 2026-09-05

## Blocked

## Completed

- [[CC-T006-summary]] — Phase 3b - remote: Tailscale bind, audit log, Telegram approval notifications — Complete — Sohail Ali — 2026-08-29
- [[CC-T005-summary]] — Phase 4 - UI and chat: diff cards, command palette, pickers, cost badges — Complete — Sohail Ali — 2026-08-29
- [[CC-T004-summary]] — Phase 3a - scheduler: cron-driven verbs on the job queue — Complete — Sohail Ali — 2026-08-29
- [[CC-T003-summary]] — Phase 2 - OpenRouter backend: API transport, tool loop, skill injection, model routing — Complete — Sohail Ali — 2026-08-29
- [[CC-T002-summary]] — Phase 1 - agent body: verbs, one-call context, worktrees, job queue, MCP — Complete — Sohail Ali — 2026-08-29
- [[CC-T001-summary]] — Phase 0 - harness foundation: defects, tests, CI, telemetry — Complete — Sohail Ali — 2026-08-29

## Archived

---

## Schema

`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`

## Conventions

- **IDs:** `T###` (general), `BUG-###`, `FEATURE-NAME`, `EPIC-NAME`, `PROJ-XXX`. For multi-project workspaces, prefix per project: `NA-T001`, `BE-T012`, `ML-T003`.
- **Hierarchy:** `TICKET / SLICE / PHASE-{ENTITIES|DB|API|UI} / TASK` (only when needed; most tickets stay flat).
- **Filenames:** every artifact in a ticket directory is `{ID}-{artifact}.md` (globally unique across the vault).
- **Tags** (in `{ID}-summary.md` frontmatter): `[active]`, `[blocked]`, `[completed]`, `[urgent]`, `[waiting]`.
