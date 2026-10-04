"""T-020 FR-13 / BR-10: Run-liveness classes after a clean turn.

`run_failures.liveness` is pure (dicts in, `{state, reason}` out). The evidence
collector is checked against a real ticket and a real tracker in a tmp repo.
"""

import pytest

from server import run_failures, run_sync, runs, tickets, trackers
from server.run_failures import liveness, tool_evidence

OK = {"subtype": "success", "is_error": False, "rate_limit": "", "tools": {}}
ERR = {"subtype": "error_during_execution", "is_error": True, "rate_limit": "", "tools": {}}


def ev(count=0, critical=False):
    return {"count": count, "critical_question": critical}


def live(text="", *, mode="default", evidence=None, lane="in-progress", turn=OK):
    return liveness(turn, mode, evidence if evidence is not None else ev(), lane, text)


class TestLivenessTable:
    @pytest.mark.parametrize("kw, state", [
        (dict(text="Done, tests pass.", evidence=ev(2)), "advanced"),
        (dict(text="Done, tests pass.", evidence=ev(2), lane="done"), "completed"),
        (dict(text="Here is the answer: 42."), "completed"),
        (dict(text=""), "empty"),
        (dict(text="   \n"), "empty"),
        (dict(text="I will first inspect the code."), "plan_only"),
        (dict(text="Waiting on access to the production credentials."), "blocked"),
        (dict(text="all done", lane="blocked"), "blocked"),
        (dict(text="all done", evidence=ev(3), lane="blocked"), "blocked"),
        (dict(text="x", evidence=ev(0, critical=True)), "blocked"),
        (dict(text="done", evidence=ev(2, critical=True)), "blocked"),
        (dict(text="done", turn=ERR), "failed"),
        (dict(text="I am not blocked, no blockers. Fixed it."), "completed"),
        (dict(text="", evidence=ev(1)), "advanced"),
    ])
    def test_each_class(self, kw, state):
        assert live(**kw)["state"] == state

    def test_reason_is_short_and_always_present(self):
        out = live(text="Waiting on access to " + "x" * 500)
        assert out["state"] == "blocked"
        assert 0 < len(out["reason"]) <= 200
        assert set(out) == {"state", "reason"}

    @pytest.mark.parametrize("mode", ["plan", "ask"])
    def test_plan_mode_planning_text_is_advanced_default_mode_is_plan_only(self, mode):
        text = "I will first inspect the code and then propose a design."
        assert live(text, mode=mode)["state"] == "advanced"
        assert live(text, mode="default")["state"] == "plan_only"
        assert live(text, mode="acceptEdits")["state"] == "plan_only"

    @pytest.mark.parametrize("mode", ["plan", "ask"])
    def test_read_only_mode_never_plan_only(self, mode):
        for text in ("Next steps:\n- read the file", "Let me check the tests.", "hello"):
            assert live(text, mode=mode)["state"] == "advanced"

    def test_read_only_mode_empty_reply_is_still_empty(self):
        assert live("", mode="plan")["state"] == "empty"

    def test_bash_only_turn_with_no_text_is_empty(self):
        assert tool_evidence({"Bash": 4})["count"] == 0
        out = live("", evidence=tool_evidence({"Bash": 4}))
        assert out["state"] == "empty"

    def test_file_tools_and_console_verbs_count_bash_does_not(self):
        tools = {"Write": 1, "Edit": 2, "MultiEdit": 1, "NotebookEdit": 1, "Bash": 9,
                 "Read": 5, "mcp__console__ticket-move": 1, "console_tracker_add": 2,
                 "mcp__console__context": 3, "console_ready": 1}
        assert tool_evidence(tools)["count"] == 1 + 2 + 1 + 1 + 1 + 2
        assert tool_evidence({})["count"] == 0
        assert tool_evidence(None)["count"] == 0

    PLANNING = [
        "I'll start by reading the config module.",
        "Let me look at the failing test first.",
        "Next steps:\n1. inspect\n2. fix",
        "Sure, I will first investigate the build.",
    ]
    SUMMARIES = [
        "The audit found three issues; the next release will include the fix for all.",
        "Refactored the parser. It will now reject empty input, and next to it sits a helper.",
        "Answer: the port is 8080, and the proxy will forward requests there.",
        "All 12 tests pass. Plan: none needed, the change is complete.",
    ]

    def test_eight_reply_text_fixtures(self):
        for text in self.PLANNING:
            assert live(text)["state"] == "plan_only", text
        for text in self.SUMMARIES:
            assert live(text)["state"] == "completed", text

    def test_plan_only_and_empty_never_schedule_retry(self):
        r = {"id": "r1", "executor": "chat", "executor_id": "c1", "state": "running",
             "backend": "claude"}
        for text in ("I will first inspect the code.", ""):
            view = {"alive": True, "busy": False, "queued": 0,
                    "last_turn": dict(OK, result=text, mode="default"), "turn_count": 1,
                    "last_output_at": "", "stop_requested": False, "started_utc": "",
                    "watchable": True, "exit_code": None, "stderr": "",
                    "pending_approvals": [], "mode": "default"}
            patch = run_sync.sync_run(r, view, "2026-10-01T12:00:00Z")
            assert patch["state"] == "done"
            assert patch["liveness"]["state"] in ("plan_only", "empty")
            assert patch["state"] != "scheduled_retry"
            assert "retry_due" not in patch


class TestCollectEvidence:
    def _ticket(self, repo):
        tickets.create(repo, "T-001", "t")
        return "T-001"

    def test_comments_since_created_and_diffstat_counted(self, repo, monkeypatch, tmp_path):
        t = self._ticket(repo)
        old = trackers.add(repo, t, "comments", "before the run")
        trackers.update(repo, t, "comments", old["id"], posted_on="2020-01-01T00:00:00Z")
        trackers.add(repo, t, "comments", "during the run")
        trackers.add(repo, t, "comments", "also during")
        run = {"ticket": t, "created": "2026-01-01T00:00:00Z", "worktree_path": str(tmp_path)}
        monkeypatch.setattr(run_sync.worktrees, "diff_stat",
                            lambda root, path: " a.py | 2 +-")
        out = run_sync.collect_evidence(repo, run, {"last_turn": {"tools": {"Write": 1, "Bash": 3}}})
        assert out["tools"] == 1 and out["comments"] == 2 and out["diff"] is True
        assert out["count"] == 1 + 2 + 1
        assert out["lane"] == tickets.load(repo, t)["stage"]

    def test_clean_worktree_and_no_ticket_add_nothing(self, repo, monkeypatch, tmp_path):
        monkeypatch.setattr(run_sync.worktrees, "diff_stat", lambda root, path: "no changes")
        run = {"ticket": "", "created": "2026-01-01T00:00:00Z", "worktree_path": str(tmp_path)}
        out = run_sync.collect_evidence(repo, run, {"last_turn": None})
        assert out["count"] == 0 and out["diff"] is False and out["lane"] == ""

    def test_new_open_critical_question_is_reported(self, repo):
        t = self._ticket(repo)
        trackers.add(repo, t, "questions", "which db?", priority="critical")
        trackers.add(repo, t, "questions", "colour?", priority="low")
        run = {"ticket": t, "created": "2000-01-01T00:00:00Z", "worktree_path": ""}
        out = run_sync.collect_evidence(repo, run, {"last_turn": None})
        assert out["critical_question"] is True and out["items"] == 2

    def test_unreadable_ticket_fails_closed_to_zero(self, repo):
        run = {"ticket": "T-999", "created": "2000-01-01T00:00:00Z", "worktree_path": ""}
        out = run_sync.collect_evidence(repo, run, {"last_turn": {"tools": {}}})
        assert out["count"] == 0 and out["critical_question"] is False


class TestDonePatchCarriesLiveness:
    def test_done_patch_has_liveness_in_the_same_patch(self):
        r = {"id": "r1", "executor": "chat", "executor_id": "c1", "state": "running"}
        view = {"alive": True, "busy": False, "queued": 0, "turn_count": 1,
                "last_turn": dict(OK, result="Fixed it.", tools={"Edit": 1}),
                "last_output_at": "", "stop_requested": False, "started_utc": "",
                "watchable": True, "exit_code": None, "stderr": "", "pending_approvals": []}
        patch = run_sync.sync_run(r, view, "2026-10-01T12:00:00Z")
        assert patch["state"] == "done" and patch["liveness"]["state"] == "advanced"

    def test_constants_exist(self):
        assert run_failures.PLANNING_ONLY.search("I will first inspect it")
        assert run_failures.NEXT_STEPS.search("Next steps: x")
