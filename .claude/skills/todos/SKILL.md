---
name: todos
description: Capture and track miscellaneous tasks, chores, ideas, and follow-ups — optionally tied to a ticket {T}, or fully general. Lighter-weight than bugs and questions; no blocking semantics. Every todo is a CLI-mutated TOML tracker, ticket-scoped ones under the ticket and general ones under the reserved `_shared` scope, so a todo can be moved in or out of a ticket at any time.
---

# /todo

**Usage:**
```
/todo "description"                 # quick-capture general (no ticket)
/todo {T} "description"             # quick-capture scoped to {T}
/todo [{T}] add "description" --type=chore --due=2026-07-10 --priority=medium
/todos [{T}]                        # list general / ticket todos
/todo doing|done TD-3
/todo snooze TD-3 2026-07-15        # push due date, keep open
/todo drop TD-3 "reason"
/todo promote TD-3 {T}              # move general → ticket (or into bugs/questions)
```

**When:** Anytime — stray thought, "come back to this", chore, idea. If it starts blocking or needs an audit trail, `promote` to `bugs`/`questions`.

**Storage (one write path for every todo):**
- Ticket-scoped: `knowledge-center/artifacts/{T}/{T}-todos.toml`
- General: `knowledge-center/artifacts/_shared/_shared-todos.toml` (reserved `_shared` scope)
Both mutated only via `console/kanban.py` (or the console's Todos tab), never hand-edited (see `consolidate/SKILL.md`). Moving a todo in/out of a ticket is a plain remove+add between trackers.

## Steps

1. **Resolve scope** — `{T}` given or inferable → ticket tracker; else `_shared`. Never guess a ticket silently — ask if ambiguous.
2. **Tidy** — silently reword the raw input into one clear sentence; preserve code identifiers/paths verbatim.
3. **Enrich (light)** — one quick grep of vault/codebase; add at most one `Context:` line; never block capture on this.
4. **Quick-capture / add** — `python console/kanban.py tracker add {T|_shared} todos "..." [--set context="..." --set type=... --set priority=... --set due=...]` (defaults: `type=task`, `priority=medium`, no due).
5. **list** — `python console/kanban.py tracker list {T|_shared} todos`; group by status; flag overdue (due past, not done/dropped).
6. **doing / done / drop** — `python console/kanban.py tracker update {T|_shared} todos {id} --set status=<doing|done|dropped> [--set done_on=<today>] [--set drop_reason="..."]`. `drop` requires a one-line reason.
7. **snooze** — `--set due=<date>` only; status unchanged.
8. **promote** — between trackers: remove from source + add to target (the Todos tab's per-row move control does this; id is per-file, so it changes). To `bugs`/`questions`: `tracker add {T} <bugs|questions> "..."`, then set the source todo `dropped` with `--set drop_reason="promoted to <D-n|Qn>"`. Link the new location from the old.

## Types

task (default) · idea · chore · investigate · follow-up · reminder.

## Priority / status

`low · medium (default) · high` — a sort key only, never blocks. Status: `open → doing → done`, or `→ dropped` (with reason).

## Item fields (both trackers)

`id` (`TD-{n}`), `status`, `type`, `priority`, `captured_by`, `captured_on`, `due`, `context`, `text`, `done_on`, `drop_reason`.

## Rules

- Todos never gate a stage — blocking items get promoted to `questions`/`bugs`.
- `{T}-todos.toml` lives at the ticket root next to `ticket.toml`; `_shared/_shared-todos.toml` holds everything else.
- `text` is the tidied wording, not the raw input.
- Never hand-edit any todos tracker — always via `console/kanban.py` or the Todos tab.

**Delegates to:** planner/builder (todo becomes real ticket work → fold into `{T}-plan.md`), `console` (storage/CLI), `bugs`, `questions`.

**Version:** 2.1 — lean rewrite; general todos fully on the `_shared` CLI path | **Updated:** 2026-08-23
