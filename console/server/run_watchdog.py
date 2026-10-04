"""T-020 FR-14: the stall watchdog.

`evaluate` is the pure decision: one Run, a plain-dict view of its session, a
clock and the thresholds in, an action out. Nothing in it reads a file or the
time, so the whole silence table is tested with dicts and an injected `now`.
`tick` is the one impure pass (thread and `run-watch` share it) and `Watchdog`
the thread `agent_manager` owns.
"""

import os
import sys
import threading
from datetime import datetime, timezone

from . import audit, run_config, run_sync, runs, tickets, trackers

_FMT = "%Y-%m-%dT%H:%M:%SZ"


def parse_utc(stamp):
    """Aware datetime from a UTC `...Z` stamp, or None when absent or unreadable."""
    try:
        return datetime.strptime(stamp, _FMT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _silent_since(run, view):
    """When the silence clock started: the latest of the session's last output
    and the `clock_floor` (set when an approval ended, BR-5), else the session's
    UTC start, else the Run's creation. Never the local-naive `started` (CR-24)."""
    seen = [parse_utc(view.get("last_output_at")), parse_utc(view.get("clock_floor"))]
    seen = [t for t in seen if t]
    if seen:
        return max(seen)
    return parse_utc(view.get("started_utc")) or parse_utc(run.get("created"))


def evaluate(run, view, now, cfg):
    """`{action, silence_secs}`; action is `none`, `suspect` or `kill`.

    Only a `running` chat Run with a watchable session has a silence clock.
    A pending approval pauses it (BR-5). `suspect` fires once: a Run already
    flagged (`liveness.state == "suspicious"`) gets `none` until the kill
    threshold. `stall_kill_secs == 0` means flag only, never kill. An unknown
    start fails closed to `none`."""
    idle = {"action": "none", "silence_secs": 0}
    if run.get("executor") != "chat" or run.get("state") != "running":
        return idle
    if view is None or not view.get("watchable", True) or view.get("pending_approvals"):
        return idle
    since = _silent_since(run, view)
    if since is None:
        return idle
    silence = max(0.0, (now - since).total_seconds())
    out = {"action": "none", "silence_secs": silence}
    kill = cfg["stall_kill_secs"]
    if kill and silence >= kill:
        out["action"] = "kill"
    elif silence > cfg["stall_suspect_secs"]:
        flagged = (run.get("liveness") or {}).get("state") == "suspicious"
        out["action"] = "none" if flagged else "suspect"
    return out


# -- the tick -------------------------------------------------------------------

_tick_lock = threading.Lock()
#: Per-process watchdog memory: Runs seen terminal (so a tick never re-parses
#: them), Runs whose approval is pending, and the clock floor stamped when an
#: approval ended (BR-5).
_terminal = set()
_paused = set()
_floor = {}
_last = {"last_tick": "", "errors": 0}
KILL_GRACE = 2.0
#: The fixed message a retry sends into the conversation (FR-16).
CONTINUATION = ("The previous attempt was interrupted by a temporary failure. "
                "Continue the task from where you left off.")
_ACTOR = {"addr": "local", "agent": "watchdog"}


def reset():
    """Forget everything between ticks (tests, and a clean server start)."""
    _terminal.clear()
    _paused.clear()
    _floor.clear()
    _last.update(last_tick="", errors=0)


def last_tick():
    return dict(_last)


def _stamp(dt):
    return dt.astimezone(timezone.utc).strftime(_FMT)


def _audit(repo_root, action, run_id, detail):
    audit.record(repo_root, action, actor=_ACTOR, target=run_id, detail=detail)


def _notice(sess, kind, text):
    sess.stream.publish({"type": "notice", "level": "warn", "kind": kind, "text": text})


#: FR-17: what a human should do next, one row per way a Run can end `failed`
#: or `timed_out`: every `run_failures.CLASSES` entry plus the three ends that
#: have no class of their own.
ACTION_TABLE = {
    "auth_required": "Log the agent CLI in again, then run-retry.",
    "model_not_found": "Fix the model name in the chat or agents.toml, then start a new Run.",
    "max_turns": "Raise the turn limit or split the task, then run-retry.",
    "unknown_session": "The CLI forgot the conversation; start a new chat for this ticket.",
    "poisoned_session": "The conversation is corrupt; start a new chat for this ticket.",
    "image_error": "Remove or replace the image the agent could not read, then start a new Run.",
    "refusal": "Rephrase or narrow the request; the model declined it.",
    "quota": "Wait for the usage window to reset, then run-retry.",
    "transient_upstream": "The provider kept failing; check its status page, then run-retry.",
    "process_lost": "The agent process died; check the console log, then run-retry.",
    "output_cap": "The agent produced too much output; narrow the task, then start a new Run.",
    "stalled": "The agent went silent and was stopped; inspect the chat, then run-retry.",
    "unclassified": "Open the Run in the inspector to see why it failed.",
    "resume_refused": "The chat cannot be resumed; start a new chat for this ticket.",
    "retry_exhausted": "Automatic retries are used up; inspect the failures, then run-retry.",
    "retry_failed": "The retry could not be sent; check the chat, then run-retry.",
}
_DETAIL_MAX = 300
_SECRET_NAME = ("TOKEN", "SECRET", "KEY", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTH")


def _scrub(text):
    """No credential-shaped env value reaches a comment (NFR-9)."""
    for name, value in os.environ.items():
        if len(value) >= 6 and any(w in name.upper() for w in _SECRET_NAME):
            text = text.replace(value, "[redacted]")
    return text


def _comment_text(run):
    key = run.get("end_reason") if run.get("end_reason") in ACTION_TABLE else None
    key = key or run.get("failure_class") or "unclassified"
    cls = run.get("failure_class") or key
    detail = _scrub(" ".join(str(run.get("failure_detail") or "").split()))[:_DETAIL_MAX]
    text = "[run %s] ended %s (%s). Detail: %s. Attempts: %s. Next: %s" % (
        run["id"], run["state"], cls if cls == key else "%s, %s" % (cls, key),
        detail or "none recorded", len(run.get("attempts") or []) or run.get("attempt") or 1,
        ACTION_TABLE.get(key, ACTION_TABLE["unclassified"]))
    if cls == "quota" and run.get("retry_not_before"):
        text += " The quota resets at %s." % run["retry_not_before"]
    return text


def escalate(repo_root, run):
    """FR-17: one `run-watchdog` comment on the Run's ticket when it ended
    `failed` or `timed_out`. Idempotent without a Run field: a comment by that
    author that already starts `[run <id>]` means it was done (CR-26). True only
    when a comment was posted. A missing ticket or any write error is reported
    on stderr, never raised: escalation must not stop the tick."""
    if run.get("state") not in ("failed", "timed_out") or not run.get("ticket"):
        return False
    marker = "[run %s]" % run["id"]
    try:
        if tickets.load(repo_root, run["ticket"]) is None:
            print("run watchdog: run %s names unknown ticket %s" % (run["id"], run["ticket"]),
                  file=sys.stderr)
            return False
        for item in trackers.list_items(repo_root, run["ticket"], "comments"):
            if item.get("author") == "run-watchdog" and str(item.get("text", "")).startswith(marker):
                return False
        from . import verb_handlers  # lazy: verb_handlers imports this module for run-watch
        verb_handlers.ticket_comment(repo_root, ticket=run["ticket"],
                                     text=_comment_text(run), author="run-watchdog")
        return True
    except Exception as exc:  # noqa: BLE001
        print("run watchdog: escalation for run %s failed: %s" % (run.get("id"), exc),
              file=sys.stderr)
        return False


def _apply(repo_root, rec, patch):
    """Write `patch` through `runs.update`; False when the Run went terminal
    under us (a human stop, the session ending), which is not an error."""
    try:
        runs.update(repo_root, rec["id"], **patch)
    except (ValueError, FileNotFoundError):
        return False
    rec.update(patch)
    escalate(repo_root, rec)  # a no-op unless that write ended the Run failed
    return True


def _clock_floor(rec, view, stamp):
    """`clock_floor` for `evaluate`: the tick that first sees a pending
    approval gone stamps it, so the silence clock restarts there (BR-5)."""
    rid = rec["id"]
    if view["pending_approvals"]:
        _paused.add(rid)
    elif rid in _paused:
        _paused.discard(rid)
        _floor[rid] = stamp
    return _floor.get(rid, "")


def _watch_one(repo_root, rec, sess, approvals, now, stamp, cfg, counts):
    view = run_sync.session_view(sess, approvals.pending_for(rec["executor_id"]))
    view["clock_floor"] = _clock_floor(rec, view, stamp)
    patch = run_sync.sync_run(
        rec, view, stamp, evidence=lambda r, v: run_sync.collect_evidence(repo_root, r, v))
    if patch:
        if not _apply(repo_root, rec, patch):
            return
        counts["synced"] += 1
        if patch.get("end_reason") == "retry_exhausted":
            _audit(repo_root, "run.retry_exhausted", rec["id"],
                   {"failure_class": patch.get("failure_class", "")})
        if rec["state"] != "running":
            return  # ended, waiting to retry or on an approval: no silence clock
    verdict = evaluate(rec, view, now, cfg)
    silence = int(verdict["silence_secs"])
    reason = "no output for %d s" % silence
    if verdict["action"] == "suspect":
        if _apply(repo_root, rec, {"liveness": {"state": "suspicious", "reason": reason}}):
            _notice(sess, "stall_suspect", "The agent has been silent for %d s." % silence)
            counts["suspicious"] += 1
    elif verdict["action"] == "kill":
        # On disk first: the exit that follows the kill must find a terminal
        # Run and cannot be re-read as `process_lost`.
        if _apply(repo_root, rec, {
                "state": "timed_out", "failure_class": "stalled", "end_reason": "stalled",
                "failure_detail": reason, "ended": stamp,
                "liveness": {"state": "failed", "reason": reason}}):
            _notice(sess, "stall_kill", "The agent was silent for %d s and was stopped." % silence)
            _audit(repo_root, "run.stall_kill", rec["id"],
                   {"silence_secs": silence, "chat": rec["executor_id"]})
            counts["killed"] += 1
            sess.kill_process(grace=KILL_GRACE)


def end_for_limit(repo_root, rec, failure_class, detail, stamp):
    """The end-of-Run path for a per-turn limit kill (`output_cap`): the Run is
    written `failed` through the same `_apply` as every other failure, so it
    gets its one escalation comment (FR-17) and an audit row (NFR-6). False
    when the Run had already ended."""
    if not _apply(repo_root, rec, {
            "state": "failed", "failure_class": failure_class, "end_reason": failure_class,
            "failure_detail": detail, "ended": stamp,
            "liveness": {"state": "failed", "reason": failure_class}}):
        return False
    _audit(repo_root, "run.%s" % failure_class, rec["id"], {"failure_class": failure_class})
    return True


def _end_failed(repo_root, rec, reason, detail, stamp):
    """A retry that could not start ends the Run `failed`, in one write."""
    return _apply(repo_root, rec, {
        "state": "failed", "end_reason": reason, "failure_detail": detail, "ended": stamp,
        "liveness": {"state": "failed", "reason": reason}})


def _retry_one(repo_root, rec, registry, approvals, now, stamp, counts):
    """FR-16 for one `scheduled_retry` Run: cancel on a stop request, wait for
    `retry_due`, then send the continuation to the live session or resume the
    dead one first. A refused resume never starts a new chat (T-011): the Run
    ends `failed/resume_refused`. The due time is on the record, so a fresh
    process picks the schedule up where it was."""
    chat = rec["executor_id"]
    sess = registry.get(chat)
    if sess is not None:
        cancel = run_sync.sync_run(
            rec, run_sync.session_view(sess, approvals.pending_for(chat)), stamp)
        if cancel:  # only a stop request answers for a scheduled_retry
            _apply(repo_root, rec, cancel)
            return
    due = parse_utc(rec.get("retry_due"))
    if due is None or due > now:
        return
    if sess is None or not sess.alive:
        port = registry.server_port() if hasattr(registry, "server_port") else 0
        try:
            registry.resume(repo_root, chat, server_port=port)
        except (ValueError, FileNotFoundError) as exc:
            _end_failed(repo_root, rec, "resume_refused", "resume refused: %s" % exc, stamp)
            return
    try:
        registry.send(chat, CONTINUATION)
    except (RuntimeError, OSError) as exc:
        _end_failed(repo_root, rec, "retry_failed", "retry send failed: %s" % exc, stamp)
        return
    if _apply(repo_root, rec, {"state": "running", "attempt": int(rec.get("attempt") or 1) + 1,
                               "retry_due": ""}):
        counts["retried"] += 1
        _audit(repo_root, "run.retry", rec["id"], {"attempt": rec["attempt"], "chat": chat})


_retry_lock = threading.Lock()
_RETRYABLE_STATES = ("failed", "timed_out", "interrupted")


def manual_retry(repo_root, run_id):
    """Retry an ended Run by hand (T-020 FR-18): a NEW Run with `retry_of` set,
    `scheduled_retry`, due now, which the next watchdog tick sends into the same
    chat. The old record is never written. Refused for a Run that has not
    failed, or while a Run retrying it is still active."""
    run_id = str(run_id or "").strip()
    old = runs.get(repo_root, run_id) if run_id else None
    if old is None:
        return {"ok": False, "error": "no run %s" % run_id}
    if old["state"] not in _RETRYABLE_STATES:
        return {"ok": False, "error": "run %s is %s; only a failed, timed_out or interrupted "
                                      "run can be retried" % (run_id, old["state"])}
    with _retry_lock:  # check and create as one step, so two callers cannot both pass
        live = [r["id"] for r in runs.list_runs(repo_root)
                if r["retry_of"] == run_id and r["state"] in runs.ACTIVE]
        if live:
            return {"ok": False, "error": "run %s already has an active retry (%s)"
                                          % (run_id, live[0])}
        due = _stamp(datetime.now(timezone.utc))
        new = runs.create(
            repo_root, ticket=old["ticket"], role=old["role"], executor=old["executor"],
            executor_id=old["executor_id"], backend=old["backend"], state="scheduled_retry",
            worktree_path=old["worktree_path"], worktree_branch=old["worktree_branch"],
            worktree_error=old["worktree_error"], retry_of=run_id, retry_due=due)
    return {"ok": True, "run": new}


def tick(repo_root, now=None, registry=None, approvals=None, startup=None):
    """One watchdog pass over every active chat Run; the thread and the
    `run-watch` verb both call this. Single-flight: a caller that finds a tick
    running gets `{busy: True}` and does nothing. The first tick of a process
    also runs the startup sweep. A failure on one Run is counted and never
    stops the others. Writes only through `runs.update` (BR-12). A chat with
    no Run is never touched (BR-9); a Run with no session is skipped.

    `startup=True` runs the one-time startup sweep, which is only valid in the
    process that owns the live session registry: the server's watchdog thread
    asks for it on its first real tick. It is never implicit, so a tick driven
    from anywhere else cannot mark live Runs `interrupted`."""
    if not _tick_lock.acquire(blocking=False):
        return {"busy": True}
    try:
        now = now or datetime.now(timezone.utc)
        stamp = _stamp(now)
        if registry is None:
            from . import agent_manager  # lazy: agent_manager owns this module's thread
            registry = agent_manager
        if approvals is None:
            from . import agent_approvals
            approvals = agent_approvals.REGISTRY
        cfg = run_config.runs_cfg(repo_root)
        counts = {"synced": 0, "suspicious": 0, "killed": 0, "retried": 0, "errors": 0}
        if startup:
            try:
                swept = run_sync.sweep_startup(repo_root, registry, approvals, stamp)
                counts["synced"] += len(swept)
            except Exception as exc:  # noqa: BLE001
                counts["errors"] += 1
                print("run watchdog: startup sweep failed: %s" % exc, file=sys.stderr)
        active = [r for r in runs.list_active(repo_root, _terminal) if r["executor"] == "chat"]
        live_ids = {r["id"] for r in active}
        for gone in (_paused | set(_floor)) - live_ids:
            _paused.discard(gone)
            _floor.pop(gone, None)
        for rec in active:
            sess = registry.get(rec["executor_id"])
            try:
                if rec["state"] == "scheduled_retry":
                    _retry_one(repo_root, rec, registry, approvals, now, stamp, counts)
                    continue
                if sess is None:
                    continue  # nothing to read or kill; the startup sweep owns this case
                _watch_one(repo_root, rec, sess, approvals, now, stamp, cfg, counts)
            except Exception as exc:  # noqa: BLE001
                counts["errors"] += 1
                print("run watchdog: run %s failed: %s" % (rec.get("id"), exc), file=sys.stderr)
        _last.update(last_tick=stamp, errors=counts["errors"])
        return dict(counts, busy=False, last_tick=stamp)
    finally:
        _tick_lock.release()


class Watchdog(threading.Thread):
    """Calls `tick` every `watch_interval_secs` until stopped. A daemon thread
    that waits on an Event, so `stop` ends it at once rather than after a
    sleep."""

    def __init__(self, repo_root, interval):
        super().__init__(name="run-watchdog", daemon=True)
        self.repo_root = repo_root
        self.interval = max(0.05, float(interval))
        self._stop_evt = threading.Event()

    def run(self):
        sweep = True  # the startup sweep rides the first tick that actually runs
        while not self._stop_evt.is_set():
            try:
                out = tick(self.repo_root, startup=sweep)
                if not out.get("busy"):
                    sweep = False
            except Exception as exc:  # noqa: BLE001
                _last["errors"] += 1
                print("run watchdog: tick failed: %s" % exc, file=sys.stderr)
            self._stop_evt.wait(self.interval)

    def stop(self, timeout=2.0):
        self._stop_evt.set()
        if self.is_alive() and threading.current_thread() is not self:
            self.join(timeout)
