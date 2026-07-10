---
name: questions
description: List, add, answer, resolve, and triage open questions for ticket {T}. Supersedes manage-questions with a richer status/type model and audit trail.
---

# /questions

**Usage:**
```
/questions {T}                    # list / summarize open questions
/questions {T} add "..."          # add a question
/questions {T} answer Q1-1 "..."  # record an answer
/questions {T} resolve Q1-1       # mark resolved
/questions {T} blockers           # show critical blockers only
```

**When:** Any stage — planning, build, or verify — when a decision needs an audit trail.

**Canonical storage:** `knowledge-center/artifacts/{T}/{T}-questions.md` (create from `.claude/skills/questions/template.md` if missing).

## Steps

1. **Load** `{T}-questions.md` if present; otherwise scaffold from the template and continue.
2. **list** — show questions grouped by status (open, answered, resolved, closed); flag critical blockers.
3. **add** — append a new entry with id, type, priority, who raised it, and links to affected artifacts. Auto-increment `Q{n}` from the current max.
4. **answer** — record the answer text and answerer; move to `answered` status.
5. **resolve** — move to `resolved`; require the answer to be reflected in the source artifact (patch it, or note why not).
6. **blockers** — filter to priority `critical` with status not in `resolved`/`closed`.

## Status model

```
open -> answered -> resolved -> closed
```

- `open` — raised, no answer yet.
- `answered` — answer recorded, not yet folded back into the source artifact.
- `resolved` — answer applied to the artifact; decision is final.
- `closed` — question dropped as moot, duplicate, or out of scope.

## Types

design · scope · requirement · blocker · decision · technical · other

## Priority / blocking rule

`low` · `medium` · `high` · `critical`. **Critical** questions must reach `resolved` before the stage they block can advance (see `.claude/skills/clarify/question-templates.md` for the full lifecycle and blocking rules).

## Entry format

```markdown
#### Q{n} [{type}] {short question} — {status}

- **Raised:** {YYYY-MM-DD} | **By:** {user|agent} | **Priority:** {low|medium|high|critical}
- **Affects:** {artifact/file references}
- **Answer:** {answer text, once answered}
- **Resolved:** {YYYY-MM-DD} — {how the artifact was updated, or why not}
```

## Rules

- `.claude/skills/clarify/question-templates.md` — lifecycle, types, and blocking rules (canonical)
- `.claude/skills/project-layout` conventions (or `CLAUDE.md` if no dedicated layout skill) — vault paths and `{T}` conventions
- Never let a stage advance past a gate with `critical` questions still `open`/`answered` (not `resolved`) if they truly block it.
- A `resolved` question without a corresponding artifact patch is just an answer, not a decision — apply it or say why not.

## Delegates to

`clarify` (surfaces assumptions, may create questions), the stage owner (planner/builder/verifier) that the blocking question affects.

**Version:** 2.0-generic | **Updated:** 2026-07-04
