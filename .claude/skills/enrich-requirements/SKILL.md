---
name: enrich-requirements
description: Replace placeholders in the requirements draft with concrete facts from the codebase or prior artifacts. Pre-freeze. Never invents data.
---

# Inputs
- `id` (required): ticket id
- `source` (optional): `codebase | history | all` (default `all`)

# Steps
1. Read `{id}-requirements-draft.md` and `{id}-context-snapshot.md`. Extract every `〈TBD〉` and unlinked mention of a module, entity, or convention.
2. For each mention, enrich from the requested source:
   - **codebase** — resolve pattern references to concrete file paths; pin naming conventions from the target repo's own style rules.
   - **history** — expand a reference using prior tickets/commits that already dealt with the same entity or area.
3. For NFR `〈TBD〉` targets where enrichment can propose a grounded default, replace with a **proposed** number and append `⚠ [unrealistic?]` so the stakeholder confirms. Ground defaults in things actually measured or established elsewhere in the codebase — never invent a number.
4. **Never invent data.** If no source supports a fact, leave `〈TBD〉` and add an entry to `{id}-gap-analysis.md` (category: Data or NFR).
5. Do not change Intent, Scope, or stakeholder-authored Business Rule text.
6. Update `{id}-context-snapshot.md` Source Log with every new lookup.
7. Append an entry to `{id}-iteration-log.md` under the current iteration (no iteration bump), listing each replacement as `{section} · {before} → {after} · source: {…}`.

# Output
```
── enrich-requirements ──
Ticket:       {id}
Source:       {source}
Placeholders: {N} found
Replaced:     {N}
Left 〈TBD〉:  {N}  (added to gap-analysis.md)
Proposed NFRs: {N}  (marked ⚠ for confirmation)
Next:         challenge-requirements {id} | clarify {id} (confirm proposed NFRs)
```

# Rules
- Every replacement cites a source (file path, commit, or prior ticket).
- Every unsupported claim stays `〈TBD〉` and gets a gap entry — no exceptions.
- NFR replacements stay marked `⚠` until the stakeholder confirms.
- Intent, Scope, and stakeholder-authored Business Rule text are never altered here.

**Delegates to:** none
**Next:** `challenge-requirements` | `clarify` (confirm proposed NFRs)
