---
name: handoff
description: Formal stage transition with a gating checklist. Used by harness between specialists. Refuses to advance if gate items fail.
---

# /handoff

**When:** Every stage transition — used by harness between specialists; nothing advances a stage without it.

**Inputs:** `id` (required, ticket id); `from`, `to` (required): `GROUND` | `CLARIFY` | `CANONICAL` | `TEMPLATE` | `SIMPLIFY` | `VERIFY` | `CLOSE`.

## Gate matrix

| from → to | Required |
|---|---|
| GROUND → CLARIFY | analysis.md exists; recommended path stated |
| CLARIFY → CANONICAL | requirements.md frozen (`requirements freeze` passed); no `open`/`critical` Qs blocking; `challenge-requirements` clean |
| CANONICAL → TEMPLATE | plan.md has Approach + Tasks; `challenge-plan` clean; effort sums match |
| TEMPLATE → SIMPLIFY | all plan tasks `[x]`; progress.md current |
| SIMPLIFY → VERIFY | simplify run on changed files; no new TODOs |
| VERIFY → CLOSE | verification.md filled; every criterion has evidence; `verify` (scope=ready) and `validate-artifacts` clean |

## Steps

1. Run the matrix row for `from→to`.
2. For each fail item, return `block: <item>` with the missing artifact/skill.
3. If all pass, append to `progress.md`: `Stage: {from} → {to}`; update `summary.md` Status.

## Output

`pass` or list of blocks with remediation skill calls.

## Gate

- Refuses to advance while any matrix item fails. Never bypass with a flag — if a gate is wrong, fix the matrix, not the bypass.
- Skipping a stage requires an explicit `decision-log.md` entry.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
