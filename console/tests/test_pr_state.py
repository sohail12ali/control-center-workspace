"""T-018 FR-6 / decision-log a1: `gh pr view` shell-out, mocked at the
`subprocess.run` boundary — the real CLI is not installed on every machine
that runs this suite (nor should this test depend on GitHub network access),
mirroring how `test_worktrees.py` tests real git plumbing but this ticket's
own decision log is explicit that `gh` gets no client of its own to fake."""

import json

import pytest

from server import pr_state


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _mock_run(monkeypatch, proc=None, raise_exc=None):
    def fake_run(*a, **k):
        if raise_exc is not None:
            raise raise_exc
        return proc
    monkeypatch.setattr(pr_state.subprocess, "run", fake_run)


class TestPrStateFor:
    def test_open_pr_maps_correctly(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(0, json.dumps({"state": "OPEN", "url": "https://x/pr/1"})))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out == {"pr_url": "https://x/pr/1", "pr_state": "open", "error": ""}

    def test_merged_pr_maps_correctly(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(0, json.dumps({"state": "MERGED", "url": "https://x/pr/2"})))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == "merged"

    def test_no_pr_for_branch(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(1, "", "no pull requests found for branch \"agent/T-001\""))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out == {"pr_url": "", "pr_state": "none", "error": ""}

    def test_ambiguous_output_does_not_raise(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(0, "not json at all"))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == ""
        assert "unrecognised" in out["error"]

    def test_gh_missing_is_non_fatal(self, monkeypatch):
        _mock_run(monkeypatch, raise_exc=FileNotFoundError("gh: command not found"))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == ""
        assert "not installed" in out["error"]
        assert "error" in out  # no exception propagated

    def test_gh_unauthenticated_is_non_fatal(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(1, "", "not logged into any GitHub hosts"))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == ""
        assert "not authenticated" in out["error"]

    def test_gh_timeout_is_non_fatal(self, monkeypatch):
        import subprocess
        _mock_run(monkeypatch, raise_exc=subprocess.TimeoutExpired(
            cmd=["gh", "pr", "view"], timeout=pr_state._GH_TIMEOUT))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == ""
        assert "timed out" in out["error"]
        assert "error" in out  # no exception propagated

    def test_no_branch_is_a_clean_error_not_a_crash(self):
        out = pr_state.pr_state_for("/repo", "")
        assert out["pr_state"] == "" and out["error"]

    def test_closed_pr_maps_correctly(self, monkeypatch):
        _mock_run(monkeypatch, _Proc(0, json.dumps({"state": "CLOSED", "url": "https://x/pr/3"})))
        out = pr_state.pr_state_for("/repo", "agent/T-001")
        assert out["pr_state"] == "closed"
