---
name: criticize
description: Routes adversarial critique to stage-specific challenge skills (requirements, plan, implementation). Use when red-teaming artifacts, challenging a plan, questioning implementation vs plan, or when autonomous dispatch needs critique routing.
---

# /criticize

**When:** Free-form "find issues" / "red-team" / "critique" requests, or an ambiguous challenge ask — `/criticize [T] [stage]`, stage ∈ `requirements` | `plan` | `implementation` | `all`. Prefer the explicit stage skill (e.g. `challenge-plan`) when the stage is already known.

**Order:** Router only — dispatches to `challenge-requirements` / `challenge-plan` / `challenge-implementation`; never performs the walk itself.

## Stage routing

| `stage` | Delegates to | Default when |
|---------|--------------|--------------|
| `requirements` | `challenge-requirements {T}` | Draft not yet frozen |
| `plan` | `challenge-plan {T}` | Requirements frozen; planning artifacts exist |
| `implementation` | `challenge-implementation {T} [slice]` | Post-build, pre-verify |
| `all` | Run applicable stages in order; skip empty | Explicit or full-ticket audit |

**Auto-detect** when `[stage]` omitted: `{T}-requirements.md` exists unfrozen → `requirements`; `{T}-plan.md` exists and no build in progress → `plan`; code changes exist for `{T}` → `implementation`; otherwise ask once.

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

## Gate

`blocked — {N} critical unresolved` until critical findings resolve; otherwise clear.

## Rules

- `.claude/skills/challenge-standards/rules.md` — finding format, severity, kinds (canonical, shared)
- Stage delegates: `.claude/skills/challenge-requirements/SKILL.md`, `.claude/skills/challenge-plan/SKILL.md`, `.claude/skills/challenge-implementation/SKILL.md`

**Delegates to:** analyst (requirements), planner (plan), verifier (implementation).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
