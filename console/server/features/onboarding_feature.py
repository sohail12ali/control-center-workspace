"""Onboarding plugin: the first-run step list.

Read-only by design — every step reports state and offers a command, and
none of them write. Disabling this row in plugins.toml removes the Overview
card and the endpoint for a workspace that is long past needing it.
"""

from .. import onboarding as onboarding_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.provide("onboarding", onboarding_mod)

    def report(req):
        return onboarding_mod.report(repo_root)

    ctx.get(r"^/api/onboarding/?$", report, "onboarding.report")


PLUGIN = Plugin(
    id="onboarding",
    apply=apply,
    requires=("boards",),
    summary="First-run setup steps, ending at the requirements pipeline.",
)
