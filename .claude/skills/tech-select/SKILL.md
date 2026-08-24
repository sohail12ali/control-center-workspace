---
name: tech-select
description: Decide a technology choice for a ticket — language, framework, library, package, design pattern, architecture style, API framework, UI framework, database, infra, auth, queue, cache, observability, build tool, test runner, etc. Researches the web for current best fits, surfaces 2-4 ranked options with tradeoffs, asks the user blocking questions via `questions`, gates on explicit user approval, and records the final pick to `decision-log.md` with rationale and rejected alternatives. Use whenever an artifact needs a "what should we use for X?" answer — works for new projects (greenfield stack picks) and existing projects (adding/replacing a component).
---

# /tech-select

**When:** Whenever an artifact needs a "what should we use for X?" answer — greenfield stack picks or adding/replacing a component in an existing project.

**Order:** User-approval-gated; records to `{T}-decision-log.md`. Called by `analyst` (GROUND/CLARIFY), `planner` (CANONICAL, before tasks presuppose a tech), `builder` (mode=`confirm-existing` for new undecided dependencies), `fixer` (root cause is "wrong tech"), `harness` (when `handoff` reports a blocking "tech choice undecided" gate). Feeds `plan risk`, `evolve`, `questions`.

**Inputs:** `id` (required); `topic` (required, free-form, one decision per call — e.g. `language`, `web-framework`, `orm`, `database`, `auth`, `queue`, `cache`, `observability`, `ui-kit`, `design-pattern:retry`, `architecture`, `api-style`, `package:pdf-parse`, `test-runner`, `ci`, `deploy-target`); `constraints` (optional — runtime, license, budget, team skills, perf SLO, compliance, hosting, latency, scale, existing stack, must-not-use; else derived from `summary.md`/`requirements.md`/`analysis.md` and confirmed with the user); `mode` (default `interactive`): `interactive` (ask user, gated) | `recommend` (ranked options only, no decision recorded) | `confirm-existing` (validate a user-proposed choice); `shortlist` (optional candidates).

**Storage:** reads `{id}-summary.md`, `{id}-requirements.md`, `{id}-analysis.md`, `{id}-decision-log.md`, `{id}-questions.toml`, prior tech decisions in this/linked tickets. Writes `{id}-decision-log.md` (final decision), `{id}-questions.toml` (blocking Qs via `questions`), and a research block in `{id}-analysis.md` under `## Research / tech-select: {topic}` (auditable evidence).

## Steps
1. **Load context.** `trace-context` for `{id}`; pull existing tech decisions from this and `[[linked]]` tickets for stack coherence. Reject early if `summary.md` is missing.
2. **Frame constraints** from caller input, requirements (functional + NFR: perf/scale/compliance/SLA), earlier locked-in stack decisions, and team-skill/license/hosting hints in `summary.md`. Mark inferred ones `assumed:` — candidate questions.
3. **Ask blocking questions.** Any load-bearing unstated constraint → file via `questions(op=add, stage=current)` and surface in chat. Almost always blocking: deployment env, expected scale, team's primary language, data shape, self-hosted vs managed, license tolerance (GPL/AGPL?), budget ceiling. **Do not proceed past step 5 with `open` blocking Qs.**
4. **Research.** Shortlist 4-6 candidates (from `shortlist` input if given), always including one "boring/default" and one "fit-for-constraint" specialist. Per candidate: `WebSearch` for current state (last 12 months — maintenance, latest stable version, CVEs, breaking-change cadence, production users, license, community); `WebFetch` the project's own docs/repo (version + maintenance) and one independent source. Cite every claim with URL + retrieval date; flag evidence >12 months old as stale. Drop candidates failing a hard constraint (license incompat, abandoned >12mo, missing runtime, scale ceiling), recording why.
5. **Score and rank** 2-4 finalists on a 1-5 rubric, weighted by constraint priority: fit to functional reqs; fit to NFRs (perf/scale/latency/footprint); maintenance health; ecosystem; team familiarity/learning curve; operational cost; lock-in/exit cost; security posture. Output a comparison table + one-line "why this could be wrong" per finalist.
6. **Recommend** a primary + runner-up, referencing ≥1 requirement or earlier decision, stating explicitly what is traded away.
7. **Approval gate** (`interactive`). Present in chat: constraint set, shortlist with drop reasons, ranked finalists table, recommendation + runner-up with "why this could be wrong", then prompt: `1) accept recommendation  2) pick runner-up  3) pick other finalist  4) reopen — change constraints / add candidates  5) defer`. **No write to `decision-log.md` until the user picks 1-3.** On 4, loop to step 2; on 5, mark deferred via `questions(op=defer)`. `recommend` mode: skip gate, return ranked list only. `confirm-existing`: run the rubric on the user's pick; if it fails a hard constraint or scores materially below an alternative, escalate to `interactive`.
8. **Record decision.** On approval, append to `{id}-decision-log.md`:

   ```
   ## tech-{topic}-{slug}
   **Decision:** {chosen tech} {version-pinned-or-range}
   **Topic:** {topic}
   **Date:** {YYYY-MM-DD}
   **Approved-by:** {user handle or "user-in-chat"}
   **Mode:** {interactive|confirm-existing}
   **Constraints honored:** {bullet list, marking any `assumed:` ones}
   **Rationale:** {3-6 lines tying the pick to specific requirements / earlier decisions}
   **Alternatives considered:**
     - {runner-up} — rejected because {reason}
     - {other} — rejected because {reason}
     - {dropped early} — failed hard constraint: {which}
   **Risks accepted:** {top 1-3, copy to plan.md § Risks via `plan risk` if rated ≥ medium}
   **Revisit-trigger:** {condition forcing re-evaluation, e.g. "if scale > 10k rps", "if license changes"}
   **Sources:** {urls with retrieval date}
   ```

9. **Propagate.** Resolve question(s) via `questions(op=resolve, decision=tech-{topic}-{slug})`; new risk → `plan risk`; invalidated frozen artifact → `evolve` (never silent rewrite); update `summary.md` "Stack"/"Current State" so future `trace-context` sees the pick.

## Output
`{id}-decision-log.md` entry (format above), `{id}-questions.toml` updates, research block in `{id}-analysis.md`, plus:

```
── tech-select ──
Ticket: {id}
Topic: {topic}
Mode: {interactive|recommend|confirm-existing}
Status: {recommended | awaiting-approval | approved | deferred | blocked-on-question}
Pick: {chosen or "—"}
Runner-up: {…}
Decision-ref: {decision-log slug or "—"}
Open questions: {count}  Risks added: {count}
Next: {next skill / agent}
```

## Gate
No decision recorded without an explicit user pick in `interactive` mode — silence is **not** approval; re-prompt once, then mark `deferred`. Sensitive choices (auth, crypto, PII storage, payment) additionally require an explicit "I accept the security/compliance implications" from the user before recording.

## Rules
- One topic per call; bundled asks ("pick the whole stack") split into a dependency-ordered queue (language → runtime → web framework → ORM → DB → …), feeding earlier picks into later `constraints`.
- Never invent a version, license, or maintenance status — cite a URL or omit the claim.
- Always keep ≥1 rejected alternative on record; a one-option "decision" is a red flag — escalate to the user.
- Every decision declares a `Revisit-trigger` — decisions without one rot.
- User overrides the recommendation → record their choice as the decision, move the recommendation to Alternatives with reason `user-override: {their reason}`; don't argue in the log.
- Coherence check before recording: diff the pick against existing decisions in this and linked tickets; conflict → stop and run `clarify` or `evolve` on the conflicting decision first.

**Version:** 1.1 — lean rewrite | **Updated:** 2026-08-23
