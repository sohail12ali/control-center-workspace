---
name: bugs
description: List, add, fix, verify, and triage open bugs/defects for ticket {T}. Parallel to questions but for QA failures and regressions tracked in {T}-open-bugs.md.
---

# /bugs

**Usage:**
```
/bugs {T}                                    # list / summarize all bugs
/bugs {T} add "description"                  # add a bug
/bugs {T} add "description" --severity=high  # add with explicit severity
/bugs {T} fix D-1 "fix description or ref"   # record fix for D-1
/bugs {T} verify D-1                         # mark D-1's fix as verified
/bugs {T} close D-1                          # close (won't fix / not a bug)
/bugs {T} blockers                           # show critical blockers only
```

**When:** Any phase after build — QA review, staging checks, or a `verify` failure that needs tracking rather than an immediate fix.

**Canonical storage:** `knowledge-center/artifacts/{T}/{T}-open-bugs.md` (create from `.claude/skills/bugs/template.md` if missing).

## Steps

1. **Load** `{T}-open-bugs.md` if present; if missing, scaffold from the template and continue.
2. **list** — show bugs grouped by status (open, in-progress, fixed, verified, closed); flag critical blockers.
3. **add** — append a `D-{n}` entry with severity, steps, expected/actual. Auto-increment `D-{n}` from the current max.
4. **fix** — set status to `fixed`; record the fix description/reference and date.
5. **verify** — set status to `verified`; record verifier and date.
6. **close** — set status to `closed`; record the reason (won't fix, duplicate, not a bug).
7. **blockers** — filter to severity `critical` with status not `verified`/`closed`.

## Severity model

| Severity | Meaning | Release gate |
|----------|---------|---------------|
| critical | Blocks a core flow; release cannot ship | Must reach `verified` |
| high | Major feature broken | Must reach `fixed` before ship |
| medium | Visible defect, workaround exists | Fix before ship |
| low | Minor cosmetic or edge case | Nice-to-fix |

Default when unspecified: **medium**.

## Status lifecycle

```
open -> in-progress -> fixed -> verified -> closed
             ^_____________________|  (re-open if verify fails)
```

## Entry format

```markdown
#### D-{n} [{severity}] {short description} — {status}

- **Found:** {YYYY-MM-DD} | **Phase:** {QA|staging|production} | **Found by:** {user|agent}
- **Steps:** {how to reproduce}
- **Expected:** {expected behavior}
- **Actual:** {actual behavior}
- **Fix:** {description or reference}
- **Fixed by:** {agent or user} | **Fixed:** {YYYY-MM-DD}
- **Verified by:** {user} | **Verified:** {YYYY-MM-DD}
```

Omit `Steps`/`Expected`/`Actual` for a one-line entry when the bug is obvious from context.

## Rules

- `.claude/skills/clarify/question-templates.md` — blocking semantics apply the same way: unverified `critical` bugs block release like unresolved critical questions block a stage.
- Critical bugs must reach `verified` before release sign-off — never ship on a `fixed`-but-unverified critical bug.

## Delegates to

`verify` (bugs surface during verification), `fix` (a critical bug needing immediate triage).

**Version:** 1.0-generic | **Updated:** 2026-07-04
