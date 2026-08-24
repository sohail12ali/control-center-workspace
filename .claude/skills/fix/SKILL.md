---
name: fix
description: Root-cause and minimal patch for a failing test, broken build, or unmet acceptance criterion. Use whenever verifier reports a block or progress.md logs a blocker. Codifies the fixer protocol so any agent can invoke it.
---

# /fix

**When:** Verifier reports a block, a test/build fails, or progress.md logs a blocker — any agent may invoke.

**Inputs:** `id` (required, ticket id); `symptom` (required — exact failing signal: test name + output, error trace, criterion id).

## Steps

1. Reproduce: run the failing check; capture exact output. No fix without reproduction.
2. Locate: trace from symptom to first failing line; cite file:line.
3. Diagnose: identify root cause. Reject any explanation that requires `--no-verify`, exception swallow, or mock-to-pass.
4. Patch: smallest change that fixes the cause. No surrounding cleanup. Scope bound: 1-3 files, depth ≤2, timebox ~5 min — beyond that, stop and route to planner.
5. Re-run the failing check; confirm green. Add/update a validating test that locks the fix (skip only if the failing check itself is that test).
6. `progress-tracker` entry: Symptom / Cause / Fix / Verification (one line each).
7. If the fix implies a design shift, run `evolve(target=plan or requirements)` with reason.

## Output

Path of patched file(s) + before/after of the failing check.

## Gate

- No suppression to make CI pass.
- If the fix expands scope, stop and route to planner — never expand silently.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
