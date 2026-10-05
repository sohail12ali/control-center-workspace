"""T-024 AC-4a / AC-4c: a ticketed chat over a real git worktree reports its
usage to the MAIN repo, not to the worktree it happens to be running in.

Written red first (T-024-01): `BaseSession._observe` calls
`telemetry.record_turn(self.cwd, ...)`, and for a ticketed chat `cwd` is the
worktree, so the record lands in `<worktree>/knowledge-center/telemetry` where
the Analytics tab (which reads the main repo) never sees it.
"""

import os
import subprocess

import pytest

from server import agent_backends, agent_manager, agent_session, boards, notify, telemetry, verb_handlers


def _git(cwd, *args):
    proc = subprocess.run(["git"] + list(args), cwd=cwd,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True)
    assert proc.returncode == 0, proc.stdout
    return proc.stdout


def _same(a, b):
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


@pytest.fixture
def gitrepo(repo):
    # Same 12 lines as test_agent_manager_worktree.gitrepo (kept local so this
    # file does not depend on another test module's fixture surviving).
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


@pytest.fixture
def worktree_session(gitrepo):
    """(main, worktree, session): a ticketed session whose cwd is a real git
    worktree and whose repo_root is the main checkout — exactly what
    `agent_manager.create` builds for a ticketed chat."""
    cwd, path, _branch, error = agent_manager._resolve_worktree(gitrepo, "T-024")
    assert error == "", "worktree could not be created: %s" % error
    assert not _same(cwd, gitrepo), "fixture must give a worktree distinct from main"
    backend = agent_backends.get(gitrepo, "alpha")
    sess = agent_session.build("sid-wt", backend, cwd, ticket="T-024",
                               model="priced-model", repo_root=gitrepo)
    return gitrepo, cwd, sess


def _end_one_turn(sess):
    sess._observe({"type": "turn.end", "cost_usd": 0.25, "input_tokens": 120,
                   "output_tokens": 40, "duration_ms": 900, "num_turns": 1})


class TestWorktreeTelemetryAnchor:
    def test_ac4a_turn_record_lands_in_the_main_repo(self, worktree_session):
        main, wt, sess = worktree_session
        _end_one_turn(sess)

        in_main = telemetry.read_records(main)
        assert [r["session"] for r in in_main] == ["sid-wt"], (
            "no telemetry record under main %s; worktree %s holds %s"
            % (main, wt, os.listdir(telemetry.telemetry_dir(wt))
               if os.path.isdir(telemetry.telemetry_dir(wt)) else "nothing"))
        assert in_main[0]["ticket"] == "T-024"

    def test_ac4a_nothing_is_written_under_the_worktree(self, worktree_session):
        main, wt, sess = worktree_session
        _end_one_turn(sess)

        stray = os.path.join(wt, "knowledge-center", "telemetry")
        assert not os.path.exists(stray), (
            "telemetry was written under the worktree: %s -> %s"
            % (stray, os.listdir(stray)))

    def test_ac4c_by_session_totals_see_the_worktree_chat(self, worktree_session):
        main, _wt, sess = worktree_session
        _end_one_turn(sess)

        totals = verb_handlers._telemetry_by_session(main)
        assert "sid-wt" in totals, (
            "the Agents tab reads main's telemetry; this session is missing: %r" % totals)
        assert totals["sid-wt"]["tokens"] > 0
        assert totals["sid-wt"]["cost_usd"] > 0


class TestNotifyAndFallback:
    def test_ac4b_the_turn_end_notification_gets_the_main_root(
            self, worktree_session, monkeypatch):
        main, wt, sess = worktree_session
        roots = []
        monkeypatch.setattr(notify, "send", lambda root, *a, **kw: roots.append(root))
        _end_one_turn(sess)

        assert len(roots) == 1
        assert _same(roots[0], main)
        assert not _same(roots[0], wt)

    def test_ac4d_no_repo_root_falls_back_to_cwd(self, gitrepo, monkeypatch):
        roots = []
        monkeypatch.setattr(notify, "send", lambda root, *a, **kw: roots.append(root))
        backend = agent_backends.get(gitrepo, "alpha")
        sess = agent_session.build("sid-nr", backend, gitrepo, ticket="T-024",
                                   model="priced-model", repo_root="")
        _end_one_turn(sess)

        assert [r["session"] for r in telemetry.read_records(gitrepo)] == ["sid-nr"]
        assert len(roots) == 1 and _same(roots[0], gitrepo)
