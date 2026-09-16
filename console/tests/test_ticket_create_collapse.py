"""T-017 FR-2/a1 — one ticket-creation path: `kanban.py ticket create` and
`verb run kickoff` both land on `kickoff.create_ticket`, so they produce
identical artifacts for equivalent inputs. The pre-T-017 bare-`tickets.create`
shortcut is no longer reachable through `cmd_ticket_create` (task 1a-5) — it
remains only as `tickets.create`, an internal helper other modules still call
directly (`kickoff.create_ticket` itself, tests, `trackers.ensure_all`).
"""

import json
import os
from types import SimpleNamespace

import pytest

import kanban
from server import kickoff, tickets, audit


def _make_template_dir(repo, names=("summary", "plan")):
    d = os.path.join(repo, "knowledge-center", "artifacts", "_template")
    os.makedirs(d, exist_ok=True)
    for name in names:
        with open(os.path.join(d, "%s.md" % name), "w", encoding="utf-8") as fh:
            fh.write("---\nticket: \"{ID}\"\n---\n\n# {ID}: {TITLE}\n")
    return d


def _make_artifact_map(repo):
    path = os.path.join(repo, "knowledge-center", "artifact-map.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Artifact Map\n\n## Active\n\n## Blocked\n\n"
                 "## Completed\n\n## Archived\n\n---\n")


def _fake_ps_runner():
    def run(argv, **kw):
        out_path = argv[argv.index("-OutputPath") + 1]
        ticket_id = argv[argv.index("-Ticket") + 1]
        title = argv[argv.index("-Title") + 1]
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write("---\nticket: \"%s\"\n---\n\n# %s: %s\n" % (ticket_id, ticket_id, title))

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""
        return Result()
    return run


def _cli_create(repo, monkeypatch, **kw):
    args = SimpleNamespace(id=kw.get("id", "T-002"), title=kw.get("title", "A CLI ticket"),
                           kind=kw.get("kind", "tickets"), owner=kw.get("owner", ""),
                           priority=kw.get("priority", tickets.DEFAULT_PRIORITY),
                           url=kw.get("url", ""))
    monkeypatch.setattr(kickoff, "_powershell_exe", lambda: "fake")
    monkeypatch.setattr("subprocess.run", lambda *a, **kw: _fake_ps_runner()(a[0], **kw))
    kanban.cmd_ticket_create(args, repo)


class TestOnePathTwoEntryPoints:
    def test_cli_create_renders_templates_and_appends_artifact_map_row(
            self, repo, monkeypatch, capsys):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        _cli_create(repo, monkeypatch, id="T-002", title="A CLI ticket")

        result = json.loads(capsys.readouterr().out)
        assert result["id"] == "T-002"
        assert len(result["rendered"]) == 2
        for path in result["rendered"]:
            assert os.path.isfile(path)
        with open(os.path.join(repo, "knowledge-center", "artifact-map.md"),
                  encoding="utf-8") as fh:
            assert "T-002-summary" in fh.read()

    def test_cli_and_kickoff_verb_produce_the_same_shape_for_equivalent_inputs(
            self, repo, monkeypatch, capsys):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        _cli_create(repo, monkeypatch, id="T-002", title="Same shape")
        cli_result = json.loads(capsys.readouterr().out)

        verb_result = kickoff.create_ticket(repo, "Same shape via verb",
                                            runner=_fake_ps_runner())
        assert set(cli_result) == set(verb_result)
        assert len(cli_result["rendered"]) == len(verb_result["rendered"]) == 2

    def test_bare_tickets_create_is_no_longer_the_cli_path(self, repo, monkeypatch, capsys):
        # The regression this guards: cmd_ticket_create must not merely write
        # ticket.toml — it must also render templates and append the
        # artifact-map row, which bare `tickets.create` alone never did.
        _make_template_dir(repo)
        _make_artifact_map(repo)
        _cli_create(repo, monkeypatch, id="T-002", title="Full artifacts")
        folder = os.path.join(repo, "knowledge-center", "artifacts", "T-002")
        rendered_files = [f for f in os.listdir(folder) if f.endswith(".md")]
        assert len(rendered_files) == 2, (
            "cmd_ticket_create must go through kickoff.create_ticket, not "
            "bare tickets.create — rendered templates are missing")


class TestPowerShellUnavailableFromCli:
    def test_a_clean_named_error_not_a_traceback(self, repo, monkeypatch, capsys):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        monkeypatch.setattr(kickoff, "_powershell_exe", lambda: None)
        args = SimpleNamespace(id="T-002", title="No PowerShell here",
                               kind="tickets", owner="", priority="medium", url="")
        # Call the function main() would, directly, to isolate the error path
        # from CLI arg-parsing/repo-root discovery (already covered elsewhere).
        try:
            kanban.cmd_ticket_create(args, repo)
            raised = None
        except kickoff.PowerShellUnavailable as exc:
            raised = exc
        assert raised is not None
        # The ticket.toml step still happened — same partial state kickoff's
        # own test suite documents for the verb path.
        assert tickets.load(repo, "T-002") is not None

    def test_main_reports_it_as_a_clean_die_not_a_traceback(
            self, repo, monkeypatch, capsys):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        monkeypatch.setattr(kickoff, "_powershell_exe", lambda: None)
        monkeypatch.setattr("server.paths.find_repo_root", lambda: repo)
        with pytest.raises(SystemExit):
            kanban.main(["ticket", "create", "T-002", "--title", "x"])
        err = capsys.readouterr().err
        assert err.startswith("error:")
        assert "Traceback" not in err


class TestAuditWiring:
    def test_ticket_creation_appears_in_the_audit_trail(self, repo, monkeypatch, capsys):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        _cli_create(repo, monkeypatch, id="T-002", title="Audited ticket")
        capsys.readouterr()
        rows = audit.read(repo, action="ticket.create")
        assert len(rows) == 1
        assert rows[0]["target"] == "T-002"

    def test_kickoff_verb_path_is_also_audited(self, repo):
        _make_template_dir(repo)
        _make_artifact_map(repo)
        kickoff.create_ticket(repo, "Via verb", runner=_fake_ps_runner())
        rows = audit.read(repo, action="ticket.create")
        assert len(rows) == 1
        assert rows[0]["target"] == "T-001"
