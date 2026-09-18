"""Session stop-hook check (T-017 FR-10, decision-log — Phase 4 slice 4a).

The stop-hook's job: at session end, remind an agent it still holds a
claimed-but-stale ticket (claimed, but no comment/move recorded since). It is
wired from `.claude/hooks/console-stop-reminder.sh` via the `stop-hook check`
CLI subcommand — this module holds the logic so it is unit-testable without a
real Claude Code session.

## Identity

There is no existing per-session "agent id" concept in this codebase distinct
from the `log-work` skill's own `knowledge-center/logs/author.local` (line 2:
slug) — the one identity file this workspace already has. Reusing it here
(rather than inventing a second identity convention) is the CANONICAL-
consistent choice; `--agent` still overrides it for a caller that already
knows its own claim identity (e.g. `claim`'s own `agent=` value).

## "No update since claim"

`claimed_at` (set by `tickets.set_claim`, see `backends/vault_backend.py`) is
a plain `date.today().isoformat()` string. `ticket.toml`'s own `updated`
field and a `comments` tracker item's `posted_on` are both later-or-equal by
construction — claiming itself stamps `updated` to the same day — so "has
this been touched since the claim" is: `updated` moved to a *later* string
than `claimed_at`, or a comment's `posted_on` sorts later than `claimed_at`.
Plain string comparison is correct here even between a bare date and a full
`...T00:00:00Z` timestamp: same day, full timestamp is a longer string with
the date as a strict prefix, and Python's lexicographic `>` ranks the longer
string above its own prefix — so a same-day comment still counts as "after".
"""

import os

from . import tickets as tickets_mod
from . import trackers as trackers_mod
from .paths import find_repo_root, resolve_rel

AUTHOR_LOCAL = os.path.join("knowledge-center", "logs", "author.local")


def resolve_agent(repo_root=None, override=""):
    """The identity to check claims for. `override` (e.g. `--agent`) wins;
    otherwise `author.local`'s slug line; otherwise "" (nothing to check —
    never an error, per the hook's own never-crash contract)."""
    override = (override or "").strip()
    if override:
        return override
    repo_root = repo_root or find_repo_root()
    path = resolve_rel(repo_root, AUTHOR_LOCAL)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh.readlines()]
    except OSError:
        return ""
    if len(lines) >= 2 and lines[1]:
        return lines[1]
    return ""


def _has_update_since_claim(repo_root, ticket):
    claimed_at = ticket.get("claimed_at") or ""
    if not claimed_at:
        return True
    if (ticket.get("updated") or "") > claimed_at:
        return True
    for item in trackers_mod.list_items(repo_root, ticket["id"], "comments"):
        if (item.get("posted_on") or "") > claimed_at:
            return True
    return False


def stale_claims(repo_root=None, agent=""):
    """Tickets `agent` still holds claimed with no update recorded since.
    Best-effort and never raises: a stop-hook must never crash session end
    (FR-10 AC) — an unreadable ticket/tracker is skipped, not fatal."""
    agent = (agent or "").strip()
    if not agent:
        return []
    repo_root = repo_root or find_repo_root()
    try:
        all_tickets = tickets_mod.list_tickets(repo_root)
    except Exception:  # noqa: BLE001 - never crash a session end
        return []
    out = []
    for ticket in all_tickets:
        try:
            if ticket.get("claimed_by") != agent:
                continue
            if _has_update_since_claim(repo_root, ticket):
                continue
            out.append({
                "id": ticket["id"],
                "title": ticket.get("title", ""),
                "claimed_at": ticket.get("claimed_at", ""),
            })
        except Exception:  # noqa: BLE001 - one bad ticket must not sink the rest
            continue
    return out


def format_reminder(stale):
    if not stale:
        return ""
    lines = ["reminder: you still hold these claimed tickets with no update recorded since claiming them —"
             " comment, move, or release the claim before you go:"]
    for t in stale:
        lines.append("  - %s (%s) claimed %s" % (t["id"], t.get("title", ""), t.get("claimed_at", "")))
    return "\n".join(lines)
