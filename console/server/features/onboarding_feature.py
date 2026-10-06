"""Onboarding plugin: the first-run checklist, and the setup wizard.

`GET /api/onboarding` is the checklist. It reports state and does not write.
`/api/onboarding/setup` is the wizard: it writes the same files Settings
edits (author, display title, provider toggles, `.env` key names, editor
MCP config, Assistant Talk/Work). Disabling this row removes both.
"""

from .. import audit
from .. import onboarding as onboarding_mod
from .. import onboarding_setup
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    ctx.provide("onboarding", onboarding_mod)

    def report(req):
        return onboarding_mod.report(repo_root)

    def setup_get(req):
        return onboarding_setup.snapshot(repo_root)

    def setup_post(req):
        body = req.body or {}
        result = onboarding_setup.apply(repo_root, body)
        audit.record(repo_root, "onboarding.setup", actor=audit.actor_of(req),
                     target=str(body.get("step") or ""),
                     detail=onboarding_setup.public_detail(body))
        return result

    def complete_post(req):
        result = onboarding_setup.complete(repo_root)
        audit.record(repo_root, "onboarding.complete", actor=audit.actor_of(req),
                     target="onboarding")
        return result

    ctx.get(r"^/api/onboarding/?$", report, "onboarding.report")
    ctx.get(r"^/api/onboarding/setup/?$", setup_get, "onboarding.setup")
    ctx.post(r"^/api/onboarding/setup/?$", setup_post, "onboarding.setup_post")
    ctx.post(r"^/api/onboarding/complete/?$", complete_post, "onboarding.complete")


PLUGIN = Plugin(
    id="onboarding",
    apply=apply,
    requires=("boards",),
    summary="First-run checklist, plus the setup wizard that writes machine choices.",
)
