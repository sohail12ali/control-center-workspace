"""Analytics plugin: charts over board data, plus worklog charts when the
work plugin is loaded. Degrades rather than failing when it isn't."""

from .. import analytics as analytics_mod
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
        return data

    ctx.get(r"^/api/analytics/?$", report, "analytics.report")


PLUGIN = Plugin(
    id="analytics",
    apply=apply,
    requires=("boards",),
    summary="Pipeline, ageing, throughput and timesheet charts.",
)
