# Question Templates and Open-Question Lifecycle

Canonical for the open-question lifecycle used by `clarify` and `questions`.

## Storage

All questions for ticket `{T}` live in `knowledge-center/artifacts/{T}/{T}-questions.md`. Create from `.claude/skills/questions/template.md` if missing.

## Slash command

Use `questions` for list / add / answer / resolve / blockers. `clarify` surfaces assumptions and may create questions here.

## Status model

```
open -> answered -> resolved -> closed
```

Critical blockers must be `resolved` before a stage that they truly gate can advance.

## Types

design · scope · requirement · blocker · decision · technical · other

## Rules of thumb

1. Write a question to `{T}-questions.md` when ambiguity blocks a stage or the decision needs an audit trail.
2. Link to affected artifacts (`{T}-requirements.md`, `{T}-plan.md`, code paths).
3. Keep the harness gate policy (CLARIFY, communication norms) in `.claude/skills/harness-standards/` as the single behavior source — this file is storage + lifecycle only.

## Structured questions pattern

- One assumption per number — atomic, answerable without a follow-up when possible.
- Prefer closed choices when options are known: `A) ... B) ... C) other (specify)`.
- Group by domain when the count exceeds 5 (e.g. Scope, Data, API, UI, Release), with sub-numbering only if needed.
- No speculation in questions — ask what is unknown; do not embed a preferred answer.
- If the user gave verbatim policy text, preserve it when logging to `{T}-questions.md`.

## Continuation rule

**Pending questions** = unresolved items in `{T}-questions.md` (`open`/`answered`, or `critical` and not `resolved`) or any CLARIFY-stage item still needing a decision.

- If pending questions exist: stop and resolve with the user (or via `questions`) before advancing past the gate they affect.
- If none are pending: continue without stopping for optional review checkpoints.
