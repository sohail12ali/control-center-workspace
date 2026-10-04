"""MCP Streamable HTTP transport (T-017 FR-4, 2a) — mounted on the same
`serve` process every other console route runs on, so Cursor/Claude
Code/VS Code and the console UI share one running process/port; stdio
(`console/mcp_server.py`) keeps working unchanged for offline use.

## No second protocol implementation (2a-3)

`_run_one` builds one `mcp.Server` per session and calls its `handle()` —
the exact same method `console/mcp_server.py`'s stdio loop calls — with an
in-memory `io.StringIO` standing in for stdout, then reads back whatever
`handle()` wrote. `initialize`/`tools/list`/`tools/call`/`resources/*` all
run through that one method; nothing here re-implements any of them.

## Sessions

HTTP has no persistent connection to key a session by the way stdio's
`Server.session_id = id(self)` does, so the client-visible identity is an
opaque id this transport hands back after `initialize`, carried on later
requests as the `Mcp-Session-Id` header (`httpd.Request.mcp_session_id`) —
the same header name the MCP Streamable HTTP spec's examples use. A request
naming an id this process doesn't hold (restarted server, unknown client)
gets a fresh session rather than an error: `tools/call` doesn't depend on
session state, and a client that actually needs subscriptions restored
re-subscribes after noticing a new id came back.

## GET+SSE (2a-2)

`/api/mcp/sse?session=...` streams whatever the change-notification bus
(`bus.py`) accumulates for that session, using `mcp.notification_message`
so the wire shape matches stdio's own `notifications/resources/updated`
exactly. A native browser `EventSource` cannot set a custom header, so the
session id also arrives as a query parameter here — `mcp_post` accepts
either, preferring the header.

## Auth (NFR-4)

No new auth scheme. `httpd._announce_binding` already flags loudly when
`serve` binds beyond loopback; this transport adds no further gate of its
own — the same trust boundary as today's unauthenticated local `serve`,
documented rather than silently introduced.
"""

import io
import json
import time
import uuid

from .. import bus as bus_mod
from .. import mcp as mcp_mod
from ..httpd import EventSource
from ..plugins.base import Plugin

#: session_id -> mcp.Server. Process-local — an HTTP-served console is one
#: process serving many sessions, the same assumption `bus.py` already makes.
_SESSIONS = {}

#: How often the SSE loop re-checks the bus for this session. Short enough
#: that tests don't have to wait meaningfully; irrelevant to correctness,
#: only to latency.
POLL_INTERVAL_S = 0.05


def _session_id_of(req):
    return req.mcp_session_id or req.query.get("session") or ""


def _get_or_create_session(repo_root, session_id):
    if session_id and session_id in _SESSIONS:
        return session_id, _SESSIONS[session_id]
    session_id = session_id or uuid.uuid4().hex
    # `session_id=` so the bus (keyed by `Server.session_id`) and this HTTP
    # transport's own session identity are the same value — without this the
    # bus would key subscriptions by `id(server)` (an object id no HTTP
    # request ever sees) while `mcp_sse` drains by the string a client holds,
    # and a subscribed session would never receive anything.
    server = mcp_mod.Server(repo_root, stdin=None, stdout=io.StringIO(),
                            session_id=session_id)
    _SESSIONS[session_id] = server
    return session_id, server


def _run_one(server, message):
    """Call the shared `Server.handle()` once, parsing back whatever it wrote
    to its in-memory stdout as the JSON-RPC message(s) it would have printed
    over stdio: at most one reply/`_fail`, plus any flushed notifications."""
    buf = io.StringIO()
    server.stdout = buf
    server.handle(message)
    lines = [ln for ln in buf.getvalue().splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def apply(ctx):
    repo_root = ctx.repo_root

    def mcp_post(req):
        session_id = _session_id_of(req)
        session_id, server = _get_or_create_session(repo_root, session_id)
        messages = _run_one(server, req.body)
        replies = [m for m in messages if "id" in m]
        notifications = [m for m in messages if "id" not in m]

        result = dict(replies[0]) if len(replies) == 1 else {"results": replies}
        if notifications:
            result["notifications"] = notifications
        # Not a JSON-RPC field — read by the client to carry on this session
        # (e.g. before calling resources/subscribe). Namespaced so it can
        # never collide with a JSON-RPC member name (all of which are bare
        # identifiers per the spec).
        result["_mcp_session_id"] = session_id
        return result

    def mcp_sse(req):
        session_id = _session_id_of(req)
        if not session_id or session_id not in _SESSIONS:
            return {"error": "unknown or missing MCP session — POST "
                             "initialize first and reuse its _mcp_session_id"}

        def chunks():
            yield "retry: 2000\n\n"
            while True:
                for change in bus_mod.default().drain(session_id):
                    payload = mcp_mod.notification_message(
                        "notifications/resources/updated", {"uri": change["uri"]})
                    yield "data: %s\n\n" % json.dumps(payload)
                time.sleep(POLL_INTERVAL_S)

        return EventSource(chunks())

    ctx.post(r"^/api/mcp/?$", mcp_post, "mcp.call")
    ctx.get(r"^/api/mcp/sse/?$", mcp_sse, "mcp.sse")


PLUGIN = Plugin(
    id="mcp_http",
    apply=apply,
    requires=(),
    summary="MCP Streamable HTTP transport — the same tools/resources stdio "
            "serves, over the console's existing HTTP port.",
)
