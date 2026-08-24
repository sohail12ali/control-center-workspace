---
name: validate-artifacts
description: Artifact integrity in one skill — scope structure validates all ticket artifacts are complete and correctly structured; scope links verifies cross-artifact links are bidirectional and reports the full Requirement ↔ Task ↔ Code ↔ Verification traceability chain with coverage percentages; scope trace shows one file's UP links (sources) and DOWN links (dependents) with missing-link report. Use after planning (before build), mid-build for coverage, or after evolve/replan. Report-only — never modifies files.
---

# /validate-artifacts

**When:** After planning (before build), mid-build (requirements coverage), after `evolve`/`replan`, or pre-merge as part of `verify ready` — `/validate-artifacts {T} [structure|links|trace {file}]` (default `structure`; `ready` runs structure + links).

## scope: structure

1. Check required artifacts exist under `knowledge-center/artifacts/{T}/`, flat `{T}-{artifact}.md` naming: `{T}-summary.md`, `{T}-requirements.md`, `{T}-plan.md`, plus any of `{T}-analysis.md`, `{T}-decision-log.md`, `{T}-questions.toml`, `{T}-progress.md`, `{T}-verification.md` the stage requires.
2. Misplacement check — flag anything unprefixed (bare `plan.md`) or nested where the flat convention doesn't allow; report with a relocate instruction.
3. Validate structure per `_template/`: requirements have functional, non-functional, acceptance-criteria, out-of-scope sections; every plan task has done-criterion, dependencies, effort; verification has status + evidence per criterion.
4. Minimum link check: every artifact's `## Links` block lists its siblings (full walk: scope links).

## scope: links

1. Load whichever artifacts exist: requirements, plan, progress, verification, summary, plus the richer chain if used — `{T}-user-stories.md`, `{T}-components.md`, `{T}-task-breakdown.md`.
2. Verify bidirectional links on the chain in use — minimal: Requirements ↔ Plan tasks ↔ Progress/Verification; richer: User Stories ↔ Components ↔ Tasks ↔ Implementation plan.
3. Per requirement/AC, build the full evidence chain: satisfying task(s) → implementing files/commits → progress/verification evidence (story/component as intermediates when present).
4. Classify gaps: **unfulfilled** (requirement/AC with no downstream task/story) · **incomplete** (task with no implementing file/commit) · **unverified** (task with no verification evidence). Also flag: tasks with no upstream requirement, tasks missing component/story on the richer chain, orphaned requirements/verification criteria, mismatched IDs, dangling wikilinks.
5. Validate link syntax: `[[{T}-{artifact}]]`, matching case, stable IDs (`US-{n}`, task ids) matching what `requirements stories` / `breakdown-tasks` actually emitted — never invent a new scheme.
6. Report per-level coverage percentages and a gap list with concrete fixes — call out blockers and dependency chains, not a flat list.

## scope: trace {file}

1. Resolve the file (repo-relative/absolute path or artifact/ticket id); ambiguous → list candidates and ask.
2. UP links (sources): code → imports, base types, injected deps, data models, called services; artifacts → wikilinks, refs, frontmatter `related`; config/rules → referenced files, globs, loaded skills.
3. DOWN links (dependents): code → inheritors, importers, covering tests; artifacts → artifacts wikilinking it, skills/agents referencing it; config/rules → loaders.
4. Missing links: UP — implicit dependency with no explicit link/import; DOWN — orphan artifact, missing test, missing rule coverage. For ticket artifacts, `## Links` + frontmatter are authoritative; prose references missing from `## Links` are gaps.

## Output

```
── Artifact Validation: {T} ──                 (structure)
Artifacts present:  [x] {T}-summary.md …
Structure validation: [x] Requirements have testable AC · [x] Plan tasks have done-criteria and effort …
Ready: true | false
Next: fix paths/structure, or proceed to build
```
```
── Artifact Link Verification: {T} ──          (links)
Requirements coverage:  [x] R-1 → Task(s) → Files → Verification · [ ] R-2 (UNFULFILLED)
Task → Progress/Verification:  [x]/[ ] with INCOMPLETE | UNVERIFIED labels
Broken links:  [{n}] {severity}: {description} — {impact} — {fix}
Coverage: Requirements {n}/{total} ({%}) · Tasks {n}/{total} ({%}) · Verification {n}/{total} ({%})
Ready: true | false
```
```
TRACE: {file-path} · Type: code | artifact | config | rule    (trace)
-- UP --  {path} — {relationship}
-- DOWN -- {path} — {relationship}
-- MISSING LINKS -- UP: {…} · DOWN: {…}
```

## Gate

- Not build-ready until requirements + plan pass structure checks with no missing sections; filenames flat `{T}-{artifact}.md`; every artifact ends with `## Links`.
- Bidirectional links must exist both ways; dangling `[[…]]` is broken. **Unfulfilled** requirements and upstream-less tasks are critical. Every task needs ≥1 implementing file/commit and ≥1 verification criterion.
- Report-only — route fixes to `fix` or `evolve`; never edit the inspected files here.

**Version:** 2.0 — absorbed check-artifact-links (scope links) and trace (scope trace) | **Updated:** 2026-08-23
