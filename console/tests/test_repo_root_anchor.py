"""T-024 FR-2: `paths.find_repo_root` honours a VALID `CONSOLE_REPO_ROOT`
between an explicit `start` and cwd, and silently ignores an invalid one."""

import os

import pytest

from server import paths


def _same(a, b):
    return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))


def _make_root(path):
    os.makedirs(os.path.join(path, "knowledge-center"))
    os.makedirs(os.path.join(path, "console"))
    return str(path)


@pytest.fixture
def main_and_worktree(tmp_path):
    main = _make_root(tmp_path / "main")
    wt = _make_root(tmp_path / "wt")  # a worktree is a full checkout: a root too
    return main, wt


class TestAnchor:
    def test_ac2a_cwd_in_a_worktree_resolves_to_the_variable(
            self, main_and_worktree, monkeypatch):
        main, wt = main_and_worktree
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", main)
        assert _same(paths.find_repo_root(), main)

    def test_ac2b_unset_variable_resolves_from_cwd_as_before(
            self, main_and_worktree, monkeypatch):
        _main, wt = main_and_worktree
        monkeypatch.chdir(wt)
        monkeypatch.delenv("CONSOLE_REPO_ROOT", raising=False)
        assert _same(paths.find_repo_root(), wt)

    def test_ac2d_an_explicit_start_beats_the_variable(
            self, main_and_worktree, monkeypatch, tmp_path):
        main, wt = main_and_worktree
        other = _make_root(tmp_path / "other")
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", main)
        assert _same(paths.find_repo_root(other), other)

    def test_an_explicit_start_that_is_no_root_falls_through_to_the_variable(
            self, main_and_worktree, monkeypatch, tmp_path):
        main, wt = main_and_worktree
        bare = tmp_path / "bare"
        bare.mkdir()
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", main)
        assert _same(paths.find_repo_root(str(bare)), main)


class TestInvalidVariableIsIgnored:
    @pytest.mark.parametrize("kind", [
        "empty", "literal", "relative", "nonexistent", "non-root-dir", "file"])
    def test_ac2c_same_result_as_no_variable_and_no_exception(
            self, kind, main_and_worktree, monkeypatch, tmp_path):
        _main, wt = main_and_worktree
        plain = tmp_path / "plain"
        plain.mkdir()
        (tmp_path / "afile").write_text("x", encoding="utf-8")
        value = {
            "empty": "",
            "literal": "${CONSOLE_REPO_ROOT:-}",
            "relative": os.path.join("main", "sub"),
            "nonexistent": str(tmp_path / "does-not-exist"),
            "non-root-dir": str(plain),
            "file": str(tmp_path / "afile"),
        }[kind]
        monkeypatch.chdir(wt)
        monkeypatch.delenv("CONSOLE_REPO_ROOT", raising=False)
        expected = paths.find_repo_root()
        monkeypatch.setenv("CONSOLE_REPO_ROOT", value)
        assert _same(paths.find_repo_root(), expected)
        assert _same(expected, wt)

    def test_no_upward_walk_from_an_invalid_variable(
            self, main_and_worktree, monkeypatch):
        # The variable names a SUBDIR of main: upward walking from it would
        # find main, so a pass here means it was ignored rather than walked.
        main, wt = main_and_worktree
        sub = os.path.join(main, "knowledge-center", "artifacts")
        os.makedirs(sub)
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", sub)
        assert _same(paths.find_repo_root(), wt)

    def test_a_broken_workspace_toml_does_not_raise(
            self, main_and_worktree, monkeypatch, tmp_path):
        _main, wt = main_and_worktree
        broken = tmp_path / "broken"
        broken.mkdir()
        (broken / "workspace.toml").write_text("not = [valid", encoding="utf-8")
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", str(broken))
        assert _same(paths.find_repo_root(), wt)


class TestWorkspaceTomlLayout:
    def test_ac2e_renamed_layout_round_trips_the_anchor(self, tmp_path, monkeypatch):
        main = tmp_path / "main"
        os.makedirs(main / "noble-knowledge")
        os.makedirs(main / "noble-console")
        (main / "workspace.toml").write_text(
            'vault = "./noble-knowledge"\nconsole = "./noble-console"\n', encoding="utf-8")
        wt = _make_root(tmp_path / "wt")
        monkeypatch.chdir(wt)
        monkeypatch.setenv("CONSOLE_REPO_ROOT", str(main))
        anchor = paths.find_repo_root()
        assert _same(anchor, main)
        assert _same(paths.vault_dir(anchor), main / "noble-knowledge")
        assert _same(paths.console_dir(anchor), main / "noble-console")
