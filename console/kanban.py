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

from server import agent_backends, agents, analytics, audit, boards, context, dotenv, export, harness_lint, jobs, model_catalog, notify, overview, render, schedules, telemetry, tickets, todos_agg, trackers, verbs, worktrees  # noqa: E402
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


def cmd_verb_list(args, repo_root):
    rows = verbs.list_verbs(repo_root, ticket=args.ticket)
    print(json.dumps(rows, indent=2) if args.json else verbs.format_list(rows))


def cmd_verb_run(args, repo_root):
    out = verbs.run(repo_root, args.verb, ticket=args.ticket,
                    confirm=args.confirm, args=_parse_kv(args.set or []))
    print(json.dumps(out, indent=2, default=str))


def cmd_audit(args, repo_root):
    rows = audit.read(repo_root, limit=args.limit, action=args.action,
                      since=args.since)
    print(json.dumps(rows, indent=2) if args.json else audit.format_list(rows))


def cmd_notify_status(args, repo_root):
    print(json.dumps(notify.status(repo_root), indent=2))


def cmd_notify_test(args, repo_root):
    """Send one real message, and say plainly whether it arrived.

    A notification path you have not tested is one you find out about at the
    moment it matters, which is the moment it is least useful to discover.
    """
    state = notify.status(repo_root)
    if not state["ready"]:
        _die("notifications are not ready: %s" % state["reason"])
    out = notify.send(repo_root, "approval",
                      args.text or "Delivery Console test message.",
                      block=True)
    print(json.dumps(out, indent=2))
    if not out["sent"]:
        sys.exit(1)


def cmd_notify_chat_id(args, repo_root):
    """Print the chat ids that have talked to this bot, so one can be copied."""
    rows, error = notify.discover_chat_ids(repo_root)
    if error:
        _die(error)
    if not rows:
        _die("no chats yet — open Telegram, find your bot, and send it any "
             "message (a group needs the bot added to it first), then re-run.")
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    for row in rows:
        print("%-16s %-10s %s" % (row["chat_id"], row["type"], row["name"]))


def cmd_schedule_list(args, repo_root):
    rows = [s.describe() for s in
            sorted(schedules.registry(repo_root).values(), key=lambda s: s.id)]
    print(json.dumps(rows, indent=2) if args.json else schedules.format_list(rows))


def cmd_schedule_due(args, repo_root):
    """What would fire right now — a dry run, submitting nothing."""
    rows = [s.describe() for s in schedules.due(repo_root)]
    print(json.dumps(rows, indent=2) if args.json else
          (schedules.format_list(rows) if rows else "Nothing due this minute."))


def cmd_job_list(args, repo_root):
    rows = jobs.JobQueue(repo_root).list_jobs(state=args.state, ticket=args.ticket)
    print(json.dumps(rows, indent=2, default=str) if args.json
          else jobs.format_list(rows))


def cmd_job_show(args, repo_root):
    job = jobs.JobQueue(repo_root).get(args.job_id)
    if job is None:
        _die("no job %s" % args.job_id)
    print(json.dumps(job, indent=2, default=str))


def cmd_job_cancel(args, repo_root):
    print(json.dumps(jobs.JobQueue(repo_root).cancel(args.job_id), indent=2))


def cmd_job_submit(args, repo_root):
    # A CLI process is short-lived, so it starts its own workers and waits.
    # The queue and the gates are the same ones the server uses; only the
    # lifetime differs.
    queue = jobs.JobQueue(repo_root).start()
    try:
        job = queue.submit(args.verb, ticket=args.ticket, confirm=args.confirm,
                           args=_parse_kv(args.set or []), submitted_by="cli")
        if args.detach:
            print(json.dumps(job, indent=2, default=str))
            return
        done = queue.wait(job["id"], timeout=args.timeout)
        if done is None:
            _die("job %s did not finish within %ss; it stays queued and the "
                 "console will pick it up" % (job["id"], args.timeout))
        print(json.dumps(done, indent=2, default=str))
        if done["state"] != jobs.DONE:
            sys.exit(1)
    finally:
        queue.stop()


def cmd_worktree_list(args, repo_root):
    entries = worktrees.list_worktrees(repo_root)
    print(json.dumps(entries, indent=2) if args.json
          else worktrees.format_list(entries))


def cmd_worktree_add(args, repo_root):
    print(json.dumps(worktrees.add(repo_root, args.name, base=args.base,
                                   branch=args.branch), indent=2))


def cmd_worktree_remove(args, repo_root):
    print(json.dumps(worktrees.remove(repo_root, args.name, force=args.force),
                     indent=2))


def cmd_worktree_prune(args, repo_root):
    print(json.dumps(worktrees.prune(repo_root), indent=2))


def cmd_context(args, repo_root):
    digest = context.build(repo_root, args.ticket)
    print(json.dumps(digest, indent=2) if args.json
          else context.format_markdown(digest))


def cmd_telemetry(args, repo_root):
    summary = telemetry.summarize(
        repo_root, group=args.by, ticket=args.ticket, skill=args.skill,
        since=args.since, until=args.until)
    print(json.dumps(summary, indent=2) if args.json
          else telemetry.format_summary(summary))


def cmd_telemetry_skills(args, repo_root):
    report = telemetry.skill_usage(repo_root)
    print(json.dumps(report, indent=2) if args.json
          else telemetry.format_skill_usage(report))


def cmd_harness_lint(args, repo_root):
    findings, summary = harness_lint.lint(repo_root)
    if args.json:
        print(json.dumps({"summary": summary,
                          "findings": [f.as_dict() for f in findings]}, indent=2))
    else:
        print(harness_lint.format_report(findings, summary))
    # Warnings are judgement calls and do not fail a build unless asked —
    # a lint that fails CI on a maybe gets switched off, taking the errors
    # with it.
    failed = summary["errors"] or (args.strict and summary["warnings"])
    if failed:
        sys.exit(1)


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


def cmd_agents_models(args, repo_root):
    """Cached catalogue, or a re-fetch. Reading is offline; --refresh is the
    only path that touches the provider's network."""
    if not args.backend:
        rows = model_catalog.summary(repo_root)
        if args.json:
            print(json.dumps(rows, indent=2))
            return
        if not rows:
            print("No API providers are enabled. Only those have a model "
                  "endpoint; a CLI's shortlist lives in agents.toml.")
            return
        print("%-14s %-9s %8s  %s" % ("PROVIDER", "STATE", "MODELS", "CACHED"))
        for row in rows:
            print("%-14s %-9s %8s  %s" % (
                row["id"],
                "ready" if row["available"] else "unusable",
                row["count"] or "-",
                ("%s (%s days old)" % (row["fetched_at"], row["age_days"]))
                if row["cached"] else "never fetched"))
            if not row["available"] and row["reason"]:
                print("               %s" % row["reason"])
        return

    if args.refresh:
        rows, error = model_catalog.fetch(repo_root, args.backend)
    else:
        hit = model_catalog.cached(repo_root, args.backend)
        if hit is None:
            _resolved, why = model_catalog.resolve(repo_root, args.backend)
            rows, error = [], why or (
                "no cached catalogue for %r — run with --refresh" % args.backend)
        else:
            rows, error = hit["models"], ""

    if args.json:
        print(json.dumps({"backend": args.backend, "count": len(rows),
                          "models": rows, "error": error}, indent=2))
        return
    if error:
        print(error)
    if rows:
        print(model_catalog.format_list(rows))


def cmd_agents_doctor(args, repo_root):
    """Whether each configured backend can actually run, and why not.

    Exists because "not installed" was the console's answer to four different
    problems — a missing binary, an unset key, a server that is not running,
    and a row someone disabled — and one word for four fixes is no help at all.
    Disabled rows are included: a backend you switched off is exactly the one
    you will later forget you switched off.
    """
    rows = []
    cfg = agent_backends.load_config(repo_root, force=True)
    enabled = agent_backends.registry(repo_root, force=True)
    for raw in cfg.get("backend", []):
        bid = raw.get("id") or "?"
        if not raw.get("enabled", True):
            rows.append({"id": bid, "label": raw.get("label", bid),
                         "kind": raw.get("transport", "?"), "state": "disabled",
                         "detail": "enabled = false in %s" % agent_backends.CONFIG_REL})
            continue
        backend = enabled.get(bid)
        if backend is None:
            continue
        if backend.is_api:
            kind = "local api" if backend.is_local else "api"
            need = backend.api_key_env or "no key needed"
        else:
            kind = "cli"
            need = backend.resolved_command or backend.command
        rows.append({
            "id": bid, "label": backend.label, "kind": kind, "needs": need,
            "state": "ready" if backend.installed else "unusable",
            "detail": backend.unavailable_reason,
        })

    if args.json:
        print(json.dumps(rows, indent=2))
        return
    print("%-14s %-10s %-9s %s" % ("BACKEND", "KIND", "STATE", "NEEDS"))
    for row in rows:
        print("%-14s %-10s %-9s %s" % (row["id"], row["kind"], row["state"],
                                       row.get("needs", "")))
        if row.get("detail") and row["state"] != "ready":
            print("               %s" % row["detail"])


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

    p = agents_sub.add_parser(
        "models", help="cached model catalogue per API provider")
    p.add_argument("backend", nargs="?",
                   help="provider id; omit for a per-provider summary")
    p.add_argument("--refresh", action="store_true",
                   help="re-fetch from the provider (the only networked path)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_agents_models)

    p = agents_sub.add_parser(
        "doctor", help="what each configured backend needs, and whether it has it")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_agents_doctor)

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

    verb = sub.add_parser("verb", help="deterministic jobs that run without a model")
    verb_sub = verb.add_subparsers(dest="verb_cmd", required=True)
    p = verb_sub.add_parser("list")
    p.add_argument("--ticket", help="also report whether each verb is runnable for it")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_verb_list)

    p = verb_sub.add_parser("run")
    p.add_argument("verb")
    p.add_argument("--ticket")
    p.add_argument("--confirm", action="store_true",
                   help="required by verbs that mutate state")
    p.add_argument("--set", action="append", metavar="KEY=VALUE",
                   help="extra handler arguments")
    p.set_defaults(func=cmd_verb_run)

    p = sub.add_parser("audit", help="who started work or changed state, and from where")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--action", choices=list(audit.ACTIONS))
    p.add_argument("--since", help="ISO timestamp or date, inclusive")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_audit)

    noti = sub.add_parser("notify", help="push approvals to a phone")
    noti_sub = noti.add_subparsers(dest="notify_cmd", required=True)
    p = noti_sub.add_parser("status", help="is a parked approval able to reach you")
    p.set_defaults(func=cmd_notify_status)
    p = noti_sub.add_parser("chat-id", help="find your chat id (message the bot first)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_notify_chat_id)
    p = noti_sub.add_parser("test", help="send one real message")
    p.add_argument("--text")
    p.set_defaults(func=cmd_notify_test)

    sched = sub.add_parser("schedule", help="cron-driven verbs (the console is the clock)")
    sched_sub = sched.add_subparsers(dest="schedule_cmd", required=True)
    p = sched_sub.add_parser("list")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_schedule_list)

    p = sched_sub.add_parser("due", help="what would fire this minute (dry run)")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_schedule_due)

    job = sub.add_parser("job", help="durable queue for verb runs")
    job_sub = job.add_subparsers(dest="job_cmd", required=True)
    p = job_sub.add_parser("submit")
    p.add_argument("verb")
    p.add_argument("--ticket")
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--set", action="append", metavar="KEY=VALUE")
    p.add_argument("--detach", action="store_true",
                   help="record it and exit; the console runs it")
    p.add_argument("--timeout", type=float, default=120.0)
    p.set_defaults(func=cmd_job_submit)

    p = job_sub.add_parser("list")
    p.add_argument("--state", choices=[jobs.QUEUED, jobs.RUNNING, jobs.DONE,
                                       jobs.ERROR, jobs.CANCELLED, jobs.INTERRUPTED])
    p.add_argument("--ticket")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_job_list)

    p = job_sub.add_parser("show")
    p.add_argument("job_id")
    p.set_defaults(func=cmd_job_show)

    p = job_sub.add_parser("cancel")
    p.add_argument("job_id")
    p.set_defaults(func=cmd_job_cancel)

    wt = sub.add_parser("worktree", help="isolated git checkouts, one per run")
    wt_sub = wt.add_subparsers(dest="worktree_cmd", required=True)
    p = wt_sub.add_parser("list")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_worktree_list)

    p = wt_sub.add_parser("add")
    p.add_argument("name", help="usually a ticket id")
    p.add_argument("--base", help="commit-ish to branch from (default: config)")
    p.add_argument("--branch", help="override the configured branch pattern")
    p.set_defaults(func=cmd_worktree_add)

    p = wt_sub.add_parser("remove")
    p.add_argument("name")
    p.add_argument("--force", action="store_true",
                   help="discard uncommitted work in the worktree")
    p.set_defaults(func=cmd_worktree_remove)

    p = wt_sub.add_parser("prune", help="forget worktrees whose directories are gone")
    p.set_defaults(func=cmd_worktree_prune)

    p = sub.add_parser("context", help="one ticket's full state, in one call")
    p.add_argument("ticket")
    p.add_argument("--json", action="store_true",
                   help="machine form; default is the markdown an agent pastes")
    p.set_defaults(func=cmd_context)

    tele = sub.add_parser("telemetry", help="token and cost totals per turn")
    tele_sub = tele.add_subparsers(dest="telemetry_cmd")
    tele.add_argument("--by", choices=telemetry.GROUPS, default="ticket")
    tele.add_argument("--ticket")
    tele.add_argument("--skill")
    tele.add_argument("--since", help="ISO timestamp or date, inclusive")
    tele.add_argument("--until", help="ISO timestamp or date, inclusive")
    tele.add_argument("--json", action="store_true")
    tele.set_defaults(func=cmd_telemetry)

    p = tele_sub.add_parser("skills",
                            help="invocation count per skill, and what never fired")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_telemetry_skills)

    harness = sub.add_parser("harness", help="checks over .claude/ skills and agents")
    harness_sub = harness.add_subparsers(dest="harness_cmd", required=True)
    p = harness_sub.add_parser("lint", help="frontmatter, dead paths, orphan skills")
    p.add_argument("--json", action="store_true")
    p.add_argument("--strict", action="store_true",
                   help="exit non-zero on warnings too, not just errors")
    p.set_defaults(func=cmd_harness_lint)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = find_repo_root()
    except RepoRootError as exc:
        _die(str(exc))
        return
    # Before anything reads a key. Loaded here rather than in each module so
    # `notify test`, `agents launch` and a served session all see the same
    # environment. A variable already exported always wins — see dotenv.py.
    dotenv.load(repo_root)
    try:
        args.func(args, repo_root)
    except (FileNotFoundError, FileExistsError, ValueError, KeyError, TimeoutError) as exc:
        # VerbError subclasses ValueError, so a failed gate reports as a clean
        # one-line error rather than a traceback.
        _die(str(exc))


if __name__ == "__main__":
    main()
