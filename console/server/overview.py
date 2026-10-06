"""Overview tab: a landing dashboard aggregated from board/tracker data.

Owns no storage. Everything here is derived, and every number is something
you can click through to on a board — a stat you can't drill into is
decoration.

Deliberately dropped from the fork's version: the Setup checklist (identity
resolution against a people roster, CLI/OAuth connection state) and the
release-gap panel, both of which depended on project-specific
infrastructure this template doesn't have.
"""

from datetime import datetime, timezone

from . import agent_approvals
from . import analytics as analytics_mod
from . import boards as boards_mod
from . import render
from . import runs as runs_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod

_ATTN_RUNS = ("failed", "timed_out", "scheduled_retry")
_NEEDS_YOU_CAP = 50
_REPAIR_CAP = 8


def _stale_days(repo_root):
    return boards_mod.load_console_config(repo_root)["general"].get("stale_days", 7)


def _entry(ticket_id, title, kind, stage, **extra):
    row = {"id": ticket_id, "title": title, "kind": kind, "stage": stage,
           "idle_days": 0, "blocking": 0, "owner": "", "href": "board"}
    row.update(extra)
    return row


def needs_attention(repo_root):
    """What a person should look at. The same payload feeds the Overview
    panels and the sidebar badge, in two lists. needs_you is what only a
    person can resolve: open questions and live approval cards (cap 50,
    exact count). needs_repair is what the work or a run must fix: blocked,
    stale and unowned tickets, answered-not-applied questions, and runs that
    failed or are waiting to retry (cap 8 per group). The legacy per-kind
    keys stay; `questions` is open-only and `answered` holds the rest.
    Read-only: nothing here changes a tracker, run or approval."""
    stale_days = _stale_days(repo_root)
    blocked, stale, unowned, questions, answered = [], [], [], [], []

    for kind in boards_mod.enabled_boards(repo_root):
        lanes = {l["id"]: l for l in boards_mod.lanes_for(kind, repo_root)}
        show = boards_mod.show_trackers_for(kind, repo_root)
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
            lane = lanes.get(ticket.get("stage"), {})
            if lane.get("terminal"):
                continue  # finished work is not "attention"
            card = render.build_card(ticket, repo_root, show, stale_days)
            entry = _entry(card["id"], card["title"], kind, ticket.get("stage"),
                           idle_days=card["idle_days"], blocking=card["blocking"],
                           owner=card["owner"])
            if card["blocking"]:
                blocked.append(entry)
            if card["stale"]:
                stale.append(entry)
            if not card["owner"]:
                unowned.append(entry)
            if "questions" in show:
                for item in trackers_mod.list_items(repo_root, card["id"], "questions"):
                    status = item.get("status")
                    if status not in ("open", "answered"):
                        continue
                    row = _entry(
                        card["id"], item.get("text") or item.get("id"), kind,
                        status or "open", type="question" if status == "open" else "answered",
                        ref=item.get("id") or "", priority=item.get("priority") or "medium")
                    (questions if status == "open" else answered).append(row)

    approvals = []
    for card in agent_approvals.REGISTRY.pending_all():
        approvals.append(_entry(card["chat"], card["tool"], "agents", "approval",
                                href="agents", type="approval"))

    runs = []
    try:
        for rec in runs_mod.list_runs(repo_root):
            if rec.get("state") not in _ATTN_RUNS:
                continue
            ticket = rec.get("ticket") or ""
            runs.append(_entry(
                ticket or rec["id"],
                "Run %s is %s" % (rec["id"], rec.get("state")),
                "tickets" if ticket else "agents",
                rec.get("state") or "",
                href="board" if ticket else "agents", type="run"))
    except OSError:
        runs = []

    blocked.sort(key=lambda e: -e["blocking"])
    stale.sort(key=lambda e: -(e["idle_days"] or 0))
    questions.sort(key=lambda e: 0 if e["priority"] == "critical" else 1)  # stable
    needs_you = (approvals + questions)[:_NEEDS_YOU_CAP]
    groups = (("blocked", blocked), ("stale", stale), ("unowned", unowned),
              ("answered", answered), ("run", runs))
    needs_repair = [dict(e, type=t) if t in ("blocked", "stale", "unowned") else e
                    for t, rows in groups for e in rows[:_REPAIR_CAP]]
    return {
        "needs_you": needs_you,
        "needs_repair": needs_repair,
        "blocked": blocked[:_REPAIR_CAP],
        "stale": stale[:_REPAIR_CAP],
        "unowned": unowned[:_REPAIR_CAP],
        "questions": questions[:_REPAIR_CAP],
        "answered": answered[:_REPAIR_CAP],
        "approvals": approvals[:_REPAIR_CAP],
        "runs": runs[:_REPAIR_CAP],
        "counts": {
            "blocked": len(blocked), "stale": len(stale), "unowned": len(unowned),
            "questions": len(questions), "answered": len(answered),
            "approvals": len(approvals), "runs": len(runs),
            "needs_you": len(approvals) + len(questions),
            "needs_repair": sum(len(rows) for _, rows in groups),
        },
    }


def recently_touched(repo_root, limit=9):
    rows = []
    for kind in boards_mod.enabled_boards(repo_root):
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
            rows.append(
                {
                    "id": ticket["id"],
                    "title": ticket["title"],
                    "kind": kind,
                    "stage": ticket.get("stage"),
                    "updated": ticket.get("updated", ""),
                    "owner": ticket.get("owner", ""),
                }
            )
    rows.sort(key=lambda r: r["updated"], reverse=True)
    return rows[:limit]


def headline_stats(repo_root):
    """The four numbers worth a tile. Each maps to a place you can go."""
    open_total = 0
    terminal_total = 0
    tracker_open = 0
    for kind in boards_mod.enabled_boards(repo_root):
        view = render.board_view(kind, repo_root)
        open_total += view["open_total"]
        terminal_total += view["total"] - view["open_total"]
        for lane in view["lanes"]:
            for card in lane["cards"]:
                tracker_open += sum(card["trackers"].values())
    return {
        "open": open_total,
        "done": terminal_total,
        "tracker_open": tracker_open,
    }


def full_overview(repo_root, now=None):
    """`now` (a datetime) is injectable for tests; `generated_at` is UTC,
    same format as trackers._now_iso."""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "generated_at": stamp,
        "stats": headline_stats(repo_root),
        "attention": needs_attention(repo_root),
        "flow": analytics_mod.lane_funnel(repo_root),
        "recent": recently_touched(repo_root),
        "stale_days": _stale_days(repo_root),
    }
