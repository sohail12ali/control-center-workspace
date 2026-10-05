"""T-024 FR-1: `procs.clean_env(repo_root)` hands every agent child the main repo
as `CONSOLE_REPO_ROOT`, and both session types spawn with it (AC-1e).
"""

import os
import threading

import pytest

from server import agent_manager, agent_session, boards, procs, run_config

# Real git repo + worktree fixture (AC-1e needs a ticketed worktree chat).
from test_worktree_anchor import _same, gitrepo  # noqa: F401


def _set_runs(repo, line):
    path = os.path.join(repo, "console", "config", "console.toml")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n[runs]\n" + line + "\n")
    boards._console_cache.clear()


class TestCleanEnvAnchor:
    def test_ac1a_the_main_root_is_set_as_an_absolute_path(self, repo):
        assert procs.clean_env(repo)["CONSOLE_REPO_ROOT"] == os.path.abspath(repo)

    def test_ac1b_without_a_root_nothing_is_added_and_ambient_passes_through(
            self, monkeypatch, repo):
        assert "CONSOLE_REPO_ROOT" not in procs.clean_env(None)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", "/ambient")
        assert procs.clean_env(None)["CONSOLE_REPO_ROOT"] == "/ambient"

    def test_ac1c_a_stale_inherited_value_is_overwritten(self, monkeypatch, repo):
        monkeypatch.setenv("CONSOLE_REPO_ROOT", os.path.join(repo, "stale"))
        assert procs.clean_env(repo)["CONSOLE_REPO_ROOT"] == os.path.abspath(repo)

    def test_ac1d_not_stripped_by_a_custom_env_strip(self, monkeypatch, repo):
        _set_runs(repo, 'env_strip = ["CONSOLE_REPO_ROOT", "CLAUDECODE"]')
        run_config.reset_warnings()
        monkeypatch.setenv("CONSOLE_REPO_ROOT", "/stale")
        assert procs.clean_env(repo)["CONSOLE_REPO_ROOT"] == os.path.abspath(repo)
        run_config.reset_warnings()

    def test_ac1d_not_stripped_by_the_default_env_strip(self, repo):
        assert "CONSOLE_REPO_ROOT" not in run_config.DEFAULT_ENV_STRIP
        assert "CONSOLE_REPO_ROOT" in procs.clean_env(repo)


class _FakeProc:
    pid = 4242
    stdin = None
    stdout = None

    def poll(self):
        return None


class _NoThread:
    def __init__(self, *a, **kw):
        pass

    def start(self):
        pass


class _StubThreading:
    Thread = _NoThread

    def __getattr__(self, name):
        return getattr(threading, name)


def _capture_spawns(monkeypatch):
    """Popen kwargs of every spawn; no process and no reader thread starts.
    Installed AFTER the worktree exists: it patches the shared `subprocess`."""
    calls = []

    def fake(*args, **kwargs):
        calls.append(kwargs)
        return _FakeProc()

    monkeypatch.setattr(agent_session.subprocess, "Popen", fake)
    monkeypatch.setattr(agent_session, "threading", _StubThreading())
    return calls


class _FakeBackend:
    """The minimum `Backend` surface the session classes touch (the fixture
    backends name CLIs that are not on PATH, so they cannot build argv)."""

    id = "fake"
    label = "Fake"
    default_mode = "default"
    resumable = True
    command = "fake-cli"

    def __init__(self, transport):
        self.transport = transport

    def session_argv(self, **kw):
        return ["fake-cli", "-p"]

    def turn_argv(self, prompt, **kw):
        return ["fake-cli", "-p", prompt]


def _worktree_chat(gitrepo, transport):
    cwd, _path, _branch, error = agent_manager._resolve_worktree(gitrepo, "T-024")
    assert error == ""
    assert not _same(cwd, gitrepo)
    return agent_session.build("sid-1", _FakeBackend(transport), cwd, ticket="T-024",
                               repo_root=gitrepo)


class TestSpawnedChildHoldsTheMainRoot:
    def test_ac1e_live_session_start(self, gitrepo, monkeypatch):
        sess = _worktree_chat(gitrepo, "stream_json")
        spawned = _capture_spawns(monkeypatch)
        assert isinstance(sess, agent_session.LiveSession)
        sess.start()
        env = spawned[0]["env"]
        assert _same(spawned[0]["cwd"], sess.cwd)
        assert _same(env["CONSOLE_REPO_ROOT"], gitrepo)
        assert not _same(env["CONSOLE_REPO_ROOT"], sess.cwd)

    def test_ac1e_turn_session_deliver(self, gitrepo, monkeypatch):
        sess = _worktree_chat(gitrepo, "resume")
        spawned = _capture_spawns(monkeypatch)
        assert isinstance(sess, agent_session.TurnSession)
        sess._busy = True
        sess._deliver("hello")
        env = spawned[0]["env"]
        assert _same(spawned[0]["cwd"], sess.cwd)
        assert _same(env["CONSOLE_REPO_ROOT"], gitrepo)
        assert not _same(env["CONSOLE_REPO_ROOT"], sess.cwd)
