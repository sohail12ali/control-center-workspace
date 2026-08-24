"""Board/ticket view-model builders shared by the HTTP server and the
static exporter, so there is exactly one rendering path for both.

View-models are built here rather than in the frontend so the static export
and the live API are byte-identical in shape, and so the "is this card
flagged / stale / over WIP" rules exist once instead of once per client.
"""

import datetime
import os

from . import boards as boards_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod

_CLOSED_STATUSES = ("resolved", "closed", "verified", "done", "dropped")
_CRITICAL = ("critical", "high")


def boards_index(repo_root):
    return [
        {"kind": k, "label": boards_mod.board_label(k, repo_root)}
        for k in boards_mod.enabled_boards(repo_root)
    ]


def _days_since(date_str):
    if not date_str:
        return None
    try:
        d = datetime.date.fromisoformat(str(date_str))
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def _open_items(repo_root, ticket_id, kind):
    return [
        it
        for it in trackers_mod.list_items(repo_root, ticket_id, kind)
        if it.get("status") not in _CLOSED_STATUSES
    ]


def build_card(ticket, repo_root, show_trackers, stale_days):
    """One board card. Everything the card shows is computed here — the
    frontend renders, it does not decide."""
    idle = _days_since(ticket.get("updated"))
    card = {
        "id": ticket["id"],
        "title": ticket["title"],
        "owner": ticket.get("owner", ""),
        "priority": tickets_mod.normalise_priority(ticket.get("priority")),
        "url": ticket.get("url", ""),
        "updated": ticket.get("updated", ""),
        "created": ticket.get("created", ""),
        "tags": ticket.get("tags", []),
        "idle_days": idle,
        "stale": idle is not None and idle >= stale_days,
        "has_scripts": bool(ticket.get("scripts_dir"))
        or os.path.isdir(os.path.join(tickets_mod.dir_for(repo_root, ticket["id"]), "ticket-scripts")),
    }
    counts, blocking = {}, 0
    for tracker_kind in show_trackers:
        items = _open_items(repo_root, ticket["id"], tracker_kind)
        counts[tracker_kind] = len(items)
        blocking += sum(
            1
            for it in items
            if it.get("priority") in _CRITICAL or it.get("severity") in _CRITICAL
        )
    card["trackers"] = counts
    card["blocking"] = blocking
    return card


def board_view(kind, repo_root):
    lanes = boards_mod.lanes_for(kind, repo_root)
    show_trackers = boards_mod.show_trackers_for(kind, repo_root)
    stale_days = boards_mod.load_console_config(repo_root)["general"].get("stale_days", 7)

    by_stage = {lane["id"]: [] for lane in lanes}
    orphans = []
    for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
        card = build_card(ticket, repo_root, show_trackers, stale_days)
        stage = ticket.get("stage")
        if stage in by_stage:
            by_stage[stage].append(card)
        else:
            # A stage no lane declares — surfaced rather than dropped, since a
            # silently invisible ticket is the worst possible failure here.
            card["unknown_stage"] = stage
            orphans.append(card)

    for cards in by_stage.values():
        cards.sort(key=lambda c: (-c["blocking"], -(c["idle_days"] or 0)))

    lane_views = []
    for lane in lanes:
        cards = by_stage.get(lane["id"], [])
        lane_views.append(
            {
                "id": lane["id"],
                "label": lane["label"],
                "terminal": lane["terminal"],
                "tone": lane["tone"],
                "wip": lane["wip"],
                "over_wip": bool(lane["wip"]) and len(cards) > lane["wip"],
                "cards": cards,
            }
        )

    total = sum(len(l["cards"]) for l in lane_views) + len(orphans)
    return {
        "kind": kind,
        "label": boards_mod.board_label(kind, repo_root),
        "blurb": boards_mod.load_board_config(kind, repo_root).get("board", {}).get("blurb", ""),
        "lanes": lane_views,
        "orphans": orphans,
        "total": total,
        "open_total": sum(len(l["cards"]) for l in lane_views if not l["terminal"]),
        "stale_days": stale_days,
    }


def ticket_view(ticket_id, repo_root):
    ticket = tickets_mod.load(repo_root, ticket_id)
    if ticket is None:
        return None
    result = dict(ticket)
    result["trackers"] = {
        kind: trackers_mod.list_items(repo_root, ticket_id, kind)
        for kind in trackers_mod.VALID_KINDS
    }
    result["idle_days"] = _days_since(ticket.get("updated"))
    result["lanes"] = boards_mod.lanes_for(ticket.get("kind", "tickets"), repo_root)
    result["artifacts"] = tickets_mod.list_artifacts(repo_root, ticket_id)
    return result
