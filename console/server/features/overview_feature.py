"""Overview plugin: the landing dashboard. Pure aggregation — owns no storage."""

from .. import overview as overview_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.register_tab(
        "overview",
        label="Overview",
        short="Home",
        icon="layout",
        group="main",
    )

    def full(req):
        return overview_mod.full_overview(repo_root)

    ctx.get(r"^/api/overview/?$", full, "overview.full")


PLUGIN = Plugin(
    id="overview",
    apply=apply,
    requires=("boards",),
    summary="Landing dashboard: attention, flow, recent activity.",
)
