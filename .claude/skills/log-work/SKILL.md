---
name: log-work
description: Per-author daily activity log, both directions — append work/milestone lines to knowledge-center/logs/YYYY-MM/YYYY-MM-DD.{slug}.md (auto-creates author.local from Git; use at session end, /log-work, or after kickoff/close-work/deploy), and mode summary produces the read-only business timesheet by ticket (≥8 h/day, author-filtered unless --all) that /work-summary used to provide. The console's Work tab reads these same files.
---

# /log-work

**When:** After meaningful work ships (session end, task/slice done, kickoff, close-work, deploy) — append. `/log-work summary [date|range] [--all]` — timesheet recap (read-only).
**Path (both modes):** `knowledge-center/logs/{YYYY-MM}/{YYYY-MM-DD}.{author_slug}.md` — one file per author per day. Never `log.md`, `log/`, or `activity/`; never mix harness-internal logs into these files. The console Work tab reads them as-is.

## Author resolution (both modes)

Run `.claude/skills/log-work/scripts/Ensure-LogAuthor.ps1` (returns `{Name, Slug, Path}`): 1) `--author=`/`--slug=` overrides · 2) `knowledge-center/logs/author.local` (line 1 name, line 2 slug; gitignored) · 3) auto-create from `git config user.name` · 4) `$env:USERNAME` · 5) git email local-part. Slug: lowercase, spaces/underscores → hyphen, strip non `[a-z0-9-]`. Never overwrite an existing `author.local`.

## Append — work line (default)

```
/log-work T042 ~3.5h Rate-limit middleware and sliding window for the public API.
/log-work Internal ~1h Daily log per-author file layout.
/log-work 2026-05-26 T038 Closed clubbing analysis for same-day exports.
/log-work --milestone "T042 | kickoff — rate-limit middleware" [--date=…]
```

1. Resolve date (default today), author, path. If the file is missing, create via `scripts/New-ActivityDay.ps1` (uses `template.md` here).
2. Append under `## Work` (create the section at end of file if absent): `- **{T}** [{Category}] ~{h} {text}` (`~h` optional; no nested author headings — author lives in frontmatter).
3. **Category (required):** `[Development]` code/builds/services · `[Code Review]` · `[Testing]` · `[Design]` architecture/requirements/spec · `[Documentation]` · `[Internal]` harness/config/tooling.
4. **Text rules (enforced):** human outcome only, ≤120 chars — feature built, bug fixed, analysis result, test/build outcome. Forbidden: agent names, skill/command names, process meta (iterations, freeze gates, artifact maps), phase-slice-task IDs, semicolons/colons/apostrophes/middle dots/em dashes; join items with "and". Example — bad: `@analyst pre-freeze pass 10 FRs`; good: `T042 rate-limit middleware requirements drafted and frozen`.
5. **Idempotent:** same slug + ticket + ≥70% similar text today → skip. Prefer `scripts/Append-WorkLog.ps1` for atomic append; no git, no artifact deep-reads.

## Append — milestone block (`--milestone`, kickoff/close)

Insert after `# {date}`, before the first `## Work`, newest first:
```markdown
## [YYYY-MM-DD] {T} | opened — {title}

- Ticket {T}
- (2-5 bullets, business tone, no colons/semicolons)
```
`kickoff` → title `{T} | opened`; `close-work` → `{T} | closed` + closure summary. One work line or one milestone per agent pass unless asked for more. List `log-work` in the completion Skills footer when appended.

## mode: summary (timesheet recap — read-only)

```
/log-work summary [YYYY-MM-DD | YYYY-MM-DD..YYYY-MM-DD | {T}] [--all] [--author="…"] [--hours=8] [--append]
```

1. Glob `logs/{YYYY-MM}/{YYYY-MM-DD}.*.md` per date. Default: current author's file only; `--all`: one timesheet block per `author_slug`.
2. Read `## Work` bullets (primary) and milestone blocks (context/fallback). Merge order: chat → per-author file(s) → light artifacts. No git unless all empty. Ask at most once.
3. Hours per author per day: user overrides → weight 1-5 → proportional split → round 0.25h → sum ≥ `--hours` (default 8.0). `--append` backfills missing lines via the append mode.
4. Output — post only the timesheet block(s), no search narration:

```
Work summary
Date 2026-05-21
Author Jane Doe
Total hours 8.0

Development

Ticket T036
Hours 3.0
- Rate-limit middleware implemented with sliding window and unit tests build green

Testing

Ticket T036
Hours 1.5
- UAT smoke test for export flow complete

Total hours 8.0
```

Body rules: group by category (hours descending), then one block per ticket (hours descending); dash bullets, one plain sentence each, no decorative symbols (no middle dots, em dashes, asterisks, hashes, semicolons, colons, apostrophes, pipes), no task IDs, "and" joins items; each bullet shows what shipped; end with Total hours ≥ the floor and equal to the sum.

## Related

`scripts/Ensure-LogAuthor.ps1` · `scripts/New-ActivityDay.ps1` · `scripts/Append-WorkLog.ps1` · `template.md` (this folder) · console Work tab (reads these files) · `progress-tracker` (per-ticket status lives there, not here).

**Version:** 2.0 — absorbed work-summary as mode summary | **Updated:** 2026-08-23
