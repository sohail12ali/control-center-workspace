"""T-021 FR-8: close_check.evaluate over fixture tickets, plus the close-check verb."""

import os
import shutil
import time
from datetime import datetime, timedelta, timezone

import pytest

from conftest import _write
from server import close_check as cc
from server import mcp, tickets, trackers, verbs
from server.paths import find_repo_root

T = "T-001"
NOW = datetime(2026, 10, 3, 12, 0, 0, tzinfo=timezone.utc)
HEAD = "| # | Criterion | Status | Evidence |\n|---|---|---|---|\n"
CLEAN = ["| 1 | a | PASS | `console/x.py:3` |", "| 2 | b | **PASS** | `console/tests/test_x.py::test_y` |"]


def stamp(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.fixture
def fx(repo):
    _write(os.path.join(repo, "console", "x.py"), "a\nb\nc\n")
    _write(os.path.join(repo, "console", "tests", "test_x.py"), "def test_y():\n    pass\n")
    tickets.create(repo, T, "A ticket")
    return repo


def verif(repo, rows=CLEAN, plan="### [x] T-001-01 — task\n"):
    d = tickets.dir_for(repo, T)
    _write(os.path.join(d, "T-001-verification.md"), "# V\n\n" + HEAD + "\n".join(rows) + "\n")
    if plan is not None:
        _write(os.path.join(d, "T-001-plan.md"), "# P\n\n" + plan)
    return repo


def codes(out, key="blocks"):
    return [b["code"] for b in out[key]]


def plant_no_verification(r):
    os.remove(os.path.join(tickets.dir_for(r, T), "T-001-verification.md"))


def plant_not_pass(r):
    verif(r, CLEAN + ["| 3 | c | PENDING | `console/x.py` |"])


def plant_stale(r):
    tickets.set_claim(r, T, "agent-1", claimed_at=stamp(NOW - timedelta(days=2)))


PLANTS = {
    "no_verification": plant_no_verification,
    "criterion_not_pass": plant_not_pass,
    "evidence_empty": lambda r: verif(r, ["| 1 | a | PASS |  |"]),
    "evidence_phantom": lambda r: verif(r, ["| 1 | a | PASS | `console/gone.py:3` |"]),
    "critical_question_open": lambda r: trackers.add(r, T, "questions", "Q", priority="critical"),
    "critical_bug_unverified": lambda r: trackers.add(r, T, "bugs", "B", severity="critical"),
    "claim_stale": plant_stale,
    "review_escalated": lambda r: tickets.record_review(r, T, "changes_requested", max_rounds=1),
    "plan_open": lambda r: verif(r, plan="### [x] T-001-01 — a\n### [ ] T-001-02 — b\n"),
}


class TestBlocks:
    @pytest.mark.parametrize("code", sorted(PLANTS))
    def test_each_code_fires_on_planted_fixture_and_not_on_clean(self, fx, code):
        verif(fx)
        assert cc.evaluate(fx, T, now=NOW)["ok"] is True
        PLANTS[code](fx)
        out = cc.evaluate(fx, T, now=NOW)
        assert codes(out) == [code] and out["ok"] is False

    def test_check_error_fires_when_a_reader_raises(self, fx, monkeypatch):
        verif(fx)
        monkeypatch.setattr(cc, "parse_verification_tables", lambda t: 1 / 0)
        out = cc.evaluate(fx, T, now=NOW)
        assert codes(out) == ["check_error"] and out["ok"] is False

    def test_unknown_ticket_is_check_error(self, fx):
        assert codes(cc.evaluate(fx, "T-404", now=NOW)) == ["check_error"]

    def test_clean_fixture_ok_with_exact_counts(self, fx):
        out = cc.evaluate(verif(fx), T, now=NOW)
        assert out["ok"] and out["blocks"] == [] and out["warnings"] == []
        assert out["basis"] == "existence" and out["ticket"] == T
        assert out["evidence"] == {"rows": 2, "pass_rows": 2, "accepted": 2, "partial": 0,
                                   "prose_only": 0, "phantom": 0, "empty": 0}


class TestRowPolicy:
    def test_accepted_plus_missing_is_partial_warn(self, fx):
        out = cc.evaluate(verif(fx, ["| 1 | a | PASS | `console/x.py:3`, `console/gone.py` |"]), T, now=NOW)
        assert out["ok"] and codes(out, "warnings") == ["evidence_partial"]
        assert out["evidence"]["partial"] == 1

    def test_only_missing_is_phantom_block(self, fx):
        out = cc.evaluate(verif(fx, ["| 1 | a | PASS | `console/gone.py`, `console/nope.py:1` |"]), T, now=NOW)
        assert codes(out) == ["evidence_phantom"] and out["evidence"]["phantom"] == 1

    def test_all_prose_table_ok_with_warnings(self, fx):
        rows = ["| 1 | a | PASS | `paint_listening` went from **2 947 ms** to **4 ms** |",
                "| 2 | b | PASS | Live: `3.1s of audio, ended by Silence` |"]
        out = cc.evaluate(verif(fx, rows), T, now=NOW)
        assert out["ok"] and codes(out, "warnings") == ["evidence_prose_only"]
        assert out["evidence"]["prose_only"] == 2

    def test_descoped_row_warns_and_is_not_a_block(self, fx):
        out = cc.evaluate(verif(fx, CLEAN + ["| 3 | c | DEFERRED | to T-9 |"]), T, now=NOW)
        assert out["ok"] and codes(out, "warnings") == ["criterion_descoped"]


class TestT020:
    def test_stale_claim_blocks_held_warns_escalated_blocks_critical_question_blocks(self, fx):
        verif(fx)
        tickets.set_claim(fx, T, "agent-1", claimed_at=stamp(NOW - timedelta(minutes=1)))
        held = cc.evaluate(fx, T, now=NOW)
        assert held["ok"] and codes(held, "warnings") == ["claim_held"]
        assert "agent-1" in held["warnings"][0]["message"]
        plant_stale(fx)
        assert codes(cc.evaluate(fx, T, now=NOW)) == ["claim_stale"]


class TestTotal:
    def test_corrupt_verification_returns_a_block(self, fx):
        d = tickets.dir_for(fx, T)
        with open(os.path.join(d, "T-001-verification.md"), "wb") as fh:
            fh.write(b"\xff\xfe\x00 not a table \x00")
        assert codes(cc.evaluate(fx, T, now=NOW)) == ["no_verification"]

    def test_no_writes(self, fx):
        verif(fx)
        snap = {}
        for root, _d, files in os.walk(os.path.join(fx, "knowledge-center")):
            for n in files:
                p = os.path.join(root, n)
                snap[p] = (open(p, "rb").read(), os.stat(p).st_mtime_ns)
        cc.evaluate(fx, T, now=NOW)
        for p, (data, mt) in snap.items():
            assert open(p, "rb").read() == data and os.stat(p).st_mtime_ns == mt

    def test_50_rows_under_half_second(self, fx):
        rows = ["| %d | r | PASS | `console/x.py:3` `console/tests/test_x.py::test_y` |" % i for i in range(50)]
        verif(fx, rows)
        start = time.monotonic()
        out = cc.evaluate(fx, T, now=NOW)
        assert time.monotonic() - start < 0.5 and out["evidence"]["accepted"] == 50


class TestVerb:
    def test_on_cli_mcp_and_verb_list(self, fx):
        shutil.copyfile(os.path.join(find_repo_root(), "console", "config", "verbs.toml"),
                        os.path.join(fx, "console", "config", "verbs.toml"))
        verbs._cache.clear()
        verif(fx)
        row = next(v for v in verbs.list_verbs(fx) if v["id"] == "close-check")
        assert row["needs_ticket"] and not row["needs_confirm"] and "existence" in row["hint"]
        assert verbs.run(fx, "close-check", ticket=T)["ok"] is True
        tools = {t["name"]: t for t in mcp.tool_list(fx)}
        assert "confirm" not in tools["close-check"]["inputSchema"]["properties"]
        verbs._cache.clear()
