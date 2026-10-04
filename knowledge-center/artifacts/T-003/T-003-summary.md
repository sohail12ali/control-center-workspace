---
tags: [completed]
status: Complete
ticket: "T-003"
closed_date: "2026-09-06"
---

# T-003: Shell hygiene: no stray console, per-OS launch path, close T-001/T-002

**Status:** Complete
**Stage:** VERIFY clean, closed — 6/10 FRs PASS, 2/10 PASS-with-PENDING-subpart (FR-2, FR-7), 2/10 accepted PENDING (FR-8 CI-push-proof, FR-10 T-002 closure), 0 FAIL, 0 blockers
**Owner:** Sohail Ali
**Created:** 2026-09-06
**Due:**

## Overview

Shell hygiene: remove the stray console window (confirmed cause A — debug-only `windows_subsystem`), add a file logger + `--console` escape hatch + descope-safe single-instance guard, apply defensive no-window hygiene to 6 Python spawn sites (cause B did not reproduce), define a per-OS launch path, add a 3-OS CI build, and close T-001/T-002. Grounded in the user-approved programme plan `our-project-is-in-optimized-treasure.md § T-003 — Shell hygiene`.

## Current State

Requirements frozen at iteration 1 ([[T-003-requirements]]) — 10 FRs, 12 NFR rows, 8 BRs, 0 open ⚠, 0 open questions, 0 unresolved gaps. 8 user stories extracted ([[T-003-user-stories]]). Planning went **multi-layer** (5 toolchain-distinct layers: Rust host, Python server, per-OS launch scripts, CI, ticket-closure) via `analyze-components` ([[T-003-components]], 15 components) → `estimate(mode=upfront)` ([[T-003-effort-estimate]], 81.2h Final/Complete envelope) → `breakdown-tasks` ([[T-003-task-breakdown]] + [[T-003-implementation-plan]], 17 tasks / 21h dev effort across 5 phases). `challenge-plan` found 3 findings (0 critical / 1 major / 2 minor) — all resolved or accepted in place ([[T-003-critique-report]] § Plan critique, [[T-003-plan-iteration-log]]). Gate clear.

Build (TEMPLATE/SIMPLIFY) complete: 15/17 tasks done, `python -m pytest` 758→783 passed (0 regressions), `cargo test` 3/3, `cargo build --release` clean. Phase 5 (close T-001/T-002) deferred to VERIFY by design ([[T-003-decision-log]]).

VERIFY clean: `challenge-implementation` (0 critical findings), fresh `verify` re-run (783/783 pytest, 3/3 cargo test, live smoke on the release exe — zero visible console windows, close-to-tray, force-kill cascade, `--console`, single-instance all confirmed), `validate-artifacts` (structure + links, 1 dangling wikilink fixed), `reconcile` (ticket lane drift fixed). T-001 closed this pass (`close-work T-001`, all 8 ACs PASS). T-002 intentionally left open — UIA tray-menu drive attempted and failed (no drivable element found, stronger negative than T-002's own prior finding), dated manual-smoke checklist written to [[T-002-verification]] instead, PENDING rows labeled `PENDING — user click-through`, `close-work T-002` NOT run per explicit instruction.

## Close note (2026-09-06)

Closed by `@harness` after a clean VERIFY handoff. FR-8 (CI job "green on all 3 runners") and FR-10 (T-002 fully closed) are accepted PENDING, not FAIL — both are genuinely gated on actions outside this session (an ASK-gated push; the user's own manual click-through), recorded in [[T-003-decision-log]] § "T-003 closes with FR-8 and FR-10 accepted PENDING, not FAIL". Everything else in scope shipped: cause-A fix, file logger, `--console` escape hatch, single-instance guard (adopted, not descoped), Python spawn hygiene, per-OS launch scripts, CI job definition, full test suite, docs, and T-001's closure.

## Links
- [[T-003-summary]] · [[T-003-analysis]] · [[T-003-requirements]] · [[T-003-user-stories]] · [[T-003-critique-report]] · [[T-003-decision-log]] · [[T-003-plan]] · [[T-003-components]] · [[T-003-task-breakdown]] · [[T-003-implementation-plan]] · [[T-003-effort-estimate]] · [[T-003-plan-iteration-log]] · [[T-003-progress]] · [[T-003-verification]]

