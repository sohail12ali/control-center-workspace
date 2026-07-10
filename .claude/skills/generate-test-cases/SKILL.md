---
name: generate-test-cases
description: Generate a traceable test-case artifact (unit, integration, e2e, negative/boundary/edge) from a ticket's requirements and acceptance criteria. Use after requirements/stories are frozen, before or during verification.
---

# /generate-test-cases

**Usage:** `/generate-test-cases [T] [slice]` — `[T]` ticket id (optional if context clear), `[slice]` optional slice/task-group id (omit for all in-scope requirements).

**When:** After requirements are frozen (and stories extracted, if the ticket uses that richer pipeline), before or during `verify`. The verifier consumes this artifact as its test plan.

**Authority:** Test scope definitions, review policy, and delegation to the target project's own test framework live in `.claude/skills/verify/SKILL.md`. This skill **designs** test cases only — it does not run any test suite and does not redefine those rules.

## Steps

1. Load `{T}-requirements.md` (acceptance criteria) and, if present, `{T}-user-stories.md` / `{T}-component-breakdown.md` for surfaces in scope.
2. For every acceptance criterion, derive at least one positive case, plus negative/boundary/edge cases where the criterion implies validation, thresholds, concurrency, or anything with real-world consequences (money, access control, irreversible actions). Choose the test layer by surface:
   - Isolated logic → **unit** (`TC-U-*`)
   - Cross-component/service/data-layer interaction → **integration** (`TC-I-*`)
   - Full user/consumer-facing workflow → **e2e** (`TC-E-*`)
   - Risk class (validation/limits/race conditions) → **negative/boundary/edge** (`TC-N/B/X-*`)
3. Build a traceability matrix: every acceptance criterion → test case IDs; flag any with no coverage as a gap.
4. Specify test data: seed/cleanup per scenario. Reference reusable setup scripts by path rather than inlining large fixtures.
5. Write the artifact from `.claude/skills/generate-test-cases/template.md` to `{T}-test-cases.md`; link it from `{T}-summary.md` / artifact map.

## Test case ID convention

`TC-{layer}-{NNN}` — `U` unit · `I` integration · `E` e2e · `N` negative · `B` boundary · `X` edge. Number sequentially within layer (`TC-U-001`). IDs are stable — never renumber on revision, only append.

Each row carries: scenario, expected result, type (positive/negative/boundary/edge), priority (P0/P1/P2), test data reference. Unit rows also name the unit under test using whatever naming convention the target project's own test suite already follows — don't invent one.

## Output

**Template:** `.claude/skills/generate-test-cases/template.md`
**Path:** `knowledge-center/artifacts/{T}/{T}-test-cases.md`

**Acceptance criteria for this skill's output:**
- Every acceptance criterion maps to ≥1 test case (gaps explicitly flagged, never silently dropped).
- Negative + boundary cases present for validation, access-control, irreversible-action, or threshold logic.
- Test data and cleanup specified per scenario — no destructive scripts against real/shared data.
- Priorities assigned (P0 = must-pass before merge).
- Summary counts and coverage % filled in.
- `## Links` block complete.

## Output contract

```
── /generate-test-cases: {T} ──
Slice:    {slice | all}
File:     knowledge-center/artifacts/{T}/{T}-test-cases.md
Cases:    U {n} · I {n} · E {n} · N/B/X {n}  (total {N})
Coverage: {mapped}/{total} ACs ({%}) | gaps: {list | none}
Priority: P0 {n} · P1 {n} · P2 {n}
Status:   written | AC gaps — review
Next:     verify {T} {scope}
```

## Rules

- Design, don't execute — running any test suite is `verify`'s job, not this skill's.
- An acceptance criterion with no test case is a coverage gap, surfaced in the matrix and the output contract — never dropped silently.
- Risk-weighted depth: validation, access control, money, or irreversible actions always get negative + boundary cases; read-only/display logic gets lighter coverage.
- Stable IDs — append new cases on revision; never renumber existing ones.
- No destructive seed data against shared/prod-like environments; setup scripts are dev-only, idempotent where possible, with cleanup.

**Delegates to:** `verify` (consumes the artifact), `invoke-project-skill` (framework-specific test scaffolding in a nested repo).

**Version:** 2.0-generic | **Updated:** 2026-07-04
