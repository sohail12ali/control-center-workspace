"""PR state, read via the `gh` CLI — no GitHub REST/GraphQL client, no token
storage (T-018 FR-6, decision-log a1).

Mirrors `worktrees.py`'s own `_git()` helper: shell out to an already-installed
CLI, parse exactly what is needed, and let anything unexpected come back as a
readable, non-fatal error rather than raising. `gh` manages its own
authentication outside this codebase — nothing here ever stores a credential.

## What this is not

Not a ticket-source adapter. `pr_state_for` is a read-only hint consumed by the
`pr-check` verb; it never becomes a second tracker or a write path back to
GitHub (see T-018 requirements § Out of Scope).
"""

import json
import subprocess

from . import procs

#: `gh pr view` is a porcelain call to the GitHub API, not local plumbing —
#: give it enough time for a slow network round-trip but not so much that a
#: hung process blocks an unattended `schedules.toml` run indefinitely.
_GH_TIMEOUT = 15


def _gh(repo_root, *args, check=True):
    proc = subprocess.run(
        ["gh"] + list(args), cwd=repo_root,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=_GH_TIMEOUT,
        **procs.popen_kwargs())
    if check and proc.returncode != 0:
        raise RuntimeError("gh %s failed: %s"
                           % (" ".join(args), (proc.stderr or proc.stdout).strip()))
    return proc


#: `gh pr view --json state` reports one of these three (GitHub's own
#: vocabulary); mapped to this module's lowercase form so a caller never has
#: to know GitHub's casing convention.
_STATE_MAP = {"OPEN": "open", "MERGED": "merged", "CLOSED": "closed"}


def pr_state_for(repo_root, branch):
    """`{"pr_url": ..., "pr_state": ..., "error": ...}` for `branch`'s PR.

    Never raises (FR-6, AC6): a missing `gh` binary, an unauthenticated `gh`,
    a `gh` call that hangs past `_GH_TIMEOUT`, no PR for the branch, and an
    unparseable response are all reported back as a result dict rather than
    an exception — Run creation and the `pr-check` verb (schedulable via
    `schedules.toml` for unattended runs) must be able to call this
    unconditionally. `pr_state` is
    `""` when nothing could be determined (check `error` for why), `"none"`
    when `gh` positively reports no PR exists for the branch, and one of
    open/merged/closed otherwise.
    """
    branch = (branch or "").strip()
    if not branch:
        return {"pr_url": "", "pr_state": "", "error": "no branch to query"}

    try:
        proc = _gh(repo_root, "pr", "view", branch, "--json", "state,url", check=False)
    except FileNotFoundError:
        return {"pr_url": "", "pr_state": "", "error": "gh CLI is not installed"}
    except subprocess.TimeoutExpired:
        return {"pr_url": "", "pr_state": "",
                "error": "gh timed out after %ds" % _GH_TIMEOUT}
    except OSError as exc:
        return {"pr_url": "", "pr_state": "", "error": "could not run gh: %s" % exc}

    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()

    if proc.returncode != 0:
        low = (err or out).lower()
        if "no pull requests found" in low or "no default branch" in low:
            return {"pr_url": "", "pr_state": "none", "error": ""}
        if ("not logged into" in low or "gh auth login" in low
                or "authentication" in low):
            return {"pr_url": "", "pr_state": "", "error": "gh is not authenticated"}
        if "command not found" in low or "not recognized" in low or "is not recognized" in low:
            return {"pr_url": "", "pr_state": "", "error": "gh CLI is not installed"}
        return {"pr_url": "", "pr_state": "", "error": err or out or "gh pr view failed"}

    try:
        data = json.loads(out)
    except ValueError:
        return {"pr_url": "", "pr_state": "",
                "error": "unrecognised gh output: %r" % out[:200]}

    state = _STATE_MAP.get(str(data.get("state") or "").upper(), "")
    return {"pr_url": data.get("url") or "", "pr_state": state, "error": ""}
