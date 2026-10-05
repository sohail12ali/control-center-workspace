"""T-024 FR-6: what must NOT change when anchoring to the main repo.

A ticketless chat, a non-git repo and a failed worktree creation all have
`cwd == repo_root`; there the new env var, telemetry and notify roots equal what
they were. Prompt, skill and `#file` resolution stay on the session cwd (D5).
AC-6c is `test_codex.py`, run unmodified.
"""

import os
import threading

import pytest

from server import agent_manager, agent_session, prompt_build, telemetry

# Fixtures and helpers shared with the other T-024 tests.
from test_api_session_roots import build_split, split  # noqa: F401
from test_api_session import Provider, api, run, say  # noqa: F401
from test_worktree_anchor import _same, gitrepo  # noqa: F401


class FakeBackend:
    """The `Backend` surface `agent_manager.create` and the session touch."""

    id = "fake"
    label = "Fake"
    transport = "stream_json"
    default_mode = "default"
    resumable = True
    command = "fake-cli"
    installed = True
    credential_reason = ""
    gated_tools = ()
    approval_timeout = 1
    supports_system_append_flag = True

    def __init__(self):
        self.compose_calls = []

    def session_argv(self, **kw):
        return ["fake-cli", "-p"]

    def compose_prompt(self, text, **kw):
        self.compose_calls.append(kw)
        return text


class _FakeProc:
    pid = 4242
    stdin = None

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


class _SubprocessStub:
    """Replaces `agent_session.subprocess` only (not the shared module), so the
    git calls that make a worktree still run for real."""

    def __init__(self, calls):
        self._calls = calls

    def Popen(self, *args, **kwargs):  # noqa: N802
        self._calls.append(kwargs)
        return _FakeProc()

    def __getattr__(self, name):
        import subprocess
        return getattr(subprocess, name)


@pytest.fixture
def chat(monkeypatch):
    """`start(repo, ticket="")` -> (session, backend, popen_kwargs)."""
    backend = FakeBackend()
    spawned = []
    monkeypatch.setattr(agent_manager.agent_backends, "get", lambda root, bid: backend)
    monkeypatch.setattr(agent_session, "subprocess", _SubprocessStub(spawned))
    monkeypatch.setattr(agent_session, "threading", _StubThreading())
    started = []

    def start(repo, ticket=""):
        snap = agent_manager.create(repo, "fake", "", ticket=ticket, open=False)
        started.append(snap["id"])
        return agent_manager.get(snap["id"]), snap

    yield start, backend, spawned
    for sid in started:
        agent_manager._sessions.pop(sid, None)


def _one_turn(sess):
    sess._observe({"type": "turn.end", "cost_usd": 0.1, "input_tokens": 10,
                   "output_tokens": 5, "duration_ms": 100, "num_turns": 1})


class TestUnchangedWhenCwdIsTheRepoRoot:
    def test_ac6a_ticketless_chat_has_one_root_everywhere(self, repo, chat):
        start, _backend, spawned = chat
        sess, snap = start(repo)

        assert _same(sess.cwd, repo) and _same(sess.repo_root, repo)
        assert _same(spawned[0]["cwd"], repo)
        assert _same(spawned[0]["env"]["CONSOLE_REPO_ROOT"], repo)
        _one_turn(sess)
        assert [r["session"] for r in telemetry.read_records(repo)] == [sess.id]

    def test_ac6b_a_failed_worktree_leaves_all_roots_equal(self, repo, chat):
        # `repo` has no `.git`: `_resolve_worktree` falls back with a reason.
        start, _backend, spawned = chat
        sess, snap = start(repo, ticket="T-024")

        assert snap["worktree_error"] and snap["worktree_path"] == ""
        assert _same(sess.cwd, repo) and _same(sess.repo_root, repo)
        assert _same(spawned[0]["cwd"], repo)
        assert _same(spawned[0]["env"]["CONSOLE_REPO_ROOT"], repo)
        _one_turn(sess)
        assert [r["session"] for r in telemetry.read_records(repo)] == [sess.id]
        assert not os.path.exists(os.path.join(repo, ".claude", "worktrees"))


class TestPromptResolutionStaysOnCwd:
    def test_ac6d_send_composes_against_the_session_cwd(self, gitrepo, chat):
        start, backend, spawned = chat
        sess, snap = start(gitrepo, ticket="T-024")
        assert not _same(sess.cwd, gitrepo)  # a real worktree
        assert _same(spawned[0]["env"]["CONSOLE_REPO_ROOT"], gitrepo)
        sess.send = lambda wire, **kw: "queued"

        agent_manager.send(sess.id, "/skill do it")

        assert _same(backend.compose_calls[-1]["repo_root"], sess.cwd)
        assert not _same(backend.compose_calls[-1]["repo_root"], gitrepo)

    def test_ac6d_the_api_system_prompt_is_built_from_the_cwd(self, split, monkeypatch):
        main, wt = split
        roots = []
        real = prompt_build.build

        def spy(root, **kw):
            roots.append(root)
            return real(root, **kw)

        monkeypatch.setattr(prompt_build, "build", spy)
        build_split(main, wt, Provider(say("hi")))

        assert len(roots) == 1 and _same(roots[0], wt)
        assert not _same(roots[0], main)
