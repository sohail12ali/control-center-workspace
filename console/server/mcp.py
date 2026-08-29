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
`notifications/initialized` acknowledgement. That is the whole stable core of
the protocol and everything a tool provider needs. Resources, prompts, sampling
and completion are not implemented, and the server says so through its declared
capabilities rather than by failing calls at runtime.

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

from . import context as context_mod
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

    def __init__(self, repo_root, stdin=None, stdout=None, stderr=None):
        self.repo_root = repo_root
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr
        self.initialized = False

    # -- wire --------------------------------------------------------------
    def _send(self, message):
        self.stdout.write(json.dumps(message) + "\n")
        self.stdout.flush()

    def _reply(self, request_id, result):
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _fail(self, request_id, code, message):
        self._send({"jsonrpc": "2.0", "id": request_id,
                    "error": {"code": code, "message": message}})

    # -- methods -----------------------------------------------------------
    def _initialize(self, params):
        self.initialized = True
        return {
            "protocolVersion": PROTOCOL_VERSION,
            # Only what is actually implemented. Declaring resources or prompts
            # here would have clients calling methods that do not exist.
            "capabilities": {"tools": {"listChanged": False}},
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
            elif method in ("shutdown", "exit"):
                if not is_notification:
                    self._reply(request_id, {})
                return False
            elif is_notification:
                pass  # unknown notifications are ignored, per JSON-RPC
            else:
                self._fail(request_id, METHOD_NOT_FOUND,
                           "unknown method %r; this server implements "
                           "initialize, tools/list and tools/call" % method)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc(file=self.stderr)
            if not is_notification:
                self._fail(request_id, INTERNAL_ERROR,
                           "%s: %s" % (type(exc).__name__, exc))
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
