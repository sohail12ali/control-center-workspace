"""T-017 decision-log a9: a genuinely renamed/relocated vault+console pair
(the plan's own illustrative `vault = "../noble-knowledge"`) must resolve
correctly not just in `paths.find_repo_root` itself, but in the real modules
that read/write under vault/console — proven here for two of them (`vault.py`
and the `runs.py` cache-dir module) so the fix isn't just paths.py moving the
gap one layer down.
"""

import os

from server import paths, runs, vault


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def _renamed_workspace(tmp_path):
    """workspace.toml naming a vault/console pair with neither literal name
    nor a shared parent — the case pre-a9 raised RepoRootError for."""
    outer = str(tmp_path / "outer")
    vault_dir = os.path.join(outer, "noble-knowledge")
    console_dir = os.path.join(outer, "actual-checkout", "console")
    os.makedirs(vault_dir)
    os.makedirs(console_dir)
    _write(os.path.join(outer, "workspace.toml"),
          'vault = "./noble-knowledge"\nconsole = "./actual-checkout/console"\n')
    anchor = paths.find_repo_root(outer)
    return anchor, vault_dir, console_dir


class TestVaultModuleHonorsRename:
    def test_list_tree_reads_the_renamed_vault_not_a_literal_knowledge_center(self, tmp_path):
        anchor, vault_dir, _console_dir = _renamed_workspace(tmp_path)
        os.makedirs(os.path.join(vault_dir, "wiki"))
        note_path = os.path.join(vault_dir, "wiki", "note.md")
        _write(note_path, "# hello\n")

        entries = vault.list_tree(anchor, "wiki")
        assert entries == [
            {"name": "note.md", "path": "wiki/note.md", "type": "file",
             "size": os.path.getsize(note_path)}
        ]

    def test_read_file_reads_from_the_renamed_vault(self, tmp_path):
        anchor, vault_dir, _console_dir = _renamed_workspace(tmp_path)
        _write(os.path.join(vault_dir, "artifact-map.md"), "# Artifact Map\n")

        assert vault.read_file(anchor, "artifact-map.md")["content"] == "# Artifact Map\n"


class TestRunsModuleHonorsRename:
    def test_runs_dir_is_under_the_renamed_console_not_a_literal_sibling(self, tmp_path):
        anchor, _vault_dir, console_dir = _renamed_workspace(tmp_path)

        d = runs.runs_dir(anchor)

        assert d == os.path.join(console_dir, ".cache", "runs")
        assert os.path.isdir(d)

    def test_create_and_get_round_trip_through_the_renamed_console(self, tmp_path):
        anchor, _vault_dir, console_dir = _renamed_workspace(tmp_path)

        rec = runs.create(anchor, ticket="T-017", role="work",
                          executor="chat", executor_id="x", backend="claude")
        got = runs.get(anchor, rec["id"])

        assert got["ticket"] == "T-017"
        assert os.path.isfile(
            os.path.join(console_dir, ".cache", "runs", rec["id"] + ".json"))
