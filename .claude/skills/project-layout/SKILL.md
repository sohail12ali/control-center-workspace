---
name: project-layout
description: Workspace layout, git conventions, vault paths, and multi-project routing patterns. Load for repo navigation, artifact paths, git branches, or build/test orchestration across sub-projects.
---

# /project-layout

**When:** Repo navigation, artifact paths, git/branch questions, or routing build/test/publish to the right sub-project. Reference skill — load before acting across repos.

## Workspaces

- **control-center-workspace** is the umbrella repo (`.claude/`, `.cursor/`, `knowledge-center/`): harness, vault, cross-cutting skills — **no product code**.
- Sub-projects are sibling folders (or multi-root workspace entries) next to the umbrella, each with its **own `.git`** and **own `CLAUDE.md`** (stack, build/test commands, layer conventions). If no workspace file is checked in, treat each folder under the workspace root as a sub-project.
- Pattern: **umbrella owns process, sub-project owns product.** Open the umbrella as primary workspace root; Obsidian vault = the umbrella folder (`knowledge-center/`).
- **Integration points** between sub-projects (UI↔API, shared DB): document once — `knowledge-center/wiki/` or the natural sub-project `CLAUDE.md` — not per ticket.
- **Editor indexing:** if the indexer excludes nested sub-projects (e.g. `.cursorignore`), toggle the entry for the sub-project being edited.

## Artifact paths

Ticket outputs → `knowledge-center/artifacts/{TICKET}/`, flat, per `consolidate` (full file set and naming).

## Capturing user-stated logic

- **Ticket/slice-scoped** business rules or domain logic → `knowledge-center/artifacts/{TICKET}/`, linked from `{TICKET}-summary.md`.
- **Cross-ticket/workspace-wide** → **propose** a minimal diff to the smallest matching `.cursor/rules/{domain}.mdc` or the sub-project's `CLAUDE.md`; **human approval before treating as merged**. Use `evolve` to fold repeated ticket learnings into durable rules.

## Sub-project build/test routing

| Layer | Path |
|-------|------|
| Per-sub-project index | `{sub-project}/CLAUDE.md` |
| Per-sub-project procedures | `{sub-project}/.claude/skills/<skill-id>/SKILL.md` |

Before any build/test/publish inside a sub-project: **read that sub-project's `CLAUDE.md` first** — never guess commands from the umbrella or memory. If routing by hand gets error-prone, keep a registry note in `knowledge-center/wiki/` mapping sub-project name → path.

## Git & branches

- Umbrella and each sub-project are **separate git roots** — detect with `git rev-parse --show-toplevel` before any command; never assume a monorepo.
- **Default branch:** check the repo's actual default (`main`, `master`, `develop`, …); if ambiguous, **stop and ask** — don't guess.
- **Feature branches** (example convention — adapt per repo): `feature/{TICKET}-{short-slug}`, e.g. `feature/T042-rate-limit-middleware`. If a repo has its own scheme (e.g. `release/*`), follow that. Prefer the same branch name across sub-projects touched by one ticket when conventions allow.
- **Don't auto-create a branch** when: working tree dirty, detached HEAD, no push access, or ambiguous default branch — stop and notify.

## Vault maintenance

Authority: conventions/directory roles → `knowledge-center/knowledge-center-index.md`; artifact naming/structure → `consolidate`; ticket starters → `knowledge-center/artifacts/_template/`.

**MUST:**
1. Frontmatter on new/edited ticket markdown: `tags`, `status`, `ticket` (shape: `_template/summary.md`).
2. Files under `artifacts/{TICKET}/` reference `{TICKET}` in frontmatter and `## Links`.
3. Wikilinks: bare filename, no `.md`, no folder prefix.
4. Logging: `log-work` → `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md` (`## Work` bullets; author in frontmatter); kickoff/close-work/stage transitions → milestone block atop the same file.

**MUST NOT:** copy long normative standards into tickets (summarize + link); invent vault folder roles contradicting `knowledge-center-index.md`; nest subfolders for the standard artifact set.

**Rules evolution:** after a review pass or recurring issue class, propose minimal diffs to `.cursor/rules/{domain}.mdc` — human gate, no assumed merge.

## Output

Reference only — no files written by this skill.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
