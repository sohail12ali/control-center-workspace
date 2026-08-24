"""ticket.toml CRUD + stage-move validation against the ticket's board config.

ticket.toml is CLI/HTTP-mutated only (see consolidate/SKILL.md) — this module
is the single write path both kanban.py and httpd.py call into.
"""

import os
import re
from datetime import date

from . import boards as boards_mod
from . import tomlio
from . import trackers as trackers_mod
from .paths import find_repo_root, ticket_dir


def _toml_path(repo_root, config, ticket_id):
    return os.path.join(ticket_dir(repo_root, config, ticket_id), "ticket.toml")


def validate_id(ticket_id, config):
    pattern = config["general"]["id_pattern"]
    if not re.match(pattern, ticket_id):
        raise ValueError(f"ticket id {ticket_id!r} does not match id_pattern {pattern!r}")


#: Priority vocabulary, lowest first. Anything else normalises to "medium" —
#: a typo in a hand-edited file must not produce an un-renderable card.
PRIORITIES = ("low", "medium", "high", "critical")
DEFAULT_PRIORITY = "medium"


def normalise_priority(value):
    v = (value or "").strip().lower()
    return v if v in PRIORITIES else DEFAULT_PRIORITY


def create(repo_root, ticket_id, title, kind="tickets", owner="",
           priority=DEFAULT_PRIORITY, url=""):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    validate_id(ticket_id, config)
    board_cfg = boards_mod.load_board_config(kind, repo_root)
    lanes = board_cfg.get("lanes", [])
    if not lanes:
        raise ValueError(f"board kind {kind!r} has no lanes configured")
    path = _toml_path(repo_root, config, ticket_id)
    if os.path.exists(path):
        raise FileExistsError(f"ticket.toml already exists for {ticket_id}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    today = date.today().isoformat()
    ticket = {
        "id": ticket_id,
        "title": title,
        "kind": kind,
        "stage": lanes[0]["id"],
        "status": "active",
        "owner": owner,
        "priority": normalise_priority(priority),
        "created": today,
        "updated": today,
        "tags": [],
        "links": [],
        "scripts_dir": "",
        # Link to this ticket in whatever external tracker the team uses
        # (Jira, Linear, GitHub, an internal tool). Empty means "not tracked
        # anywhere else", which is the normal case for a standalone vault —
        # the card simply doesn't show the link.
        "url": url,
    }
    tomlio.atomic_write(path, {"ticket": ticket})
    trackers_mod.ensure_all(repo_root, ticket_id)
    return ticket


def load(repo_root, ticket_id):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    path = _toml_path(repo_root, config, ticket_id)
    if not os.path.isfile(path):
        return None
    ticket = tomlio.load(path)["ticket"]
    # Defaults for fields added after a ticket was written, so an older
    # ticket.toml keeps loading instead of erroring on a missing key.
    ticket.setdefault("url", "")
    ticket["priority"] = normalise_priority(ticket.get("priority"))
    return ticket


def _save(repo_root, config, ticket_id, ticket):
    path = _toml_path(repo_root, config, ticket_id)
    tomlio.atomic_write(path, {"ticket": ticket})


def list_tickets(repo_root=None, kind=None, stage=None, owner=None):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    root_dir = os.path.join(repo_root, config["general"]["data_root"])
    results = []
    if not os.path.isdir(root_dir):
        return results
    for name in sorted(os.listdir(root_dir)):
        if name.startswith("_"):
            continue
        path = os.path.join(root_dir, name, "ticket.toml")
        if not os.path.isfile(path):
            continue
        ticket = tomlio.load(path)["ticket"]
        if kind and ticket.get("kind") != kind:
            continue
        if stage and ticket.get("stage") != stage:
            continue
        if owner and ticket.get("owner") != owner:
            continue
        results.append(ticket)
    return results


def dir_for(repo_root, ticket_id):
    """The ticket's folder. Wrapper so callers don't need the config object
    just to locate a directory."""
    config = boards_mod.load_console_config(repo_root)
    return ticket_dir(repo_root, config, ticket_id)


def list_artifacts(repo_root, ticket_id):
    """The markdown artifacts and any ticket-scripts/ folder beside the TOML.

    Lets the ticket drawer link out to the real files instead of pretending
    the TOML is the whole ticket — the markdown is still where the substance
    lives, and this is a board, not an editor.
    """
    folder = dir_for(repo_root, ticket_id)
    if not os.path.isdir(folder):
        return {"files": [], "scripts_dir": None}
    files, scripts = [], None
    for name in sorted(os.listdir(folder)):
        full = os.path.join(folder, name)
        if os.path.isdir(full):
            if name == "ticket-scripts":
                scripts = {
                    "name": name,
                    "count": len([f for f in os.listdir(full) if not f.startswith(".")]),
                }
            continue
        if name.endswith(".md"):
            files.append(
                {
                    "name": name,
                    "artifact": name[len(ticket_id) + 1 : -3] if name.startswith(ticket_id + "-") else name[:-3],
                    "size": os.path.getsize(full),
                }
            )
    return {"files": files, "scripts_dir": scripts}


def move(repo_root, ticket_id, stage):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    ticket = load(repo_root, ticket_id)
    if ticket is None:
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")
    if not boards_mod.valid_stage(ticket["kind"], stage, repo_root):
        valid = [lane["id"] for lane in boards_mod.lanes_for(ticket["kind"], repo_root)]
        raise ValueError(f"{stage!r} is not a valid lane for board {ticket['kind']!r}; valid: {valid}")
    ticket["stage"] = stage
    ticket["updated"] = date.today().isoformat()
    _save(repo_root, config, ticket_id, ticket)
    return ticket


#: Fields a user may edit directly. `id`/`kind`/`created` are identity or
#: history and are deliberately absent; `stage` has its own validated move().
EDITABLE = ("title", "owner", "priority", "status", "url", "tags", "links", "scripts_dir")


def set_field(repo_root, ticket_id, field, value):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    ticket = load(repo_root, ticket_id)
    if ticket is None:
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")
    if field not in ticket:
        raise ValueError(f"unknown ticket field: {field!r}")
    if field == "priority":
        value = normalise_priority(value)
    ticket[field] = value
    ticket["updated"] = date.today().isoformat()
    _save(repo_root, config, ticket_id, ticket)
    return ticket


def patch(repo_root, ticket_id, fields):
    """Set several fields at once, rejecting anything not user-editable.

    One write instead of one per field: the drawer can change owner and
    priority together, and two sequential writes would stamp `updated` twice
    and briefly leave the file half-updated.
    """
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    ticket = load(repo_root, ticket_id)
    if ticket is None:
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")

    unknown = [k for k in fields if k not in EDITABLE]
    if unknown:
        raise ValueError(
            "not editable: %s (editable: %s)" % (", ".join(sorted(unknown)), ", ".join(EDITABLE))
        )
    if "title" in fields and not str(fields["title"]).strip():
        raise ValueError("title cannot be empty")

    for key, value in fields.items():
        ticket[key] = normalise_priority(value) if key == "priority" else value
    ticket["updated"] = date.today().isoformat()
    _save(repo_root, config, ticket_id, ticket)
    return ticket
