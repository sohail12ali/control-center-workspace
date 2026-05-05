---
name: risk-scan
description: Extract and rate risks across a ticket's artifacts. Feeds the Risks section of plan.md and surfaces blockers early. Use during planning and re-run after every `evolve`.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Scan `analysis.md` (Findings), `decision-log.md` (Alternatives rejected), `requirements.md` (NFRs), and `progress.md` (Blockers) for risk language.
2. For each risk, score:
   - likelihood: low / med / high
   - impact: low / med / high
3. Rank by likelihood × impact.
4. For top risks (high×high, high×med, med×high), require explicit mitigation; flag any without one.
5. Write/update `plan.md` Risks section as a table: Risk / Likelihood / Impact / Mitigation / Owner.

# Output
Ranked risk list and any risk missing a mitigation.

# Rules
- Don't invent risks; cite the artifact line that surfaced each.
- Risks without mitigation block stage advance to TEMPLATE.
- If a risk is realized, route to `fix` and `evolve`.
