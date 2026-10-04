"""No-window spawn hygiene (`server.procs`) — defensive, not a fix for an
observed defect (see `T-003-decision-log.md` § "Cause B scope"). Every named
spawn site is driven with `subprocess.Popen`/`run` monkeypatched, so the
assertion is on the kwargs actually handed to the OS call, not on a live
process. `os.name` is monkeypatched on the `procs` module itself so both the
`nt` and the POSIX branch are provable on one machine.
"""

import os
import shutil
import signal
import subprocess
import threading

import pytest

from server import (agent_session, agent_tools, agents, boards, onboarding, procs,
                    run_config, worktrees)
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


_DENY = ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "CLAUDE_CODE_MESSAGING_TOKEN")


def _assert_tree_spawn(kwargs, os_name):
    """Group flags for `os_name` and an env with every deny-list name stripped,
    auth variables kept."""
    assert not set(_DENY) & set(kwargs["env"])
    assert kwargs["env"]["ANTHROPIC_BASE_URL"] == "http://keep"
    if os_name == "nt":
        assert kwargs["creationflags"] & procs.CREATE_NEW_PROCESS_GROUP
        assert _has_no_window_flag(kwargs)
        assert "start_new_session" not in kwargs
    else:
        assert kwargs["start_new_session"] is True
        assert not _has_no_window_flag(kwargs)


def _poison_env(monkeypatch):
    for n in _DENY:
        monkeypatch.setenv(n, "sentinel")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://keep")


class TestLiveSessionStart:
    @pytest.mark.parametrize("os_name", ["nt", "posix"])
    def test_env_excludes_deny_list_and_group_flags_on_nt_and_posix(
            self, monkeypatch, tmp_path, os_name):
        _poison_env(monkeypatch)
        monkeypatch.setattr(procs.os, "name", os_name)
        calls = _capture_popen(monkeypatch, agent_session)
        agent_session.LiveSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1")).start()
        _assert_tree_spawn(calls[0], os_name)

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
    @pytest.mark.parametrize("os_name", ["nt", "posix"])
    def test_env_and_group_flags(self, monkeypatch, tmp_path, os_name):
        _poison_env(monkeypatch)
        monkeypatch.setattr(procs.os, "name", os_name)
        calls = _capture_popen(monkeypatch, agent_session)
        agent_session.TurnSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1")).send("hi")
        _assert_tree_spawn(calls[0], os_name)

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
    @pytest.mark.parametrize("os_name", ["nt", "posix"])
    def test_env_and_group_flags(self, monkeypatch, repo, os_name):
        _poison_env(monkeypatch)
        monkeypatch.setattr(procs.os, "name", os_name)
        calls = self._launch(monkeypatch, repo)
        _assert_tree_spawn(calls[0], os_name)

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


# -- T-020 2a-1: kill_tree, tree_spawn_kwargs, clean_env (FR-5, FR-6) ----------

_SIGKILL = getattr(signal, "SIGKILL", 9)


class _AliveProc:
    """A child that stays alive until `die_on` calls to `wait` have timed out.
    `die_on=None` means it never dies on its own."""

    def __init__(self, pid=4242, die_on=None):
        self.pid = pid
        self.returncode = None
        self.die_on = die_on
        self.waits = []
        self.terminated = self.killed = 0

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.die_on is not None and len(self.waits) >= self.die_on:
            self.returncode = 0
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.returncode

    def terminate(self):
        self.terminated += 1

    def kill(self):
        self.killed += 1


class TestKillTree:
    def _taskkill(self, monkeypatch):
        calls = []

        def fake(argv, **kw):
            calls.append((argv, kw))
            return _FakeCompleted()

        monkeypatch.setattr(procs.subprocess, "run", fake)
        return calls

    def test_nt_issues_taskkill_T_then_T_F_after_grace_with_no_window_flag(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = self._taskkill(monkeypatch)
        proc = _AliveProc(pid=77, die_on=2)  # survives the grace wait, dies after /F
        procs.kill_tree(proc, grace=0.2)
        assert [c[0] for c in calls] == [["taskkill", "/PID", "77", "/T"],
                                         ["taskkill", "/PID", "77", "/T", "/F"]]
        assert all(_has_no_window_flag(c[1]) for c in calls)
        assert proc.waits[0] == 0.2

    def test_nt_polite_ask_that_works_is_not_forced(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = self._taskkill(monkeypatch)
        procs.kill_tree(_AliveProc(die_on=1), grace=0.2)
        assert len(calls) == 1 and "/F" not in calls[0][0]

    def test_posix_signals_term_then_kill_on_own_group_never_getpgrp(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "posix")
        sent = []
        monkeypatch.setattr(procs.os, "getpgid", lambda pid: pid, raising=False)
        monkeypatch.setattr(procs.os, "getpgrp", lambda: 1, raising=False)
        monkeypatch.setattr(procs.os, "killpg", lambda g, sig: sent.append((g, sig)),
                            raising=False)
        proc = _AliveProc(pid=500, die_on=2)
        procs.kill_tree(proc, grace=0.2)
        assert sent == [(500, signal.SIGTERM), (500, _SIGKILL)]
        assert proc.terminated == 0 and proc.killed == 0

    def test_posix_never_signals_a_group_it_does_not_lead(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "posix")
        sent = []
        monkeypatch.setattr(procs.os, "getpgid", lambda pid: 1, raising=False)  # our group
        monkeypatch.setattr(procs.os, "killpg", lambda g, sig: sent.append((g, sig)),
                            raising=False)
        proc = _AliveProc(pid=500, die_on=2)
        procs.kill_tree(proc, grace=0.2)
        assert sent == []
        assert proc.terminated == 1 and proc.killed == 1

    def test_already_exited_process_is_a_no_op(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        calls = self._taskkill(monkeypatch)
        monkeypatch.setattr(procs.os, "killpg",
                            lambda *a: calls.append(a), raising=False)
        proc = _AliveProc()
        proc.returncode = 0
        procs.kill_tree(proc)
        monkeypatch.setattr(procs.os, "name", "posix")
        procs.kill_tree(proc)
        assert calls == [] and proc.waits == []

    def test_taskkill_missing_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")

        def boom(*a, **kw):
            raise FileNotFoundError("taskkill")

        monkeypatch.setattr(procs.subprocess, "run", boom)
        proc = _AliveProc(die_on=2)
        procs.kill_tree(proc, grace=0.1)  # must not raise; wait() decides
        assert proc.returncode == 0


class TestTreeSpawnKwargs:
    def test_nt_flags(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "nt")
        assert procs.tree_spawn_kwargs() == {
            "creationflags": 0x200 | procs.CREATE_NO_WINDOW}

    def test_posix_new_session(self, monkeypatch):
        monkeypatch.setattr(procs.os, "name", "posix")
        assert procs.tree_spawn_kwargs() == {"start_new_session": True}


@pytest.fixture
def _fresh_warnings():
    run_config.reset_warnings()
    yield
    run_config.reset_warnings()


def _set_runs(repo, line):
    """Append a `[runs]` line to the fixture workspace's console.toml (a tmp
    copy, never the real config) and drop the loader cache."""
    path = os.path.join(repo, "console", "config", "console.toml")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n[runs]\n" + line + "\n")
    boards._console_cache.clear()


class TestCleanEnv:
    def test_deny_list_removed_and_auth_vars_kept(self, monkeypatch, repo, _fresh_warnings):
        for name in run_config.DEFAULT_ENV_STRIP:
            monkeypatch.setenv(name, "sentinel")
        monkeypatch.setenv("ANTHROPIC_BASE_URL", "http://x")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_SCOPES", "a b")
        env = procs.clean_env(repo)
        assert not set(run_config.DEFAULT_ENV_STRIP) & set(env)
        assert env["ANTHROPIC_BASE_URL"] == "http://x"
        assert env["CLAUDE_CODE_OAUTH_SCOPES"] == "a b"
        assert "PATH" in env or "Path" in env

    def test_env_strip_override_from_config(self, monkeypatch, repo, _fresh_warnings):
        _set_runs(repo, 'env_strip = ["MY_SECRET_X"]')
        monkeypatch.setenv("MY_SECRET_X", "1")
        monkeypatch.setenv("CLAUDECODE", "1")
        env = procs.clean_env(repo)
        assert "MY_SECRET_X" not in env and env["CLAUDECODE"] == "1"

    def test_non_list_env_strip_falls_back_with_one_warning(
            self, monkeypatch, repo, capsys, _fresh_warnings):
        _set_runs(repo, 'env_strip = "CLAUDECODE"')
        monkeypatch.setenv("CLAUDECODE", "1")
        capsys.readouterr()
        assert "CLAUDECODE" not in procs.clean_env(repo)
        procs.clean_env(repo)
        warns = [ln for ln in capsys.readouterr().err.splitlines() if "env_strip" in ln]
        assert len(warns) == 1


class TestNoBareKill:
    def test_no_bare_proc_kill_or_terminate_in_session_or_agents(self):
        """FR-5 AC4. `os.kill(pid, sig)` (a signal send, used by the live
        interrupt fallback) is not a process kill and stays."""
        import ast
        import inspect
        for mod in (agent_session, agents):
            tree = ast.parse(inspect.getsource(mod))
            bad = [n.lineno for n in ast.walk(tree)
                   if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                   and n.func.attr in ("kill", "terminate")
                   and not (isinstance(n.func.value, ast.Name) and n.func.value.id == "os")]
            assert bad == [], "%s: bare kill/terminate at lines %s" % (mod.__name__, bad)


class TestKillProcess:
    def test_kill_process_calls_kill_tree_and_leaves_stopping_false(
            self, monkeypatch, tmp_path):
        seen = []
        monkeypatch.setattr(agent_session.procs, "kill_tree",
                            lambda proc, grace=5.0: seen.append((proc, grace)))
        sess = agent_session.TurnSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1"))
        sess.proc = _AliveProc()
        sess.kill_process(grace=1.5)
        assert seen == [(sess.proc, 1.5)]
        assert sess.stop_requested is False

    def test_stop_and_interrupt_use_kill_tree_with_two_second_grace(
            self, monkeypatch, tmp_path):
        seen = []
        monkeypatch.setattr(agent_session.procs, "kill_tree",
                            lambda proc, grace=5.0: seen.append(grace))
        sess = agent_session.TurnSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1"))
        sess._turn_proc = _AliveProc()
        assert sess.interrupt() is True
        sess.stop()
        assert seen == [2.0, 2.0]

    def test_live_stop_force_kills_tree_when_stdin_close_is_ignored(
            self, monkeypatch, tmp_path):
        seen = []
        monkeypatch.setattr(agent_session.procs, "kill_tree",
                            lambda proc, grace=5.0: seen.append(grace))
        sess = agent_session.LiveSession(
            "s1", _FakeBackend(), str(tmp_path), Stream("s1"))
        sess.stop_wait_secs = 0.01
        sess.proc = _AliveProc()
        sess.proc.stdin = None
        sess.stop()
        assert seen == [2.0] and sess.stop_requested is True


class TestStopJob:
    def test_stop_job_uses_kill_tree(self, monkeypatch):
        seen = []
        monkeypatch.setattr(agents.procs, "kill_tree",
                            lambda proc, grace=5.0: seen.append((proc, grace)))
        proc = _AliveProc()
        agents._JOBS["j1"] = {"status": "running", "proc": proc,
                              "lock": threading.Lock()}
        try:
            assert agents.stop_job("", "j1") == {"id": "j1", "status": "stopping"}
        finally:
            agents._JOBS.pop("j1", None)
        assert seen == [(proc, 2.0)]


class TestRepoRootThreading:
    def test_build_passes_repo_root_to_the_session(self, tmp_path):
        sess = agent_session.build("s1", _FakeBackend(), str(tmp_path),
                                   repo_root="R:/ws")
        assert sess.repo_root == "R:/ws"
        assert agent_session.build("s2", _FakeBackend(), str(tmp_path)).repo_root == ""
