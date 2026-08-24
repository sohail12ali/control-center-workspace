"""Work plugin: read-only timesheet over log-work's existing daily files."""

import datetime

from .. import worklog as worklog_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.provide("worklog", worklog_mod)
    ctx.register_tab(
        "work", label="Work", short="Log", icon="clock", group="main", needs_live=True, badge=True
    )

    def day(req):
        date = req.query.get("date") or datetime.date.today().isoformat()
        return {
            "date": date,
            "sheets": worklog_mod.day_timesheet(repo_root, date, author_slug=req.query.get("author")),
        }

    def rng(req):
        end = req.query.get("end") or datetime.date.today().isoformat()
        start = req.query.get("start") or (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        return worklog_mod.range_summary(repo_root, start, end, author_slug=req.query.get("author"))

    def authors(req):
        return worklog_mod.known_authors(repo_root)

    ctx.get(r"^/api/work/day/?$", day, "work.day")
    ctx.get(r"^/api/work/range/?$", rng, "work.range")
    ctx.get(r"^/api/work/authors/?$", authors, "work.authors")


PLUGIN = Plugin(
    id="work",
    apply=apply,
    summary="Timesheet view over knowledge-center/logs daily files.",
)
