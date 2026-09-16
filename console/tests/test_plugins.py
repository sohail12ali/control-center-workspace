"""The plugin registry, against the config this template actually ships.

Every route in the console exists because a row in `plugins.toml` names a
module that exposes a `PLUGIN`. Nothing else checks that the two agree, so a
renamed module or a row added without one fails at server start — for the
person running it, not for the person who wrote it. These tests move that
failure back to the commit.
"""

import os
import re

import pytest

from server import tomlio, verbs
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry


def _read(root, rel):
    """Read and close. A leaked handle is a ResourceWarning; an unpinned
    encoding decodes as cp1252 on Windows and mangles anything non-ASCII."""
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture(scope="module")
def root():
    return find_repo_root()


@pytest.fixture(autouse=True)
def _no_real_writes(monkeypatch):
    """These tests deliberately run against the REAL checkout, because their
    subject is the shipped config. That makes any side effect a side effect on
    the developer's own workspace — the verb-run tests were writing real audit
    records, which showed up in `kanban audit` as runs nobody performed.

    Auditing has its own tests; here it is silenced."""
    from server import audit
    monkeypatch.setattr(audit, "record", lambda *a, **k: None)


class TestShippedRegistry:
    def test_every_enabled_row_imports_and_exposes_a_plugin(self, root):
        for row in plugin_registry._load_rows(root):
            plugin = plugin_registry._import_plugin(row["module"])
            assert plugin.id, "%s has a PLUGIN with no id" % row["module"]

    def test_row_ids_match_their_plugin_ids(self, root):
        # A row saying `id = "verbs"` while the module calls itself something
        # else makes `enabled = false` silently fail to disable anything.
        for row in plugin_registry._load_rows(root):
            plugin = plugin_registry._import_plugin(row["module"])
            assert plugin.id == row["id"]

    def test_every_dependency_is_present_and_enabled(self, root):
        enabled = {row["id"] for row in plugin_registry._load_rows(root)}
        for row in plugin_registry._load_rows(root):
            plugin = plugin_registry._import_plugin(row["module"])
            for need in plugin.requires or ():
                assert need in enabled, \
                    "%s requires %s, which is not enabled" % (plugin.id, need)

    def test_the_whole_registry_builds(self, root):
        from server import boards
        ctx, router = plugin_registry.build(root, boards.load_console_config(root))
        assert router is not None
        # Every enabled plugin contributed, and the nav has tabs to boot from.
        assert ctx.tabs()

    def test_verbs_plugin_is_enabled(self, root):
        ids = {row["id"] for row in plugin_registry._load_rows(root)}
        assert "verbs" in ids

    def test_the_verbs_plugin_registers_no_tab(self, root):
        # Verbs are things you run from where you already are, not a
        # destination. A tab would add somewhere nobody wants to visit.
        assert "register_tab" not in _read(
            root, "console/server/features/verbs_feature.py")

    def test_assistant_plugin_is_enabled(self, root):
        # T-004: exactly one new plugins.toml row, httpd.py untouched.
        ids = {row["id"] for row in plugin_registry._load_rows(root)}
        assert "assistant" in ids

    def test_assistant_plugin_registers_a_tab(self, root):
        # T-016: home tab. Routes still exist without the tab being visited.
        assert "register_tab" in _read(
            root, "console/server/features/assistant_feature.py")


class TestVerbRoutes:
    """The handlers, called directly — no HTTP, so a signature mistake is
    caught here rather than as a 500 in a browser."""

    def _apply(self, root):
        from server.features import verbs_feature

        routes = {}

        class Ctx:
            repo_root = root

            def get(self, pattern, fn, name):
                routes[("GET", name)] = fn

            def post(self, pattern, fn, name):
                routes[("POST", name)] = fn

            def register_tab(self, *a, **kw):
                raise AssertionError("the verbs plugin must not register a tab")

            def provide(self, *a, **kw):
                pass

        verbs_feature.apply(Ctx())
        return routes

    def test_it_registers_the_expected_routes(self, root):
        routes = self._apply(root)
        assert set(routes) == {
            ("GET", "verbs.list"), ("POST", "verbs.run"),
            ("POST", "verbs.submit"), ("GET", "verbs.jobs"),
            ("GET", "runs.list"),
            # Cancel is a POST: a GET that stops work is one a browser will
            # repeat and a prefetcher will call unprompted.
            ("POST", "verbs.job_cancel")}

    def test_listing_returns_the_real_registry(self, root):
        routes = self._apply(root)

        class Req:
            query = {}
            body = {}

        out = routes[("GET", "verbs.list")](Req())
        ids = {v["id"] for v in out["verbs"]}
        assert ids == set(verbs.registry(root))

    def test_listing_marks_availability_for_a_ticket(self, root):
        routes = self._apply(root)

        class Req:
            query = {"ticket": "CC-T001"}
            body = {}

        rows = {v["id"]: v for v in routes[("GET", "verbs.list")](Req())["verbs"]}
        assert rows["context"]["available"] is True

    def test_running_a_verb_returns_its_result(self, root):
        routes = self._apply(root)

        class Req:
            query = {}
            body = {}

        out = routes[("POST", "verbs.run")](Req(), "harness-lint")
        assert out["verb"] == "harness-lint"
        assert "summary" in out["result"]

    def test_a_failed_gate_raises_for_the_error_handler(self, root):
        # The HTTP layer turns VerbError into a 400 with the message; the
        # handler's job is to let it through rather than swallow it.
        routes = self._apply(root)

        class Req:
            query = {}
            body = {}

        with pytest.raises(verbs.VerbError):
            routes[("POST", "verbs.run")](Req(), "context")


class TestAssistantRoutes:
    """Route registration only — the handlers spawn real backend processes,
    so they're exercised against a throwaway `repo` fixture in
    `test_assistant.py`, never against the real checkout `root` used here."""

    def test_it_registers_the_expected_routes(self, root):
        from server.features import assistant_feature

        routes = {}
        tabs = {}

        class Ctx:
            repo_root = root

            def get(self, pattern, fn, name):
                routes[("GET", name)] = fn

            def post(self, pattern, fn, name):
                routes[("POST", name)] = fn

            def register_tab(self, tab_id, **kw):
                tabs[tab_id] = kw

            def provide(self, *a, **kw):
                pass

        assistant_feature.apply(Ctx())
        assert "assistant" in tabs
        assert tabs["assistant"].get("needs_live") is True
        assert set(routes) == {
            ("GET", "assistant.session"), ("POST", "assistant.new"),
            ("POST", "assistant.say"), ("GET", "assistant.stream"),
            ("GET", "assistant.memory_get"), ("POST", "assistant.memory_post"),
            ("GET", "assistant.settings_get"),
            ("POST", "assistant.settings_post"),
            # Separate from settings_get on purpose: this one probes backends
            # until one answers, and settings_get is guaranteed not to touch a
            # socket because the tray reads it on its hot path.
            ("GET", "assistant.resolve_get"),
            # T-015: the voice overlay's Allow/Deny. The Assistant answers a
            # card on its own chat, so the caller needs no chat id.
            ("POST", "assistant.approve")}


class TestPaletteAssets:
    """The palette is three files that have to agree: the script, its load
    order in index.html, and the key handler that opens it."""

    def test_index_loads_the_palette_before_the_router(self, root):
        # Match the script tags, not the prose: a comment mentioning app.js
        # is not a load order, and matching it made this test lie once already.
        html = _read(root, "console/static/index.html")
        order = re.findall(r'<script src="([^"]+)"', html)
        assert "palette.js" in order, "the palette is never loaded"
        assert order.index("palette.js") < order.index("app.js")
        assert order.index("core.js") < order.index("palette.js")
        assert "assistant.js" in order
        assert order.index("assistant.js") < order.index("app.js")

    def test_the_key_handler_opens_it(self, root):
        app = _read(root, "console/static/app.js")
        assert "C.palette" in app and "metaKey || e.ctrlKey" in app

    def test_the_palette_only_uses_icons_that_exist(self, root):
        # An unknown icon renders as an empty svg — invisible, and nothing
        # errors, so it would ship unnoticed.
        icons = _read(root, "console/static/icons.js")
        known = set(re.findall(r"^\s{4}([A-Za-z][A-Za-z0-9]*):", icons, re.M))
        palette = _read(root, "console/static/palette.js")
        used = set(re.findall(r'icon: "([a-zA-Z]+)"', palette))
        used |= set(re.findall(r'C\.icon\("([a-zA-Z]+)"\)', palette))
        used |= set(re.findall(r'row\.icon \|\| "([a-zA-Z]+)"', palette))
        assert used <= known, "unknown icons: %s" % sorted(used - known)

    def test_the_diff_card_styles_exist(self, root):
        css = _read(root, "console/static/styles.css")
        for cls in (".ct-diff", ".ct-d-add", ".ct-d-remove", ".cp-panel", ".cp-row"):
            assert cls in css, "missing style %s" % cls


class TestInShellHome:
    """T-016 FR-1: Assistant is first only when html.in-shell. Browser
    NAV_ORDER is unchanged (Overview first)."""

    def test_server_nav_still_starts_with_overview(self, root):
        from server.features.shell_feature import NAV_ORDER
        assert NAV_ORDER[0] == "overview"
        assert "assistant" not in NAV_ORDER

    def test_frontend_sorts_assistant_only_in_shell(self, root):
        app = _read(root, "console/static/app.js")
        assert 'classList.contains("in-shell")' in app
        assert 't.id === "assistant"' in app

    def test_board_start_is_not_compose_only(self, root):
        src = _read(root, "console/static/board.js")
        assert "/api/verbs/delegate/run" in src
        assert "/api/assistant/say" in src

    def test_wiki_has_no_live_agents_session_tray_lock(self, root):
        wiki = _read(root, "knowledge-center/wiki/desktop-assistant.md")
        assert "live Agents session" not in wiki
        assert "[[T-016-decision-log]]" in wiki
