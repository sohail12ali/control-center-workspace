"""One call that tells an agent everything it needs to start a turn.

## The saving

`trace-context` currently opens a ticket's artifacts one by one — seven or eight
files, most of them read in full — at the start of every turn, and then the model
re-derives the same conclusions it derived last turn: which tasks are unchecked,
whether anything is blocking, what happened most recently. That is a large,
repeated, entirely mechanical cost.

This module computes those conclusions once, in Python, and returns them as a
digest small enough to paste into a prompt. The model reads a paragraph instead
of eight files, and reads *facts* rather than raw material it has to reduce.

## Composition, not reimplementation

Everything here is assembled from the readers that already own each fact —
`tickets`, `trackers`, `telemetry`, `boards`. Nothing is recomputed from the
filesystem in a second way. That is deliberate: a digest that derives lane or
blocker state by its own route is a second source of truth, and it will
eventually disagree with the board over something that matters.

The two exceptions are plan tasks and progress entries, which live in markdown
that nothing else parses. Both parsers are narrow, and both report what they
could not parse rather than guessing.

## Truncation is stated, never silent

Every section has a cap. When a cap bites, the digest says how many items it
dropped. A digest that quietly omits the newest blocker is worse than one that
is honestly incomplete, because the reader cannot tell the difference.
"""

import os
import re

from . import boards as boards_mod
from . import telemetry as telemetry_mod
from . import tickets as tickets_mod
from . import trackers as trackers_mod

#: Section caps. Small on purpose: this is a prompt payload, not a report.
MAX_TRACKER_ITEMS = 8
MAX_OPEN_TASKS = 12
MAX_PROGRESS_ENTRIES = 3
MAX_PROGRESS_CHARS = 600

_TASK_RE = re.compile(r"^###\s*\[( |x|X)\]\s*(\S+)\s*(?:[-—–]\s*)?(.*)$")
_DATED_RE = re.compile(r"^###\s+(\d{4}-\d{2}-\d{2})\s*$")


def _artifact_path(repo_root, ticket_id, name):
    folder = tickets_mod.dir_for(repo_root, ticket_id)
    return os.path.join(folder, "%s-%s.md" % (ticket_id, name))


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


# ----------------------------------------------------------------- plan -----

def plan_tasks(repo_root, ticket_id):
    """[{id, title, done}] parsed from `### [ ] {id} — {title}` headings.

    Returns `parsed: False` when the plan exists but contains no task headings
    at all — an empty task list and an unparseable plan are different facts,
    and an agent told "no open tasks" about a plan it cannot read will do the
    wrong thing confidently.
    """
    text = _read(_artifact_path(repo_root, ticket_id, "plan"))
    if not text:
        return {"parsed": False, "exists": False, "tasks": []}
    tasks = []
    for line in text.splitlines():
        match = _TASK_RE.match(line.strip())
        if not match:
            continue
        mark, task_id, title = match.groups()
        tasks.append({
            "id": task_id.strip(),
            "title": re.sub(r"\s*\(\s*[\d.]+\s*h\s*\)\s*$", "", title).strip(),
            "done": mark.lower() == "x",
        })
    return {"parsed": bool(tasks), "exists": True, "tasks": tasks}


# ------------------------------------------------------------- progress -----

def recent_progress(repo_root, ticket_id, limit=MAX_PROGRESS_ENTRIES):
    """The most recent dated entries from progress.md, newest first."""
    text = _read(_artifact_path(repo_root, ticket_id, "progress"))
    if not text:
        return []
    entries, current = [], None
    for line in text.splitlines():
        match = _DATED_RE.match(line.strip())
        if match:
            current = {"date": match.group(1), "lines": []}
            entries.append(current)
        elif current is not None and line.strip():
            current["lines"].append(line.rstrip())
    out = []
    for entry in reversed(entries[-limit:]):
        body = "\n".join(entry["lines"]).strip()
        truncated = len(body) > MAX_PROGRESS_CHARS
        out.append({
            "date": entry["date"],
            "text": body[:MAX_PROGRESS_CHARS],
            "truncated": truncated,
        })
    return out


# -------------------------------------------------------------- digest ------

def build(repo_root, ticket_id):
    """The whole picture for one ticket, as plain data."""
    ticket = tickets_mod.load(repo_root, ticket_id)
    if ticket is None:
        raise FileNotFoundError("no ticket.toml for %s" % ticket_id)

    kind = ticket.get("kind") or "tickets"
    try:
        lanes = {l["id"]: l for l in boards_mod.lanes_for(kind, repo_root)}
    except ValueError:
        lanes = {}
    lane = lanes.get(ticket.get("stage") or "", {})

    trackers = {}
    for tracker_kind in trackers_mod.VALID_KINDS:
        items = trackers_mod.list_items(repo_root, ticket_id, tracker_kind,
                                        status="open")
        trackers[tracker_kind] = {
            "open": len(items),
            "items": [{"id": i.get("id"), "text": i.get("text", "")}
                      for i in items[:MAX_TRACKER_ITEMS]],
            "omitted": max(0, len(items) - MAX_TRACKER_ITEMS),
        }

    plan = plan_tasks(repo_root, ticket_id)
    open_tasks = [t for t in plan["tasks"] if not t["done"]]

    spend = telemetry_mod.summarize(repo_root, group="ticket", ticket=ticket_id)

    return {
        "ticket": {
            "id": ticket.get("id"),
            "title": ticket.get("title", ""),
            "kind": kind,
            "stage": ticket.get("stage", ""),
            "stage_label": lane.get("label", ticket.get("stage", "")),
            "terminal": bool(lane.get("terminal")),
            "status": ticket.get("status", ""),
            "owner": ticket.get("owner", ""),
            "priority": ticket.get("priority", ""),
            "created": ticket.get("created", ""),
            "updated": ticket.get("updated", ""),
        },
        "artifacts": tickets_mod.list_artifacts(repo_root, ticket_id),
        "trackers": trackers,
        "blockers": trackers_mod.blockers(repo_root, ticket_id),
        "plan": {
            "exists": plan["exists"],
            "parsed": plan["parsed"],
            "total": len(plan["tasks"]),
            "done": len(plan["tasks"]) - len(open_tasks),
            "open": open_tasks[:MAX_OPEN_TASKS],
            "omitted": max(0, len(open_tasks) - MAX_OPEN_TASKS),
        },
        "progress": recent_progress(repo_root, ticket_id),
        "spend": spend["totals"],
    }


def format_markdown(digest):
    """The digest as the compact markdown an agent actually consumes."""
    t = digest["ticket"]
    out = ["# %s — %s" % (t["id"], t["title"] or "(untitled)")]
    out.append("")
    out.append("**Lane** %s%s · **Status** %s · **Owner** %s · **Priority** %s"
               % (t["stage_label"] or "?", " (terminal)" if t["terminal"] else "",
                  t["status"] or "?", t["owner"] or "unassigned",
                  t["priority"] or "?"))
    out.append("**Updated** %s · **Created** %s" % (t["updated"], t["created"]))

    blockers = digest["blockers"]
    out.append("")
    if blockers:
        out.append("## BLOCKED")
        for kind, items in sorted(blockers.items()):
            for item in items:
                out.append("- **%s** %s — %s" % (kind[:-1].upper(),
                                                 item.get("id", "?"),
                                                 item.get("text", "")))
    else:
        out.append("**No blockers.**")

    plan = digest["plan"]
    out.append("")
    out.append("## Plan")
    if not plan["exists"]:
        out.append("No plan artifact.")
    elif not plan["parsed"]:
        out.append("Plan exists but no `### [ ] {id} — {title}` task headings were "
                   "found. Read it directly before assuming there is no work.")
    else:
        out.append("%d/%d tasks done." % (plan["done"], plan["total"]))
        for task in plan["open"]:
            out.append("- [ ] %s — %s" % (task["id"], task["title"]))
        if plan["omitted"]:
            out.append("- ...and %d more open task(s) not shown." % plan["omitted"])

    out.append("")
    out.append("## Open trackers")
    any_open = False
    for kind in ("questions", "bugs", "todos"):
        section = digest["trackers"][kind]
        if not section["open"]:
            continue
        any_open = True
        out.append("**%s (%d)**" % (kind, section["open"]))
        for item in section["items"]:
            out.append("- %s %s" % (item["id"], item["text"]))
        if section["omitted"]:
            out.append("- ...and %d more not shown." % section["omitted"])
    if not any_open:
        out.append("None open.")

    out.append("")
    out.append("## Artifacts")
    files = digest["artifacts"].get("files", [])
    out.append(", ".join(f["artifact"] for f in files) if files else "None.")

    progress = digest["progress"]
    if progress:
        out.append("")
        out.append("## Recent progress")
        for entry in progress:
            out.append("### %s" % entry["date"])
            out.append(entry["text"])
            if entry["truncated"]:
                out.append("_(entry truncated — read the artifact for the rest)_")

    spend = digest["spend"]
    if spend.get("turns"):
        cost = "$%.4f" % spend["cost_usd"]
        if not spend.get("cost_complete"):
            cost += " (partial — %d turn(s) unpriced)" % spend["unpriced_turns"]
        out.append("")
        out.append("## Spend to date")
        out.append("%d turns · %d tokens · %s"
                   % (spend["turns"], spend["tokens"], cost))

    return "\n".join(out)
