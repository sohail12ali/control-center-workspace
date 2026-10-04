"""T-018 Phase 3b: the `pr-check` verb (FR-6) and its lane-hint suggestion
(FR-7, decision-log a4). Mirrors test_ready_claim_comment_verbs.py's shape —
verbs installed from the shipped verbs.toml, run through `verbs.run`.

Decision-log a4 is a hard acceptance gate, not a style preference: this file
includes a grep-based test asserting the lane-hint code path never calls
`ticket_move`/`close-work`, independently of what the suggestion text says.
"""

import ast
import inspect
import json
import os
import shutil

import pytest

from server import pr_state, tickets, trackers, verb_handlers, verbs
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


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _mock_gh(monkeypatch, state, url="https://example/pr/1"):
    def fake_run(*a, **k):
        return _Proc(0, json.dumps({"state": state, "url": url}))
    monkeypatch.setattr(pr_state.subprocess, "run", fake_run)


class TestPrCheckVerb:
    def test_needs_confirm(self, wired):
        with pytest.raises(verbs.VerbError):
            verbs.run(wired, "pr-check", ticket="T-001")

    def test_no_branch_is_a_named_refusal(self, wired):
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["ok"] is False
        assert "branch" in out["error"]

    def test_updates_pr_url_and_state_on_open(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001")
        _mock_gh(monkeypatch, "OPEN")
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["ok"] is True
        assert out["ticket"]["pr_state"] == "open"
        assert out["ticket"]["pr_url"] == "https://example/pr/1"
        assert tickets.load(wired, "T-001")["pr_state"] == "open"

    def test_gh_error_is_a_named_refusal_not_a_crash(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001")

        def fake_run(*a, **k):
            raise FileNotFoundError("gh not found")
        monkeypatch.setattr(pr_state.subprocess, "run", fake_run)
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["ok"] is False
        assert "not installed" in out["error"]

    def test_appears_in_verb_registry(self, wired):
        assert "pr-check" in verbs.registry(wired)


class TestLaneHint:
    def test_pr_open_suggests_verify_via_comment(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001")
        _mock_gh(monkeypatch, "OPEN")
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["suggestion"] is not None
        assert "verify" in out["suggestion"]["text"].lower()
        items = trackers.list_items(wired, "T-001", "comments")
        assert len(items) == 1
        assert "verify" in items[0]["text"].lower()

    def test_pr_merged_suggests_done_via_comment(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001")
        _mock_gh(monkeypatch, "MERGED")
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["suggestion"] is not None
        assert "close-work" in out["suggestion"]["text"].lower()

    def test_no_transition_no_suggestion(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001", pr_state="open")
        _mock_gh(monkeypatch, "OPEN")
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["suggestion"] is None

    def test_merge_while_already_done_has_no_suggestion(self, wired, monkeypatch):
        tickets.set_pr(wired, "T-001", branch="agent/T-001")
        tickets.move(wired, "T-001", "done")
        _mock_gh(monkeypatch, "MERGED")
        out = verbs.run(wired, "pr-check", ticket="T-001", confirm=True)
        assert out["suggestion"] is None

    def test_never_calls_ticket_move_or_close_work(self):
        """Decision-log a4, hard gate: grep the lane-hint source for the two
        forbidden call names. Independently verifiable by inspection, not
        just by behavioural assertion above."""
        src = inspect.getsource(verb_handlers._lane_hint)
        tree = ast.parse(src)
        func_def = tree.body[0]
        # Strip the docstring (which names the forbidden calls in prose, for
        # a human reading the source) before checking actual call sites.
        body_src = "\n".join(
            ast.get_source_segment(src, node) or ""
            for node in func_def.body
            if not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)))
        assert "ticket_move" not in body_src
        assert "close_work" not in body_src
        called_names = {
            node.func.id for node in ast.walk(func_def)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "ticket_move" not in called_names
        assert "close_work" not in called_names
