"""Loads plugins listed in console/config/plugins.toml, in dependency order.

Two independent switches decide whether a surface exists, and they are kept
separate on purpose (same reasoning as the fork this pattern comes from):

- `plugins.toml` — committed, server-side. `enabled = false` means the module
  is never imported and its routes don't exist for anybody who pulls this
  checkout. Use it to say "this deployment doesn't do that".
- Settings tab toggles — per-user, browser-local. They hide a tab for one
  person without changing what the server offers.

Do not unify them: one is a deployment fact, the other is a preference.
"""

import importlib
import os

from .. import tomlio
from .base import PluginContext, PluginError, Router

CONFIG_REL = os.path.join("console", "config", "plugins.toml")


def _load_rows(repo_root):
    path = os.path.join(repo_root, CONFIG_REL)
    if not os.path.isfile(path):
        raise PluginError(f"plugin registry not found: {CONFIG_REL}")
    data = tomlio.load(path)
    rows = data.get("plugin", [])
    if not isinstance(rows, list):
        raise PluginError("plugins.toml: expected [[plugin]] rows")
    return [r for r in rows if r.get("enabled", True)]


def _import_plugin(module_name):
    """Import `module_name` relative to the server package and return its
    PLUGIN. A module without PLUGIN is a config error, not a crash."""
    full = f"{__package__.rsplit('.', 1)[0]}.{module_name}"
    try:
        mod = importlib.import_module(full)
    except ImportError as exc:
        raise PluginError(f"cannot import plugin module {module_name!r}: {exc}") from None
    plugin = getattr(mod, "PLUGIN", None)
    if plugin is None:
        raise PluginError(f"module {module_name!r} has no PLUGIN — see plugins/base.py")
    return plugin


def _order(plugins):
    """Topological sort by each plugin's own `requires`. Raises on a cycle or
    a missing dependency, naming the plugins involved — a silent wrong order
    would surface much later as a confusing provider lookup failure."""
    by_id = {p.id: p for p in plugins}
    ordered = []
    state = {}  # id -> "visiting" | "done"

    def visit(pid, trail):
        if state.get(pid) == "done":
            return
        if state.get(pid) == "visiting":
            raise PluginError("plugin dependency cycle: " + " -> ".join(trail + [pid]))
        if pid not in by_id:
            raise PluginError(
                f"plugin {trail[-1] if trail else '?'} requires {pid!r}, which is not enabled"
            )
        state[pid] = "visiting"
        for dep in by_id[pid].requires:
            visit(dep, trail + [pid])
        state[pid] = "done"
        ordered.append(by_id[pid])

    for p in plugins:
        visit(p.id, [])
    return ordered


def build(repo_root, console_config):
    """Load every enabled plugin and return (context, router).

    Called once by the HTTP server and once per CLI invocation, so a CLI verb
    and an API route always see the same wiring.
    """
    rows = _load_rows(repo_root)
    plugins = []
    for row in rows:
        module = row.get("module")
        if not module:
            raise PluginError(f"plugins.toml row {row.get('id')!r} has no module")
        plugin = _import_plugin(module)
        declared = row.get("id")
        if declared and declared != plugin.id:
            raise PluginError(
                f"plugins.toml says id={declared!r} but {module} declares {plugin.id!r} — one of them is wrong"
            )
        plugins.append(plugin)

    router = Router()
    ctx = PluginContext(repo_root, console_config, router)
    for plugin in _order(plugins):
        plugin.apply(ctx)
    return ctx, router


def loaded_ids(repo_root):
    """Cheap introspection for the CLI/doctor path — which rows are on."""
    return [r.get("id") for r in _load_rows(repo_root)]
