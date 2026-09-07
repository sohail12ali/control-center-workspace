"""Who asked the console to do what, and from where.

## Why, given the tailnet already authenticates

Authentication answers "may this request happen". It does not answer "what
happened, and was it me". Once the board is reachable from a phone, a laptop and
whatever else joins the tailnet, those become different questions — and the
second one is the one you ask at the worst possible moment, usually about a run
you do not remember starting.

So this records the small set of things that *start work or change state*:
starting a chat, running or queuing a verb, answering an approval. Not reads.
An audit log that records every board poll is one nobody scrolls through, and a
log nobody reads is not an audit.

## Local and gitignored

Records live under `console/.cache/audit/` by default. They carry client
addresses, which are a fact about your network rather than about the project,
and committing them to a template other people clone would be a strange thing
to do. This is a log of what happened on this machine.

## Append-only, never fatal

One JSON object per line, one file per month. A write that fails is dropped
rather than raised: the audit trail is evidence about the work, and evidence
that can abort the work is worse than a gap in the evidence.
"""

import json
import os
import threading
from datetime import datetime, timezone

from . import boards as boards_mod

DEFAULT_DIR = os.path.join("console", ".cache", "audit")

_lock = threading.Lock()

#: Actions worth a line. Anything that starts work or changes state; nothing
#: that merely looks at it.
ACTIONS = ("chat.start", "chat.stop", "verb.run", "verb.submit",
           "job.cancel", "approval.decide", "schedule.fire",
           # An outbound call made with the workspace's credentials. Reading
           # the cached catalogue is a read and is not recorded; re-fetching
           # leaves this machine, which is the line everything else here draws.
           "models.refresh",
           # Inbound Telegram. `rejected` is the more important of the two:
           # a bot token addresses a public endpoint, so a stranger probing it
           # is a thing that happens, and this is the only place it is visible.
           "telegram.command", "telegram.rejected",
           # Both quiet the channel or prove it works; neither can widen it.
           "notify.prefs", "notify.test",
           # T-004: the Assistant's own mutating calls — one chat, a dispatch
           # table, and a settings file, audited the same way everything else
           # here is (BR-2).
           "assistant.say", "assistant.kickoff", "assistant.remember",
           "assistant.settings", "assistant.persona_truncated")


def audit_dir(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("audit", {}) or {}
    return os.path.join(repo_root, cfg.get("dir") or DEFAULT_DIR)


def enabled(repo_root):
    cfg = boards_mod.load_console_config(repo_root).get("audit", {}) or {}
    return bool(cfg.get("enabled", True))


def actor_of(req):
    """A short description of who is asking, from the request.

    Best-effort by design. Behind a tailnet the peer address IS the identity in
    any practical sense, and inventing a richer one from headers a client
    controls would look more authoritative than it is.
    """
    if req is None:
        return {"addr": "local", "agent": ""}
    addr = getattr(req, "client_addr", "") or ""
    agent = getattr(req, "user_agent", "") or ""
    return {"addr": addr or "local", "agent": agent[:120]}


def record(repo_root, action, *, actor=None, target="", detail=None,
           outcome="ok"):
    """Append one line. Returns the record, or None if it could not be written."""
    if not enabled(repo_root):
        return None
    now = datetime.now(timezone.utc)
    entry = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "action": action,
        "actor": actor or {"addr": "local", "agent": ""},
        "target": target or "",
        "detail": detail or {},
        "outcome": outcome,
    }
    try:
        folder = audit_dir(repo_root)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, now.strftime("%Y-%m") + ".jsonl")
        line = json.dumps(entry, separators=(",", ":"), default=str) + "\n"
        with _lock:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line)
    except OSError:
        # Evidence that can abort the work is worse than a gap in the evidence.
        return None
    return entry


def read(repo_root, limit=200, action=None, since=None):
    """Recent records, newest first. A corrupt line is skipped, not fatal.

    Timestamps have one-second resolution, and bursts within a second are
    normal rather than exotic — a verb run records twice, a chat start is
    followed immediately by its first approval. Sorting on `ts` alone leaves
    those ties to the sort's stability, which preserves the order they were
    READ in, i.e. exactly backwards.

    So files are walked oldest-first and each line is numbered as it is read.
    That counter is chronological within a file by construction (the log is
    append-only) and across files by the month in the filename, which makes it
    a correct tiebreaker without changing the record format or reinterpreting
    logs already on disk.
    """
    folder = audit_dir(repo_root)
    if not os.path.isdir(folder):
        return []
    out = []
    order = 0
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".jsonl"):
            continue
        with open(os.path.join(folder, name), "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                order += 1
                if action and entry.get("action") != action:
                    continue
                if since and entry.get("ts", "") < since:
                    continue
                out.append((entry.get("ts", ""), order, entry))
    out.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [entry for _ts, _order, entry in out[:limit]]


def format_list(rows):
    if not rows:
        return "No audit records."
    lines = ["%-20s %-16s %-20s %-24s %s"
             % ("WHEN", "ACTION", "ACTOR", "TARGET", "OUTCOME")]
    for row in rows:
        lines.append("%-20s %-16s %-20s %-24s %s" % (
            row.get("ts", ""), row.get("action", ""),
            (row.get("actor") or {}).get("addr", ""),
            row.get("target", "") or "-", row.get("outcome", "")))
    return "\n".join(lines)
