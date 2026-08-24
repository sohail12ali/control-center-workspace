"""Pure-function analytics derived from board/tracker data (always available)
and worklog data (available once log-work files exist). Every function here
is generic board/worklog math — no ShopLC-style release-packaging charts
(those depended on the Files/Releases tabs, which this template doesn't
implement)."""

import datetime

from . import boards as boards_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod
from . import worklog as worklog_mod

_CLOSED_STATUSES = ("resolved", "closed", "verified", "done", "dropped")


def _all_tickets(repo_root):
    tickets = []
    for kind in boards_mod.enabled_boards(repo_root):
        tickets.extend(tickets_mod.list_tickets(repo_root, kind=kind))
    return tickets


def lane_funnel(repo_root):
    """Ticket count per lane, per enabled board kind. Carries each lane's
    terminal/tone flags so a caller can colour or exclude finished lanes
    without re-reading the board config."""
    out = {}
    for kind in boards_mod.enabled_boards(repo_root):
        lanes = boards_mod.lanes_for(kind, repo_root)
        counts = {lane["id"]: 0 for lane in lanes}
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
            stage = ticket.get("stage")
            if stage in counts:
                counts[stage] += 1
        out[kind] = [
            {
                "lane": lane["id"],
                "label": lane["label"],
                "count": counts.get(lane["id"], 0),
                "terminal": lane["terminal"],
                "tone": lane["tone"],
            }
            for lane in lanes
        ]
    return out


def days_since(date_str):
    if not date_str:
        return None
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def idle_by_lane(repo_root):
    """Median/max idle days (since 'updated') per lane, per board kind."""
    out = {}
    for kind in boards_mod.enabled_boards(repo_root):
        by_lane = {}
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
            idle = days_since(ticket.get("updated"))
            if idle is None:
                continue
            by_lane.setdefault(ticket.get("stage"), []).append(idle)
        out[kind] = {
            lane: {"median": sorted(vals)[len(vals) // 2], "max": max(vals), "count": len(vals)}
            for lane, vals in by_lane.items()
            if vals
        }
    return out


def flag_bars(repo_root):
    """Count of tickets with an open critical blocker (question/bug) per kind."""
    out = {}
    for kind in boards_mod.enabled_boards(repo_root):
        flagged = 0
        total = 0
        for ticket in tickets_mod.list_tickets(repo_root, kind=kind):
            total += 1
            if trackers_mod.blockers(repo_root, ticket["id"]):
                flagged += 1
        out[kind] = {"flagged": flagged, "total": total}
    return out


def stage_mix(repo_root):
    """What fraction of all enabled-board tickets sit in each board kind."""
    counts = {kind: len(tickets_mod.list_tickets(repo_root, kind=kind)) for kind in boards_mod.enabled_boards(repo_root)}
    total = sum(counts.values()) or 1
    return {kind: {"count": n, "pct": round(100 * n / total, 1)} for kind, n in counts.items()}


def throughput(repo_root, weeks=8):
    """Tickets whose stage is a 'closed-shaped' lane (done/closed/verify's
    terminal lane), bucketed by ISO week of 'updated'. Best-effort — this
    template has no explicit closed-timestamp field, so it uses the last
    update on a terminal-lane ticket as a proxy."""
    terminal_lanes = {"done", "closed", "verified"}
    buckets = {}
    for ticket in _all_tickets(repo_root):
        if ticket.get("stage") not in terminal_lanes:
            continue
        updated = ticket.get("updated")
        if not updated:
            continue
        try:
            d = datetime.date.fromisoformat(updated)
        except ValueError:
            continue
        iso = d.isocalendar()
        key = f"{iso[0]}-W{iso[1]:02d}"
        buckets[key] = buckets.get(key, 0) + 1
    return dict(sorted(buckets.items())[-weeks:])


def worklog_charts(repo_root, start_date, end_date, author_slug=None):
    return worklog_mod.range_summary(repo_root, start_date, end_date, author_slug=author_slug)


def full_report(repo_root, window_days=30, author_slug=None, include_worklog=True):
    end = datetime.date.today()
    start = end - datetime.timedelta(days=window_days)
    report = {
        "lane_funnel": lane_funnel(repo_root),
        "idle_by_lane": idle_by_lane(repo_root),
        "flag_bars": flag_bars(repo_root),
        "stage_mix": stage_mix(repo_root),
        "throughput": throughput(repo_root),
        "window_days": window_days,
    }
    # The work plugin can be disabled independently; when it is, say so
    # rather than shipping an empty chart that reads as "nobody logged time".
    report["worklog"] = (
        worklog_charts(repo_root, start.isoformat(), end.isoformat(), author_slug)
        if include_worklog
        else None
    )
    return report
