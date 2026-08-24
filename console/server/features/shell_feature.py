"""Shell plugin: /api/config — the nav manifest the frontend boots from.

Load order doesn't matter here: the config handler calls `ctx.tabs()` when a
request arrives, long after every plugin has applied, so the tab list it
serves is always the full set of plugins that actually loaded. That's what
makes a disabled plugin's tab disappear from the nav without the frontend
knowing plugins exist at all.

Also declares the frontend-only surfaces (About, Settings), which have no
routes but still need to appear in the manifest.
"""

from ..plugins.base import Plugin

# Nav order. Ids not present here sort after, alphabetically — so a
# third-party plugin's tab still shows up without editing this list.
NAV_ORDER = [
    "overview",
    "board:tickets",
    "board:investigations",
    "board:migrations",
    "board:releases",
    "agents",
    "work",
    "analytics",
    "todos",
    "vault",
    "about",
    "settings",
]


def nav_sort_key(tab_id):
    """Public because the static exporter orders the same manifest — one
    ordering rule, imported, rather than two that can disagree."""
    try:
        return (0, NAV_ORDER.index(tab_id), "")
    except ValueError:
        return (1, 0, tab_id)


def apply(ctx):
    # Frontend-only surfaces. They have no routes, but the nav needs them,
    # and declaring them here (rather than hardcoding in JS) keeps one source
    # of truth for "what tabs exist".
    ctx.register_tab("about", label="About", short="?", icon="info", group="meta")
    ctx.register_tab("settings", label="Settings", short="Set", icon="sliders", group="meta", always=True)

    def config(req):
        tabs = ctx.tabs()
        ordered = [tabs[k] for k in sorted(tabs, key=nav_sort_key)]
        general = ctx.config.get("general", {})
        return {
            "title": general.get("title", "Delivery Console"),
            "subtitle": general.get("subtitle", ""),
            "tabs": ordered,
            "boards": [
                {"kind": t["kind"], "label": t["label"]}
                for t in ordered
                if t.get("group") == "boards"
            ],
            "stale_days": general.get("stale_days", 7),
        }

    def routes(req):
        """Introspection: which routes this deployment actually serves. Useful
        when a tab 404s and you need to know whether its plugin is loaded."""
        return {"routes": ctx.router.describe(), "tabs": sorted(ctx.tabs())}

    ctx.get(r"^/api/config/?$", config, "shell.config")
    ctx.get(r"^/api/routes/?$", routes, "shell.routes")


PLUGIN = Plugin(
    id="shell",
    apply=apply,
    summary="Nav manifest and route introspection.",
)
