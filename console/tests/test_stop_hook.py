"""T-017 FR-10 (Phase 4, slice 4a) — session stop-hook check.

Reminds an agent about a claimed-but-stale ticket (no comment/move recorded
since the claim) at session end; never crashes. Backed by `stop_hook.py` and
exercised via `kanban.py stop-hook check` for one-api (`--json`) coverage.
"""

import json
import os
from types import SimpleNamespace

from server import stop_hook, tickets, trackers
import kanban


def _create(repo, tid="CC-T001", **kw):
    return tickets.create(repo, tid, kw.pop("title", "A ticket"), **kw)


def _write_author_local(repo, name="Sam Agent", slug="sam-agent"):
    path = os.path.join(repo, "knowledge-center", "logs", "author.local")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(name + "\n" + slug + "\n")


def _ns(**kw):
    return SimpleNamespace(**kw)


class TestResolveAgent:
    def test_override_wins(self, repo):
        _write_author_local(repo)
        assert stop_hook.resolve_agent(repo, "override-id") == "override-id"

    def test_falls_back_to_author_local_slug(self, repo):
        _write_author_local(repo, slug="sam-agent")
        assert stop_hook.resolve_agent(repo, "") == "sam-agent"

    def test_no_author_local_is_empty_not_an_error(self, repo):
        assert stop_hook.resolve_agent(repo, "") == ""


class TestStaleClaims:
    def test_no_agent_returns_empty(self, repo):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1")
        assert stop_hook.stale_claims(repo, "") == []

    def test_claim_with_no_update_is_stale(self, repo):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", claimed_at="2026-09-16")
        stale = stop_hook.stale_claims(repo, "agent-1")
        assert [s["id"] for s in stale] == ["CC-T001"]

    def test_claim_then_comment_is_not_stale(self, repo):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", claimed_at="2026-09-16")
        trackers.add(repo, "CC-T001", "comments", "picking this up", author="agent-1")
        assert stop_hook.stale_claims(repo, "agent-1") == []

    def test_claim_then_move_is_not_stale(self, repo, monkeypatch):
        import datetime as real_datetime

        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", claimed_at="2020-01-01")

        class _FrozenDate(real_datetime.date):
            @classmethod
            def today(cls):
                return real_datetime.date(2020, 1, 2)

        monkeypatch.setattr(tickets, "date", _FrozenDate)
        tickets.move(repo, "CC-T001", "in-progress")
        assert stop_hook.stale_claims(repo, "agent-1") == []

    def test_unclaimed_ticket_is_never_reported(self, repo):
        _create(repo)
        assert stop_hook.stale_claims(repo, "agent-1") == []

    def test_a_different_agents_claim_is_not_reported(self, repo):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1")
        assert stop_hook.stale_claims(repo, "agent-2") == []

    def test_never_raises_on_a_broken_repo_root(self, tmp_path):
        assert stop_hook.stale_claims(str(tmp_path / "does-not-exist"), "agent-1") == []


class TestFormatReminder:
    def test_empty_is_empty_string(self):
        assert stop_hook.format_reminder([]) == ""

    def test_names_the_ticket(self):
        text = stop_hook.format_reminder([{"id": "CC-T001", "title": "A ticket", "claimed_at": "2026-09-16"}])
        assert "CC-T001" in text and "A ticket" in text


class TestCliOneApi:
    def test_json_reports_stale_claims(self, repo, capsys):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", claimed_at="2026-09-16")
        kanban.cmd_stop_hook_check(_ns(agent="agent-1", json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["agent"] == "agent-1"
        assert [s["id"] for s in payload["stale"]] == ["CC-T001"]

    def test_plain_mode_prints_a_reminder_line(self, repo, capsys):
        _create(repo)
        tickets.set_claim(repo, "CC-T001", "agent-1", claimed_at="2026-09-16")
        kanban.cmd_stop_hook_check(_ns(agent="agent-1", json=False), repo)
        assert "CC-T001" in capsys.readouterr().out

    def test_plain_mode_prints_nothing_when_clean(self, repo, capsys):
        kanban.cmd_stop_hook_check(_ns(agent="agent-1", json=False), repo)
        assert capsys.readouterr().out == ""

    def test_never_crashes_even_if_stale_claims_raises(self, repo, capsys, monkeypatch):
        def _boom(*a, **kw):
            raise RuntimeError("boom")

        monkeypatch.setattr(stop_hook, "stale_claims", _boom)
        kanban.cmd_stop_hook_check(_ns(agent="agent-1", json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["stale"] == []
        assert "boom" in payload["error"]

    def test_parser_wires_the_subcommand(self):
        parser = kanban.build_parser()
        args = parser.parse_args(["stop-hook", "check", "--agent", "x", "--json"])
        assert args.func is kanban.cmd_stop_hook_check
        assert args.agent == "x" and args.json is True
