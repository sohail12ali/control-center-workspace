---
name: verify
description: Verifies implementation against acceptance criteria via scoped unit, integration, e2e, review, or ready checks. Use with /verify {T} [scope] after slice implementation or before merge.
---

# /verify

**Usage:** `/verify [T] [scope]` — `[T]` ticket id (optional if context clear), `[scope]` one of the scopes below.

**When:** After slice implementation, to validate quality and completeness before merge.

**Choosing the default scope (per `harness-standards` test policy — don't run a full/slow suite for routine work):**
- No `[scope]` given, routine mid-slice check → default to **`review`** only (fastest reliable signal for "did this change look right").
- No `[scope]` given, but the calling context is a merge/release gate (e.g. `close-work`'s pre-close check, or the user says "ready to merge") → default to **`ready`**.
- `[scope]` explicitly given → always honor it, including `all`.
- Never silently escalate to `all` "to be safe" — that's the harness-standards violation this rule exists to prevent. If unsure which the caller wants, ask instead of guessing wide.

**Test plan input:** unit/integration/e2e scopes verify against `{T}-test-cases.md` (produced by `generate-test-cases`). If absent or stale vs. current acceptance criteria, generate it first, then verify against case IDs `TC-U/I/E/N/B/X-*`.

## Scopes

| Scope | Checks |
|-------|--------|
| `unit` | Isolated component/unit logic per the test-case artifact |
| `integration` | Component-to-component interactions, real dependencies |
| `e2e` | Full user/consumer workflows end-to-end |
| `review` | Structured code review by changed surface, severity-graded |
| `ready` | Pre-release audit — all of the above plus security and performance |
| `all` | Run all applicable scopes in sequence — explicit only, see default-scope rule above |

**Delegate test-framework specifics to the target project's own CLAUDE.md.** This skill does not run any particular build tool or test runner by name — resolve the target project (via `invoke-project-skill` when the ticket is in a nested repo), then:
- Run the project's own build command.
- Run the project's own test suite for the scope in play (unit/integration/e2e as the project defines it).
- Follow the project's own test-naming and structure conventions — do not impose a naming scheme this skill invented.

## Steps

1. Resolve `{T}` and load `{T}-test-cases.md` if the scope needs it (unit/integration/e2e/ready). Generate it first if missing or stale.
2. Resolve the target project. If nested, delegate the build/test invocation via `invoke-project-skill`; read that project's CLAUDE.md for its actual commands first.
3. Run the checks for the requested scope; capture pass/fail counts and coverage if the project's tooling reports it.
4. For `review`/`ready`, walk changed files by surface (data layer, API/service layer, UI, config/scripts — whatever surfaces the diff touches) and grade issues by severity.
5. Classify every failure or finding as **fixable** or **blocker** (see table below).
6. Write results to `{T}-verification.md` (or the ticket's equivalent) — criterion, status, evidence.
7. Emit the output contract.

## Fixable vs blocker

| Fixable | Blocker |
|---------|---------|
| Typos, missing null/guard checks, style/lint within policy | Spec vs. implementation conflict |
| Missing selector/identifier the AC already implies | Architecture or contract change needing sign-off |
| Test assertion mismatch after an intentional, documented behavior change | Change made only to force an unrelated check green |
| Artifact link or metadata drift | Scope creep or missing requirements |

**Fixable** → handoff to `fix` (small, bounded surface; re-run the failing check after).
**Blocker** → report with a mitigation plan; escalate to the planning stage (`evolve` / re-plan) — do not weaken a check to pass it.

## Verification checklist

```
Verification: {T} — scope: {scope}
- [ ] Acceptance criteria traced to code or tests
- [ ] Project's own build command run (touched surfaces)
- [ ] Project's own test suite run for the requested scope
- [ ] Code review surfaces covered (data / API / UI / security as applicable)
- [ ] Each failure classified: fixable vs blocker
- [ ] Fixable → fix handoff; re-run failed checks
- [ ] Blocker → user + evolve/re-plan; no check weakened to pass
- [ ] Output contract filled
```

## Output

```
── Verification: {T} ──
Scope: {scope}
Tests: {total}/{passing}/{coverage or n/a}
Issues: {count} ({fixable} auto-fixed, {blockers} blocking)
Quality: {grade A/B/C/F}
Blockers: {list, or none}
Status: done | needs review | blocked
```

## Rules

- Required checks (when in scope): unit validates acceptance criteria, integration validates component interactions, e2e validates user workflows if a UI/consumer surface is in scope, review validates standards.
- All blockers resolved before merge.
- Fixable issues may be auto-repaired only within a small, bounded file set — otherwise route to the planning stage.
- Never invent or assume a stack's test framework, naming convention, or tooling — read the target project's own CLAUDE.md / testing docs first.

**Delegates to:** `fix` (fixable issues), planner/`evolve` (blockers), `invoke-project-skill` (nested repo build/test), `generate-test-cases` (missing/stale test plan).

**Version:** 2.0-generic | **Updated:** 2026-07-04
