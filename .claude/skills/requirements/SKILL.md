---
name: requirements
description: The pre-freeze requirements pipeline in one skill — ops draft | enrich | iterate | freeze | stories. Drafts v0 from stakeholder intent grounded in the context snapshot, replaces placeholders with cited facts (never invents data), applies feedback rounds (the only op that bumps iteration), runs the freeze gate, and extracts user stories from frozen requirements. Use /requirements {T} {op}; critique passes live in challenge-requirements.
---

# /requirements

**When:** Everything between `analyze` (context) and planning. Pre-freeze except `stories` (post-freeze).
**Order:** `analyze {T} context` → **draft** → `challenge-requirements` (gaps + red-team) → **enrich** → `clarify`/`questions` → **iterate** (per feedback round) → `challenge-requirements` → **freeze** → **stories** → planner.
**Inputs:** `id` (required); `op` (required): `draft | enrich | iterate | freeze | stories`; op-specific: `intent` (draft), `source codebase|history|all` (enrich, default all), `feedback` (iterate).

## op: draft — v0 from stakeholder intent

1. Ensure scaffold exists (`kickoff {id}` if missing). If `{id}-context-snapshot.md` is missing/stale, run `analyze {id} context` first; empty snapshot → fail, never draft ungrounded.
2. Copy `_template/requirements-draft.md` → `{id}-requirements-draft.md`. One draft file, no parallel requirement files.
3. Populate v0 (keep every template section; `〈TBD〉` allowed for NFR targets and AC stubs): Intent (stakeholder wording verbatim + one-line interpretation) · Context Summary (wikilinked) · Scope (assumptions marked) · 3-8 candidate FRs · NFR seeds · Data entities · Business Rules `BR-{n}` · Edge Cases · External Dependencies · Open Questions (one per assumption — no silent assumptions).
4. Frontmatter: `iteration: 0`, `status: drafting`, `freeze_status: open`. Initial entry in `{id}-iteration-log.md`. Log each open question via `console/kanban.py tracker add {id} questions "..." --set type=requirements`. End with the `## Links` block.

## op: enrich — replace placeholders with cited facts

1. Extract every `〈TBD〉` and unlinked module/entity/convention mention from the draft + snapshot.
2. Enrich from `source`: **codebase** (concrete file paths, repo's own conventions) / **history** (prior tickets, commits). Every replacement cites its source.
3. NFR `〈TBD〉` with a grounded default → **proposed** number marked `⚠ [unrealistic?]` until the stakeholder confirms. **Never invent data** — unsupported facts stay `〈TBD〉` and go to `{id}-gap-analysis.md`.
4. Never alter Intent, Scope, or stakeholder-authored BR text. Update snapshot Source Log; iteration-log entry (no bump).

## op: iterate — apply a feedback round (the ONLY op that bumps iteration, exactly +1)

1. Capture feedback verbatim in the iteration-log entry. Classify each point: `intent | scope | fr | nfr | data | br | edge | integration | stakeholder | challenge-⚠ | answer-Q`.
2. Apply changes in place in the draft (mutable, no version files); every change traces to a feedback point; Intent changes called out explicitly, never silent.
   - Closing a `⚠` finding: remove from Challenge Findings, fix the original section.
   - Closing a question: `console/kanban.py tracker update {id} questions {item-id} --set status=resolved --set resolved_on=<today>`.
   - Closing a gap: update `{id}-gap-analysis.md` Resolution Log.
3. Bump `iteration: N → N+1`; full iteration-log entry (trigger verbatim, type, scope, delta bullets, why, gaps closed/opened, questions opened/answered, resulting ⚠/〈TBD〉 counts).
4. Suggest next: `freeze` if the checklist would pass, else the most effective pass (`challenge-requirements` if wording changed, `enrich` if new entities appeared).

## op: freeze — the gate between drafting and everything downstream

1. Read draft, gap-analysis, questions TOML, snapshot, iteration log. Run the checklist below deterministically; fail at the first `✗`.
2. On `✗`: no mutation except an iteration-log freeze-attempt row (attempt N · fail · blockers); report failed items with section pointers + the op/skill to run.
3. On all `✓`: draft frontmatter `status: frozen`, `freeze_status: frozen`, `frozen_at`, `frozen_iteration` · finalize `{id}-requirements.md` (title, frozen timestamp, iteration, Intent, in/out-of-scope, condensed FRs with AC checklists, NFR table, data entities, BRs, edge cases, links back to draft + iteration log) · iteration-log pass row · hand off `@planner → requirements {id} stories`.

## op: stories — user stories from frozen requirements

1. Read `{id}-requirements.md` (unfrozen draft → warn: stories may churn).
2. Extract user-centric stories `US-{n}: {Title}` — As a {role} / I want {action} / So that {benefit}; testable AC checklist; numbered BRs and edge cases. No overlap; 3-8 per ticket (split/merge outside that).
3. Write `{id}-user-stories.md` with traceability stubs for components and tasks (filled by planning). End with `## Links`.

## Output

| op | Writes |
|----|--------|
| draft | `{id}-requirements-draft.md` (v0), iteration-log entry, questions via CLI |
| enrich | draft placeholders replaced with cited facts; gap-analysis entries for remaining `〈TBD〉`; snapshot Source Log |
| iterate | draft updated in place, iteration +1, full iteration-log entry, synced questions TOML + gap Resolution Log |
| freeze | `{id}-requirements.md` finalized + frozen frontmatter (pass) / freeze-attempt row only (fail) |
| stories | `{id}-user-stories.md` |

## Gate (freeze checklist — all must pass)

- [ ] All `〈TBD〉` replaced or explicitly deferred with rationale
- [ ] All ⚠ findings resolved or `⚠ accepted: {rationale}`
- [ ] No 🔴 blocker gaps in `{id}-gap-analysis.md`
- [ ] All blocker/critical questions answered or resolved
- [ ] Every FR has ≥1 testable acceptance criterion (no vague modifiers)
- [ ] Every NFR has a concrete target or explicit "N/A — rationale"
- [ ] Every new/changed entity has a canonical reference or plan-to-create note
- [ ] Out-of-scope list non-empty
- [ ] Stakeholder sign-off recorded where required
- [ ] Interactions with Existing Features populated (or explicit "no interactions" + rationale)

Report (every op):
```
── requirements {op} ──
Ticket:    {id}
Iteration: {N}
{op-specific counts: FRs/placeholders replaced/changes applied/checklist result/stories}
⚠ remaining: {N} · 〈TBD〉 remaining: {N}
Next:      {next op or skill} {id}
```
Freeze pass adds: `Result: ✓ FROZEN (iteration {N}) · HANDOFF: @planner → requirements {id} stories`.

**Version:** 2.0 — merged draft/enrich/iterate/freeze/extract-stories into one op-based skill | **Updated:** 2026-08-23
