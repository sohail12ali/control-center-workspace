---
name: risk-scan
description: Extract and rate risks across a ticket's artifacts. Feeds the Risks section of plan.md and surfaces blockers early. Lightweight, always-on scan — use during planning and re-run after every `evolve`. Distinct from `challenge-plan`'s deeper adversarial pass (sequencing, traceability, layer-violation, etc.) — this skill only extracts and rates already-stated risk language; it doesn't hunt for structural plan defects.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Scan `analysis.md` (Findings), `decision-log.md` (Alternatives rejected), `requirements.md` (NFRs), `progress.md` (Blockers), and — if present — `{T}-critique-report.md` § Plan critique for risk language.
2. If `challenge-plan` has run, pull forward any `critical-path` or `rollback-gap` findings from the critique report as candidate risks (cite the `CR-{n}` id as the source instead of re-deriving).
3. For each risk, score:
   - likelihood: low / med / high
   - impact: low / med / high
4. Rank by likelihood × impact.
5. For top risks (high×high, high×med, med×high), require explicit mitigation; flag any without one.
6. Write/update `plan.md` Risks section as a table: Risk / Likelihood / Impact / Mitigation / Owner / Source.

# Output
Ranked risk list and any risk missing a mitigation.

# Rules
- Don't invent risks; cite the artifact line (or `CR-{n}`) that surfaced each.
- Risks without mitigation block stage advance to TEMPLATE.
- If a risk is realized, route to `fix` and `evolve`.
- If a structural plan defect surfaces here that isn't just a stated risk (e.g. a sequencing or traceability gap), don't rate it as a risk — hand it to `challenge-plan` instead so it gets a proper `CR-{n}` finding.
