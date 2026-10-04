"""T-020 FR-3: reconcile a chat Run with the session it points at.

`sync_run` is pure: a Run record, a plain-dict view of its session and a clock
string in, a patch out (empty means "leave it"). Nothing here reads the
filesystem or the clock, so the whole decision table is tested with dicts.
`session_view` builds that dict from session attributes only (never the event
ring, which can overflow, decision a3); `sweep_startup` is the one function
that touches the run store.
"""

from datetime import datetime, timezone

from . import run_config, run_failures, runs, tickets, trackers, worktrees


def _parse_now(now):
    try:
        return datetime.strptime(now, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _detail(kind, turn_end, exit_code):
    bits = [kind]
    if turn_end:
        bits.append("turn=%s" % (turn_end.get("subtype") or "?"))
    if exit_code is not None:
        bits.append("exit=%s" % exit_code)
    return " ".join(bits)


def _verdict_for(run, kind, turn_end, exit_code, stderr, now, runs_cfg):
    """The `classify` verdict, or a hand-made one when the Run may not be
    classified. Only the Claude CLI's `turn.end` fields are understood (FR-11),
    so another backend maps to `process_lost` or `unclassified` and nothing
    else; so does anything `classify` cannot call a failure (CR-20)."""
    if (run.get("backend") or "") in ("claude", "codex") and turn_end is not None:
        te = turn_end
        rl = ({"status": te["rate_limit"], "resets_at": te.get("resets_at") or 0}
              if te.get("rate_limit") else None)
        verdict = run_failures.classify(te, rl, exit_code, stderr, now, runs_cfg)
        if verdict["class"]:
            return verdict
    elif (run.get("backend") or "") in ("claude", "codex") and kind == "process_lost":
        verdict = run_failures.classify(None, None, exit_code, stderr, now, runs_cfg)
        if verdict["class"]:
            return verdict
    cls = "process_lost" if kind == "process_lost" else "unclassified"
    return {"class": cls, "retryable_class": cls in run_failures.RETRYABLE,
            "detail": _detail(kind, turn_end, exit_code), "retry_not_before": ""}


def decide_default(run, *, kind, turn_end, exit_code, stderr, now, cfg=None, runs_cfg=None):
    """The real `decide_failure`: classify (Claude CLI only), then the retry
    table. `now` is the clock string `sync_run` was given; an unreadable one,
    or any unexpected error, fails closed to `failed/unclassified` with no
    retry (BR-2). `cfg` / `runs_cfg` default to `console.toml`."""
    when = _parse_now(now)
    if when is None:
        return {"state": "failed", "failure_class": "unclassified", "end_reason": "unclassified",
                "failure_detail": _detail(kind, turn_end, exit_code)}
    retry = cfg or run_config.retry_cfg()
    verdict = _verdict_for(run, kind, turn_end, exit_code, stderr, when,
                           runs_cfg or run_config.runs_cfg())
    return run_failures.decide(run, verdict, when, retry)


def session_view(session, pending_approvals):
    """The plain-dict view `sync_run` reads. `pending_approvals` is
    `Approvals.pending_for(session.id)`. The session keeps no stderr, so
    `stderr` is always "" until a later task gives it one."""
    snap = session.snapshot()
    return {
        "alive": bool(snap["alive"]),
        "busy": bool(snap["busy"]),
        "queued": len(snap["queued"]),
        "last_turn": snap["last_turn"],
        "turn_count": snap["turn_count"],
        "last_output_at": snap["last_output_at"],
        "started_utc": snap["started_utc"],
        "stop_requested": bool(session.stop_requested),
        "exit_code": snap["exit_code"],
        "transport": snap["transport"],
        # An API session has no child and never passes `_handle_line`, so
        # there is no output clock to watch (CR-25); it is still reconciled.
        "watchable": not session.backend.is_api,
        "stderr": "",
        "mode": snap.get("mode") or "",
        "pending_approvals": list(pending_approvals),
    }


def collect_evidence(repo_root, run, view):
    """Durable evidence for FR-13, from outside the turn: file-mutating tools
    and console verbs in `view["last_turn"]["tools"]`, ticket comments and
    tracker items created since the Run started, a non-empty worktree diffstat,
    and whether a new critical question is open. Unreadable ticket data counts
    as no evidence (fail closed, NFR-2). Tracker items carry a date only, so
    those are compared by day; comments carry a full timestamp."""
    tools = ((view or {}).get("last_turn") or {}).get("tools")
    out = run_failures.tool_evidence(tools)
    out.update(comments=0, items=0, diff=False, lane="")
    created = run.get("created") or ""
    ticket = run.get("ticket") or ""
    if ticket:
        try:
            out["lane"] = (tickets.load(repo_root, ticket) or {}).get("stage", "")
            out["comments"] = sum(
                1 for c in trackers.list_items(repo_root, ticket, "comments")
                if created and (c.get("posted_on") or "") >= created)
            for kind, stamp in (("questions", "raised_on"), ("bugs", "found_on"),
                                ("todos", "captured_on")):
                for item in trackers.list_items(repo_root, ticket, kind):
                    if created and (item.get(stamp) or "") >= created[:10]:
                        out["items"] += 1
                        if (kind == "questions" and item.get("priority") == "critical"
                                and item.get("status") == "open"):
                            out["critical_question"] = True
        except (OSError, ValueError, KeyError):
            pass
    stat = worktrees.diff_stat(repo_root, run.get("worktree_path") or "")
    out["diff"] = stat not in ("", "no changes")
    out["count"] += out["comments"] + out["items"] + (1 if out["diff"] else 0)
    return out


def _ended(state, reason, now, view):
    patch = {"state": state, "end_reason": reason, "ended": now}
    if view and view.get("last_output_at"):
        patch["last_output_at"] = view["last_output_at"]
    return patch


def _failed(run, kind, turn_end, view, now, decide_failure):
    patch = dict(decide_failure(
        run, kind=kind, turn_end=turn_end,
        exit_code=view.get("exit_code") if view else None,
        stderr=view.get("stderr", "") if view else "", now=now))
    if patch.get("state") in runs.TERMINAL:  # a scheduled retry has not ended
        patch.setdefault("ended", now)
        patch.setdefault("liveness", {"state": "failed", "reason": " ".join(
            str(patch.get("failure_detail") or patch.get("end_reason") or "").split())[:200]})
    if view and view.get("last_output_at"):
        patch.setdefault("last_output_at", view["last_output_at"])
    return patch


def _liveness(run, view, last, evidence):
    """FR-13, written in the same patch as the terminal `done` (FR-2).
    `evidence` is a callable `(run, view) -> dict` (the caller owns the I/O,
    `collect_evidence`), or None for tool evidence from the view alone."""
    ev = evidence(run, view) if evidence else run_failures.tool_evidence(last.get("tools"))
    return run_failures.liveness(last, view.get("mode", ""), ev, ev.get("lane", ""),
                                 last.get("result", ""))


def sync_run(run, view, now, *, startup=False, decide_failure=None, evidence=None):
    """The patch that brings `run` in line with its session, or `{}`.

    `view` is None when the server holds no session for the Run's chat.
    Precedence: terminal / non-chat no-op; a stop request; `scheduled_retry`
    (waiting on purpose, CR-23); no session or a dead one that never ended a
    turn; pending approval; busy or queued; last turn clean or failed.
    `decide_failure` defaults to the real policy (`decide_default`); `evidence`
    is the optional FR-13 evidence callable, see `_liveness`.
    """
    decide_failure = decide_failure or decide_default
    if run["executor"] != "chat" or run["state"] in runs.TERMINAL:
        return {}
    if view is not None and view["stop_requested"]:
        return _ended("interrupted", "stopped", now, view)
    if run["state"] == "scheduled_retry":
        return {}

    last = view["last_turn"] if view else None
    lost = view is None or (not view["alive"] and (view["busy"] or last is None))
    if lost:
        if startup:
            return _ended("interrupted", "server_restart", now, view)
        return _failed(run, "process_lost", last, view, now, decide_failure)

    if view["alive"]:
        if view["pending_approvals"]:
            target = "needs-approval"
        elif view["busy"] or view["queued"] or last is None:
            target = "running"
        else:
            target = None
        if target:
            return {} if target == run["state"] else {"state": target}

    failed = last["is_error"] or last["subtype"].startswith("error")
    if not failed:
        patch = _ended("done", "completed", now, view)
        patch["liveness"] = _liveness(run, view, last, evidence)
        return patch
    kind = "process_lost" if last["subtype"] == "process_exit" else "turn_error"
    return _failed(run, kind, last, view, now, decide_failure)


def sweep_startup(repo_root, registry, approvals, now, *, decide_failure=None):
    """Reconcile every ACTIVE chat Run once, at server start. `registry` is
    anything with `.get(chat_id)` returning a session or None (`agent_manager`
    or a dict). Returns `{run_id: patch}` for the Runs that changed."""
    changed = {}
    for rec in runs.list_runs(repo_root):
        if rec["executor"] != "chat" or rec["state"] not in runs.ACTIVE:
            continue
        sess = registry.get(rec["executor_id"])
        view = (session_view(sess, approvals.pending_for(rec["executor_id"]))
                if sess is not None else None)
        patch = sync_run(rec, view, now, startup=True, decide_failure=decide_failure,
                         evidence=lambda r, v: collect_evidence(repo_root, r, v))
        if not patch:
            continue
        try:
            runs.update(repo_root, rec["id"], **patch)
        except ValueError:
            continue  # went terminal between the listing and the write
        changed[rec["id"]] = patch
    return changed
