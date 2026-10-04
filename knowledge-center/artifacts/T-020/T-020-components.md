---
ticket: "T-020"
artifact: components
---

# Components: T-020

Every module this ticket touches or creates, mapped from the real source (file:line verified by read on 2026-10-01). 21 components is above the usual 5-12 band; reason: three slices over four layers on an L-sized ticket, and most components are one small module or one function group. No circular dependency (graph below). Layers are this project's own: **Data** (JSON/TOML records), **Service** (server modules), **Verb/API** (registry + handlers + transports), **Protocol/CI** (agent text, workflow).

**Produced by:** `analyze-components`. **Consumed by:** `breakdown-tasks`. Tracks: [[T-020-requirements]], [[T-020-task-breakdown]].

---

## Data layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| run-store | module edit `console/server/runs.py` (`STATES` :17, `create` :45, `get` :82, `list_runs` :90, `set_state` :107) | Two new states, TERMINAL/ACTIVE, default-on-read fields, lock-guarded `update`, `find_active_chat_run`, Windows replace-retry; `list_active` terminal-id cache added later in 3b-2 | `tomlio._acquire_lock` (`tomlio.py:279`), `paths` | A | FR-1, FR-2, NFR-8 | pending |
| ticket-claims-data | module edit `console/server/tickets.py` (`create` :38, `load` :90, `set_claim` :218) | `claimed_run`, `review_rounds`, `review_escalated` defaults; `parse_claimed_at`; `claim_status` + pure evaluator; `record_review`; adopt-under-lock in `set_claim` | run-store, run-config, `tomlio.atomic_update` (:320), `backends/vault_backend.py` | C | FR-19, FR-20, FR-21, FR-24 | pending |
| run-config | NEW `console/server/run_config.py` | Readers for `[runs]`, `[runs.retry]`, `[claims]`, `[review]` with code defaults and warn-once fallback; never writes config | `boards.load_console_config` (`boards.py:21`) | A | NFR-10; config ACs of FR-6/14/15/20/24 | pending |

## Service layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| session-state | edit `console/server/agent_session.py` (`BaseSession` :62, `snapshot` :162, `_handle_line` :255, `_observe` :280), `agent_approvals.py` (`Approvals` :79) | `last_output_at`, `started_utc`, `last_turn` (+rate_limit, tool counts), `turn_count`, `stop_requested`, `Approvals.pending_for` | — | A | FR-4 | pending |
| run-sync | NEW `console/server/run_sync.py` | `session_view` builder, pure `sync_run`, startup sweep, `decide_failure` seam, evidence collector | run-store, session-state | A | FR-3, FR-13 (collector) | pending |
| procs | edit `console/server/procs.py` (:25-40) | `kill_tree`, `tree_spawn_kwargs`, `clean_env`, `iter_capped_lines` | run-config | A | FR-5, FR-6, FR-7 | pending |
| session-spawn-sites | edit `agent_session.py` (`LiveSession.start` :404, `.stop` :476, `TurnSession._deliver` :544, `.interrupt` :600, `.stop` :612), `agents.py` (`launch` :221, `stop_job` :332), `agent_manager.py` (`create` :84, `resume` :273) | Use procs at every spawn/kill site; `kill_process()`; `repo_root` on sessions | procs, session-state | A | FR-5, FR-6 | pending |
| output-caps | edit `agent_session.py` (`LiveSession._read` :494, `TurnSession._read_turn` :562), `agents.py` (`_reader_thread` :180), `agent_manager.py` | Per-line cap, per-turn byte cap, `on_limit` seam, O(1) buffer accounting | procs, session-spawn-sites, run-store | A | FR-7 | pending |
| linger-kill | edit `agent_session.py` (`_read_turn`), `agents.py` (`_reader_thread`) | Kill a per-turn process that outlives its result | procs, output-caps | A | FR-8 | pending |
| turn-evidence | edit `console/server/agent_normalize.py` (`_result` :300-324) | `errors`, `error`, `api_error_status`, `stop_reason` on `turn.end` | — | B | FR-10 | pending |
| run-failures | NEW `console/server/run_failures.py` | `classify`, quota reset parse, `liveness`, class/non-retryable constants | turn-evidence | B | FR-11, FR-12, FR-13 | pending |
| run-retry-policy | in `run_failures.py` + wiring in `run_sync.py` | Retry table, caps, due time, `decide_failure` replaces fail-closed default | run-failures, run-sync, run-config | B | FR-15, FR-3 | pending |
| run-watchdog | NEW `console/server/run_watchdog.py` + edit `agent_manager.py` (`shutdown_all` :429), `features/agents_feature.py` (:22-34) | Pure `evaluate`, single-flight `tick`, thread lifecycle, terminal-first-then-kill, due-retry execution, `list_active` terminal cache | run-sync, run-retry-policy, session-spawn-sites, `agent_manager.resume` (:273), `audit.py` | B | FR-14, FR-16, NFR-7 | pending |
| run-escalation | in `run_watchdog.py` | One idempotent `run-watchdog` comment per failed/timed_out Run; per-class action table | run-watchdog, `verb_handlers.ticket_comment` (:461) | B | FR-17 | pending |

## Verb/API layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| run-verbs | edit `console/config/verbs.toml` (+ `run-watch`, `run-retry`), `verb_handlers.py` | On-demand tick and re-run; schemas derived by `mcp._schema_for` (:67) | run-watchdog | B | FR-18 | pending |
| claim-verbs | edit `verbs.toml` (+ `claim-release`), `verb_handlers.py` (`ticket_claim` :437), `backends/{base,vault_backend}.py`, `audit.py` `ACTIONS` (:44) | `claim` gains `run=` and adopt; `ready` lists stale; `claim-release` with force path | ticket-claims-data | C | FR-19, FR-21, FR-22 | pending |
| review-counter | edit `verbs.toml` (+ `review-round`), `verb_handlers.py` (`tracker_add` :530 gains `raised_by`), uses `tickets.record_review` | Counter verb, one critical question at escalation | ticket-claims-data | C | FR-24 | pending |
| context-digest | edit `console/server/context.py` (`build` :166, `format_markdown` :225) | `claim`, `review`, `runs` keys + one line each when non-empty | ticket-claims-data, run-store | C | FR-23 | pending |

## Protocol / CI layer

| Component | Type | Purpose | Dependencies | Slice | Requirement/AC | Status |
|-----------|------|---------|---------------|-------|-----------------|--------|
| process-tree-proof | NEW test `console/tests/test_proc_tree.py` | Real `sys.executable` process tree: no orphan after `kill_tree`; Windows control test | procs, session-spawn-sites | A | FR-9 | pending |
| ci-matrix | edit `.github/workflows/verify.yml` (`desktop` job :90-169) | Run the process-tree tests on windows/ubuntu/macos runners (the `tests` job :21 is ubuntu-only) | process-tree-proof | A | FR-9 AC2, NFR-3 | pending |
| agent-protocols | edit `.claude/agents/verifier.md` (step 10 :22), `fixer.md` (step 1 :13) | `review-round` calls and `review.escalated` stop rule | review-counter, context-digest | C | FR-25 | pending |

---

## Dependency graph

```
run-config ──┬─> procs ──> session-spawn-sites ──┬─> output-caps ──> linger-kill
             │                                    └─> process-tree-proof ──> ci-matrix
             ├─> run-retry-policy ┐
             └─> ticket-claims-data ──┬─> claim-verbs
                                      ├─> review-counter ──> agent-protocols
                                      └─> context-digest ─────┘
run-store ──┬─> run-sync ──> run-retry-policy ──> run-watchdog ──> run-escalation ──> run-verbs
            ├─> output-caps (Run written before kill)
            └─> ticket-claims-data (ACTIVE set), context-digest
session-state ──> run-sync, session-spawn-sites
turn-evidence ──> run-failures ──> run-retry-policy
```

## Graph analysis

- **Root:** run-store, session-state, run-config, turn-evidence, procs (procs reads config lazily; treated as root).
- **Leaf:** run-verbs, ci-matrix, linger-kill, agent-protocols, claim-verbs, context-digest.
- **Middle:** run-sync, run-failures, run-retry-policy, run-watchdog, run-escalation, session-spawn-sites, output-caps, ticket-claims-data, review-counter, process-tree-proof.
- **Circular deps:** none. Two cycle hazards were designed out: `verb_handlers` imports `agent_manager`, so the watchdog logic lives in `run_watchdog.py` (imports `verb_handlers`) and `agent_manager` imports it lazily inside `start_watchdog`; `procs` imports `run_config` lazily inside `clean_env` to stay a leaf.
- **Isolated components:** none (each maps to at least one FR).
- **Critical path (7):** run-store -> session-state -> run-sync -> run-retry-policy -> run-watchdog -> run-escalation -> run-verbs. Weighted by effort: 3 + 3 + 3 + 3 + 3 + 2 + 3 = 20h of the 73.5h dev total.
- **Bottleneck:** run-store (9 dependents, task 1a-1, scheduled first); second: run-config (task 1a-3).
- **Shared-file hot spots** (one builder at a time): `agent_session.py` (1a-2, 2a-2, 2b-1, 2b-2, 2b-3), `agents.py` (2a-2, 2b-1, 2b-3), `agent_manager.py` (2a-2, 2b-2, 3b-2), `procs.py` (2a-1, 2b-1), `run_sync.py` (1a-4, 2b-2 callers, 3a-4, 3a-5), `run_failures.py` (3a-2..3a-5), `verb_handlers.py` (3c-1, 4a-1, 4a-3, 4a-4, 4b-1), `verbs.toml` (3c-1, 4a-4, 4b-1), `tickets.py` (4a-1..4a-3, 4b-1), `audit.py` (3b-2, 4a-3, 4a-4, 4b-1).
- **Parallelizable (if more than one builder):** the 2a chain (procs hygiene) and the 3a-1..3a-4 pure modules touch no common files and need only 1a-1/1a-3; the 4b-1 review counter is independent of Runs. The plan keeps one serial order because five tasks share `agent_session.py` and the suite must be green at every boundary.

## Status summary

| Layer | Total | Pending | In-progress | Done |
|-------|------:|--------:|------------:|-----:|
| Data | 3 | 3 | 0 | 0 |
| Service | 11 | 11 | 0 | 0 |
| Verb/API | 4 | 4 | 0 | 0 |
| Protocol/CI | 3 | 3 | 0 | 0 |
| **Total** | 21 | 21 | 0 | 0 |

## Links
- [[T-020-summary]] · [[T-020-requirements]] · [[T-020-plan]] · [[T-020-components]] · [[T-020-task-breakdown]] · [[T-020-implementation-plan]] · [[T-020-critique-report]]
