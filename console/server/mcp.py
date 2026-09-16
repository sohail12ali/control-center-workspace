"""MCP server — the console's verbs as native tools for any MCP client.

## Why this and not one integration per client

Claude Code, Cursor, and the OpenRouter backend this roadmap adds next all need
the same thing: the ability to ask the console what it knows instead of reading
eight files to work it out. Writing that three times means three surfaces that
drift. MCP is the one protocol all three already speak, so the console
implements it once and every client gets an identical tool set.

## Tools come from the verb registry, not from a list here

There is no tool table in this module. `tools/list` walks
`verbs.registry()` and generates a schema from each handler's own signature, so
adding a row to `verbs.toml` adds a tool with no change here. A tool list
maintained by hand beside the thing it describes is a list that goes stale.

## Deliberately small

Three methods — `initialize`, `tools/list`, `tools/call` — plus the
`notifications/initialized` acknowledgement, and (T-017 FR-3) `resources/list`,
`resources/read`, `resources/subscribe`/`resources/unsubscribe` plus the
`notifications/resources/updated` push. Prompts, sampling and completion are
still not implemented, and the server says so through its declared
capabilities rather than by failing calls at runtime.

## Resources (T-017 FR-3)

Every ticket is exposed as one resource, `ticket://{ID}`, whose content is the
same digest the `context` tool/verb already produces — `resources/read`
delegates to `verb_handlers.ticket_context` rather than building a second
representation of a ticket. A session that calls `resources/subscribe` on a
`ticket://{ID}` is notified (`notifications/resources/updated`) the next time
that ticket changes, via the change-notification bus in `bus.py` — scoped to
MCP resource subscribers only, never the console board UI (decision-log a8).

Transport is newline-delimited JSON on stdin/stdout, which is what MCP's stdio
transport specifies. **Nothing may write to stdout except protocol messages** —
a stray `print` corrupts the stream and the client sees a parse error rather
than whatever went wrong. Diagnostics go to stderr.

Run it with `python console/mcp_server.py`; see that file for client wiring.
"""

import inspect
import json
import sys
import traceback

from . import bus as bus_mod
from . import context as context_mod
from . import tickets as tickets_mod
from . import verbs as verbs_mod

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "delivery-console"
SERVER_VERSION = "1.0.0"

# JSON-RPC 2.0 codes.
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _schema_for(verb):
    """A JSON Schema for one verb, derived from its handler's signature.

    Deriving beats declaring: a hand-written schema beside a handler is one
    rename away from lying about what the tool accepts, and the client trusts
    the schema.
    """
    func = verb.resolve()
    properties, required = {}, []
    for name, param in inspect.signature(func).parameters.items():
        if name == "repo_root":
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name == "ticket":
            properties["ticket"] = {
                "type": "string",
                "description": "Ticket id, e.g. CC-T001.",
            }
            if verb.needs_ticket:
                required.append("ticket")
            continue
        prop = {"type": "string"}
        if param.default is not inspect.Parameter.empty and param.default is not None:
            prop["description"] = "Default: %s" % (param.default,)
        properties[name] = prop

    if verb.needs_confirm:
        properties["confirm"] = {
            "type": "boolean",
            "description": ("This verb changes state and will refuse to run "
                            "without an explicit true."),
        }
        required.append("confirm")

    return {"type": "object", "properties": properties, "required": required}


def tool_list(repo_root):
    out = []
    for verb in sorted(verbs_mod.registry(repo_root).values(), key=lambda v: v.id):
        description = verb.label
        if verb.hint:
            description += " — " + verb.hint
        out.append({
            "name": verb.id,
            "description": description,
            "inputSchema": _schema_for(verb),
        })
    return out


#: URIs are `ticket://{ID}` — the one resource kind this ticket ships
#: (ticket context). A future resource kind gets its own prefix, not a
#: branch inside this one.
RESOURCE_SCHEME = "ticket://"


def _resource_uri(ticket_id):
    return RESOURCE_SCHEME + ticket_id


def _ticket_id_from_uri(uri):
    if not (uri or "").startswith(RESOURCE_SCHEME):
        return None
    return uri[len(RESOURCE_SCHEME):]


def resource_list(repo_root):
    """One resource per ticket — the same tickets `ticket list` reports."""
    out = []
    for t in tickets_mod.list_tickets(repo_root):
        out.append({
            "uri": _resource_uri(t["id"]),
            "name": t["id"],
            "description": t.get("title", ""),
            "mimeType": "text/markdown",
        })
    return out


def resource_read(repo_root, uri):
    """A resource's content — the same digest `context`/`ticket_context`
    produces, so a resource read and a `context` tool call never disagree.
    Raises `FileNotFoundError` for an unknown ticket (via `context.build`
    itself), `ValueError` for a URI outside `RESOURCE_SCHEME` — both are
    reported as clean tool/protocol errors by the caller, never a traceback.
    """
    ticket_id = _ticket_id_from_uri(uri)
    if ticket_id is None:
        raise ValueError("unknown resource scheme: %r (expected %s...)"
                         % (uri, RESOURCE_SCHEME))
    digest = context_mod.build(repo_root, ticket_id)
    text = context_mod.format_markdown(digest)
    return {"uri": uri, "mimeType": "text/markdown", "text": text}


def notification_message(method, params):
    """The JSON-RPC shape of a server-initiated message — pulled out so the
    HTTP transport's SSE endpoint (2a-2, `features/mcp_http_feature.py`) can
    build the exact same notification stdio sends, instead of a second
    hand-written copy of `{"jsonrpc": "2.0", ...}`."""
    return {"jsonrpc": "2.0", "method": method, "params": params}


def _text(payload):
    return {"content": [{"type": "text", "text": payload}]}


def _error_text(message):
    """A tool-level failure, reported as an unsuccessful result rather than a
    protocol error — the model should see what went wrong and be able to
    correct itself, which a JSON-RPC error code does not let it do."""
    return {"content": [{"type": "text", "text": message}], "isError": True}


def call_tool(repo_root, name, arguments):
    arguments = dict(arguments or {})
    ticket = arguments.pop("ticket", None) or None
    confirm = bool(arguments.pop("confirm", False))

    try:
        result = verbs_mod.run(repo_root, name, ticket=ticket, confirm=confirm,
                               args=arguments)
    except verbs_mod.VerbError as exc:
        return _error_text(str(exc))
    except FileNotFoundError as exc:
        return _error_text(str(exc))
    except Exception as exc:  # noqa: BLE001
        return _error_text("%s: %s" % (type(exc).__name__, exc))

    # `context` is the one tool whose value is its prose form — it exists to be
    # read by a model, and its markdown is a third the size of its JSON.
    if name == "context" and isinstance(result, dict) and "ticket" in result:
        return _text(context_mod.format_markdown(result))
    return _text(json.dumps(result, indent=2, default=str))


class Server:
    """One MCP session over a pair of streams."""

    def __init__(self, repo_root, stdin=None, stdout=None, stderr=None,
                 session_id=None):
        self.repo_root = repo_root
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.initialized = False
        # A fresh identity per session/process by default — the bus keys
        # subscriptions and pending notifications by this. Stdio never passes
        # `session_id` (there is exactly one session per process, and no
        # client-facing id to align it with). The HTTP transport (2a) does
        # pass one — its own session id, the same one a client resubscribes
        # with — so the bus and the HTTP-visible session identity are the
        # same key, not two unrelated ones.
        self.session_id = session_id if session_id is not None else id(self)

    # -- wire --------------------------------------------------------------
    def _send(self, message):
        self.stdout.write(json.dumps(message) + "\n")
        self.stdout.flush()

    def _reply(self, request_id, result):
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _fail(self, request_id, code, message):
        self._send({"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": code, "message": message}})

    def _notify(self, method, params):
        """A server-initiated message — no `id`, per JSON-RPC's notification
        shape, so a client never mistakes it for a reply to something it
        asked."""
        self._send(notification_message(method, params))

    def _flush_resource_notifications(self):
        """Drain whatever this session's subscriptions accumulated and push
        one `notifications/resources/updated` per changed URI. Called at the
        end of every `handle()` turn (task 1e-5/1e-6) — the stdio transport
        has no idle-connection thread to push down mid-wait, so "the next
        time this session's loop turns over" is the delivery point (see
        bus.py's own docstring)."""
        for change in bus_mod.default().drain(self.session_id):
            self._notify("notifications/resources/updated", {"uri": change["uri"]})

    # -- methods -----------------------------------------------------------
    def _initialize(self, params):
        self.initialized = True
        return {
            "protocolVersion": PROTOCOL_VERSION,
            # Only what is actually implemented. Declaring prompts or sampling
            # here would have clients calling methods that do not exist.
            "capabilities": {
                "tools": {"listChanged": False},
                # T-017 FR-3: additive — a tools-only client that never calls
                # resources/* sees no change in behavior.
                "resources": {"subscribe": True, "listChanged": False},
            },
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }

    def handle(self, message):
        """Process one message. Returns True unless the session should end."""
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            self._fail(message.get("id") if isinstance(message, dict) else None,
                       INVALID_REQUEST, "not a JSON-RPC 2.0 message")
            return True

        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") or {}

        # A notification has no id and must never be answered — replying to one
        # is a protocol violation that some clients treat as fatal.
        is_notification = "id" not in message

        try:
            if method == "initialize":
                self._reply(request_id, self._initialize(params))
            elif method in ("notifications/initialized", "initialized"):
                pass
            elif method == "ping":
                if not is_notification:
                    self._reply(request_id, {})
            elif method == "tools/list":
                self._reply(request_id, {"tools": tool_list(self.repo_root)})
            elif method == "tools/call":
                name = params.get("name") or ""
                if not name:
                    self._fail(request_id, INVALID_PARAMS, "tools/call needs a name")
                else:
                    self._reply(request_id,
                                call_tool(self.repo_root, name,
                                          params.get("arguments")))
            elif method == "resources/list":
                self._reply(request_id, {"resources": resource_list(self.repo_root)})
            elif method == "resources/read":
                uri = params.get("uri") or ""
                try:
                    contents = resource_read(self.repo_root, uri)
                except (ValueError, FileNotFoundError) as exc:
                    self._fail(request_id, INVALID_PARAMS, str(exc))
                else:
                    self._reply(request_id, {"contents": [contents]})
            elif method == "resources/subscribe":
                uri = params.get("uri") or ""
                if not uri:
                    self._fail(request_id, INVALID_PARAMS, "resources/subscribe needs a uri")
                else:
                    bus_mod.default().subscribe(self.session_id, uri)
                    if not is_notification:
                        self._reply(request_id, {})
            elif method == "resources/unsubscribe":
                uri = params.get("uri") or ""
                bus_mod.default().unsubscribe(self.session_id, uri or None)
                if not is_notification:
                    self._reply(request_id, {})
            elif method in ("shutdown", "exit"):
                if not is_notification:
                    self._reply(request_id, {})
                if method == "exit":
                    bus_mod.default().unsubscribe(self.session_id)
                return False
            elif is_notification:
                pass  # unknown notifications are ignored, per JSON-RPC
            else:
                self._fail(request_id, METHOD_NOT_FOUND,
                           "unknown method %r; this server implements "
                           "initialize, tools/list, tools/call, resources/list, "
                           "resources/read, resources/subscribe and "
                           "resources/unsubscribe" % method)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc(file=self.stderr)
            if not is_notification:
                self._fail(request_id, INTERNAL_ERROR,
                           "%s: %s" % (type(exc).__name__, exc))
        self._flush_resource_notifications()
        return True

    def serve_forever(self):
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                self._fail(None, PARSE_ERROR, "invalid JSON")
                continue
            if not self.handle(message):
                break
