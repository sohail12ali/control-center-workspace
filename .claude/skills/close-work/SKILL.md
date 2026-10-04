---
name: close-work
description: VERIFY → Close. Finalizes verification.md, sets Status=Complete, stamps closed_date, moves the artifact-map row to Completed, syncs the console board lane to done, optionally archives, and points to deployer when the ticket ships code. Use only after verify (scope=ready) and validate-artifacts pass with no block items.
---

# /close-work

**When:** After `verify` (scope=ready) and `validate-artifacts` pass with no block items.
**Order:** verifier's last step; `deployer {id}` may follow on explicit request.

# Inputs
- `id` (required) · `archive` (optional, default false — move dir to `artifacts/_archive/{id}/`)

# Steps
1. Run `python console/kanban.py verb run close-check --ticket {id}`. Abort when the result has `ok: false`, and list the block codes. Do not continue.
2. Confirm `{id}-verification.md` exists and every acceptance criterion has evidence.
3. Run `verify` (scope=ready) and `validate-artifacts`; abort on any `block`.
4. Update `{id}-summary.md`: Status=`Complete`, tags `[completed]`, `closed_date: {today}` in frontmatter, append close note.
5. Console sync: `python console/kanban.py ticket move {id} done`. The guard runs `close-check` again and refuses the move when it blocks (skip with a note if `console/` is absent).
6. Move the row in `artifact-map.md` from `## Active`/`## Blocked` to `## Completed`.
7. If `archive`: move the directory; update map row with `(archived)` suffix.

# Output
Final summary path + updated map entry.

# Gate
- Never close with unchecked plan tasks unless `{id}-decision-log.md` records the descope.
- Never silently drop unmet criteria — route to fixer.
- Never edit `verification.md` only to satisfy `close-check`.
- Never call `close-override` or invent a reason; only the user supplies one.

**Next:** `deployer {id}` if the ticket ships code (ASK-gated), else `standup` or done.

**Version:** 1.1 — lean rewrite; console lane sync on close | **Updated:** 2026-08-23
