# Artifact Map

Index of all work artifacts. One row per ticket. Update when artifacts are created, change status, or close.

## Active

- [[T-002-summary]] — Desktop tray skeleton as the Agents control surface — Verify — Sohail Ali — 2026-09-05

## Blocked

## Completed

- [[T-010-summary]] — Voice responsiveness: HUD, cues, adaptive VAD, faster STT — Complete — Sohail Ali — 2026-09-07
- [[T-009-summary]] — Tray click-to-talk, armed icon, Assistant settings panel — Complete — Sohail Ali — 2026-09-07
- [[T-008-summary]] — Hands-free listening: wake word, echo handling, barge-in — Complete — Sohail Ali — 2026-09-07
- [[T-007-summary]] — Multimodal send: screenshot pixels to vision models, destination chip — Complete — Sohail Ali — 2026-09-07
- [[T-006-summary]] — Voice: mic capture, STT, hotkey, spoken replies — Complete — Sohail Ali — 2026-09-07
- [[T-005-summary]] — Native bridge: tray icon states, screenshot, OCR, clipboard — Complete — Sohail Ali — 2026-09-07
- [[T-004-summary]] — Assistant brain: persona, /api/assistant, fast commands, Settings backend picker, memory — Complete — Sohail Ali — 2026-09-06
- [[T-003-summary]] — Shell hygiene: no stray console, per-OS launch path, close T-001/T-002 — Complete — Sohail Ali — 2026-09-06
- [[T-001-summary]] — Native desktop shell spike wrapping the Delivery Console — Complete — Sohail Ali — 2026-09-06
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
