---
name: tech-select
description: Decide a technology choice for a ticket — language, framework, library, package, design pattern, architecture style, API framework, UI framework, database, infra, auth, queue, cache, observability, build tool, test runner, etc. Researches the web for current best fits, surfaces 2-4 ranked options with tradeoffs, asks the user blocking questions via `manage-questions`, gates on explicit user approval, and records the final pick to `decision-log.md` with rationale and rejected alternatives. Use whenever an artifact needs a "what should we use for X?" answer — works for new projects (greenfield stack picks) and existing projects (adding/replacing a component).
---

# Inputs
- `id` (required): ticket id
- `topic` (required): what is being chosen — e.g. `language`, `web-framework`, `orm`, `database`, `state-mgmt`, `auth`, `queue`, `cache`, `observability`, `ui-kit`, `design-pattern:retry`, `architecture`, `api-style`, `package:pdf-parse`, `test-runner`, `ci`, `deploy-target`. Free-form; one decision per call.
- `constraints` (optional): hard constraints provided by caller — runtime, license, budget, team skills, perf SLO, compliance, hosting, latency, scale, existing stack to fit, must-not-use list. If absent, the skill will derive them from `summary.md` / `requirements.md` / `analysis.md` and confirm with the user.
- `mode` (optional, default `interactive`): `interactive` (ask user, gated) | `recommend` (return ranked options without asking, no decision recorded) | `confirm-existing` (validate a choice the user already proposed against constraints).
- `shortlist` (optional): caller-provided candidates to evaluate. If absent, the skill builds the shortlist itself.

# Storage
- Reads: `{id}-summary.md`, `{id}-requirements.md`, `{id}-analysis.md`, `{id}-decision-log.md`, `{id}-questions.md`, plus any prior tech decisions in this or linked tickets (avoid contradictions).
- Writes: `{id}-decision-log.md` (final decision), `{id}-questions.md` (blocking Qs via `manage-questions`), and a transient research block in `{id}-analysis.md` under `## Research / tech-select: {topic}` so the evidence is auditable.

# Steps

1. **Load context.** Run `trace-context` for `{id}`. Pull existing tech decisions from this ticket and any `[[linked]]` tickets to keep the stack coherent. Reject the call early if `summary.md` is missing.

2. **Frame constraints.** Build a constraint set from (a) caller `constraints` input, (b) requirements (functional + non-functional, especially perf / scale / compliance / SLA), (c) existing stack already locked in earlier decisions, (d) team-skill / license / hosting hints in `summary.md`. List any **inferred** constraints separately and mark them `assumed:` — these become candidate questions.

3. **Decide if questions are needed.** If a constraint is load-bearing for the choice and not stated, file it via `manage-questions(op=add, stage=current)` and also surface it in chat. **Do not proceed past step 5 with `open` blocking Qs.** Examples that almost always block: target deployment env, expected scale, team's primary language, data-shape (relational vs document vs time-series), self-hosted vs managed, license tolerance (GPL/AGPL?), budget ceiling.

4. **Research.**
   - Build a shortlist: start from `shortlist` input if given, else 4-6 candidates known to the agent. Explicitly include at least one "boring/default" choice and one "fit-for-constraint" specialist.
   - For each candidate run `WebSearch` for current state (last 12 months): maintenance status, latest stable version, recent CVEs, breaking-change cadence, known production users, license, community size signal. Use `WebFetch` on the project's own docs/repo to confirm version + maintenance, and on one independent source (benchmark, comparison, post-mortem). Cite every claim with URL + retrieval date.
   - **Drop candidates** that fail a hard constraint (license incompat, abandoned >12mo, missing required runtime, scale ceiling below requirement). Record why each was dropped.

5. **Score and rank** the survivors (2-4 finalists) on a fixed rubric. Use a 1-5 scale, weight by constraint priority:
   - Fit to functional requirements
   - Fit to non-functional (perf, scale, latency, footprint)
   - Maintenance health (release cadence, issue close rate, last commit)
   - Ecosystem / library availability
   - Team familiarity (or learning curve cost)
   - Operational cost (hosting, license, ops burden)
   - Lock-in / exit cost
   - Security posture (CVE history, supply-chain hygiene)

   Output a comparison table. Include a one-line "why this could be wrong" per finalist (the strongest counter-argument).

6. **Recommend.** Pick a primary recommendation and a runner-up. The recommendation must reference at least one requirement or earlier decision. State explicitly what you are trading away.

7. **Approval gate (mode=`interactive`).** Present to the user in chat:
   - The constraint set used (so they can challenge it).
   - The shortlist with drop reasons.
   - The ranked finalists table.
   - The recommendation + runner-up with the "why this could be wrong" lines.
   - A numbered choice prompt: `1) accept recommendation  2) pick runner-up  3) pick other finalist  4) reopen — change constraints / add candidates  5) defer`.

   **Do not write to `decision-log.md` until the user picks 1-3.** On `4` loop back to step 2 with the user's new input. On `5` mark the topic deferred via `manage-questions(op=defer)`.

   In `mode=recommend`, skip the gate and return the ranked list only. In `mode=confirm-existing`, run the rubric against the user's proposed pick; if it fails a hard constraint or scores materially below an alternative, escalate to `interactive`.

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
   **Risks accepted:** {top 1-3, copy to `risk-scan` if rated ≥ medium}
   **Revisit-trigger:** {condition that should force a re-evaluation, e.g. "if scale > 10k rps", "if team adds a Rust hire", "if license changes"}
   **Sources:** {urls with retrieval date}
   ```

9. **Propagate.**
   - Resolve the corresponding question(s) via `manage-questions(op=resolve, decision=tech-{topic}-{slug})`.
   - If the choice introduces a new risk, hand to `risk-scan`.
   - If the choice invalidates a frozen artifact (requirement, plan task), call `evolve` on that artifact — never silently rewrite it.
   - Update `summary.md` "Stack" / "Current State" line so future `trace-context` calls see the pick.

# Output

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

# Rules

- One topic per call. If the caller bundles topics ("pick the whole stack"), split into a dependency-ordered queue (language → runtime → web framework → ORM → DB → …) and run this skill per topic, feeding earlier picks into `constraints` for later ones.
- Never invent a candidate's version, license, or maintenance status — cite a URL or omit the claim.
- Web evidence older than 12 months must be flagged stale; prefer the project's own latest release notes.
- No decision is recorded without an explicit user pick in `interactive` mode. Silence is **not** approval. Re-prompt once, then mark `deferred`.
- Always keep at least one rejected alternative on record — a one-option "decision" is a red flag and must be escalated back to the user.
- Every decision must declare a `Revisit-trigger`. Decisions without a trigger rot.
- If the user overrides the recommendation, record their choice as the decision and move the recommendation to `Alternatives considered` with reason `user-override: {their reason}`. Do not argue in the log.
- Coherence check: before recording, diff the pick against existing decisions in this and linked tickets. Conflict → stop and run `clarify` or `evolve` on the conflicting decision first.
- Sensitive choices (auth, crypto, data-storage of PII, payment) require an explicit "I accept the security/compliance implications" from the user before recording.

# Wiring

- `analyst` may call this skill during GROUND/CLARIFY when a requirement depends on an unmade tech choice.
- `planner` calls this skill during CANONICAL before writing tasks that presuppose a specific tech.
- `builder` calls this skill (mode=`confirm-existing`) when about to introduce a new dependency that isn't in the decision-log.
- `fixer` calls this skill when the root cause is "wrong tech" and a swap is on the table.
- `harness` routes here whenever `handoff` reports a blocking "tech choice undecided" gate.
