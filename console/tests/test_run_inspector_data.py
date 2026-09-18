"""T-018 FR-8 (data half): `verb_handlers._enrich_run` / `run_list` / `run_show`
add worktree display, diffstat, and telemetry cost/tokens to a Run record for
the Agents-tab inspector (decision-log a5 — this feeds the existing view, no
new route)."""

import os
import subprocess

import pytest

from server import boards, runs, telemetry, verb_handlers, worktrees


def _git(cwd, *args):
    proc = subprocess.run(["git"] + list(args), cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    assert proc.returncode == 0, proc.stdout
    return proc.stdout


@pytest.fixture
def gitrepo(repo):
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("# fixture\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    boards._console_cache.clear()
    return repo


class TestWorktreeDisplay:
    def test_ticketless_run_shows_shared_tree(self, repo):
        rec = runs.create(repo, ticket="", executor="chat", executor_id="c1")
        out = verb_handlers.run_list(repo)["runs"][0]
        assert out["worktree_display"] == "shared tree"
        assert out["diffstat"] == ""

    def test_ticketed_run_with_real_worktree_shows_its_path(self, gitrepo):
        entry = worktrees.add(gitrepo, "T-001")
        rec = runs.create(gitrepo, ticket="T-001", executor="chat",
                          executor_id="c1", worktree_path=entry["path"],
                          worktree_branch=entry["branch"])
        out = verb_handlers.run_list(gitrepo)["runs"][0]
        assert out["worktree_display"] == entry["path"]
        assert out["diffstat"] == "no changes"

    def test_ticketed_run_with_a_fallback_shows_the_reason_not_blank(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="c1",
                          worktree_error="T-001 is not a git repository")
        out = verb_handlers.run_show(repo, run_id=rec["id"])
        assert out["worktree_display"] == "T-001 is not a git repository"

    def test_real_diff_shows_up_in_the_stat(self, gitrepo):
        entry = worktrees.add(gitrepo, "T-001")
        with open(os.path.join(entry["path"], "README.md"), "a", encoding="utf-8") as fh:
            fh.write("more\n")
        rec = runs.create(gitrepo, ticket="T-001", executor="chat",
                          executor_id="c1", worktree_path=entry["path"])
        out = verb_handlers.run_show(gitrepo, run_id=rec["id"])
        assert "README.md" in out["diffstat"]


class TestTelemetryOnRuns:
    def test_cost_and_tokens_are_summed_for_the_runs_session(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="sess-a")
        telemetry.record_turn(repo, session="sess-a", backend="claude",
                              model="claude-opus-5", input_tokens=100,
                              output_tokens=50, cost_usd=0.01)
        telemetry.record_turn(repo, session="sess-a", backend="claude",
                              model="claude-opus-5", input_tokens=200,
                              output_tokens=25, cost_usd=0.02)
        telemetry.record_turn(repo, session="sess-other", backend="claude",
                              model="claude-opus-5", input_tokens=999,
                              output_tokens=999, cost_usd=9.0)
        out = verb_handlers.run_show(repo, run_id=rec["id"])
        assert out["tokens"] == 375
        assert out["cost_usd"] == 0.03

    def test_no_telemetry_is_zero_not_missing(self, repo):
        rec = runs.create(repo, ticket="T-001", executor="chat", executor_id="c1")
        out = verb_handlers.run_show(repo, run_id=rec["id"])
        assert out["cost_usd"] == 0
        assert out["tokens"] == 0
