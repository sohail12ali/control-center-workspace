---
name: progress-tracker
description: Append a dated entry to progress.md and sync summary.md status. Use after every meaningful build or fix step — at minimum once per task completion or blocker.
---

# Inputs
- `id` (required): ticket id
- `entry` (required): `{ done?, started?, blocked?, next? }`
- `status` (optional): one of `Open`, `In Progress`, `Blocked`, `Complete`

# Steps
1. Append a dated section to `artifacts/{id}/{id}-progress.md`.
2. If `entry.done` references a task in `plan.md`, mark it `[x]`.
3. If `entry.blocked`, add to Blockers section with impact + ETA, set Status=`Blocked`.
4. Update `summary.md` Current State (one-line) and Status.
5. If status changed, update the row in `artifact-map.md`.

# Output
Path to progress.md and updated status.

# Rules
- One entry per call. Don't batch days.
- Don't fabricate progress; require concrete evidence (commit, file, test result).
