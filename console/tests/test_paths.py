"""`find_repo_root` (T-017 FR-6/2c): the pre-existing sibling-folder walk plus
a new, backward-compatible `workspace.toml` first branch (decision-log a7).
"""

import os

import pytest

from server import paths, workspace_config


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class TestSiblingFallbackUnchanged:
    """2c-3: existing single-repo checkouts (no workspace.toml) resolve
    exactly as before this ticket."""

    def test_resolves_a_plain_sibling_layout(self, tmp_path):
        root = str(tmp_path / "ws")
        os.makedirs(os.path.join(root, "knowledge-center"))
        os.makedirs(os.path.join(root, "console"))
        assert paths.find_repo_root(str(root)) == root

    def test_walks_upward_from_a_nested_start(self, tmp_path):
        root = str(tmp_path / "ws")
        os.makedirs(os.path.join(root, "knowledge-center"))
        os.makedirs(os.path.join(root, "console"))
        nested = os.path.join(root, "knowledge-center", "artifacts", "T-001")
        os.makedirs(nested)
        assert paths.find_repo_root(nested) == root

    def test_the_real_checkout_still_resolves(self):
        # No workspace.toml exists at this repo's own root — pins that the
        # new first branch is a true no-op for the actual project checkout.
        root = paths.find_repo_root()
        assert workspace_config.find(root) is None
        assert os.path.isdir(os.path.join(root, "knowledge-center"))
        assert os.path.isdir(os.path.join(root, "console"))


class TestWorkspaceTomlFirstBranch:
    """2c-1/2c-4: a workspace.toml naming a literal knowledge-center/console
    pair resolves to their shared parent, found wherever workspace.toml is,
    not just by walking up from the start directory."""

    def test_split_repo_layout_bound_by_workspace_toml_resolves(self, tmp_path):
        outer = str(tmp_path / "outer")
        real_root = os.path.join(outer, "actual-checkout")
        os.makedirs(os.path.join(real_root, "knowledge-center"))
        os.makedirs(os.path.join(real_root, "console"))
        # workspace.toml sits above the pair it names — not discoverable by
        # today's plain upward directory walk from a start inside `outer`
        # alone, but findable once workspace.toml is searched for first.
        _write(os.path.join(outer, "workspace.toml"),
              'vault = "./actual-checkout/knowledge-center"\n'
              'console = "./actual-checkout/console"\n')
        nested_start = os.path.join(real_root, "knowledge-center")
        assert paths.find_repo_root(nested_start) == real_root

    def test_a_renamed_layout_resolves_via_the_workspace_toml_anchor(self, tmp_path):
        """2c/a9: a `workspace.toml` naming a vault that isn't literally
        called `knowledge-center` no longer raises `RepoRootError` — the
        plan's own illustrative renamed layout is real scope, not a future
        case. `find_repo_root` returns a stable anchor (the workspace.toml's
        own directory); `vault_dir`/`console_dir` re-resolve the real,
        renamed paths from it."""
        root = str(tmp_path / "ws")
        os.makedirs(os.path.join(root, "my-vault"))
        os.makedirs(os.path.join(root, "console"))
        _write(os.path.join(root, "workspace.toml"),
              'vault = "./my-vault"\nconsole = "./console"\n')
        anchor = paths.find_repo_root(root)
        assert paths.vault_dir(anchor) == os.path.join(root, "my-vault")
        assert paths.console_dir(anchor) == os.path.join(root, "console")

    def test_an_unresolvable_workspace_toml_path_still_raises_named_error(self, tmp_path):
        root = str(tmp_path / "ws")
        os.makedirs(os.path.join(root, "console"))
        _write(os.path.join(root, "workspace.toml"),
              'vault = "./nonexistent"\nconsole = "./console"\n')
        with pytest.raises(workspace_config.WorkspaceConfigError):
            paths.find_repo_root(root)


class TestVaultDirConsoleDirRenamedPair:
    """a9: `vault_dir`/`console_dir`/`resolve_rel` resolve a genuinely
    renamed/relocated vault+console pair — the plan's own illustrative
    `vault = "../noble-knowledge"` — not just find_repo_root not crashing."""

    def test_the_plans_own_illustrative_renamed_pair_resolves(self, tmp_path):
        outer = str(tmp_path / "outer")
        vault = os.path.join(outer, "noble-knowledge")
        console = os.path.join(outer, "actual-checkout", "console")
        os.makedirs(vault)
        os.makedirs(console)
        _write(os.path.join(outer, "workspace.toml"),
              'vault = "./noble-knowledge"\nconsole = "./actual-checkout/console"\n')
        anchor = paths.find_repo_root(outer)
        assert paths.vault_dir(anchor) == vault
        assert paths.console_dir(anchor) == console

    def test_resolve_rel_honors_the_rename_for_a_console_config_path(self, tmp_path):
        outer = str(tmp_path / "outer")
        os.makedirs(os.path.join(outer, "noble-knowledge"))
        os.makedirs(os.path.join(outer, "my-console"))
        _write(os.path.join(outer, "workspace.toml"),
              'vault = "./noble-knowledge"\nconsole = "./my-console"\n')
        anchor = paths.find_repo_root(outer)
        rel = os.path.join("console", "config", "verbs.toml")
        assert paths.resolve_rel(anchor, rel) == os.path.join(
            outer, "my-console", "config", "verbs.toml")

    def test_resolve_rel_honors_the_rename_for_a_vault_path(self, tmp_path):
        outer = str(tmp_path / "outer")
        os.makedirs(os.path.join(outer, "noble-knowledge"))
        os.makedirs(os.path.join(outer, "console"))
        _write(os.path.join(outer, "workspace.toml"),
              'vault = "./noble-knowledge"\nconsole = "./console"\n')
        anchor = paths.find_repo_root(outer)
        rel = os.path.join("knowledge-center", "artifacts")
        assert paths.resolve_rel(anchor, rel) == os.path.join(
            outer, "noble-knowledge", "artifacts")

    def test_vault_dir_console_dir_are_a_no_op_with_no_workspace_toml(self, tmp_path):
        root = str(tmp_path / "ws")
        os.makedirs(os.path.join(root, "knowledge-center"))
        os.makedirs(os.path.join(root, "console"))
        assert paths.vault_dir(root) == os.path.join(root, "knowledge-center")
        assert paths.console_dir(root) == os.path.join(root, "console")
        rel = os.path.join("console", "config", "verbs.toml")
        assert paths.resolve_rel(root, rel) == os.path.join(root, rel)
