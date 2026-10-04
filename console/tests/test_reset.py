"""Workspace reset — the destructive path, so the cases are about what
survives (_template, _shared, config, docs) as much as what gets wiped."""

import os

from server import reset


def _write(path, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _seed_workspace(repo):
    artifacts = os.path.join(repo, "knowledge-center", "artifacts")
    _write(os.path.join(artifacts, "_template", "requirements.md"))
    _write(os.path.join(artifacts, "_shared", "_shared-todos.toml"), 'ticket = "_shared"\n')
    _write(os.path.join(artifacts, "CC-T001", "ticket.toml"))
    _write(os.path.join(repo, "knowledge-center", "artifact-map.md"), "stale content")
    _write(os.path.join(repo, "knowledge-center", "investigations", "INV-1", "dossier.md"))
    _write(os.path.join(repo, "knowledge-center", "logs", "2026-08", "2026-08-01.sam.md"))
    _write(os.path.join(repo, "knowledge-center", "logs", "author.local"), "sam")
    _write(os.path.join(repo, "knowledge-center", "telemetry", "2026-08.jsonl"))
    _write(os.path.join(repo, "knowledge-center", "docs", "idea.md"), "keep me")
    _write(os.path.join(repo, "console", ".cache", "jobs", "j1.json"))


class TestPlan:
    def test_lists_ticket_dirs_but_not_template_or_shared(self, repo):
        _seed_workspace(repo)
        actions = reset.plan(repo)
        deleted = {p for kind, p in actions if kind == "rmtree"}
        artifacts = os.path.join(repo, "knowledge-center", "artifacts")
        assert os.path.join(artifacts, "CC-T001") in deleted
        assert os.path.join(artifacts, "_template") not in deleted
        assert os.path.join(artifacts, "_shared") not in deleted

    def test_dry_run_touches_nothing(self, repo):
        _seed_workspace(repo)
        reset.plan(repo)
        assert os.path.isdir(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))

    def test_keep_logs_excludes_log_dir(self, repo):
        _seed_workspace(repo)
        default_actions = {p for _, p in reset.plan(repo)}
        kept_actions = {p for _, p in reset.plan(repo, keep_logs=True)}
        log_dir = os.path.join(repo, "knowledge-center", "logs", "2026-08")
        assert log_dir in default_actions
        assert log_dir not in kept_actions

    def test_keep_investigations_excludes_investigations_dir(self, repo):
        _seed_workspace(repo)
        inv_dir = os.path.join(repo, "knowledge-center", "investigations", "INV-1")
        kept_actions = {p for _, p in reset.plan(repo, keep_investigations=True)}
        assert inv_dir not in kept_actions


class TestRun:
    def test_apply_removes_tickets_and_keeps_scaffolding(self, repo):
        _seed_workspace(repo)
        reset.run(repo, apply=True)
        artifacts = os.path.join(repo, "knowledge-center", "artifacts")
        assert not os.path.isdir(os.path.join(artifacts, "CC-T001"))
        assert os.path.isdir(os.path.join(artifacts, "_template"))
        assert os.path.isdir(os.path.join(artifacts, "_shared"))

    def test_apply_resets_artifact_map_and_shared_todos(self, repo):
        _seed_workspace(repo)
        reset.run(repo, apply=True)
        with open(os.path.join(repo, "knowledge-center", "artifact-map.md"), encoding="utf-8") as fh:
            assert "## Active" in fh.read()
        shared = os.path.join(repo, "knowledge-center", "artifacts", "_shared", "_shared-todos.toml")
        with open(shared, encoding="utf-8") as fh:
            assert fh.read() == reset.SHARED_TODOS_TOML

    def test_apply_keeps_author_local_and_docs(self, repo):
        _seed_workspace(repo)
        reset.run(repo, apply=True)
        assert os.path.isfile(os.path.join(repo, "knowledge-center", "logs", "author.local"))
        assert os.path.isfile(os.path.join(repo, "knowledge-center", "docs", "idea.md"))

    def test_apply_clears_cache_and_telemetry(self, repo):
        _seed_workspace(repo)
        reset.run(repo, apply=True)
        assert not os.path.isdir(os.path.join(repo, "console", ".cache", "jobs"))
        assert not os.path.isfile(os.path.join(repo, "knowledge-center", "telemetry", "2026-08.jsonl"))

    def test_apply_returns_the_same_plan_it_executed(self, repo):
        _seed_workspace(repo)
        planned = reset.plan(repo)
        executed = reset.run(repo, apply=True)
        assert executed == planned

    def test_apply_false_is_a_no_op(self, repo):
        _seed_workspace(repo)
        reset.run(repo, apply=False)
        assert os.path.isdir(os.path.join(repo, "knowledge-center", "artifacts", "CC-T001"))
