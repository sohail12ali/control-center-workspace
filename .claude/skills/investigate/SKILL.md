---
name: investigate
description: Production-issue or bug-report triage — rewrite the intake, classify with proof (bug vs feature vs config vs data vs unknown), trace cause across all workspace sub-projects, and persist a dossier outside ticket artifacts unless a real {T} already exists. Use before fix/ticket-draft when it's unclear whether something is broken, by design, or a config/data problem.
---

# /investigate

**When:** A prod report, UAT escalation, screenshot, or "is this broken?" question arrives with no ticket, and the answer needs cause-tracing. Runs before `fix` (which already knows root cause) and `ticket-draft` (which scopes a new ask) — this skill produces the proof-backed classification they consume.

**Inputs:** the report (text, error, screenshot description, repro); `{T}` optional if an open ticket already owns it.

## Steps

1. **Rewrite the intake** — restate in precise, testable terms (expected, actual, when, data/environment). Flag missing repro details as open questions; never guess them.
2. **Resolve scope** — workspace-wide vs specific sub-project(s), via `project-layout`; multi-sub-project reports fan out across all of them.
3. **Trace cause**, in priority order: (a) this workspace's ticket artifacts + `knowledge-center/wiki/` (known issue/limitation?); (b) the sub-project's own `CLAUDE.md`/rules (by design?); (c) the sub-project's actual code (read it, don't infer from naming); (d) web/external sources only if unresolved.
4. **Classify with proof** — every classification cites what was checked:
   - **bug** — contradicts the sub-project's own spec/code intent; cite the code path.
   - **regression** — worked before, a specific change broke it; cite the commit/PR/dated artifact.
   - **feature** — behaves as designed; cite the spec/code/rule.
   - **config** — environment/settings issue; cite the config value.
   - **data** — bad/missing/malformed data, not logic; cite the record or query.
   - **unknown** — unresolvable with available evidence; state exactly what's missing.
5. **Persist the dossier** (Output below) — a non-trivial investigation never lives only in chat.
6. **Route:** `bug`/`regression` → `ticket-draft` (or `kickoff` if trivial) or `fix` if quick/safe/isolated; `feature`/`config`/`data` → report back (optionally a `todos` entry); `unknown` → list what's needed, offer re-run.

## Output

- **No real `{T}` yet (common case):** `knowledge-center/investigations/INV-{YYYY-MM-DD}-{slug}/INV-{YYYY-MM-DD}-{slug}-dossier.md` — sanctioned non-flat exception (see `consolidate`).
- **`{T}` exists:** `knowledge-center/artifacts/{T}/investigations/INV-{YYYY-MM-DD}-{slug}-dossier.md`.
- If `ticket-draft`/`kickoff` later opens `{T}`, move the dossier into `artifacts/{T}/investigations/` and link from `{T}-summary.md`.

```
── investigate: {slug} ──
Report:       {one line}
Scope:        {workspace-wide | sub-project(s)}
Classification: {bug | regression | feature | config | data | unknown}
Proof:        {file:line | artifact | doc cited}
Dossier:      {path}
Next:         ticket-draft | fix | report-only | re-run (missing: {what})
```

## Rules

- Never classify without citing what was checked — "looks like a bug" is a guess, not a classification.
- Don't skip the `feature`/by-design possibility because the reporter was surprised.
- Never create a ticket here — route to `ticket-draft`/`kickoff`/`fix` (each has its own gate).
- `data` is not license to edit production data — report the finding; fixes follow the sub-project's own process.

**Delegates:** `project-layout` (sub-project resolution), `ticket-draft`/`kickoff`/`fix` (routing), `todos` (follow-up without a ticket).

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
