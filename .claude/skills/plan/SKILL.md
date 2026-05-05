---
name: plan
description: CANONICAL stage — strategy and structure. Decides approach, slices, layers, risks. Writes the Approach/Slices/Risks sections of plan.md. Pairs with `plan-effort` (which adds task-level decomposition and estimates).
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read frozen `requirements.md`, `analysis.md`, `decision-log.md`.
2. Decide approach: 3-5 line rationale tying chosen path to constraints/decisions.
3. Decide structure:
   - Single-layer: flat task list (handed to `plan-effort`)
   - Multi-layer: `SLICE → PHASE-{ENTITIES|DB|API|UI}` tree; create subdirs from `_template`
4. Pull risks from analysis + decision-log; rate likelihood × impact (`risk-scan` if ≥3 risks).
5. Write plan.md sections: Approach / Slices / Risks. Leave Tasks/Effort empty for `plan-effort`.
6. Hand off to `plan-effort` for task decomposition.

# Output
Path to plan.md (strategy filled, tasks pending) and recommended structure (flat vs sliced).

# Rules
- Don't decompose tasks here; that's `plan-effort`.
- Approach must reference at least one decision-log entry or analysis finding.
- If multiple viable approaches, run `clarify` instead of guessing.
