#!/usr/bin/env python3
"""Delivery Console CLI. python console/kanban.py <verb> ...

Stdlib-only. See console/README.md for the full verb list and console/config/
for board-kind and id-pattern configuration. Ticket/tracker files are TOML,
mutated only through this CLI (or the HTTP API it shares code with) — never
hand-edited.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import datetime  # noqa: E402

from server import agents, analytics, boards, export, overview, render, tickets, todos_agg, trackers  # noqa: E402
from server import worklog as worklog_mod  # noqa: E402
from server import vault as vault_mod  # noqa: E402
from server.paths import RepoRootError, find_repo_root  # noqa: E402


def _die(msg):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def _parse_kv(pairs):
    out = {}
    for pair in pairs:
        if "=" not in pair:
            _die(f"--set expects key=value, got: {pair!r}")
        key, _, value = pair.partition("=")
        out[key] = value
    return out


def cmd_ticket_create(args, repo_root):
    ticket = tickets.create(
        repo_root, args.id, args.title, kind=args.kind, owner=args.owner or "",
        priority=args.priority, url=args.url or ""
    )
    print(json.dumps(ticket, indent=2))


def cmd_ticket_list(args, repo_root):
    rows = tickets.list_tickets(repo_root, kind=args.kind, stage=args.stage, owner=args.owner)
    print(json.dumps(rows, indent=2))


def cmd_ticket_show(args, repo_root):
    result = render.ticket_view(args.id, repo_root)
    if result is None:
        _die(f"no ticket.toml for {args.id}")
    print(json.dumps(result, indent=2))


def cmd_ticket_move(args, repo_root):
    print(json.dumps(tickets.move(repo_root, args.id, args.stage), indent=2))


def cmd_ticket_set(args, repo_root):
    print(json.dumps(tickets.set_field(repo_root, args.id, args.field, args.value), indent=2))


def cmd_tracker_add(args, repo_root):
    extra = _parse_kv(args.set)
    item = trackers.add(repo_root, args.id, args.kind, args.text, **extra)
    print(json.dumps(item, indent=2))


def cmd_tracker_list(args, repo_root):
    items = trackers.list_items(repo_root, args.id, args.kind, status=args.status)
    print(json.dumps(items, indent=2))


def cmd_tracker_update(args, repo_root):
    extra = _parse_kv(args.set)
    item = trackers.update(repo_root, args.id, args.kind, args.item_id, **extra)
    print(json.dumps(item, indent=2))


def cmd_tracker_blockers(args, repo_root):
    print(json.dumps(trackers.blockers(repo_root, args.id), indent=2))


def cmd_onboard(args, repo_root):
    from server import onboarding

    r = onboarding.report(repo_root)
    if args.json:
        print(json.dumps(r, indent=2))
        return
    mark = {"ok": "[x]", "todo": "[ ]", "warn": "[!]", "fail": "[X]"}
    print("Setup: %d/%d" % (r["done"], r["total"]))
    print()
    for s in r["steps"]:
        print(" %s %-22s %s" % (mark.get(s["status"], "[ ]"), s["title"], s["detail"]))
        if s.get("hint"):
            print("     -> %s" % s["hint"])
        if s.get("chain") and s["status"] != "ok":
            print("     chain: %s" % " -> ".join("/" + c for c in s["chain"]))
    if not r["complete"]:
        print()
        print("Next: %s" % r["next"])


def cmd_overview(args, repo_root):
    print(json.dumps(overview.full_overview(repo_root), indent=2))


def cmd_todos(args, repo_root):
    print(json.dumps(todos_agg.all_todos(repo_root, status=args.status, owner=args.owner), indent=2))


def cmd_work_day(args, repo_root):
    date = args.date or datetime.date.today().isoformat()
    print(json.dumps(worklog_mod.day_timesheet(repo_root, date, author_slug=args.author), indent=2))


def cmd_work_range(args, repo_root):
    end = args.end or datetime.date.today().isoformat()
    start = args.start or (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    print(json.dumps(worklog_mod.range_summary(repo_root, start, end, author_slug=args.author), indent=2))


def cmd_analytics(args, repo_root):
    print(json.dumps(analytics.full_report(repo_root, window_days=args.window, author_slug=args.author), indent=2))


def cmd_vault_tree(args, repo_root):
    print(json.dumps(vault_mod.list_tree(repo_root, args.path), indent=2))


def cmd_vault_file(args, repo_root):
    print(json.dumps(vault_mod.read_file(repo_root, args.path), indent=2))


def cmd_vault_graph(args, repo_root):
    print(json.dumps(vault_mod.build_graph(repo_root), indent=2))


def cmd_agents_backends(args, repo_root):
    print(json.dumps(agents.list_backends(repo_root), indent=2))


def cmd_agents_catalog(args, repo_root):
    print(json.dumps(agents.list_catalog(repo_root), indent=2))


def cmd_agents_launch(args, repo_root):
    print(json.dumps(agents.launch(repo_root, args.backend, args.prompt, cwd=args.cwd), indent=2))


def cmd_agents_jobs(args, repo_root):
    print(json.dumps(agents.list_jobs(repo_root), indent=2))


def cmd_agents_show(args, repo_root):
    job = agents.get_job(repo_root, args.job_id)
    if job is None:
        _die(f"no such job: {args.job_id}")
    print(json.dumps(job, indent=2))


def cmd_agents_stop(args, repo_root):
    print(json.dumps(agents.stop_job(repo_root, args.job_id), indent=2))


def cmd_serve(args, repo_root):
    from server import httpd

    httpd.serve(repo_root, host=args.host, port=args.port)


def cmd_export(args, repo_root):
    path = export.export_static(repo_root, args.out)
    print(f"exported to {path}")


def cmd_refresh(args, repo_root):
    # Cheap re-index: touch every board's ticket list once so a broken
    # config/data file surfaces immediately instead of silently on next use.
    try:
        for kind in boards.enabled_boards(repo_root):
            tickets.list_tickets(repo_root, kind=kind)
    except Exception as exc:  # noqa: BLE001 - hooks must never crash a session
        if not args.quiet:
            print(f"refresh warning: {exc}", file=sys.stderr)
        return
    if not args.quiet:
        print("console: refreshed")


def build_parser():
    parser = argparse.ArgumentParser(prog="kanban.py")
    sub = parser.add_subparsers(dest="group", required=True)

    ticket = sub.add_parser("ticket", help="ticket.toml operations")
    ticket_sub = ticket.add_subparsers(dest="action", required=True)

    p = ticket_sub.add_parser("create")
    p.add_argument("id")
    p.add_argument("--title", required=True)
    p.add_argument("--kind", default="tickets")
    p.add_argument("--owner", default="")
    p.add_argument("--priority", default=tickets.DEFAULT_PRIORITY, choices=tickets.PRIORITIES)
    p.add_argument("--url", default="", help="link to this ticket in an external tracker")
    p.set_defaults(func=cmd_ticket_create)

    p = ticket_sub.add_parser("list")
    p.add_argument("--kind")
    p.add_argument("--stage")
    p.add_argument("--owner")
    p.set_defaults(func=cmd_ticket_list)

    p = ticket_sub.add_parser("show")
    p.add_argument("id")
    p.set_defaults(func=cmd_ticket_show)

    p = ticket_sub.add_parser("move")
    p.add_argument("id")
    p.add_argument("stage")
    p.set_defaults(func=cmd_ticket_move)

    p = ticket_sub.add_parser("set")
    p.add_argument("id")
    p.add_argument("field")
    p.add_argument("value")
    p.set_defaults(func=cmd_ticket_set)

    tracker = sub.add_parser("tracker", help="questions/bugs/todos operations")
    tracker_sub = tracker.add_subparsers(dest="action", required=True)

    p = tracker_sub.add_parser("add")
    p.add_argument("id")
    p.add_argument("kind", choices=trackers.VALID_KINDS)
    p.add_argument("text")
    p.add_argument("--set", action="append", default=[], help="extra field, key=value (repeatable)")
    p.set_defaults(func=cmd_tracker_add)

    p = tracker_sub.add_parser("list")
    p.add_argument("id")
    p.add_argument("kind", choices=trackers.VALID_KINDS)
    p.add_argument("--status")
    p.set_defaults(func=cmd_tracker_list)

    p = tracker_sub.add_parser("update")
    p.add_argument("id")
    p.add_argument("kind", choices=trackers.VALID_KINDS)
    p.add_argument("item_id")
    p.add_argument("--set", action="append", default=[], help="field to change, key=value (repeatable)")
    p.set_defaults(func=cmd_tracker_update)

    p = tracker_sub.add_parser("blockers")
    p.add_argument("id")
    p.set_defaults(func=cmd_tracker_blockers)

    p = sub.add_parser("onboard", help="first-run setup steps, ending at the requirements pipeline")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_onboard)

    p = sub.add_parser("overview")
    p.set_defaults(func=cmd_overview)

    p = sub.add_parser("todos")
    p.add_argument("--status")
    p.add_argument("--owner")
    p.set_defaults(func=cmd_todos)

    work = sub.add_parser("work", help="worklog/timesheet operations")
    work_sub = work.add_subparsers(dest="action", required=True)

    p = work_sub.add_parser("day")
    p.add_argument("--date")
    p.add_argument("--author")
    p.set_defaults(func=cmd_work_day)

    p = work_sub.add_parser("range")
    p.add_argument("--start")
    p.add_argument("--end")
    p.add_argument("--author")
    p.set_defaults(func=cmd_work_range)

    p = sub.add_parser("analytics")
    p.add_argument("--window", type=int, default=30)
    p.add_argument("--author")
    p.set_defaults(func=cmd_analytics)

    vault = sub.add_parser("vault", help="knowledge-center graph/tree/file operations")
    vault_sub = vault.add_subparsers(dest="action", required=True)

    p = vault_sub.add_parser("tree")
    p.add_argument("--path", default="")
    p.set_defaults(func=cmd_vault_tree)

    p = vault_sub.add_parser("file")
    p.add_argument("--path", required=True)
    p.set_defaults(func=cmd_vault_file)

    p = vault_sub.add_parser("graph")
    p.set_defaults(func=cmd_vault_graph)

    agents_cmd = sub.add_parser("agents", help="agent backend/job operations")
    agents_sub = agents_cmd.add_subparsers(dest="action", required=True)

    p = agents_sub.add_parser("backends")
    p.set_defaults(func=cmd_agents_backends)

    p = agents_sub.add_parser("catalog")
    p.set_defaults(func=cmd_agents_catalog)

    p = agents_sub.add_parser("launch")
    p.add_argument("backend")
    p.add_argument("prompt")
    p.add_argument("--cwd")
    p.set_defaults(func=cmd_agents_launch)

    p = agents_sub.add_parser("jobs")
    p.set_defaults(func=cmd_agents_jobs)

    p = agents_sub.add_parser("show")
    p.add_argument("job_id")
    p.set_defaults(func=cmd_agents_show)

    p = agents_sub.add_parser("stop")
    p.add_argument("job_id")
    p.set_defaults(func=cmd_agents_stop)

    p = sub.add_parser("serve")
    p.add_argument("--host")
    p.add_argument("--port", type=int)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("export")
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("refresh")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_refresh)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = find_repo_root()
    except RepoRootError as exc:
        _die(str(exc))
        return
    try:
        args.func(args, repo_root)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError, TimeoutError) as exc:
        _die(str(exc))


if __name__ == "__main__":
    main()
