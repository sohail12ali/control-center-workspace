"""MCP Streamable HTTP transport (T-017 FR-4, 2a) — mounted on the real
router the shipped `plugins.toml` builds, same as `test_ui_endpoints.py`."""

import itertools
import os

import pytest

from server import boards, httpd, tickets
from server.paths import find_repo_root
from server.plugins import registry as plugin_registry
from server.features import mcp_http_feature


class App:
    def __init__(self, repo_root, router):
        self.repo_root = repo_root
        self.router = router


@pytest.fixture
def app(repo):
    real = find_repo_root()
    src = os.path.join(real, "console", "config", "plugins.toml")
    dst = os.path.join(repo, "console", "config", "plugins.toml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(src, encoding="utf-8") as fh:
        text = fh.read()
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write(text)

    boards._console_cache.clear()
    config = boards.load_console_config(repo)
    _ctx, router = plugin_registry.build(repo, config)
    mcp_http_feature._SESSIONS.clear()
    yield App(repo, router)
    mcp_http_feature._SESSIONS.clear()


def call(app, method, path, query=None, body=None, session_id=""):
    handler, args = app.router.resolve(method, path)
    assert handler is not None, "no route for %s %s" % (method, path)
    req = httpd.Request(method, path, query or {}, body, app.repo_root,
                        client_addr="100.64.0.9", user_agent="pytest",
                        mcp_session_id=session_id)
    return handler(req, *args)


def _rpc(id_, method, params=None):
    return {"jsonrpc": "2.0", "id": id_, "method": method, "params": params or {}}


class TestRoutesExist:
    def test_post_and_sse_routes_are_registered(self, app):
        handler, _ = app.router.resolve("POST", "/api/mcp")
        assert handler is not None
        handler, _ = app.router.resolve("GET", "/api/mcp/sse")
        assert handler is not None


class TestPostRequestResponse:
    def test_initialize_returns_a_session_id_and_capabilities(self, app):
        result = call(app, "POST", "/api/mcp", body=_rpc(1, "initialize"))
        assert result["result"]["capabilities"]["resources"]["subscribe"] is True
        assert result["_mcp_session_id"]

    def test_tools_list_and_stdio_agree(self, app):
        """2a-4: identical `tools/list` results over HTTP vs. stdio for an
        equivalent request."""
        from server import mcp as mcp_mod

        http_result = call(app, "POST", "/api/mcp", body=_rpc(1, "tools/list"))

        stdio_server = mcp_mod.Server(app.repo_root, stdin=None,
                                      stdout=_Capture(), stderr=_Capture())
        stdio_server.handle(_rpc(1, "tools/list"))
        stdio_reply = stdio_server.stdout.parsed()[0]

        assert http_result["result"] == stdio_reply["result"]

    def test_tools_call_and_stdio_agree(self, app):
        tickets.create(app.repo_root, "T-950", "Parity ticket")
        from server import mcp as mcp_mod

        http_result = call(app, "POST", "/api/mcp",
                           body=_rpc(1, "tools/call",
                                    {"name": "context", "arguments": {"ticket": "T-950"}}))

        stdio_server = mcp_mod.Server(app.repo_root, stdin=None,
                                      stdout=_Capture(), stderr=_Capture())
        stdio_server.handle(_rpc(1, "tools/call",
                                 {"name": "context", "arguments": {"ticket": "T-950"}}))
        stdio_reply = stdio_server.stdout.parsed()[0]

        assert http_result["result"] == stdio_reply["result"]

    def test_a_session_persists_across_requests(self, app):
        init = call(app, "POST", "/api/mcp", body=_rpc(1, "initialize"))
        session_id = init["_mcp_session_id"]
        result = call(app, "POST", "/api/mcp", body=_rpc(2, "tools/list"),
                     session_id=session_id)
        assert result["_mcp_session_id"] == session_id

    def test_unknown_session_id_gets_a_fresh_server_rather_than_an_error(self, app):
        """A client-named id this process doesn't hold (restarted server,
        unknown client) starts a fresh session under that same id rather
        than refusing the request."""
        result = call(app, "POST", "/api/mcp", body=_rpc(1, "tools/list"),
                      session_id="does-not-exist")
        assert result["_mcp_session_id"] == "does-not-exist"
        assert "result" in result


class TestSseNotifications:
    def test_a_subscribed_session_receives_a_mutation_notification(self, app):
        from server import verb_handlers

        tickets.create(app.repo_root, "T-951", "SSE ticket")
        init = call(app, "POST", "/api/mcp", body=_rpc(1, "initialize"))
        session_id = init["_mcp_session_id"]
        call(app, "POST", "/api/mcp",
             body=_rpc(2, "resources/subscribe", {"uri": "ticket://T-951"}),
             session_id=session_id)

        verb_handlers.ticket_move(app.repo_root, ticket="T-951", stage="in-progress")

        source = call(app, "GET", "/api/mcp/sse", query={"session": session_id})
        first_events = list(itertools.islice(source, 2))
        assert first_events[0].startswith("retry:")
        assert "notifications/resources/updated" in first_events[1]
        assert "ticket://T-951" in first_events[1]
        source.close()

    def test_unknown_session_is_a_clean_error_not_a_hang(self, app):
        result = call(app, "GET", "/api/mcp/sse", query={"session": "nope"})
        assert "error" in result


class TestConcurrentSessionsIsolated:
    """2a-5: multiple concurrent HTTP clients isolated — one session's
    subscription/notification never reaches another session."""

    def test_two_sessions_only_see_their_own_notifications(self, app):
        from server import verb_handlers

        tickets.create(app.repo_root, "T-952", "Session A ticket")
        tickets.create(app.repo_root, "T-953", "Session B ticket")

        session_a = call(app, "POST", "/api/mcp", body=_rpc(1, "initialize"))["_mcp_session_id"]
        session_b = call(app, "POST", "/api/mcp", body=_rpc(1, "initialize"))["_mcp_session_id"]
        assert session_a != session_b

        call(app, "POST", "/api/mcp",
             body=_rpc(2, "resources/subscribe", {"uri": "ticket://T-952"}),
             session_id=session_a)
        call(app, "POST", "/api/mcp",
             body=_rpc(2, "resources/subscribe", {"uri": "ticket://T-953"}),
             session_id=session_b)

        verb_handlers.ticket_move(app.repo_root, ticket="T-952", stage="in-progress")

        source_a = call(app, "GET", "/api/mcp/sse", query={"session": session_a})
        events_a = "".join(itertools.islice(source_a, 2))
        source_a.close()
        assert "T-952" in events_a

        # Session B's own SSE stream, drained separately, has nothing queued —
        # session A's mutation never touched it, and closing session A's
        # stream above did not disturb session B's registry entry.
        from server import bus as bus_mod
        assert bus_mod.default().drain(session_b) == []
        assert session_b in mcp_http_feature._SESSIONS


class _Capture:
    """A tiny stdout stand-in that also parses back what it captured, for the
    stdio-vs-HTTP parity tests."""

    def __init__(self):
        self._lines = []

    def write(self, text):
        self._lines.append(text)

    def flush(self):
        pass

    def parsed(self):
        import json
        return [json.loads(ln) for ln in "".join(self._lines).splitlines() if ln.strip()]
