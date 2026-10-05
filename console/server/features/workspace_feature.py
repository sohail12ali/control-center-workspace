"""Template check and a typed clean of this checkout's workspace content.

No tab. The Settings page hosts the panel. Routes exist so that page can
read the report and apply a clean; the CLI and the commit hook call the
same module directly.

Clean deletes working-tree files. It does not commit, and it does not
rewrite history. The typed word is the same one the CLI asks for, because
this page has no authentication of its own.
"""

from .. import audit
from .. import reset as reset_mod
from .. import workspace_check
from ..plugins.base import Plugin

CONFIRM = "reset"


def apply(ctx):
    repo_root = ctx.repo_root

    def report(req):
        return workspace_check.report(repo_root)

    def clean(req):
        confirm = ((req.body or {}).get("confirm") or "").strip()
        if confirm != CONFIRM:
            raise ValueError("type reset to confirm")
        actions = reset_mod.run(repo_root, apply=True)
        audit.record(
            repo_root, "workspace.clean", actor=audit.actor_of(req),
            target="workspace", detail={"count": len(actions)},
        )
        return {
            "ok": True,
            "applied": True,
            "count": len(actions),
            "report": workspace_check.report(repo_root),
        }

    ctx.get(r"^/api/workspace/?$", report, "workspace.report")
    ctx.post(r"^/api/workspace/clean/?$", clean, "workspace.clean")


PLUGIN = Plugin(
    id="workspace",
    apply=apply,
    summary="Template check and a typed clean of workspace content. History is not rewritten.",
)
