"""Workspace reset — wipe project-specific state, keep the template shell.

Used by `python console/kanban.py reset` (see console/README.md and
knowledge-center/wiki/reset-to-clean-slate.md). Always dry-runs first;
callers must pass apply=True to actually delete/rewrite anything.
"""

import os
import shutil

ARTIFACT_MAP_HEADER = """# Artifact Map

Index of all work artifacts. One row per ticket. Update when artifacts are created, change status, or close.

## Active

## Blocked

## Completed

## Archived

---

## Schema

`- [[{ID}-summary]] — {title} — Status — Owner — {DATE}`

## Conventions

- **IDs:** `T###` (general), `BUG-###`, `FEATURE-NAME`, `EPIC-NAME`, `PROJ-XXX`. For multi-project workspaces, prefix per project: `NA-T001`, `BE-T012`, `ML-T003`.
- **Hierarchy:** `TICKET / SLICE / PHASE-{ENTITIES|DB|API|UI} / TASK` (only when needed; most tickets stay flat).
- **Filenames:** every artifact in a ticket directory is `{ID}-{artifact}.md` (globally unique across the vault).
- **Tags** (in `{ID}-summary.md` frontmatter): `[active]`, `[blocked]`, `[completed]`, `[urgent]`, `[waiting]`.
"""

SHARED_TODOS_TOML = """[meta]
ticket = "_shared"
tracker = "todos"
"""


def plan(repo_root, *, keep_logs=False, keep_investigations=False):
    """Build the list of (kind, path) actions a reset would take. Never touches disk."""
    actions = []

    artifacts_dir = os.path.join(repo_root, "knowledge-center", "artifacts")
    if os.path.isdir(artifacts_dir):
        for name in sorted(os.listdir(artifacts_dir)):
            if name in ("_template", "_shared"):
                continue
            full = os.path.join(artifacts_dir, name)
            if os.path.isdir(full):
                actions.append(("rmtree", full))

    shared_todos = os.path.join(artifacts_dir, "_shared", "_shared-todos.toml")
    if os.path.isfile(shared_todos):
        actions.append(("write", shared_todos))

    artifact_map = os.path.join(repo_root, "knowledge-center", "artifact-map.md")
    if os.path.isfile(artifact_map):
        actions.append(("write", artifact_map))

    if not keep_investigations:
        inv_dir = os.path.join(repo_root, "knowledge-center", "investigations")
        if os.path.isdir(inv_dir):
            for name in sorted(os.listdir(inv_dir)):
                full = os.path.join(inv_dir, name)
                if os.path.isdir(full):
                    actions.append(("rmtree", full))

    if not keep_logs:
        logs_dir = os.path.join(repo_root, "knowledge-center", "logs")
        if os.path.isdir(logs_dir):
            for name in sorted(os.listdir(logs_dir)):
                if name == "author.local":
                    continue
                full = os.path.join(logs_dir, name)
                if os.path.isdir(full):
                    actions.append(("rmtree", full))

    telemetry_dir = os.path.join(repo_root, "knowledge-center", "telemetry")
    if os.path.isdir(telemetry_dir):
        for name in sorted(os.listdir(telemetry_dir)):
            if name.endswith(".jsonl"):
                actions.append(("remove", os.path.join(telemetry_dir, name)))

    cache_dir = os.path.join(repo_root, "console", ".cache")
    if os.path.isdir(cache_dir):
        for name in sorted(os.listdir(cache_dir)):
            full = os.path.join(cache_dir, name)
            actions.append(("rmtree" if os.path.isdir(full) else "remove", full))

    return actions


def run(repo_root, *, apply, keep_logs=False, keep_investigations=False):
    """Return (actions, applied). actions is the plan; applied mirrors apply."""
    actions = plan(repo_root, keep_logs=keep_logs, keep_investigations=keep_investigations)
    if apply:
        for kind, path in actions:
            if kind == "rmtree":
                shutil.rmtree(path, ignore_errors=True)
            elif kind == "remove":
                if os.path.exists(path):
                    os.remove(path)
            elif kind == "write":
                content = ARTIFACT_MAP_HEADER if path.endswith("artifact-map.md") else SHARED_TODOS_TOML
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
    return actions
