---
ticket: "T-029"
artifact: verification
---

# Verification: T-029

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | AC-1 no stale one-shot claim about the tab in about.js | MET (static) | `about.js:198-217`; repo grep for "headless one-shot" / "No live steering" now hits only README one-shot launcher text (`console/README.md` Agents section), `agents.py:22`, `.claude/skills/console/SKILL.md:18` — all about `agents launch` |
| 2 | AC-2 "planned native shell" gone | MET (static) | `console/README.md:14-21`; grep "planned native shell" -> only the audit plan file |
| 3 | AC-3 four doors + naming traps | MET (static) | `console/README.md:667` onward |
| 4 | AC-4 agents.js comment | MET (static) | `agents.js:16-19` |
| 5 | AC-5 docs-contract test passes | NOT RUN | no shell in this session; static read: test needs `**No live steering (one-shot launcher only).**` present and `**No worktree isolation.**` absent in README — both unchanged by this edit |

## Test Results
Not run. `console/tests/test_docs_agree_with_config.py` is the only test that reads `console/README.md`; no test reads `about.js` or `agents.js` (grep of `console/tests`).

## Claim -> code evidence
- Ticketed chat -> worktree, fallback to root with reason: `agent_manager.py:65-81`, `:142-146`; ticket passed from tab: `features/agents_feature.py:196`.
- `agents launch` has no steer/worktree/gate, plan default: `agents.py:22-31`, `kanban.py:405-406`, `agents.py:268` (cwd = root or given), `config/agents.toml:105,205` (`default_mode = "plan"`).
- Assistant -> `agent_manager.create`: `features/assistant_feature.py:273`; `delegate`/`launch_role`: `verb_handlers.py:168,230,331,354`; Run points at chat/job: `runs.py:1-6`; Telegram: `telegram_bot.py:356,375`.
- Naming traps: `backends/__init__.py:1-2` (ticket storage), `jobs.py:1` (queue for verbs), `agents.py:34` (`_JOBS`), `runs.py:1`.

## Edge Cases Probed
- Not verified in a browser (no preview run); About render is JS string/element edits only.

## Notes
Not closed: verification incomplete (AC-5 unrun, no visual check).

## Links
- [[T-029-summary]] · [[T-029-analysis]] · [[T-029-requirements]] · [[T-029-decision-log]] · [[T-029-plan]] · [[T-029-progress]] · [[T-029-verification]]
