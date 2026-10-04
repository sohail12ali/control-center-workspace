"""Ticket liveness: does an active ticket have a way to make progress? (T-021 FR-6)

A ticket-state check, not harness lint: it needs Run records, a clock and the
ticket's trackers. Read-only (no write call anywhere) and total: any read that
fails becomes a `check_error` warning for that ticket, never an exception.

Applies to `tickets`-kind tickets in `in-progress`, `verify` or `blocked`.
Action paths: a live Run (`runs.ACTIVE`), a held claim, a pending question
(`open` or `answered`). A stale claim, a terminal Run, a resolved question and
the human `owner` are not paths. `blocked` additionally needs a routable item
(a pending question or an open critical bug) and someone to route it to.
Every finding is level `warn` and names its remedy.
"""

from datetime import datetime, timezone

from . import runs as runs_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod
from .paths import find_repo_root

APPLIES_LANES = ("in-progress", "verify", "blocked")
NO_ACTION_PATH = "no_action_path"
CLAIM_STALE = "claim_stale"
BLOCKED_PROSE_ONLY = "blocked_prose_only"
BLOCKED_NO_OWNER = "blocked_no_owner"
CHECK_ERROR = "check_error"

_REMEDY = {
    NO_ACTION_PATH: "no live Run, held claim or pending question: `claim` the ticket, "
                    "or `tracker-add` a question for the person who must act",
    CLAIM_STALE: "the only claim is stale (%s): re-claim to refresh it, or `claim-release`",
    BLOCKED_PROSE_ONLY: "blocked with no pending question or critical bug: "
                        "`tracker-add` a question saying what unblocks it",
    BLOCKED_NO_OWNER: "blocked with no owner and no claim holder: set an owner or `claim` it",
}


def _finding(code, message=None):
    return {"code": code, "level": "warn", "message": message or _REMEDY[code]}


def _result(ticket_id, stage, applies, paths, findings):
    return {"ticket": ticket_id, "stage": stage, "applies": applies,
            "ok": not findings, "paths": paths, "findings": findings}


def _pending_question(repo_root, ticket_id):
    items = trackers_mod.list_items(repo_root, ticket_id, "questions")
    return any(i.get("status") in ("open", "answered") for i in items)


def evaluate(repo_root, ticket_id, now=None):
    """Liveness of one ticket: {ticket, stage, applies, ok, paths[], findings[]}."""
    repo_root = repo_root or find_repo_root()
    now = now or datetime.now(timezone.utc)
    stage = ""
    try:
        ticket = tickets_mod.load(repo_root, ticket_id)
        if ticket is None:
            raise FileNotFoundError("no ticket.toml for %s" % ticket_id)
        stage = ticket.get("stage") or ""
        if (ticket.get("kind") or "tickets") != "tickets" or stage not in APPLIES_LANES:
            return _result(ticket_id, stage, False, [], [])
        return _evaluate_applicable(repo_root, ticket_id, ticket, stage, now)
    except Exception as exc:  # noqa: BLE001 - the check never raises
        return _result(ticket_id, stage, bool(stage in APPLIES_LANES), [],
                       [_finding(CHECK_ERROR, "cannot evaluate %s: %s" % (ticket_id, exc))])


def _evaluate_applicable(repo_root, ticket_id, ticket, stage, now):
    claim = tickets_mod.claim_status(repo_root, ticket_id, now=now)
    live = any(r.get("state") in runs_mod.ACTIVE
               for r in runs_mod.list_runs(repo_root, ticket=ticket_id))
    question = _pending_question(repo_root, ticket_id)
    held = claim["state"] == "held"
    paths = [name for name, on in (("run", live), ("claim", held), ("question", question)) if on]
    if stage != "blocked":
        if paths:
            return _result(ticket_id, stage, True, paths, [])
        if claim["state"] == "stale":
            return _result(ticket_id, stage, True, paths,
                           [_finding(CLAIM_STALE, _REMEDY[CLAIM_STALE] % claim["basis"])])
        return _result(ticket_id, stage, True, paths, [_finding(NO_ACTION_PATH)])
    bug = _open_critical_bug(repo_root, ticket_id)
    paths = [p for p in paths if p != "claim"] + (["bug"] if bug else [])
    paths.sort(key=("run", "question", "bug").index)
    code = _blocked_code(ticket, claim, question, bug)
    return _result(ticket_id, stage, True, paths, [_finding(code)] if code else [])


def _open_critical_bug(repo_root, ticket_id):
    return "bugs" in trackers_mod.blockers(repo_root, ticket_id)


def _blocked_code(ticket, claim, question, bug):
    """The one routability rule for `blocked`: a next action AND an owner."""
    if not (question or bug):
        return BLOCKED_PROSE_ONLY
    owner = claim["holder"] if claim["state"] == "held" else ticket.get("owner") or ""
    return None if owner else BLOCKED_NO_OWNER


def blocked_refusal(repo_root, ticket_id, now=None):
    """Would a ticket be routable if it were `blocked` now? None when yes, else a
    finding `{code, level, message}`. Used by the move gate (FR-7); may raise."""
    ticket = tickets_mod.load(repo_root, ticket_id)
    claim = tickets_mod.claim_status(repo_root, ticket_id, now=now or datetime.now(timezone.utc))
    code = _blocked_code(ticket, claim, _pending_question(repo_root, ticket_id),
                         _open_critical_bug(repo_root, ticket_id))
    return _finding(code) if code else None


def scan(repo_root, now=None):
    """Every `tickets`-kind ticket: {checked, failing[], summary{checked, ok, warn}}."""
    repo_root = repo_root or find_repo_root()
    now = now or datetime.now(timezone.utc)
    failing, checked, ok = [], 0, 0
    try:
        ids = [t["id"] for t in tickets_mod.list_tickets(repo_root, kind="tickets")]
    except Exception as exc:  # noqa: BLE001
        failing.append(_result("", "", False, [], [_finding(CHECK_ERROR, "cannot list tickets: %s" % exc)]))
        ids = []
    for ticket_id in ids:
        res = evaluate(repo_root, ticket_id, now=now)
        if not res["applies"] and res["ok"]:
            continue
        checked += 1
        if res["ok"]:
            ok += 1
        else:
            failing.append(res)
    return {"checked": checked, "failing": failing,
            "summary": {"checked": checked, "ok": ok, "warn": len(failing)}}
