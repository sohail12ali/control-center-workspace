"""T-021 FR-6: the ticket liveness check, over fixture tickets and an injected clock."""

import os
import shutil
import time
from datetime import datetime, timedelta, timezone

import pytest

from conftest import TICKETS_BOARD, _write
from server import mcp, runs, ticket_liveness, tickets, tomlio, verbs
from server.paths import find_repo_root
from server import trackers

NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)
T = "T-001"
EXPECT_PATH = "console/config/boards/tickets.toml"


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def lv(repo):
    """The fixture workspace with a `verify` lane added to the tickets board."""
    _write(os.path.join(repo, EXPECT_PATH), TICKETS_BOARD.replace(
        '[[lanes]]\nid = "blocked"', '[[lanes]]\nid = "verify"\nlabel = "Verify"\n\n'
        '[[lanes]]\nid = "blocked"'))
    from server import boards
    boards._console_cache.clear()
    boards._board_cache.clear()
    return repo


def build(repo, stage, *, tid=T, owner="", run=None, claim=None, question=None,
          bug=False, kind=None):
    """One ticket in `stage` with the named facts planted."""
    tickets.create(repo, tid, "A ticket", owner=owner)
    tickets.move(repo, tid, stage)
    if kind:
        path = os.path.join(tickets.dir_for(repo, tid), "ticket.toml")
        data = tomlio.load(path)
        data["ticket"]["kind"] = kind
        tomlio.atomic_write(path, data)
    if run:
        runs.create(repo, executor="chat", executor_id="c", ticket=tid, state=run)
    if claim == "held":
        tickets.set_claim(repo, tid, "agent-1", claimed_at=stamp(NOW - timedelta(minutes=1)))
    elif claim == "stale":
        tickets.set_claim(repo, tid, "agent-1", claimed_at=stamp(NOW - timedelta(days=2)))
    if question:
        item = trackers.add(repo, tid, "questions", "Q?")
        if question != "open":
            trackers.update(repo, tid, "questions", item["id"], status=question)
    if bug:
        trackers.add(repo, tid, "bugs", "crash", severity="critical")
    return tid


# (id, stage, facts, applies, expected code or None, expected paths)
ROWS = [
    ("open-nothing", "open", {}, False, None, []),
    ("done-lane", "done", {}, False, None, []),
    ("investigations", "in-progress", {"kind": "investigations"}, False, None, []),
    ("running-run", "in-progress", {"run": "running"}, True, None, ["run"]),
    ("retry-run", "in-progress", {"run": "scheduled_retry"}, True, None, ["run"]),
    ("done-run-only", "in-progress", {"run": "done"}, True, "no_action_path", []),
    ("held-claim", "in-progress", {"claim": "held"}, True, None, ["claim"]),
    ("stale-claim", "in-progress", {"claim": "stale"}, True, "claim_stale", []),
    ("open-question", "in-progress", {"question": "open"}, True, None, ["question"]),
    ("answered-question", "in-progress", {"question": "answered"}, True, None, ["question"]),
    ("resolved-question", "in-progress", {"question": "resolved"}, True, "no_action_path", []),
    ("verify-nothing", "verify", {}, True, "no_action_path", []),
    ("blocked-question-owner", "blocked", {"question": "open", "owner": "sam"}, True, None,
     ["question"]),
    ("blocked-bug-owner", "blocked", {"bug": True, "owner": "sam"}, True, None, ["bug"]),
    ("blocked-nothing", "blocked", {"owner": "sam"}, True, "blocked_prose_only", []),
    ("blocked-question-no-owner", "blocked", {"question": "open"}, True, "blocked_no_owner",
     ["question"]),
    ("blocked-live-run-only", "blocked", {"run": "running", "owner": "sam"}, True,
     "blocked_prose_only", ["run"]),
]


class TestEvaluateTable:
    @pytest.mark.parametrize("row", ROWS, ids=[r[0] for r in ROWS])
    def test_row(self, lv, row):
        _, stage, facts, applies, code, paths = row
        build(lv, stage, **facts)
        out = ticket_liveness.evaluate(lv, T, now=NOW)
        assert out["applies"] is applies and out["ticket"] == T
        assert out["paths"] == paths
        assert [f["code"] for f in out["findings"]] == ([code] if code else [])
        assert out["ok"] is (code is None)
        assert all(f["level"] == "warn" and f["message"] for f in out["findings"])

    def test_unknown_ticket_is_check_error_not_a_raise(self, lv):
        out = ticket_liveness.evaluate(lv, "T-999", now=NOW)
        assert [f["code"] for f in out["findings"]] == ["check_error"]


class TestScan:
    def test_corrupt_questions_toml_is_check_error_and_scan_continues(self, lv):
        build(lv, "in-progress", tid="T-001", question="open")
        build(lv, "in-progress", tid="T-002")
        _write(os.path.join(tickets.dir_for(lv, "T-001"), "T-001-questions.toml"), "[[[ nope")
        out = ticket_liveness.scan(lv, now=NOW)
        by = {r["ticket"]: [f["code"] for f in r["findings"]] for r in out["failing"]}
        assert by == {"T-001": ["check_error"], "T-002": ["no_action_path"]}
        assert out["summary"] == {"checked": 2, "ok": 0, "warn": 2}

    def test_100_tickets_under_2_seconds_and_no_writes(self, lv):
        for n in range(100):
            build(lv, ("in-progress", "verify", "blocked")[n % 3], tid="T-%03d" % (n + 1))
        snap = {}
        for root, _dirs, files in os.walk(os.path.join(lv, "knowledge-center")):
            for name in files:
                p = os.path.join(root, name)
                with open(p, "rb") as fh:
                    snap[p] = (fh.read(), os.stat(p).st_mtime_ns)
        start = time.monotonic()
        out = ticket_liveness.scan(lv, now=NOW)
        assert time.monotonic() - start < 2.0
        assert out["checked"] == out["summary"]["checked"] == 100
        for p, (data, mtime) in snap.items():
            with open(p, "rb") as fh:
                assert fh.read() == data and os.stat(p).st_mtime_ns == mtime


class TestVerb:
    @pytest.fixture
    def wired(self, lv):
        src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
        shutil.copyfile(src, os.path.join(lv, "console", "config", "verbs.toml"))
        verbs._cache.clear()
        yield lv
        verbs._cache.clear()

    def test_runs_without_confirm_and_returns_scan(self, wired):
        build(wired, "in-progress", tid="T-001")
        out = verbs.run(wired, "ticket-liveness")
        assert out["summary"] == {"checked": 1, "ok": 0, "warn": 1}
        one = verbs.run(wired, "ticket-liveness", ticket="T-001")
        assert [f["code"] for f in one["findings"]] == ["no_action_path"]

    def test_mcp_tool_list_contains_ticket_liveness(self, wired):
        tools = {t["name"]: t for t in mcp.tool_list(wired)}
        schema = tools["ticket-liveness"]["inputSchema"]
        assert "confirm" not in schema["properties"] and schema["required"] == []
