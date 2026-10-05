"""Is this checkout a blank template, and would a commit publish a secret?

`reset.plan` is the list of workspace content. `instance_rows` reports that
list and skips a rewrite whose file is already the empty scaffold, so a
checkout that only has `_template/` reads as blank.

Those paths stay ordinary git files. A fork commits its own tickets, logs,
and investigations. This module never ignores them.

Secrets are a separate list. The pre-commit hook fails when one is staged.
CI fails when one is tracked. A ticket file fails neither.
"""

import fnmatch
import os
import subprocess

from . import agent_tools
from . import procs
from . import reset as reset_mod

#: Machine files whose basenames do not match `agent_tools.SECRET_PATTERNS`.
EXTRA_SECRET_RELS = (
    "console/config/notify-local.toml",
    ".claude/settings.local.json",
)

CACHE_PREFIX = "console/.cache"

HOOKS_PATH = ".githooks"
HOOKS_COMMAND = "git config core.hooksPath .githooks"

NOTE = (
    "Clean deletes these files from this checkout only. The branch others "
    "clone still has them until you commit the deletions. Older commits keep "
    "them. A fork commits its own tickets on its own branch."
)


def _norm(rel):
    rel = (rel or "").replace("\\", "/").strip()
    if rel.startswith("./"):
        rel = rel[2:]
    return rel.lstrip("/")


def is_secret_path(rel):
    """True for a repo-relative path that must not be committed."""
    rel = _norm(rel)
    if not rel:
        return False
    base = rel.rsplit("/", 1)[-1]
    for pat in agent_tools.SECRET_PATTERNS:
        if fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(rel, pat):
            return True
    if rel in EXTRA_SECRET_RELS:
        return True
    return rel == CACHE_PREFIX or rel.startswith(CACHE_PREFIX + "/")


def _read(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read().replace("\r\n", "\n")
    except OSError:
        return None


def _is_scaffold(path):
    """A rewrite target that already holds the empty template."""
    name = os.path.basename(path)
    if name == "artifact-map.md":
        return _read(path) == reset_mod.ARTIFACT_MAP_HEADER
    if name == "_shared-todos.toml":
        return _read(path) == reset_mod.SHARED_TODOS_TOML
    return False


def instance_rows(repo_root):
    """Workspace content still in the working tree.

    Same paths `reset.plan` would delete or rewrite, except a rewrite that
    already matches the empty scaffold.
    """
    rows = []
    for kind, path in reset_mod.plan(repo_root):
        if kind == "write" and _is_scaffold(path):
            continue
        rel = _norm(os.path.relpath(path, repo_root))
        # The clean records itself under console/.cache/audit after the wipe.
        # That line is gitignored machine evidence, not project content, and
        # counting it would make a checkout look dirty the moment it was cleaned.
        if rel == "console/.cache/audit" or rel.startswith("console/.cache/audit/"):
            continue
        rows.append({
            "action": "rewrite" if kind == "write" else "delete",
            "path": rel,
        })
    return rows


def _git(repo_root, args):
    """`(returncode, stdout)` or `(None, "")` when git cannot be run."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **procs.popen_kwargs(),
        )
    except OSError:
        return None, ""
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def _git_paths(repo_root, args):
    code, out = _git(repo_root, args)
    if code != 0:
        return None
    return [_norm(part) for part in out.split("\0") if part.strip()]


def _inside_work_tree(repo_root):
    code, out = _git(repo_root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


def staged_secrets(repo_root):
    """Secret paths in the index diff for the commit about to be made.

    A deletion is not listed: removing a secret is the point of the gate.
    """
    paths = _git_paths(
        repo_root,
        ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
    )
    if paths is None:
        return []
    return [{"path": rel, "where": "staged"} for rel in paths if is_secret_path(rel)]


def tracked_secrets(repo_root):
    """Secret paths in the index, which is what a clone of HEAD would contain.

    A path that is also part of the staged diff is marked `staged`.
    """
    indexed = _git_paths(repo_root, ["ls-files", "-z"])
    if indexed is None:
        return []
    staged = {row["path"] for row in staged_secrets(repo_root)}
    return [
        {"path": rel, "where": "staged" if rel in staged else "tracked"}
        for rel in indexed
        if is_secret_path(rel)
    ]


def hook_status(repo_root):
    """Whether this checkout opted into `.githooks`. Never writes git config."""
    command = HOOKS_COMMAND
    if not _inside_work_tree(repo_root):
        return {
            "active": False,
            "path": "",
            "command": command,
            "detail": "not a git checkout",
        }
    code, out = _git(repo_root, ["config", "--get", "core.hooksPath"])
    got = out.strip() if code == 0 else ""
    if not got:
        return {
            "active": False,
            "path": "",
            "command": command,
            "detail": "core.hooksPath is unset, so the secret check does not run on commit",
        }
    full = got if os.path.isabs(got) else os.path.normpath(os.path.join(repo_root, got))
    want = os.path.normpath(os.path.join(repo_root, HOOKS_PATH))
    active = os.path.normcase(full) == os.path.normcase(want)
    return {
        "active": active,
        "path": got,
        "command": command,
        "detail": (
            "the secret check runs before each commit"
            if active else
            "core.hooksPath points somewhere other than .githooks"
        ),
    }


def report(repo_root):
    """The template question: leftover workspace content, plus any secret in git."""
    instance = instance_rows(repo_root)
    secrets = tracked_secrets(repo_root)
    return {
        "ok": not instance and not secrets,
        "blank": not instance,
        "instance": instance,
        "secrets": secrets,
        "hook": hook_status(repo_root),
        "note": NOTE,
        "scope": "template",
    }


def secret_report(repo_root, *, staged_only=False):
    """The commit gate. Tickets are not part of this answer."""
    secrets = staged_secrets(repo_root) if staged_only else tracked_secrets(repo_root)
    return {
        "ok": not secrets,
        "secrets": secrets,
        "scope": "staged" if staged_only else "tracked",
    }


def format_report(payload):
    """Plain text for the CLI. JSON callers print the dict themselves."""
    scope = payload.get("scope")
    secrets = payload.get("secrets") or []
    lines = []
    if scope == "staged":
        lines.append("staged secrets:" if secrets else "staged secrets: none")
    elif scope == "tracked":
        lines.append("secrets:" if secrets else "secrets: none tracked or staged")
    else:
        if payload.get("blank"):
            lines.append("template: blank")
        else:
            lines.append("template: workspace content is still in this checkout")
            for row in payload.get("instance") or []:
                lines.append("  %s  %s" % (row["action"], row["path"]))
        lines.append("secrets:" if secrets else "secrets: none tracked or staged")
    for row in secrets:
        lines.append("  %s  %s" % (row["where"], row["path"]))
    hook = payload.get("hook")
    if hook:
        state = "on" if hook.get("active") else "off"
        lines.append("commit hook: %s — %s" % (state, hook.get("detail") or ""))
        if not hook.get("active"):
            lines.append(hook.get("command") or HOOKS_COMMAND)
    if payload.get("note") and scope == "template":
        lines.append(payload["note"])
    return "\n".join(lines)
