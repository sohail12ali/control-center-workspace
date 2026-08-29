"""Ops plugin: the machine's own state, read-only, over HTTP.

No tab. Schedules, worktrees and the notification channel are not destinations
— they are facts about this checkout that belong beside whatever they qualify:
schedules under the work they will submit, worktrees and notification health in
Settings, next to the other things you configure once and then forget.

Read-only on purpose. Adding a worktree checks out a branch and writes to disk;
editing a schedule changes what fires while nobody is watching. Both are
reasonable from a terminal where you can see the error, and neither is
something to put behind a button on a page that has no authentication of its
own. The UI reports; the CLI still owns the verbs that change things.

Every handler degrades instead of raising. A checkout with no git, no
schedules file, or no Telegram credentials is a normal checkout, and a panel
that 500s on it would be a worse answer than one that says "none".
"""

from .. import notify as notify_mod
from .. import schedules as schedules_mod
from .. import worktrees as worktrees_mod
from ..plugins.base import Plugin


def apply(ctx):
    repo_root = ctx.repo_root

    def schedules(req):
        """Every schedule and when it next runs.

        `clock_running` is the honest part. The console is the clock: nothing
        fires while `serve` is not running, and a next-run time shown without
        that caveat reads as a promise the deployment may not be keeping.
        """
        try:
            rows = [s.describe() for s in
                    schedules_mod.registry(repo_root, force=True).values()]
        except Exception as exc:  # noqa: BLE001
            # A malformed cron expression is a config error, not a server
            # error: name it in the panel rather than blanking the tab.
            return {"schedules": [], "error": str(exc), "clock_running": True}
        rows.sort(key=lambda r: (not r["enabled"], r["next_run"] or "~", r["id"]))
        return {"schedules": rows, "error": "", "clock_running": True,
                "enabled_count": sum(1 for r in rows if r["enabled"])}

    def worktrees(req):
        try:
            rows = worktrees_mod.list_worktrees(repo_root)
        except Exception as exc:  # noqa: BLE001
            return {"worktrees": [], "error": str(exc)}
        return {"worktrees": rows, "error": ""}

    def notify_status(req):
        """Whether a parked approval can actually reach a phone.

        Reports presence, never values — the same discipline as everywhere
        else a credential is involved.
        """
        return notify_mod.status(repo_root)

    ctx.get(r"^/api/schedules/?$", schedules, "ops.schedules")
    ctx.get(r"^/api/worktrees/?$", worktrees, "ops.worktrees")
    ctx.get(r"^/api/notify/?$", notify_status, "ops.notify")


PLUGIN = Plugin(
    id="ops",
    apply=apply,
    summary="Read-only machine state: schedules, worktrees, notification health.",
)
