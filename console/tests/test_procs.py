"""No-window spawn hygiene (`server.procs`) — defensive, not a fix for an
observed defect (see `T-003-decision-log.md` § "Cause B scope"). Every named
spawn site is driven with `subprocess.Popen`/`run` monkeypatched, so the
assertion is on the kwargs actually handed to the OS call, not on a live
process. `os.name` is monkeypatched on the `procs` module itself so both the
`nt` and the POSIX branch are provable on one machine.
"""

import shutil
import threading

import pytest

from server import agent_session, agent_tools, agents, onboarding, procs, worktrees
from server.agent_events import Stream


def _has_no_window_flag(kwargs):
    return bool(kwargs.get("creationflags", 0) & procs.CREATE_NO_WINDOW)


class _FakeProc:
    def __init__(self, pid=4242, returncode=0):
        self.pid = pid
        self.returncode = returncode

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode


class _FakeCompleted:
    def __init__(self, returncode=0, stdout=""):
        self.returncode = returncode
        self.stdout = stdout


class _NoOpThread:
    """Stands in for `threading.Thread` so a reader thread never actually
    runs — the assertion is on the spawn call, not on stream plumbing."""

    def __init__(self, *a, **kw):
        pass

    def start(self):
        pass


def _capture_popen(monkeypatch, module):
    calls = []

    def fake(*args, **kwargs):
        calls.append(kwargs)
        return _FakeProc()

    monkeypatch.setattr(module.subprocess, "Popen", fake)
    monkeypatch.setattr(module, "threading", _StubThreading())
    return calls


class _StubThreading:
    """Only `Thread` is replaced; every other attribute (`Lock`, `Condition`,
    ...) falls through to the real module, since `BaseSession.__init__` and
    friends still need those to work normally."""

    Thread = _NoOpThread

    def __getattr__(self, name):
        return getattr(threading, name)


def _capture_run(monkeypatch, module):
    calls = []

    def fake(*args, **kwargs):
        calls.append(kwargs)
        return _FakeCompleted()

    monkeypatch.setattr(module.subprocess, "run", fake)
    return calls


class TestProcsModule:
    """The two primitives everything else composes."""

    def test_no_window_flags_ors_in_the_bit_on_nt(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        assert procs.no_window_flags() == procs.CREATE_NO_WINDOW
        assert procs.no_window_flags(0x200) == (0x200 | procs.CREATE_NO_WINDOW)

    def test_no_window_flags_is_a_no_op_on_posix(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "posix")
        assert procs.no_window_flags() == 0
        assert procs.no_window_flags(0x200) == 0x200

    def test_popen_kwargs_on_nt(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        assert procs.popen_kwargs() == {"creationflags": procs.CREATE_NO_WINDOW}

    def test_popen_kwargs_is_empty_on_posix(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "posix")
        assert procs.popen_kwargs() == {}


class _FakeBackend:
    """The minimum `Backend` surface `agent_session` calls."""

    id = "alpha"
    label = "Alpha"
    transport = "stream_json"
    default_mode = "default"
    resumable = True

    def session_argv(self, **kw):
        return ["alpha-cli", "-p"]

    def turn_argv(self, prompt, **kw):
        return ["alpha-cli", "-p", prompt]


class TestLiveSessionStart:
    """`agent_session.py:375` — LiveSession.start, CREATE_NEW_PROCESS_GROUP
    must survive the OR."""

    def _session(self, tmp_path):
        return agent_session.LiveSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1"))

    def test_flag_present_on_nt(self, monkeypatch, tmp_path):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = _capture_popen(monkeypatch, agent_session)
        self._session(tmp_path).start()
        assert calls and _has_no_window_flag(calls[0])

    def test_flag_absent_on_posix(self, monkeypatch, tmp_path):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = _capture_popen(monkeypatch, agent_session)
        self._session(tmp_path).start()
        assert calls and not _has_no_window_flag(calls[0])


class TestTurnSessionDeliver:
    """`agent_session.py:507-512` — TurnSession._deliver."""

    def _session(self, tmp_path):
        return agent_session.TurnSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1"))

    def test_flag_present_on_nt(self, monkeypatch, tmp_path):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = _capture_popen(monkeypatch, agent_session)
        sess = self._session(tmp_path)
        sess.send("hi")
        assert calls and _has_no_window_flag(calls[0])

    def test_flag_absent_on_posix(self, monkeypatch, tmp_path):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = _capture_popen(monkeypatch, agent_session)
        sess = self._session(tmp_path)
        sess.send("hi")
        assert calls and not _has_no_window_flag(calls[0])


class TestAgentsLaunch:
    """`agents.py:209-217` — the one-shot `agents.launch` path."""

    def _launch(self, monkeypatch, repo):
        monkeypatch.setattr(shutil, "which", lambda cmd: "C:\\fake\\" + cmd)
        calls = _capture_popen(monkeypatch, agents)
        agents.launch(repo, "beta", "hello")
        return calls

    def test_flag_present_on_nt(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = self._launch(monkeypatch, repo)
        assert calls and _has_no_window_flag(calls[0])

    def test_flag_absent_on_posix(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = self._launch(monkeypatch, repo)
        assert calls and not _has_no_window_flag(calls[0])


class TestRunCommand:
    """`agent_tools.py:247-249` — `run_command`, `shell=True` kept,
    `stdin=DEVNULL` added."""

    def test_flag_present_on_nt(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = _capture_run(monkeypatch, agent_tools)
        agent_tools.dispatch(repo, "run_command", {"command": "echo hi"})
        assert calls and _has_no_window_flag(calls[0])
        assert calls[0]["shell"] is True
        assert calls[0]["stdin"] is agent_tools.subprocess.DEVNULL

    def test_flag_absent_on_posix(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = _capture_run(monkeypatch, agent_tools)
        agent_tools.dispatch(repo, "run_command", {"command": "echo hi"})
        assert calls and not _has_no_window_flag(calls[0])


class TestOnboardingGitUser:
    """`onboarding.py:70-71` — `_git_user`."""

    def test_flag_present_on_nt(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = _capture_run(monkeypatch, onboarding)
        onboarding._git_user(repo)
        assert calls and _has_no_window_flag(calls[0])

    def test_flag_absent_on_posix(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = _capture_run(monkeypatch, onboarding)
        onboarding._git_user(repo)
        assert calls and not _has_no_window_flag(calls[0])


class TestWorktreesGit:
    """`worktrees.py:57-59` — `_git`."""

    def test_flag_present_on_nt(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = _capture_run(monkeypatch, worktrees)
        worktrees._git(repo, "status")
        assert calls and _has_no_window_flag(calls[0])

    def test_flag_absent_on_posix(self, monkeypatch, repo):
        monkeypatch.setattr(procs.os, "name", "posix")
        calls = _capture_run(monkeypatch, worktrees)
        worktrees._git(repo, "status")
        assert calls and not _has_no_window_flag(calls[0])
