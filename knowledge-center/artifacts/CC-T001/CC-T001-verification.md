---
ticket: "CC-T001"
artifact: verification
---

# Verification: CC-T001

**Verified:** 2026-08-29 · **Result:** PASS with two stated gaps (one blocked, one deferred).

## Evidence

| Command | Result |
| --- | --- |
| `python -m pytest` | **166 passed** |
| `python console/kanban.py harness lint` | `39 skills, 7 agents \| 0 error(s), 0 warning(s)` — exit 0 |
| `python console/kanban.py ticket list` | returns CC-T001 |
| `python console/kanban.py agents backends` | both rows, `installed: true`, `launchable: true` |
| `python console/kanban.py overview` | exit 0 |
| `python console/kanban.py telemetry` | `No telemetry recorded yet.` (correct — no chat has run) |
| `python console/kanban.py telemetry skills` | 39 skills listed, all in never-fired |
| `python -c "json.load(open('.claude/settings.json'))"` | parses; keys `['permissions', 'hooks']` |
| YAML parse of `.github/workflows/verify.yml` | jobs `['tests', 'harness', 'cli']` |

Test counts by module: tomlio 16 · tickets 29 · trackers 25 · boards 9 ·
agent_backends 25 · harness_lint 24 · telemetry 32 · agents_catalog 6.

## Acceptance criteria

| Criterion | Status | Evidence |
| --- | --- | --- |
| Permission gates exist and fire | **Met** | `settings.json` `permissions.ask` covers `git push`, `git push --force`, `git commit`, `git reset --hard`, `gh pr create`, `gh pr merge`, `WebFetch`, `WebSearch`; `permissions.deny` covers `.env`, `*.key`, `credentials.json` |
| Console has a green test suite | **Met** | 166 tests, 7 modules, all against a `tmp_path` fixture root — none touch the real vault |
| Harness wiring is machine-checked | **Met** | `harness lint`, clean on the real tree; 24 tests prove each check fires on a planted fault |
| Token and cost measurable per ticket | **Met with a gap** | Module + CLI + session wiring all tested; see Gap 2 |
| Skill pruning has an evidence base | **Met with a gap** | `telemetry skills` works and is tested; it has no data to report until chats run through the console |
| Regressions caught before merge | **Met** | 3 CI jobs + opt-in pre-commit; all run the same commands as local |

## Gaps — stated, not hidden

**Gap 1 — `.claude/settings.local.json` was not written (blocked).**
Moving `defaultMode: acceptEdits` and the sibling-repo `additionalDirectories` into the
user-local settings file was denied by the permission classifier, correctly: it is a
permissions file, and self-granting permissions is exactly what that gate is for. Not
worked around. Tracked as **TD-2** with the exact content to paste. The committed
`settings.json` is complete and correct without it; the missing part is convenience, not
safety.

**Gap 2 — telemetry has never recorded a *live* chat.**
The wiring is proven at the seam that matters: five tests drive a real
`agent_session.build(...)` object through a `turn.end` event and assert the record lands
on disk with the right ticket, skill, persona and token counts. What has *not* happened is
an end-to-end run — a real `claude` subprocess, streaming, writing a record — because that
spends the user's tokens on a real agent run, which was not requested and is not mine to
trigger for a green checkmark. So `telemetry --ticket CC-T001` currently reports nothing,
and the plan's done-criterion "reports non-zero tokens" is **unproven**, not met.
Recorded as an accepted gap in [[CC-T001-decision-log]].

*TD-1, which was the real blocker, is now closed* — the Agents tab composer has a ticket
picker and sends `ticket` on chat creation, so the first chat started from the tab
satisfies the criterion with no further code. Verified live: server on :8799 served
`/api/agents/catalog` with the open-ticket list, `/api/agents/backends` with both rows
installed, index and `agents.js` at 200, and the mutating route correctly refusing a
request with no `X-Console-Request` header.

**Work done after the first verification pass** (TD-1 and two defects found while doing it):

| Change | Evidence |
| --- | --- |
| Agents tab ticket picker; `ticket` threaded to the API | 6 new catalog tests; live route check |
| Catalog had **two implementations** — `agents.list_catalog()` and the HTTP feature's own globs — free to show different rosters. Collapsed onto one. | `agents catalog` and `/api/agents/catalog` now return identical data |
| `static/agents.js` held a **literal NUL byte** in a sentinel string, which made the file read as binary to grep and every text tool. Replaced with the six-character escape sequence; semantics identical (node: length 7, `charCodeAt(0) === 0`). | `node --check` passes; file now greppable |

## Scope changes during build

**D3 grew, and the plan's description of it is now understated.**
The plan called the `[agents.backends]` block in `console.toml` dead config to delete. It
was not dead: `server/agents.py` — the whole `kanban agents *` CLI path — read it, while
the Agents tab read `agents.toml`. Two registries for one concept, free to disagree about
command, model and permission mode with nothing to catch it. Deleting the block made
`agents backends` return `{}`, which is how this surfaced.

Reverting would have restored the duplication. Instead `agents.py` now sources
`agent_backends.registry()` and uses `Backend.compose_prompt()`/`turn_argv()`, which also
gives the CLI path the Windows `.CMD` resolution it never had. `oneshot_args` was added to
the claude row, which had only `session_args` and therefore no one-shot argv at all.
`_from_legacy` is untouched and covered by a test.

**One defect fixed outside plan scope:** `trackers._next_id` reused ids after deletion
(remove `D-2`, next add is `D-2`). Found while writing CC-T001-02. Fixed rather than
logged, because tracker ids are cited by id in durable markdown, so a reused id silently
re-points an existing citation — a data-integrity bug, not a cosmetic one.

## Effort

Estimated 13 h, actual ~9.5 h. Under mostly because 04 and 05 shared a module and 06 was
smaller than sized; 01 ran over (1.5 h vs 1 h) on the D3 discovery.

## Links
- [[CC-T001-summary]] · [[CC-T001-analysis]] · [[CC-T001-requirements]] · [[CC-T001-decision-log]] · [[CC-T001-plan]] · [[CC-T001-progress]] · [[CC-T001-verification]]
- Source dossier: [[INV-2026-08-29-control-center-v3-dossier]]
