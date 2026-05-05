---
name: manage-questions
description: Maintain a per-ticket open-questions queue. Extracts Qs from artifacts, tracks status (open / deferred / resolved), assigns owner, surfaces what's blocking which stage. Use at every stage gate.
---

# Inputs
- `id` (required): ticket id
- `op` (required): `extract` | `add` | `resolve` | `defer` | `list`
- `payload` (op-dependent): question text, owner, decision ref

# Storage
`artifacts/{id}/{id}-questions.md` (created on first call). Schema:

```
| # | Question | Status | Stage | Owner | Decision |
|---|---|---|---|---|---|
```

# Steps
- `extract`: scan summary/analysis/requirements/plan for `?` lines, TODOs, "TBD", "?" placeholders → add as `open`
- `add`: append a Q with stage + owner
- `resolve`: mark resolved, link to `decision-log` entry, patch source artifact
- `defer`: mark deferred with target stage
- `list`: print open Qs grouped by stage, oldest first

# Output
Counts by status + the next blocking Q for the current stage.

# Rules
- Never let a stage advance with `open` Qs that block it (planner blocked by req-stage Qs, etc.).
- Resolutions must reference a `decision-log.md` entry; otherwise it's just an answer, not a decision.
