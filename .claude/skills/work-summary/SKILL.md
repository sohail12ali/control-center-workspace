---
name: work-summary
description: Quick business timesheet by ticket (≥8 h/day) from per-author knowledge-center/logs daily files, chat, and light artifacts. Filters by author unless --all. Use for timesheet, work overview, or /work-summary.
---

# /work-summary

Read-only **work recap + timesheet** from per-author daily logs. **≥8.0 h per author per day** (default). **Keep it short.**

**Primary path:** `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md`

**Default:** current author only — resolve slug via `.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1` (same as `/log-work`). **`--all`** = every `*.{slug}.md` file for the date(s), one timesheet block per distinct `author_slug`.

## Speed and simplicity (required)

| Principle | Requirement |
|-----------|-------------|
| **Brevity** | Post **only** the timesheet block(s) — no search narration |
| **Deliverables** | Each activity shows code/module/build, not meta (skip "resolved questions", "attempted X", agent names, skill names) |
| **Symbols** | Output body uses no decorative symbols — no middle dots, em dashes, asterisks, hashes, semicolons, colons, apostrophes, or pipes in any bullet text |
| **No task IDs** | Never show phase-slice-task IDs in output — plain business descriptions only |
| **Tool use** | chat → glob per-author log files for date → light artifacts. No git unless all empty |
| **Questions** | Ask at most once |

## Usage

```
/work-summary
/work-summary 2026-05-21
/work-summary 2026-05-19..2026-05-21
/work-summary T042
/work-summary --all
/work-summary --author="Jane Doe"
/work-summary --hours=8
/work-summary --verbose
/work-summary --append
```

| Parameter | Notes |
|-----------|-------|
| Date / range | Glob `logs/{YYYY-MM}/{YYYY-MM-DD}.*.md` for each date |
| `--all` | All author slugs for the date(s); ≥8h **per author** |
| `--author=` | Filter to one display name (resolve slug; match frontmatter `author:`) |
| `--hours={N}` | Daily floor (default 8.0) |
| `--append` | Backfill missing lines via `/log-work` |

## Reading daily logs

### File discovery (per date)

1. Glob: `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.*.md`
2. **Default (no `--all`):** read only `{YYYY-MM-DD}.{current_slug}.md` from `Ensure-LogAuthor.ps1`.
3. **`--all`:** read every slug file; emit one timesheet section per `author_slug` / `author` frontmatter pair.

| Section | Use for timesheet |
|---------|-------------------|
| Frontmatter `author:` + `author_slug:` | Timesheet header and file selection |
| `## Work` bullets | **Primary** — `- **{T}** [{Category}] ~{h} {text}` |
| `## [YYYY-MM-DD]` milestone blocks | Context / fallback if no Work bullets; business one-liner per ticket |

**Author resolution:** `Ensure-LogAuthor.ps1` → `{ Name, Slug }`. **Merge order:** chat → per-author file(s) for resolved slug (or all slugs with `--all`) → light artifacts.

## Hour allocation

Per author per day: user overrides → weight 1–5 → proportional split → round 0.25h → sum ≥ `--hours` (default 8.0).

## Output

Plain timesheet grouped by category then by ticket. No decorative symbols anywhere in output — no middle dots, em dashes, asterisks, hashes, semicolons, colons, apostrophes, or pipes. Use plain labels and dash bullets only. No task IDs.

**`--all` with multiple authors:** repeat the block below once per author (Date + Author + Total hours), separated by a blank line.

```
Work summary
Date 2026-05-21
Author Jane Doe
Total hours 8.0

Development

Ticket T036
Hours 3.0
- Rate-limit middleware implemented with sliding window and unit tests build green
- Data schema for archived orders with data layer and API endpoint and integration tests passing

Ticket T042
Hours 3.5
- Export module refactored and 3 output formats consolidated into one client build green
- Queue algorithm v2 to v3 cutover with performance benchmarks added

Testing

Ticket T036
Hours 1.5
- UAT smoke test for export flow and archived order scenarios complete

Total hours 8.0
```

Rules for the output body:
- Group by category first (Development, Code Review, Testing, Design, Documentation, Internal), ordered by total hours descending across all tickets in that category.
- Within each category, one ticket block per ticket id, ordered by hours descending.
- Each activity is a dash bullet, one line, plain sentence, no symbols of any kind.
- Use "and" instead of semicolons to join items in a bullet.
- Each activity must show what shipped (code, module, service, test, build result) — not meta work (questions resolved, approaches tried, iterations, agent or skill names).
- Never include phase-slice-task IDs — plain business descriptions only.
- Hours per ticket are the sum of that ticket and category activity weights after rounding to 0.25 h.
- Always end with a Total hours line that matches the sum of all ticket hours and is at least --hours (default 8.0).

## Related

| Command / script | Purpose |
|------------------|---------|
| `/log-work` | Append work line to today's per-author log file |
| `.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1` | Resolve current author name + slug |
| `progress-tracker` | Status and blockers per ticket |
| `project-layout/SKILL.md` | `logs/` layout and append rules |

**Version:** 1.0 — ported from lc-wms-cursor-config, genericized for control-center-workspace
