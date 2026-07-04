---
name: check-artifact-links
description: Verify all cross-artifact links are bidirectional and complete, and report the full Requirement <-> Task <-> Code/Files <-> Verification traceability chain with coverage percentages. Use after planning to confirm artifacts are connected, mid-build to show requirements coverage, or after evolve to re-check traceability.
---

# /check-artifact-links

**Usage:** `/check-artifact-links [T]` — `[T]` ticket id (optional if context clear).

**When:** After planning, to validate artifacts are connected before build; mid-build, to show requirements coverage or re-check traceability after `evolve`; or before merge, as part of `verify`'s `ready` scope.

## Steps

1. Load whichever ticket artifacts exist under `knowledge-center/artifacts/{T}/`: `{T}-requirements.md`, `{T}-plan.md`, `{T}-progress.md`, `{T}-verification.md`, `{T}-summary.md`, plus the richer optional chain if the ticket uses it — `{T}-user-stories.md`, `{T}-components.md`, `{T}-task-breakdown.md` (from `extract-stories` / `analyze-components` / `breakdown-tasks`).
2. Verify bidirectional links between whatever chain is in use:
   - Minimal chain: Requirements ↔ Plan tasks ↔ Progress/Verification.
   - Richer chain (if present): User Stories ↔ Components ↔ Tasks ↔ Implementation plan.
3. For each requirement/acceptance criterion, build the full traceability chain and its evidence: which plan task(s) satisfy it → which files/commits implement it → what progress/verification evidence exists. If the richer chain is present, insert story/component as intermediate links.
4. Check completeness and classify gaps precisely, not just "broken/missing":
   - **unfulfilled** — requirement/acceptance criterion has no downstream task (or story, in the richer chain).
   - **incomplete** — task has no implementing file/commit.
   - **unverified** — task has no verification evidence.
   - Also: every plan task → at least one requirement/criterion it satisfies; every task in a richer chain → at least one component and one story; orphaned requirements, unlinked tasks, mismatched IDs, or wikilinks that don't resolve to an existing file.
5. Validate link syntax: `[[{T}-{artifact}]]` wikilinks, matching case, and stable IDs (e.g. `US-{n}`, task ids) if the richer chain is in use. ID formats must match whatever `extract-stories` / `breakdown-tasks` actually emitted — don't invent a new scheme here.
6. Report coverage percentages per level (requirements / tasks / verification) and a flagged gap list with concrete fixes — don't just list gaps flat, call out blockers and dependency chains.

## Output

```
── Artifact Link Verification: {T} ──

Artifacts checked: {list}

Requirements coverage:
  [x] R-1: {title}
    -> Task(s): {ids}
    -> Files: {n} ({paths or count})
    -> Verification: {criterion status}

  [ ] R-2: {title} (UNFULFILLED — no task linked)

Task -> Progress/Verification links:
  [x] Task 3 -> progress entry {date} -> verification criterion 1
  [ ] Task 4 -> (INCOMPLETE — no files/commits) | (UNVERIFIED — no verification evidence)

Broken links:
  [1] {severity}: {description} — {impact} — {fix}

Coverage summary:
  Requirements: {n}/{total} linked/fulfilled ({%})
  Tasks: {n}/{total} linked/complete ({%})
  Verification: {n}/{total} criteria with evidence ({%})

Ready: true | false
Next: fix links, or proceed
```

## Rules

- Bidirectional links must exist in both directions.
- Every requirement/acceptance criterion needs at least one downstream task; orphans are critical findings (**unfulfilled**).
- Every task needs at least one upstream requirement/criterion; unmoored tasks are critical findings.
- Every task needs at least one implementing file/commit (**incomplete** if not) and at least one verification criterion (**unverified** if not) — orphaned verification criteria with no requirement source are a gap too.
- Wikilink targets must resolve to a real file in the ticket directory — treat a dangling `[[...]]` as a broken link.

**Delegates to:** none (verification/reporting only).

**Version:** 3.0-merged | **Updated:** 2026-07-04
