"""T-020 FR-8: a per-turn process that printed its result but did not exit is
tree-killed after `[runs].linger_grace_secs`.

Fakes only: the "process" is an object whose stdout blocks on a queue until the
fake `kill_tree` (or the test) ends it. Grace is 0.2 s through a tmp
console.toml; nothing here sleeps over a second.
"""

import json
import queue
import subprocess
import threading
import time


import pytest

from server import agent_session, agents, boards, procs, run_config
from server.agent_events import Stream

RESULT = json.dumps({"type": "result", "subtype": "success", "result": "ok"})


class _Stdout:
    """Blocks in `readline` until a line or EOF is pushed."""

    def __init__(self):
        self.q = queue.Queue()

    def push(self, line):
        self.q.put(line + chr(10))

    def eof(self):
        self.q.put("")

    def readline(self, size=-1):
        return self.q.get(timeout=5)


class _Proc:
    def __init__(self, pid=1):
        self.pid = pid
        self.returncode = None
        self.stdout = _Stdout()

    def poll(self):
        return self.returncode

    def exit(self, code=0):
        self.returncode = code
        self.stdout.eof()

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.returncode


class _Backend:
    id = "alpha"
    label = "Alpha"
    transport = "resume"
    default_mode = "default"
    resumable = True


@pytest.fixture
def kills(monkeypatch):
    """Fake `kill_tree`: records the process and ends it like a real kill."""
    seen = []

    def fake(proc, grace=5.0):
        seen.append(proc)
        proc.exit(-9)

    monkeypatch.setattr(procs, "kill_tree", fake)
    return seen


@pytest.fixture
def cfg(repo):
    with open(repo + "/console/config/console.toml", "a", encoding="utf-8") as fh:
        fh.write(chr(10) + "[runs]" + chr(10) + "linger_grace_secs = 0.1" + chr(10))
    boards._console_cache.clear()
    run_config.reset_warnings()
    return repo


def _session(repo, tmp_path, cls=agent_session.TurnSession):
    sess = cls("s1", _Backend(), str(tmp_path), Stream("s1"), repo_root=repo)
    sess.events = []
    real = sess.stream.publish

    def publish(ev):
        sess.events.append(ev)
        return real(ev)

    sess.stream.publish = publish
    return sess


def _run_reader(target, *args):
    t = threading.Thread(target=target, args=args, daemon=True)
    t.start()
    return t


def _until(pred, timeout=1.5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.02)
    return pred()


def _kinds(sess):
    return [e.get("kind") for e in sess.events if e.get("type") == "notice"]


class TestLinger:
    def test_result_then_sleep_killed_within_grace_plus_one_second(
            self, cfg, tmp_path, kills):
        sess = _session(cfg, tmp_path)
        proc = _Proc()
        t0 = time.monotonic()
        reader = _run_reader(sess._read_turn, proc)
        proc.stdout.push(RESULT)
        assert _until(lambda: kills)  # grace 0.2 s + 1 s allowance
        assert time.monotonic() - t0 < 1.2
        reader.join(2)
        assert kills == [proc] and "lingering_killed" in _kinds(sess)
        assert not reader.is_alive() and sess.busy is False

    def test_exit_inside_grace_not_killed_no_notice(self, cfg, tmp_path, kills):
        sess = _session(cfg, tmp_path)
        proc = _Proc()
        reader = _run_reader(sess._read_turn, proc)
        proc.stdout.push(RESULT)
        proc.exit(0)
        reader.join(2)
        time.sleep(0.3)  # three graces (0.1 s)
        assert kills == [] and "lingering_killed" not in _kinds(sess)

    def test_live_session_alive_after_result_never_killed(self, cfg, tmp_path, kills):
        sess = _session(cfg, tmp_path, agent_session.LiveSession)
        proc = _Proc()
        sess.proc = proc
        reader = _run_reader(sess._read)
        proc.stdout.push(RESULT)
        time.sleep(0.3)  # three graces
        assert kills == [] and "lingering_killed" not in _kinds(sess)
        proc.exit(0)
        reader.join(2)

    @pytest.mark.parametrize("queued", [False, True])
    def test_busy_false_and_queue_drains_when_process_lingers(
            self, cfg, tmp_path, kills, queued):
        sess = _session(cfg, tmp_path)
        delivered = []
        sess._deliver = delivered.append
        sess._busy = True
        if queued:
            sess._queue.append({"id": "q1", "text": "next"})
        proc = _Proc()
        reader = _run_reader(sess._read_turn, proc)
        proc.stdout.push(RESULT)
        assert _until(lambda: kills)
        reader.join(2)
        assert _until(lambda: sess._queue == [])
        if queued:
            assert _until(lambda: delivered == ["next"])
        else:
            assert _until(lambda: sess.busy is False)

    def test_kill_targets_the_old_process_not_the_next_turns(self, cfg, tmp_path, kills):
        sess = _session(cfg, tmp_path)
        old, new = _Proc(pid=1), _Proc(pid=2)
        reader = _run_reader(sess._read_turn, old)
        old.stdout.push(RESULT)
        time.sleep(0.05)
        sess.proc = sess._turn_proc = new  # the next turn has already started
        assert _until(lambda: kills)
        reader.join(2)
        assert kills == [old]

    def test_overlapping_readers_do_not_clobber_each_other(self, cfg, tmp_path, kills):
        sess = _session(cfg, tmp_path)
        a, b = _Proc(pid=1), _Proc(pid=2)
        reader_a = _run_reader(sess._read_turn, a)
        time.sleep(0.05)
        reader_b = _run_reader(sess._read_turn, b)
        b.stdout.push(RESULT)
        b.exit(0)
        reader_b.join(2)
        a.exit(1)  # A never produced a result
        reader_a.join(2)
        ends = sorted(e["subtype"] for e in sess.events if e.get("type") == "turn.end")
        assert ends == ["process_exit", "success"]
        assert "_observe" not in vars(sess)  # nothing left swapped on the instance
        assert kills == []

    def test_agents_launch_result_then_linger_killed_and_status_finalised(
            self, cfg, kills):
        job = {"backend": "b", "prompt": "p", "cwd": "", "status": "running",
               "exit_code": None, "started_at": 0.0, "finished_at": None,
               "buffer": [], "truncated": False, "lock": threading.Lock()}
        agents._JOBS["jlinger"] = job
        proc = _Proc()
        try:
            reader = _run_reader(agents._reader_thread, "jlinger", proc, cfg)
            proc.stdout.push("some output")
            proc.stdout.push(RESULT)
            assert _until(lambda: kills)
            reader.join(2)
            assert not reader.is_alive() and kills == [proc]
            assert job["status"] == "done" and job["lingering_killed"] is True
            assert job["finished_at"] is not None
        finally:
            agents._JOBS.pop("jlinger", None)

    def test_agents_launch_exit_inside_grace_is_not_killed(self, cfg, kills):
        job = {"backend": "b", "prompt": "p", "cwd": "", "status": "running",
               "exit_code": None, "started_at": 0.0, "finished_at": None,
               "buffer": [], "truncated": False, "lock": threading.Lock()}
        agents._JOBS["jlinger2"] = job
        proc = _Proc()
        try:
            reader = _run_reader(agents._reader_thread, "jlinger2", proc, cfg)
            proc.stdout.push(RESULT)
            proc.exit(0)
            reader.join(2)
            time.sleep(0.3)
            assert kills == [] and "lingering_killed" not in job
            assert job["status"] == "done"
        finally:
            agents._JOBS.pop("jlinger2", None)
