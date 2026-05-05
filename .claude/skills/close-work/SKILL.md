---
name: close-work
description: VERIFY → Close. Finalizes verification.md, sets Status=Complete, moves the artifact-map row to Completed, optionally archives. Use only after validate(target=verification) passes with no block items.
---

# Inputs
- `id` (required): ticket id
- `archive` (optional, default false): move dir to `artifacts/_archive/{id}/`

# Steps
1. Confirm `verification.md` exists and every acceptance criterion has evidence.
2. Run `validate target=verification`; abort if any `block`.
3. Update `summary.md`: Status=`Complete`, tags `[completed]`, append close note.
4. Move row in `artifact-map.md` from `## Active`/`## Blocked` to `## Completed`.
5. If `archive`: move directory; update map with `(archived)` suffix.

# Output
Final summary path and the updated map entry.

# Rules
- Never close while plan tasks remain unchecked unless `decision-log.md` records the descope.
- Never silently drop unmet criteria; route to fixer instead.
