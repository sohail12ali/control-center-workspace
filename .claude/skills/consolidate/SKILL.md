---
name: consolidate
description: Canonical home for artifact layout, naming, wikilink, and structure rules for every ticket. Optional /consolidate migrates a scattered multi-folder ticket to the flat convention.
---

# consolidate

**Two roles:** (1) **Structure rules** — canonical paths and naming every skill and agent follows. (2) **`/consolidate {TICKET}`** — optional one-way migration of a legacy multi-folder ticket into the flat convention.

Workspace layout (repos, git, multi-project routing): `.claude/skills/project-layout/SKILL.md`.

`CLAUDE.md` states the filename convention inline; this file is the canonical, detailed source it links to.

---

## Structure rules

### Ticket folder (`knowledge-center/artifacts/{TICKET}/`)

`{TICKET}` = ticket id (`T013`, `BUG-042`, `FEATURE-AUTH`; multi-project workspaces may prefix, e.g. `NA-T001`). Filenames: **`{TICKET}-{artifact}.md`** (kebab-case `artifact`) — flat, no subfolders, for the standard set below.

| File | Phase |
|------|-------|
| `{TICKET}-summary.md` | All — hub |
| `{TICKET}-analysis.md` | GROUND, CLARIFY |
| `{TICKET}-requirements.md` | CLARIFY, CANONICAL |
| `{TICKET}-decision-log.md` | CLARIFY, CANONICAL |
| `{TICKET}-questions.md` | CLARIFY |
| `{TICKET}-plan.md` | CANONICAL, TEMPLATE |
| `{TICKET}-progress.md` | TEMPLATE → VERIFY |
| `{TICKET}-verification.md` | VERIFY |

Optional, add only when the ticket needs them: `{TICKET}-architecture.md`, `{TICKET}-risks.md`, `{TICKET}-notes.md`, `{TICKET}-test-plan.md`, `{TICKET}-open-bugs.md` (see `bugs`), `{TICKET}-open-todos.md` (see `todos`), and the pre-freeze working set (`{TICKET}-requirements-draft.md`, `{TICKET}-context-snapshot.md`, `{TICKET}-gap-analysis.md`, `{TICKET}-iteration-log.md`, `{TICKET}-user-stories.md`, `{TICKET}-critique-report.md`) created on demand by the requirements/planning/verification pipelines.

**Anti-patterns:** planning markdown at the vault root; files without the `{TICKET}-` prefix; nested subfolders (`requirements/`, `plans/`, `qa/`, …) for the standard set — the flat convention exists precisely to avoid these. Scaffold new tickets via `kickoff`, not manual copy.

### Vault siblings

| Path | Role |
|------|------|
| `knowledge-center/artifact-map.md` | Fleet index — one row per ticket, updated on create/status-change/close |
| `knowledge-center/artifacts/_template/` | Source templates for `kickoff` |
| `knowledge-center/wiki/` | Durable, cross-ticket reference docs and ADRs |
| `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{slug}.md` | Per-author daily log — see `log-work/SKILL.md` |

### Wikilinks

- Omit `.md`, no folder prefix needed since filenames are globally unique: `[[T013-summary]]`, not `[[artifacts/T013/summary]]`.
- Artifact-map rows link the hub: `- [[{TICKET}-summary]] — {title} — {Status} — {Owner} — {DATE}`.
- Every artifact ends with a `## Links` block listing every sibling artifact in the ticket, so the ticket renders as a fully-connected cluster in Obsidian's graph view. Do not strip or shorten this block.

### Before save / finalize

Path + `{TICKET}-` prefix correct · frontmatter complete (`tags`, `status`, `ticket`) · wikilinks resolve · `## Links` block present and complete · artifact-map row current.

### Find files for a ticket

1. `{TICKET}-summary.md` (hub, links to every sibling).
2. `knowledge-center/artifact-map.md` (status, owner, cross-ticket view).
3. Glob `knowledge-center/artifacts/{TICKET}/{TICKET}-*.md` for the full set.

Product code layout for a specific sub-project (source folders, build/test commands): that sub-project's own `CLAUDE.md` — not duplicated here.

---

## `/consolidate {TICKET}`

**When:** A ticket has artifacts scattered across legacy subfolders (e.g. `requirements/`, `plans/`, `database/`, `api/`, `ui/`, `testing/`, `qa/`) instead of the flat `{TICKET}-{artifact}.md` convention, and the ticket should be brought in line before further work.

**Skip if:** Already flat (every artifact file sits directly under `artifacts/{TICKET}/` with the `{TICKET}-` prefix).

| Before | After |
|--------|-------|
| Multi-folder scatter, inconsistent naming | Flat `{TICKET}-{artifact}.md` set at ticket root |
| Duplicate/versioned review files | Single **mutable** `{TICKET}-verification.md` (or equivalent), updated in place |

### Steps

1. **Validate** — list the ticket directory; exit if already flat.
2. **Merge** — fold each legacy subfolder's content into the matching standard artifact (e.g. `requirements/*` → `{TICKET}-requirements.md`; `qa/*` or `review/*` → `{TICKET}-verification.md`). Preserve substantive content; do not silently drop findings — summarize into the target file.
3. **Rename** — any single-purpose file without the `{TICKET}-` prefix gets it; kebab-case the artifact name.
4. **Hub** — rewrite `{TICKET}-summary.md`'s `## Links` block to reference the final flat file set; update the `knowledge-center/artifact-map.md` row if the path or status changed.
5. **Delete** merged-empty legacy folders. Keep any folder still holding non-artifact material (e.g. raw stakeholder attachments) but note it isn't part of the flat convention.
6. **Verify** — every remaining file matches `{TICKET}-*.md` directly under the ticket root · `## Links` blocks resolve both ways (see `trace` skill) · artifact-map row current.

### Output

```
── Consolidation complete ──
Ticket: {TICKET} | scattered → flat | Next: progress-tracker or verify
```

**Delegates:** `planner` (structure) · `check-artifact-links` / `trace` (link integrity)

**Version:** 1.0 — ported from lc-wms-cursor-config, generalized to control-center-workspace's flat artifact convention
