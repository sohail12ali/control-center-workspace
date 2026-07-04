---
name: project-layout
description: Workspace layout, git conventions, vault paths, and multi-project routing patterns. Load for repo navigation, artifact paths, git branches, or build/test orchestration across sub-projects.
---

# Project Layout

**Workspace resolution:** the VS Code / Cursor multi-root workspace file (if one exists) lists every sub-project folder. If no workspace file is checked in yet, treat each folder added under the workspace root as a sub-project with its own `CLAUDE.md`.

---

## Workspaces

**control-center-workspace** is the umbrella repo (`.claude/`, `.cursor/`, `knowledge-center/`). It is project-independent: it owns the harness, the vault, and cross-cutting skills, but no product code of its own.

Sub-projects are added as sibling folders (or as entries in a multi-root workspace file) **next to** this umbrella repo. Each sub-project has its **own `.git`** (nested repository) and its **own `CLAUDE.md`** describing its stack, build/test commands, and layer conventions.

**Recommended:** open the umbrella repo as the primary workspace root, with sub-projects added alongside it. **Obsidian:** open the umbrella repo folder as the vault; notes live under `knowledge-center/`.

### Example layout (adapt to the actual workspace)

| Folder | Role |
|--------|------|
| `control-center-workspace/` (this repo) | Harness, vault, cross-cutting skills — no product code |
| `{sub-project}/` | One product/service/app repo, own `.git` and `CLAUDE.md` |
| `{sub-project}/.claude/skills/` | That sub-project's own build/test/publish procedures |

This is an example shape, not a mandate — a workspace may have one sub-project or a dozen; the pattern that matters is: **umbrella owns process, sub-project owns product**.

### Integration points

When a workspace has multiple sub-projects that call each other (a UI calling a service API, a batch job sharing a database with a web app, etc.), document the integration points once — in the umbrella `knowledge-center/wiki/`, or in whichever sub-project's `CLAUDE.md` is the natural home — rather than repeating them per ticket.

### Indexing / editor scope

If the editor's indexer is configured to exclude nested sub-projects by default (e.g. `.cursorignore`), toggle the entry for the sub-project actively being edited so the editor indexes that tree.

---

## Artifact paths

Skills and agents use **`knowledge-center/artifacts/{TICKET}/`** for ticket outputs. See `consolidate/SKILL.md` for the full file set and naming convention. Prefer one flat directory per ticket — no nested subfolders for the standard artifact set.

---

## Capturing user-stated logic (artifacts vs rules)

When the user provides **business rules**, **core feature principles**, or **domain logic** that must not be lost to chat compaction:

- **Ticket- or slice-scoped**: record it under `knowledge-center/artifacts/{TICKET}/` — link from `{TICKET}-summary.md`.
- **Cross-ticket or workspace-wide**: **propose** a minimal addition to the smallest matching `.cursor/rules/{domain}.mdc` file, or the relevant sub-project's `CLAUDE.md`. Present the diff for **human approval** before treating it as merged policy.

Use `evolve` to fold ticket learnings into durable rules once a pattern repeats.

---

## Sub-project build/test routing

**Umbrella** agents orchestrate tickets end to end; **sub-project repos** own executable build/test/publish procedures for their own stack.

| Layer | Path |
|-------|------|
| Per-sub-project index | `{sub-project}/CLAUDE.md` |
| Per-sub-project procedures | `{sub-project}/.claude/skills/<skill-id>/SKILL.md` |

Before running a build, test, or publish command inside a sub-project: **read that sub-project's own `CLAUDE.md` first** — do not guess commands, output paths, or conventions from the umbrella repo or from memory. If a workspace grows enough sub-projects that routing by hand becomes error-prone, add a small registry note under `knowledge-center/wiki/` mapping sub-project name → path, and keep it current as sub-projects are added or removed.

---

## Git & branches

### Umbrella vs sub-project repos

- The umbrella repo (this one) and each sub-project are **separate git roots**. Always detect the root with `git rev-parse --show-toplevel` before assuming which repo a command targets.
- Never assume a single monorepo checkout — a multi-root workspace can span several independent `.git` directories.

### Default remote branch (per repo)

1. Check the repo's actual default branch (`main`, `master`, `develop`, or similar) — do not assume `main` universally.
2. If ambiguous, **stop and ask** for the base branch name rather than guessing.

### Feature branch naming (example convention — adapt per repo)

```
feature/{TICKET}-{short-slug}
```

Example: `feature/T042-rate-limit-middleware`. This is a common convention, not a fixed rule — if a sub-project already has its own branch naming scheme (e.g. `release/*` for release branches), follow that repo's existing convention instead. Prefer using the same branch name across sub-projects touched by the same ticket, when the conventions allow it.

### When not to auto-create a branch

Working tree dirty, detached HEAD, no push access, or ambiguous default branch — stop and notify the user instead of guessing.

---

## Vault maintenance

### Authority

- **Conventions and directory roles**: `knowledge-center/knowledge-center-index.md`.
- **Artifact naming and structure**: `consolidate/SKILL.md`.
- **Ticket starters**: `knowledge-center/artifacts/_template/`.

### MUST

1. **Frontmatter** on new or edited ticket markdown: `tags`, `status`, `ticket` (see `_template/summary.md` for the shape).
2. **Ticket linkage**: files under `artifacts/{TICKET}/` reference `{TICKET}` in frontmatter and in the `## Links` block.
3. **Wikilinks** in vault notes: bare filename, no `.md`, no folder prefix (filenames are globally unique across the vault).
4. **Logging:** `log-work` → `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md` (`## Work` bullets; author in frontmatter). Kickoff / close-work / stage transitions → milestone block at the top of the same per-author file.

### MUST NOT

- Copy long normative standards from rules into every ticket — summarize and link instead.
- Invent vault folder roles that contradict `knowledge-center-index.md`.
- Create nested subfolders for the standard ticket artifact set — keep it flat.

### Rules evolution

After a review pass or recurring issue class, propose minimal rule diffs to the appropriate `.cursor/rules/{domain}.mdc` file. **Human gate**: present proposed edits; do not assume merge without explicit approval.

---

**Version:** 1.0 — ported from lc-wms-cursor-config, genericized for control-center-workspace (project-agnostic, no named sub-repos or company-specific registry)
