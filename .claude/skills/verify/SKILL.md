---
name: verify
description: Verifies implementation against acceptance criteria via scoped unit, integration, e2e, review, or ready checks, and designs the traceable test-case artifact (scope cases — unit/integration/e2e/negative/boundary/edge with AC traceability) that the other scopes consume. Use /verify {T} [scope] after slice implementation, before merge, or with scope cases after requirements freeze to produce {T}-test-cases.md.
---

# /verify

**When:** After slice implementation or before merge — `/verify {T} [scope]`; `scope cases` runs after requirements freeze (before/during verification) to produce the test plan.
**Order:** `challenge-implementation` first (adversarial pass); unit/integration/e2e scopes verify against `{T}-test-cases.md` (scope `cases` produces it).
**Scope default** (per `harness-standards` test policy): routine mid-slice → `review`; merge/release gate → `ready`; explicit scope always honored, incl. `all`. Never silently escalate to `all`.

## Scopes

| Scope | Checks |
|-------|--------|
| `cases` | Design the test-case artifact from requirements/stories (below) |
| `unit` | Isolated component/unit logic per the test-case artifact |
| `integration` | Component-to-component interactions, real dependencies |
| `e2e` | Full user/consumer workflows end-to-end |
| `review` | Structured code review by changed surface, severity-graded |
| `ready` | Pre-release audit — all of the above plus security and performance |
| `all` | All applicable scopes in sequence — explicit only |

## Steps — run scopes (unit/integration/e2e/review/ready/all)

1. Resolve `{T}`; for unit/integration/e2e/ready load `{T}-test-cases.md` — run scope `cases` first if missing or stale vs current AC; verify against `TC-U/I/E/N/B/X-*` ids.
2. Resolve the target project; read its own CLAUDE.md for actual build/test commands — never invent a framework/runner/naming convention. Nested repo → `invoke-project-skill`.
3. Run the project's own build + test suite for the requested scope; capture pass/fail counts and coverage if reported.
4. `review`/`ready`: walk changed files by surface (data / API-service / UI / config — whatever the diff touches); grade issues by severity.
5. Classify every failure — **fixable**: typos, missing guards, style within policy, missing selector the AC implies, assertion mismatch after documented behavior change, artifact link/metadata drift. **Blocker**: spec vs implementation conflict, architecture/contract change needing sign-off, green-forcing change, scope creep/missing requirements.
6. Write `{T}-verification.md` — criterion, status, evidence. Emit the output contract.

## Steps — scope cases (design the test plan)

1. Load `{T}-requirements.md` (AC) and, if present, `{T}-user-stories.md` / `{T}-components.md` for surfaces in scope (`/verify {T} cases [slice]`).
2. Per AC derive ≥1 positive case, plus negative/boundary/edge where the criterion implies validation, thresholds, concurrency, or real-world consequences (money, access control, irreversible actions). Layer: unit `TC-U-*` · integration `TC-I-*` · e2e `TC-E-*` · negative/boundary/edge `TC-N/B/X-*`.
3. Traceability matrix: every AC → case ids; uncovered ACs flagged as gaps, never dropped silently.
4. Test data: seed/cleanup per scenario; reference reusable setup scripts by path; scripts dev-only, idempotent, never destructive against real/shared data.
5. Write from `.claude/skills/verify/test-cases-template.md` to `{T}-test-cases.md`; link from `{T}-summary.md`/artifact map.

**Case ids:** `TC-{layer}-{NNN}` (`U/I/E/N/B/X`), sequential within layer, stable — append on revision, never renumber. Each row: scenario, expected result, type, priority (P0 must pass before merge / P1 / P2), test-data ref. Unit rows follow the target project's own test-naming convention.

## Output

`{T}-verification.md` (criterion / status / evidence) — or `{T}-test-cases.md` for scope cases.

```
── Verification: {T} ──
Scope: {scope}
Tests: {total}/{passing}/{coverage or n/a}
Issues: {count} ({fixable} auto-fixed, {blockers} blocking)
Quality: {grade A/B/C/F}
Blockers: {list, or none}
Status: done | needs review | blocked
```
```
── Verification (cases): {T} ──
Cases:    U {n} · I {n} · E {n} · N/B/X {n}  (total {N})
Coverage: {mapped}/{total} ACs ({%}) | gaps: {list | none}
Priority: P0 {n} · P1 {n} · P2 {n}
Next:     verify {T} {scope}
```

## Gate

- All blockers resolved before merge. Fixable → `fix` (bounded file set, re-run the failing check); blocker → mitigation plan, escalate to `evolve`/re-plan — never weaken a check to pass it.
- Static-only verification must be labeled as such (code verified, feature not exercised).

**Delegates to:** `fix`, planner/`evolve`, `invoke-project-skill`.

**Version:** 3.0 — absorbed generate-test-cases as scope cases | **Updated:** 2026-08-23
