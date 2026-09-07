---
tags: [active]
status: Complete
ticket: "T-004"
---

# T-004: Assistant brain: persona, /api/assistant, fast commands, Settings backend picker, memory

**Status:** Complete  
**Stage:** VERIFY (closed) complete, amended — ready for TEMPLATE (build)  
**Owner:** Sohail Ali  
**Created:** 2026-09-06  
**Due:**  

## Overview

Assistant brain: a console-owned persona, `/api/assistant` (say/session/new/stream/memory), a deterministic fast-command table, a Settings backend picker (service half), and file-based memory — typed-first, testable with no mic and no native bridge. Binding plan: `T-004 — Assistant brain (typed first, voice later)` in `our-project-is-in-optimized-treasure.md`. **Reply-path speaking (FR-8) and the Settings-tab UI picker (FR-7 AC2) are deferred to T-006** (amendment 2026-09-06).

## Current State

CANONICAL complete: `T-004-components.md` (12 components, dependency graph, C1 bottleneck, C5/C9 flagged novel/no-analogue), `T-004-task-breakdown.md` + `T-004-implementation-plan.md` (originally 41 tasks/47.5h Dev), `T-004-effort-estimate.md` (originally 85.0h Final/Complete, ≈2-3.5x the programme's pre-decomposition "M · 3 d" sizing). Put to the user before any build started; **amended 2026-09-06** ([[T-004-decision-log]] § Amendment 2026-09-06, via `evolve`): FR-8 (C9 — reply-path watcher, `is_assistant` flag, `assistant.js`, `spoken_form()`) deferred in full to T-006; FR-7 AC2 (C7's Settings-tab UI picker) deferred to T-006, C7's service half (`assistant.toml` + `GET`/`POST /api/assistant/settings`) stays in T-004. 2 new FR-6 ACs added for defects observed this session: the `kickoff` verb's artifact-map insertion must be `## Active`-heading-relative, and a regression guard for the `New-FromTemplate.ps1` double-encoding fix (BOM + mangled dashes under Windows PowerShell 5.1, already fixed and re-encoded this session). Post-amendment: **36 tasks, 40.5h Dev** (`T-004-effort-estimate.md`'s 85.0h Final/Complete figure is stale, flagged not recomputed). No T-004 code exists yet. Ready for TEMPLATE: hand off to builder, Phase 1 first (C1's `system_append`/`extra` threading is the bottleneck — build it first in isolation).

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
