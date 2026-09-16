"""Durable Run records — tagged union of chat / job / cursor-pointer.

A Run is not a job (`jobs.py` stays verb-only) and not a chat. It *points at*
one of those so the Assistant and the inspector can watch work that started
from delegate, the board, or a harness launch (T-016).
"""

import json
import os
import uuid
from datetime import datetime, timezone

from .paths import resolve_rel

RUNS_REL = os.path.join("console", ".cache", "runs")

STATES = ("queued", "running", "needs-approval", "done", "failed", "interrupted")
EXECUTORS = ("chat", "job", "cursor")
ROLES = ("work", "analyst", "planner", "builder", "verifier", "fixer",
         "harness", "deployer", "assistant")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def runs_dir(repo_root):
    d = resolve_rel(repo_root, RUNS_REL)
    os.makedirs(d, exist_ok=True)
    return d


def _path(repo_root, run_id):
    return os.path.join(runs_dir(repo_root), run_id + ".json")


def _write(path, record):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def create(repo_root, *, ticket="", role="work", executor="chat",
           executor_id="", backend="", state="running",
           worktree_path="", worktree_branch="", worktree_error=""):
    """`worktree_path`/`worktree_branch`/`worktree_error` (T-018 FR-1..FR-3,
    decision-log a2) record where THIS Run's isolated checkout lives — fixed
    at the moment the Run started, unlike `ticket.toml`'s `branch` which is
    durable across every Run against the ticket. All three default to `""`
    so a Run created without them (every pre-T-018 caller) round-trips
    unchanged; a ticketless Run leaves them empty rather than "shared tree" —
    that display string is the inspector's job (verb_handlers._enrich_run),
    not a fact this record stores."""
    if executor not in EXECUTORS:
        raise ValueError("executor must be one of %s" % ", ".join(EXECUTORS))
    if state not in STATES:
        raise ValueError("state must be one of %s" % ", ".join(STATES))
    if role and role not in ROLES:
        raise ValueError("role must be one of %s" % ", ".join(ROLES))
    rid = uuid.uuid4().hex[:12]
    stamp = _now()
    record = {
        "id": rid,
        "ticket": ticket or "",
        "role": role or "work",
        "executor": executor,
        "executor_id": executor_id or "",
        "backend": backend or "",
        "state": state,
        "created": stamp,
        "updated": stamp,
        "worktree_path": worktree_path or "",
        "worktree_branch": worktree_branch or "",
        "worktree_error": worktree_error or "",
    }
    _write(_path(repo_root, rid), record)
    return record


def get(repo_root, run_id):
    path = _path(repo_root, run_id)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def list_runs(repo_root, ticket=None, state=""):
    out = []
    d = runs_dir(repo_root)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(d, name)
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
        if ticket and rec.get("ticket") != ticket:
            continue
        if state and rec.get("state") != state:
            continue
        out.append(rec)
    return out


def set_state(repo_root, run_id, state):
    if state not in STATES:
        raise ValueError("state must be one of %s" % ", ".join(STATES))
    rec = get(repo_root, run_id)
    if rec is None:
        raise FileNotFoundError("no run %s" % run_id)
    rec["state"] = state
    rec["updated"] = _now()
    _write(_path(repo_root, run_id), rec)
    return rec
