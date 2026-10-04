"""ticket.toml CRUD + stage-move validation against the ticket's board config.

ticket.toml is CLI/HTTP-mutated only (see consolidate/SKILL.md) — this module
is the single write path both kanban.py and httpd.py call into.
"""

import os
import re
from datetime import date, datetime, timezone

from . import boards as boards_mod
from . import run_config
from . import runs as runs_mod
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
        # The Run that holds the claim, or "" (T-020 FR-19). Set only by
        # `set_claim`, cleared on release.
        "claimed_run": "",
        # Consecutive review rounds that asked for changes, and whether the
        # loop has escalated to a human (T-020 FR-24). Set only by
        # `record_review`, never by `set_field`/`patch`.
        "review_rounds": 0,
        "review_escalated": False,
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
    ticket.setdefault("claimed_run", "")
    ticket.setdefault("review_rounds", 0)
    ticket.setdefault("review_escalated", False)
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


def parse_claimed_at(value):
    """Aware UTC datetime for a `claimed_at`, or None. A full `...Z` stamp is
    read as is; a legacy date-only value means the end of that day, so a claim
    is never judged older than it could be (T-020 FR-19)."""
    try:
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _verdict(state, basis, reason, ticket, age):
    return {"state": state, "holder": ticket.get("claimed_by") or "",
            "claimed_at": ticket.get("claimed_at") or "",
            "claimed_run": ticket.get("claimed_run") or "",
            "age_secs": age, "basis": basis, "reason": reason}


def evaluate_claim(ticket, runs_for_ticket, now, cfg):
    """Pure stale-claim rule (T-020 FR-20). `runs_for_ticket` holds the Runs on
    the ticket plus the linked one if it lives elsewhere. Order: no holder is
    free; a linked ACTIVE Run protects the claim however old (BR-6); a linked
    Run ended past the grace, or missing, makes it stale; unlinked, any ACTIVE
    Run protects it and otherwise only a known age past the TTL expires it.
    Unknown time never expires a claim (BR-7)."""
    if not (ticket.get("claimed_by") or ""):
        return _verdict("free", "", "no holder", ticket, None)
    claimed = parse_claimed_at(ticket.get("claimed_at") or "")
    age = None if claimed is None else max(0, int((now - claimed).total_seconds()))
    link = ticket.get("claimed_run") or ""
    by_id = {r.get("id"): r for r in runs_for_ticket}
    grace = cfg["dead_grace_secs"]

    def held(basis, why):
        return _verdict("held", basis, why, ticket, age)

    if link:
        rec = by_id.get(link)
        if rec is not None and rec.get("state") in runs_mod.ACTIVE:
            return held("run_live", "linked run %s is %s" % (link, rec["state"]))
        if rec is not None:
            ended = parse_claimed_at(rec.get("ended") or rec.get("updated") or "")
            if ended is None:
                return held("unknown", "linked run %s has no readable end time" % link)
            gone = (now - ended).total_seconds()
            if gone >= grace:
                return _verdict("stale", "run_dead",
                                "linked run %s ended %ds ago" % (link, gone), ticket, age)
            return held("run_grace", "linked run %s ended %ds ago, inside the grace" % (link, gone))
        if age is not None and age > grace:
            return _verdict("stale", "run_missing",
                            "linked run %s has no record" % link, ticket, age)
        return held("unknown" if age is None else "run_grace",
                    "linked run %s has no record; claim too new or undated" % link)
    live = [r["id"] for r in runs_for_ticket if r.get("state") in runs_mod.ACTIVE]
    if live:
        return held("run_live", "run %s is active on the ticket" % live[0])
    if age is None:
        return held("unknown", "claimed_at is unknown")
    ttl = cfg["ttl_secs"]
    if ttl and age > ttl:
        return _verdict("stale", "ttl", "claim is %ds old, ttl %ds" % (age, ttl), ticket, age)
    return held("fresh", "claim is %ds old" % age)


def claim_status(repo_root, ticket_id, now=None):
    """`evaluate_claim` over the stored ticket and its Runs. Any failure reads
    as `held/unknown`: a claim is never expired on a guess (BR-7)."""
    repo_root = repo_root or find_repo_root()
    try:
        ticket = load(repo_root, ticket_id)
    except Exception as exc:  # noqa: BLE001
        return _verdict("held", "unknown", "cannot evaluate: %s" % exc, {}, None)
    if ticket is None:
        return _verdict("held", "unknown", "no ticket.toml for %s" % ticket_id, {}, None)
    return _verdict_now(repo_root, ticket_id, ticket, now)


def _verdict_now(repo_root, ticket_id, ticket, now=None):
    """Verdict for `ticket` (as read, maybe under a lock) against the Runs on
    disk now; any failure is `held/unknown`."""
    now = now or datetime.now(timezone.utc)
    try:
        found = runs_mod.list_runs(repo_root, ticket=ticket_id)
        link = ticket.get("claimed_run") or ""
        if link and all(r.get("id") != link for r in found):
            rec = runs_mod.get(repo_root, link)
            if rec is not None:
                found.append(rec)
        return evaluate_claim(ticket, found, now, run_config.claims_cfg(repo_root))
    except Exception as exc:  # noqa: BLE001 - fail closed, whatever broke
        return _verdict("held", "unknown", "cannot evaluate: %s" % exc, ticket, None)


def set_claim(repo_root, ticket_id, claimed_by, claimed_at=None, *, claimed_run=None,
              adopt_stale=False, now=None, info=None):
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
    `ClaimConflictError` instead of overwriting the existing claim, unless
    `adopt_stale` is set and the claim is `stale`: staleness is re-evaluated
    inside the lock (T-020 FR-21), so of two adopters exactly one wins, and the
    previous holder, time, run, basis and age are written to `info`. Claiming
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
            verdict = _verdict_now(repo_root, ticket_id, ticket, now)
            if not (adopt_stale and verdict["state"] == "stale"):
                raise ClaimConflictError(
                    f"{ticket_id} is already claimed by {current!r} "
                    f"(basis: {verdict['basis']}); a human can free it with claim-release")
            if info is not None:
                info.update(previous_holder=current,
                            previous_claimed_at=ticket.get("claimed_at") or "",
                            previous_claimed_run=ticket.get("claimed_run") or "",
                            basis=verdict["basis"], age_secs=verdict["age_secs"])
        ticket["claimed_by"] = claimed_by
        ticket["claimed_at"] = (claimed_at or "") if claimed_by else ""
        # None keeps the link (a same-holder refresh); release always clears it.
        ticket["claimed_run"] = (ticket.get("claimed_run", "") if claimed_run is None
                                 else claimed_run) if claimed_by else ""
        ticket["updated"] = date.today().isoformat()

    raw = tomlio.atomic_update(path, _mutate)
    return raw["ticket"]


FORCE_REASON_MIN = 10


def release_claim(repo_root, ticket_id, agent, force=False, reason="", now=None):
    """Release a claim under the `atomic_update` lock (T-020 FR-22, BR-13).

    The holder releases its own; anyone releases a `stale` claim; a `held`
    claim of another identity needs `force` and a `reason` of at least 10
    characters. Returns an outcome dict (never raises for a refusal) carrying
    the previous holder, time, run and basis for the caller's audit row."""
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    path = _toml_path(repo_root, config, ticket_id)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")
    reason = (reason or "").strip()
    out = {"ok": False, "released": False, "forced": False, "error": ""}

    def _mutate(raw):
        ticket = raw.setdefault("ticket", {})
        holder = ticket.get("claimed_by") or ""
        if not holder:
            out.update(ok=True, error="", basis="free")
            return None
        verdict = _verdict_now(repo_root, ticket_id, ticket, now)
        out.update(previous_holder=holder,
                   previous_claimed_at=ticket.get("claimed_at") or "",
                   previous_claimed_run=ticket.get("claimed_run") or "",
                   basis=verdict["basis"])
        if force and len(reason) < FORCE_REASON_MIN:
            out["error"] = "force needs a reason of at least %d characters" % FORCE_REASON_MIN
            return None
        own, stale = holder == agent, verdict["state"] == "stale"
        if not (own or stale or force):
            out["error"] = ("%s is held by %r (basis: %s); only the holder may release it "
                            "- pass force=true and a reason of at least %d characters to override"
                            % (ticket_id, holder, verdict["basis"], FORCE_REASON_MIN))
            return None
        ticket["claimed_by"] = ticket["claimed_at"] = ticket["claimed_run"] = ""
        ticket["updated"] = date.today().isoformat()
        out.update(ok=True, released=True, forced=bool(force and not (own or stale)))

    # A refusal returns None from `_mutate`, which rewrites the file unchanged.
    tomlio.atomic_update(path, _mutate)
    return out


REVIEW_OUTCOMES = ("changes_requested", "approved", "human_decision")


def record_review(repo_root, ticket_id, outcome, max_rounds=3):
    """Count a review outcome under the `atomic_update` lock (T-020 FR-24, BR-8).

    `changes_requested` increments; reaching `max_rounds` sets
    `review_escalated` and returns `escalate: True` on that one transition
    only; while escalated it is refused without counting. Only `approved` and
    `human_decision` reset both fields. Returns {ok, rounds, escalated,
    escalate}; the caller opens the question (outside the lock)."""
    if outcome not in REVIEW_OUTCOMES:
        raise ValueError("outcome must be one of %s" % ", ".join(REVIEW_OUTCOMES))
    repo_root = repo_root or find_repo_root()
    config = boards_mod.load_console_config(repo_root)
    path = _toml_path(repo_root, config, ticket_id)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"no ticket.toml for {ticket_id}")
    out = {}

    def _mutate(raw):
        ticket = raw.setdefault("ticket", {})
        rounds = int(ticket.get("review_rounds") or 0)
        escalated = bool(ticket.get("review_escalated", False))
        escalate = False
        ok = True
        if outcome == "changes_requested":
            if escalated:
                ok = False
            else:
                rounds += 1
                escalated = escalate = rounds >= max_rounds
        else:
            rounds, escalated = 0, False
        if ok:
            ticket["review_rounds"], ticket["review_escalated"] = rounds, escalated
            ticket["updated"] = date.today().isoformat()
        out.update(ok=ok, rounds=rounds, escalated=escalated, escalate=escalate)

    tomlio.atomic_update(path, _mutate)
    return out


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
