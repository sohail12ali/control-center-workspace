---
name: bugs
description: List, add, fix, verify, and triage open bugs/defects for ticket {T}. Parallel to questions but for QA failures and regressions, backed by the Delivery Console's CLI-mutated TOML tracker.
---

# /bugs

**Usage:**
```
/bugs {T}                                    # list / summarize all bugs
/bugs {T} add "description" [--severity=high]
/bugs {T} fix D-1 "fix description or ref"
/bugs {T} verify D-1                         # mark fix verified
/bugs {T} close D-1                          # won't fix / not a bug
/bugs {T} blockers                           # critical blockers only
```

**When:** Any phase after build — QA review, staging checks, or a `verify` failure that needs tracking rather than an immediate fix.

**Storage:** `knowledge-center/artifacts/{T}/{T}-bugs.toml` — mutated only via `console/kanban.py`, never hand-edited (see `consolidate/SKILL.md`).

## Steps

1. **list** — `python console/kanban.py tracker list {T} bugs`; group by status; flag critical severity.
2. **add** — `python console/kanban.py tracker add {T} bugs "description" --set severity=<severity> [--set steps="..." --set expected="..." --set actual="..."]`. CLI auto-increments `D-{n}`, fills `found_on`.
3. **fix** — `python console/kanban.py tracker update {T} bugs {id} --set status=fixed --set fix="..." --set fixed_by=<user|agent> --set fixed_on=<today>`.
4. **verify** — `python console/kanban.py tracker update {T} bugs {id} --set status=verified --set verified_by=<user> --set verified_on=<today>`.
5. **close** — `python console/kanban.py tracker update {T} bugs {id} --set status=closed --set fix="<reason: won't fix | duplicate | not a bug>"`.
6. **blockers** — `python console/kanban.py tracker blockers {T}`, read the `bugs` key.

## Severity model

| Severity | Meaning | Release gate |
|----------|---------|---------------|
| critical | Blocks a core flow | Must reach `verified` |
| high | Major feature broken | Must reach `fixed` before ship |
| medium | Visible defect, workaround exists | Fix before ship |
| low | Minor cosmetic / edge case | Nice-to-fix |

Default: **medium**.

## Status lifecycle

`open → in-progress → fixed → verified → closed` (re-open to `in-progress` if verify fails).

## Item fields (`{T}-bugs.toml`)

`id` (`D-{n}`), `status`, `severity`, `found_on`, `phase`, `found_by`, `text`, `steps`, `expected`, `actual`, `fix`, `fixed_by`, `fixed_on`, `verified_by`, `verified_on`.

## Rules

- Unverified `critical` bugs block release exactly like unresolved critical questions block a stage (`.claude/skills/clarify/question-templates.md`). Never ship on a `fixed`-but-unverified critical bug.
- Never hand-edit `{T}-bugs.toml` — always via `console/kanban.py`.

**Delegates to:** `console` (storage/CLI), `verify` (bugs surface there), `fix` (critical bug needing immediate triage).

**Version:** 2.1 — lean rewrite | **Updated:** 2026-08-23
