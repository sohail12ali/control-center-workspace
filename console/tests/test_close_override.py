"""T-021 FR-10: close-override moves despite blocks, and only with a real reason."""

import os
import shutil

import pytest

from conftest import TICKETS_BOARD, _write
from server import audit, mcp, tickets, trackers, verbs
from server import verb_handlers
from server.paths import find_repo_root

T = "T-001"


def make(repo, stage="in-progress", tid=T, kind="tickets"):
    tickets.create(repo, tid, "A ticket", kind=kind)
    if stage != "open":
        tickets.move(repo, tid, stage)
    return tid


def wire(repo):
    shutil.copyfile(os.path.join(find_repo_root(), "console", "config", "verbs.toml"),
                    os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()


def overrides(repo):
    return [r for r in audit.read(repo, limit=50) if r["action"] == "ticket.close.override"]


def comments(repo, tid=T):
    return trackers.list_items(repo, tid, "comments")


class TestCloseOverride:
    def test_empty_and_9_char_reason_refused_no_override_audit_row(self, repo):
        make(repo)
        for reason in ("", "123456789"):
            out = verb_handlers.close_override(repo, ticket=T, reason=reason)
            assert out["ok"] is False
            assert tickets.load(repo, T)["stage"] == "in-progress"
        assert overrides(repo) == []

    def test_valid_reason_on_blocked_fixture_done_one_audit_row_with_reason_and_codes_one_comment(self, repo):
        make(repo)
        out = verb_handlers.close_override(repo, ticket=T, reason="human accepts the gap")
        assert out["ok"] is True and out["stage"] == "done"
        assert tickets.load(repo, T)["stage"] == "done"
        got = overrides(repo)
        assert len(got) == 1
        assert got[0]["detail"]["reason"] == "human accepts the gap"
        assert "no_verification" in got[0]["detail"]["blocks"]
        notes = comments(repo)
        assert len(notes) == 1 and notes[0]["author"] == "close-override"
        assert "human accepts the gap" in notes[0]["text"]

    def test_without_confirm_raises_verberror(self, repo):
        make(repo)
        wire(repo)
        with pytest.raises(verbs.VerbError):
            verbs.run(repo, "close-override", ticket=T, args={"reason": "human accepts the gap"})
        assert tickets.load(repo, T)["stage"] == "in-progress"
        assert overrides(repo) == []
        verbs._cache.clear()

    def test_listed_on_cli_and_mcp(self, repo):
        wire(repo)
        row = next(v for v in verbs.list_verbs(repo) if v["id"] == "close-override")
        assert row["needs_ticket"] and row["needs_confirm"]
        tools = {t["name"]: t for t in mcp.tool_list(repo)}
        schema = tools["close-override"]["inputSchema"]
        assert "confirm" in schema["properties"] and "confirm" in schema["required"]
        assert "reason" in schema["properties"]
        verbs._cache.clear()

    def test_already_done_and_investigations_refused(self, repo):
        make(repo, stage="done")
        done = verb_handlers.close_override(repo, ticket=T, reason="human accepts the gap")
        assert done["ok"] is False and "terminal" in done["error"]
        _write(os.path.join(repo, "console/config/boards/investigations.toml"),
               TICKETS_BOARD.replace('kind    = "tickets"', 'kind    = "investigations"')
               .replace('id = "done"', 'id = "resolved"'))
        from server import boards
        boards._board_cache.clear()
        tickets.create(repo, "INV-1", "dossier", kind="investigations")
        inv = verb_handlers.close_override(repo, ticket="INV-1", reason="human accepts the gap")
        assert inv["ok"] is False and "tickets only" in inv["error"]
        assert overrides(repo) == []

    def test_no_blocks_says_no_override_needed(self, repo):
        make(repo)
        _write(os.path.join(repo, "console", "x.py"), "a\n")
        d = tickets.dir_for(repo, T)
        _write(os.path.join(d, "T-001-verification.md"),
               "# V\n\n| # | Criterion | Status | Evidence |\n|---|---|---|---|\n"
               "| 1 | a | PASS | `console/x.py:1` |\n")
        _write(os.path.join(d, "T-001-plan.md"), "# P\n\n### [x] T-001-01 — done\n")
        out = verb_handlers.close_override(repo, ticket=T, reason="human accepts the gap")
        assert out["ok"] is False and out["error"] == "no override needed"
        assert tickets.load(repo, T)["stage"] == "in-progress"
        assert overrides(repo) == []

    def test_override_action_is_registered(self):
        assert "ticket.close.override" in audit.ACTIONS
