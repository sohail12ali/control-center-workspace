---
name: identify-gaps
description: Surface missing stakeholders, business rules, edge cases, NFRs, data flows, integrations, compliance gaps, and existing-feature overlap/conflict/reuse in the requirements draft. Pre-freeze. Re-run after each iterate-requirements pass.
---

# Inputs
- `id` (required): ticket id

# Steps
1. Read `{id}-requirements-draft.md` and `{id}-context-snapshot.md`.
2. Copy `knowledge-center/artifacts/_template/gap-analysis.md` into `{id}-gap-analysis.md` if missing; otherwise update in place (preserve the Resolution Log).
3. Walk each internal-completeness category and record gaps:
   - **Stakeholders** — roles named in context/codebase that the draft omits; impacted users not listed.
   - **Business rules** — quantities, thresholds, ordering rules, state transitions implied by FRs but not stated.
   - **Edge cases** — concurrency, network/partial failures, idempotency, empty/over-limit inputs; compare against similar-feature history.
   - **Non-functional** — every NFR row that is `〈TBD〉` or missing a number.
   - **Data / entities** — FKs unspecified, lifecycle unspecified (create/update/archive), no canonical reference.
   - **Integrations** — external systems named in context that the draft doesn't address.
   - **UX / UI** — error messaging, offline/degraded-network handling, accessibility.
   - **Compliance / audit** — retention, sensitive-data scope, regulatory logging.
   - **Cross-cutting** — feature flags, backfill, rollback.
4. **Existing-feature overlap check** (external-completeness lens, same pass): for each FR, compare against similar feature entry points already in the codebase, existing components touching the same data/entities, and prior ticket artifacts under `knowledge-center/artifacts/*/` covering related areas (per `{id}-context-snapshot.md`'s Similar existing features / prior tickets). Classify each interaction:
   - **overlap** — an existing feature already does some or all of what the FR asks; candidate for reuse or extension.
   - **conflict** — the new FR would break a contract or invariant an existing feature relies on.
   - **reuse** — an existing component (validator, base class, shared service, UI pattern) can be used as-is.
   - **isolation** — shares terminology but serves distinct users/flows; document the boundary.
   Write findings to `{id}-requirements-draft.md` § Interactions with Existing Features (table): existing feature (wikilink), interaction, risk (low/med/high), action (modify existing / extend / isolate / defer / reject). Populate the section even when there's no overlap at all — state that explicitly, don't leave it blank. For each **reuse** hit, add the wikilink to the draft's FR/Data sections so task breakdown later knows about it. Never delete or rewrite existing FR text here — only add cross-references and the Interactions table.
5. Assign severity to each internal gap:
   - 🔴 **blocker** — would change scope, entity shape, FR behavior, or NFR targets.
   - 🟡 **important** — would change acceptance criteria or test plan.
   - 🟢 **minor** — cosmetic or deferrable.
   Every **conflict** from step 4 is always a 🔴 blocker, filed under gap-analysis's Cross-cutting category.
6. For every 🔴 blocker (internal or conflict), add a matching entry to `{id}-questions.md` (stage: `requirements`, priority: `critical` for internal blockers, `high` or `critical` for conflicts).
7. Update the Summary table counts (gaps by severity, interactions by category).
8. Append an entry to `{id}-iteration-log.md` under the current iteration (no iteration bump).

# Output
```
── identify-gaps ──
Ticket:       {id}
Total gaps:   {N}  (🔴 {b} / 🟡 {i} / 🟢 {m})
Interactions: {N}  (overlap {o} / conflict {c} / reuse {r} / isolation {i})
New questions opened: {N}
Next:         clarify {id} (answer blockers/conflicts) → iterate-requirements {id} "answers"
```

# Rules
- Every category row in the Summary table is filled, even if 0 — absence of a gap is a claim too.
- Every 🔴 gets a matching question entry.
- Don't silently edit the draft here — gaps and interactions are recorded, not fixed. `iterate-requirements` applies fixes.

**Delegates to:** none
**Next:** `clarify` (resolve blockers/conflicts) → `iterate-requirements`
