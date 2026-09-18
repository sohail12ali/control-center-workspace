"""Board config.

Lane flags are the part with teeth: `terminal` is what stops a Done column
being counted as backlog, and `wip` is advisory on purpose — a board that
refuses a move just gets bypassed.
"""

import os

import pytest

from server import boards


class TestLanes:
    def test_lanes_come_back_in_board_order(self, repo):
        assert [l["id"] for l in boards.lanes_for("tickets", repo)] == \
            ["open", "in-progress", "blocked", "done"]

    def test_flags_default_off(self, repo):
        first = boards.lanes_for("tickets", repo)[0]
        assert first["terminal"] is False
        assert first["wip"] is None
        assert first["tone"] == ""

    def test_flags_are_read_where_set(self, repo):
        lanes = {l["id"]: l for l in boards.lanes_for("tickets", repo)}
        assert lanes["done"]["terminal"] is True
        assert lanes["in-progress"]["wip"] == 3
        assert lanes["blocked"]["tone"] == "danger"

    def test_valid_stage(self, repo):
        assert boards.valid_stage("tickets", "blocked", repo) is True
        assert boards.valid_stage("tickets", "verify", repo) is False


class TestConfig:
    def test_enabled_boards_is_the_filter_not_the_inventory(self, repo):
        # A board config can exist on disk and still be switched off.
        path = os.path.join(repo, "console", "config", "boards", "migrations.toml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('[board]\nkind = "migrations"\nlabel = "Migrations"\n\n'
                     '[[lanes]]\nid = "todo"\nlabel = "To do"\n')
        boards._board_cache.clear()

        assert "migrations" in boards.all_board_kinds(repo)
        assert boards.enabled_boards(repo) == ["tickets"]

    def test_board_label(self, repo):
        assert boards.board_label("tickets", repo) == "Tickets"

    def test_show_trackers(self, repo):
        assert boards.show_trackers_for("tickets", repo) == ["questions", "bugs"]

    def test_unknown_kind_raises(self, repo):
        with pytest.raises(ValueError):
            boards.load_board_config("nope", repo)

    def test_console_config_exposes_the_id_pattern(self, repo):
        cfg = boards.load_console_config(repo)
        assert cfg["general"]["id_pattern"].startswith("^[A-Z]")
