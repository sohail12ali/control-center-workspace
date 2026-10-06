"""Shared view preferences over HTTP: four routes on `prefs_store`.

No tab. The desktop app and every browser read and write the same copy here,
so a theme chosen in one shows up in the other. `enabled = false` in
`plugins.toml` removes the routes, and the page then falls back to its own
`localStorage` exactly as it did before this plugin existed.

Only `prefs.import` and `prefs.reset` are audited. A routine `POST /api/prefs`
fires on every setting a person touches (a draft saved per keystroke would
flood the audit directory), while a reset and a migration are the two moments
worth a line. Detail carries key names and counts, never values.

The provider lets `shell_feature` put `prefs_rev` on `/api/config` without
importing the store module.
"""

from .. import audit, prefs_store
from ..plugins.base import Plugin


def apply(ctx):
    def get(req):
        return prefs_store.snapshot(req.repo_root)

    def post(req):
        body = req.body or {}
        return prefs_store.apply(req.repo_root, set=body.get("set"), delete=body.get("del"))

    def import_(req):
        result = prefs_store.import_values(req.repo_root, (req.body or {}).get("values"))
        audit.record(
            req.repo_root, "prefs.import", actor=audit.actor_of(req), target="prefs",
            detail={
                "imported": result["imported"], "skipped": result["skipped"],
                # A rejected key is client-chosen text and may be anything, so
                # only how many, never which.
                "rejected": len(result["rejected"]), "closed": result["closed"],
            },
        )
        return result

    def reset(req):
        # Read just before the reset for the count; a write landing in between
        # makes the audit number off by that write, which is acceptable here.
        cleared = sorted(prefs_store.snapshot(req.repo_root)["prefs"])
        result = prefs_store.reset(req.repo_root)
        audit.record(
            req.repo_root, "prefs.reset", actor=audit.actor_of(req), target="prefs",
            detail={"cleared": cleared, "count": len(cleared), "rev": result["rev"]},
        )
        return result

    ctx.get(r"^/api/prefs/?$", get, "prefs.get")
    ctx.post(r"^/api/prefs/?$", post, "prefs.post")
    ctx.post(r"^/api/prefs/import/?$", import_, "prefs.import")
    ctx.post(r"^/api/prefs/reset/?$", reset, "prefs.reset")
    ctx.provide("prefs", prefs_store)


PLUGIN = Plugin(
    id="prefs",
    apply=apply,
    summary="View preferences shared by the app and every browser, kept in console/.cache/prefs.json.",
)
