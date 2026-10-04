"""T-020 FR-24, BR-8: the review-loop counter, escalation and `review-round`."""

import os
import shutil
import threading

import pytest

from server import audit, run_config, tickets, trackers, verbs
from server.paths import find_repo_root


@pytest.fixture
def wired(repo):
    src = os.path.join(find_repo_root(), "console", "config", "verbs.toml")
    shutil.copyfile(src, os.path.join(repo, "console", "config", "verbs.toml"))
    verbs._cache.clear()
    run_config.reset_warnings()
    tickets.create(repo, "T-001", "A ticket")
    yield repo
    verbs._cache.clear()


def review(repo, outcome, agent="verifier"):
    return verbs.run(repo, "review-round", ticket="T-001", confirm=True,
                     args={"outcome": outcome, "agent": agent})


def critical_questions(repo):
    return [q for q in trackers.list_items(repo, "T-001", "questions")
            if q["priority"] == "critical"]


class TestReviewRound:
    def test_three_changes_requested_escalate_with_exactly_one_critical_question_in_blockers(
            self, wired):
        outs = [review(wired, "changes_requested") for _ in range(3)]
        assert [o["rounds"] for o in outs] == [1, 2, 3]
        assert [o["escalate"] for o in outs] == [False, False, True]
        t = tickets.load(wired, "T-001")
        assert (t["review_rounds"], t["review_escalated"]) == (3, True)
        qs = critical_questions(wired)
        assert len(qs) == 1 and qs[0]["type"] == "review" and qs[0]["raised_by"] == "review-loop"
        assert qs[0] in trackers.blockers(wired, "T-001")["questions"]
        assert t["stage"] == "open"  # no lane moved
        assert len(trackers.list_items(wired, "T-001", "comments")) == 1

    def test_fourth_refused_rounds_stay_three_no_second_question(self, wired):
        for _ in range(3):
            review(wired, "changes_requested")
        out = review(wired, "changes_requested")
        assert out["ok"] is False and out["escalated"] is True
        assert tickets.load(wired, "T-001")["review_rounds"] == 3
        assert len(critical_questions(wired)) == 1

    def test_approved_resets_and_interleaved_approved_prevents_escalation(self, wired):
        review(wired, "changes_requested")
        review(wired, "changes_requested")
        out = review(wired, "approved")
        assert out["ok"] is True and out["rounds"] == 0
        assert tickets.load(wired, "T-001")["review_rounds"] == 0
        for _ in range(2):
            review(wired, "changes_requested")
        review(wired, "approved")
        review(wired, "changes_requested")
        t = tickets.load(wired, "T-001")
        assert (t["review_rounds"], t["review_escalated"]) == (1, False)
        assert critical_questions(wired) == []

    def test_human_decision_clears_escalation_and_restarts_at_one(self, wired):
        for _ in range(3):
            review(wired, "changes_requested")
        out = review(wired, "human_decision", agent="human")
        assert out["ok"] is True
        t = tickets.load(wired, "T-001")
        assert (t["review_rounds"], t["review_escalated"]) == (0, False)
        assert review(wired, "changes_requested")["rounds"] == 1

    def test_older_toml_loads_zero_false_and_create_includes_fields(self, wired):
        created = tickets.create(wired, "T-002", "New")
        assert (created["review_rounds"], created["review_escalated"]) == (0, False)
        path = tickets._toml_path(wired, tickets.boards_mod.load_console_config(wired), "T-001")
        text = open(path, encoding="utf-8").read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(l for l in text.splitlines()
                               if not l.startswith("review_")) + "\n")
        t = tickets.load(wired, "T-001")
        assert (t["review_rounds"], t["review_escalated"]) == (0, False)
        assert review(wired, "changes_requested")["rounds"] == 1

    def test_not_user_editable(self, wired):
        assert "review_rounds" not in tickets.EDITABLE
        assert "review_escalated" not in tickets.EDITABLE

    def test_max_rounds_config_five_and_invalid_falls_back_to_three(self, wired, capsys):
        path = os.path.join(wired, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n[review]\nmax_rounds = 5\n")
        tickets.boards_mod._console_cache.clear()
        outs = [review(wired, "changes_requested") for _ in range(5)]
        assert [o["escalate"] for o in outs] == [False] * 4 + [True]
        # invalid values fall back to 3 with one warning
        for bad in ("0", '"many"'):
            tickets.boards_mod._console_cache.clear()
            run_config.reset_warnings()
            text = open(path, encoding="utf-8").read().replace("max_rounds = 5", "max_rounds = %s" % bad)
            text = text.replace("max_rounds = 0", "max_rounds = %s" % bad)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            tickets.boards_mod._console_cache.clear()
            assert run_config.review_cfg(wired)["max_rounds"] == 3
            run_config.review_cfg(wired)
            assert capsys.readouterr().err.count("max_rounds") == 1

    def test_each_call_audited_with_identity(self, wired):
        review(wired, "changes_requested", agent="verifier")
        review(wired, "approved", agent="verifier")
        rows = audit.read(wired, action="ticket.review")
        assert len(rows) == 2
        assert {r["detail"]["agent"] for r in rows} == {"verifier"}
        assert {r["detail"]["outcome"] for r in rows} == {"changes_requested", "approved"}

    def test_refused_call_is_audited_too(self, wired):
        for _ in range(4):
            review(wired, "changes_requested")
        rows = audit.read(wired, action="ticket.review")
        assert len(rows) == 4 and rows[0]["outcome"].startswith("error:")

    def test_unknown_outcome_refused_and_counter_untouched(self, wired):
        out = review(wired, "maybe")
        assert out["ok"] is False and "changes_requested" in out["error"]
        assert tickets.load(wired, "T-001")["review_rounds"] == 0

    def test_concurrent_changes_requested_create_one_question(self, wired):
        barrier = threading.Barrier(6)

        def go():
            barrier.wait()
            review(wired, "changes_requested")

        threads = [threading.Thread(target=go) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert tickets.load(wired, "T-001")["review_rounds"] == 3
        assert len(critical_questions(wired)) == 1

    def test_in_verb_list_with_confirm_and_ticket_gates(self, wired):
        row = [v for v in verbs.list_verbs(wired) if v["id"] == "review-round"][0]
        assert row["needs_ticket"] and row["needs_confirm"]
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "review-round", ticket="T-001", args={"outcome": "approved"})


class TestTrackerAdd:
    def test_raised_by_passes_through(self, wired):
        item = verbs.run(wired, "tracker-add", ticket="T-001", confirm=True,
                         args={"kind": "questions", "text": "Why?", "raised_by": "someone"})
        assert item["raised_by"] == "someone"
        plain = verbs.run(wired, "tracker-add", ticket="T-001", confirm=True,
                          args={"kind": "questions", "text": "Again?"})
        assert plain["raised_by"] == "agent"
