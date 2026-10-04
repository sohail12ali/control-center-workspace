"""`workspace.toml` schema + parser (T-017 FR-6, slice 1c — schema only;
`find_repo_root` wiring is Phase 2's 2c, not exercised here)."""

import os

import pytest

from server import workspace_config


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _split_workspace(tmp_path):
    """A split-repo layout: workspace.toml at the top, vault/console as
    named sibling directories elsewhere under it."""
    root = tmp_path / "split-ws"
    vault_dir = root / "my-vault"
    console_dir = root / "my-console"
    os.makedirs(vault_dir)
    os.makedirs(console_dir)
    return str(root), str(vault_dir), str(console_dir)


class TestParse:
    def test_reads_a_valid_workspace_toml(self, tmp_path):
        root, vault_dir, console_dir = _split_workspace(tmp_path)
        _write(os.path.join(root, "workspace.toml"),
              'name = "demo"\nvault = "./my-vault"\nconsole = "./my-console"\n')
        result = workspace_config.parse(os.path.join(root, "workspace.toml"))
        assert result["name"] == "demo"
        assert os.path.normpath(result["vault"]) == os.path.normpath(vault_dir)
        assert os.path.normpath(result["console"]) == os.path.normpath(console_dir)
        assert result["projects"] == []

    def test_reads_projects_array(self, tmp_path):
        root, vault_dir, console_dir = _split_workspace(tmp_path)
        os.makedirs(os.path.join(root, "sub-project"))
        _write(os.path.join(root, "workspace.toml"),
              'vault = "./my-vault"\nconsole = "./my-console"\n\n'
              '[[projects]]\nname = "sub-project"\npath = "./sub-project"\n')
        result = workspace_config.parse(os.path.join(root, "workspace.toml"))
        assert result["projects"] == [{
            "name": "sub-project", "path": "./sub-project",
            "resolved_path": os.path.normpath(os.path.join(root, "sub-project")),
        }]

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            workspace_config.parse(str(tmp_path / "workspace.toml"))

    def test_missing_required_key_names_it(self, tmp_path):
        path = str(tmp_path / "workspace.toml")
        _write(path, 'vault = "./my-vault"\n')  # console missing
        with pytest.raises(workspace_config.WorkspaceConfigError, match="console"):
            workspace_config.parse(path)

    def test_a_vault_path_that_does_not_exist_names_the_path(self, tmp_path):
        path = str(tmp_path / "workspace.toml")
        os.makedirs(str(tmp_path / "my-console"))
        _write(path, 'vault = "./nonexistent"\nconsole = "./my-console"\n')
        with pytest.raises(workspace_config.WorkspaceConfigError) as exc:
            workspace_config.parse(path)
        assert "nonexistent" in str(exc.value)
        assert "vault" in str(exc.value)

    def test_a_console_path_that_does_not_exist_names_the_path(self, tmp_path):
        path = str(tmp_path / "workspace.toml")
        os.makedirs(str(tmp_path / "my-vault"))
        _write(path, 'vault = "./my-vault"\nconsole = "./nonexistent"\n')
        with pytest.raises(workspace_config.WorkspaceConfigError) as exc:
            workspace_config.parse(path)
        assert "nonexistent" in str(exc.value)
        assert "console" in str(exc.value)


class TestFindAndResolve:
    def test_find_walks_upward_from_a_nested_start(self, tmp_path):
        root, _, _ = _split_workspace(tmp_path)
        _write(os.path.join(root, "workspace.toml"),
              'vault = "./my-vault"\nconsole = "./my-console"\n')
        nested = os.path.join(root, "my-vault", "artifacts", "T-001")
        os.makedirs(nested)
        assert workspace_config.find(nested) == os.path.join(root, "workspace.toml")

    def test_find_returns_none_when_absent(self, tmp_path):
        assert workspace_config.find(str(tmp_path)) is None

    def test_resolve_is_find_plus_parse(self, tmp_path):
        root, vault_dir, _ = _split_workspace(tmp_path)
        _write(os.path.join(root, "workspace.toml"),
              'vault = "./my-vault"\nconsole = "./my-console"\n')
        result = workspace_config.resolve(root)
        assert os.path.normpath(result["vault"]) == os.path.normpath(vault_dir)

    def test_resolve_returns_none_not_an_error_when_absent(self, tmp_path):
        # a7: absence is the default, unremarkable case — never an error.
        assert workspace_config.resolve(str(tmp_path)) is None
