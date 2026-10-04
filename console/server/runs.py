"""Durable Run records — tagged union of chat / job / cursor-pointer.

A Run is not a job (`jobs.py` stays verb-only) and not a chat. It *points at*
one of those so the Assistant and the inspector can watch work that started
from delegate, the board, or a harness launch (T-016).
"""

import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

from . import tomlio
from .paths import resolve_rel

RUNS_REL = os.path.join("console", ".cache", "runs")

STATES = ("queued", "running", "needs-approval", "done", "failed", "interrupted",
          "timed_out", "scheduled_retry")
#: A terminal Run is immutable (T-020 BR-1). ACTIVE is the rest: the owner can
#: still act on it, so a claim linked to one is never stale (BR-6).
TERMINAL = frozenset({"done", "failed", "interrupted", "timed_out"})
ACTIVE = frozenset(STATES) - TERMINAL
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


_REPLACE_TRIES = 25


def _write(path, record):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    # On Windows a reader that has the target open makes `os.replace` raise
    # PermissionError until it closes it (CR-28). Readers hold it for a
    # millisecond, so a short retry turns a failed write into a slower one.
    for attempt in range(_REPLACE_TRIES):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == _REPLACE_TRIES - 1:
                raise
            time.sleep(0.02)


def _read(path):
    # The other half of the same Windows race: `open` on a file mid-replace
    # raises PermissionError, and a watchdog tick must not die on it.
    for attempt in range(_REPLACE_TRIES):
        try:
            with open(path, encoding="utf-8") as fh:
                return json.load(fh)
        except PermissionError:
            if attempt == _REPLACE_TRIES - 1:
                raise
            time.sleep(0.02)


def _defaults():
    """The T-020 fields and what a record written before them reads as. Empty
    string / empty list mean "unknown" or "none yet", never zero or success
    (NFR-2). Built per call so no two reads share a mutable default."""
    return {
        "attempt": 1, "attempts": [], "failure_class": "", "failure_detail": "",
        "retry_not_before": "", "retry_due": "", "retry_of": "",
        "end_reason": "", "ended": "", "last_output_at": "",
        "liveness": {"state": "", "reason": ""},
    }


def _with_defaults(rec):
    out = _defaults()
    out.update(rec)
    return out


def create(repo_root, *, ticket="", role="work", executor="chat",
           executor_id="", backend="", state="running",
           worktree_path="", worktree_branch="", worktree_error="",
           retry_of="", retry_due=""):
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
    if retry_of:  # a manual retry: a new Run that points back (T-020 FR-18)
        record.update(retry_of=retry_of, retry_due=retry_due)
    _write(_path(repo_root, rid), record)
    return _with_defaults(record)


def get(repo_root, run_id):
    path = _path(repo_root, run_id)
    if not os.path.isfile(path):
        return None
    return _with_defaults(_read(path))


def list_runs(repo_root, ticket=None, state=""):
    out = []
    d = runs_dir(repo_root)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        rec = _with_defaults(_read(os.path.join(d, name)))
        if ticket and rec.get("ticket") != ticket:
            continue
        if state and rec.get("state") != state:
            continue
        out.append(rec)
    return out


def list_active(repo_root, known_terminal=None):
    """Runs in an ACTIVE state, parsing only what can still change.

    `known_terminal` is a set the caller keeps between calls: ids found
    terminal are added to it and never read again (a terminal Run is immutable,
    BR-1), so a steady-state watchdog tick reads active files only, not the
    whole history (T-020 NFR-7, CR-32)."""
    known = known_terminal if known_terminal is not None else set()
    out = []
    d = runs_dir(repo_root)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json") or name[:-5] in known:
            continue
        try:
            rec = _with_defaults(_read(os.path.join(d, name)))
        except (OSError, ValueError):
            continue  # mid-replace or half-written: the next tick sees it
        if rec.get("state") in TERMINAL:
            known.add(name[:-5])
        else:
            out.append(rec)
    return out


def find_active_chat_run(repo_root, chat_id):
    """The ACTIVE chat Run whose conversation is `chat_id`, or None. A chat a
    human started has no Run, so None is a normal answer, not an error."""
    found = [r for r in list_runs(repo_root)
             if r["executor"] == "chat" and r["executor_id"] == chat_id
             and r["state"] in ACTIVE]
    return max(found, key=lambda r: r["created"]) if found else None


#: Everything `update` may write. Identity and history (`id`, `ticket`, `role`,
#: `executor*`, `created`, the worktree facts) are set once by `create`.
UPDATABLE = frozenset({
    "state", "attempt", "attempts", "failure_class", "failure_detail",
    "retry_not_before", "retry_due", "retry_of", "end_reason", "ended",
    "last_output_at", "liveness",
})
DETAIL_MAX = 500
ATTEMPTS_MAX = 10
TRUNCATION_MARKER = "...[truncated]"
#: Credential shapes never stored in a Run (NFR-9): sk-/ghp_ keys, Bearer tokens.
_SECRET_RE = re.compile(r"\bsk-[A-Za-z0-9_-]{10,}|\bghp_[A-Za-z0-9]{10,}"
                        r"|\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")


def update(repo_root, run_id, **fields):
    """Change fields of a Run under its lock file, in one write (T-020 FR-2).

    The read-check-write happens while holding `<run>.json.lock`, the same
    `tomlio` primitive tickets use, so two threads (the watchdog and a human
    stop) cannot lose each other's fields. A call may set a terminal `state`
    together with its annotations (`failure_class`, `liveness`, `ended`...);
    once the record is terminal on disk every later call raises ValueError and
    writes nothing, so callers work out the annotations first and write once.
    """
    unknown = sorted(set(fields) - UPDATABLE)
    if unknown:
        raise ValueError("cannot update run field(s): %s" % ", ".join(unknown))
    if "state" in fields and fields["state"] not in STATES:
        raise ValueError("state must be one of %s" % ", ".join(STATES))
    if "failure_detail" in fields:
        detail = _SECRET_RE.sub("[redacted]", str(fields["failure_detail"] or ""))
        if len(detail) > DETAIL_MAX:
            detail = detail[:DETAIL_MAX - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER
        fields["failure_detail"] = detail
    if "attempts" in fields:
        fields["attempts"] = list(fields["attempts"])[-ATTEMPTS_MAX:]

    path = _path(repo_root, run_id)
    lock = path + ".lock"
    tomlio._acquire_lock(lock, 5.0)
    try:
        if not os.path.isfile(path):
            raise FileNotFoundError("no run %s" % run_id)
        rec = _read(path)
        if rec.get("state") in TERMINAL:
            raise ValueError("run %s is %s, a terminal state; a terminal run is immutable"
                             % (run_id, rec["state"]))
        rec.update(fields)
        rec["updated"] = _now()
        _write(path, rec)
    finally:
        tomlio._release_lock(lock)
    return _with_defaults(rec)


def set_state(repo_root, run_id, state):
    return update(repo_root, run_id, state=state)
