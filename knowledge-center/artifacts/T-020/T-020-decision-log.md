---
ticket: "T-020"
artifact: decision-log
---

# Decisions: T-020

> Every decision below was **decided under delegated authority 2026-10-01, reversible**: the owner said "go wild, do end to end", so the analyst chose the safest minimal default. No user answer is implied or invented. Each links to its tracker question (`{T}-questions.toml`). Reverting one means a `requirements` evolve, not a silent edit.

## a1-run-lifecycle-first (Q4 context)
**Decision:** Build the missing Run lifecycle before anything else. States: add exactly `timed_out` and `scheduled_retry`; no `cancelled` (a human stop is `interrupted` with `end_reason=stopped`). Terminal states are immutable; Run JSON gets a locked `update`.
**Context:** `runs.set_state` has no caller outside tests; Runs stay `running` forever (`runs.py:107`, grep).
**Alternatives:** (a) add a `cancelled` state, rejected: one more state for a distinction `end_reason` carries; (b) leave Runs write-once and keep the watchdog in session memory only, rejected: nothing survives a restart and claims could not read Run state.
**Rationale:** Items 1, 2, 3 and 5 all read Run state; a minimal state set keeps the board vocabulary small.
**Impact:** FR-1..FR-3; dossier effort "S" becomes about L.

## a2-run-covers-chat-until-first-terminal (Q2)
**Decision:** A Run covers its chat from creation until it first reaches a terminal state. Later turns on the same chat are not tracked; a human is present for those.
**Alternatives:** reopen terminal Runs on a new turn (rejected: breaks immutability and any reader that saw `done`); one Run per turn (rejected: Runs are created by verbs, not per turn).
**Rationale:** Keeps BR-1 simple and testable. **Impact:** § 3 scope, § 8 edge case, FR-3.

## a3-session-retains-last-turn (Q3)
**Decision:** `BaseSession` keeps `last_turn` (the `turn.end` plus that turn's last `rate_limit` notice) and a turn counter as attributes. `sync_run` reads attributes, never the 4000-event ring.
**Rationale:** The ring can overflow within one 15 s tick on a long turn (`agent_events.py:38`). **Impact:** FR-3, FR-4, FR-11.

## a4-scope-chat-runs-only (Q4)
**Decision:** Watchdog, reconcile and retry apply only to `executor=chat` Runs created by `delegate`/`launch-role`. Chats a human starts in the Agents tab have no Run and are never stall-killed or retried. Process hygiene (tree kill, env strip, per-turn output cap, lingering-after-result kill) applies to every chat.
**Alternatives:** create a Run for every chat (rejected: changes the Agents tab flow and would auto-kill interactive work); hygiene only for Runs (rejected: orphan processes come from any chat).
**Impact:** BR-9 (narrowed), FR-5..FR-8, FR-14.

## a5-defaults (Q5)
**Decision:** stall suspect 600 s; stall kill 1800 s (0 means flag only); watch tick 15 s; claim TTL 28 800 s (0 disables TTL); dead-owner grace 60 s; transient retry delays 30 s then 120 s; quota 2 retries; max-turns 2 retries at 1 s; process-lost 1 retry at 10 s; total retries 3; line cap 1 MiB; per-turn output cap 64 MiB; linger grace 5 s; quota parse horizon 8 days and quota auto-wait limit 6 h; review rounds 3. All config under `console.toml` sections `[runs]`, `[runs.retry]`, `[claims]`, `[review]` with code defaults; invalid values fall back with one warning.
**Rationale:** Paperclip scaled down: 60 min / 4 h (`recovery/service.ts:166`) to 10 / 30 min, because a single-user console wants a hung `claude` freed within an hour. Transient delays `[30,30]` (`heartbeat.ts:815`) widened to `[30,120]` for a rate-limit that clears in minutes. Review rounds 3 is Paperclip's constant (`issue-execution-policy.ts:69`). TTL 8 h is one working day and only applies when owner liveness is unknown. Nothing here is measured on this console; they are proposals marked reversible.
**Impact:** FR-7, FR-8, FR-12, FR-14, FR-15, FR-20, FR-24, NFR-10.

## a6-taskkill-not-job-object (Q6)
**Decision:** Windows tree kill is `taskkill /PID n /T` then `/T /F`, ported from `desktop/sidecar.py:208-219` into `procs.kill_tree`. POSIX: `start_new_session=True` plus `killpg` TERM then KILL. A ctypes Job Object is deferred as a todo.
**Alternatives:** Job Object now: reaches reparented grandchildren and cleans up on a server crash, but needs `AssignProcessToJobObject` after spawn (a race window) and hits the job-breakaway failure class that bit CI on 2026-09-07; it also needs a second fallback path.
**Rationale:** Smallest design meeting FR-9's no-orphan test for the cases we initiate (kill while the root is alive). **Known limit:** a grandchild whose parent already exited is out of reach of `/T`; stated in § 8 and the FR-9 docstring. **Impact:** FR-5, FR-9.

## a7-review-counter-on-ticket-toml (Q7)
**Decision:** `review_rounds` and `review_escalated` live on `ticket.toml`, mutated only by `tickets.record_review` under `atomic_update`, through one `review-round` verb with `outcome` of `changes_requested | approved | human_decision`. Escalation opens one critical question plus a comment; it moves no lane.
**Alternatives:** a new tracker kind (rejected: touches `trackers.VALID_KINDS`, `ensure_all`, every ticket scaffold and needs a template); counting verifier bugs (rejected: bugs are not rounds).
**Rationale:** Same pattern as `set_claim`/`set_pr`; one counter per ticket, as Paperclip keeps it per stage. **Limit:** the verb layer cannot tell human from agent, so BR-8 relies on audit and protocol; see Q12. **Impact:** FR-24, FR-25.

## a8-no-ttl-for-live-owner (Q8)
**Decision:** A claim whose owner has an ACTIVE Run is never stale, however old. TTL applies only when the claim has no owning Run and no ACTIVE Run exists on the ticket.
**Context (contradiction recorded):** the dossier's "adopt if the owning run/pid is dead **or** `claimed_at` is past a TTL" read literally steals live work. Paperclip: "must not clear or adopt locks held by non-terminal runs" (`doc/execution-semantics.md:184`), no TTL (`issues.ts:7505`). T-018 reuses one worktree per ticket, so a stolen claim means two agents in one worktree.
**Impact:** FR-20, BR-6, BR-7.

## a9-claimed-run-linkage (Q1)
**Decision:** Add optional `claimed_run` to `ticket.toml`. The `claim` verb takes an optional `run=` argument; when absent it auto-links to the sole ACTIVE chat Run on the ticket, else stays empty. Empty means "owner unknown": any ACTIVE Run on the ticket protects the claim. `claimed_run` is cleared on release.
**Alternatives:** match by identity string (rejected: identities are free text); require agents to pass their run id (rejected: they do not know it); no link (rejected: CR-2 shows a new owner would be blocked by its own live Run).
**Rationale:** Failure mode is conservative: a wrong auto-link only keeps a claim "held" longer. **Impact:** FR-19..FR-22, data entity `ticket.toml`.

## a10-env-deny-list (Q9)
**Decision:** Default deny list of 11 names: `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SESSION`, `CLAUDE_CODE_PARENT_SESSION` (Paperclip's four, `server-utils.ts:4717-4722`) plus `CLAUDE_CODE_SESSION_ID`, `CLAUDE_CODE_CHILD_SESSION`, `CLAUDE_CODE_HOST_SESSION_ID`, `CLAUDE_CODE_MESSAGING_SOCKET`, `CLAUDE_CODE_MESSAGING_TOKEN`, `CLAUDE_CODE_EXECPATH`, `CLAUDE_PID` (present in this session's environment, names only inspected). Overridable by `[runs].env_strip`. Never strip `ANTHROPIC_*`, `CLAUDE_CODE_OAUTH_*`, `CLAUDE_CODE_USE_*`, `CLAUDE_CODE_MAX_OUTPUT_TOKENS`.
**Rationale:** Paperclip's list matches only 2 of the 27 `CLAUDE*` variables here; stripping by prefix would break auth. `CLAUDECODE` as the nesting guard is from Paperclip's comment, not reproduced (no real `claude` spawn); recorded as an Open Confirmation. **Impact:** FR-6, NFR-9.

## a11-no-auto-continuation-of-plan-only (Q10)
**Decision:** `plan_only` and `empty` are classified and recorded on the Run; never auto-continued or retried in this ticket.
**Rationale:** Paperclip continues them within a bounded budget; here each continuation spends model tokens and the default modes are read-only, so a policy decision belongs to the owner. **Impact:** FR-13.

## a12-claimed-at-utc-timestamp (Q11)
**Decision:** `claimed_at` becomes `YYYY-MM-DDTHH:MM:SSZ` (UTC). Legacy date-only is read as the end of that day UTC; empty or unparsable is unknown (fail closed). `stop_hook`'s string comparison stays valid (`stop_hook.py:20-29` anticipated full timestamps). The 3 baseline `test_stop_hook.py` failures (date-rot fixtures) are fixed with a clock seam as part of FR-19.
**Impact:** FR-19, NFR-5.

## a13-watchdog-own-thread
**Decision:** The watchdog is a thread owned by `agent_manager`, started by the agents plugin, not hung on `schedules.Ticker`, which does not start unless a schedule is enabled (`httpd.py:276-279`; both shipped schedules are parked). `run-watch` is the same tick as a verb for on-demand and scheduled use. Ticks are single-flight.
**Impact:** FR-14, FR-18.

## a14-dead-session-rule
**Decision:** A session that dies while the server runs, without a terminal `turn.end`, is `process_lost` and follows the retry table (1 retry via `resume`). `interrupted` is reserved for the startup sweep (the server restart killed it) and for a human stop; neither is retried automatically. `run-retry` accepts `failed`, `timed_out` and `interrupted`.
**Rationale:** Auto-resuming every Run at every console restart would surprise the owner; an in-server crash is different. Resolves CR-5. **Impact:** FR-3, FR-15, FR-18.

## a15-escalation-is-a-comment
**Decision:** A terminal `failed`/`timed_out` Run with a ticket gets one `comments` item from `run-watchdog` with class, detail and the next human action. No question is opened and no lane moves, except the review loop (FR-24), which opens one critical question because it is a decision, not a fault.
**Rationale:** A comment does not block `ready`; a stalled run is information, a review stalemate is a blocker. **Impact:** FR-17, FR-24.

## a16-non-retryable-and-no-fresh-start
**Decision:** `timed_out`/`stalled` is non-retryable by default (a human decides, `run-retry`). `unknown_session` and `poisoned_session` are non-retryable and never clear the session to start fresh.
**Context (contradiction recorded):** Paperclip clears a poisoned or unknown session and continues from scratch (`execute.ts:1249-1255`); this console's baseline refuses to resume as a new chat (`agent_manager.py:282-285`, T-011).
**Impact:** FR-15, FR-16.

## a17-critique-report-has-no-template
**Decision:** `T-020-critique-report.md` was scaffolded from `challenge-standards/rules.md` and the T-018 precedent because `_template/` has no `critique-report.md`. This is a gap in the template set, flagged here rather than papered over; not fixed in this ticket (no template additions in scope).

## Open, non-blocking (needs the user; design works without)
- **Q12** human gate for `claim-release force` and `review-round human_decision`: user may add the two MCP tool names to the claude row's `gated_tools` in `agents.toml` by hand. Without it: audit + protocol + reason requirement.
- **Q13** phone alert for stall or escalation: needs a user edit of `[notify].events` and a follow-up. Without it: ticket comment, `run-show`, audit.
- **Q14** one captured real quota stream to confirm `resetsAt` units/status words. Without it: both units accepted by magnitude, prose fallback, otherwise no automatic retry.

## Amendment 2026-10-02
**FR-18 / FR-14 (run-watch ownership; verifier defect D-A).** The frozen FR-18 reads `run-watch` as "one reconcile + watchdog + due-retry tick" with no process qualifier. Clarified, not rewritten: a tick is only meaningful in the process that owns the live session registry (the server, which starts the watchdog). (1) The startup sweep runs only from the watchdog thread's first real tick, never from the verb. (2) `run-watch` from a process without a live registry (CLI, stdio MCP) does nothing and returns `{ok: true, skipped: "no live session registry in this process", synced: 0, suspicious: 0, killed: 0, retried: 0, errors: 0}`; inside the server (HTTP `/api/verbs/run-watch/run`, scheduler) it runs the one shared single-flight tick (BR-12). Ownership signal: `agent_manager.owns_registry()`, set by `start_watchdog`. The FR-18 AC "returns counts ... mutates nothing when no Runs exist" still holds in both modes. Consequence: with `[runs] watchdog_enabled = false` no startup sweep runs (the sweep is part of the watchdog).

## Links
- [[T-020-summary]] · [[T-020-analysis]] · [[T-020-requirements]] · [[T-020-requirements-draft]] · [[T-020-decision-log]] · `T-020-questions.toml` · [[T-020-critique-report]] · [[T-020-iteration-log]] · [[T-020-plan]] · [[T-020-progress]] · [[T-020-verification]]
