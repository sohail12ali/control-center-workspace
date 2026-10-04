"""T-020 FR-3: reconcile a chat Run with its session.

`sync_run` is pure: the tests call it with plain dicts and no repo root. The
sweep and `session_view` are checked against the real run store and the real
session classes, with no process spawned.
"""

from datetime import datetime, timezone

import pytest

from server import agent_session, runs, run_sync
from server.agent_events import RING_MAX, Stream

NOW = "2026-10-01T12:00:00Z"
OK = {"subtype": "success", "is_error": False, "rate_limit": "", "tools": {}}
ERR = {"subtype": "error_during_execution", "is_error": True, "rate_limit": "", "tools": {}}
LOST = {"subtype": "process_exit", "is_error": True, "rate_limit": "", "tools": {}}


def run(state="running", executor="chat", **kw):
    return dict({"id": "r1", "executor": executor, "executor_id": "c1", "state": state}, **kw)


def view(**kw):
    return dict({"alive": True, "busy": False, "queued": 0, "last_turn": None,
                 "turn_count": 0, "last_output_at": "", "stop_requested": False,
                 "started_utc": "", "watchable": True, "exit_code": None,
                 "stderr": "", "pending_approvals": []}, **kw)


def state_of(r, patch):
    return patch.get("state", r["state"])


class TestSyncRunTable:
    @pytest.mark.parametrize("v, startup, expected", [
        # alive session
        (view(busy=True), False, "running"),
        (view(busy=True), True, "running"),
        (view(queued=2, last_turn=OK), False, "running"),
        (view(), False, "running"),                      # alive, idle, nothing yet
        (view(busy=True, pending_approvals=[{"key": "k"}]), False, "needs-approval"),
        (view(pending_approvals=[{"key": "k"}]), True, "needs-approval"),
        (view(last_turn=OK, turn_count=1), False, "done"),
        (view(last_turn=ERR, turn_count=1), False, "failed"),
        # dead session
        (view(alive=False, last_turn=OK, turn_count=1), False, "done"),
        (view(alive=False, last_turn=ERR, turn_count=1), False, "failed"),
        (view(alive=False), False, "scheduled_retry"),   # no turn ended: process lost, one retry (3a-5)
        (view(alive=False), True, "interrupted"),
        (view(alive=False, busy=True, last_turn=OK), False, "scheduled_retry"),
        (view(alive=False, busy=True, last_turn=OK), True, "interrupted"),
        # absent session
        (None, False, "scheduled_retry"),
        (None, True, "interrupted"),
        # a human stopped it
        (view(stop_requested=True, busy=True), False, "interrupted"),
        (view(stop_requested=True, alive=False), False, "interrupted"),
    ])
    def test_state_for_each_row(self, v, startup, expected):
        r = run()
        assert state_of(r, run_sync.sync_run(r, v, NOW, startup=startup)) == expected

    def test_needs_approval_run_goes_back_to_running_when_answered(self):
        r = run("needs-approval")
        assert run_sync.sync_run(r, view(busy=True), NOW) == {"state": "running"}

    def test_unchanged_state_is_an_empty_patch(self):
        assert run_sync.sync_run(run(), view(busy=True), NOW) == {}

    def test_terminal_patches_carry_ended_and_last_output(self):
        v = view(last_turn=OK, last_output_at="2026-10-01T11:59:00Z")
        patch = run_sync.sync_run(run(), v, NOW)
        assert patch["state"] == "done"
        assert patch["ended"] == NOW
        assert patch["last_output_at"] == "2026-10-01T11:59:00Z"

    def test_stop_and_restart_reasons_are_recorded(self):
        stopped = run_sync.sync_run(run(), view(stop_requested=True), NOW)
        assert (stopped["state"], stopped["end_reason"]) == ("interrupted", "stopped")
        swept = run_sync.sync_run(run(), None, NOW, startup=True)
        assert (swept["state"], swept["end_reason"]) == ("interrupted", "server_restart")
        assert swept["ended"] == NOW

    def test_default_seam_is_fail_closed_unclassified(self):
        patch = run_sync.sync_run(run(), view(last_turn=ERR), NOW)
        assert patch["state"] == "failed" and patch["failure_class"] == "unclassified"
        assert patch["ended"] == NOW and patch["failure_detail"]


class TestStartupSweep:
    def test_live_kept_dead_and_absent_interrupted_with_ended(self, repo):
        live = runs.create(repo, executor="chat", executor_id="live", state="running")
        dead = runs.create(repo, executor="chat", executor_id="dead", state="running")
        gone = runs.create(repo, executor="chat", executor_id="gone", state="running")
        registry = {
            "live": _FakeSession(view(busy=True)),
            "dead": _FakeSession(view(alive=False)),
        }
        out = run_sync.sweep_startup(repo, registry, _NoApprovals(), NOW)
        assert runs.get(repo, live["id"])["state"] == "running"
        for rec in (dead, gone):
            got = runs.get(repo, rec["id"])
            assert got["state"] == "interrupted" and got["ended"] == NOW
        assert set(out) == {dead["id"], gone["id"]}

    def test_only_chat_runs_in_active_states_are_visited(self, repo):
        job = runs.create(repo, executor="job", executor_id="j", state="running")
        done = runs.create(repo, executor="chat", executor_id="d", state="done")
        run_sync.sweep_startup(repo, {}, _NoApprovals(), NOW)
        assert runs.get(repo, job["id"])["state"] == "running"
        assert runs.get(repo, done["id"])["state"] == "done"


class TestTerminal:
    @pytest.mark.parametrize("state", sorted(runs.TERMINAL))
    def test_terminal_run_never_changed_even_after_another_turn(self, state):
        r = run(state)
        later = view(busy=True, last_turn=ERR, turn_count=5)
        assert run_sync.sync_run(r, later, NOW) == {}
        assert run_sync.sync_run(r, None, NOW, startup=True) == {}
        assert run_sync.sync_run(r, view(stop_requested=True), NOW) == {}


class TestRing:
    def test_overflowed_ring_still_yields_state_from_last_turn(self, tmp_path):
        sess = agent_session.LiveSession("s1", _Backend(), str(tmp_path), Stream("s1"))
        sess._handle_line('{"type": "result", "subtype": "success", "is_error": false,'
                          ' "result": "ok", "num_turns": 1}')
        for _ in range(RING_MAX + 1):
            sess._handle_line("noise")
        assert sess.stream.head >= RING_MAX + 1
        r = run()
        patch = run_sync.sync_run(r, run_sync.session_view(sess, []), NOW)
        assert patch["state"] == "done"


class TestStop:
    def test_stop_requested_beats_scheduled_retry(self):
        r = run("scheduled_retry")
        patch = run_sync.sync_run(r, view(stop_requested=True, alive=False), NOW)
        assert patch["state"] == "interrupted" and patch["end_reason"] == "stopped"

    def test_scheduled_retry_otherwise_untouched(self):
        r = run("scheduled_retry")
        assert run_sync.sync_run(r, view(last_turn=ERR), NOW) == {}


class TestRestart:
    def test_scheduled_retry_with_absent_session_is_untouched_at_startup(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="c", state="scheduled_retry")
        assert run_sync.sync_run(rec, None, NOW, startup=True) == {}
        assert run_sync.sweep_startup(repo, {}, _NoApprovals(), NOW) == {}
        assert runs.get(repo, rec["id"])["state"] == "scheduled_retry"


class TestSeam:
    def test_failure_rows_call_decide_failure_with_turn_exit_and_stderr(self):
        calls = []

        def decide(r, **kw):
            calls.append(kw)
            return {"state": "failed", "failure_class": "quota", "failure_detail": "x"}

        err = view(last_turn=ERR, exit_code=1, stderr="boom")
        patch = run_sync.sync_run(run(), err, NOW, decide_failure=decide)
        assert patch["failure_class"] == "quota" and patch["ended"] == NOW
        assert calls == [{"kind": "turn_error", "turn_end": ERR, "exit_code": 1,
                          "stderr": "boom", "now": NOW}]

        calls.clear()
        run_sync.sync_run(run(), view(last_turn=LOST, alive=False, exit_code=137),
                          NOW, decide_failure=decide)
        run_sync.sync_run(run(), None, NOW, decide_failure=decide)
        assert [c["kind"] for c in calls] == ["process_lost", "process_lost"]
        assert calls[0]["exit_code"] == 137 and calls[1]["turn_end"] is None

    def test_success_and_startup_rows_never_call_the_seam(self):
        def boom(*a, **k):
            raise AssertionError("seam called")

        run_sync.sync_run(run(), view(last_turn=OK), NOW, decide_failure=boom)
        run_sync.sync_run(run(), None, NOW, startup=True, decide_failure=boom)
        run_sync.sync_run(run(), view(stop_requested=True), NOW, decide_failure=boom)


def _claude_run(**kw):
    return run(**dict({"backend": "claude", "created": "2026-10-01T11:00:00Z",
                       "attempt": 1, "attempts": []}, **kw))


def _turn(result="", **kw):
    return dict(dict(ERR, result=result, error="", errors=[], api_error_status=None,
                     stop_reason=""), **kw)


class TestProcessLost:
    def test_killed_externally_while_running_gives_process_lost_and_one_scheduled_retry(self):
        r = _claude_run()
        gone = view(alive=False, busy=True, exit_code=137)
        patch = run_sync.sync_run(r, gone, NOW)
        assert patch["state"] == "scheduled_retry"
        assert patch["failure_class"] == "process_lost"
        assert patch["retry_due"] == "2026-10-01T12:00:10Z"
        assert "ended" not in patch and "liveness" not in patch
        assert len(patch["attempts"]) == 1
        # The retry runs (attempt 2) and the process is lost again: no second retry.
        r.update(patch, state="running", attempt=2)
        again = run_sync.sync_run(r, gone, "2026-10-01T12:05:00Z")
        assert again["state"] == "failed" and again["end_reason"] == "retry_exhausted"
        assert again["ended"] == "2026-10-01T12:05:00Z"
        assert again["liveness"]["state"] == "failed"

    def test_same_run_absent_at_startup_is_interrupted_without_retry(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="gone", backend="claude",
                          state="running")
        out = run_sync.sweep_startup(repo, {}, _NoApprovals(), NOW)
        assert out[rec["id"]]["state"] == "interrupted"
        assert "retry_due" not in out[rec["id"]]
        assert runs.get(repo, rec["id"])["state"] == "interrupted"


class TestDefaultPolicy:
    def test_claude_auth_failure_is_classified_and_final(self):
        v = view(last_turn=_turn("Failed to authenticate: OAuth session expired"))
        patch = run_sync.sync_run(_claude_run(), v, NOW)
        assert patch["state"] == "failed" and patch["failure_class"] == "auth_required"
        assert patch["end_reason"] == "auth_required" and patch["ended"] == NOW

    def test_claude_overload_is_retried_and_reads_session_rate_limit(self):
        v = view(last_turn=_turn("overloaded", api_error_status=529))
        patch = run_sync.sync_run(_claude_run(), v, NOW)
        assert patch["state"] == "scheduled_retry"
        assert patch["failure_class"] == "transient_upstream"
        assert patch["retry_due"] == "2026-10-01T12:00:30Z"

    def test_claude_quota_uses_the_notice_reset(self):
        reset = int(datetime(2026, 10, 1, 15, 0, tzinfo=timezone.utc).timestamp())
        v = view(last_turn=_turn("You've hit your limit", rate_limit="rejected", resets_at=reset))
        patch = run_sync.sync_run(_claude_run(), v, NOW)
        assert patch["state"] == "scheduled_retry" and patch["failure_class"] == "quota"
        assert patch["retry_due"] == "2026-10-01T15:01:00Z"

    @pytest.mark.parametrize("backend", ["cursor-agent", "openrouter", ""])
    def test_non_claude_backend_is_never_classified_from_text(self, backend):
        v = view(last_turn=_turn("Failed to authenticate", api_error_status=429))
        patch = run_sync.sync_run(_claude_run(backend=backend), v, NOW)
        assert patch["state"] == "failed" and patch["failure_class"] == "unclassified"
        assert "retry_due" not in patch

    def test_non_claude_backend_process_lost_is_still_retried(self):
        r = _claude_run(backend="cursor-agent")
        patch = run_sync.sync_run(r, view(alive=False, busy=True), NOW)
        assert patch["state"] == "scheduled_retry" and patch["failure_class"] == "process_lost"

    def test_unclassified_failure_is_never_retried(self):
        patch = run_sync.sync_run(_claude_run(), view(last_turn=_turn("odd")), NOW)
        assert patch["state"] == "failed" and patch["failure_class"] == "unclassified"
        assert patch["liveness"] == {"state": "failed", "reason": patch["failure_detail"][:200]}

    def test_bad_clock_fails_closed(self):
        patch = run_sync.sync_run(_claude_run(), view(last_turn=_turn("overloaded",
                                  api_error_status=529)), "not-a-time")
        assert patch["state"] == "failed" and patch["failure_class"] == "unclassified"


class TestScope:
    @pytest.mark.parametrize("executor", ["job", "cursor"])
    def test_non_chat_executor_untouched(self, executor):
        r = run(executor=executor)
        assert run_sync.sync_run(r, None, NOW) == {}
        assert run_sync.sync_run(r, view(last_turn=ERR), NOW) == {}


class TestApiSession:
    def test_api_session_is_reconciled_but_marked_unwatchable(self, tmp_path):
        api = _Backend(transport="openai_api", is_api=True)
        sess = agent_session.LiveSession("s2", api, str(tmp_path), Stream("s2"))
        v = run_sync.session_view(sess, [])
        assert v["watchable"] is False and v["transport"] == "openai_api"
        assert run_sync.sync_run(run(), view(watchable=False, last_turn=ERR), NOW)["state"] == "failed"
        cli = agent_session.LiveSession("s3", _Backend(), str(tmp_path), Stream("s3"))
        assert run_sync.session_view(cli, [])["watchable"] is True


class TestSessionView:
    def test_view_comes_from_attributes_and_stop_flag(self, tmp_path):
        sess = agent_session.LiveSession("s1", _Backend(), str(tmp_path), Stream("s1"))
        sess._handle_line('{"type": "result", "subtype": "success", "is_error": false,'
                          ' "result": "ok", "num_turns": 1}')
        sess._stopping = True
        v = run_sync.session_view(sess, [{"key": "k"}])
        assert v["stop_requested"] is True and v["turn_count"] == 1
        assert v["last_turn"]["subtype"] == "success"
        assert v["pending_approvals"] == [{"key": "k"}]
        assert v["queued"] == 0 and v["alive"] is False and v["busy"] is False
        assert v["last_output_at"]

    def test_last_turn_carries_failure_evidence_for_the_classifier(self, tmp_path):
        sess = agent_session.LiveSession("s1", _Backend(), str(tmp_path), Stream("s1"))
        sess._handle_line('{"type": "result", "subtype": "error_during_execution",'
                          ' "is_error": true, "result": "boom", "errors": ["e1"],'
                          ' "api_error_status": 429, "stop_reason": "x", "num_turns": 1}')
        last = run_sync.session_view(sess, [])["last_turn"]
        assert (last["result"], last["errors"], last["api_error_status"]) == ("boom", ["e1"], 429)
        assert last["stop_reason"] == "x" and last["error"] == "" and last["resets_at"] == 0


class _Backend:
    id = "alpha"
    label = "Alpha"
    default_mode = "default"
    resumable = True
    command = "alpha-cli"

    def __init__(self, transport="stream_json", is_api=False):
        self.transport = transport
        self.is_api = is_api


class _FakeSession:
    """What `session_view` reads from a registry entry, built from a view dict."""

    def __init__(self, v):
        self.backend = _Backend()
        self.stop_requested = v["stop_requested"]
        self._v = v

    def snapshot(self):
        keys = ("alive", "busy", "last_turn", "turn_count", "last_output_at",
                "started_utc", "exit_code")
        snap = {k: self._v[k] for k in keys}
        snap["queued"] = [{}] * self._v["queued"]
        snap["transport"] = self.backend.transport
        return snap


class _NoApprovals:
    def pending_for(self, chat):
        return []
