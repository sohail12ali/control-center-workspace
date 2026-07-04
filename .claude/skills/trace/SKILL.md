---
name: trace
description: Show all UP links (sources) and DOWN links (dependents) of a file; report missing links in both directions. Report only — does not modify files.
---

# /trace

**Usage:** `/trace {file-path}` — `{file-path}` a repo-relative or absolute path to any file (code, config, markdown artifact, etc.), or an artifact/ticket id.

## Steps

1. **Resolve the file** — locate it in the workspace. If ambiguous, list candidates and ask.
2. **Trace UP links (sources)** — what this file depends on:
   - Code files: imports, base types/interfaces, injected dependencies, referenced data models, called functions/services.
   - Markdown artifacts: wikilinks, file references, "See also" links, frontmatter `related` fields.
   - Config/rule files: referenced files, globs, or other rules/skills it loads.
3. **Trace DOWN links (dependents)** — what depends on this file:
   - Code files: types that inherit/implement it, files that import/reference it, tests that cover it.
   - Markdown artifacts: other artifacts that wikilink to it, skills/agents that reference it.
   - Config/rule files: skills/agents that load it, other rules that reference it.
4. **Report missing links** — for each direction, flag gaps:
   - UP: file uses something with no explicit link/import (implicit dependency).
   - DOWN: file should be referenced by something but isn't (orphan artifact, missing test, missing rule coverage).
5. Do nothing else — report only. Suggest `fix` or `evolve` if gaps need action; do not modify files here.

## Output

```
TRACE: {file-path}
Type: code | artifact | config | rule

-- UP (sources / dependencies) --
  {path} — {relationship}

-- DOWN (dependents / consumers) --
  {path} — {relationship}

-- MISSING LINKS --
  UP:   {description of missing source link, or none}
  DOWN: {description of missing dependent link, or none}
```

## Rules

- Report only — never edit the traced file or its neighbors.
- For ticket artifacts, treat the `## Links` block and frontmatter as the authoritative link list; anything referenced in prose but missing from `## Links` is a gap.

**Delegates to:** none (reporting only); route findings to `fix` or `evolve`.

**Version:** 2.0-generic | **Updated:** 2026-07-04
