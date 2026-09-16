"""T-016 Run store and launch-role fail-closed."""

import pytest

from server import runs, tickets, verbs
from server.paths import find_repo_root
import os
import shutil


class TestRunStore:
    def test_create_list_get(self, repo):
        rec = runs.create(repo, ticket="T-001", role="work", executor="chat",
                          executor_id="abc", backend="claude")
        assert rec["state"] == "running"
        assert rec["executor"] == "chat"
        got = runs.get(repo, rec["id"])
        assert got["executor_id"] == "abc"
        listed = runs.list_runs(repo, ticket="T-001")
        assert len(listed) == 1

    def test_set_state_interrupted(self, repo):
        rec = runs.create(repo, executor="chat", executor_id="x")
        out = runs.set_state(repo, rec["id"], "interrupted")
        assert out["state"] == "interrupted"
        assert runs.get(repo, rec["id"])["state"] == "interrupted"

    def test_bad_executor_refused(self, repo):
        with pytest.raises(ValueError):
            runs.create(repo, executor="sidecar")

    def test_ticket_filter(self, repo):
        runs.create(repo, ticket="T-001", executor="chat", executor_id="a")
        runs.create(repo, ticket="T-002", executor="job", executor_id="b")
        assert len(runs.list_runs(repo, ticket="T-001")) == 1


def _install_shipped_verbs(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    dest = os.path.join(repo, "console", "config", "verbs.toml")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copyfile(src, dest)
    verbs._cache.clear()


@pytest.fixture
def wired(repo):
    _install_shipped_verbs(repo)
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


class TestLaunchRole:
    def test_unknown_role(self, wired):
        out = verbs.run(wired, "launch-role", ticket="T-001", confirm=True,
                        args={"role": "intern"})
        assert out["ok"] is False
        assert "analyst" in out["error"]

    def test_missing_cursor_agent_does_not_use_claude(self, wired):
        out = verbs.run(wired, "launch-role", ticket="T-001", confirm=True,
                        args={"role": "analyst"})
        assert out["ok"] is False
        assert "fallen through" in out["error"]
        assert runs.list_runs(wired) == []

    def test_run_list_empty(self, wired):
        out = verbs.run(wired, "run-list", ticket="T-001")
        assert out["count"] == 0


class TestDelegateWrap:
    def test_successful_delegate_writes_a_run(self, wired, monkeypatch):
        from server import verb_handlers

        class FakeBackend:
            gated_tools = ()
            transport = "openai_api"
            id = "work-bot"

        captured = {}

        def fake_create(repo_root, backend_id, task, **kw):
            captured["backend"] = backend_id
            captured["task"] = task
            return {"id": "chat-xyz", "model": "m"}

        monkeypatch.setattr(verb_handlers.agent_backends, "registry",
                            lambda root: {"work-bot": FakeBackend()})
        monkeypatch.setattr(verb_handlers.assistant_config,
                            "resolve_work_backend",
                            lambda *a, **k: "work-bot")
        monkeypatch.setattr(verb_handlers.agent_backends, "get",
                            lambda root, bid: FakeBackend())
        monkeypatch.setattr(verb_handlers.agent_manager, "server_port",
                            lambda: 8790)
        monkeypatch.setattr(verb_handlers.agent_manager, "create", fake_create)

        out = verb_handlers.delegate(wired, ticket="T-001", task="do the thing")
        assert out["ok"] is True
        assert out["run"]
        rec = runs.get(wired, out["run"])
        assert rec["executor_id"] == "chat-xyz"
        assert rec["role"] == "work"
        assert rec["executor"] == "chat"


class TestLaunchRoleSuccess:
    def test_creates_cursor_agent_run(self, wired, monkeypatch):
        from server import verb_handlers

        class FakeBackend:
            installed = True
            unavailable_reason = ""

        captured = {}

        def fake_create(repo_root, backend_id, task, **kw):
            captured["backend"] = backend_id
            captured["persona"] = kw.get("persona")
            return {"id": "chat-role"}

        monkeypatch.setattr(verb_handlers.agent_backends, "get",
                            lambda root, bid: FakeBackend())
        monkeypatch.setattr(verb_handlers.agent_manager, "server_port",
                            lambda: 8790)
        monkeypatch.setattr(verb_handlers.agent_manager, "create", fake_create)

        out = verb_handlers.launch_role(wired, ticket="T-001", role="analyst")
        assert out["ok"] is True
        assert captured["backend"] == "cursor-agent"
        assert captured["persona"] == "analyst"
        rec = runs.get(wired, out["run"])
        assert rec["role"] == "analyst"
        assert rec["backend"] == "cursor-agent"
