"""Analytics plugin: charts over board data, plus worklog charts when the
work plugin is loaded. Degrades rather than failing when it isn't."""

import datetime

from .. import analytics as analytics_mod
from .. import telemetry
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root
    # Dependency inversion in practice: ask the context whether worklog data
    # exists rather than importing the module and hoping its plugin is on.
    has_worklog = ctx.has_provider("worklog")

    ctx.register_tab(
        "analytics", label="Analytics", short="Stats", icon="chart", group="main", needs_live=True
    )

    def report(req):
        window = int(req.query.get("window", 30))
        data = analytics_mod.full_report(
            repo_root,
            window_days=window,
            author_slug=req.query.get("author"),
            include_worklog=has_worklog,
        )
        data["board_filter"] = req.query.get("board", "all")
        data["spend"] = _spend(repo_root, window)
        return data

    def _spend(repo_root, window):
        """Token and cost totals for the same window the charts use.

        Folded into this payload rather than given its own endpoint: it is one
        more section of the same page, and a second request would only add a
        way for half the tab to load.

        `unpriced_turns` travels with the total everywhere it goes. A cost
        drawn from records where some turns had no rate is a different number
        from a complete one, and the reader has to be able to tell.
        """
        since = (datetime.date.today()
                 - datetime.timedelta(days=window)).isoformat()
        try:
            by_model = telemetry.summarize(repo_root, group="model", since=since)
            by_ticket = telemetry.summarize(repo_root, group="ticket", since=since)
        except Exception as exc:  # noqa: BLE001
            return {"available": False, "reason": str(exc), "totals": {},
                    "by_model": [], "by_ticket": []}
        return {
            "available": True,
            "reason": "",
            "window_days": window,
            "totals": by_model["totals"],
            "by_model": by_model["rows"][:8],
            "by_ticket": by_ticket["rows"][:8],
        }

    ctx.get(r"^/api/analytics/?$", report, "analytics.report")


PLUGIN = Plugin(
    id="analytics",
    apply=apply,
    requires=("boards",),
    summary="Pipeline, ageing, throughput and timesheet charts.",
)
