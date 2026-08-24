"""Workspace-root resolution shared by every console module.

A "repo root" is a directory that has both knowledge-center/ and console/
as immediate children — the same umbrella-workspace shape project-layout
already documents for this template.
"""

import os


class RepoRootError(RuntimeError):
    pass


def _is_repo_root(path):
    return os.path.isdir(os.path.join(path, "knowledge-center")) and os.path.isdir(
        os.path.join(path, "console")
    )


def find_repo_root(start=None):
    """Search upward for a repo root, trying `start`/cwd first, then the
    console/ package's own location (so the CLI works regardless of the
    caller's current directory)."""
    candidates = []
    if start:
        candidates.append(os.path.abspath(start))
    candidates.append(os.getcwd())
    candidates.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for candidate in candidates:
        path = candidate
        while True:
            if _is_repo_root(path):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
    raise RepoRootError(
        "could not find a workspace root (needs both knowledge-center/ and console/ as siblings)"
    )


def artifacts_dir(repo_root, config):
    return os.path.join(repo_root, config["general"]["data_root"])


def ticket_dir(repo_root, config, ticket_id):
    return os.path.join(artifacts_dir(repo_root, config), ticket_id)
