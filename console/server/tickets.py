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
from .paths import artifacts_dir, find_repo_root, ticket_dir


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
        # Who currently has this ticket claimed (T-017 FR-8), and when. This
        # is distinct from `owner` (the human set at creation) — an agent
        # picking up a ticket does not change who owns it. Empty means
        # "unclaimed". See decision-log a3.
        "claimed_by": "",
        "claimed_at": "",
        # This ticket's delivery identity (T-018 FR-5, decision-log a2):
        # the branch a worktree was created on, and the PR opened from it.
        # Durable across however many Runs execute against the ticket, unlike
        # the per-Run `worktree_path`/`worktree_branch` on the Run record.
        # Mutated only through `set_pr`, never hand-edited or `set_field`.
        "branch": "",
        "pr_url": "",
        "pr_state": "",
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
    ticket.setdefault("claimed_by", "")
    ticket.setdefault("claimed_at", "")
    ticket.setdefault("branch", "")
    ticket.setdefault("pr_url", "")
    ticket.setdefault("pr_state", "")
    ticket["priority"] = normalise_priority(ticket.get("priority"))
    return ticket


def _save(repo_root, config, ticket_id, ticket):
    path = _toml_path(repo_root, config, ticket_id)
    tomlio.atomic_write(path, {"ticket": ticket})


def list_tickets(repo_root=None, kind=None, stage=None, owner=None):
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    root_dir = artifacts_dir(repo_root, config)
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


class ClaimConflictError(RuntimeError):
    """A claim attempt found the ticket already claimed by someone else
    (T-017 FR-8, Edge Case §8). Named so a caller can report it as a refused
    claim rather than a generic write failure or a silent overwrite."""


def set_claim(repo_root, ticket_id, claimed_by, claimed_at=None):
    """Set `claimed_by`/`claimed_at` (T-017 FR-8, decision-log a3).

    A dedicated mutator, not `set_field`/`patch` — those are the user-editable
    surface (`EDITABLE`), and a claim is a verb-driven fact, not a field a
    human hand-edits. Pass `claimed_by=""` to release the claim.

    Race-safe (task 3a-5): the read-check-write happens inside one
    `tomlio.atomic_update` call, under the same lock file `atomic_write` uses
    for a single write. A plain `load()` + `_save()` pair — what every other
    mutator in this module still uses, and what this function used before
    3a-5 — only locks the write half; two concurrent claims could both read
    an empty `claimed_by` before either wrote, and both "win". Claiming an
    already-claimed ticket for a *different* identity raises
    `ClaimConflictError` instead of overwriting the existing claim. Claiming
    by the *same* identity that already holds it is a no-op success that
    refreshes `claimed_at` (task 3a-6); releasing (`claimed_by=""`) always
    succeeds regardless of who currently holds the claim.
    """
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    path = _toml_path(repo_root, config, ticket_id)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")
    claimed_by = claimed_by or ""

    def _mutate(raw):
        ticket = raw.setdefault("ticket", {})
        current = ticket.get("claimed_by") or ""
        if claimed_by and current and current != claimed_by:
            raise ClaimConflictError(
                f"{ticket_id} is already claimed by {current!r}")
        ticket["claimed_by"] = claimed_by
        ticket["claimed_at"] = (claimed_at or "") if claimed_by else ""
        ticket["updated"] = date.today().isoformat()

    raw = tomlio.atomic_update(path, _mutate)
    return raw["ticket"]


def set_pr(repo_root, ticket_id, *, branch=None, pr_url=None, pr_state=None):
    """Set `branch`/`pr_url`/`pr_state` (T-018 FR-5, decision-log a2).

    A dedicated mutator, not `set_field`/`patch` — those are the user-editable
    surface (`EDITABLE`); a ticket's branch/PR identity is a verb-driven fact
    (worktree creation, a `gh pr view` read), same category as `set_claim`'s
    `claimed_by`/`claimed_at`. Any of the three keyword args left as `None`
    means "leave unchanged" (task 3a-2) — pass `""` explicitly to clear a
    field. Race-safe via `tomlio.atomic_update`, the same lock-guarded
    read-modify-write `set_claim` uses, so a worktree-creation write and a
    `pr-check` write cannot interleave and half-clobber each other.

    Publishing to the MCP change bus is the caller's job here, same as
    `set_claim` — the `pr-check` verb (3b-1) publishes after calling this,
    mirroring `ticket_claim`/`ticket_comment` in verb_handlers.py rather than
    this module reaching into `bus` itself.
    """
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    path = _toml_path(repo_root, config, ticket_id)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")

    def _mutate(raw):
        ticket = raw.setdefault("ticket", {})
        if branch is not None:
            ticket["branch"] = branch
        if pr_url is not None:
            ticket["pr_url"] = pr_url
        if pr_state is not None:
            ticket["pr_state"] = pr_state
        ticket["updated"] = date.today().isoformat()

    raw = tomlio.atomic_update(path, _mutate)
    return raw["ticket"]


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
