"""T-020 FR-7: output caps for agent children.

2b-1: a per-line cap on the reader loops (`procs.iter_capped_lines`) and O(1)
buffer accounting in `agents._reader_thread`. Streams here are in-memory fakes;
nothing is spawned. The cap counts decoded characters, because the pipes are
text mode (CR-37).
"""

import io
import time

import pytest

from server import agent_session, agents, boards, procs, run_config
from server.agent_events import Stream

MIB = 1024 * 1024


class _RecordingStream(io.StringIO):
    """Records the size asked of every `readline`, to prove no single read
    pulls more than cap (+1) characters into memory."""

    def __init__(self, text):
        super().__init__(text)
        self.sizes = []

    def readline(self, size=-1):
        self.sizes.append(size)
        return super().readline(size)


class TestLineCap:
    def test_three_mib_line_becomes_one_truncated_event_and_next_line_parses(self):
        cap = 1 * MIB
        stream = _RecordingStream("x" * (3 * MIB) + "\n" + '{"ok": 1}\n')
        lines = list(procs.iter_capped_lines(stream, cap))
        assert len(lines) == 2
        assert lines[0].startswith("x" * 100) and lines[0].rstrip().endswith(procs.LINE_TRUNCATED)
        assert len(lines[0]) <= cap + len(procs.LINE_TRUNCATED) + 1
        assert lines[1] == '{"ok": 1}\n'

    def test_per_line_memory_bounded_by_cap_plus_marker(self):
        cap = 1000
        stream = _RecordingStream("y" * 10_000 + "\n" + "short\n")
        lines = list(procs.iter_capped_lines(stream, cap))
        assert max(len(ln) for ln in lines) <= cap + len(procs.LINE_TRUNCATED) + 1
        assert stream.sizes and all(0 < n <= cap + 1 for n in stream.sizes)
        assert lines[-1] == "short\n"

    def test_exact_cap_line_is_not_truncated(self):
        cap = 50
        stream = io.StringIO("z" * cap + "\n" + "z" * (cap + 1) + "\n")
        a, b = procs.iter_capped_lines(stream, cap)
        assert a == "z" * cap + "\n"
        assert b.rstrip().endswith(procs.LINE_TRUNCATED)

    def test_overlong_last_line_without_newline_and_empty_stream(self):
        assert list(procs.iter_capped_lines(io.StringIO(""), 10)) == []
        out = list(procs.iter_capped_lines(io.StringIO("q" * 25), 10))
        assert len(out) == 1 and out[0].rstrip().endswith(procs.LINE_TRUNCATED)

    def test_reader_loop_publishes_one_truncated_event_then_parses_next(
            self, repo, tmp_path):
        with open(repo + "/console/config/console.toml", "a", encoding="utf-8") as fh:
            fh.write("\n[runs]\nmax_line_bytes = 200\n")
        boards._console_cache.clear()
        run_config.reset_warnings()

        class _Backend:
            id = "alpha"
            label = "Alpha"
            transport = "resume"
            default_mode = "default"
            resumable = True

        class _Proc:
            stdout = io.StringIO("w" * 5000 + "\n" + "plain text\n")

            def wait(self, timeout=None):
                return 0

        sess = agent_session.TurnSession("s1", _Backend(), str(tmp_path), Stream("s1"),
                                         repo_root=repo)
        seen = []
        sess._handle_line = seen.append
        sess._read_turn(_Proc())
        assert len(seen) == 2
        assert seen[0].endswith(procs.LINE_TRUNCATED) and len(seen[0]) <= 200 + 40
        assert seen[1] == "plain text"


class _FakeProc:
    returncode = 0

    def __init__(self, text):
        self.stdout = io.StringIO(text)

    def wait(self, timeout=None):
        return 0


def _job():
    import threading
    return {"backend": "b", "prompt": "p", "cwd": "", "status": "running",
            "exit_code": None, "started_at": 0.0, "finished_at": None,
            "buffer": [], "truncated": False, "lock": threading.Lock()}


class TestAgentsReader:
    @pytest.fixture(autouse=True)
    def _clean(self):
        yield
        agents._JOBS.pop("jcap", None)

    def test_ten_thousand_short_lines_under_one_second(self, repo):
        agents._JOBS["jcap"] = _job()
        proc = _FakeProc("line of output\n" * 10_000)
        t0 = time.monotonic()
        agents._reader_thread("jcap", proc, repo)
        assert time.monotonic() - t0 < 1.0
        job = agents._JOBS["jcap"]
        assert len(job["buffer"]) == 10_000 and job["truncated"] is False
        assert job["status"] == "done"

    def test_truncated_flag_set_past_200k_chars(self, repo):
        agents._JOBS["jcap"] = _job()
        proc = _FakeProc(("x" * 99 + "\n") * 3000)  # 300 000 chars
        agents._reader_thread("jcap", proc, repo)
        job = agents._JOBS["jcap"]
        assert job["truncated"] is True
        assert len(job["buffer"]) <= 3000
        assert len(job["buffer"]) >= 1000 - 1


# -- 2b-2: per-turn output cap (FR-7 AC2, BR-9) --------------------------------

from types import SimpleNamespace

from server import agent_manager, runs


class _TurnBackend:
    id = "alpha"
    label = "Alpha"
    transport = "resume"
    default_mode = "default"
    resumable = True


def _cap_session(repo, tmp_path, cap=4096, **kw):
    with open(repo + "/console/config/console.toml", "a", encoding="utf-8") as fh:
        fh.write("\n[runs]\nmax_turn_output_bytes = %d\n" % cap)
    boards._console_cache.clear()
    run_config.reset_warnings()
    sess = agent_session.TurnSession("s1", _TurnBackend(), str(tmp_path), Stream("s1"),
                                     repo_root=repo, **kw)
    sess._deliver = lambda text: None  # the turn "starts" without a process
    sess.events = []
    sess.stream.publish = sess.events.append
    sess.kills = []
    sess.kill_process = lambda grace=5.0: sess.kills.append(grace)
    return sess


def _feed(sess, n_chars, line=100):
    for _ in range(n_chars // line):
        sess._handle_line("a" * (line - 1))  # the reader strips the newline


def _cap_notices(sess):
    return [e for e in sess.events if e.get("type") == "notice" and e.get("kind") == "output_cap"]


class TestTurnCap:
    def test_breach_publishes_one_notice_and_one_kill(self, repo, tmp_path):
        sess = _cap_session(repo, tmp_path)
        sess.send("go")
        _feed(sess, 6000)
        assert len(_cap_notices(sess)) == 1 and len(sess.kills) == 1

    def test_counter_resets_at_turn_start_two_turns_no_breach(self, repo, tmp_path):
        sess = _cap_session(repo, tmp_path)
        sess.send("one")
        _feed(sess, 3000)
        sess._busy = False  # turn one ended
        sess.send("two")
        _feed(sess, 3000)
        assert _cap_notices(sess) == [] and sess.kills == []

    def test_queue_drain_also_resets_the_counter(self, repo, tmp_path):
        sess = _cap_session(repo, tmp_path)
        sess.send("one")
        _feed(sess, 3000)
        sess._queue.append({"id": "q1", "text": "next"})
        sess._drain()
        _feed(sess, 3000)
        assert sess.kills == []

    def test_run_is_terminal_before_kill_is_called(self, repo, tmp_path):
        order = []
        sess = _cap_session(repo, tmp_path,
                            on_limit=lambda s, cls, detail: order.append(("limit", cls)))
        sess.kill_process = lambda grace=5.0: order.append(("kill",))
        sess.send("go")
        _feed(sess, 6000)
        assert order == [("limit", "output_cap"), ("kill",)]

    def test_chat_without_run_is_still_killed_without_error(self, repo, tmp_path):
        sess = _cap_session(repo, tmp_path, on_limit=agent_manager._make_on_limit(repo))
        sess.send("go")
        _feed(sess, 6000)
        assert len(sess.kills) == 1

    def test_second_breach_after_kill_is_ignored(self, repo, tmp_path):
        calls = []
        sess = _cap_session(repo, tmp_path,
                            on_limit=lambda s, cls, detail: calls.append(cls))
        sess.send("go")
        _feed(sess, 6000)
        _feed(sess, 6000)
        assert calls == ["output_cap"] and len(sess.kills) == 1
        assert len(_cap_notices(sess)) == 1

    def test_a_failing_callback_does_not_stop_the_kill(self, repo, tmp_path):
        def boom(*a):
            raise RuntimeError("callback bug")

        sess = _cap_session(repo, tmp_path, on_limit=boom)
        sess.send("go")
        _feed(sess, 6000)
        assert len(sess.kills) == 1


class TestOnLimitHook:
    def test_active_chat_run_is_written_failed_with_output_cap(self, repo):
        run = runs.create(repo, ticket="T-1", role="work", executor="chat",
                          executor_id="s1", state="running")
        agent_manager._make_on_limit(repo)(SimpleNamespace(id="s1"), "output_cap",
                                           "turn output over 4096")
        rec = runs.get(repo, run["id"])
        assert (rec["state"], rec["failure_class"], rec["end_reason"]) == (
            "failed", "output_cap", "output_cap")
        assert rec["ended"] and "4096" in rec["failure_detail"]

    def test_cap_failure_posts_one_escalation_comment_and_one_audit_row(self, repo):
        from server import audit, tickets, trackers
        tickets.create(repo, "T-001", "A ticket")
        run = runs.create(repo, ticket="T-001", role="work", executor="chat",
                          executor_id="s1", state="running")
        hook = agent_manager._make_on_limit(repo)
        hook(SimpleNamespace(id="s1"), "output_cap", "turn output over 4096")
        hook(SimpleNamespace(id="s1"), "output_cap", "turn output over 4096")  # a second breach
        notes = [c for c in trackers.list_items(repo, "T-001", "comments")
                 if c.get("author") == "run-watchdog"]
        assert len(notes) == 1 and notes[0]["text"].startswith("[run %s]" % run["id"])
        assert "too much output" in notes[0]["text"]
        rows = audit.read(repo, action="run.output_cap")
        assert len(rows) == 1 and rows[0]["target"] == run["id"]

    def test_run_already_terminal_is_left_alone(self, repo):
        run = runs.create(repo, ticket="T-1", role="work", executor="chat",
                          executor_id="s1", state="done")
        agent_manager._make_on_limit(repo)(SimpleNamespace(id="s1"), "output_cap", "x")
        assert runs.get(repo, run["id"])["state"] == "done"

    def test_create_and_resume_supply_on_limit(self, repo, monkeypatch):
        seen = {}

        class _Sess:
            id = "sx"

            def __init__(self, **kw):
                seen.update(kw)

            def start(self):
                pass

            def snapshot(self):
                return {}

        backend = SimpleNamespace(installed=True, transport="resume", gated_tools=[],
                                  supports_system_append_flag=True)
        monkeypatch.setattr(agent_manager.agent_backends, "get", lambda r, b: backend)
        monkeypatch.setattr(agent_manager.agent_session, "build",
                            lambda sid, be, cwd, **kw: _Sess(**kw))
        agent_manager.create(repo, "alpha", "", open=False)
        try:
            assert callable(seen["on_limit"]) and seen["repo_root"] == repo
        finally:
            with agent_manager._lock:
                agent_manager._sessions.clear()
