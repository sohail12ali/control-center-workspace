---
ticket: "{ID}"
artifact: requirements-draft
status: drafting
freeze_status: open
iteration: 0
created: "{DATE}"
last_updated: "{DATE}"
---

# Requirements Draft: {ID}

> Working requirements document. **Not frozen.** Expect revisions each iteration until `freeze-requirements {ID}` passes.

**Command reference:**
- **Created by:** `draft-requirements {ID}`
- **Grounded by:** `analyze-context {ID}` → writes `{ID}-context-snapshot.md`
- **Gaps surfaced by:** `identify-gaps {ID}`
- **Challenged by:** `challenge-requirements {ID}` (adds ⚠ markers below)
- **Enriched by:** `enrich-requirements {ID} [source]`
- **Cross-checked by:** `compare-with-existing {ID}`
- **Iterated by:** `iterate-requirements {ID} "feedback"`
- **Frozen by:** `freeze-requirements {ID}` → produces `{ID}-requirements-summary.md`

**Legend:** `⚠` challenge finding · `〈TBD〉` placeholder awaiting enrichment or stakeholder answer · `[[link]]` grounded fact with source

---

## 1. Intent

**Stakeholder (one line):** _what outcome they want_

**Business driver:** _why now_

**Raw intent verbatim:**
> _original request from stakeholder, preserved unedited_

## 2. Context Summary

(Condensed from [[{ID}-context-snapshot]])

- **Similar existing features:** _list with wikilinks_
- **Affected code areas:** _module / layer names_
- **Known risks from history:** _prior-ticket / git findings_

## 3. Scope

### In scope
- _bullet_

### Out of scope (explicit)
- _bullet — why not_

### Assumptions
- _bullet — confirm with stakeholder_

## 4. Functional Requirements

Number each `FR-{n}`. Each must be independently verifiable.

### FR-1: _Title_
**Description:** _what the system must do_

**Actor:** _role_

**Trigger:** _event / user action_

**Preconditions:**
- _bullet_

**Flow:**
1. _step_
2. _step_

**Postconditions / observable outcomes:**
- _bullet_

**Acceptance criteria (testable):**
- [ ] _criterion_
- [ ] _criterion_

**Business rules invoked:** BR-{n}, BR-{n}

## 5. Non-Functional Requirements

| Category | Requirement | Target | Notes |
|---|---|---|---|
| Performance | | 〈TBD〉 | |
| Scalability | | | |
| Security / Auth | | | |
| Auditability | | | |
| Availability | | | |
| Usability | | | |
| Compliance | | | |

## 6. Data Requirements

### Entities (new / changed)
| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| | new / exists | | create/update/archive | |

### Data flows
_source → transformation → sink_

### Retention / archival
_duration, location_

## 7. Business Rules

Number each `BR-{n}`. Each is atomic.

- **BR-1:** _rule in natural language_

## 8. Edge Cases

- _bullet — expected behaviour_

## 9. Interactions with Existing Features

(Populated by `compare-with-existing {ID}`)

| Existing feature | Interaction | Risk | Action |
|---|---|---|---|
| [[…]] | overlap / conflict / reuse | low/med/high | modify / isolate / defer |

## 10. External Dependencies

- _system, API, team — what we need from them, when_

## 11. Stakeholders

| Role | Name/Team | Concern | Sign-off required |
|---|---|---|---|
| | | | yes / no |

## 12. Open Questions (mirrored)

Mirrored from [[{ID}-questions]]. Blocker questions must be resolved before freeze.

- Q{n}: _text_ — status: open | answered | resolved

## 13. Challenge Findings (⚠)

(Appended by `challenge-requirements {ID}`. Each must be resolved or explicitly accepted before freeze.)

- ⚠ _finding_ — **resolution:** 〈TBD〉

## 14. Draft History

See [[{ID}-iteration-log]] for per-iteration diff + rationale.

Current iteration: **{iteration}**

---

## Freeze Checklist (run by `freeze-requirements`)

- [ ] All `〈TBD〉` placeholders replaced or explicitly deferred
- [ ] All ⚠ findings resolved or explicitly accepted with rationale
- [ ] All blocker open questions answered
- [ ] Every FR has at least one testable acceptance criterion
- [ ] Every NFR has a concrete target or documented reason for absence
- [ ] Every new/changed entity has a canonical reference or creation plan
- [ ] Out-of-scope list is non-empty
- [ ] Stakeholder sign-off recorded
- [ ] `{ID}-requirements-summary.md` generated for `extract-stories` consumption

## Links
- [[{ID}-summary]] · [[{ID}-analysis]] · [[{ID}-requirements-draft]] · [[{ID}-context-snapshot]] · [[{ID}-gap-analysis]] · [[{ID}-iteration-log]] · [[{ID}-decision-log]] · [[{ID}-questions]] · [[{ID}-plan]] · [[{ID}-progress]] · [[{ID}-verification]]
