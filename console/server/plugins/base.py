"""Plugin contract and the shared context every plugin receives.

Design intent (the SOLID part, stated once here rather than repeated in each
plugin):

- **Single responsibility** — a plugin owns one feature surface (one tab, or
  one domain concern). It knows how to read its own data and which routes
  expose it. It does not know about other plugins.
- **Open/closed** — adding a feature means adding a module + a row in
  `config/plugins.toml`. No existing file gets edited, and in particular
  `httpd.py` never grows another `elif`: it asks the router, which asks the
  registry.
- **Liskov / interface segregation** — every plugin is the same tiny shape
  (`PLUGIN = Plugin(...)` with an `apply(ctx)`), and `apply` only has to use
  the parts of the context it needs. A pure-data plugin registers no routes;
  a route-only plugin registers no provider.
- **Dependency inversion** — plugins depend on `PluginContext` (an
  abstraction they're handed), never on the server, the CLI, or each other's
  modules. Cross-plugin needs go through `ctx.provider(id)`, so the consumer
  depends on a name/protocol rather than an import.

`requires` on the Plugin itself (not in the config file) drives load order,
because a module's own dependencies are a property of the code, not of the
deployment's on/off choices.
"""

import re


class PluginError(Exception):
    pass


class Plugin:
    """One feature. `apply(ctx)` is called once at boot, in dependency order."""

    __slots__ = ("id", "apply", "requires", "summary")

    def __init__(self, id, apply, requires=(), summary=""):
        if not id:
            raise PluginError("plugin needs an id")
        if not callable(apply):
            raise PluginError(f"plugin {id!r}: apply must be callable")
        self.id = id
        self.apply = apply
        self.requires = tuple(requires)
        self.summary = summary

    def __repr__(self):
        return f"Plugin({self.id!r}, requires={self.requires!r})"


class Route:
    """One HTTP route. `pattern` is a regex over the path; captured groups are
    passed to the handler as positional args after the request object."""

    __slots__ = ("method", "pattern", "handler", "name")

    def __init__(self, method, pattern, handler, name=""):
        self.method = method.upper()
        self.pattern = re.compile(pattern)
        self.handler = handler
        self.name = name or getattr(handler, "__name__", "route")

    def match(self, method, path):
        if method.upper() != self.method:
            return None
        return self.pattern.match(path)


class Router:
    """Collects routes from plugins and resolves a request to one handler.

    Deliberately dumb: no middleware stack, no nesting. The HTTP layer owns
    transport concerns (headers, status codes, CSRF); this owns nothing but
    "which function handles this path".
    """

    def __init__(self):
        self._routes = []

    def add(self, method, pattern, handler, name=""):
        self._routes.append(Route(method, pattern, handler, name))

    def resolve(self, method, path):
        """Returns (handler, groups) or (None, ()) if nothing matches."""
        for route in self._routes:
            m = route.match(method, path)
            if m:
                return route.handler, m.groups()
        return None, ()

    def describe(self):
        return [
            {"method": r.method, "pattern": r.pattern.pattern, "name": r.name}
            for r in self._routes
        ]


class PluginContext:
    """What a plugin is handed at boot. The only thing plugins may depend on.

    `providers` is the cross-plugin seam: a plugin publishes a callable or
    object under a name, and a later plugin asks for it by that name. That
    keeps `analytics` able to use board data without importing the boards
    module, so either can be swapped or disabled independently.
    """

    def __init__(self, repo_root, config, router):
        self.repo_root = repo_root
        self.config = config
        self.router = router
        self._providers = {}
        self._tabs = {}

    # -- providers -----------------------------------------------------
    def provide(self, name, obj):
        if name in self._providers:
            raise PluginError(f"provider {name!r} already registered")
        self._providers[name] = obj

    def provider(self, name):
        if name not in self._providers:
            raise PluginError(
                f"provider {name!r} is not available — is its plugin enabled in config/plugins.toml?"
            )
        return self._providers[name]

    def has_provider(self, name):
        return name in self._providers

    # -- tabs ----------------------------------------------------------
    def register_tab(self, tab_id, **manifest):
        """Declare a UI surface. The frontend reads this from /api/config, so
        a disabled plugin's tab disappears from the nav without the frontend
        knowing which plugins exist."""
        self._tabs[tab_id] = {"id": tab_id, **manifest}

    def tabs(self):
        return dict(self._tabs)

    # -- routes (thin sugar over the router) ---------------------------
    def get(self, pattern, handler, name=""):
        self.router.add("GET", pattern, handler, name)

    def post(self, pattern, handler, name=""):
        self.router.add("POST", pattern, handler, name)
