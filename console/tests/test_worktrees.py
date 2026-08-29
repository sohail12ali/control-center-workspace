"""Worktree isolation.

Every test runs against a real git repository built in `tmp_path` — worktrees
are git plumbing, and mocking git here would test the mock. The cases that
matter are the refusals: reusing a path, removing uncommitted work, and a name
that tries to escape the worktree root.
"""

import os
import subprocess

import pytest

from server import boards, worktrees


def _git(cwd, *args):
    proc = subprocess.run(["git"] + list(args), cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    assert proc.returncode == 0, proc.stdout
    return proc.stdout


@pytest.fixture
def gitrepo(repo):
    """The console fixture root, made into a real git repo with one commit."""
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


class TestListing:
    def test_a_fresh_repo_has_only_its_main_worktree(self, gitrepo):
        entries = worktrees.list_worktrees(gitrepo)
        assert len(entries) == 1
        assert entries[0]["is_main"] is True
        assert entries[0]["branch"] == "main"

    def test_not_a_git_repo_is_a_clear_error(self, repo):
        with pytest.raises(worktrees.WorktreeError) as exc:
            worktrees.list_worktrees(repo)
        assert "not a git repository" in str(exc.value)


class TestAdd:
    def test_creates_a_checkout_on_a_new_branch(self, gitrepo):
        entry = worktrees.add(gitrepo, "CC-T001")
        assert os.path.isdir(entry["path"])
        assert os.path.isfile(os.path.join(entry["path"], "README.md"))
        assert entry["branch"] == "agent/CC-T001"

    def test_it_is_reported_as_managed(self, gitrepo):
        worktrees.add(gitrepo, "CC-T001")
        entry = [e for e in worktrees.list_worktrees(gitrepo) if not e["is_main"]][0]
        assert entry["managed"] is True

    def test_two_tickets_get_independent_checkouts(self, gitrepo):
        # The property the whole task exists for: concurrent runs must not
        # be editing the same files.
        a = worktrees.add(gitrepo, "CC-T001")
        b = worktrees.add(gitrepo, "CC-T002")
        assert a["path"] != b["path"]

        with open(os.path.join(a["path"], "only-in-a.txt"), "w") as fh:
            fh.write("a")
        assert not os.path.exists(os.path.join(b["path"], "only-in-a.txt"))

    def test_refuses_an_existing_path(self, gitrepo):
        worktrees.add(gitrepo, "CC-T001")
        with pytest.raises(worktrees.WorktreeError) as exc:
            worktrees.add(gitrepo, "CC-T001")
        assert "already exists" in str(exc.value)

    def test_refuses_a_branch_already_checked_out(self, gitrepo):
        worktrees.add(gitrepo, "CC-T001")
        worktrees.remove(gitrepo, "CC-T001")
        # The branch survives the worktree; a second worktree on it is a git
        # impossibility, so say so rather than surfacing raw git output.
        worktrees.add(gitrepo, "CC-T001")
        with pytest.raises(worktrees.WorktreeError) as exc:
            worktrees.add(gitrepo, "other", branch="agent/CC-T001")
        assert "already checked out" in str(exc.value)

    def test_reuses_an_existing_branch_rather_than_failing(self, gitrepo):
        first = worktrees.add(gitrepo, "CC-T001")
        worktrees.remove(gitrepo, "CC-T001")
        second = worktrees.add(gitrepo, "CC-T001")
        assert second["branch"] == first["branch"]

    @pytest.mark.parametrize("bad", ["../escape", "a/b", "", "with space", "..", "x\\y"])
    def test_refuses_a_name_that_could_escape_the_root(self, gitrepo, bad):
        # This name arrives from a CLI argument or an agent tool call.
        with pytest.raises(worktrees.WorktreeError):
            worktrees.add(gitrepo, bad)

    def test_branch_pattern_comes_from_config(self, gitrepo):
        path = os.path.join(gitrepo, "console", "config", "console.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('\n[worktrees]\nbranch_pattern = "wt/{ticket}-run"\n')
        boards._console_cache.clear()
        assert worktrees.add(gitrepo, "CC-T001")["branch"] == "wt/CC-T001-run"


class TestRemove:
    def test_removes_a_clean_worktree(self, gitrepo):
        path = worktrees.add(gitrepo, "CC-T001")["path"]
        worktrees.remove(gitrepo, "CC-T001")
        assert not os.path.exists(path)

    def test_refuses_to_discard_uncommitted_work(self, gitrepo):
        # An agent run's entire output can be uncommitted. Deleting it on a
        # tidy-up is unrecoverable, so this must be an explicit act.
        path = worktrees.add(gitrepo, "CC-T001")["path"]
        with open(os.path.join(path, "work.txt"), "w") as fh:
            fh.write("hours of work")
        with pytest.raises(worktrees.WorktreeError) as exc:
            worktrees.remove(gitrepo, "CC-T001")
        assert "work.txt" in str(exc.value)      # says what would be lost
        assert os.path.exists(path)

    def test_untracked_files_count_as_work(self, gitrepo):
        path = worktrees.add(gitrepo, "CC-T001")["path"]
        with open(os.path.join(path, "brand-new.txt"), "w") as fh:
            fh.write("created by the run")
        assert worktrees.dirty_files(gitrepo, path) == ["brand-new.txt"]

    def test_force_discards_and_reports_how_much(self, gitrepo):
        path = worktrees.add(gitrepo, "CC-T001")["path"]
        with open(os.path.join(path, "work.txt"), "w") as fh:
            fh.write("x")
        out = worktrees.remove(gitrepo, "CC-T001", force=True)
        assert out["discarded_changes"] == 1
        assert not os.path.exists(path)

    def test_unknown_name_raises(self, gitrepo):
        with pytest.raises(worktrees.WorktreeError):
            worktrees.remove(gitrepo, "CC-T999")

    def test_refuses_a_worktree_it_did_not_create(self, gitrepo, tmp_path):
        outside = str(tmp_path / "elsewhere")
        _git(gitrepo, "worktree", "add", "-b", "manual", outside)
        entry = [e for e in worktrees.list_worktrees(gitrepo)
                 if e["path"].replace("/", os.sep) == outside][0]
        assert entry["managed"] is False
        with pytest.raises(worktrees.WorktreeError):
            worktrees.remove(gitrepo, "elsewhere")


class TestPrune:
    def test_prune_clears_records_of_deleted_directories(self, gitrepo):
        import shutil
        path = worktrees.add(gitrepo, "CC-T001")["path"]
        shutil.rmtree(path)
        worktrees.prune(gitrepo)
        assert len(worktrees.list_worktrees(gitrepo)) == 1
