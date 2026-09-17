---
ticket: "T-016"
artifact: verification
---

# Verification: T-016

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| FR-1 | `in-shell` default is Assistant tab; without the class, `NAV_ORDER` unchanged; `say` still Assistant session | PASS (unit/integration) / PENDING (native window) | `NAV_ORDER[0]==overview` and `"assistant" not in NAV_ORDER` (`shell_feature.py`). `app.js` `orderManifest` sorts on `html.in-shell`. `register_tab("assistant")` in `assistant_feature.py`. `/api/assistant/say` unchanged (`test_assistant.py` say reuse). Native first-paint not exercised this pass (TC-E-001). |
| FR-2 | Shared Run record; Assistant can name id+state; survives restart | PASS | `console/server/runs.py` JSON under `console/.cache/runs/`. Delegate wrap `answer["run"]` (`verb_handlers.py`). `_compose_extra` `## Runs` (`test_assistant.py::test_runs_section_names_id_and_state`). `GET /api/runs` (`test_ui_endpoints.TestAssistantHomeAndRuns`). |
| FR-3 | `startAgentFor` not compose+`go("agents")` only; ticket-scoped | PASS | `board.js` posts `/api/verbs/delegate/run` with `ticket`, then `/api/assistant/say`; compose is last fallback (`test_plugins.test_board_start_is_not_compose_only`). |
| FR-4 | Agents list shows Run ids; resume still works | PASS | `agents.js` `refreshChats` fetches `/api/runs`; `openRun` calls `resumeChat` when orphaned+resumable. `resumeChat` unchanged (`POST .../resume`). |
| FR-5 | Four mutation verbs as MCP tools; invalid lane fails like `tickets.move`; pytest | PASS | `test_mutation_verbs.py` + MCP names `console_ticket_move` etc. |
| FR-6 | `cursor-agent` + persona; missing binary named fail; no claude fallback; seven agent files | PASS | `test_runs.TestLaunchRole` (missing → "fallen through", no Run) and `TestLaunchRoleSuccess` (persona=analyst, backend=cursor-agent). `.claude/agents/` count unchanged (no new agent files). |
| FR-7 | Wiki has no "live Agents session" tray lock; T-016 wikilinks | PASS | `test_plugins.test_wiki_has_no_live_agents_session_tray_lock`. `console/config/assistant.md` Run / `console_launch_role` line. |

## Test Results

- 2026-09-11: `python -m pytest -o addopts="" console/tests/test_runs.py console/tests/test_mutation_verbs.py console/tests/test_plugins.py console/tests/test_assistant.py console/tests/test_ui_endpoints.py console/tests/test_verbs.py::TestShippedRegistry console/tests/test_assistant_commands.py` → **268 passed**.
- 2026-09-11: `test_stylesheet.py` → pass after adding `.as-home`.
- 2026-09-11: `test_mcp.py`, `test_agent_tools.py`, `test_harness_lint.py`, `test_assistant_reply.py` → pass (stylesheet was the only fail, then fixed).

## Edge Cases Probed
- Invalid lane on ticket-move
- launch-role unknown role and missing cursor-agent (no silent claude)
- Bad Run executor
- Empty run list GET
- Assistant extra omits `## Runs` when none exist

## Notes
- close-work not run (ASK-gated). Deploy not requested.
- T-015 paths (tray probe, HUD, `settings_get`) not edited.
- TC-E-001 (open the Tauri window and confirm Assistant is first) was not run in this session.

## Links
- [[T-016-summary]] · [[T-016-analysis]] · [[T-016-requirements]] · [[T-016-decision-log]] · [[T-016-plan]] · [[T-016-progress]] · [[T-016-verification]] · [[T-016-test-cases]]
