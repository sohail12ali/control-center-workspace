"""T-020 FR-19: `claimed_at` as a UTC timestamp and the `claimed_run` link."""

import os
import re
import shutil
from datetime import datetime, timezone

import pytest

from server import runs, tickets, verbs
from server.backends import vault_backend
from server.paths import find_repo_root

UTC_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")


@pytest.fixture
def wired(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    shutil.copyfile(src, os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


def claim(repo, **args):
    args.setdefault("agent", "agent-1")
    return verbs.run(repo, "claim", ticket="T-001", confirm=True, args=args)


def chat_run(repo, state="running", ticket="T-001", chat="c1"):
    rec = runs.create(repo, executor="chat", executor_id=chat, ticket=ticket, state=state)
    return rec["id"]


class TestClaimedAtUtc:
    def test_verb_claim_stamps_utc_timestamp_matching_regex(self, wired):
        out = claim(wired)
        assert UTC_STAMP.match(out["ticket"]["claimed_at"])
        assert UTC_STAMP.match(tickets.load(wired, "T-001")["claimed_at"])

    def test_backend_claim_uses_the_injected_clock(self, wired):
        now = datetime(2026, 9, 16, 23, 59, 58, tzinfo=timezone.utc)
        out = vault_backend.default().claim(wired, "T-001", "agent-1", now=now)
        assert out["claimed_at"] == "2026-09-16T23:59:58Z"


class TestParseClaimedAt:
    def test_date_only_is_end_of_day_utc(self):
        assert tickets.parse_claimed_at("2026-09-16") == \
            datetime(2026, 9, 16, 23, 59, 59, tzinfo=timezone.utc)

    def test_empty_and_garbage_are_none(self):
        assert tickets.parse_claimed_at("") is None
        assert tickets.parse_claimed_at(None) is None
        assert tickets.parse_claimed_at("garbage") is None

    def test_full_timestamp_as_is(self):
        assert tickets.parse_claimed_at("2026-09-16T08:30:00Z") == \
            datetime(2026, 9, 16, 8, 30, 0, tzinfo=timezone.utc)


class TestClaimedRun:
    def test_older_toml_without_claimed_run_loads_empty(self, wired):
        path = tickets._toml_path(wired, tickets.boards_mod.load_console_config(wired), "T-001")
        text = open(path, encoding="utf-8").read()
        assert "claimed_run" in text  # new tickets carry it
        open(path, "w", encoding="utf-8").write(
            "\n".join(l for l in text.splitlines() if not l.startswith("claimed_run")) + "\n")
        assert tickets.load(wired, "T-001")["claimed_run"] == ""

    def test_explicit_run_stored(self, wired):
        rid = chat_run(wired, chat="x")
        chat_run(wired, chat="y")
        out = claim(wired, run=rid)
        assert out["ticket"]["claimed_run"] == rid
        assert tickets.load(wired, "T-001")["claimed_run"] == rid

    def test_sole_active_chat_run_autolinked(self, wired):
        rid = chat_run(wired)
        chat_run(wired, state="done", chat="old")
        assert claim(wired)["ticket"]["claimed_run"] == rid

    def test_zero_or_two_active_runs_store_empty(self, wired):
        assert claim(wired)["ticket"]["claimed_run"] == ""
        tickets.set_claim(wired, "T-001", "")
        chat_run(wired, chat="a")
        chat_run(wired, chat="b")
        assert claim(wired)["ticket"]["claimed_run"] == ""

    def test_runs_on_other_tickets_are_not_linked(self, wired):
        chat_run(wired, ticket="T-999")
        assert claim(wired)["ticket"]["claimed_run"] == ""

    def test_unknown_run_id_refused(self, wired):
        out = claim(wired, run="nope")
        assert out["ok"] is False and "nope" in out["error"]
        assert tickets.load(wired, "T-001")["claimed_by"] == ""

    def test_release_clears_claimed_run(self, wired):
        claim(wired, run=chat_run(wired))
        tickets.set_claim(wired, "T-001", "")
        t = tickets.load(wired, "T-001")
        assert t["claimed_by"] == "" and t["claimed_run"] == ""

    def test_set_claim_without_run_keeps_existing_link_on_refresh(self, wired):
        rid = chat_run(wired)
        tickets.set_claim(wired, "T-001", "agent-1", claimed_run=rid)
        tickets.set_claim(wired, "T-001", "agent-1")
        assert tickets.load(wired, "T-001")["claimed_run"] == rid
