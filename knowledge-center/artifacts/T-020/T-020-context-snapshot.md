---
ticket: "T-020"
artifact: context-snapshot
status: complete
created: "2026-10-01"
last_updated: "2026-10-01"
scope: codebase + history
---

# Context Snapshot: T-020

> What exists today that this ticket touches, reuses, or conflicts with. Frozen facts only. Every bullet cites a source.

**Command reference:**
- **Created/refreshed by:** `analyze T-020 context`
- **Consumed by:** `requirements` (draft/enrich), `challenge-requirements`

---

## 1. Intent (echo)

Make a Run survive the ways agent runs fail: classify failures (incl. quota reset time), catch stalls, retry with caps, kill process trees cleanly on Windows, reap stale claims, cap the review loop. Console server only, stdlib Python (`T-020-summary.md`; dossier Tier 1, items 1-6).

## 2. Codebase Findings

### Similar / adjacent features already built
| Feature | Entry point | Layers involved | Reuse opportunity | Source |
|---|---|---|---|---|
| Run record store (write-once) | `runs.create/get/list_runs/set_state` | JSON file per Run | Extend in place: new states + fields; add locked update | `console/server/runs.py:17,45-116` |
| Chat sessions, Live and Turn transports | `agent_session.LiveSession/TurnSession` | subprocess, reader thread, `Stream` | Single choke point for spawn, kill, env, caps, `last_output_at` | `console/server/agent_session.py:399-626` |
| Session registry + resume | `agent_manager.create/get/resume/stop` | process-memory dict + transcripts | `get(sid)` finds the live session for a Run; `resume` is the retry path for a dead chat | `console/server/agent_manager.py:84-333` |
| Rate-limit notice with `resets_at` | `Normalizer.feed` (`rate_limit_event`) | normaliser | Structured quota time, preferred over prose | `console/server/agent_normalize.py:136-151` |
| `turn.end` event | `Normalizer._result` | normaliser | Add failure-evidence fields additively | `console/server/agent_normalize.py:300-324` |
| Approval timeout, parked-approval events | `Approvals.request`, `approval.request/decided` | hook + registry | Silence clock must pause while an approval is pending | `console/server/agent_approvals.py:87-164` |
| `taskkill /T /F` and `killpg` | `sidecar.kill_tree` | desktop sidecar | Port into `procs.py`; cannot import `desktop/` | `desktop/sidecar.py:208-245` |
| No-window spawn flags | `procs.no_window_flags/popen_kwargs` | spawn helpers | Home for `kill_tree`, `clean_env`, `tree_spawn_kwargs` | `console/server/procs.py:25-40` |
| Interrupted vs failed vs done semantics | `JobQueue._reconcile` | jobs | Same pattern for Runs at startup: dead process means `interrupted`, never `done` | `console/server/jobs.py:20-27,144-163` |
| Race-safe read-modify-write | `tomlio.atomic_update`, lock file | TOML | Model for claim/review mutators; JSON Runs need an equivalent lock | `console/server/tomlio.py:279-347`, `tickets.py:218-255` |
| Verb layer (CLI + MCP + HTTP) | `verbs.toml` + `verb_handlers.py` | registry | New mutations are rows + one-line handlers; MCP schema derived from signature | `console/config/verbs.toml:128-148`, `console/server/mcp.py:67-116`, `verbs.py:171-193` |
| Audit trail | `audit.record(repo_root, action, target=, detail=, outcome=)` | JSONL | Every claim adopt/release, force action, escalation | `console/server/audit.py:94`, `verb_handlers.py:453-456` |
| Change bus | `bus.default().publish("ticket://T")` | MCP notifications | Publish on every ticket mutation | `verb_handlers.py:457` |
| Claim reminder to the holder | `stop_hook.stale_claims` | hook | Existing meaning of "stale claim" (holder reminder); new rule must not reuse the word for a different thing | `console/server/stop_hook.py:60-98` |
| Scheduler tick thread | `Ticker`, `_start_scheduler` | thread | Not reusable: it starts only when a schedule is enabled (all parked by default) | `console/server/httpd.py:260-286`, `schedules.py:189-252` |
| Config read with code defaults | `boards.load_console_config(...).get("jobs")` | console.toml | Same pattern for a `[runs]` / `[claims]` / `[review]` section; defaults live in code so no config file is edited | `console/server/jobs.py:67-73` |
| Telemetry unpriced-not-zero | `telemetry.record_turn` | JSONL | Attempt cost per retry stays attributable | `console/server/agent_session.py:328-360` |

### Existing patterns to reuse
- Fail closed: unknown never shown as zero (`agent_session.py:336-339`, `telemetry` cost None).
- Refuse rather than silently start fresh (`agent_manager.py:282-285`, `test_agent_resume.py:66-90`).
- Verb handler signature `(repo_root, ticket=None, **args)`; no `**kwargs` (`verb_handlers.py:6-12`).
- Tests monkeypatch `subprocess.Popen` and `threading` for spawn assertions (`test_procs.py:51-83`); real-git tests build a tmp repo (`test_agent_manager_worktree.py:26-37`).
- Additive fields with `setdefault` on load (`tickets.py:97-105`).

### Naming and architectural conventions in play
- Artifacts `{T}-{name}.md` flat, `## Links` block; TOML only via `console/kanban.py` (`CLAUDE.md` Layout).
- `needs_confirm` is a stray-call guard, not a human gate; human gates live in `agents.toml` `gated_tools` (`verbs.toml:25-30`). Never write `agents.toml` (tomlio drops comments).
- Exactly 7 agents, 39 skills; `harness lint` warns on roster drift (`CLAUDE.md`; lint baseline 0/0).

## 3. Historical Findings

### Prior tickets touching the same area
| Ticket | What it did | Outcome | Lessons |
|---|---|---|---|
| T-016 | Run store, `launch-role`, `delegate` Run wrap | shipped; Runs are pointer records | `runs.py:1-6` states a Run "points at" chat/job; no lifecycle was built |
| T-017 | `claim`/`ready`/`comment` verbs, Backend SPI, race-safe `set_claim` | shipped (`6902b92`) | `claimed_at` is a date; no release verb; stop-hook reads it |
| T-018 | Worktree per ticket (reused across Runs), Run inspector | shipped (`1698d6e`) | Two live Runs on one ticket share one worktree, so an unsafe claim adoption corrupts work |
| T-011 | Resume dead chats in place | shipped | Resume refuses without a native session id; retry must honour that |
| T-003 | `procs.py` no-window hygiene | shipped | Defensive only; agent spawns did not reproduce stray consoles (memory `stray-terminal-root-cause`) |
| T-021, T-022 | Honest close lint; evals (parallel tickets, same tree) | in flight | T-021 builds its liveness lint on this ticket's run-liveness and stale-claim output: keep field names stable |

### Relevant commits / PRs
- `6902b92` Ship T-017 (claim, ready, comment) · `1698d6e` Ship T-018 (worktree isolation, PR hints, Run inspector) · `0c42658` T-016 artifacts.

### Known incidents / regressions in this area
- 2026-09-07: five defects invisible on Windows/py3.14, incl. `CREATE_BREAKAWAY_FROM_JOB` failing the spawn under restrictive job objects (memory `cross-platform-defects-only-ci-finds`).
- T-004: delegated builds reported success the disk contradicted (memory `subagent-status-not-evidence`): verification here must come from the tree and the pytest count.
- Baseline: 3 failing tests in `test_stop_hook.py` from date-dependent fixtures (this pass, `pytest -o addopts="" -q` over 11 modules: 222 passed, 3 failed).

## 4. External Systems in the Loop

- `claude` CLI stream-json dialect: `result` fields (`subtype`, `is_error`, `result`, `errors`, `api_error_status`, `stop_reason`), `rate_limit_event`. Never spawned in this ticket; tests use fixture lines.
- `cursor-agent` (Windows `.CMD` shim, process tree).
- Windows `taskkill.exe`; POSIX `killpg`.
- Optional: IANA tz data for quota reset zones (`zoneinfo`, may be absent on Windows).

## 5. Preliminary Risks Spotted

- Quota prose can drift between CLI versions; unrecognised text must fall to non-retryable, never to a guessed retry.
- A watchdog that kills a run silent for a legitimately long tool call; mitigated by pausing the clock during approvals and using generous defaults.
- `taskkill /T` cannot reach grandchildren whose parent already exited.
- Changing `claimed_at` from date to timestamp touches `stop_hook` string comparison semantics.
- Adding fields to `ticket.toml` (`review_*`) touches `tickets.create` key set; any test or export asserting an exact key set would break.
- Watchdog thread plus verb handlers plus CLI processes all write Run JSON; without a lock a lost update can resurrect a terminal Run.

## 6. Open Confirmations

- `rate_limit_event.resetsAt` units (seconds vs milliseconds) and the `status` vocabulary (`rejected`?): no real sample on this machine; only the pass-through at `agent_normalize.py:148`. Confirm from one captured transcript. Design accepts either unit by magnitude and falls back to prose.
- `CLAUDECODE` as the nested-session guard: from Paperclip's comment (`server-utils.ts:4712-4716`), not reproduced here (no real `claude` spawn allowed).
- Whether `claude` emits periodic output while a long tool runs: the normaliser mentions a periodic `status` ping (`agent_normalize.py:158-168`, observed on claude 2.1.146) but not that it continues during a tool call. Watchdog defaults are therefore generous.
- Real quota prose beyond Paperclip's fixtures ("resets 4:30pm (America/Chicago)", `parse.test.ts:66,173,193,205`).

---

## Source Log

| When | Method | Target | Why |
|---|---|---|---|
| 2026-10-01 | Read | `console/server/{runs,agent_manager,agent_events,agent_session,agent_normalize,jobs,procs,tickets,verb_handlers,worktrees,schedules,agents,agent_approvals,verbs,mcp,stop_hook,context,tomlio}.py` | trace Run/claim/process paths |
| 2026-10-01 | Read | `console/server/backends/{base,vault_backend}.py`, `console/server/httpd.py:255-342`, `features/agents_feature.py` | claim writer, thread start points |
| 2026-10-01 | Read | `console/config/{verbs,agents,console,schedules}.toml` (read-only) | verb rows, backend args, config sections |
| 2026-10-01 | Read | `console/tests/{conftest,test_runs,test_procs,test_agent_manager_worktree,test_agent_resume,test_ready_claim_comment_verbs,test_tickets,test_stop_hook}.py` | test seams, baseline |
| 2026-10-01 | Grep | `set_state`, `runs_mod.`, `env=`, `stall|retry|backoff|timeout|taskkill|killpg`, `claimed_at`, `claim` | confirm absences |
| 2026-10-01 | Read | `desktop/sidecar.py:130-270` | tree-kill precedent |
| 2026-10-01 | Read | paperclip files listed in [[T-020-analysis]] Research | reference behaviour |
| 2026-10-01 | Bash | `pytest -o addopts="" -q` on 11 touched modules; `harness lint`; `zoneinfo`/`tzdata` probe; `env` name list (values not read) | baseline and environment facts |
| 2026-10-01 | Read | `console/.cache/agent-chats/*.events.jsonl`, `console/.cache/runs/` | real `turn.end` sample; Run store empty |
| 2026-10-01 | Read | memory notes `windows-native-threading-traps`, `stray-terminal-root-cause`, `cross-platform-defects-only-ci-finds`, `subagent-status-not-evidence` | Windows process lessons |

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements-draft]] · [[T-020-context-snapshot]] · [[T-020-gap-analysis]] · [[T-020-iteration-log]] · [[T-020-decision-log]] · [[T-020-critique-report]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
