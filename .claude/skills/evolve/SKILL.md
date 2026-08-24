---
name: evolve
description: Amend a frozen artifact when reality shifts mid-flight (scope change, new constraint, discovery). Captures the delta and the why. Use instead of silently rewriting; preserves decision history.
---

# /evolve

**When:** A frozen artifact must change mid-flight (scope change, new constraint, discovery) — never silently rewrite post-freeze.

**Order:** Run `reconcile` on the ticket after every evolve.

**Inputs:** `id` (required, ticket id); `target` (required): `requirements` | `plan` | `architecture` | `analysis`; `reason` (required): trigger (discovery, user request, dependency change, risk realized).

## Steps

1. Snapshot the current target into `decision-log.md` under `## Amendment {DATE}` — Before / After diff summary, not the full file.
2. Apply the change to the target file in place.
3. Cascade: `requirements` change → flag affected `plan` tasks for re-validate; `plan` change → flag affected `progress`/`verification` rows.
4. Append to `progress.md`: `Amended {target}: {reason}`.
5. Update `summary.md` Current State with the shift.

## Output

List of cascaded artifacts that need re-validation.

## Gate

- The decision-log entry is mandatory — never amend silently.
- If the amendment expands scope past the original ticket, route to harness for re-scoping (possibly a new ticket).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
