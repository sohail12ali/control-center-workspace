---
name: analyze-context
description: Deep-scan the codebase and prior artifacts to ground the requirements draft in reality. Pre-freeze. Use before draft-requirements, or whenever scope or intent shifts.
---

# Inputs
- `id` (required): ticket id
- `scope` (optional): `codebase | history | all` (default `all`)

# Steps
1. Copy `knowledge-center/artifacts/_template/context-snapshot.md` into `knowledge-center/artifacts/{id}/{id}-context-snapshot.md` if missing; otherwise update in place.
2. **codebase scope:**
   - Grep the repo(s) named in `id`'s workspace folder for existing features with similar names or domain terms.
   - Record one representative file per layer touched (e.g., entry point, service/logic, data access, UI) — use whatever layering the target repo actually has.
   - Identify reusable patterns already in the codebase (validators, base classes, shared components).
   - Cross-reference the target repo's own `CLAUDE.md` / skill rules for conventions in play.
3. **history scope:**
   - `git log --oneline --grep` on domain keywords in the relevant repo(s).
   - Read prior ticket artifacts under `knowledge-center/artifacts/*/` for related work (search by domain keyword, not just ticket id).
   - Note known issues (search `knowledge-center/logs/` for relevant dates, if logs exist).
4. Populate every section of the template. **Cite every bullet** — file path, commit sha, or ticket id. No speculation, no "might exist".
5. Fill the Source Log table for traceability.
6. If a bullet is an unverified claim, add it to the Open Confirmations section instead of stating it as fact.

# Output
```
── analyze-context ──
Ticket:           {id}
Scope:            {scope}
Similar features: {N}
Prior tickets:    {N}
Source log:       {N} lookups recorded
Open confirmations: {N}
Next:             draft-requirements {id} (if draft not yet v0) | enrich-requirements {id}
```

# Rules
- Descriptive only — this step never invents requirements, it records what exists today.
- Every bullet needs a source; unverified claims go to Open Confirmations, not the main sections.
- Don't grep the whole workspace blind — resolve the relevant repo(s) from the ticket's stated scope first.

**Delegates to:** none (reads only)
**Next:** `draft-requirements` (if no draft yet) or `enrich-requirements`
