"""The preferences plugin (T-036, `features/prefs_feature.py`): routes, wiring, CSRF.

`App`, `app` and `call()` are a local copy of `test_ui_endpoints.py:30-75`. The
fixtures there are module-local and `conftest.py` is shared by every test while
other tickets add tests to it, so a 15-line copy is cheaper than a shared-file
edit (decision D-31).

Every workspace here is the `repo` fixture's throwaway root. No test may write
the real checkout's `console/.cache/prefs.json`.
"""

import importlib
import json
import os
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from server import audit, boards, httpd, prefs_store, tomlio
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry

SECRET = "SECRET-VALUE-do-not-log-8841"


class App:
    """A built console: the shipped plugin set, wired against a scratch root."""

    def __init__(self, repo_root, router, ctx=None):
        self.repo_root = repo_root
        self.router = router
        self.ctx = ctx


def _shipped_plugins_text():
    src = os.path.join(find_repo_root(), "console", "config", "plugins.toml")
    with open(src, encoding="utf-8") as fh:
        return fh.read()


def build_app(repo, plugins_text):
    dst = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(plugins_text)
    boards._console_cache.clear()
    config = boards.load_console_config(repo)
    ctx, router = plugin_registry.build(repo, config)
    return App(repo, router, ctx)


@pytest.fixture
def app(repo):
    """The real router, built from the SHIPPED plugins.toml, against a
    throwaway workspace."""
    return build_app(repo, _shipped_plugins_text())


def routed(app, method, path):
    handler, _args = app.router.resolve(method, path)
    return handler is not None


def call(app, method, path, query=None, body=None):
    """Dispatch one request the way httpd does, returning the handler's data."""
    handler, args = app.router.resolve(method, path)
    assert handler is not None, "no route for %s %s" % (method, path)
    req = httpd.Request(method, path, query or {}, body, app.repo_root,
                        client_addr="100.64.0.9", user_agent="pytest")
    return handler(req, *args)


def _store_file(repo):
    return os.path.join(repo, "console", ".cache", "prefs.json")


class TestRoutes:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/prefs"),
        ("GET", "/api/prefs/"),
        ("POST", "/api/prefs"),
        ("POST", "/api/prefs/import"),
        ("POST", "/api/prefs/reset"),
    ])
    def test_the_four_routes_resolve(self, app, method, path):
        assert routed(app, method, path), "%s %s is not routed" % (method, path)

    def test_import_and_reset_are_posts_not_gets(self, app):
        # A GET that wipes every saved preference is one a prefetcher will call.
        assert not routed(app, "GET", "/api/prefs/reset")
        assert not routed(app, "GET", "/api/prefs/import")

    def test_route_names_are_the_documented_ones(self, app):
        names = {(r["method"], r["name"]) for r in app.router.describe()
                 if r["name"].startswith("prefs.")}
        assert names == {("GET", "prefs.get"), ("POST", "prefs.post"),
                         ("POST", "prefs.import"), ("POST", "prefs.reset")}

    def test_ac24_get_returns_the_empty_shape_when_nothing_is_stored(self, app):
        assert call(app, "GET", "/api/prefs") == {"prefs": {}, "rev": 0, "import_open": True}
        assert not os.path.exists(_store_file(app.repo_root))

    def test_ac25_post_returns_rev_and_prev_and_get_reflects_it(self, app):
        first = call(app, "POST", "/api/prefs", body={"set": {"theme": "dark"}})
        assert first == {"rev": 1, "prev": 0}
        assert call(app, "GET", "/api/prefs") == {
            "prefs": {"theme": "dark"}, "rev": 1, "import_open": True}
        again = call(app, "POST", "/api/prefs", body={"set": {"theme": "dark"}})
        assert again["rev"] == again["prev"] == 1
        deleted = call(app, "POST", "/api/prefs", body={"del": ["theme"]})
        assert deleted == {"rev": 2, "prev": 1}

    def test_an_empty_post_body_is_a_harmless_noop(self, app):
        assert call(app, "POST", "/api/prefs", body={}) == {"rev": 0, "prev": 0}

    def test_a_bad_key_raises_the_valueerror_httpd_turns_into_a_400(self, app):
        with pytest.raises(ValueError):
            call(app, "POST", "/api/prefs", body={"set": {"bad key": 1}})
        assert not os.path.exists(_store_file(app.repo_root))

    def test_import_and_reset_round_trip_through_the_router(self, app):
        imported = call(app, "POST", "/api/prefs/import",
                        body={"values": {"theme": "dark", "voice": {"autoRead": True}}})
        assert imported["imported"] == ["theme", "voice"]
        assert imported["closed"] is False and imported["rev"] == 1
        reset = call(app, "POST", "/api/prefs/reset", body={})
        assert reset == {"prefs": {}, "rev": 2, "closed": True}
        closed = call(app, "POST", "/api/prefs/import", body={"values": {"theme": "light"}})
        assert closed["closed"] is True and closed["imported"] == []
        assert call(app, "GET", "/api/prefs")["import_open"] is False

    def test_an_import_without_values_is_a_valueerror(self, app):
        with pytest.raises(ValueError):
            call(app, "POST", "/api/prefs/import", body={})


class TestRegistration:
    def test_ac33_the_shipped_registry_row_has_no_requires_and_the_module_exposes_plugin(self):
        rows = tomlio.loads(_shipped_plugins_text())["plugin"]
        ids = [r["id"] for r in rows]
        row = rows[ids.index("prefs")]
        assert row["module"] == "features.prefs_feature"
        assert row["enabled"] is True
        assert "requires" not in row
        # Placed between `workspace` and `shell`, as the plan says.
        assert ids.index("workspace") < ids.index("prefs") < ids.index("shell")

        mod = importlib.import_module("server.features.prefs_feature")
        assert mod.PLUGIN.id == row["id"] == "prefs"
        assert mod.PLUGIN.requires == ()

    def test_ac33_the_plugin_registers_no_tab(self, app):
        with open(importlib.import_module("server.features.prefs_feature").__file__,
                  encoding="utf-8") as fh:
            assert "register_tab" not in fh.read()
        assert "prefs" not in app.ctx.tabs()

    def test_ac33_the_provider_is_the_store_module(self, app):
        assert app.ctx.has_provider("prefs")
        assert app.ctx.provider("prefs") is prefs_store

    def test_disabling_the_row_removes_the_routes_and_the_provider(self, repo):
        text = _shipped_plugins_text()
        marker = 'id = "prefs"\nmodule = "features.prefs_feature"\nenabled = true'
        assert marker in text
        off = build_app(repo, text.replace(marker, marker.replace("true", "false")))
        for method, path in (("GET", "/api/prefs"), ("POST", "/api/prefs"),
                             ("POST", "/api/prefs/import"), ("POST", "/api/prefs/reset")):
            assert not routed(off, method, path)
        assert not off.ctx.has_provider("prefs")

    def test_ac36_only_the_store_the_plugin_and_shell_feature_read_preferences(self):
        server_dir = os.path.join(find_repo_root(), "console", "server")
        allowed = {"prefs_store.py", "prefs_feature.py", "shell_feature.py"}
        needles = ("prefs_store", ".cache/prefs.json", 'provider("prefs")')
        offenders = []
        for root, _dirs, files in os.walk(server_dir):
            for name in files:
                if not name.endswith(".py") or name in allowed:
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as fh:
                    text = fh.read()
                if any(n in text for n in needles):
                    offenders.append(os.path.relpath(os.path.join(root, name), server_dir))
        assert offenders == []


@pytest.fixture
def server(app):
    """A real in-process HTTP server over the app's router.

    `repo_root` and `router` go on a SUBCLASS: `httpd.serve()` sets them on the
    shared `Handler` class, and doing the same here would leak this test's
    scratch root into any later test that reads it.
    """
    class H(httpd.Handler):
        repo_root = app.repo_root
        router = app.router

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield srv
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def http(server, method, path, body=None, csrf=True):
    url = "http://127.0.0.1:%d%s" % (server.server_address[1], path)
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if csrf:
        headers["X-Console-Request"] = "1"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return res.status, json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read().decode("utf-8") or "{}")


class TestOverHttp:
    def test_ac34_post_without_the_csrf_header_is_403_and_with_it_is_201(self, server, app):
        # No body on the refused request: the server answers 403 before reading
        # one, and closing a socket with unread bytes can reset the connection
        # before the client has read the status.
        status, payload = http(server, "POST", "/api/prefs", csrf=False)
        assert status == 403 and "X-Console-Request" in payload["error"]
        assert not os.path.exists(_store_file(app.repo_root))

        status, payload = http(server, "POST", "/api/prefs", {"set": {"theme": "dark"}})
        assert status == 201
        assert payload == {"rev": 1, "prev": 0}

    def test_ac34_import_and_reset_need_the_header_too(self, server):
        assert http(server, "POST", "/api/prefs/import", csrf=False)[0] == 403
        assert http(server, "POST", "/api/prefs/reset", csrf=False)[0] == 403

    def test_a_get_needs_no_header_and_returns_what_was_posted(self, server):
        http(server, "POST", "/api/prefs", {"set": {"theme": "dark"}})
        status, payload = http(server, "GET", "/api/prefs", csrf=False)
        assert status == 200
        assert payload == {"prefs": {"theme": "dark"}, "rev": 1, "import_open": True}

    def test_a_bad_key_is_a_400_with_a_sentence_and_stores_nothing(self, server, app):
        status, payload = http(server, "POST", "/api/prefs", {"set": {"1x": 1}})
        assert status == 400 and "'1x'" in payload["error"]
        assert not os.path.exists(_store_file(app.repo_root))

    def test_a_nan_value_in_the_body_is_a_400(self, server):
        # `json.loads` accepts the bare token NaN; the store must be the one
        # that refuses it.
        url = "http://127.0.0.1:%d/api/prefs" % server.server_address[1]
        req = urllib.request.Request(
            url, data=b'{"set": {"n": NaN}}', method="POST",
            headers={"X-Console-Request": "1", "Content-Type": "application/json"})
        with pytest.raises(urllib.error.HTTPError) as err:
            urllib.request.urlopen(req, timeout=10)
        assert err.value.code == 400
        err.value.close()


class TestAudit:
    @pytest.fixture
    def recorded(self, monkeypatch):
        calls = []

        def fake(repo_root, action, **kwargs):
            calls.append({"action": action, **kwargs})

        monkeypatch.setattr(audit, "record", fake)
        return calls

    def test_ac32_import_and_reset_are_audited_once_each_with_names_and_counts(self, app, recorded):
        call(app, "POST", "/api/prefs/import",
             body={"values": {"theme": SECRET, "voice": {"x": SECRET}, "bad key": SECRET}})
        call(app, "POST", "/api/prefs/reset", body={})
        assert [c["action"] for c in recorded] == ["prefs.import", "prefs.reset"]
        imp, rst = recorded
        assert imp["detail"] == {"imported": ["theme", "voice"], "skipped": [],
                                 "rejected": 1, "closed": False}
        assert rst["detail"] == {"cleared": ["theme", "voice"], "count": 2, "rev": 2}
        assert SECRET not in json.dumps(recorded)

    def test_ac32_a_routine_set_and_a_read_are_not_audited(self, app, recorded):
        call(app, "POST", "/api/prefs", body={"set": {"theme": SECRET}})
        call(app, "POST", "/api/prefs", body={"del": ["theme"]})
        call(app, "GET", "/api/prefs")
        assert recorded == []


class TestRealAuditTrail:
    """AC-32 against the real `audit.record`, writing into the scratch root
    (pattern `test_notify_audit.py:268`)."""

    def _raw(self, repo):
        folder = audit.audit_dir(repo)
        if not os.path.isdir(folder):
            return ""
        text = ""
        for name in sorted(os.listdir(folder)):
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                text += fh.read()
        return text

    def test_ac32_both_names_are_registered_actions(self):
        assert "prefs.reset" in audit.ACTIONS
        assert "prefs.import" in audit.ACTIONS
        # Each is listed once: `kanban.py audit --action` and the Work-tab
        # filter are built from this tuple.
        assert audit.ACTIONS.count("prefs.reset") == audit.ACTIONS.count("prefs.import") == 1

    def test_ac32_import_and_reset_write_lines_with_names_and_counts_and_no_values(self, app):
        call(app, "POST", "/api/prefs/import",
             body={"values": {"theme": SECRET, "voice": {"note": SECRET}, "1x": SECRET}})
        call(app, "POST", "/api/prefs/reset", body={})

        raw = self._raw(app.repo_root)
        assert SECRET not in raw
        rows = audit.read(app.repo_root, limit=10)
        by_action = {r["action"]: r for r in rows}
        assert sorted(by_action) == ["prefs.import", "prefs.reset"]
        assert by_action["prefs.import"]["detail"] == {
            "imported": ["theme", "voice"], "skipped": [], "rejected": 1, "closed": False}
        assert by_action["prefs.reset"]["detail"]["cleared"] == ["theme", "voice"]
        assert by_action["prefs.reset"]["detail"]["count"] == 2
        assert by_action["prefs.import"]["actor"]["addr"] == "100.64.0.9"
        # The rejected key's name is client-chosen text and is not recorded.
        assert "1x" not in raw

    def test_ac32_a_routine_post_writes_no_audit_line(self, app):
        call(app, "POST", "/api/prefs", body={"set": {"theme": SECRET}})
        call(app, "POST", "/api/prefs", body={"set": {"theme": "light"}, "del": ["x"]})
        call(app, "POST", "/api/prefs", body={"del": ["theme"]})
        assert audit.read(app.repo_root, limit=10) == []
        assert self._raw(app.repo_root) == ""
        assert not os.path.exists(audit.audit_dir(app.repo_root))
