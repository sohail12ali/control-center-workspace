"""T-004: the Assistant's own local, ephemeral state.

Three primitives, all under `console/.cache/assistant/` (gitignored —
`.gitignore:67` covers the whole `console/.cache/` tree already, so nothing
new is needed there):

    session.json   which live chat is "the" Assistant chat right now — sid,
                   backend, model, created/updated timestamps.
    memory.md      a small, capped, free-text fact store the `remember`
                   fast command/verb appends to. Re-injected into every new
                   session's `extra` context (see `assistant_feature.py`).
    last-reply     plain text, overwritten each completed turn — the thing a
                   future voice bridge (T-005/T-006) reads to speak or show
                   "what did it just say" without replaying the transcript.

## Why files, not a database

One user, one process, one assistant chat at a time — the entire point of
`console/.cache/` for every other module that already uses it (agent-chats,
telemetry, audit). A locking library would be solving a concurrency problem
this ticket does not have (BR-4's NFR: single-writer-per-process).

## Why memory is capped and guarded

`memory.md` is plain text, and it gets re-read into every future session's
system prompt (FR-4) — so it must never grow without bound (a slow prompt-
budget leak) and must never carry something that looks like a credential
(the `remember-secret-guard` decision). Both are enforced here, once, so
every caller (the `remember` verb, the fast-command row, `assistant_feature`'s
`memory` route) gets the same guarantee for free.
"""

import os
import re
import time

CACHE_REL = os.path.join("console", ".cache", "assistant")

SESSION_FILE = "session.json"
MEMORY_FILE = "memory.md"
LAST_REPLY_FILE = "last-reply.txt"

#: `memory.md`'s hard cap, chars. Re-injected into every session's prompt
#: budget (FR-4's ≤1,500 share), so unbounded growth here is a slow leak into
#: every future turn's cost, not just a local disk-space concern.
MEMORY_CAP = 1500

#: Secret-shaped fact patterns (`remember-secret-guard`). Cheap and
#: deliberately conservative: a false positive just means "ask a human to
#: store that one," which costs nothing on a single-user local tool.
_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN"),
    re.compile(r"\bsk-ant-[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    re.compile(r"\bghp_[A-Za-z0-9]{10,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}"),
    # A bare KEY=value line, the shape of a pasted .env entry.
    re.compile(r"(?m)^[A-Z][A-Z0-9_]*\s*=\s*\S+$"),
)


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def cache_dir(repo_root):
    d = os.path.join(repo_root, CACHE_REL)
    os.makedirs(d, exist_ok=True)
    return d


def _path(repo_root, name):
    return os.path.join(cache_dir(repo_root), name)


# -- session pointer ---------------------------------------------------------

def read_session(repo_root):
    """The current pointer, or None if the Assistant has never run."""
    path = _path(repo_root, SESSION_FILE)
    if not os.path.isfile(path):
        return None
    import json
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        # A corrupt pointer must not wedge every future `say` — treat it as
        # absent, exactly like a first run, and let write_session replace it.
        return None


def write_session(repo_root, *, sid, backend, model=""):
    """Create or overwrite the pointer. `created_at` survives an overwrite of
    the same sid; a new sid gets a fresh one."""
    import json
    existing = read_session(repo_root)
    created_at = existing.get("created_at") if existing and existing.get("sid") == sid else _now()
    record = {
        "sid": sid, "backend": backend, "model": model,
        "created_at": created_at or _now(), "updated_at": _now(),
    }
    path = _path(repo_root, SESSION_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    return record


def clear_session(repo_root):
    """Forget which chat was "the" Assistant chat.

    Used by the `new chat` fast command. Deleting the pointer rather than
    writing an empty one keeps `read_session`'s single "absent" case — a
    first run and a deliberate reset then take exactly the same code path.
    """
    path = _path(repo_root, SESSION_FILE)
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False


# -- memory --------------------------------------------------------------

def secret_shaped(text):
    """Does `text` look like a credential rather than a fact worth keeping?"""
    return any(p.search(text) for p in _SECRET_PATTERNS)


def read_memory(repo_root):
    path = _path(repo_root, MEMORY_FILE)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def remember(repo_root, fact):
    """Append `fact` to `memory.md`, capped at MEMORY_CAP chars, oldest-first
    trim. Declines (never appends, never raises) a secret-shaped fact."""
    fact = (fact or "").strip()
    if not fact:
        return {"ok": False, "reason": "nothing to remember"}
    if secret_shaped(fact):
        return {"ok": False,
                "reason": "that looks like a credential, not a fact — "
                          "declined so it never lands in memory.md"}

    current = read_memory(repo_root)
    line = fact if not current else "\n" + fact
    combined = current + line
    if len(combined) > MEMORY_CAP:
        # Oldest-first trim: drop from the FRONT so the newest fact (the one
        # just asked for) is always the one that survives.
        combined = combined[-MEMORY_CAP:]
        # Don't leave a fragment of a line dangling at the front.
        nl = combined.find("\n")
        if nl != -1:
            combined = combined[nl + 1:]

    path = _path(repo_root, MEMORY_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(combined)
    return {"ok": True, "chars": len(combined)}


# -- last reply ------------------------------------------------------------

def write_last_reply(repo_root, text):
    """Overwritten every completed turn — never grows."""
    path = _path(repo_root, LAST_REPLY_FILE)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text or "")


def read_last_reply(repo_root):
    path = _path(repo_root, LAST_REPLY_FILE)
    if not os.path.isfile(path):
        return ""
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()
