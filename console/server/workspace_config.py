"""`workspace.toml` schema + parser (T-017 FR-6, decision-log a7).

An optional, fully backward-compatible alternative to the sibling-folder
`knowledge-center/` + `console/` layout `paths._is_repo_root` checks for
today. Its absence must reproduce today's behaviour exactly — see a7 — so
this module only reads and validates a `workspace.toml` when one exists; it
never requires one.

Schema/parsing only, in this phase (Phase 1 / 1c). Wiring this into
`paths.find_repo_root` (the upward-search branch, with a fallback to the
existing sibling-folder check) is Phase 2's 2c.

Shape (`name` and `projects` optional; `vault`/`console` required):

    name = "my-workspace"
    vault = "./knowledge-center"
    console = "./console"

    [[projects]]
    name = "sub-project"
    path = "./sub-project"

`vault`/`console` are resolved relative to the directory the `workspace.toml`
itself lives in, not the caller's cwd.
"""

import os

from . import tomlio

FILENAME = "workspace.toml"

#: Keys a valid workspace.toml must declare. `name` and `projects` are
#: optional decoration; without a resolvable vault/console pair there is
#: nothing for `find_repo_root` (Phase 2) to point at.
REQUIRED_KEYS = ("vault", "console")


class WorkspaceConfigError(ValueError):
    """A `workspace.toml` exists but names a path that isn't there, or is
    missing a required key. Distinct from `FileNotFoundError` (no
    workspace.toml at all — the normal, unremarkable case per a7) so a
    caller can tell "not using this feature" apart from "using it wrong",
    and the error names exactly which path is missing (Edge Case §8)."""


def find(start):
    """Search upward from `start` for a `workspace.toml`. Returns its path,
    or None if none is found by the filesystem root — mirrors
    `paths.find_repo_root`'s own upward walk, but does not raise: an absent
    `workspace.toml` is the default case, not an error."""
    path = os.path.abspath(start)
    while True:
        candidate = os.path.join(path, FILENAME)
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


def parse(path):
    """Load and validate one `workspace.toml` at `path`.

    Raises `WorkspaceConfigError` naming exactly what's wrong — a missing key,
    or a `vault`/`console` that doesn't resolve to a real directory — rather
    than a bare `FileNotFoundError` surfacing deep in an unrelated module
    (Edge Case §8).
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    data = tomlio.load(path)
    root_dir = os.path.dirname(os.path.abspath(path))

    missing = [k for k in REQUIRED_KEYS if not data.get(k)]
    if missing:
        raise WorkspaceConfigError(
            "%s is missing required key(s): %s" % (path, ", ".join(missing)))

    def _resolve(rel, key):
        resolved = os.path.normpath(os.path.join(root_dir, rel))
        if not os.path.isdir(resolved):
            raise WorkspaceConfigError(
                "%s names %s=%r, which does not exist (resolved to %s)"
                % (path, key, rel, resolved))
        return resolved

    vault_path = _resolve(data["vault"], "vault")
    console_path = _resolve(data["console"], "console")

    projects = []
    for proj in data.get("projects", []):
        rel = proj.get("path", "")
        entry = {"name": proj.get("name", ""), "path": rel}
        if rel:
            entry["resolved_path"] = os.path.normpath(os.path.join(root_dir, rel))
        projects.append(entry)

    return {
        "name": data.get("name", ""),
        "root": root_dir,
        "vault": vault_path,
        "console": console_path,
        "projects": projects,
    }


def resolve(start):
    """Convenience: find + parse in one call. Returns None (not an error) if
    no `workspace.toml` exists between `start` and the filesystem root — the
    caller (Phase 2's `find_repo_root`) falls back to the sibling-folder
    check in that case."""
    found = find(start)
    if found is None:
        return None
    return parse(found)
