"""Generic tracker CRUD for questions/bugs/todos, backed by {T}-{kind}.toml.

Field shapes mirror the pre-existing questions/bugs/todos SKILL.md entry
formats exactly (same status models, same taxonomies) — only the storage
mechanism changed, from hand-edited markdown to CLI-mutated TOML.

`gaps` and `critique` are intentionally NOT in VALID_KINDS yet — reserved
names, promoted only once questions/bugs/todos are proven on this CLI
(see consolidate/SKILL.md).
"""

import os
from datetime import date, datetime, timezone

from . import boards as boards_mod
from . import tomlio
from .paths import find_repo_root, ticket_dir

VALID_KINDS = ("questions", "bugs", "todos")

_ID_FORMATS = {
    "questions": lambda n: f"Q{n}",
    "bugs": lambda n: f"D-{n}",
    "todos": lambda n: f"TD-{n}",
}

_DEFAULT_STATUS = {
    "questions": "open",
    "bugs": "open",
    "todos": "open",
}

# predicate: item counts as a release-blocking critical item for this kind
_IS_BLOCKER = {
    "questions": lambda it: it.get("priority") == "critical" and it.get("status") not in ("resolved", "closed"),
    "bugs": lambda it: it.get("severity") == "critical" and it.get("status") not in ("verified", "closed"),
    "todos": lambda it: False,  # todos never block, by design
}


def _check_kind(kind):
    if kind not in VALID_KINDS:
        raise ValueError(f"unknown tracker kind {kind!r}; valid: {VALID_KINDS}")


def _tracker_path(repo_root, ticket_id, kind):
    config = boards_mod.load_console_config(repo_root)
    return os.path.join(ticket_dir(repo_root, config, ticket_id), f"{ticket_id}-{kind}.toml")


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(repo_root, ticket_id, kind):
    _check_kind(kind)
    repo_root = repo_root or find_repo_root()
    path = _tracker_path(repo_root, ticket_id, kind)
    if not os.path.isfile(path):
        return {"meta": {"ticket": ticket_id, "tracker": kind, "updated": ""}, "items": []}
    data = tomlio.load(path)
    data.setdefault("meta", {"ticket": ticket_id, "tracker": kind, "updated": ""})
    data.setdefault("items", [])
    return data


def _save(repo_root, ticket_id, kind, data):
    path = _tracker_path(repo_root, ticket_id, kind)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data["meta"]["updated"] = _now_iso()
    tomlio.atomic_write(path, data)


def _next_id(items, kind):
    fmt = _ID_FORMATS[kind]
    existing = {it["id"] for it in items}
    n = len(items) + 1
    while fmt(n) in existing:
        n += 1
    return fmt(n)


def add(repo_root, ticket_id, kind, text, **fields):
    _check_kind(kind)
    repo_root = repo_root or find_repo_root()
    data = load(repo_root, ticket_id, kind)
    item_id = _next_id(data["items"], kind)
    today = date.today().isoformat()
    item = {"id": item_id, "status": _DEFAULT_STATUS[kind], "text": text}

    if kind == "questions":
        item.update(
            {
                "type": fields.get("type", "other"),
                "priority": fields.get("priority", "medium"),
                "raised_by": fields.get("raised_by", "agent"),
                "raised_on": today,
                "affects": fields.get("affects", []),
                "answer": "",
                "resolved_on": "",
            }
        )
    elif kind == "bugs":
        item.update(
            {
                "severity": fields.get("severity", "medium"),
                "found_on": today,
                "phase": fields.get("phase", ""),
                "found_by": fields.get("found_by", "agent"),
                "steps": fields.get("steps", ""),
                "expected": fields.get("expected", ""),
                "actual": fields.get("actual", ""),
                "fix": "",
                "fixed_by": "",
                "fixed_on": "",
                "verified_by": "",
                "verified_on": "",
            }
        )
    elif kind == "todos":
        item.update(
            {
                "type": fields.get("type", "task"),
                "priority": fields.get("priority", "medium"),
                "captured_by": fields.get("captured_by", "agent"),
                "captured_on": today,
                "due": fields.get("due", ""),
                "context": fields.get("context", ""),
                "done_on": "",
                "drop_reason": "",
            }
        )

    data["items"].append(item)
    _save(repo_root, ticket_id, kind, data)
    return item


def list_items(repo_root, ticket_id, kind, status=None):
    _check_kind(kind)
    repo_root = repo_root or find_repo_root()
    data = load(repo_root, ticket_id, kind)
    items = data["items"]
    if status:
        items = [it for it in items if it.get("status") == status]
    return items


def update(repo_root, ticket_id, kind, item_id, **fields):
    _check_kind(kind)
    repo_root = repo_root or find_repo_root()
    data = load(repo_root, ticket_id, kind)
    for item in data["items"]:
        if item["id"] == item_id:
            item.update(fields)
            _save(repo_root, ticket_id, kind, data)
            return item
    raise KeyError(f"no item {item_id!r} in {ticket_id}-{kind}.toml")


def remove(repo_root, ticket_id, kind, item_id):
    """Delete an item outright. Used by a move, which is a remove from the
    source plus an add to the target — there is no in-place "reparent"
    because the two live in different files."""
    _check_kind(kind)
    repo_root = repo_root or find_repo_root()
    data = load(repo_root, ticket_id, kind)
    keep = [it for it in data["items"] if it["id"] != item_id]
    if len(keep) == len(data["items"]):
        raise KeyError(f"no item {item_id!r} in {ticket_id}-{kind}.toml")
    gone = [it for it in data["items"] if it["id"] == item_id][0]
    data["items"] = keep
    _save(repo_root, ticket_id, kind, data)
    return gone


def ensure_all(repo_root, ticket_id):
    """Scaffold empty {T}-{kind}.toml for every tracker kind that doesn't
    already exist yet — called by tickets.create() so a fresh ticket has
    all three trackers present (even if empty) from the start."""
    repo_root = repo_root or find_repo_root()
    for kind in VALID_KINDS:
        path = _tracker_path(repo_root, ticket_id, kind)
        if not os.path.isfile(path):
            _save(repo_root, ticket_id, kind, {"meta": {"ticket": ticket_id, "tracker": kind, "updated": ""}, "items": []})


def blockers(repo_root, ticket_id):
    repo_root = repo_root or find_repo_root()
    out = {}
    for kind in VALID_KINDS:
        pred = _IS_BLOCKER[kind]
        items = [it for it in list_items(repo_root, ticket_id, kind) if pred(it)]
        if items:
            out[kind] = items
    return out
