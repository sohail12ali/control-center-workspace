---
ticket: "T-004"
artifact: verification
---

# Verification: T-004

Verified 2026-09-06 against the working tree, Windows 11 / Python 3.14.
Baseline before T-004: **783 passed**. After: **949 passed** (`python -m pytest
-o addopts="" -q`), 0 failures, 166 new tests.

The `-o addopts=""` matters: `pytest.ini` sets `-q --strict-markers`, and under
plain `-q` this suite prints only progress dots with no summary line, so a
count read from a bare `python -m pytest` is not trustworthy. Every count in
this file came from a run with the summary line visible.

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| FR-1 | Plugin + routes, `httpd.py` untouched | PASS | `console/server/features/assistant_feature.py`, tenth row in `plugins.toml`. Eight routes registered (`say`/`session`/`new`/`stream`/`memory` GET+POST/`settings` GET+POST) — pinned exactly by `test_plugins.py::TestAssistantRoutes`. `httpd.py` and `app.js` absent from the diff |
| FR-2 | One reused Assistant chat; busy → queued; idle timeout | PASS | `_ensure_session` reuses while alive and inside `session_idle_minutes`; live HTTP smoke returned `{"result":"queued","id":"8ddf928db322"}` and `GET /api/assistant/session` showed `{'id':'8ddf928db322','agent':'claude','title':'Assistant','active':True,'busy':True}`. `.claude/agents/*.md` still exactly 7 — `test_harness_lint.py::TestRealAgentRoster` reads the real directory |
| FR-3 | Persona injected per backend | PASS | `console/config/assistant.md` (49 lines) via `prompt_build.persona_text`'s second root; claude carries it on `--append-system-prompt`, an `openai_api` backend via `extra=`, a flagless CLI via a first-turn wire prefix. `test_agent_backends.py::TestSystemAppend` covers flag present/absent/empty; `test_assistant.py::TestSystemAppendDispatch` covers the wire-prefix branch |
| FR-4 | Injected session context within budget | PASS | `_compose_extra` = tickets digest (≤1,200) + memory (≤1,500) + a capabilities line (≤500), each capped with a stated marker. `test_assistant.py::TestInjectedContext`. Confirmed live: asked "what is this workspace for?", the reply described the harness, vault, ticket lifecycle and Console — it had read the injected context |
| FR-5 | Deterministic fast-command table | PASS | `console/server/assistant_commands.py`; 69 tests in `test_assistant_commands.py`. Real CLI output below. `status T-002` and `status t dash two` both answer with no model call; `stop the server` falls through to the model instead of interrupting |
| FR-6 | Three verbs incl. `kickoff` | PASS | `console/server/kickoff.py` + rows in `verbs.toml`; `test_kickoff.py`. Both amendment ACs covered — artifact-map insertion is heading-relative, and rendered templates are asserted BOM-free UTF-8 |
| FR-7 | Settings, service half | PASS | `console/config/assistant.toml` (committed defaults) + `GET`/`POST /api/assistant/settings`. Round-trip verified live (below). **AC2 (Settings-tab control) deferred to T-006** per the 2026-09-06 amendment |
| FR-8 | Reply path | **DEFERRED to T-006** | Struck in full by the amendment. Not attempted, not failed. See the consequence noted below |
| FR-9 | Capped, guarded memory | PASS | `console/server/assistant.py`; cap 1,500 with oldest-first trim, secret-shaped facts declined. `test_assistant.py::TestMemory`. Live: `remember the tray menu is drivable via MN_GETHMENU` → `Noted.` |
| FR-10 | CLI parity | PASS | `kanban assistant say/session/memory/settings`. Shares the route's own handler via `assistant_feature.handlers()` — one implementation, two callers, no CSRF bypass (CSRF is enforced by `httpd` on the way in). Output below |
| FR-11 | `native_bridge` honest stub | PASS | `available()` → `(False, "shell not running")` with no pointer file; `test_native_bridge.py` (10 tests). Live: `copy that` → "I cannot reach the clipboard" |

## Test Results

```
python -m pytest -o addopts="" -q
949 passed, 1 warning in 85.90s
```

```
python -m pytest -o addopts="" -q console/tests/test_assistant_commands.py
69 passed in 8.87s
```

## Live CLI — deterministic commands, no model call

```
>>> what's open
T-002: Desktop tray skeleton as the Agents control surface (Verify)
T-004: Assistant brain: persona, /api/assistant, fast commands, Settings backend picker, memory (Open)

>>> status T-002
T-002 is in Verify, 0 of 4 tasks open, 0 blockers.

>>> status t dash two
T-002 is in Verify, 0 of 4 tasks open, 0 blockers.

>>> status of the migration is not a ticket
queued -> chat b79c26fc2a16          # correctly NOT a status command

>>> copy that
There is no last reply to copy yet.

>>> mute
Muted.

>>> unmute
Unmuted.

>>> use cursor
Next chat uses cursor-agent.
```

Settings round-trip:

```
python console/kanban.py assistant settings --set backend=claude
  -> settings.backend == "claude"
console/.cache/assistant/settings.json  ->  {"backend": "claude", "speak": true}
console/config/assistant.toml           ->  unchanged
```

## Live model turn (HTTP, server on :8791)

```
POST /api/assistant/say {"text":"In one short sentence, what is this workspace for?"}
  -> {"result":"queued","id":"8ddf928db322"}

transcript:
  text.done :: It's a project-independent agentic harness: a Claude Code agent
               pipeline plus an Obsidian knowledge vault, ticket lifecycle, and
               Delivery Console for running structured software development work.
```

The server was started for this check and stopped afterwards (pid 25008).

## Edge Cases Probed

- **Whole-utterance matching.** `stop the server`, `cancel my subscription please`,
  `i will remember the password myself`, `what's open in the browser right now`,
  `status of the migration` — all reach the model. Only the bare utterance fires
  a command. This is the property that stops a spoken sentence triggering an
  action nobody asked for.
- **Spoken ticket ids.** `t dash two`, `t 2`, `ticket 4`, `T-4`, `twenty` all
  canonicalise; a span with no number returns None and falls through rather than
  inventing an id.
- **Unknown backend name.** `use banana` falls through to the model instead of
  being mapped to something plausible.
- **Degenerate title.** `create ticket for` (nothing after it) falls through —
  a ticket called "for" is worse than being asked what to call it.
- **Half-wrong settings patch.** Rejected whole; stored settings unchanged.
- **Malformed config / corrupt override / corrupt session pointer.** Each falls
  back to defaults rather than taking the Assistant down.
- **Uninstalled stored backend.** Skipped in favour of a working one.

## Notes

Two things found and fixed during this pass, both by tests I wrote:

1. `status t dash two` silently fell through to the model because the ticket
   pattern enumerated the shapes it accepted. Replaced with a loose capture
   validated by `canonical_ticket`, which is what the module's own docstring
   already claimed it did.
2. `_h_status` read `plan["open"]` as a count, but `context.build` returns a
   **capped list** of open tasks there. Open count is now `total - done`.

### A consequence of the FR-8 deferral, stated plainly

`copy that` cannot succeed in T-004 even with a native bridge running, because
nothing calls `assistant.write_last_reply` — its only caller is the reply
watcher, which is FR-8's and now T-006's. The function is written and tested;
it is simply not yet wired to a producer. The command answers honestly ("no
last reply to copy yet") rather than appearing to work, and T-006 makes it
live by adding the watcher. This is a deliberate consequence of the descope,
not an oversight.

### Not verified

- `kickoff` verb against a real vault: exercised in `tmp_path` by `test_kickoff.py`
  only. Running it for real would create a stray ticket directory, so it was not
  done here.
- The CLI creates in-process sessions that die with the process, so a model turn
  from the CLI cannot be followed to its reply. Model-path verification went
  through HTTP against a running server instead, which is how the shell will
  call it anyway.

## Links
- [[T-004-summary]] · [[T-004-analysis]] · [[T-004-requirements]] · [[T-004-decision-log]] · [[T-004-plan]] · [[T-004-progress]] · [[T-004-verification]]
