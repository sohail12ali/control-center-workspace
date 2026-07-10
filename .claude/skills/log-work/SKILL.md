---
name: log-work
description: Appends work or milestone lines to per-author daily log files (knowledge-center/logs/YYYY-MM/YYYY-MM-DD.{slug}.md). Auto-creates author.local from Git. Use at agent session end, /log-work, or after kickoff/close-work/deploy.
---

# /log-work

Write to **`knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md`** — **one file per author per calendar day**. No shared daily file. Two append types:

| Type | Where in file | When |
|------|---------------|------|
| **Work** (default) | `## Work` → bullet | Timesheet line after a slice, deploy, or analysis pass |
| **Milestone** | After `# {date}`, before `## Work` — `## [{date}] …` block | Kickoff, close-work, harness stage transitions |

**Tone:** Write like a human developer on a timesheet — what feature was built, what bug was fixed, what analysis concluded, what test or build passed. Concrete outcomes only (≤120 chars). **Never** log which skill ran, which agent was invoked, or process steps (iterations, freeze gates, artifact maps).

## Setup (auto on first use)

`knowledge-center/logs/author.local` is **gitignored** and **auto-created** on first append from `git config user.name` (see Author resolution). Manual override: create `author.local` with two lines — display name, slug.

**Helper:** `.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1` — returns `{ Name, Slug, Path }` JSON; creates `author.local` only when missing.

## Layout

```text
knowledge-center/logs/
  author.local            # gitignored — auto-created
  YYYY-MM/
    YYYY-MM-DD.{slug}.md  # per-author daily log (milestones + work)
```

**Do not use:** `log.md`, `log/`, `activity/`. Internal harness operation logs (if any) belong in their own path — never mix them into per-author daily files.

## Categories

Every work line must include one category tag. Valid values:

| Tag | Use for |
|-----|---------|
| `[Development]` | Code, data layer, builds, services |
| `[Code Review]` | Review passes, feedback applied |
| `[Testing]` | UAT, unit tests, smoke tests |
| `[Design]` | Architecture, requirements, spec |
| `[Documentation]` | Docs, artifact updates, reference material |
| `[Internal]` | Harness setup, config, tooling |

## Example daily file

```markdown
---
date: 2026-05-25
author: Jane Doe
author_slug: jane-doe
type: daily-log
---

# 2026-05-25

## [2026-05-25] T042 kickoff rate-limit middleware

- Ticket T042
- Rate-limit middleware scope for the public API

## Work

- **T042** [Development] ~3.5h Rate-limit middleware added with sliding window and build green
```

## Human voice — good vs bad

| Bad (process / meta) | Good (outcome) |
|----------------------|----------------|
| `Authored log-sync skill` | `Added sync workflow for release notes into changelog` |
| `@analyst pre-freeze pass 10 FRs 13 BRs` | `T042 rate-limit middleware requirements drafted and frozen` |
| `Persisted artifact map to vault` | `T038 partial-export bug documented with repro steps` |
| `Iteration 2 applied 6 stakeholder answers` | `T042 rate-limit scope updated per stakeholder feedback` |
| `Full analyst pass context snapshot gap analysis` | `T042 rate-limit gaps identified and documented` |

## Invoke without the slash command

| User says | Action |
|-----------|--------|
| Log my work on T042 | `/log-work T042` + distill from chat |
| Record 4h on T038 today | `/log-work T038 ~4h …` |

## Usage

```
/log-work T042
/log-work T042 ~3.5h Rate-limit middleware and sliding window for the public API.
/log-work Internal ~1h Daily log per-author file layout and author auto-provision.
/log-work 2026-05-26 T038 Closed clubbing analysis for same-day exports.
/log-work --author="Jane Doe" T036 ~2h Priority rules for the queue worker.
/log-work --author="Jane Doe" --slug=jane-doe T036 ~2h Priority rules for the queue worker.

/log-work --milestone "T042 | kickoff — rate-limit middleware"
/log-work --milestone "T038 | closed — export redirect" --date=2026-05-23
```

| Parameter | Notes |
|-----------|-------|
| `{T}` or text | **Work:** ticket id (`T042`, `Internal`) + business line |
| `~{N}h` | Optional hour hint on work bullets |
| `YYYY-MM-DD` | Date (default **today**) |
| `--author=` | Override display name |
| `--slug=` | Override author slug (default derived from name) |
| `--milestone "title"` | Insert `## [{date}] {title}` block + bullets from chat (not a work bullet) |
| `--date=` | With `--milestone` only |

## Author resolution

Run **`.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1`** (or equivalent logic) before append:

| Priority | Source |
|----------|--------|
| 1 | `--author=` (+ derive slug unless `--slug=`) |
| 2 | `knowledge-center/logs/author.local` — line 1 = display name, line 2 = slug |
| 3 | **Auto-create:** `git config user.name` (repo-local then global); derive slug; **write** `author.local` (two lines, UTF-8) |
| 4 | `$env:USERNAME` or `$env:USER` + derived slug; write `author.local` |
| 5 | `git config user.email` — local-part as slug, email as display; write `author.local` |

**Slug derivation:** lowercase; trim; spaces/underscores → single hyphen; strip non `[a-z0-9-]`; collapse repeated hyphens. Example: `Jane Doe` → `jane-doe`. Store slug in `author.local` line 2 so renames stay stable.

**Never overwrite** an existing `author.local`.

## Append procedure

### Work line (default)

1. Resolve **date**, **author name**, and **author slug** (Ensure-LogAuthor).
2. Path: `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md`.
3. If missing: run `.claude/skills/log-work/scripts/New-ActivityDay.ps1` (uses `template.md` in this skill folder).
4. Ensure **`## Work`** section exists at end of file; append bullet directly under it (no nested `## {Author}` — author is in frontmatter only).
5. Append: `- **{T}** [{Category}] ~{h} {text}` (`~h` optional). Category required — pick from the Categories table above.
6. **Text rules (enforced):**
   - **Human outcome only** — feature built, bug fixed, analysis result, test or build outcome
   - **Forbidden:** agent names (`@analyst`, `@builder`), skill/command names (`/log-work`, `kickoff`, `pre-freeze`), process meta (`iteration N`, `freeze gate`, `artifact map`, `vault intake`, `distill from chat`)
   - No task IDs in text (no phase-slice-task patterns) — plain business descriptions only
   - No semicolons, colons, apostrophes, middle dots, or em dashes in the text content
   - Join multiple items with "and" instead of semicolons
7. **Idempotent:** same author slug + ticket + ≥70% similar text in today's author file → skip.
8. **Prefer** `.claude/skills/log-work/scripts/Append-WorkLog.ps1` for atomic append; otherwise one file write — no git, no artifact deep-reads.

### Milestone block (`--milestone` or agent kickoff/close)

1. Same per-author path: `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md`; create if missing.
2. Insert **after** `# {date}` line, **before** first `## Work` or at top of body if no Work yet.
3. Format:

```markdown
## [YYYY-MM-DD] {title}

- Ticket {T}
- (2 to 5 bullets, scope, business tone, no colons or semicolons)
```

4. **Newest milestone first** (prepend below `# {date}`).
5. **`kickoff`:** title `{T} | opened` + bullets from scaffold steps.
6. **`close-work`:** title `{T} | closed` + closure summary from the ticket's summary artifact.

## Speed (required)

- **One** work line or **one** milestone block per agent pass unless user asks for more.
- Do not read deep artifact folders or architecture notes just to write the log.
- List **`log-work`** in completion **Skills:** when appended.

## Agent-end

| Agent / skill | Append |
|---------------|--------|
| **kickoff** | Milestone `opened` + `/log-work {T}` work line |
| **analyst** | Work line after kickoff, freeze, major requirements pass — **outcome only**, not agent name |
| **builder** | Work line after a task or slice — **what shipped**, not task id |
| **fixer** | Milestone on close + work line |
| **verifier / close-work** | Work line after verification passes or the ticket closes |

## Related

| Command / doc | Purpose |
|---------------|---------|
| `/work-summary` | Timesheet from per-author daily files |
| `project-layout/SKILL.md` | `logs/` layout and append rules |
| `.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1` | Resolve or auto-create author.local |
| `.claude/skills/log-work/scripts/New-ActivityDay.ps1` | Create empty per-author daily file |
| `.claude/skills/log-work/scripts/Append-WorkLog.ps1` | Atomic work-line append |

**Version:** 1.0 — ported from lc-wms-cursor-config, genericized for control-center-workspace
