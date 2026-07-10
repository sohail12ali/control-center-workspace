---
name: challenge-requirements
description: Red-team the requirements draft. Flag ambiguities, contradictions, untestable criteria, unstated assumptions, and unrealistic constraints. Pre-freeze, find-don't-fix.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `{id}-requirements-draft.md`, `{id}-context-snapshot.md`, `{id}-gap-analysis.md`.
2. Walk every section and flag findings with `⚠` markers written **inline** into the draft's Challenge Findings section (never silently rephrase the source text):
   - **ambiguity** — vague modifiers (`quickly`, `easily`, `as needed`, `if possible`), undefined pronouns, undefined domain terms.
   - **contradiction** — scope vs. FR, FR vs. BR, FR vs. NFR, NFR vs. context snapshot.
   - **untestable** — acceptance criteria without an observable outcome, thresholds without numbers, "should work" phrasing.
   - **unstated-assumption** — preconditions a reader would need to infer (role, data state, system state).
   - **unrealistic-constraint** — NFR targets not supported by existing infra in the context snapshot; ungrounded timelines.
   - **spof** — FR depends on one external system with no fallback noted.
   - **scope-creep** — in-scope items not traceable to Intent; out-of-scope items re-introduced implicitly via an FR.
   - **nfr-unmeasurable** — NFR without a stated measurement method.
3. For each finding, write: `⚠ [{kind}] §{section}: {one-sentence issue} — resolution: 〈TBD〉`
4. Count findings by kind; update the Challenge Findings header.
5. Do **not** propose rewrites here — resolutions happen via `iterate-requirements`. Challenge and repair are separate passes so the signal isn't diluted.
6. Append an entry to `{id}-iteration-log.md` under the current iteration (no iteration bump) listing every section that received a `⚠`.
7. Sync to `{id}-critique-report.md` per `.claude/skills/challenge-standards/rules.md`:
   - Scaffold the report if missing (minimal header + one section per stage).
   - Map each `⚠` to a `CR-{n}` row (severity: default `major`; `critical` for freeze-blocking ambiguity/contradiction).
   - Update its Summary table counts and "Last run" for the Requirements stage.
   - Don't duplicate full finding text — point back to the draft section for detail.

# Output
```
── challenge-requirements ──
Ticket:   {id}
Findings: {N} total
  ambiguity: {n}  contradiction: {n}  untestable: {n}  unstated-assumption: {n}
  unrealistic-constraint: {n}  spof: {n}  scope-creep: {n}  nfr-unmeasurable: {n}
Next:     clarify {id} (discuss with stakeholder) → iterate-requirements {id} "resolutions"
```

# Rules
- At least one walk-through per section is performed — findings may be zero, but every section is considered.
- Every `⚠` line has `{kind}` and `§{section}` so it's grep-able.
- No silent edits to FR / BR / NFR text — only the Challenge Findings section and critique report are written here.
- `{id}-critique-report.md` is kept current with CR rows and summary counts (see `challenge-standards/rules.md`).

**Delegates to:** none
**Next:** `clarify` → `iterate-requirements`
