"""Cross-vault Todos: every ticket's todos plus the ones that belong to no
ticket at all.

General (unscoped) todos are a normal TOML tracker under a reserved
`_shared` scope — the same file format, the same read/write path, the same
id scheme as a ticket's todos. They used to be markdown, which made them
read-only from the console and made "promote this to a ticket" a
rewrite-the-markdown special case. As a tracker, moving a todo in or out of a
ticket is just remove-from-source + add-to-target through one code path.

`_shared` is already a sanctioned non-ticket folder under artifacts/ (see
consolidate/SKILL.md), so this introduces no new layout rule.
"""

import os

from . import boards as boards_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod

#: Reserved scope id for todos that belong to no ticket. Not a valid ticket
#: id (the id_pattern requires a leading capital), so it can never collide.
GENERAL = "_shared"

_CARRY_FIELDS = ("text", "type", "status", "priority", "due", "context", "raised_on")


def _annotate(item, scope, owner=""):
    row = dict(item)
    row["scope"] = scope
    row["general"] = scope == GENERAL
    row["ticket"] = None if scope == GENERAL else scope
    row["owner"] = owner
    return row


def all_todos(repo_root, status=None, owner=None):
    """Every todo, ticket-scoped and general, each annotated with where it
    lives so the caller can write back to the right file."""
    results = []

    for ticket in tickets_mod.list_tickets(repo_root):
        for item in trackers_mod.list_items(repo_root, ticket["id"], "todos"):
            results.append(_annotate(item, ticket["id"], ticket.get("owner", "")))

    for item in trackers_mod.list_items(repo_root, GENERAL, "todos"):
        results.append(_annotate(item, GENERAL))

    if status:
        results = [r for r in results if r.get("status") == status]
    if owner:
        results = [r for r in results if r.get("owner") == owner]
    return results


def scopes(repo_root):
    """Where a todo can live: every ticket, plus general. Feeds the move
    picker so it offers real destinations rather than free text."""
    out = [{"id": GENERAL, "label": "General (no ticket)", "general": True}]
    for ticket in tickets_mod.list_tickets(repo_root):
        out.append({"id": ticket["id"], "label": ticket["id"] + " — " + ticket["title"],
                    "general": False})
    return out


def _validate_scope(repo_root, scope):
    if scope == GENERAL:
        return
    if tickets_mod.load(repo_root, scope) is None:
        raise ValueError("no such ticket: %r" % scope)


def create(repo_root, text, scope=GENERAL, **fields):
    text = (text or "").strip()
    if not text:
        raise ValueError("a todo needs some text")
    _validate_scope(repo_root, scope)
    item = trackers_mod.add(repo_root, scope, "todos", text, **fields)
    return _annotate(item, scope)


def move(repo_root, scope, item_id, target):
    """Move one todo to another ticket, or to/from general.

    Remove-then-add, in that order by design: the two live in different
    files, so there is no atomic reparent. Add first and a crash would
    duplicate the todo; remove first and the worst case is a lost item whose
    text is still in the response. The target write is validated before the
    source is touched, so the common failure (a typo'd ticket) can't lose
    anything.
    """
    if target == scope:
        raise ValueError("that todo is already there")
    _validate_scope(repo_root, scope)
    _validate_scope(repo_root, target)

    existing = [it for it in trackers_mod.list_items(repo_root, scope, "todos") if it["id"] == item_id]
    if not existing:
        raise KeyError("no todo %r in %s" % (item_id, scope))
    src = existing[0]

    carried = {k: src[k] for k in _CARRY_FIELDS if k in src and k != "text"}
    trackers_mod.remove(repo_root, scope, "todos", item_id)
    try:
        item = trackers_mod.add(repo_root, target, "todos", src.get("text", ""), **carried)
    except Exception:
        # Put it back rather than losing it if the target write fails.
        trackers_mod.add(repo_root, scope, "todos", src.get("text", ""), **carried)
        raise
    return {"moved": True, "from": scope, "to": target,
            "old_id": item_id, "item": _annotate(item, target)}


def delete(repo_root, scope, item_id):
    _validate_scope(repo_root, scope)
    gone = trackers_mod.remove(repo_root, scope, "todos", item_id)
    return {"deleted": item_id, "scope": scope, "text": gone.get("text", "")}
