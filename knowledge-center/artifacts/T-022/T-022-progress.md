---
ticket: "T-022"
artifact: progress
---

# Progress: T-022

## Status Summary
Stage: TEMPLATE done in the tree (13 of 13 plan tasks). Verify is not closed. Live smoke is NOT RUN.

## Dated Log

### 2026-10-01
- Done: GROUND + CLARIFY (requirements frozen, 15 FR); CANONICAL (13-task flat plan, 6 user stories, challenge-plan 12 findings CR-13..CR-24, all folded in).
- Amended requirements: FR-13 (CI gets one replay-only step, added last) and FR-14 (T-020/T-021 cannot run the suite; tasks 12-13 are the retroactive check). Reason: build order T-020 -> T-021 -> T-022 made the frozen wording impossible. See [[T-022-decision-log]] § Amendment.
- Started: nothing built.
- Blocked: tasks 12-13 on T-020 and T-021 (by design: they pin quotes to final prompt text).
- Next: builder on task 01 once T-020 and T-021 are built (or earlier for 01-11 if parallel work is wanted).

### 2026-10-04
- Done: T-022-01 through T-022-13. Package `console/evals/` (`scenario.py`, `grade.py`, `runner.py`), 10 scenarios, 20 fixtures, `evals-replay` verb, CLI `evals list|replay|live`, CI step, README. Quotes pinned to the current prompt files. `python -m pytest -o addopts="" -q console/tests -k evals`: 201 passed (after the must-fail fixture for `stop-on-failed-gate` also called `Skill handoff`, and the `.env` scan stopped matching the substring inside `os.environ`).
- Closing gate: `evals replay` exit 0 in 0.79 s (10/10 pass). `evals list --coverage` agents 7/7, uncovered skills 33. `evals replay --changed` exit 0 and selected all 10, because this worktree also edits `console/evals/**`, which gates every scenario. `harness lint`: 39 skills, 7 agents, 0 errors, 20 `description-too-long` warnings (same set as the T-021 baseline). No 3.12-only syntax in `console/evals` or `console/tests/test_evals*.py` (no f-strings, no `type` statements, no PEP 695, no `itertools.batched`). py3.11 CI result is PENDING until this tree is pushed.
- FR-6 manual smoke: **NOT RUN**. No live `evals live --confirm` against Claude. Q9 and Q10 stay open. One live pass would not be a reliability claim anyway.
- Full suite `python -m pytest -o addopts="" -q`: 2231 passed, 3 failed, 258 s. The first run was 2229 passed / 5 failed. Two of those five were this work and are fixed: `ct-toolgroup` had no CSS rule, and `agent_manager.create` read `credential_reason` on a SimpleNamespace fake. The remaining 3 are `desktop/tests/test_install_launcher.py` (`bash.exe` exit 1, empty stderr). That directory was not part of this build.
- Started: nothing further in this ticket.
- Blocked: live smoke, on a Claude login and a price table (Q9, Q10).
- Next: verifier. Do not point the eval runner at Codex or OpenAI.

## Links
- [[T-022-summary]] · [[T-022-analysis]] · [[T-022-requirements]] · [[T-022-decision-log]] · [[T-022-plan]] · [[T-022-progress]] · [[T-022-verification]]
