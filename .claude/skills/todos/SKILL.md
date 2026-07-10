---
name: todos
description: Capture and track miscellaneous tasks, chores, ideas, and follow-ups — optionally tied to a ticket {T}, or fully general. Lighter-weight than bugs and questions; no blocking semantics.
---

# /todo

**Usage:**
```
/todo "description"                          # quick-capture a general todo (no ticket)
/todo {T} "description"                      # quick-capture a todo scoped to ticket {T}
/todo add "description" --type=chore --due=2026-07-10 --priority=medium
/todo {T} add "description" --type=idea
/todos                                        # list all general todos
/todos {T}                                    # list todos for ticket {T}
/todo doing TD-3                              # mark TD-3 in progress
/todo done TD-3                               # mark TD-3 done
/todo snooze TD-3 2026-07-15                  # push due date, keep open
/todo drop TD-3 "reason"                      # won't do
/todo promote TD-3 {T}                        # escalate a general todo into a ticket-scoped one (or into bugs/questions)
```

**When:** Anytime — a stray thought mid-build, a "come back to this" during review, a chore not worth its own ticket, an idea worth not losing. If it turns out to block progress or need an audit trail, `promote` it to `bugs` or `questions` instead.

**Canonical storage:**
- Ticket-scoped: `knowledge-center/artifacts/{T}/{T}-open-todos.md`
- General (no ticket): `knowledge-center/artifacts/_shared/general-todos.md`

Both use the same layout; the general file omits `{T}` from frontmatter and title.

## Steps

1. **Resolve target** — if `{T}` is given (or inferable from current context), use the ticket file; otherwise use the general file. Never guess a ticket silently — ask if ambiguous.
2. **Load** the target file if present; scaffold a minimal frontmatter block if missing.
3. **Tidy** — silently clean up spelling/grammar and reword the raw input into one clear sentence. Preserve code identifiers and paths verbatim. Skip silently if already clean.
4. **Enrich (light touch)** — one quick, targeted lookup (grep the vault and, if a file/ticket is named or inferable, the relevant codebase). Add at most one `Context:` line if something relevant turns up; skip if nothing surfaces quickly — never block capture on this.
5. **Quick-capture** — append a `TD-{n}` entry with `type=task`, `priority=medium`, no due date.
6. **add** — same as quick-capture but accepts `--type`, `--priority`, `--due` flags.
7. **list** — group by status (open, doing, done, dropped); flag overdue items (due date past, status not done/dropped).
8. **doing / done / drop** — update status; `drop` requires a one-line reason.
9. **snooze** — update the due date only; status unchanged.
10. **promote** — move the entry into `{T}-open-todos.md` (from general), or hand off to `bugs add` / `questions add` if it turns out to be a defect or a decision needing an audit trail. Remove from the source file and link to the new location.

## Type taxonomy

| Type | Meaning |
|------|---------|
| task | Default — a discrete piece of work |
| idea | Worth exploring later, not yet scoped |
| chore | Small maintenance/cleanup |
| investigate | Needs a spike before it's actionable |
| follow-up | Circle back after something else lands (link it) |
| reminder | Time-boxed nudge, often has a due date |

Default type when unspecified: **task**.

## Priority (soft, not a release gate)

`low` · `medium` (default) · `high`. Priority is a sort key only — it never blocks anything. If an item needs real blocking semantics, `promote` it to `questions` (decision) or `bugs` (defect).

## Status lifecycle

```
open -> doing -> done
  |
  -> dropped   (won't do — record reason)
```

## Entry format

```markdown
#### TD-{n} [{type}] {short description} — {status}

- **Captured:** {YYYY-MM-DD} | **By:** {user|agent} | **Priority:** {low|medium|high}
- **Due:** {YYYY-MM-DD or —} | **Links:** {optional file/artifact references}
- **Context:** {optional one-line auto-enrichment}
- **Done:** {YYYY-MM-DD} — {optional closing note}
```

Minimal quick-capture form: `#### TD-{n} [task] {short description} — open`. Omit `Due`/`Links`/`Context` when not applicable.

## Rules

- Not a harness gate — todos never block a stage. If an item starts blocking progress, `promote` it into `questions` or `bugs`, which do gate.
- `{T}-open-todos.md` lives at the ticket root next to the ticket's other artifacts; `_shared/general-todos.md` for anything not tied to a ticket.
- `{short description}` is the tidied wording, not the raw input — most todos stay one line plus captured metadata.

## Delegates to

Planner/builder (when a todo becomes real ticket work — fold it into `{T}-plan.md` at that point rather than duplicating it), `bugs` (when a todo turns out to be a defect), `questions` (when a todo turns out to be an undecided design/scope question).

**Version:** 1.0-generic | **Updated:** 2026-07-04
