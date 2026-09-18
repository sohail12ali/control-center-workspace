---
ticket: "T-004"
artifact: plan
---

# Plan: T-004

## Approach

Multi-layer (12 components, a real dependency chain with a bottleneck — `plan`'s flat-mode thresholds don't apply). Build as ten small, independently testable slices, each extending an already-proven in-repo pattern (plugin/route, session-create, verb-with-`needs_confirm`, prompt-budget `extra=`) rather than one large plugin, per `analysis.md`'s Recommended Path. The one plumbing change (`BaseSession` `system_append`/`extra` threading, C1) is the bottleneck and gates most of the other components — build it first, in isolation. C5's fast-command table has no in-repo analogue and carries the ticket's real remaining risk; effort and sequencing are weighted accordingly (`T-004-effort-estimate.md`). Full decomposition, dependency graph, and risk analysis live one file each (CANONICAL) — this file stays a pointer, not a duplicate.

**Amendment 2026-09-06** ([[T-004-decision-log]] § Amendment 2026-09-06, via `evolve`): C9 (reply path, `is_assistant` flag, `assistant.js`, FR-8 in full) deferred in full to T-006; the Settings-tab UI half of C7 (FR-7 AC2) deferred to T-006. Both were flagged novel/no-in-repo-analogue risk concentrations; the user chose to trim scope rather than force the estimate to fit the programme's "M · 3 d" sizing.

## Slices

10 slices (post-amendment; was 11 — Slice 8/C9 deferred to T-006), numbered to match each component's headline user story (`T-004-components.md`'s Slice column = `T-004-user-stories.md`'s US-N). Full task-level detail, effort, and dependencies: [[T-004-task-breakdown]]. Phase/slice/task narrative with file-touch lists: [[T-004-implementation-plan]].

## Tasks, Effort, Acceptance criterion coverage

Owned by [[T-004-task-breakdown]] (36 atomic tasks post-amendment, was 41; `{phase}-{slice}-{task}` IDs) and [[T-004-implementation-plan]] (phase/slice synthesis) for the multi-layer path — not duplicated here. Bottom-up total: **40.5h Dev** (was 47.5h before the amendment); the prior **85.0h Final/Complete** figure in [[T-004-effort-estimate]] is now stale pending a fresh `estimate(mode=forecast)` pass (not recomputed — see that artifact's revision log). AC coverage: every in-scope FR/BR traces to ≥1 task — see implementation-plan's "Acceptance criterion coverage" section for the FR→task map; full bidirectional trace via `validate-artifacts T-004 links`.

## Risks

Owned by `T-004-components.md`'s "Dependency graph analysis" section (bottleneck, novel-component flags, safe build order) and `T-004-effort-estimate.md`'s "Risks widening the upper bound" — not duplicated here. `plan risk` op has not yet been run standalone this turn; run before `challenge-plan` if a separate likelihood×impact table is wanted.

## Dependencies
- Blocks: T-005 (native bridge real impl), T-006 (voice/mic) — both depend on T-004 per the programme plan.
- Blocked by: T-003 (shell hygiene) — stated dependency; its artifacts (`procs.py`, `logger.rs`, `.cache/desktop/*.log`) already exist in the working tree per `analysis.md`, so satisfied in substance though T-003 is not yet `close-work`'d.

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements]] · [[T-004-user-stories]] · [[T-004-components]] · [[T-004-task-breakdown]] · [[T-004-implementation-plan]] · [[T-004-effort-estimate]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
