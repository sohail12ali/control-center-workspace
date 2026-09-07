"""Git worktrees — one isolated checkout per run.

## Why this comes before anything remote

Today every agent run happens in the same working tree. One run at a time, with
a human watching, that is merely untidy. The moment runs are scheduled, queued,
or triggered from a phone, it is a correctness problem: two agents editing the
same files interleave their changes, and neither the board nor the transcript
records that it happened. Nothing built on top of concurrent runs can be trusted
until they are isolated, which is why this is the first task of the phase rather
than a convenience added later.

## Safety rules, and why each one exists

- **Never create over an existing path.** Reusing a directory silently inherits
  whatever the last run left there, including a half-applied edit.
- **Never remove a worktree with uncommitted work** unless forced, and when
  refusing, say exactly what would be lost. An agent run's whole output can be
  uncommitted; deleting it on a tidy-up is unrecoverable.
- **Never guess a branch name.** The pattern comes from config, because branch
  conventions are a property of the project, not of this tool.

## What this is not

Not a git wrapper. It runs four porcelain commands and parses one of them. Any
other git operation belongs to the project's own tooling, which is what
`invoke-project-skill` exists to reach.
"""

import os
import re
import subprocess

from . import boards as boards_mod
from . import procs

DEFAULT_ROOT = os.path.join(".claude", "worktrees")
DEFAULT_BRANCH_PATTERN = "agent/{ticket}"
DEFAULT_BASE = "HEAD"

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


class WorktreeError(ValueError):
    pass


def _config(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("worktrees", {}) or {}
    return {
        "root": cfg.get("root") or DEFAULT_ROOT,
        "branch_pattern": cfg.get("branch_pattern") or DEFAULT_BRANCH_PATTERN,
        "base": cfg.get("base") or DEFAULT_BASE,
    }


def _git(repo_root, *args, check=True):
    proc = subprocess.run(
        ["git"] + list(args), cwd=repo_root,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        **procs.popen_kwargs())
    if check and proc.returncode != 0:
        raise WorktreeError("git %s failed: %s"
                            % (" ".join(args), (proc.stderr or proc.stdout).strip()))
    return proc


def _require_git_repo(repo_root):
    proc = _git(repo_root, "rev-parse", "--git-dir", check=False)
    if proc.returncode != 0:
        raise WorktreeError("%s is not a git repository" % repo_root)


def worktree_root(repo_root):
    return os.path.join(repo_root, _config(repo_root)["root"])


def path_for(repo_root, name):
    """Where a worktree named `name` lives.

    `name` is validated rather than merely joined: it reaches this from a
    ticket id, a CLI argument, or eventually an agent tool call, and
    `../../etc` would otherwise resolve to a real directory outside the repo.
    """
    if not _SAFE_SEGMENT.match(name or ""):
        raise WorktreeError(
            "invalid worktree name %r — letters, digits, dot, dash and "
            "underscore only" % name)
    return os.path.join(worktree_root(repo_root), name)


def branch_for(repo_root, name):
    return _config(repo_root)["branch_pattern"].format(ticket=name)


def list_worktrees(repo_root):
    """[{path, branch, head, is_main, managed}] from `git worktree list`.

    `managed` marks the ones under our configured root — the ones this module
    created and may remove. A worktree someone made by hand elsewhere is
    reported but never touched.
    """
    _require_git_repo(repo_root)
    out = _git(repo_root, "worktree", "list", "--porcelain").stdout
    entries, current = [], None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[9:].strip(), "branch": "", "head": "",
                       "is_main": not entries}
            entries.append(current)
        elif current is None:
            continue
        elif line.startswith("HEAD "):
            current["head"] = line[5:].strip()
        elif line.startswith("branch "):
            current["branch"] = line[7:].strip().replace("refs/heads/", "")
        elif line.strip() == "detached":
            current["branch"] = "(detached)"

    root = os.path.abspath(worktree_root(repo_root))
    for entry in entries:
        entry["managed"] = (not entry["is_main"] and
                            os.path.abspath(entry["path"]).startswith(root))
        entry["name"] = os.path.basename(entry["path"].rstrip("/\\"))
    return entries


def _find(repo_root, name):
    target = os.path.abspath(path_for(repo_root, name))
    for entry in list_worktrees(repo_root):
        if os.path.abspath(entry["path"]) == target:
            return entry
    return None


def dirty_files(repo_root, worktree_path):
    """Paths with uncommitted changes, including untracked ones.

    Untracked files count: a run that created files and did not commit them has
    produced exactly the work someone would be most upset to lose.
    """
    proc = _git(worktree_path, "status", "--porcelain", check=False)
    if proc.returncode != 0:
        return []
    return [line[3:].strip() for line in proc.stdout.splitlines() if line.strip()]


def add(repo_root, name, base=None, branch=None):
    """Create an isolated checkout for `name`. Returns its record."""
    _require_git_repo(repo_root)
    path = path_for(repo_root, name)
    if os.path.exists(path):
        raise WorktreeError(
            "%s already exists — remove it first rather than reusing whatever "
            "the last run left there" % path)

    cfg = _config(repo_root)
    branch = branch or branch_for(repo_root, name)
    base = base or cfg["base"]

    for entry in list_worktrees(repo_root):
        if entry["branch"] == branch:
            raise WorktreeError(
                "branch %r is already checked out at %s — git allows one "
                "worktree per branch" % (branch, entry["path"]))

    os.makedirs(worktree_root(repo_root), exist_ok=True)
    exists = _git(repo_root, "rev-parse", "--verify", "--quiet",
                  "refs/heads/" + branch, check=False).returncode == 0
    if exists:
        _git(repo_root, "worktree", "add", path, branch)
    else:
        _git(repo_root, "worktree", "add", "-b", branch, path, base)

    return _find(repo_root, name) or {"path": path, "branch": branch,
                                      "name": name, "managed": True}


def remove(repo_root, name, force=False):
    """Remove a managed worktree. Refuses to discard uncommitted work."""
    _require_git_repo(repo_root)
    entry = _find(repo_root, name)
    if entry is None:
        raise WorktreeError("no worktree named %r" % name)
    if not entry["managed"]:
        raise WorktreeError(
            "%s was not created here (it is outside %s) — remove it with git "
            "directly if that is really what you want"
            % (entry["path"], _config(repo_root)["root"]))

    dirty = dirty_files(repo_root, entry["path"])
    if dirty and not force:
        shown = ", ".join(dirty[:5])
        more = "" if len(dirty) <= 5 else " and %d more" % (len(dirty) - 5)
        raise WorktreeError(
            "%s has %d uncommitted change(s) (%s%s) — pass force to discard "
            "them" % (entry["path"], len(dirty), shown, more))

    args = ["worktree", "remove", entry["path"]]
    if force:
        args.append("--force")
    _git(repo_root, *args)
    return {"removed": entry["path"], "branch": entry["branch"],
            "discarded_changes": len(dirty) if force else 0}


def prune(repo_root):
    """Drop git's records of worktrees whose directories are gone."""
    _require_git_repo(repo_root)
    _git(repo_root, "worktree", "prune")
    return {"pruned": True}


def format_list(entries):
    if not entries:
        return "No worktrees."
    width = max(len(e["name"]) for e in entries)
    lines = []
    for entry in entries:
        tag = "main" if entry["is_main"] else ("managed" if entry["managed"] else "external")
        lines.append("%-*s  %-8s %-28s %s" % (
            width, entry["name"], tag, entry["branch"] or "(none)", entry["path"]))
    return "\n".join(lines)
