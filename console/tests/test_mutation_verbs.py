"""T-016: ticket move/set and tracker add/update as verbs."""

import os
import shutil

import pytest

from server import tickets, trackers, verbs
from server.paths import find_repo_root


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


class TestTicketMoveSet:
    def test_move_needs_confirm(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "ticket-move", ticket="T-001",
                      args={"stage": "in-progress"})

    def test_move_changes_lane(self, wired):
        out = verbs.run(wired, "ticket-move", ticket="T-001", confirm=True,
                        args={"stage": "in-progress"})
        assert out["stage"] == "in-progress"
        assert tickets.load(wired, "T-001")["stage"] == "in-progress"

    def test_invalid_lane_fails_like_tickets_move(self, wired):
        with pytest.raises(ValueError) as exc:
            verbs.run(wired, "ticket-move", ticket="T-001", confirm=True,
                      args={"stage": "not-a-lane"})
        assert "not-a-lane" in str(exc.value)

    def test_set_owner(self, wired):
        out = verbs.run(wired, "ticket-set", ticket="T-001", confirm=True,
                        args={"field": "owner", "value": "Irshad"})
        assert out["owner"] == "Irshad"


class TestTrackerVerbs:
    def test_add_question(self, wired):
        item = verbs.run(wired, "tracker-add", ticket="T-001", confirm=True,
                         args={"kind": "questions", "text": "Why?",
                               "type": "design", "priority": "high"})
        assert item["id"] == "Q1"
        assert item["text"] == "Why?"
        assert item["type"] == "design"

    def test_update_status_does_not_blank_answer(self, wired):
        verbs.run(wired, "tracker-add", ticket="T-001", confirm=True,
                  args={"kind": "questions", "text": "Why?"})
        verbs.run(wired, "tracker-update", ticket="T-001", confirm=True,
                  args={"kind": "questions", "item_id": "Q1",
                        "answer": "Because."})
        out = verbs.run(wired, "tracker-update", ticket="T-001", confirm=True,
                        args={"kind": "questions", "item_id": "Q1",
                              "status": "answered"})
        assert out["status"] == "answered"
        assert out["answer"] == "Because."

    def test_add_needs_confirm(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "tracker-add", ticket="T-001",
                      args={"kind": "todos", "text": "x"})


class TestMcpNames:
    def test_tool_names_are_prefixed(self, wired):
        from server import agent_tools
        names = {d["function"]["name"] for d in agent_tools.tool_definitions(wired)}
        assert "console_ticket_move" in names
        assert "console_ticket_set" in names
        assert "console_tracker_add" in names
        assert "console_tracker_update" in names
