---
ticket: "T-022"
artifact: gap-analysis
status: closed
created: "2026-10-01"
last_updated: "2026-10-01"
---

# Gap Analysis: T-022

**Sources:** [[T-022-requirements-draft]] · [[T-022-context-snapshot]]

## Summary

| Category        | 🔴 | 🟡 | 🟢 | Total |
|-----------------|----|----|-----|-------|
| Stakeholders    | 0  | 1  | 0   | 1     |
| Business rules  | 0  | 2  | 0   | 2     |
| Edge cases      | 0  | 3  | 0   | 3     |
| NFRs            | 0  | 1  | 0   | 1     |
| Data / entities | 0  | 2  | 0   | 2     |
| Integrations    | 0  | 1  | 1   | 2     |
| UX / UI         | 0  | 0  | 1   | 1     |
| Compliance      | 0  | 0  | 1   | 1     |
| Cross-cutting   | 0  | 0  | 2   | 2     |
| **Total**       | **0** | **10** | **5** | **15** |

## Resolution Log

| Date | Gap ID | Action | Owner |
|------|--------|--------|-------|
| 2026-10-01 | — | Initial pass from `challenge-requirements` (gaps) | analyst |
| 2026-10-01 | G1 | Closed in iteration 1: README rule + `evals replay --changed` in sibling verify steps (recorded in decision-log and FR-14 scope) | analyst |
| 2026-10-01 | G2 | Closed: FR-8 defines "usable and completed" | analyst |
| 2026-10-01 | G3 | Accepted: `text scope any/all`; smoke NOT RUN until Q9 (FR-6 AC) | analyst |
| 2026-10-01 | G4 | Closed: FR-9 unions `git diff` and `git status --porcelain` | analyst |
| 2026-10-01 | G5 | Closed: FR-4 normalizes `\` to `/`; FR-2/FR-11 single-line quotes | analyst |
| 2026-10-01 | G6 | Closed: FR-6 `procs.no_window_flags`, terminate then kill | analyst |
| 2026-10-01 | G7 | Closed: NFR numbers set (delegated defaults) | analyst |
| 2026-10-01 | G8 | Closed: FR-13 pattern list | analyst |
| 2026-10-01 | G9 | Closed: synthetic ticket `EV-001` | analyst |
| 2026-10-01 | G10 | Closed: README coupling note (FR-14); graders limited to calls/text/turn end | analyst |
| 2026-10-01 | G11 | Closed: scenario 10 exercises `skill` | analyst |
| 2026-10-01 | G12 | Closed: FR-15 audit fields | analyst |
| 2026-10-01 | G13 | Closed: FR-15 `grader_version` + rollback | analyst |
| 2026-10-01 | G14 | Closed: FR-1 output shape | analyst |
| 2026-10-01 | G15 | Closed: FR-6 `--model`, `session.init.model` recorded | analyst |

---

## Stakeholders
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G1 | 🟡 | T-020 and T-021 will edit text that scenarios quote (skills, `blocked` contract, failure classifiers) and have no stated rule for who updates a quote | BR/README rule: update the `[[source]]` quote in the same change that edits the rule; `evals replay --changed` in each ticket's verify step |

## Business rules
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G2 | 🟡 | "usable completed turn" (used by BR-8 and FR-8 `model`) is undefined | Define: `turn.end` present, `is_error=false`, not an empty turn |
| G3 | 🟡 | Under `plan` mode a model may answer with `ExitPlanMode` only and make no tool call, so call-based checks (`first_call`) could be unmeasurable; unverified without a login | Prompt wording tuned at first smoke, not the checker; AC: smoke must show ≥ 1 `tool_use` for `trace-context-first`; live ACs verified with fake spawn and recorded NOT RUN until Q9 |

## Edge cases
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G4 | 🟡 | `git diff --name-only` misses untracked/new files, so a newly added skill would not gate | `--changed` unions `git diff --name-only <base>` and `git status --porcelain` |
| G5 | 🟡 | Windows: file paths in tool args use backslashes; scenario regexes would need both; CRLF checkouts break multi-line quotes | Canonical call string normalizes `\` to `/`; quotes single-line; files read in text mode |
| G6 | 🟡 | Timeout / tool-cap termination on Windows unspecified; stray console windows are a known past defect | Spawn with `procs.no_window_flags`; `terminate()` then `kill()` after 5 s (mirror `agent_session.py:476-492`) |

## Non-functional requirements
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G7 | 🟡 | NFR targets TBD: replay duration, live timeout, per-scenario budget cap | Enrich with grounded proposals (marked `⚠ [unrealistic?]`) |

## Data / entities
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G8 | 🟡 | Fixture hygiene scan has no pattern list | Specify: user-profile paths (`C:\Users\`, `/Users/`, `/home/`), `sk-`/`ghp_`-style tokens, `OPENROUTER`, `Bearer ` |
| G9 | 🟡 | Synthetic ticket `T-900` will collide with a real ticket eventually | Use `EV-001` (matches `id_pattern`, never minted by the T-series) |

## Integrations
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G10 | 🟢 | Eval view depends on `Normalizer` shapes that have no tests and may change | Graders read only tool calls, text and `turn.end`; raw fixtures stay valid; note the coupling in README |
| G11 | 🟡 | `skill` field in the scenario format is unused by the starter set (speculative) | Add one skill-level scenario (`evolve-logs-before-editing`) that injects `skill = "evolve"` |

## UX / UI
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G14 | 🟢 | CLI table shape unspecified | Give an ASCII example in FR-1 enrich |

## Compliance / audit
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G12 | 🟢 | Audit record fields for a live run unspecified | Scenario ids, model, backend, outcome, `run_id`; no transcript text |

## Cross-cutting
| ID | Sev | Gap | Proposed resolution |
|----|-----|-----|---------------------|
| G13 | 🟢 | No `grader_version` bump rule or rollback path | Integer constant in `grade.py`, bumped on any semantic change; rollback = remove verb row and `evals` block |
| G15 | 🟢 | `claude` row sets no default model, so unpinned live runs drift | `--model` flag; record `session.init.model` in every result; comparisons require equal models |

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements-draft]] · [[T-022-context-snapshot]] · [[T-022-gap-analysis]] · [[T-022-iteration-log]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
