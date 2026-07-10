---
name: criticize
description: Routes adversarial critique to stage-specific challenge skills (requirements, plan, implementation). Use when red-teaming artifacts, challenging a plan, questioning implementation vs plan, or when autonomous dispatch needs critique routing.
---

# /criticize

**Usage:** `/criticize [T] [stage]` — `[T]` ticket id (optional if context clear), `[stage]` one of `requirements` | `plan` | `implementation` | `all`.

**When:** Free-form "find issues", "red-team", or "critique" requests, or an ambiguous challenge ask. Prefer the explicit stage skill (e.g. `challenge-plan`) when the stage is already known.

## Stage routing

| `stage` | Delegates to | Default when |
|---------|--------------|--------------|
| `requirements` | `challenge-requirements {T}` | Draft not yet frozen |
| `plan` | `challenge-plan {T}` | Requirements frozen; planning artifacts exist |
| `implementation` | `challenge-implementation {T} [slice]` | Post-build, pre-verify |
| `all` | Run applicable stages in order; skip empty | Explicit or full-ticket audit |

**Auto-detect** (when `[stage]` omitted):

1. `{T}-requirements.md` exists and is not frozen → `requirements`
2. `{T}-plan.md` exists and no build is in progress → `plan`
3. Code changes exist for `{T}` → `implementation`
4. Otherwise → ask once for stage

## Steps

1. Ensure `{T}-critique-report.md` exists (scaffold if missing).
2. Load `.claude/skills/challenge-standards/rules.md`.
3. Delegate to the stage skill(s); do not duplicate their walk logic here.
4. Aggregate results into one report block.

## Output

```
── /criticize ──
Ticket:    {T}
Stage:     {stage}
Dispatch:  criticize → challenge-{stage}
Findings:  {N} total (critical {c} / major {m} / minor {n})
Report:    knowledge-center/artifacts/{T}/{T}-critique-report.md
Gate:      clear | blocked — {N} critical unresolved
Next:      {stage-specific repair command}
```

## Rules

- `.claude/skills/challenge-standards/rules.md` — finding format, severity, and kinds (canonical, shared)
- `.claude/skills/challenge-requirements/SKILL.md` — requirements delegate
- `.claude/skills/challenge-plan/SKILL.md` — plan delegate
- `.claude/skills/challenge-implementation/SKILL.md` — implementation delegate
- This skill is a router only — it never performs the walk itself.

**Delegates to:** analyst (requirements), planner (plan), verifier (implementation).

**Version:** 1.0-generic | **Updated:** 2026-07-04
