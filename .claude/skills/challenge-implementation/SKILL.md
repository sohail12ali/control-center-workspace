---
name: challenge-implementation
description: Red-team implemented code against plan and requirements. Find plan drift and spec gaps before formal verify. Use when questioning implementation vs plan or for a post-build adversarial review.
---

# /challenge-implementation

**When:** After a slice's build completes; re-run after significant `fix` or `evolve` on the same slice — `/challenge-implementation [T] [slice]`.

**Order:** Before `verify review`. This pass is intent-vs-reality and plan traceability — executable checks, style/lint review, and merge sign-off stay with `verify`.

## Steps

1. Ensure `{T}-critique-report.md` exists (scaffold if missing — shared with `challenge-requirements`/`challenge-plan`).
2. Load `.claude/skills/challenge-standards/rules.md` for finding format and severity.
3. Read `{T}-plan.md`, `{T}-requirements.md`, `{T}-test-cases.md` (if present), `{T}-progress.md`.
4. Diff the ticket's branch against its base; intersect with slice tasks when `[slice]` is supplied.
5. Walk the diff; assign `CR-{n}` finding IDs per category: **plan-drift** (code ≠ task AC/component contract), **incomplete-slice** (tasks marked done but files/changes missing), **spec-gap** (required behavior absent from code), **error-handling** (happy-path only where AC requires failure paths), **test-gap** (AC with no test case/coverage plan), **security-risk** (plausible injection, secret exposure, auth bypass — escalate to `verify` if confirmed), **operational-risk** (missing transaction boundary, idempotency, concurrency handling).
6. Write findings to `{T}-critique-report.md` § Implementation critique; update summary counts and last-run date; append a resolution-log row.
7. Confirmed defects: optionally stub a `D-{n}` entry via `console/kanban.py tracker add {T} bugs "..." --set severity=<guess>` (`{T}-bugs.toml`; severity guess per `.claude/skills/bugs/SKILL.md`).
8. Findings only — no code edits. Every finding traced to a plan task, user story, or requirement; changed files in scope read or explicitly skipped with a stated reason.

## Output

`{T}-critique-report.md` § Implementation critique, plus:

```
── /challenge-implementation ──
Ticket:    {T}
Slice:     {slice | all}
Findings:  {N} total (critical {c} / major {m} / minor {n})
  plan-drift:        {n}
  incomplete-slice:  {n}
  spec-gap:          {n}
  error-handling:    {n}
  test-gap:          {n}
  security-risk:     {n}
  operational-risk:  {n}
Report:    {T}-critique-report.md § Implementation critique
Gate:      clear | blocked — {c} critical
Next:      verify {T} review | fix {T} | evolve {T}
```

## Gate

Critical findings block (`blocked — {c} critical`) until resolved via `fix`/`evolve`; otherwise clear → `verify {T} review`.

## Rules

- `.claude/skills/challenge-standards/rules.md` — finding format and severity (shared across challenge-*)
- `.claude/skills/verify/SKILL.md` — executable checks and merge sign-off
- `.claude/skills/bugs/SKILL.md` — defect stub format

**Delegates to:** verifier (confirmed security-risk findings), fixer (confirmed defects).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
