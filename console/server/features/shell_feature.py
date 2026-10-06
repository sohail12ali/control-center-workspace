"""Shell plugin: /api/config — the nav manifest the frontend boots from.

Load order doesn't matter here: the config handler calls `ctx.tabs()` when a
request arrives, long after every plugin has applied, so the tab list it
serves is always the full set of plugins that actually loaded. That's what
makes a disabled plugin's tab disappear from the nav without the frontend
knowing plugins exist at all.

Also declares the frontend-only surfaces (About, Settings), which have no
routes but still need to appear in the manifest.
"""

import hashlib
import os

from .. import onboarding_setup
from ..plugins.base import Plugin
from ..ui_version import STATIC_DIR, UiVersion, manifest_digest

# Nav order for the browser (`kanban.py serve` without html.in-shell).
# The Assistant tab is registered by its plugin but is *not* listed here:
# putting it first is a frontend sort when `html.in-shell` is set
# (T-016 FR-1 / BR-4). The CSS class is client-only, so this list cannot
# branch on it. Ids not present here sort after, alphabetically.
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


def _workspace_id(repo_root):
    """Which checkout this server serves, as a hash and never the path (D-30).
    `desktop/sidecar.py` keeps a byte-for-byte copy of this recipe so it can
    refuse to attach to another checkout's server on the same port."""
    norm = os.path.normcase(os.path.realpath(repo_root))
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:12]


def apply(ctx):
    # Frontend-only surfaces. They have no routes, but the nav needs them,
    # and declaring them here (rather than hardcoding in JS) keeps one source
    # of truth for "what tabs exist".
    ctx.register_tab("about", label="About", short="?", icon="info", group="meta")
    ctx.register_tab("settings", label="Settings", short="Set", icon="sliders", group="meta", always=True)

    # One stamp object for the process (T-036): the manifest half is computed
    # on the first request, after every plugin has applied, and kept; the file
    # half is read fresh each time.
    ui = UiVersion(STATIC_DIR, lambda: manifest_digest(ctx.tabs(), ctx.router.describe()))

    def config(req):
        # Both fields are additive and optional. A page treats an absent
        # `ui_version` as "unknown" and an absent `prefs_rev` as "ignore", so a
        # stamp that cannot be computed, or a disabled prefs plugin (no
        # `requires`, so it may be absent), costs a field and never the payload.
        extras = {}
        stamp = ui.value()
        if stamp is not None:
            extras["ui_version"] = stamp
        if ctx.has_provider("prefs"):
            extras["prefs_rev"] = ctx.provider("prefs").rev(ctx.repo_root)
        tabs = ctx.tabs()
        ordered = [tabs[k] for k in sorted(tabs, key=nav_sort_key)]
        general = ctx.config.get("general", {})
        # Per-machine name from the setup wizard. console.toml stays the
        # committed default — rewriting it would drop its comments.
        title = onboarding_setup.display_title(ctx.repo_root) or general.get("title") or "Delivery Console"
        return {
            "title": title,
            "subtitle": general.get("subtitle", ""),
            "tabs": ordered,
            "boards": [
                {"kind": t["kind"], "label": t["label"]}
                for t in ordered
                if t.get("group") == "boards"
            ],
            "stale_days": general.get("stale_days", 7),
            "workspace": _workspace_id(ctx.repo_root),
            **extras,
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
