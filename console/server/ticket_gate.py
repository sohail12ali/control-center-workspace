"""Guarded lane moves for the agent-facing paths (T-021 FR-7, FR-9).

`guarded_move` is what `verb_handlers.ticket_move` and `kanban ticket move` call.
Two gates, both prospective and both limited to `tickets`-kind tickets:

- A move INTO `blocked` is refused when the ticket has no next action (a pending
  question or an open critical bug) or no owner.
- A move INTO a terminal lane runs `close_check.evaluate`. Blocks refuse the
  move. A clean verdict moves, then records the evidence counts.

Moves out of those lanes, to any other lane, or of other kinds are not evaluated.
`tickets.move` stays the raw writer (the board drag and `close-override` use it
directly).
"""

from . import audit
from . import backends as backends_mod
from . import boards as boards_mod
from . import close_check
from . import ticket_liveness
from . import tickets as tickets_mod
from .paths import find_repo_root

BLOCK_ACTION = "ticket.block"
CLOSE_ACTION = "ticket.close"

_CLOSE_HINT = ("close-check refused this move. Fix the blocks, then move again. "
               "Only a person supplies a reason to `close-override`.")


def _refuse(repo_root, ticket_id, finding):
    audit.record(repo_root, BLOCK_ACTION, target=ticket_id,
                 outcome="refused: %s" % finding["code"])
    return {"ok": False, "refused": finding["code"], "message": finding["message"],
            "hint": "fix the cause, then move again: `tracker-add` a question "
                    "(kind=questions) saying what unblocks the ticket"}


def _entering_terminal(repo_root, ticket, stage):
    """True when `stage` is a terminal lane and the ticket is not already in one."""
    if ticket is None or (ticket.get("kind") or "tickets") != "tickets":
        return False
    lanes = {lane["id"]: lane for lane in boards_mod.lanes_for("tickets", repo_root)}
    target = lanes.get(stage)
    current = lanes.get(ticket.get("stage"))
    if not target or not target.get("terminal"):
        return False
    return not (current and current.get("terminal"))


def _verdict_or_check_error(repo_root, ticket_id, now):
    try:
        return close_check.evaluate(repo_root, ticket_id, now=now)
    except Exception as exc:  # noqa: BLE001 - the evaluator is total; a leak still blocks
        return {"ok": False, "blocks": [{"code": "check_error", "level": "block",
                                          "message": "cannot check %s: %s" % (ticket_id, exc)}],
                "warnings": [], "evidence": {}}


def _refuse_close(repo_root, ticket_id, verdict):
    codes = [b.get("code") for b in verdict.get("blocks") or []]
    audit.record(repo_root, CLOSE_ACTION, target=ticket_id,
                 outcome="refused: %s" % ",".join(codes),
                 detail={"blocks": codes})
    return {"ok": False, "blocked": True, "ticket": ticket_id,
            "blocks": verdict.get("blocks") or [], "hint": _CLOSE_HINT}


def guarded_move(repo_root, ticket_id, stage, now=None):
    """Move a ticket to `stage` unless a gate refuses.

    A `blocked` refusal is `{ok: False, refused, message, hint}`. A close
    refusal is `{ok: False, blocked: True, ticket, blocks, hint}`. Either way
    nothing is written to the ticket. Otherwise the moved ticket.
    """
    repo_root = repo_root or find_repo_root()
    ticket = tickets_mod.load(repo_root, ticket_id)
    guard_blocked = (stage == "blocked" and ticket is not None
                     and (ticket.get("kind") or "tickets") == "tickets"
                     and ticket.get("stage") != "blocked")
    if guard_blocked:
        finding = ticket_liveness.blocked_refusal(repo_root, ticket_id, now=now)
        if finding:
            return _refuse(repo_root, ticket_id, finding)
    verdict = None
    if _entering_terminal(repo_root, ticket, stage):
        verdict = _verdict_or_check_error(repo_root, ticket_id, now)
        if not verdict.get("ok"):
            return _refuse_close(repo_root, ticket_id, verdict)
    result = backends_mod.default_backend().move(repo_root, ticket_id, stage)
    if guard_blocked:
        audit.record(repo_root, BLOCK_ACTION, target=ticket_id)
    if verdict is not None:
        audit.record(repo_root, CLOSE_ACTION, target=ticket_id, detail={
            "evidence": verdict.get("evidence") or {},
            "warnings": [w.get("code") for w in verdict.get("warnings") or []],
        })
    return result
