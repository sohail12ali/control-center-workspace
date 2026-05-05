---
name: handoff
description: Formal stage transition with a gating checklist. Used by harness between specialists. Refuses to advance if gate items fail.
---

# Inputs
- `id` (required): ticket id
- `from`, `to` (required): stage names — `GROUND`, `CLARIFY`, `CANONICAL`, `TEMPLATE`, `SIMPLIFY`, `VERIFY`, `CLOSE`

# Gate matrix
| from → to | Required |
|---|---|
| GROUND → CLARIFY | analysis.md exists; recommended path stated |
| CLARIFY → CANONICAL | requirements.md frozen; no `open` Qs blocking; validate(requirements) clean |
| CANONICAL → TEMPLATE | plan.md has Approach + Tasks; validate(plan) clean; effort sums match |
| TEMPLATE → SIMPLIFY | all plan tasks `[x]`; progress.md current |
| SIMPLIFY → VERIFY | simplify run on changed files; no new TODOs |
| VERIFY → CLOSE | verification.md filled; every criterion has evidence; validate(verification) clean |

# Steps
1. Run the matrix row for `from→to`.
2. For each fail item, return `block: <item>` with the missing artifact/skill.
3. If all pass, append to `progress.md`: `Stage: {from} → {to}`, update `summary.md` Status.

# Output
`pass` or list of blocks with remediation skill calls.

# Rules
- Never bypass with a flag. If a gate is wrong, fix the matrix, not the bypass.
- Skipping a stage requires an explicit `decision-log.md` entry.
