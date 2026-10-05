# Reset to a clean slate

How to take this workspace — a working control-center instance with real
tickets, logs, and history — back to an empty template someone else can
start a new project from.

## Command

```bash
python console/kanban.py reset --dry-run   # see the plan, changes nothing
python console/kanban.py reset             # prompts, then applies
python console/kanban.py reset --yes       # applies without prompting (scripts/CI)
```

Always run `--dry-run` first. The prompt (without `--yes`) requires typing
`reset` to confirm — there is no undo outside of git.

The same clean is on the Settings tab, under Workspace. It shows the
template check, then applies only after you type `reset`. It does not
commit.

```bash
python console/kanban.py workspace check            # leftover content, and any secret in git
python console/kanban.py workspace check --secrets  # secret paths only; tickets are allowed
python console/kanban.py workspace check --staged   # what the pre-commit hook runs
```

`workspace check` exits 1 when workspace content is still in this checkout
or a secret path is tracked. `--secrets` and `--staged` exit 1 only for
secret paths. A ticket, log, or investigation file is allowed: that is how
a fork stores its own project.

Options:

| Flag | Effect |
|------|--------|
| `--keep-logs` | keep `knowledge-center/logs/` daily activity logs |
| `--keep-investigations` | keep `knowledge-center/investigations/` |

## What gets wiped

- Every ticket dir under `knowledge-center/artifacts/` except `_template/`
  and `_shared/`
- `knowledge-center/artifacts/_shared/_shared-todos.toml` — reset to an
  empty tracker
- `knowledge-center/artifact-map.md` — reset to the empty Active / Blocked
  / Completed / Archived template
- `knowledge-center/investigations/*` (unless `--keep-investigations`)
- `knowledge-center/logs/*` daily log folders, keeping `author.local`
  (unless `--keep-logs`)
- `knowledge-center/telemetry/*.jsonl`
- `console/.cache/` (job queue, audit log, agent chat transcripts — already
  gitignored, local/ephemeral state)

## What's kept

- `knowledge-center/artifacts/_template/` and `_shared/` (the scaffolding
  `kickoff` copies from)
- `knowledge-center/docs/` and `knowledge-center/wiki/` — durable,
  project-independent documentation
- `console/config/` — board kinds, agent backends, pricing, verbs
- `.claude/` agents and skills
- git history — reset only touches the working tree, so prior state is
  always recoverable via git if the repo hasn't been re-initialized

## After a reset

Clean deletes files in this checkout. The branch a clone or fork sees still
has them until you commit those deletions. Older commits keep the files.
There is no history rewrite.

1. Commit the deletions when you want that branch to be the blank starting
   point. Until then, `git status` shows them as deleted.
2. `python console/kanban.py onboard` walks the six first-run steps
   (identity, project name, boards, agent CLI, first ticket, requirements).
3. `python console/kanban.py ticket create T001 --title "..."` to start the
   first real ticket, or use `kickoff` from a Claude/Cursor session.

Someone who clones or forks the commit that contains those deletions gets
an empty workspace and commits their own tickets on their own branch.
Ticket paths stay normal git files.

Secret paths stay off the branch: `.env`, key and certificate files,
`console/config/notify-local.toml`, `.claude/settings.local.json`, and
`console/.cache/`. `knowledge-center/logs/author.local` is one person's
name; log-work creates it locally and it is gitignored. The commit hook
that refuses staged secrets is opt-in:

```bash
git config core.hooksPath .githooks
```

## Starting a genuinely new project from this template

A workspace reset only clears *content*; it doesn't rename the project or
touch identity that lives outside `knowledge-center/`. Also check:

- `control-center.template.json` / `control-center.code-workspace` — project
  name and folder wiring
- `console/config/console.toml`, `boards/`, `agents.toml` — board kinds and
  agent backends specific to the old project
- `.claude/settings.local.json` (gitignored) and
  `console/config/notify-local.toml` (gitignored) — per-machine settings
  that won't follow a fresh clone anyway

## Links

- [[../../CLAUDE.md]] — layout this reset respects
- `.claude/skills/kickoff/SKILL.md` — how a new ticket is seeded post-reset
- `.claude/skills/console/SKILL.md` — the Delivery Console CLI this command
  belongs to
