---
name: consolidate
description: Canonical home for artifact layout, naming, wikilink, and structure rules for every ticket. Optional /consolidate migrates a scattered multi-folder ticket to the flat convention.
---

# /consolidate

**When:** (1) Reference — canonical structure rules every skill and agent follows (CLAUDE.md links here). (2) `/consolidate {TICKET}` — one-way migration of a legacy multi-folder ticket to the flat convention. Skip if already flat. Workspace/git layout lives in `project-layout`.

## Structure rules

### Ticket folder — `knowledge-center/artifacts/{TICKET}/`

`{TICKET}` = ticket id (`T013`, `BUG-042`, `FEATURE-AUTH`; multi-project workspaces may prefix, e.g. `NA-T001`). Filenames: **`{TICKET}-{artifact}.md`** (kebab-case artifact) — flat, no subfolders, for the standard set:

| File | Phase |
|------|-------|
| `{TICKET}-summary.md` | All — hub |
| `{TICKET}-analysis.md` | GROUND, CLARIFY |
| `{TICKET}-requirements.md` | CLARIFY, CANONICAL |
| `{TICKET}-decision-log.md` | CLARIFY, CANONICAL |
| `{TICKET}-questions.toml` | CLARIFY |
| `{TICKET}-plan.md` | CANONICAL, TEMPLATE |
| `{TICKET}-progress.md` | TEMPLATE → VERIFY |
| `{TICKET}-verification.md` | VERIFY |
| `ticket.toml` | All — console/CLI state (stage, status, owner; see `console`) |

Optional, on demand: `{TICKET}-architecture.md`, `{TICKET}-risks.md`, `{TICKET}-notes.md`, `{TICKET}-test-plan.md`, `{TICKET}-bugs.toml`, `{TICKET}-todos.toml`, `{TICKET}-release.md`, and the pre-freeze working set (`{TICKET}-requirements-draft.md`, `{TICKET}-context-snapshot.md`, `{TICKET}-gap-analysis.md`, `{TICKET}-iteration-log.md`, `{TICKET}-user-stories.md`, `{TICKET}-critique-report.md`). Reserved, not yet console-wired: `{TICKET}-gaps.toml`, `{TICKET}-critique.toml`.

**TOML exception:** `ticket.toml` and the tracker files (`{TICKET}-questions.toml`/`-bugs.toml`/`-todos.toml`) are **CLI-mutated only** — written by `console/kanban.py` (directly or via the `questions`/`bugs`/`todos` skills), never hand-edited (trackers need atomic, race-safe writes under concurrent agents).

**Subfolder exceptions (the only ones):** `{TICKET}/ticket-scripts/` — SQL or other scripts that don't fit the `{TICKET}-{artifact}` pattern; no declaration needed; never put a `{TICKET}-{artifact}`-pattern file inside it. `{TICKET}/investigations/` and `knowledge-center/investigations/` — see `investigate`.

**Anti-patterns:** planning markdown at vault root; files without the `{TICKET}-` prefix; nested subfolders (`requirements/`, `plans/`, `qa/`, …) for the standard set. Scaffold new tickets via `kickoff`, never manual copy.

### Vault siblings

| Path | Role |
|------|------|
| `knowledge-center/artifact-map.md` | Fleet index — one row per ticket, updated on create/status-change/close |
| `knowledge-center/artifacts/_template/` | Source templates for `kickoff` |
| `knowledge-center/wiki/` | Durable cross-ticket reference docs and ADRs |
| `knowledge-center/investigations/INV-{date}-{slug}/` | Pre-ticket dossiers (see `investigate`); once `{TICKET}` exists, dossiers go under `artifacts/{TICKET}/investigations/` |
| `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{slug}.md` | Per-author daily log — see `log-work` |

### Wikilinks

- Bare filename, no `.md`, no folder prefix (filenames are globally unique): `[[T013-summary]]`, never `[[artifacts/T013/summary]]`.
- Artifact-map row: `- [[{TICKET}-summary]] — {title} — {Status} — {Owner} — {DATE}`.
- Every artifact ends with a `## Links` block listing every sibling artifact — the ticket renders as a fully-connected Obsidian cluster. Never strip or shorten it.
- `.toml` files are never wikilinked (bare `[[name]]` resolves to `name.md`); reference as plain text `` `{TICKET}-questions.toml` ``.

### Before save/finalize

Path + `{TICKET}-` prefix correct · frontmatter complete (`tags`, `status`, `ticket`) · wikilinks resolve · `## Links` block present and complete · artifact-map row current.

### Find files for a ticket

1. `{TICKET}-summary.md` (hub). 2. `knowledge-center/artifact-map.md`, or `console/kanban.py ticket show {TICKET}` (adds tracker counts). 3. Glob `knowledge-center/artifacts/{TICKET}/{TICKET}-*.md`; `ticket.toml` + tracker `.toml`s sit alongside.

Sub-project code layout: that sub-project's own `CLAUDE.md` — not duplicated here.

## Steps — `/consolidate {TICKET}`

1. **Validate** — list the ticket directory; exit if already flat.
2. **Merge** — fold each legacy subfolder into the matching standard artifact (`requirements/*` → `{TICKET}-requirements.md`; `qa/*`/`review/*` → single mutable `{TICKET}-verification.md`, updated in place). Preserve substantive content — never silently drop findings.
3. **Rename** — add the `{TICKET}-` prefix; kebab-case the artifact name.
4. **Hub** — rewrite `{TICKET}-summary.md`'s `## Links` to the final flat set; update the artifact-map row if path/status changed.
5. **Delete** merged-empty legacy folders; keep folders holding non-artifact material (note they're outside the convention).
6. **Verify** — every file matches `{TICKET}-*.md` at ticket root · `## Links` resolve both ways (`validate-artifacts`, scopes links/trace) · artifact-map row current.

## Output

Migration edits files in place under `knowledge-center/artifacts/{TICKET}/` per the rules above, plus:

```
── Consolidation complete ──
Ticket: {TICKET} | scattered → flat | Next: progress-tracker or verify
```

**Delegates:** `planner` (structure) · `validate-artifacts` (link integrity, scopes links/trace)

**Version:** 1.2 — lean rewrite | **Updated:** 2026-08-23
