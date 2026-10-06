"""Setup wizard writes. The checklist stays read-only; these cover the
write path: allowlisted .env edits, the four stores, and a response that
never contains a key value."""

import json
import os

from server import audit, boards, dotenv, httpd, onboarding, onboarding_setup, setup_editor
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry


SECRET = "sk-test-onboarding-secret"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _app(repo):
    real = find_repo_root()
    src = os.path.join(real, "console", "config", "plugins.toml")
    dst = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)
    boards._console_cache.clear()
    config = boards.load_console_config(repo)
    _ctx, router = plugin_registry.build(repo, config)
    return router


def _call(repo, router, method, path, body=None):
    handler, args = router.resolve(method, path)
    assert handler is not None, "no route for %s %s" % (method, path)
    req = httpd.Request(method, path, {}, body, repo,
                        client_addr="127.0.0.1", user_agent="pytest")
    return handler(req, *args)


class TestSetKeys:
    def test_rewrites_only_the_allowlisted_line(self, repo, monkeypatch):
        # delenv records the previous value and restores it on teardown,
        # including the assignment set_keys makes into os.environ below.
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        path = os.path.join(repo, ".env")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# keep me\nOPENAI_API_KEY=old # stay\nUNRELATED=leave\n# tail\n")
        result = dotenv.set_keys(repo, {"OPENAI_API_KEY": "new-value"})
        text = _read(path)
        assert "# keep me" in text
        assert "# tail" in text
        assert "UNRELATED=leave" in text
        assert "OPENAI_API_KEY=new-value # stay" in text
        assert "old" not in text
        assert result == {"written": ["OPENAI_API_KEY"], "applied": ["OPENAI_API_KEY"]}
        assert os.environ["OPENAI_API_KEY"] == "new-value"

    def test_refuses_a_name_outside_the_allowlist(self, repo):
        path = os.path.join(repo, ".env")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("OPENAI_API_KEY=keep\n")
        try:
            dotenv.set_keys(repo, {"TELEGRAM_BOT_TOKEN": SECRET})
        except ValueError as exc:
            assert SECRET not in str(exc)
            assert "TELEGRAM_BOT_TOKEN" in str(exc)
        else:
            raise AssertionError("expected ValueError")
        assert _read(path) == "OPENAI_API_KEY=keep\n"
        assert not os.path.isfile(path + ".tmp")

    def test_a_shell_value_is_not_replaced(self, repo, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "from-shell")
        result = dotenv.set_keys(repo, {"OPENAI_API_KEY": "from-file"})
        assert result["written"] == ["OPENAI_API_KEY"]
        assert result["applied"] == []
        assert os.environ["OPENAI_API_KEY"] == "from-shell"
        assert "from-file" in _read(os.path.join(repo, ".env"))


class TestApply:
    def test_writes_the_four_stores_once(self, repo, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("LMSTUDIO_API_KEY", raising=False)

        fresh = onboarding_setup.snapshot(repo)
        assert fresh["should_open"] is True
        assert SECRET not in json.dumps(fresh)

        onboarding_setup.apply(repo, {
            "step": "workspace", "name": "Irshad Example", "title": "Noble Desk",
        })
        author = _read(os.path.join(repo, "knowledge-center", "logs", "author.local"))
        assert author == "Irshad Example\nirshad-example\n"
        title = json.loads(_read(os.path.join(repo, "console", ".cache", "workspace.json")))
        assert title["title"] == "Noble Desk"
        project = [s for s in onboarding.steps(repo) if s["id"] == "project"][0]
        assert project["status"] == "ok"
        assert project["extra"]["title"] == "Noble Desk"
        # Named, so the wizard no longer covers the board on its own.
        assert onboarding_setup.snapshot(repo)["should_open"] is False

        onboarding_setup.apply(repo, {
            "step": "environment",
            "enabled": {"alpha": True},
            "keys": {"OPENAI_API_KEY": SECRET, "OPENROUTER_API_KEY": ""},
        })
        stored = json.loads(_read(
            os.path.join(repo, "console", ".cache", "agents", "providers.json")))
        assert stored["enabled"]["alpha"] is True
        assert SECRET in _read(os.path.join(repo, ".env"))
        snap = onboarding_setup.snapshot(repo)
        blob = json.dumps(snap)
        assert SECRET not in blob
        assert snap["keys"]["OPENAI_API_KEY"] == "set"
        assert snap["keys"]["OPENROUTER_API_KEY"] == "missing"

        onboarding_setup.apply(repo, {"step": "files", "editors": ["cursor"]})
        onboarding_setup.apply(repo, {"step": "files", "editors": ["cursor"]})
        agents = _read(os.path.join(repo, "AGENTS.md"))
        assert agents.count("console:agents-snippet:start") == 1
        mcp = json.loads(_read(os.path.join(repo, ".cursor", "mcp.json")))
        assert list(mcp["mcpServers"]) == ["console"]

        onboarding_setup.apply(repo, {
            "step": "models",
            "backend": "", "model": "", "work_backend": "", "work_model": "",
        })
        settings = json.loads(_read(
            os.path.join(repo, "console", ".cache", "assistant", "settings.json")))
        assert settings["backend"] == ""
        assert settings["model"] == ""
        assert settings["work_backend"] == ""
        assert settings["work_model"] == ""

        done = onboarding_setup.complete(repo)
        assert done["completed_at"]
        assert done["should_open"] is False
        assert SECRET not in json.dumps(done)

    def test_http_response_and_audit_omit_the_secret(self, repo, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        router = _app(repo)
        out = _call(repo, router, "POST", "/api/onboarding/setup", {
            "step": "environment",
            "keys": {"OPENAI_API_KEY": SECRET},
        })
        assert SECRET not in json.dumps(out)
        assert out["keys"]["OPENAI_API_KEY"] == "set"
        folder = audit.audit_dir(repo)
        logged = ""
        for name in os.listdir(folder):
            logged += _read(os.path.join(folder, name))
        assert SECRET not in logged
        assert "OPENAI_API_KEY" in logged

        onboarding_setup.apply(repo, {
            "step": "workspace", "name": "Ada", "title": "Desk",
        })
        cfg = _call(repo, router, "GET", "/api/config")
        assert cfg["title"] == "Desk"
        assert SECRET not in json.dumps(cfg)


class TestModelIds:
    def test_shortlist_dicts_become_id_strings(self):
        ids = onboarding_setup._model_ids(
            [{"id": "cached-one"}],
            [{"id": "opus", "label": "Opus (alias)", "hint": ""}, "cached-one", ""],
        )
        assert ids == ["cached-one", "opus"]
        assert all(isinstance(mid, str) for mid in ids)


class TestEditorStatus:
    def test_reports_a_wired_editor_without_writing(self, repo):
        before = setup_editor.editor_status(repo)
        assert [row["wired"] for row in before] == [False, False, False]
        setup_editor.setup_editor(repo, "vscode")
        after = {row["id"]: row["wired"] for row in setup_editor.editor_status(repo)}
        assert after == {"cursor": False, "claude": False, "vscode": True}
