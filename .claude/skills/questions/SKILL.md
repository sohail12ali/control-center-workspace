---
name: questions
description: List, add, answer, resolve, and triage open questions for ticket {T}. Backed by the Delivery Console's CLI-mutated TOML tracker, not hand-edited markdown.
---

# /questions

**Usage:**
```
/questions {T}                    # list / summarize open questions
/questions {T} add "..."          # add a question
/questions {T} answer Q1 "..."    # record an answer
/questions {T} resolve Q1         # mark resolved
/questions {T} blockers           # show critical blockers only
```

**When:** Any stage when a decision needs an audit trail.

**Storage:** `knowledge-center/artifacts/{T}/{T}-questions.toml` — mutated only via `console/kanban.py`, never hand-edited (see `consolidate/SKILL.md`).

## Steps

1. **list** — `python console/kanban.py tracker list {T} questions`; group by status; flag critical blockers.
2. **add** — `python console/kanban.py tracker add {T} questions "..." --set type=<type> --set priority=<priority> --set raised_by=<user|agent>`. CLI auto-increments `Q{n}`, fills `raised_on`.
3. **answer** — `python console/kanban.py tracker update {T} questions {id} --set status=answered --set answer="..."`.
4. **resolve** — `python console/kanban.py tracker update {T} questions {id} --set status=resolved --set resolved_on=<today>`; the answer must be reflected in the source artifact first (patch it, or note why not).
5. **blockers** — `python console/kanban.py tracker blockers {T}`, read the `questions` key.

## Status model

`open → answered → resolved → closed` — open: no answer yet · answered: recorded, not yet folded into the source artifact · resolved: applied, decision final · closed: moot/duplicate/out of scope.

## Types / priority

Types: design · scope · requirement · blocker · decision · technical · other.
Priority: `low · medium · high · critical`. **Critical** questions must reach `resolved` before the stage they block advances. Full lifecycle + blocking rules (canonical): `.claude/skills/clarify/question-templates.md`.

## Item fields (`{T}-questions.toml`)

`id` (`Q{n}`), `status`, `type`, `priority`, `raised_by`, `raised_on`, `affects`, `text`, `answer`, `resolved_on`.

## Rules

- Never advance a gate with `critical` questions still `open`/`answered`.
- A `resolved` question without an artifact patch is just an answer — apply it or say why not.
- Never hand-edit `{T}-questions.toml` — always via `console/kanban.py`.

**Delegates to:** `console` (storage/CLI), `clarify`, the stage owner the question blocks.

**Version:** 3.1 — lean rewrite | **Updated:** 2026-08-23
