---
name: validate-artifacts
description: Validate all ticket artifacts are complete and correctly structured. Use after planning (before build) or after changes (evolve, re-plan).
---

# /validate-artifacts

**Usage:** `/validate-artifacts [T]` — `[T]` ticket id (optional if context clear).

**When:** After planning, to confirm the plan is complete before building; or after changes, to re-check structure.

## Steps

1. Check required artifacts exist under `knowledge-center/artifacts/{T}/` using the flat `{T}-{artifact}.md` naming: `{T}-summary.md`, `{T}-requirements.md`, `{T}-plan.md`, plus any of `{T}-analysis.md`, `{T}-decision-log.md`, `{T}-questions.md`, `{T}-progress.md`, `{T}-verification.md` that the ticket's stage requires.
2. **Misplacement check** — flag any artifact that is unprefixed (e.g. bare `plan.md`) or nested in a subfolder that the flat convention doesn't use; report with a relocate instruction.
3. Validate artifact structure (required sections/fields/tables per `knowledge-center/artifacts/_template/`):
   - Requirements: functional, non-functional, acceptance criteria, out-of-scope sections present.
   - Plan: each task has a done-criterion, dependencies, and effort.
   - Verification: every acceptance criterion has a status and evidence column.
4. Check cross-artifact links (see `check-artifact-links` for the full bidirectional walk) — at minimum confirm every artifact's `## Links` block lists its siblings.
5. Report missing artifacts, missing sections, or broken links with concrete fixes.

## Output

```
── Artifact Validation: {T} ──

Artifacts present:
  [x] {T}-summary.md
  [x] {T}-requirements.md
  [x] {T}-plan.md
  ...

Structure validation:
  [x] Requirements have testable acceptance criteria
  [x] Plan tasks have done-criteria and effort
  ...

Ready: true | false
Next: fix paths/structure, or proceed to build
```

## Rules

- Filenames must follow `{T}-{artifact}.md` flat under `knowledge-center/artifacts/{T}/` — no nested subfolders for standard artifacts.
- Every artifact must end with a `## Links` block per `CLAUDE.md`'s linking convention.
- A ticket is not build-ready until requirements and plan both pass structure checks with no missing sections.

**Delegates to:** none (validation only); `check-artifact-links` for the deeper bidirectional link walk.

**Version:** 1.0-generic | **Updated:** 2026-07-04
