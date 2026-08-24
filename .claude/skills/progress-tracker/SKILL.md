---
name: progress-tracker
description: Append a dated entry to progress.md, sync summary.md status, and (when task_id/component are given) patch the matching row in task-breakdown.md/components.md with actual effort, links, or done state. Use after every meaningful build or fix step — at minimum once per task completion or blocker, and whenever a task or component completes.
---

# /progress-tracker

**When:** After every meaningful build or fix step — at minimum once per task completion or blocker, and whenever a task or component completes.

**Inputs:** `id` (required, ticket id); `entry` (required): `{ done?, started?, blocked?, next? }`; `status` (optional): `Open` | `In Progress` | `Blocked` | `Complete`; `task_id` (optional): task ID from `{T}-task-breakdown.md` — when set, also patches that task's row (done state, actual effort); `component` (optional): component name from `{T}-components.md` — when set, also patches that component's row (done state, files touched, links).

## Steps

1. Append a dated section to `artifacts/{id}/{id}-progress.md`.
2. If `entry.done` references a task in `plan.md`, mark it `[x]`.
3. If `task_id` is given and `{id}-task-breakdown.md` exists, find that task's row and mark it done, recording actual vs. estimated effort.
4. If `component` is given and `{id}-components.md` exists, find that component's row and mark it done, recording the files/links that closed it.
5. If `entry.blocked`, add to Blockers section with impact + ETA, set Status=`Blocked`.
6. Update `summary.md` Current State (one line) and Status.
7. If status changed, update the row in `artifact-map.md`.

## Output

Path to progress.md and updated status; path to task-breakdown.md/components.md if patched.

## Rules

- One entry per call — don't batch days.
- Don't fabricate progress; require concrete evidence (commit, file, test result).
- If `task_id`/`component` references a file or row that doesn't exist, say so rather than silently skipping — never invent a row.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
