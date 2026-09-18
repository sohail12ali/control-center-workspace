"""Workspace-root resolution shared by every console module.

A "repo root" is a directory that has both knowledge-center/ and console/
as immediate children — the same umbrella-workspace shape project-layout
already documents for this template.

T-017 FR-6/2c: a `workspace.toml` (see `workspace_config.py`) is an optional,
alternative way to name where `vault`/`console` live, for a split-repo
layout where they are not plain siblings. It is tried FIRST on every search
candidate, but only ever *found*, never *required* — a candidate with no
`workspace.toml` anywhere above it falls straight through to the sibling-folder
check that already existed, unchanged (decision-log a7: 100% backward
compatible, every pre-T-017 checkout has no `workspace.toml` and must resolve
exactly as before).

T-017 decision-log a9 closes the narrowing a7 originally accepted: a
`workspace.toml` naming a genuinely *renamed* vault/console pair (e.g.
`vault = "../noble-knowledge"`) now resolves end-to-end too, via
`vault_dir`/`console_dir`/`resolve_rel` below, rather than raising
`RepoRootError`. Every module in this package that used to join
`repo_root + "knowledge-center"` / `repo_root + "console"` literally should
go through one of those three instead of `os.path.join` directly.
"""

import os

from . import workspace_config


class RepoRootError(RuntimeError):
    pass


def _is_repo_root(path):
    return os.path.isdir(os.path.join(path, "knowledge-center")) and os.path.isdir(
        os.path.join(path, "console")
    )


def _repo_root_from_workspace(resolved):
    """Reduce a resolved `workspace.toml` to the single anchor string
    `find_repo_root` returns, that `vault_dir`/`console_dir` (below) can
    always re-resolve back to the *real* `vault`/`console` directories from.

    Two shapes:
    - The common one: `vault`/`console` are still literally named
      `knowledge-center`/`console` and share one parent — return that parent,
      unchanged from pre-a9 behavior, so every existing literal
      `os.path.join(repo_root, "knowledge-center")` call site (not yet
      migrated to `vault_dir`) still lands correctly.
    - The renamed/relocated case (decision-log a9): no shared parent reduces
      the pair to a literal `knowledge-center`/`console` sibling layout.
      Return `resolved["root"]` instead — the directory the `workspace.toml`
      itself lives in. `vault_dir`/`console_dir` re-run
      `workspace_config.resolve` starting from that exact directory, which
      finds the same `workspace.toml` again (it's right there) and returns
      the real, renamed `vault`/`console` paths. This anchor is only ever
      consumed through that re-resolution, never joined against a literal
      folder name, so an arbitrary rename is safe here.
    """
    vault = os.path.normpath(resolved["vault"])
    console = os.path.normpath(resolved["console"])
    if (os.path.basename(vault) == "knowledge-center"
            and os.path.basename(console) == "console"
            and os.path.dirname(vault) == os.path.dirname(console)):
        return os.path.dirname(console)
    return resolved["root"]


def find_repo_root(start=None):
    """Search upward for a repo root, trying `start`/cwd first, then the
    console/ package's own location (so the CLI works regardless of the
    caller's current directory).

    For each candidate, a `workspace.toml` found anywhere above it (T-017 2c)
    is tried first via `workspace_config.resolve`, which itself returns
    `None` (never raises) when no `workspace.toml` exists at all — the
    ordinary case, which falls straight through to the pre-existing
    sibling-folder walk with no behavior change (decision-log a7). A
    `workspace.toml` that *does* exist always resolves to an anchor now
    (decision-log a9) — see `_repo_root_from_workspace` for the two shapes;
    neither raises. Callers that need the actual `vault`/`console`
    directories (not just an anchor to pass around) should use `vault_dir`/
    `console_dir`, not join this return value against a literal folder name.
    """
    candidates = []
    if start:
        candidates.append(os.path.abspath(start))
    candidates.append(os.getcwd())
    candidates.append(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for candidate in candidates:
        ws = workspace_config.resolve(candidate)
        if ws is not None:
            return _repo_root_from_workspace(ws)
        path = candidate
        while True:
            if _is_repo_root(path):
                return path
            parent = os.path.dirname(path)
            if parent == path:
                break
            path = parent
    raise RepoRootError(
        "could not find a workspace root (needs both knowledge-center/ and console/ as siblings, "
        "or a workspace.toml naming them)"
    )


def vault_dir(repo_root=None):
    """The real, on-disk vault directory for `repo_root` (default: the
    result of `find_repo_root()`), honoring a `workspace.toml` that renames
    or relocates it (decision-log a9). Falls back to the pre-T-017 literal
    `repo_root/knowledge-center` when no `workspace.toml` governs `repo_root`
    — a true no-op for every checkout that predates this feature."""
    root = repo_root if repo_root is not None else find_repo_root()
    ws = workspace_config.resolve(root)
    if ws is not None:
        return ws["vault"]
    return os.path.join(root, "knowledge-center")


def console_dir(repo_root=None):
    """The real, on-disk console directory for `repo_root` — see `vault_dir`
    (same reasoning, mirrored for `console`)."""
    root = repo_root if repo_root is not None else find_repo_root()
    ws = workspace_config.resolve(root)
    if ws is not None:
        return ws["console"]
    return os.path.join(root, "console")


def resolve_rel(repo_root, rel):
    """Join a `rel` path whose first component is the literal, historical
    `"knowledge-center"` or `"console"` folder name (the shape almost every
    `*_REL` constant in this package is written in) against the *real*
    vault/console directory for `repo_root`, honoring a renaming
    `workspace.toml` (decision-log a9). Any other first component — there
    shouldn't be one, but this is defensive — falls back to a plain literal
    join against `repo_root`, matching pre-a9 behavior exactly.
    """
    normalized = rel.replace("/", os.sep).replace("\\", os.sep)
    head, _, rest = normalized.partition(os.sep)
    if head == "knowledge-center":
        base = vault_dir(repo_root)
    elif head == "console":
        base = console_dir(repo_root)
    else:
        return os.path.join(repo_root, rel)
    return os.path.join(base, rest) if rest else base


def artifacts_dir(repo_root, config):
    return resolve_rel(repo_root, config["general"]["data_root"])


def ticket_dir(repo_root, config, ticket_id):
    return os.path.join(artifacts_dir(repo_root, config), ticket_id)
