"""Template check, the secret commit gate, and the typed clean.

A ticket file is workspace content: the template report names it, and a
fork is allowed to commit it. A secret path fails the gate. Clean applies
only when the body says reset.
"""

import json
import os
import shutil
import subprocess
from types import SimpleNamespace

import pytest

import kanban
from server import httpd, reset, verbs, workspace_check
from server.features import workspace_feature
from server.paths import find_repo_root


def _write(path, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def _git(repo, *args):
    proc = subprocess.run(
        ["git", *args], cwd=repo,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    return proc


def _routes(repo):
    routes = {}

    class Ctx:
        repo_root = repo

        def get(self, pattern, fn, name):
            routes[("GET", name)] = fn

        def post(self, pattern, fn, name):
            routes[("POST", name)] = fn

    workspace_feature.apply(Ctx())
    return routes


def _req(repo, body):
    return httpd.Request("POST", "/api/workspace/clean", {}, body, repo)


class TestTemplate:
    def test_lists_a_ticket_dir_and_not_the_template(self, repo):
        artifacts = os.path.join(repo, "knowledge-center", "artifacts")
        _write(os.path.join(artifacts, "_template", "requirements.md"))
        _write(os.path.join(artifacts, "CC-T001", "ticket.toml"))
        _write(os.path.join(repo, "knowledge-center", "artifact-map.md"), "stale content")
        paths = {row["path"] for row in workspace_check.instance_rows(repo)}
        assert "knowledge-center/artifacts/CC-T001" in paths
        assert "knowledge-center/artifact-map.md" in paths
        assert not any("_template" in path for path in paths)

    def test_template_alone_is_a_blank_checkout(self, repo):
        artifacts = os.path.join(repo, "knowledge-center", "artifacts")
        _write(os.path.join(artifacts, "_template", "requirements.md"))
        _write(os.path.join(artifacts, "_shared", "_shared-todos.toml"), reset.SHARED_TODOS_TOML)
        _write(os.path.join(repo, "knowledge-center", "artifact-map.md"), reset.ARTIFACT_MAP_HEADER)
        report = workspace_check.report(repo)
        assert report["instance"] == []
        assert report["blank"] is True
        assert report["hook"]["active"] is False


class TestSecrets:
    def test_machine_files_are_secrets_and_a_ticket_is_not(self):
        assert workspace_check.is_secret_path(".env")
        assert workspace_check.is_secret_path(".claude/settings.local.json")
        assert workspace_check.is_secret_path("console/config/notify-local.toml")
        assert workspace_check.is_secret_path("console/.cache/audit/2026-10.jsonl")
        assert workspace_check.is_secret_path("id_rsa")
        assert not workspace_check.is_secret_path("knowledge-center/artifacts/T-1/ticket.toml")
        assert not workspace_check.is_secret_path("knowledge-center/logs/2026-10/2026-10-04.sam.md")

    def test_staged_env_fails_and_a_staged_ticket_does_not(self, repo):
        _git(repo, "init")
        _write(os.path.join(repo, ".env"), "OPENAI_API_KEY=secret\n")
        _write(os.path.join(repo, "knowledge-center", "artifacts", "T-1", "ticket.toml"), "id = \"T-1\"\n")
        _git(repo, "add", "-f", ".env")
        _git(repo, "add", "--", os.path.join("knowledge-center", "artifacts", "T-1", "ticket.toml"))
        staged = {row["path"] for row in workspace_check.staged_secrets(repo)}
        assert ".env" in staged
        assert not any(path.endswith("ticket.toml") for path in staged)
        assert workspace_check.secret_report(repo, staged_only=True)["ok"] is False

    def test_a_committed_secret_fails_the_tracked_check_only(self, repo):
        _git(repo, "init")
        _write(os.path.join(repo, ".env"), "TOKEN=secret\n")
        _git(repo, "add", "-f", ".env")
        _git(repo, "-c", "user.email=t@example.com", "-c", "user.name=Test",
             "commit", "--no-verify", "-m", "add env")
        assert workspace_check.staged_secrets(repo) == []
        tracked = workspace_check.tracked_secrets(repo)
        assert tracked == [{"path": ".env", "where": "tracked"}]
        assert workspace_check.secret_report(repo, staged_only=False)["ok"] is False

    def test_cli_staged_allows_a_ticket_and_refuses_an_env(self, repo, capsys):
        _git(repo, "init")
        _write(os.path.join(repo, "knowledge-center", "artifacts", "T-1", "ticket.toml"), "id = \"T-1\"\n")
        _git(repo, "add", "--", os.path.join("knowledge-center", "artifacts", "T-1", "ticket.toml"))
        kanban.cmd_workspace_check(SimpleNamespace(staged=True, secrets=False, json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True
        assert payload["secrets"] == []

        _write(os.path.join(repo, ".env"), "TOKEN=secret\n")
        _git(repo, "add", "-f", ".env")
        with pytest.raises(SystemExit) as exc:
            kanban.cmd_workspace_check(SimpleNamespace(staged=True, secrets=False, json=True), repo)
        assert exc.value.code == 1
        refused = json.loads(capsys.readouterr().out)
        assert any(row["path"] == ".env" for row in refused["secrets"])


class TestClean:
    def test_without_the_word_reset_nothing_is_deleted(self, repo):
        ticket = os.path.join(repo, "knowledge-center", "artifacts", "CC-T001", "ticket.toml")
        template = os.path.join(repo, "knowledge-center", "artifacts", "_template", "requirements.md")
        _write(ticket)
        _write(template)
        clean = _routes(repo)[("POST", "workspace.clean")]
        with pytest.raises(ValueError, match="type reset"):
            clean(_req(repo, {}))
        with pytest.raises(ValueError, match="type reset"):
            clean(_req(repo, {"confirm": "Reset"}))
        assert os.path.isfile(ticket)
        assert os.path.isfile(template)

    def test_reset_removes_the_ticket_and_keeps_the_template(self, repo):
        ticket_dir = os.path.join(repo, "knowledge-center", "artifacts", "CC-T001")
        template = os.path.join(repo, "knowledge-center", "artifacts", "_template", "requirements.md")
        _write(os.path.join(ticket_dir, "ticket.toml"))
        _write(template)
        out = _routes(repo)[("POST", "workspace.clean")](_req(repo, {"confirm": "reset"}))
        assert out["applied"] is True
        assert not os.path.isdir(ticket_dir)
        assert os.path.isfile(template)
        assert out["report"]["blank"] is True


class TestVerb:
    def test_secret_check_verb_allows_a_checkout_with_no_secrets(self, repo):
        shutil.copyfile(
            os.path.join(find_repo_root(), "console", "config", "verbs.toml"),
            os.path.join(repo, "console", "config", "verbs.toml"),
        )
        _git(repo, "init")
        _write(os.path.join(repo, "knowledge-center", "artifacts", "T-1", "ticket.toml"), "id = \"T-1\"\n")
        _git(repo, "add", "--", os.path.join("knowledge-center", "artifacts", "T-1", "ticket.toml"))
        out = verbs.run(repo, "secret-check")
        assert out["ok"] is True
        assert out["secrets"] == []
