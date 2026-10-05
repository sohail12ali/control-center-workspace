---
ticket: "T-020"
artifact: requirements
status: frozen
frozen_date: "2026-10-01"
frozen_iteration: 2
---

# Requirements: T-020

> Frozen summary for `requirements stories`/planner consumption. Full detail (flows, data, interactions, business-rule wording) lives in [[T-020-requirements-draft]] (frozen v2). Decisions behind it: [[T-020-decision-log]] (all "decided under delegated authority 2026-10-01, reversible"). Frozen 2026-10-01 at iteration 2: 25 FR / 11 NFR / 13 BR, 0 open challenge findings, 0 blocker questions.

## Intent

Make a delegated Run survive the ways agent runs actually fail, without a human watching: classify failures (incl. quota reset time), catch stalls, retry with caps, kill process trees (incl. Windows), expire stale claims safely, cap the review loop. Console server only, stdlib Python. Dossier items 1-6 of [[INV-2026-10-01-paperclip-adoption-dossier]]. GROUND found the Run store write-once (no caller of `runs.set_state` outside tests), so a Run lifecycle (FR-1..FR-4) is the foundation. Effort is closer to L than the dossier's S: three slices (A lifecycle + hygiene, B classify/watch/retry, C claims + review loop).

## Scope

### In scope
- Run lifecycle reconcile, two new states, additive Run fields (foundation for everything below).
- Item 1: Claude failure classifier incl. quota reset time → `retry_not_before`.
- Item 2: run-liveness classes and a stall watchdog with configurable thresholds.
- Item 3: retry/backoff table with caps and an explicit non-retryable list.
- Item 4: child-process hygiene at the session layer (all chats): tree-kill incl. Windows, grace-then-kill, output caps, lingering-after-result kill, env stripping, with a no-orphan test.
- Item 5: stale-claim rule, audited release and force-release, via `verbs.toml`.
- Item 6: review-loop counter and escalation, verifier/fixer protocol text.
- `console context` shows claim, review and latest-run facts.

### Out of scope
- UI work (Run pill, stall hint, Needs-me desk): dossier Tier 3.
- Budgets and spend caps: Tier 4, `pricing.toml` is empty.
- Worktree hardening and resume fingerprint: Tier 4.
- Retrying, watching, or killing chats a human started from the Agents tab (no Run exists; a human is present).
- Runs for `job` and `cursor` executors (nothing creates them today).
- Auto-continuation of `plan_only` or `empty` turns (cost policy; classify and surface only).
- Job Object (ctypes) process containment: deferred, todo recorded.
- New skills or agents (roster stays 7 and 39); writing `agents.toml`; editing any `.toml` under `console/config`.
- Phone/Telegram alerts for stall or escalation (needs a user edit of `console.toml [notify].events`).
- Non-Claude failure dialects beyond a generic `process_failed`/`unclassified` class.
- Stale `.lock` file recovery in `tomlio`; telemetry path under worktrees (adjacent defects, todos).

## Functional Requirements

### Slice A: Run lifecycle and process hygiene

#### FR-1: Run states and terminal immutability
`runs.STATES` gains `timed_out` and `scheduled_retry` (minimal set; no `cancelled`: a human stop is `interrupted` with `end_reason=stopped`). `TERMINAL = {done, failed, interrupted, timed_out}`; `ACTIVE = {queued, running, needs-approval, scheduled_retry}`. `set_state` refuses any change out of a terminal state.

- [ ] `runs.STATES` equals the existing six plus `timed_out`, `scheduled_retry`; `runs.TERMINAL` and `runs.ACTIVE` partition it.
- [ ] `set_state(done -> running)` raises `ValueError`; the record on disk is unchanged.
- [ ] An existing record with state `running` loads and lists unchanged.

#### FR-2: Additive Run fields and a locked update
Run records gain fields with defaults on read (old records load): `attempt` (int, 1), `attempts` (list, last 10 entries `{n, started, ended, failure_class}`), `failure_class`, `failure_detail` (max 500 chars), `retry_not_before` (UTC ISO or ""), `retry_due` (UTC ISO or ""), `retry_of` (run id or ""), `end_reason`, `ended` (UTC ISO), `last_output_at` (UTC ISO or ""), `liveness` ...

- [ ] `runs.get` on a record written by the pre-T-020 code returns every new key with its default; no exception.
- [ ] 8 threads calling `runs.update` on one Run with different fields leave a record containing all 8 fields (no lost update).
- [ ] `update(state="done", liveness={...}, ended=...)` on a `running` Run writes all of them in one write; a second `update` of any field on that now-terminal Run raises `ValueError` and the file is byte-identical afterwards.
- [ ] `failure_detail` longer than 500 chars is stored truncated with a trailing marker.

#### FR-3: Run to session reconcile
A pure function `sync_run(run, session_view, now) -> patch` maps a chat-executor Run and its live session to a state. `session_view` is built from session **attributes** (`alive`, `busy`, queue depth, `last_turn`, `turn_count`, `last_output_at`, `stop_requested` from `_stopping`) and `Approvals.pending_for(chat)`, never from the event ring (which can overflow, FR-4).

- [ ] Table-driven test over (session alive/dead/absent, busy, pending approval, last turn ok/error/none, queue empty/non-empty, startup sweep vs running server) asserts the resulting state for each row.
- [ ] Startup sweep with three active Runs (live session, dead session, no session) leaves the first and marks the other two `interrupted`, `ended` set.
- [ ] A Run in a terminal state is never changed by `sync_run` (returns an empty patch), including when its chat later takes another turn.
- [ ] A session that overflowed its ring (more than `RING_MAX` events after the `turn.end`) still yields the right state because `last_turn` is read.
- [ ] A session whose process is killed externally while the server runs yields `process_lost` and one `scheduled_retry`; the same Run found absent at startup yields `interrupted` and no retry.

#### FR-4: Output timestamp and last-turn memory on sessions
`BaseSession` records `last_output_at` (UTC ISO) and a monotonic counterpart on every line read from the child's stdout (before JSON parsing, so non-JSON text counts), and retains `last_turn` (the most recent `turn.end` event plus the last `rate_limit` notice seen in that turn) and `turn_count` as attributes updated in `_observe`.

- [ ] Feeding one line through `_handle_line` with an injected clock sets `last_output_at` to that time; snapshot contains it.
- [ ] A session that has produced no output reports `last_output_at == ""`, never `now`.
- [ ] After a `turn.end` followed by `RING_MAX + 1` further events, `session.last_turn` still holds that `turn.end`.
- [ ] `Approvals.pending_for(chat)` lists a parked request while it waits and is empty after `decide` or `forget`.

#### FR-5: Process-tree kill in `procs.py`
`procs.kill_tree(proc, grace=5.0)` ends a child and its descendants: ask first (POSIX `SIGTERM` to the group; Windows `taskkill /PID n /T`), wait up to `grace`, then force (POSIX `SIGKILL` to the group; Windows `taskkill /PID n /T /F`), then reap. Spawn sites pass `procs.tree_spawn_kwargs()` (POSIX `start_new_session=True`;

- [ ] With `os.name` patched to `nt` and `subprocess.run` faked, `kill_tree` issues `taskkill /PID <pid> /T` then, if the fake child is still alive after `grace`, `/T /F`, both with the no-window flag.
- [ ] With `os.name` patched to `posix` and `os.killpg` faked, it signals `TERM` then `KILL` on the child's own group id, and never on `os.getpgrp()`.
- [ ] `kill_tree` on an already-exited process returns without error and without invoking `taskkill`/`killpg`.
- [ ] grep: no remaining bare `proc.kill()`/`proc.terminate()` in `agent_session.py` or `agents.py`.

#### FR-6: Environment stripping for agent children
Every agent child process (both `agent_session` spawn sites and `agents.launch`) is started with `env=procs.clean_env()`: `os.environ` minus a deny list of session-identity and nesting variables.

- [ ] With every listed name set to a sentinel in `os.environ`, `clean_env()` contains none of them and keeps `PATH`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_OAUTH_SCOPES`.
- [ ] Each of the three spawn sites passes an `env=` whose keys exclude the deny list (assert on the kwargs handed to a faked `Popen`).
- [ ] `[runs].env_strip` in a fixture `console.toml` replaces the default list; an invalid value (non-list) falls back to the default with one warning, no exception.

#### FR-7: Output caps
Reader loops read with a per-line limit (`[runs].max_line_bytes`, default 1 MiB): an over-long line is truncated with a marker and the remainder discarded, never held whole in memory. A per-**turn** cap on stdout bytes (`[runs].max_turn_output_bytes`, default 64 MiB, counter reset at each `turn.start`;

- [ ] A fake stream containing one 3 MiB line with cap 1 MiB yields one truncated event and memory held per line ≤ cap + marker; the next line parses normally.
- [ ] A fake stream exceeding `max_turn_output_bytes` (set to 4 KiB in the test) within one turn triggers exactly one `output_cap` notice and one `kill_tree` call; the same bytes spread over two turns (counter reset at `turn.start`) trigger none.
- [ ] `agents._reader_thread` appends 10 000 short lines in under 1 s (regression for the O(n²) sum) and still sets `truncated` past 200 000 chars.

#### FR-8: Lingering-after-result kill
For per-turn processes (`TurnSession`, `agents.launch`): once a terminal result event has been read, if the process has not exited within `[runs].linger_grace_secs` (default 5), `kill_tree` is called, the turn is finalised, and the transcript records `{type: notice, kind: lingering_killed}`.

- [ ] A fake turn process that prints a result line then sleeps is killed within `linger_grace_secs + 1 s` (injected clock/grace 0.2 s in test); `busy` becomes False and the queue drains.
- [ ] A fake process that prints a result and exits within the grace window is not killed and no `lingering_killed` notice appears.
- [ ] A `LiveSession` fake that stays alive after `result` is never killed by this rule.

#### FR-9: No orphaned child after a kill (real-process test)
A test spawns a fake CLI (`sys.executable -c ...`, never `claude`/`cursor-agent`) that starts a child which starts a grandchild, each sleeping, and prints their pids; the test calls the production kill path (`kill_tree` via `LiveSession.stop`-equivalent) and proves all three pids are gone. It runs on Windows (primary) and POSIX.

- [ ] After `kill_tree`, polling up to 10 s finds root, child and grandchild pids not running (Windows: `OpenProcess` exit-code check; POSIX: `os.kill(pid, 0)` raises).
- [ ] A Windows-only (`os.name == "nt"`, skipped elsewhere) control test kills the same tree with plain `proc.kill()` and asserts the grandchild **is still alive**, then cleans it up with `kill_tree`; it proves the main test can fail. It runs in CI on the Windows runner.
- [ ] Known limit stated in the test docstring and in § 8: a grandchild whose parent already exited before the kill is out of reach of `taskkill /T`.


### Slice B: classify, watch, retry

#### FR-10: `turn.end` carries failure evidence
`Normalizer._result` adds, additively, `errors` (list of strings, each ≤500 chars, max 10), `error` (str ≤500), `api_error_status` (int or null), `stop_reason` (str ≤64). Existing keys and consumers are unchanged. The session also remembers the most recent `rate_limit` notice of the current turn for the classifier.

- [ ] A fixture `result` line with `errors:["x"]`, `api_error_status:429`, `stop_reason:"refusal"` produces a `turn.end` containing those values; a line without them yields `[]`, `""`, `null`, `""`.
- [ ] The existing normaliser tests pass unchanged.

#### FR-11: Claude failure classifier
A pure module (`run_failures.classify`) takes the final `turn.end`, the turn's last `rate_limit` notice, the process exit code (or None) and a bounded stderr tail, and returns `{class, retryable_class, detail, retry_not_before}`.

- [ ] Fixture table with at least 20 rows (one per class, precedence conflicts, the real "Failed to authenticate" sample, an assistant message that merely mentions "unauthorized" in a successful turn) yields the expected class for each.
- [ ] `subtype:"success", is_error:true` with the auth sample classifies `auth_required`, not success.
- [ ] A successful turn whose assistant text contains "rate limit" is not classified as failed.
- [ ] Unknown text on a failed turn returns `unclassified` (never `transient_upstream`).

#### FR-12: Quota reset time to `retry_not_before`
For `quota` and `transient_upstream`, `retry_not_before` (UTC ISO or "") is taken from, in order: (a) the turn's `rate_limit` notice `resets_at` when its status is `rejected`, accepting epoch seconds or milliseconds by magnitude (> 1e11 means ms);

- [ ] Fixtures from Paperclip `parse.test.ts` ("resets 4pm (America/Chicago)", "resets at 4pm (America/Chicago).", "resets 2:30am (UTC)", "resets 4:30pm (America/Chicago)") parse to the expected UTC instants for fixed `now` values, including the rollover case (time already past today → tomorrow).
- [ ] With `zoneinfo.ZoneInfo` monkeypatched to raise `ZoneInfoNotFoundError`, a non-UTC zone returns `""` and the class stays `quota`; `UTC` still parses.
- [ ] `resets_at` as seconds and as milliseconds yield the same instant; a value in the past or beyond the horizon yields `""`.
- [ ] 12-hour edge cases: `12am`, `12pm`, `12:00am` map to 00:00 and 12:00; `13pm` is rejected.

#### FR-13: Run-liveness classes
After a turn ends without error, `run_failures.liveness` assigns `liveness.state` ∈ `completed | advanced | plan_only | empty | blocked | failed` plus a reason ≤200 chars. Durable evidence beats prose: evidence = (a) `tool.start` events in the turn for file-mutating tools (`Write`, `Edit`, `MultiEdit`, `NotebookEdit`;

- [ ] Table test over (mode, evidence count, text, ticket lane, new critical question) covers each class.
- [ ] A turn in `plan` mode that says "I will first inspect the code" with no tools yields `advanced`, not `plan_only`; the same text in `default` mode with no tools yields `plan_only`.
- [ ] A turn whose only tool calls are `Bash` and whose text is empty yields `empty`, not `advanced`.
- [ ] A fixture of at least 8 reply texts (4 planning-only, 4 genuine summaries containing words like "next" or "will" mid-sentence) classifies correctly under the pattern constant.
- [ ] `plan_only` and `empty` runs are not retried (assert no `scheduled_retry` transition).

#### FR-14: Stall watchdog
A watchdog thread owned by `agent_manager` (started by the agents plugin, stopped in `shutdown_all`, not tied to `Ticker`) ticks every `[runs].watch_interval_secs` (default 15) and evaluates each chat Run through a pure `evaluate(run, session_view, now, cfg)`. Only `running` Runs have a silence clock (`scheduled_retry` waits for its due time under FR-16;

- [ ] With an injected clock: silence 599 s → no action; 601 s → `suspicious` and one notice; a second tick at 700 s adds no second notice; 1801 s → kill called once and Run `timed_out`.
- [ ] A Run with a pending approval for 1 h of fake time is never marked suspicious or killed.
- [ ] A session with output at 1799 s ago resets the clock (no kill).
- [ ] The Run is already `timed_out` on disk at the moment the fake `kill_tree` is called, and a following `sync_run` over the dead session returns an empty patch.
- [ ] A chat without a Run is not evaluated (fake registry contains it; no kill call).
- [ ] Thresholds read from `[runs]` in a fixture `console.toml`; `stall_kill_secs <= stall_suspect_secs` is rejected at load with defaults used and one warning.
- [ ] `agent_manager.shutdown_all` stops the thread (join within 2 s).
- [ ] `stall_kill_secs = 0` with 10 h of fake silence flags `suspicious` and never calls `kill_tree`; `watchdog_enabled = false` starts no thread.
- [ ] If evaluating Run A raises, Run B in the same tick is still evaluated and `errors` is 1.
- [ ] Two concurrent ticks (thread and `run-watch`) kill and retry each Run at most once; the loser returns `{busy:true}`.

#### FR-15: Retry table with caps
One table in code (defaults overridable under `[runs.retry]`), keyed by failure class:

| class | max retries | delay |
|---|---|---|
| `transient_upstream` | 2 | 30 s, 120 s |
| `quota` | 2 | `max(60 s, retry_not_before - now + 60 s)`;

- [ ] For each class, N+1 consecutive failures produce N `scheduled_retry` transitions then `failed` with a retry-exhausted `end_reason`.
- [ ] Every non-retryable class goes straight to `failed` with zero retries (parametrised test over the list).
- [ ] `quota` with `retry_not_before` 3 h ahead schedules due time ≥ that instant + 60 s; with empty `retry_not_before`, or one 3 days ahead, it fails without retry and the escalation comment names the reset time when known.
- [ ] A Run that fails twice transiently then once with `process_lost` stops at the total cap 3 and the 4th failure is terminal.
- [ ] Changing a delay in `[runs.retry]` changes the scheduled due time; a non-numeric value falls back with one warning.

#### FR-16: Retry execution
When a `scheduled_retry` Run is due (checked on each watchdog tick, durable across restarts because `retry_due` is on the Run record), the retry sends a fixed continuation message to the same conversation: a live session gets `send(...)`; a dead session goes through `agent_manager.resume`.

- [ ] With a fake live session, a due retry calls `send` once with the continuation text and the Run is `running`, `attempt=2`.
- [ ] With a dead session and a fake `resume` raising `ValueError`, the Run is `failed`, `end_reason=resume_refused`, and `agent_manager.create` is never called.
- [ ] A `scheduled_retry` Run whose due time is in the future is untouched by a tick; after a simulated server restart (fresh watchdog, same files) it is retried at its due time.
- [ ] A user `stop` on a `scheduled_retry` Run cancels the pending retry (Run `interrupted`).

#### FR-17: Escalation record
When a Run ends `failed` or `timed_out` (non-retryable class, exhausted retries, resume refused, stall kill) and it has a ticket, the watchdog adds one `comments` tracker item (author `run-watchdog`) by calling `verb_handlers.ticket_comment` (audit and bus publish come with it) stating run id, class, detail ≤300 chars, attempts, and the next human action from one table keyed by ...

- [ ] The action table has a row for every class in FR-11 plus `resume_refused` and exhaustion (asserted by iterating the class set).
- [ ] A failed Run produces exactly one comment even if the sync runs three times.
- [ ] A `done` Run produces none; a ticketless Run produces none.
- [ ] The comment text never contains env var values or the raw `result` beyond 300 chars.

#### FR-18: Verbs for the Run layer
`verbs.toml` gains `run-watch` (one reconcile + watchdog + due-retry tick; `needs_confirm`; schedulable via `schedules.toml` like any verb; reports `last_tick` and `errors`) and `run-retry` (`run_id` arg;

- [ ] `verbs.run(repo, "run-watch", confirm=True)` returns counts `{synced, suspicious, killed, retried}` and mutates nothing when no Runs exist.
- [ ] `run-retry` on a `done` Run returns `{ok:false, error}`; on an unknown id returns `{ok:false, error}`.
- [ ] `run-retry` on a `failed` Run creates exactly one new Run with `retry_of` set and leaves the old file byte-identical; a second call while the new Run is ACTIVE returns `{ok:false}` and creates nothing.
- [ ] The MCP tool list contains both verbs with schemas derived from the signatures; the HTTP route `/api/verbs/run-watch/run` accepts them (existing verb-layer tests extended, no new transport code).


### Slice C: claims and the review loop

#### FR-19: `claimed_at` becomes a UTC timestamp; `claimed_run` links the owner
`VaultBackend.claim` stamps `claimed_at` as `YYYY-MM-DDTHH:MM:SSZ` (UTC, injectable clock) instead of `date.today()`. `ticket.toml` gains `claimed_run` (run id or "", default on load, set only by `set_claim`, cleared on release): the `claim` verb takes an optional `run` argument; when absent it auto-links to the sole ACTIVE chat Run on the ticket, else stays empty.

- [ ] A claim via the verb stores a value matching `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$`.
- [ ] `parse_claimed_at("2026-09-16")` equals `2026-09-16T23:59:59Z`; `""` and `"garbage"` return `None`.
- [ ] `tests/test_stop_hook.py` passes in full on any calendar date (clock injected); the semantic assertions (claim with no update is reported, claim then comment is not) are unchanged.
- [ ] `ticket.toml` files with date-only or empty `claimed_at` still load (existing `test_an_older_ticket_toml…` stays green); an older file without `claimed_run` loads with `""`.
- [ ] `claim` with `run=<id>` stores it; with no `run` and exactly one ACTIVE chat Run on the ticket stores that id; with zero or two ACTIVE Runs stores `""`; release clears it.

#### FR-20: Stale-claim rule
`tickets.claim_status(repo_root, ticket_id, now)` returns `{state: free|held|stale, holder, claimed_at, claimed_run, age_secs, basis, reason}`. Evaluated in this order: (1) no `claimed_by` → `free`. (2) `claimed_run` set: that Run ACTIVE (`queued`, `running`, `needs-approval`, `scheduled_retry`) → `held`, basis `run_live`, **regardless of age** (BR-6);

- [ ] Table test over an injected clock covers every branch: linked live Run + claim 3 days old → `held/run_live`; linked Run terminal 61 s ago → `stale/run_dead`; linked Run terminal 30 s ago → `held`; linked Run id with no record, claim 2 min old → `stale/run_missing`; unlinked, a different ACTIVE Run exists → `held/run_live`; unlinked, no Runs, claim 9 h old → `stale/ttl`; same, 7 h old → `held`; same with `ttl_secs=0` and 9 h → `held`; empty `claimed_at` → `held/unknown`.
- [ ] Scenario: planner claimed with its Run linked, that Run is now `done` 5 min ago, builder's own Run is ACTIVE on the same ticket → `stale/run_dead`, so the builder can adopt (a plain "any ACTIVE Run protects the claim" rule would wrongly return `held`).
- [ ] A Run in `scheduled_retry` counts as ACTIVE (the owner will come back).
- [ ] Config keys read from `[claims]` with code defaults; invalid values fall back with one warning.

#### FR-21: Adopting a stale claim and listing it
The `claim` verb, called by a different identity on a `stale` claim, adopts it: the swap happens inside the same `tomlio.atomic_update` that writes the claim and re-evaluates staleness under the lock; the adopter's `claimed_run` is set per FR-19; the audit record (`ticket.claim.adopt`) carries previous holder, previous `claimed_at`, previous `claimed_run`, basis and age;

- [ ] Existing `test_ready_claim_comment_verbs.py` assertions pass unchanged (fresh claims excluded; refusal names the holder).
- [ ] Two threads adopting the same stale claim as different identities: exactly one succeeds, the other is refused; the final holder equals the winner.
- [ ] After adoption the audit log has one `ticket.claim.adopt` row whose `detail` includes `previous_holder` and `basis`.
- [ ] `ready` returns a stale-claimed ticket with `claim.state == "stale"` and omits a held one.

#### FR-22: `claim-release` verb with an audited force path
New verb `claim-release` (`needs_ticket`, `needs_confirm`), args `agent`, `force` (default empty), `reason`. The holder may release its own claim; anyone may release a `stale` claim; a `held` claim by another identity is refused unless `force` is set, and `force` requires a `reason` of at least 10 characters.

- [ ] Holder release clears `claimed_by`, `claimed_at` and `claimed_run`; a non-holder release of a held claim returns `{ok:false}` and leaves the claim.
- [ ] Release of a stale claim by a third identity succeeds and the audit row records `basis`.
- [ ] `force` with an empty or 5-character `reason` is refused; with a valid reason it succeeds, writes `ticket.claim.force_release` with `previous_holder` and `reason`, and adds a comment.
- [ ] `kanban verb list` and the MCP tool list both include `claim-release`; running it without `confirm` is a `VerbError`.

#### FR-23: Context digest shows claim, review and run facts
Supporting requirement: agents choose actions from `trace-context`, so FR-25's fixer rule ("stop when `review.escalated`") and T-021's liveness lint need these facts in the digest.

- [ ] A ticket with a stale claim, `review_rounds=2` and one failed Run renders three lines in the markdown and the matching keys in JSON.
- [ ] A ticket with none of these renders exactly as before (existing context tests unchanged).

#### FR-24: Review-loop counter and escalation
`ticket.toml` gains `review_rounds` (int, 0) and `review_escalated` (bool, false), defaulted on load and mutated only through `tickets.record_review` under `tomlio.atomic_update` (not in `EDITABLE`). New verb `review-round` (`needs_ticket`, `needs_confirm`), arg `outcome` ∈ `changes_requested | approved | human_decision`, optional `agent`. `changes_requested` increments;

- [ ] Three consecutive `changes_requested` calls give rounds 1, 2, 3; the third returns `escalate:true`, sets `review_escalated`, and creates exactly one critical open question that `trackers.blockers` reports.
- [ ] A fourth `changes_requested` returns `{ok:false, escalated:true}`; `review_rounds` stays 3; no second question exists.
- [ ] `approved` after two rounds resets to 0; an interleaved `approved` between `changes_requested` calls prevents escalation (consecutive rule).
- [ ] `human_decision` after escalation clears `review_escalated`; a new `changes_requested` then starts at 1.
- [ ] An older `ticket.toml` without the fields loads with 0/false; `tickets.create` includes them; no existing exact-key-set test breaks.
- [ ] `[review].max_rounds = 5` in a fixture config changes the threshold; `0` or non-integer falls back to 3 with one warning.

#### FR-25: Verifier and fixer protocols use the counter
`.claude/agents/verifier.md` step 10 and `.claude/agents/fixer.md` step 1 are edited (existing files only): the verifier, on unmet criteria, calls `review-round outcome=changes_requested` before routing to the fixer and stops and surfaces the escalation to the user when the reply says `escalate`; on a clean pass it calls `outcome=approved`;

- [ ] `grep review-round .claude/agents/verifier.md` and `.claude/agents/fixer.md` find the new steps, and both files contain the `review.escalated` stop rule; both files keep their output contract blocks intact.
- [ ] `python console/kanban.py harness lint` reports 0 errors and 0 warnings and the roster line still reads `39 skills, 7 agents`.
- [ ] `git diff --stat` for the ticket shows no new files under `.claude/agents` or `.claude/skills`.

## Non-Functional Requirements

| ID | Category | Requirement | Target | Notes |
|---|---|---|---|---|
| NFR-1 | Constraints | Stdlib-only Python in the console runtime; no new pip dependency; vanilla JS untouched (no static change in this ticket) | 0 new third-party imports in `console/server`; `git diff` touches no `console/static` file | `zoneinfo` is stdlib but its data may be absent on Windows (FR-12) |
| NFR-2 | Reliability | Fail closed: unknown is never shown as zero or as success | `last_output_at`, `retry_not_before`, `claimed_at` unknown render as `""`/`unknown`; unclassified failure never retries; unknown claim time never expires | tests named in FR-2, FR-11, FR-12, FR-20 |
| NFR-3 | Portability | Windows 11 + Python 3.14 primary; POSIX branches provable on one machine | `os.name` monkeypatched tests for `nt` and `posix` in `kill_tree`, `tree_spawn_kwargs`; CI matrix (Win/Linux/macOS) stays green | job-object breakaway lesson: nothing here requests breakaway |
| NFR-4 | Testability | Fakes only: no real `claude`/`cursor-agent`, no network, no model call; injectable clock; no test sleeps > 2 s | grep of new tests finds no `claude`/`cursor-agent` spawn; whole new test set < 30 s on the dev machine; real-process test ≤ 15 s | the FR-9 process tree uses `sys.executable` only |
| NFR-5 | Compatibility | Old Runs, old `ticket.toml`, old transcripts load unchanged; roster stays 7 agents / 39 skills | baseline of the touched modules (222 passed) stays passing; the 3 date-rot failures become passing | lint line `39 skills, 7 agents` unchanged |
| NFR-6 | Auditability | Every automatic or forced state change leaves a trace | each of: stall kill, retry scheduled, retry exhausted, claim adopt, release, force release, review escalation has an audit row or transcript event (asserted per FR) | audit is append-only, never fatal (`audit.py`) |
| NFR-7 | Performance | Watchdog and reconcile cost scale with active Runs, not history | one tick over 100 fake active Runs < 100 ms; reading 10 000 lines through `_handle_line` with timestamping < 2 s; `runs.list_runs` unchanged complexity | uses fakes; no real I/O waits |
| NFR-8 | Concurrency | No lost update on Run JSON; no double adoption of a claim | FR-2 and FR-21 concurrency tests pass 20 consecutive runs | existing lock-file primitive reused, no second mechanism |
| NFR-9 | Security | No secret reaches a log, transcript, comment or audit row; session-identity env vars are not inherited by agent children | FR-6 tests; FR-17 comment test; names only in any message | `CLAUDE_CODE_MESSAGING_TOKEN` is a credential-shaped variable present in this environment |
| NFR-10 | Configurability | Every threshold is read from `console.toml` sections `[runs]`, `[runs.retry]`, `[claims]`, `[review]` with code defaults; invalid values fall back with one warning, never crash | config files are never written by code; `agents.toml` untouched | same pattern as `jobs._config` |
| NFR-11 | Honesty of docs | The known limits are stated where a reader will look | § 8 and the FR-9 test docstring state the `taskkill /T` reach limit; the dossier contradictions are recorded in the decision log | BE HONEST gate |

## Business Rules

- **BR-1:** A terminal Run (`done`, `failed`, `interrupted`, `timed_out`) is immutable.
- **BR-2:** A failure that is unclassified, or whose class is on the non-retryable list, is never retried automatically.
- **BR-3:** Retries are bounded per class and in total; when the bound is reached the Run fails and a human is told once.
- **BR-4:** A retry never fires before `retry_not_before`; the due time is the later of the table delay and `retry_not_before`.
- **BR-5:** The silence clock does not advance while an approval is pending (the approval has its own 300 s bound).
- **BR-6:** A claim whose owner has an ACTIVE Run is never stale, however old.
- **BR-7:** An unknown claim time or unknown owner liveness never causes expiry; the human force path exists for that case.
- **BR-8:** Only `approved` and `human_decision` reset the review counter; escalation stops further rounds until one of them. The verb layer cannot verify who calls; audit is the check.
- **BR-9:** A chat with no Run (started by a human) is never stall-killed, auto-retried or reconciled. Process hygiene (tree kill on stop, env strip, per-turn output cap, lingering-after-result kill) applies to every chat: those protect the machine, not the work.
- **BR-10:** In a read-only mode (`plan`, `ask`) a non-empty reply is never classified `plan_only`.
- **BR-11:** Every kill is a tree kill when the root is alive: ask, wait grace, force; never a group signal without a dedicated group.
- **BR-12:** Ticket and tracker TOML change only through `console/kanban.py` or the verb handlers that wrap the same writers; automatic actors (watchdog, review escalation) call those existing handlers (`ticket_comment`, `tracker_add`) and never write TOML directly; the watchdog thread and the `run-watch` verb call one shared tick function; `agents.toml` and `console/config/*.toml` are never written by code.
- **BR-13:** A force release needs `confirm`, a stated reason of at least 10 characters, and is always audited with the previous holder.

## Data Entities (new / changed)

| Entity | Source | Fields | Lifecycle | Reference |
|---|---|---|---|---|
| Run record | exists | + `attempt`, `attempts[]`, `failure_class`, `failure_detail`, `retry_not_before`, `retry_due`, `retry_of`, `end_reason`, `ended`, `last_output_at`, `liveness{state,reason}`; states + `timed_out`, `scheduled_retry` | create → active → terminal (immutable) | `console/server/runs.py`; FR-1, FR-2 |
| Session snapshot | exists | + `last_output_at` | per session, in memory | `agent_session.py:162`; FR-4 |
| `turn.end` event | exists | + `errors`, `error`, `api_error_status`, `stop_reason` | transcript line | `agent_normalize.py:313`; FR-10 |
| `ticket.toml` | exists | `claimed_at` full UTC timestamp; + `claimed_run`, `review_rounds`, `review_escalated` | claim lifecycle (cleared on release); review counter resets on approve/human decision | `tickets.py:52-84`; FR-19, FR-24 |
| Failure classes, retry table | new, code | class set, per-class caps and delays | static, overridable via config | `run_failures.py` (new); FR-11, FR-15 |
| Config sections `[runs]`, `[runs.retry]`, `[claims]`, `[review]` | new, read-only | thresholds, caps, env strip list | edited by the user only | `console/config/console.toml` (user-edited, not by this ticket) |
| Verb rows `run-watch`, `run-retry`, `claim-release`, `review-round` | new | id, handler, `needs_ticket`, `needs_confirm` | registry load | `console/config/verbs.toml`; FR-18, FR-22, FR-24 |
| Audit actions | new values | `ticket.claim.adopt`, `.release`, `.force_release`, `ticket.review`, `run.stall_kill`, `run.retry`, `run.retry_exhausted` | append-only | `console/server/audit.py` |
| Comments and questions items | exists | author `run-watchdog` / `review-loop` | existing tracker lifecycle | `console/server/trackers.py` |

## Edge Cases

- Run `running` but its session was deleted from the registry → `interrupted`, never `done`.
- Server restarts mid-`scheduled_retry` → retried at the persisted due time through `resume`; if resume refuses → `failed/resume_refused`.
- Two failures in one turn stream (error then result) → classified once, from the final `turn.end`.
- Quota text present but zone unresolvable (no tzdata on Windows) → class `quota`, `retry_not_before=""`, no retry, one escalation comment.
- `turn.end` with `subtype:"success"` and `is_error:true` → failed.
- Exit 0 with refusal → failed, `refusal`, not retried.
- Watchdog tick races a human stop → terminal wins; the tick re-reads under the lock and does nothing.
- Approval pending for the whole threshold window → never stalled; after the 300 s approval timeout denies, the clock resumes from that moment.
- `taskkill` missing from PATH or returns non-zero because the process is already gone → no exception, `proc.wait` decides.
- Grandchild whose parent exited before the kill is unreachable by `taskkill /T` (documented limit; Job Object deferred).
- Runs on other tickets never affect a claim; only the linked Run, or ACTIVE Runs on the same ticket when no Run is linked, count.
- Planner's claim is linked to its finished Run and the builder's Run is live on the same ticket → stale (`run_dead`), adoptable.
- Claim made by an external agent with no console Run, and a console Run starts later on that ticket → the claim stays `held` while that Run is ACTIVE (conservative).
- Claim with empty `claimed_at` and no linked Run (legacy tests, hand edits) → `held/unknown`; only `force` frees it.
- A chat takes another turn after its Run is `done` → untracked; the terminal Run is not touched.
- `run-retry` after a terminal failure → a new Run (`retry_of`), never a rewrite of the old one.
- Date-only legacy `claimed_at` equal to today → end-of-day bound, cannot expire today.
- Same-identity re-claim during a long external session refreshes `claimed_at` (heartbeat).
- `changes_requested` called on a ticket with no `review_*` fields → fields default, count 1.
- A review escalation question already resolved by a human but `human_decision` not called → counter stays escalated; the protocol says the human decision call is what resets (visible in `console context`).
- A queued follow-up drains after a failed turn → the Run follows the newest turn; the failed turn is still recorded in `attempts`.
- Over-long single line from a child → truncated with a marker; stream continues.
- `max_total_retries = 0` → no automatic retries at all (valid, documented way to switch retry off).

## Contradictions with the dossier (verified, recorded)

- The Run store has no lifecycle at all (not merely no watchdog); `claimed_at` is read by `stop_hook.py:61`; Paperclip forbids adopting a live owner's lock and has no TTL, so item 5 is narrowed (decision a8); Paperclip's Windows path is direct-child kill only; Paperclip clears a poisoned session while T-011 refuses silent fresh starts (decision a16).

## Open, non-blocking (need the user; design works without)

- **Q12** human gate for `claim-release force` and `review-round human_decision`: needs the user to add two tool names to the claude row's `gated_tools` in `agents.toml` by hand. Without it: audit + reason + protocol.
- **Q13** phone alert on stall kill / review escalation: needs a user edit of `[notify].events` and a follow-up ticket. Without it: ticket comment, `run-show`, audit.
- **Q14** one captured real quota stream to confirm `resetsAt` units and status words. Without it: both units accepted by magnitude, prose fallback, otherwise no automatic retry.

## Acceptance Criteria

Every FR above carries its own checklist. The ticket is accepted when all of them pass with cited evidence, `python console/kanban.py harness lint` reports 0 errors and 0 warnings at `39 skills, 7 agents`, and the touched-module baseline (222 passed before this ticket) has no new failures while the 3 date-rot failures in `test_stop_hook.py` pass.

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-requirements-draft]] · [[T-020-decision-log]] · [[T-020-iteration-log]] · [[T-020-gap-analysis]] · [[T-020-critique-report]] · [[T-020-context-snapshot]] · [[T-020-user-stories]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
- Source: [[INV-2026-10-01-paperclip-adoption-dossier]]
