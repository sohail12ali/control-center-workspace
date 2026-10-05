"""T-020 FR-14: the pure silence decision of the stall watchdog."""

import os
from datetime import datetime, timedelta, timezone

import pytest

from server import boards, run_config, run_watchdog
from server.run_watchdog import evaluate

NOW = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
CFG = {"stall_suspect_secs": 600, "stall_kill_secs": 1800}


def ago(secs):
    return (NOW - timedelta(seconds=secs)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(**kw):
    return dict({"executor": "chat", "state": "running", "created": ago(99999),
                 "liveness": {"state": "", "reason": ""}}, **kw)


def view(**kw):
    return dict({"watchable": True, "pending_approvals": [], "last_output_at": "",
                 "started_utc": ""}, **kw)


def act(r, v, cfg=CFG, now=NOW):
    return evaluate(r, v, now, cfg)["action"]


class TestEvaluate:
    def test_599_none_601_suspect_700_no_second_notice_1801_kill(self):
        r = run()
        assert act(r, view(last_output_at=ago(599))) == "none"
        assert act(r, view(last_output_at=ago(601))) == "suspect"
        flagged = run(liveness={"state": "suspicious", "reason": "x"})
        assert act(flagged, view(last_output_at=ago(700))) == "none"
        assert act(flagged, view(last_output_at=ago(1801))) == "kill"
        assert act(r, view(last_output_at=ago(1801))) == "kill"

    def test_pending_approval_one_hour_never_suspect_or_kill(self):
        v = view(last_output_at=ago(3600), pending_approvals=[{"key": "k"}])
        assert act(run(), v) == "none"
        assert act(run(state="needs-approval"), view(last_output_at=ago(3600))) == "none"

    def test_clock_restarts_from_the_approval_end(self):
        v = view(last_output_at=ago(3600), clock_floor=ago(30))
        assert act(run(), v) == "none"
        assert act(run(), dict(v, clock_floor=ago(700))) == "suspect"

    def test_output_at_1799_seconds_ago_resets_clock(self):
        flagged = run(liveness={"state": "suspicious", "reason": ""})
        v = view(last_output_at=ago(1799), started_utc=ago(5000))
        assert act(flagged, v) == "none"
        assert act(flagged, view(last_output_at=ago(10), started_utc=ago(5000))) == "none"

    def test_zero_kill_flags_suspicious_only_after_ten_hours(self):
        cfg = {"stall_suspect_secs": 600, "stall_kill_secs": 0}
        v = view(last_output_at=ago(10 * 3600))
        assert act(run(), v, cfg) == "suspect"
        flagged = run(liveness={"state": "suspicious", "reason": ""})
        assert act(flagged, v, cfg) == "none"  # flag-only: never "kill"

    def test_api_session_never_evaluated(self):
        assert act(run(), view(watchable=False, last_output_at=ago(99999))) == "none"
        assert act(run(), None) == "none"

    def test_only_running_chat_runs_have_a_clock(self):
        v = view(last_output_at=ago(99999))
        for state in ("queued", "needs-approval", "scheduled_retry", "done", "failed",
                      "interrupted", "timed_out"):
            assert act(run(state=state), v) == "none"
        assert act(run(executor="job"), v) == "none"

    def test_fallback_chain_uses_utc_started_then_created(self):
        r = run(created=ago(1000))
        # No output yet: the UTC session start wins over the Run's creation.
        assert act(r, view(started_utc=ago(50))) == "none"
        assert act(r, view(started_utc=ago(700))) == "suspect"
        # No session start either: the Run's creation. Local-naive `started` is ignored.
        assert act(r, view(started="2026-10-01 17:00:00")) == "suspect"
        assert act(run(created=ago(40)), view()) == "none"
        # Nothing parseable at all: fail closed.
        assert act(run(created=""), view()) == "none"

    def test_thresholds_from_config_and_inverted_pair_rejected(self, repo, capsys):
        path = os.path.join(repo, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n[runs]\nstall_suspect_secs = 100\nstall_kill_secs = 200\n")
        boards._console_cache.clear()
        run_config.reset_warnings()
        cfg = run_config.runs_cfg(repo)
        assert act(run(), view(last_output_at=ago(150)), cfg) == "suspect"
        assert act(run(), view(last_output_at=ago(250)), cfg) == "kill"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n")
        text = open(path, encoding="utf-8").read().replace("stall_kill_secs = 200",
                                                           "stall_kill_secs = 50")
        open(path, "w", encoding="utf-8").write(text)
        boards._console_cache.clear()
        run_config.reset_warnings()
        bad = run_config.runs_cfg(repo)
        assert (bad["stall_suspect_secs"], bad["stall_kill_secs"]) == (600, 1800)
        assert capsys.readouterr().err.count("stall_kill_secs") == 1
        run_config.reset_warnings()

    def test_module_parse_utc(self):
        assert run_watchdog.parse_utc("2026-10-01T12:00:00Z") == NOW
        assert run_watchdog.parse_utc("") is None and run_watchdog.parse_utc(None) is None


# -- FR-14 rest: the tick, the thread -----------------------------------------

import threading  # noqa: E402
import time  # noqa: E402

from server import agent_manager, audit, run_sync, runs  # noqa: E402


class _Backend:
    is_api = False
    transport = "stream_json"


class _Stream:
    def __init__(self):
        self.events = []

    def publish(self, ev):
        self.events.append(ev)


class FakeSession:
    def __init__(self, sid, silent_secs=0, *, alive=True, busy=True, on_kill=None, api=False):
        self.id = sid
        self.backend = _Backend()
        self.backend.is_api = api
        self.stop_requested = False
        self.stream = _Stream()
        self.kills = []
        self._on_kill = on_kill
        self.alive, self.busy = alive, busy
        self.last_output_at = ago(silent_secs)

    def snapshot(self):
        return {"alive": self.alive, "busy": self.busy, "queued": [], "last_turn": None,
                "turn_count": 0, "last_output_at": self.last_output_at,
                "started_utc": ago(99999), "exit_code": None, "transport": "stream_json",
                "mode": "default"}

    def kill_process(self, grace=5.0):
        self.kills.append(grace)
        if self._on_kill:
            self._on_kill(self)
        self.alive = False


class Approvals:
    def __init__(self):
        self.pending = {}

    def pending_for(self, chat):
        return list(self.pending.get(chat, []))


@pytest.fixture(autouse=True)
def _fresh_state():
    run_watchdog.reset()
    run_config.reset_warnings()
    yield
    run_watchdog.reset()


def mk(repo, chat, **kw):
    return runs.create(repo, executor="chat", executor_id=chat, backend="claude", **kw)


def go(repo, registry, approvals=None, now=NOW, **kw):
    kw.setdefault("startup", False)
    return run_watchdog.tick(repo, now=now, registry=registry,
                             approvals=approvals or Approvals(), **kw)


class TestTick:
    def test_run_is_timed_out_on_disk_when_fake_kill_tree_is_called(self, repo):
        rec = mk(repo, "c1")
        seen = []
        sess = FakeSession("c1", 1801, on_kill=lambda s: seen.append(runs.get(repo, rec["id"])))
        out = go(repo, {"c1": sess})
        assert out["killed"] == 1 and sess.kills == [2.0] and len(seen) == 1
        on_disk = seen[0]
        assert on_disk["state"] == "timed_out" and on_disk["failure_class"] == "stalled"
        assert on_disk["end_reason"] == "stalled" and on_disk["ended"] == ago(0)
        assert [e["kind"] for e in sess.stream.events] == ["stall_kill"]

    def test_following_sync_over_dead_session_returns_empty_patch(self, repo):
        rec = mk(repo, "c1")
        sess = FakeSession("c1", 1801)
        go(repo, {"c1": sess})
        again = runs.get(repo, rec["id"])
        view = run_sync.session_view(sess, [])
        assert view["alive"] is False
        assert run_sync.sync_run(again, view, ago(0)) == {}

    def test_suspect_once_writes_liveness_and_one_notice(self, repo):
        rec = mk(repo, "c1")
        sess = FakeSession("c1", 700)
        assert go(repo, {"c1": sess})["suspicious"] == 1
        assert runs.get(repo, rec["id"])["liveness"]["state"] == "suspicious"
        assert go(repo, {"c1": sess}, now=NOW + timedelta(seconds=30))["suspicious"] == 0
        assert [e["kind"] for e in sess.stream.events] == ["stall_suspect"] and not sess.kills

    def test_zero_kill_config_never_kills(self, repo):
        path = os.path.join(repo, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n[runs]\nstall_kill_secs = 0\n")
        boards._console_cache.clear()
        mk(repo, "c1")
        sess = FakeSession("c1", 10 * 3600)
        out = go(repo, {"c1": sess})
        assert out["suspicious"] == 1 and out["killed"] == 0 and not sess.kills

    def test_chat_without_run_is_not_evaluated(self, repo):
        sess = FakeSession("human", 99999)
        out = go(repo, {"human": sess})
        assert out["killed"] == 0 and out["suspicious"] == 0
        assert not sess.kills and not sess.stream.events

    def test_run_whose_chat_has_no_session_is_skipped(self, repo):
        rec = mk(repo, "gone")
        out = go(repo, {})
        assert out["errors"] == 0 and runs.get(repo, rec["id"])["state"] == "running"

    def test_unwatchable_api_session_is_not_killed(self, repo):
        mk(repo, "c1")
        sess = FakeSession("c1", 99999, api=True)
        assert go(repo, {"c1": sess})["killed"] == 0 and not sess.kills

    def test_pending_approval_pauses_then_clock_restarts_when_it_ends(self, repo):
        rec = mk(repo, "c1")
        sess = FakeSession("c1", 3600)
        approvals = Approvals()
        approvals.pending["c1"] = [{"key": "k"}]
        out = go(repo, {"c1": sess}, approvals)
        assert out["killed"] == 0 and runs.get(repo, rec["id"])["state"] == "needs-approval"
        approvals.pending["c1"] = []
        later = NOW + timedelta(seconds=15)
        out = go(repo, {"c1": sess}, approvals, now=later)
        assert out["killed"] == 0 and not sess.kills  # old output, but the clock restarted
        assert runs.get(repo, rec["id"])["state"] == "running"
        out = go(repo, {"c1": sess}, approvals, now=later + timedelta(seconds=1900))
        assert out["killed"] == 1

    def test_exception_in_run_a_still_evaluates_run_b_errors_is_one(self, repo, monkeypatch):
        mk(repo, "a")
        rec_b = mk(repo, "b")
        real = run_sync.session_view

        def boom(sess, pending):
            if sess.id == "a":
                raise RuntimeError("bad session")
            return real(sess, pending)

        monkeypatch.setattr(run_watchdog.run_sync, "session_view", boom)
        sb = FakeSession("b", 1801)
        out = go(repo, {"a": FakeSession("a", 1801), "b": sb})
        assert out["errors"] == 1 and out["killed"] == 1 and sb.kills
        assert runs.get(repo, rec_b["id"])["state"] == "timed_out"

    def test_two_concurrent_ticks_act_once_loser_busy(self, repo):
        mk(repo, "c1")
        entered, release = threading.Event(), threading.Event()

        def hold(sess):
            entered.set()
            release.wait(2)

        sess = FakeSession("c1", 1801, on_kill=hold)
        results = []
        t = threading.Thread(target=lambda: results.append(go(repo, {"c1": sess})))
        t.start()
        try:
            assert entered.wait(2)
            assert go(repo, {"c1": sess}) == {"busy": True}
        finally:
            release.set()
            t.join(2)
        assert not t.is_alive() and len(sess.kills) == 1 and results[0]["killed"] == 1

    def test_hundred_active_runs_under_100ms(self, repo):
        registry = {}
        for i in range(100):
            mk(repo, "c%d" % i)
            registry["c%d" % i] = FakeSession("c%d" % i, 5)
        # A warm-up tick first: Windows scans a just-written file on its first
        # read (seconds for 100 files), which is the host, not the tick.
        go(repo, registry)
        t0 = time.perf_counter()
        out = go(repo, registry)
        took = time.perf_counter() - t0
        assert out["errors"] == 0 and out["killed"] == 0
        assert took < 0.1, took

    def test_terminal_ids_not_reparsed_on_second_tick(self, repo, monkeypatch):
        for i in range(5):
            r = mk(repo, "t%d" % i)
            runs.update(repo, r["id"], state="done")
        for i in range(2):
            mk(repo, "a%d" % i)
        registry = {"a0": FakeSession("a0", 5), "a1": FakeSession("a1", 5)}
        reads = []
        real = runs._read
        monkeypatch.setattr(runs, "_read", lambda path: reads.append(path) or real(path))
        go(repo, registry)
        assert len(reads) == 7
        reads.clear()
        go(repo, registry)
        assert len(reads) == 2

    def test_tick_never_sweeps_unless_told_to(self, repo):
        rec = mk(repo, "gone")
        out = run_watchdog.tick(repo, now=NOW, registry={}, approvals=Approvals())
        assert out["synced"] == 0 and runs.get(repo, rec["id"])["state"] == "running"

    def test_explicit_startup_tick_sweeps(self, repo):
        rec = mk(repo, "gone")
        out = run_watchdog.tick(repo, now=NOW, registry={}, approvals=Approvals(), startup=True)
        assert out["synced"] == 1
        assert runs.get(repo, rec["id"])["state"] == "interrupted"

    def test_thread_asks_for_startup_sweep_until_a_tick_actually_ran(self, repo, monkeypatch):
        calls = []
        dog = run_watchdog.Watchdog(repo, 0.05)

        def fake_tick(repo_root, **kw):
            calls.append(kw.get("startup"))
            if len(calls) >= 4:
                dog._stop_evt.set()
            return {"busy": True} if len(calls) == 1 else {}

        monkeypatch.setattr(run_watchdog, "tick", fake_tick)
        dog.run()
        assert calls == [True, True, False, False]


class TestListActive:
    def test_skips_terminal_and_remembers_them(self, repo):
        done = mk(repo, "d")
        runs.update(repo, done["id"], state="done")
        live = mk(repo, "l")
        known = set()
        assert [r["id"] for r in runs.list_active(repo, known)] == [live["id"]]
        assert known == {done["id"]}


class TestThread:
    def test_shutdown_all_joins_within_two_seconds(self, repo):
        thread = agent_manager.start_watchdog(repo)
        try:
            assert thread is not None and thread.is_alive()
            t0 = time.monotonic()
            agent_manager.shutdown_all()
            assert time.monotonic() - t0 < 2
            thread.join(2)
            assert not thread.is_alive()
        finally:
            agent_manager.stop_watchdog()
        assert all(t.name != "run-watchdog" for t in threading.enumerate())

    def test_watchdog_enabled_false_starts_no_thread(self, repo):
        path = os.path.join(repo, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n[runs]\nwatchdog_enabled = false\n")
        boards._console_cache.clear()
        assert agent_manager.start_watchdog(repo) is None
        assert all(t.name != "run-watchdog" for t in threading.enumerate())

    def test_start_twice_gives_one_thread_and_stop_is_idempotent(self, repo):
        first = agent_manager.start_watchdog(repo)
        try:
            assert agent_manager.start_watchdog(repo) is first
        finally:
            agent_manager.stop_watchdog()
            agent_manager.stop_watchdog()
        assert not first.is_alive()

    def test_stall_kill_writes_audit_row(self, repo):
        rec = mk(repo, "c1")
        go(repo, {"c1": FakeSession("c1", 1801)})
        rows = audit.read(repo, action="run.stall_kill")
        assert len(rows) == 1 and rows[0]["target"] == rec["id"]
        assert rows[0]["detail"]["silence_secs"] >= 1801


# -- FR-16: retry execution ----------------------------------------------------


class Reg:
    """Registry fake: sessions by id plus the two calls a retry may make. `create`
    exists only so a test can prove it is never reached (T-011 invariant)."""

    def __init__(self, sessions=None, resume_error=None, send_error=None):
        self.sessions = dict(sessions or {})
        self.resume_error, self.send_error = resume_error, send_error
        self.resumed, self.sent, self.created = [], [], []

    def get(self, sid):
        return self.sessions.get(sid)

    def server_port(self):
        return 4321

    def resume(self, repo_root, sid, *, server_port=0):
        self.resumed.append((sid, server_port))
        if self.resume_error:
            raise self.resume_error
        self.sessions[sid] = FakeSession(sid, 0, busy=False)

    def send(self, sid, text, mode="auto"):
        if self.send_error:
            raise self.send_error
        self.sent.append((sid, text))

    def create(self, *a, **kw):
        self.created.append((a, kw))
        raise AssertionError("a retry must never start a new chat")


def scheduled(repo, chat, due_in=-5, **kw):
    rec = mk(repo, chat, **kw)
    due = (NOW + timedelta(seconds=due_in)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return runs.update(repo, rec["id"], state="scheduled_retry", retry_due=due,
                       failure_class="transient_upstream", attempt=1)


class TestRetryExecution:
    def test_live_session_gets_one_send_and_run_is_running_attempt_two(self, repo):
        rec = scheduled(repo, "c1")
        reg = Reg({"c1": FakeSession("c1", 5, busy=False)})
        out = go(repo, reg)
        assert out["retried"] == 1 and out["errors"] == 0
        assert reg.sent == [("c1", run_watchdog.CONTINUATION)] and not reg.resumed
        now = runs.get(repo, rec["id"])
        assert now["state"] == "running" and now["attempt"] == 2
        assert audit.read(repo, action="run.retry")[0]["target"] == rec["id"]
        assert go(repo, reg)["retried"] == 0 and len(reg.sent) == 1

    def test_dead_session_is_resumed_then_sent(self, repo):
        rec = scheduled(repo, "c1")
        reg = Reg()
        assert go(repo, reg)["retried"] == 1
        assert reg.resumed == [("c1", 4321)] and reg.sent == [("c1", run_watchdog.CONTINUATION)]
        assert runs.get(repo, rec["id"])["state"] == "running"

    @pytest.mark.parametrize("exc", [ValueError("no cli session id"), FileNotFoundError("no transcript")])
    def test_dead_session_resume_value_error_fails_resume_refused_and_never_creates(self, repo, exc):
        rec = scheduled(repo, "c1")
        reg = Reg(resume_error=exc)
        out = go(repo, reg)
        now = runs.get(repo, rec["id"])
        assert out["retried"] == 0 and out["errors"] == 0
        assert now["state"] == "failed" and now["end_reason"] == "resume_refused"
        assert now["ended"] == ago(0) and not reg.created and not reg.sent

    @pytest.mark.parametrize("exc", [RuntimeError("session has ended"), OSError("pipe")])
    def test_send_error_fails_retry_failed(self, repo, exc):
        rec = scheduled(repo, "c1")
        reg = Reg({"c1": FakeSession("c1", 5, busy=False)}, send_error=exc)
        go(repo, reg)
        now = runs.get(repo, rec["id"])
        assert now["state"] == "failed" and now["end_reason"] == "retry_failed"
        assert not reg.created

    def test_future_due_untouched_then_retried_after_simulated_restart(self, repo):
        rec = scheduled(repo, "c1", due_in=120)
        reg = Reg({"c1": FakeSession("c1", 5, busy=False)})
        assert go(repo, reg)["retried"] == 0
        assert runs.get(repo, rec["id"])["state"] == "scheduled_retry" and not reg.sent
        run_watchdog.reset()  # a fresh process: nothing in memory, same files
        assert go(repo, reg, now=NOW + timedelta(seconds=121))["retried"] == 1
        assert runs.get(repo, rec["id"])["attempt"] == 2

    def test_stop_request_cancels_pending_retry_run_interrupted(self, repo):
        rec = scheduled(repo, "c1")
        sess = FakeSession("c1", 5, busy=False)
        sess.stop_requested = True
        reg = Reg({"c1": sess})
        go(repo, reg)
        now = runs.get(repo, rec["id"])
        assert now["state"] == "interrupted" and now["end_reason"] == "stopped"
        assert not reg.sent and not reg.resumed

    def test_unreadable_due_time_is_left_alone(self, repo):
        rec = scheduled(repo, "c1")
        runs.update(repo, rec["id"], retry_due="soon")
        reg = Reg({"c1": FakeSession("c1", 5, busy=False)})
        assert go(repo, reg)["retried"] == 0 and not reg.sent


# -- FR-17: escalation comment ---------------------------------------------------

from server import run_failures, tickets, trackers  # noqa: E402


def failed_run(repo, ticket="T-001", **kw):
    rec = mk(repo, "c1", ticket=ticket)
    fields = dict(state="failed", failure_class="auth_required", end_reason="auth_required",
                  failure_detail="not logged in", ended=ago(0))
    fields.update(kw)
    return runs.update(repo, rec["id"], **fields)


def comments(repo, ticket="T-001"):
    return trackers.list_items(repo, ticket, "comments")


@pytest.fixture
def tk(repo):
    tickets.create(repo, "T-001", "A ticket")
    return repo


class TestEscalation:
    def test_action_table_has_row_per_class_plus_resume_refused_and_exhaustion(self):
        for key in run_failures.CLASSES + ("resume_refused", "retry_exhausted", "retry_failed"):
            assert run_watchdog.ACTION_TABLE.get(key), key

    def test_failed_run_one_comment_after_three_syncs(self, tk):
        rec = failed_run(tk)
        assert [run_watchdog.escalate(tk, rec) for _ in range(3)] == [True, False, False]
        items = comments(tk)
        assert len(items) == 1 and items[0]["author"] == "run-watchdog"
        assert items[0]["text"].startswith("[run %s]" % rec["id"])
        assert "auth_required" in items[0]["text"] and "not logged in" in items[0]["text"]
        assert len(audit.read(tk, action="ticket.comment")) == 1

    def test_stall_kill_tick_posts_one_comment_even_over_repeated_ticks(self, tk):
        mk(tk, "c1", ticket="T-001")
        reg = {"c1": FakeSession("c1", 1801)}
        go(tk, reg)
        go(tk, reg, now=NOW + timedelta(seconds=15))
        items = comments(tk)
        assert len(items) == 1 and "stalled" in items[0]["text"]

    def test_failed_end_reached_through_a_retry_start_failure_is_escalated(self, tk):
        scheduled(tk, "c1", ticket="T-001")
        go(tk, Reg(resume_error=ValueError("nothing to resume")))
        items = comments(tk)
        assert len(items) == 1 and "resume_refused" in items[0]["text"]

    def test_done_and_ticketless_runs_post_nothing(self, tk):
        done = mk(tk, "c1", ticket="T-001")
        done = runs.update(tk, done["id"], state="done")
        assert run_watchdog.escalate(tk, done) is False
        loose = failed_run(tk, ticket="")
        assert run_watchdog.escalate(tk, loose) is False
        assert comments(tk) == []

    def test_comment_never_contains_env_values_or_long_raw_result(self, tk, monkeypatch):
        monkeypatch.setenv("MY_SERVICE_TOKEN", "s3cr3t-value-xyz")
        rec = failed_run(tk, failure_detail="boom s3cr3t-value-xyz " + "y" * 450)
        run_watchdog.escalate(tk, rec)
        text = comments(tk)[0]["text"]
        assert "s3cr3t-value-xyz" not in text
        assert "y" * 301 not in text and len(text) < 900

    def test_quota_comment_names_reset_time_when_known(self, tk):
        rec = failed_run(tk, failure_class="quota", end_reason="quota",
                         retry_not_before="2026-10-01T15:00:00Z")
        run_watchdog.escalate(tk, rec)
        assert "2026-10-01T15:00:00Z" in comments(tk)[0]["text"]

    def test_unknown_ticket_is_reported_not_raised(self, repo):
        rec = failed_run(repo, ticket="T-404")
        assert run_watchdog.escalate(repo, rec) is False
