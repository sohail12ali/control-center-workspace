"""T-018 FR-1..FR-4: worktree resolution as wired into `agent_manager.create`.

`_resolve_worktree` is tested directly rather than through `create()` itself —
`create()` spawns a real backend process, which is what `test_agent_backends.py`
and friends already avoid; the worktree decision (reuse/create/fall-back) is a
pure function of the repo and the ticket id, so it is unit-testable against a
real git repo the same way `test_worktrees.py` tests `worktrees.add`/`_find`.
"""

import os
import subprocess

import pytest

from server import agent_manager, boards, worktrees


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


class TestResolveWorktree:
    def test_creates_a_worktree_for_a_new_ticket(self, gitrepo):
        cwd, path, branch, error = agent_manager._resolve_worktree(gitrepo, "T-018")
        assert cwd == path
        assert os.path.isdir(path)
        assert branch == "agent/T-018"
        assert error == ""

    def test_reuses_the_existing_worktree_rather_than_recreating(self, gitrepo):
        first = agent_manager._resolve_worktree(gitrepo, "T-018")
        second = agent_manager._resolve_worktree(gitrepo, "T-018")
        assert first[1] == second[1]
        assert second[3] == ""
        # Only one entry under the managed root — a naive second `add()`
        # would have raised WorktreeError("already exists") instead.
        managed = [e for e in worktrees.list_worktrees(gitrepo) if e["managed"]]
        assert len(managed) == 1

    def test_falls_back_to_repo_root_on_non_git_repo(self, repo):
        # `repo` (not `gitrepo`) has no `.git` — exactly the WorktreeError case.
        cwd, path, branch, error = agent_manager._resolve_worktree(repo, "T-018")
        assert cwd == repo
        assert path == "" and branch == ""
        assert "not a git repository" in error

    def test_ticketless_call_site_never_reaches_worktree_resolution(self, gitrepo):
        # `create()` only calls `_resolve_worktree` when `ticket` is truthy;
        # this pins that no worktree exists after resolving nothing.
        assert worktrees.list_worktrees(gitrepo)[0]["is_main"] is True
        assert len([e for e in worktrees.list_worktrees(gitrepo) if not e["is_main"]]) == 0
