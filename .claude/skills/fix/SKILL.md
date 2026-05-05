---
name: fix
description: Root-cause and minimal patch for a failing test, broken build, or unmet acceptance criterion. Use whenever verifier reports a block or progress.md logs a blocker. Codifies the fixer protocol so any agent can invoke it.
---

# Inputs
- `id` (required): ticket id
- `symptom` (required): exact failing signal (test name + output, error trace, criterion id)

# Steps
1. Reproduce: run the failing check; capture exact output.
2. Locate: trace from symptom to first failing line; cite file:line.
3. Diagnose: identify root cause. Reject any explanation that requires `--no-verify`, exception swallow, or mock-to-pass.
4. Patch: smallest change that fixes the cause. No surrounding cleanup.
5. Re-run the failing check; confirm green.
6. `progress-tracker` entry: Symptom / Cause / Fix / Verification (one line each).
7. If fix implies a design shift, run `evolve(target=plan or requirements)` with reason.

# Output
Path of patched file(s) + before/after of the failing check.

# Rules
- No fix without reproduction.
- No suppression to make CI pass.
- If the fix expands scope, stop and route to planner instead of expanding silently.
