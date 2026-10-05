"""T-021 FR-7: the `blocked` branch of ticket_gate.guarded_move (prospective, no override)."""

import argparse
import json
import os

import pytest

from conftest import TICKETS_BOARD, _write
from server import audit, tickets, trackers, verb_handlers
from server import ticket_gate

import kanban

T = "T-001"


def make(repo, stage="in-progress", tid=T, owner="sam", kind=None):
    tickets.create(repo, tid, "A ticket", owner=owner)
    tickets.move(repo, tid, stage)
    return tid


def rows(repo, action="ticket.block"):
    return [r for r in audit.read(repo, limit=50) if r["action"] == action]


def cli(repo, stage, tid=T, capsys=None):
    args = argparse.Namespace(id=tid, stage=stage)
    code = 0
    try:
        kanban.cmd_ticket_move(args, repo)
    except SystemExit as exc:
        code = exc.code
    return code, json.loads(capsys.readouterr().out)


class TestBlockedGate:
    def test_no_question_refused_lane_unchanged_one_audit_row(self, repo):
        make(repo)
        out = ticket_gate.guarded_move(repo, T, "blocked")
        assert out["ok"] is False and out["refused"] == "blocked_prose_only"
        assert out["message"] and out["hint"]
        assert tickets.load(repo, T)["stage"] == "in-progress"
        got = rows(repo)
        assert len(got) == 1 and got[0]["outcome"] == "refused: blocked_prose_only"
        assert got[0]["target"] == T

    def test_after_tracker_add_question_move_succeeds(self, repo):
        make(repo)
        trackers.add(repo, T, "questions", "what unblocks this?")
        out = ticket_gate.guarded_move(repo, T, "blocked")
        assert out["stage"] == "blocked"
        assert tickets.load(repo, T)["stage"] == "blocked"
        assert [r["outcome"] for r in rows(repo)] == ["ok"]

    def test_empty_owner_no_claim_is_blocked_no_owner(self, repo):
        make(repo, owner="")
        trackers.add(repo, T, "questions", "Q?")
        out = ticket_gate.guarded_move(repo, T, "blocked")
        assert out["ok"] is False and out["refused"] == "blocked_no_owner"
        assert tickets.load(repo, T)["stage"] == "in-progress"

    def test_critical_bug_is_a_next_action(self, repo):
        make(repo)
        trackers.add(repo, T, "bugs", "crash", severity="critical")
        assert ticket_gate.guarded_move(repo, T, "blocked")["stage"] == "blocked"

    def test_other_moves_and_moves_out_of_blocked_unevaluated(self, repo):
        make(repo, stage="blocked")  # already blocked with nothing: prospective only
        out = ticket_gate.guarded_move(repo, T, "in-progress")
        assert out["stage"] == "in-progress"
        assert ticket_gate.guarded_move(repo, T, "open")["stage"] == "open"
        assert rows(repo) == []

    def test_cli_and_verb_return_same_refusal(self, repo, capsys):
        make(repo)
        via_verb = verb_handlers.ticket_move(repo, ticket=T, stage="blocked")
        code, via_cli = cli(repo, "blocked", capsys=capsys)
        assert code == 1 and via_cli == via_verb
        assert via_verb["refused"] == "blocked_prose_only"

    def test_cli_success_prints_ticket_and_exits_zero(self, repo, capsys):
        make(repo)
        trackers.add(repo, T, "questions", "Q?")
        code, out = cli(repo, "blocked", capsys=capsys)
        assert code == 0 and out["stage"] == "blocked"

    def test_other_kinds_never_refused(self, repo):
        _write(os.path.join(repo, "console/config/boards/investigations.toml"), TICKETS_BOARD)
        from server import boards
        boards._console_cache.clear()
        boards._board_cache.clear()
        tickets.create(repo, "INV-1", "dossier", kind="investigations")
        out = ticket_gate.guarded_move(repo, "INV-1", "blocked")
        assert out.get("ok") is not False and rows(repo) == []

    def test_invalid_lane_still_raises_valueerror(self, repo):
        make(repo)
        with pytest.raises(ValueError):
            ticket_gate.guarded_move(repo, T, "nowhere")

    def test_unknown_ticket_still_raises(self, repo):
        with pytest.raises(FileNotFoundError):
            ticket_gate.guarded_move(repo, "T-404", "blocked")

    def test_audit_action_is_registered(self):
        assert "ticket.block" in audit.ACTIONS


HEAD = "| # | Criterion | Status | Evidence |\n|---|---|---|---|\n"


def closeable(repo, tid=T):
    """A ticket whose close-check is clean: one cited file, no open plan tasks."""
    _write(os.path.join(repo, "console", "x.py"), "a\nb\nc\n")
    d = tickets.dir_for(repo, tid)
    _write(os.path.join(d, "%s-verification.md" % tid),
           "# V\n\n" + HEAD + "| 1 | a | PASS | `console/x.py:1` |\n")
    _write(os.path.join(d, "%s-plan.md" % tid), "# P\n\n### [x] %s-01 — done\n" % tid)


class TestCloseGate:
    def test_open_critical_question_refused_lane_unchanged_audit_row(self, repo):
        make(repo)
        closeable(repo)
        trackers.add(repo, T, "questions", "still open", priority="critical")
        out = ticket_gate.guarded_move(repo, T, "done")
        assert out["ok"] is False and out["blocked"] is True
        assert "critical_question_open" in [b["code"] for b in out["blocks"]]
        assert out["hint"]
        assert tickets.load(repo, T)["stage"] == "in-progress"
        got = rows(repo, "ticket.close")
        assert len(got) == 1 and got[0]["outcome"].startswith("refused:")
        assert "critical_question_open" in got[0]["outcome"]

    def test_clean_ticket_moves_and_audit_carries_counts(self, repo):
        make(repo)
        closeable(repo)
        out = ticket_gate.guarded_move(repo, T, "done")
        assert out["stage"] == "done"
        got = rows(repo, "ticket.close")
        assert len(got) == 1 and got[0]["outcome"] == "ok"
        assert got[0]["detail"]["evidence"]["accepted"] == 1
        assert got[0]["detail"]["warnings"] == []

    def test_injected_exception_leaves_lane_and_returns_check_error(self, repo, monkeypatch):
        make(repo)
        closeable(repo)

        def boom(*_a, **_k):
            raise RuntimeError("reader exploded")

        monkeypatch.setattr(ticket_gate.close_check, "evaluate", boom)
        out = ticket_gate.guarded_move(repo, T, "done")
        assert out["blocked"] is True
        assert [b["code"] for b in out["blocks"]] == ["check_error"]
        assert tickets.load(repo, T)["stage"] == "in-progress"
        assert rows(repo, "ticket.close")[0]["outcome"] == "refused: check_error"

    def test_cli_and_verb_agree_and_cli_exits_1(self, repo, capsys):
        make(repo)
        via_verb = verb_handlers.ticket_move(repo, ticket=T, stage="done")
        code, via_cli = cli(repo, "done", capsys=capsys)
        assert code == 1 and via_cli["blocked"] is True and via_verb["blocked"] is True
        assert [b["code"] for b in via_cli["blocks"]] == [b["code"] for b in via_verb["blocks"]]

    def test_direct_tickets_move_still_unguarded(self, repo):
        make(repo)
        moved = tickets.move(repo, T, "done")
        assert moved["stage"] == "done"
        assert rows(repo, "ticket.close") == []

    def test_non_terminal_reopen_and_other_kinds_not_checked(self, repo):
        make(repo)
        out = ticket_gate.guarded_move(repo, T, "in-progress")
        assert out["stage"] == "in-progress" and rows(repo, "ticket.close") == []
        tickets.move(repo, T, "done")
        reopened = ticket_gate.guarded_move(repo, T, "open")
        assert reopened["stage"] == "open" and rows(repo, "ticket.close") == []
        _write(os.path.join(repo, "console/config/boards/investigations.toml"),
               TICKETS_BOARD.replace('kind    = "tickets"', 'kind    = "investigations"')
               .replace('id = "done"', 'id = "resolved"'))
        from server import boards
        boards._board_cache.clear()
        tickets.create(repo, "INV-1", "dossier", kind="investigations")
        moved = ticket_gate.guarded_move(repo, "INV-1", "resolved")
        assert moved.get("stage") == "resolved"
        assert rows(repo, "ticket.close") == []

    def test_close_action_is_registered(self):
        assert "ticket.close" in audit.ACTIONS
