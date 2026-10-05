---
ticket: "T-021"
artifact: verification
---

# Verification: T-021

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| FR-1 | description-too-long WARN at 301 chars, skills only | PASS | `console/tests/test_harness_lint.py` `TestDescriptionLength`; `harness lint` 0 errors, 20 warnings |
| FR-2 | task-boundary rule in plan, pointer from breakdown-tasks | PASS | `console/tests/test_task_boundary_text.py` |
| FR-3 | stale docs fixed, OpenRouter ships enabled | PASS | `console/tests/test_docs_agree_with_config.py` |
| FR-4 | README joins roster-count check | PASS | `console/tests/test_harness_lint.py` `TestReadmeCounts` |
| FR-5 | assistant persona fits cap and carries the untrusted-content clause | PASS | `console/tests/test_persona_fit.py` |
| FR-6 | ticket liveness module, verb, digest | PASS | `console/tests/test_ticket_liveness.py`; sweep liveness column matches `verb run ticket-liveness` (T-015, T-016, T-019 `no_action_path`) |
| FR-7 | blocked move refused without a next action | PASS | `console/tests/test_ticket_gate.py` `TestBlockedGate` |
| FR-8 | close-check parsers, evaluate, verb | PASS | `console/tests/test_close_check_parse.py`, `console/tests/test_close_check.py` |
| FR-9 | terminal move runs close-check | PASS | `console/tests/test_ticket_gate.py` `TestCloseGate` |
| FR-10 | close-override | PASS | `console/tests/test_close_override.py` |
| FR-11 | protocol text | PASS | `console/tests/test_close_protocol_text.py`; `harness lint` 39 skills, 7 agents, 0 errors |
| Calibration | 22 done tickets | PASS | sweep: pass_rows=191, evidence_empty=0, evidence_phantom=0, prose_only=157 (82.2%). Historical `criterion_not_pass` blocks on already-done tickets were left in place. `files changed: 0` |

## Test Results

## Edge Cases Probed
- 

## Notes

## Links
- [[T-021-summary]] · [[T-021-analysis]] · [[T-021-requirements]] · [[T-021-decision-log]] · [[T-021-plan]] · [[T-021-progress]] · [[T-021-verification]]
