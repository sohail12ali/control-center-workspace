---
name: challenge-implementation
description: Red-team implemented code against plan and requirements. Find plan drift and spec gaps before formal verify. Use when questioning implementation vs plan or for a post-build adversarial review.
---

# /challenge-implementation

**Usage:** `/challenge-implementation [T] [slice]` — `[T]` ticket id (optional if context clear), `[slice]` optional slice/task-group id.

**When:** After a slice's build completes and before `verify review`. Re-run after significant `fix` or `evolve` on the same slice.

## Steps

1. Ensure `{T}-critique-report.md` exists (scaffold if missing — shared with `challenge-requirements` / `challenge-plan`).
2. Load `.claude/skills/challenge-standards/rules.md` for finding format and severity.
3. Read scope artifacts: `{T}-plan.md`, `{T}-requirements.md`, `{T}-test-cases.md` (if present), `{T}-progress.md`.
4. Gather code scope: diff the ticket's branch against its base; intersect with slice tasks when `[slice]` is supplied.
5. Walk the diff and assign `CR-{n}` finding IDs per category:
   - **plan-drift** — code does not match a task's acceptance criteria or component contract
   - **incomplete-slice** — tasks marked done but files/changes are missing
   - **spec-gap** — behavior implied by requirements not reflected in code
   - **error-handling** — happy-path only where the AC requires failure paths
   - **test-gap** — AC with no test case or coverage plan
   - **security-risk** — plausible injection, secret exposure, or auth bypass (escalate to `verify` if confirmed)
   - **operational-risk** — missing transaction boundary, idempotency, or concurrency handling
6. Write findings to `{T}-critique-report.md` § Implementation critique; update summary counts and last-run date.
7. For confirmed defects, optionally stub a `D-{n}` entry in `{T}-open-bugs.md` (severity guess per `.claude/skills/bugs/SKILL.md`).
8. Append a row to the critique report's resolution log.
9. Do not duplicate full `verify review` checklists — this pass is about intent vs. reality and plan traceability, not exhaustive style/lint review.

## Acceptance criteria

- Changed files in scope read, or explicitly skipped with a stated reason.
- Every finding traced to a plan task, user story, or requirement pointer.
- No silent code edits — this skill only produces findings.
- Security-risk findings flagged for `verify` follow-up.

## Output

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

## Rules

- `.claude/skills/challenge-standards/rules.md` — finding format and severity (shared across the challenge-* family)
- `.claude/skills/verify/SKILL.md` — defer executable checks and merge sign-off to verify
- `.claude/skills/bugs/SKILL.md` — defect stub format

**Delegates to:** verifier (confirmed security-risk findings), fixer (confirmed defects).

**Version:** 1.0-generic | **Updated:** 2026-07-04
