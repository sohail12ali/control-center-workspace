"""MCP server.

Driven the way a client drives it — JSON in, JSON out, over real streams — so
the framing and the notification rules are exercised rather than assumed. The
end-to-end test runs the actual entry-point script as a subprocess, because the
one failure this design is most exposed to is something printing to stdout and
corrupting the protocol stream, and that only shows up in a real process.
"""

import io
import json
import os
import subprocess
import sys

import pytest

from server import bus, mcp, tickets, verbs

VERBS = """\
[[verb]]
id = "context"
label = "Ticket context"
hint = "Everything about one ticket"
handler = "verb_handlers.ticket_context"
needs_ticket = true

[[verb]]
id = "telemetry"
label = "Token totals"
handler = "verb_handlers.telemetry_summary"

[[verb]]
id = "guarded"
label = "Mutates things"
handler = "verb_handlers.open_todos"
needs_confirm = true

[[verb]]
id = "ticket-move"
label = "Move a ticket"
handler = "verb_handlers.ticket_move"
needs_ticket = true
needs_confirm = true
"""


@pytest.fixture(autouse=True)
def _clean_bus():
    """The bus is a process-wide singleton (see bus.py) — clear it around
    every test so subscriptions/pending notifications never leak across
    tests that happen to reuse the same `id(session)`."""
    bus._default = bus.Bus()
    yield
    bus._default = bus.Bus()


@pytest.fixture
def wired(repo):
    with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(VERBS)
    verbs._cache.clear()
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()


class Session:
    """A client that speaks to a Server over in-memory streams."""

    def __init__(self, repo_root):
        self.out = io.StringIO()
        self.server = mcp.Server(repo_root, stdout=self.out,
                                 stderr=io.StringIO())

    def send(self, method, params=None, request_id=1, notification=False):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notification:
            message["id"] = request_id
        before = self.out.tell()
        self.server.handle(message)
        self.out.seek(before)
        raw = self.out.read().strip()
        self.out.seek(0, io.SEEK_END)
        return json.loads(raw) if raw else None


@pytest.fixture
def session(wired):
    s = Session(wired)
    s.send("initialize", {"protocolVersion": mcp.PROTOCOL_VERSION})
    return s


class TestHandshake:
    def test_initialize_reports_version_and_identity(self, wired):
        reply = Session(wired).send("initialize", {})
        result = reply["result"]
        assert result["protocolVersion"] == mcp.PROTOCOL_VERSION
        assert result["serverInfo"]["name"] == mcp.SERVER_NAME

    def test_only_implemented_capabilities_are_declared(self, wired):
        # Declaring prompts or sampling here would have clients calling
        # methods that do not exist. `resources` was added additively in
        # T-017 FR-3 — a tools-only client that never calls resources/* sees
        # no change in behavior (still exercised by the tests below).
        caps = Session(wired).send("initialize", {})["result"]["capabilities"]
        assert set(caps) == {"tools", "resources"}
        assert caps["resources"]["subscribe"] is True

    def test_initialized_notification_gets_no_reply(self, session):
        # Answering a notification is a protocol violation some clients treat
        # as fatal.
        assert session.send("notifications/initialized", notification=True) is None

    def test_unknown_notification_is_ignored_silently(self, session):
        assert session.send("notifications/whatever", notification=True) is None

    def test_unknown_method_is_a_jsonrpc_error(self, session):
        # `resources/list` is now implemented (T-017 FR-3) — use a method
        # that genuinely doesn't exist.
        reply = session.send("prompts/list")
        assert reply["error"]["code"] == mcp.METHOD_NOT_FOUND

    def test_a_non_jsonrpc_message_is_rejected(self, wired):
        s = Session(wired)
        s.server.handle({"method": "initialize"})
        assert "error" in json.loads(s.out.getvalue().strip())


class TestToolList:
    def test_tools_come_from_the_verb_registry(self, session):
        names = {t["name"] for t in session.send("tools/list")["result"]["tools"]}
        assert names == {"context", "telemetry", "guarded", "ticket-move"}

    def test_adding_a_verb_adds_a_tool_with_no_code_change(self, wired, session):
        path = os.path.join(wired, "console", "config", "verbs.toml")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write('\n[[verb]]\nid = "extra"\nlabel = "Extra"\n'
                     'handler = "verb_handlers.skill_usage"\n')
        verbs._cache.clear()
        names = {t["name"] for t in session.send("tools/list")["result"]["tools"]}
        assert "extra" in names

    def test_description_carries_label_and_hint(self, session):
        tools = {t["name"]: t for t in session.send("tools/list")["result"]["tools"]}
        assert tools["context"]["description"] == \
            "Ticket context — Everything about one ticket"

    def test_schema_is_derived_from_the_handler_signature(self, session):
        tools = {t["name"]: t for t in session.send("tools/list")["result"]["tools"]}
        schema = tools["telemetry"]["inputSchema"]
        # telemetry_summary(repo_root, ticket=None, by="ticket")
        assert set(schema["properties"]) == {"ticket", "by"}
        assert schema["required"] == []

    def test_a_required_ticket_is_marked_required(self, session):
        tools = {t["name"]: t for t in session.send("tools/list")["result"]["tools"]}
        assert tools["context"]["inputSchema"]["required"] == ["ticket"]

    def test_a_mutating_verb_requires_explicit_confirmation(self, session):
        tools = {t["name"]: t for t in session.send("tools/list")["result"]["tools"]}
        schema = tools["guarded"]["inputSchema"]
        assert schema["properties"]["confirm"]["type"] == "boolean"
        assert "confirm" in schema["required"]


class TestToolCall:
    def test_context_returns_markdown_not_json(self, session):
        # This tool exists to be read by a model, and its markdown is a third
        # the size of its JSON.
        text = session.send("tools/call", {
            "name": "context", "arguments": {"ticket": "CC-T001"},
        })["result"]["content"][0]["text"]
        assert text.startswith("# CC-T001")
        assert "## Plan" in text

    def test_other_tools_return_json(self, session):
        text = session.send("tools/call", {
            "name": "telemetry", "arguments": {},
        })["result"]["content"][0]["text"]
        assert json.loads(text)["group"] == "ticket"

    def test_arguments_reach_the_handler(self, session):
        text = session.send("tools/call", {
            "name": "telemetry", "arguments": {"by": "model"},
        })["result"]["content"][0]["text"]
        assert json.loads(text)["group"] == "model"

    def test_a_failed_gate_is_a_tool_error_not_a_protocol_error(self, session):
        # The model should see what went wrong and be able to correct itself,
        # which a JSON-RPC error code does not let it do.
        result = session.send("tools/call", {
            "name": "guarded", "arguments": {},
        })["result"]
        assert result["isError"] is True
        assert "confirm" in result["content"][0]["text"]

    def test_confirmation_lets_a_guarded_tool_run(self, session):
        result = session.send("tools/call", {
            "name": "guarded", "arguments": {"confirm": True},
        })["result"]
        assert "isError" not in result

    def test_an_unknown_tool_is_a_tool_error_naming_what_exists(self, session):
        result = session.send("tools/call", {"name": "ghost", "arguments": {}})["result"]
        assert result["isError"] is True
        assert "context" in result["content"][0]["text"]

    def test_a_missing_ticket_is_reported_not_crashed(self, session):
        result = session.send("tools/call", {
            "name": "context", "arguments": {"ticket": "CC-T999"},
        })["result"]
        assert result["isError"] is True

    def test_tools_call_without_a_name_is_invalid_params(self, session):
        assert session.send("tools/call", {})["error"]["code"] == mcp.INVALID_PARAMS


class TestResourcesList:
    """Task 1e-2: `resources/list` enumerates ticket-context resources."""

    def test_lists_one_resource_per_ticket(self, session):
        resources = session.send("resources/list")["result"]["resources"]
        assert len(resources) == 1
        assert resources[0]["uri"] == "ticket://CC-T001"
        assert resources[0]["name"] == "CC-T001"
        assert resources[0]["mimeType"] == "text/markdown"

    def test_reflects_a_newly_created_ticket(self, wired, session):
        tickets.create(wired, "CC-T002", "A second ticket")
        uris = {r["uri"] for r in session.send("resources/list")["result"]["resources"]}
        assert "ticket://CC-T002" in uris


class TestResourcesRead:
    """Task 1e-3: `resources/read` delegates to `verb_handlers.ticket_context`
    — the same content the `context` tool/verb produces."""

    def test_returns_the_same_content_as_the_context_tool(self, session):
        via_resource = session.send("resources/read",
                                    {"uri": "ticket://CC-T001"})["result"]["contents"][0]["text"]
        via_tool = session.send("tools/call", {
            "name": "context", "arguments": {"ticket": "CC-T001"},
        })["result"]["content"][0]["text"]
        assert via_resource == via_tool

    def test_mime_type_is_markdown(self, session):
        contents = session.send("resources/read",
                                {"uri": "ticket://CC-T001"})["result"]["contents"][0]
        assert contents["mimeType"] == "text/markdown"
        assert contents["uri"] == "ticket://CC-T001"

    def test_an_unknown_ticket_is_invalid_params_not_a_crash(self, session):
        reply = session.send("resources/read", {"uri": "ticket://CC-T999"})
        assert reply["error"]["code"] == mcp.INVALID_PARAMS

    def test_a_uri_outside_the_ticket_scheme_is_invalid_params(self, session):
        reply = session.send("resources/read", {"uri": "file:///etc/passwd"})
        assert reply["error"]["code"] == mcp.INVALID_PARAMS


class TestResourcesSubscribeAndNotify:
    """Tasks 1e-4/1e-5/1e-6: subscribe, then a verb mutation on that ticket
    delivers `notifications/resources/updated` to the subscribed session —
    scoped to this MCP session, never the console board UI (decision-log a8)."""

    def test_subscribe_acknowledges_with_an_empty_result(self, session):
        reply = session.send("resources/subscribe", {"uri": "ticket://CC-T001"})
        assert reply["result"] == {}

    def test_subscribe_without_a_uri_is_invalid_params(self, session):
        reply = session.send("resources/subscribe", {})
        assert reply["error"]["code"] == mcp.INVALID_PARAMS

    def test_a_mutation_on_a_subscribed_ticket_pushes_a_notification(self, session):
        session.send("resources/subscribe", {"uri": "ticket://CC-T001"})
        # The mutation and the notification are both produced by this single
        # `tools/call` turn — `Session.send` returns only the JSON-RPC reply,
        # so read the raw buffer to see the notification alongside it.
        before = session.out.tell()
        session.server.handle({
            "jsonrpc": "2.0", "id": 99, "method": "tools/call",
            "params": {"name": "ticket-move",
                      "arguments": {"ticket": "CC-T001", "stage": "blocked", "confirm": True}},
        })
        session.out.seek(before)
        lines = [json.loads(l) for l in session.out.read().strip().splitlines()]
        session.out.seek(0, io.SEEK_END)

        notifications = [m for m in lines if m.get("method") ==
                        "notifications/resources/updated"]
        assert len(notifications) == 1
        assert notifications[0]["params"]["uri"] == "ticket://CC-T001"
        assert "id" not in notifications[0]  # a notification, not a reply

    def test_a_mutation_on_an_unsubscribed_ticket_notifies_nobody(self, wired, session):
        tickets.create(wired, "CC-T002", "Not subscribed")
        session.send("resources/subscribe", {"uri": "ticket://CC-T001"})
        before = session.out.tell()
        session.server.handle({
            "jsonrpc": "2.0", "id": 99, "method": "tools/call",
            "params": {"name": "ticket-move",
                      "arguments": {"ticket": "CC-T002", "stage": "blocked", "confirm": True}},
        })
        session.out.seek(before)
        lines = [json.loads(l) for l in session.out.read().strip().splitlines()]
        session.out.seek(0, io.SEEK_END)
        assert not any(m.get("method") == "notifications/resources/updated" for m in lines)

    def test_unsubscribe_stops_future_notifications(self, session):
        session.send("resources/subscribe", {"uri": "ticket://CC-T001"})
        session.send("resources/unsubscribe", {"uri": "ticket://CC-T001"})
        before = session.out.tell()
        session.server.handle({
            "jsonrpc": "2.0", "id": 99, "method": "tools/call",
            "params": {"name": "ticket-move",
                      "arguments": {"ticket": "CC-T001", "stage": "blocked", "confirm": True}},
        })
        session.out.seek(before)
        lines = [json.loads(l) for l in session.out.read().strip().splitlines()]
        session.out.seek(0, io.SEEK_END)
        assert not any(m.get("method") == "notifications/resources/updated" for m in lines)


class TestStreamProtocol:
    def test_bad_json_gets_a_parse_error_and_the_session_continues(self, wired):
        stdin = io.StringIO('not json\n{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
        out = io.StringIO()
        mcp.Server(wired, stdin=stdin, stdout=out, stderr=io.StringIO()).serve_forever()
        replies = [json.loads(l) for l in out.getvalue().strip().splitlines()]
        assert replies[0]["error"]["code"] == mcp.PARSE_ERROR
        assert "tools" in replies[1]["result"]

    def test_blank_lines_are_skipped(self, wired):
        stdin = io.StringIO('\n\n{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n')
        out = io.StringIO()
        mcp.Server(wired, stdin=stdin, stdout=out, stderr=io.StringIO()).serve_forever()
        assert len(out.getvalue().strip().splitlines()) == 1

    def test_one_message_per_line(self, wired):
        stdin = io.StringIO(
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n')
        out = io.StringIO()
        mcp.Server(wired, stdin=stdin, stdout=out, stderr=io.StringIO()).serve_forever()
        lines = out.getvalue().strip().splitlines()
        assert [json.loads(l)["id"] for l in lines] == [1, 2]


class TestRealProcess:
    """The entry point as a client actually runs it."""

    def test_a_real_subprocess_speaks_clean_protocol(self):
        # The failure this guards: anything printing to stdout corrupts the
        # stream, and the client reports a parse error instead of the problem.
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo = os.path.dirname(root)
        proc = subprocess.run(
            [sys.executable, os.path.join(root, "mcp_server.py")],
            input='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
                  '{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
                  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n',
            capture_output=True, text=True, cwd=repo, timeout=60)

        lines = [l for l in proc.stdout.strip().splitlines() if l.strip()]
        replies = [json.loads(l) for l in lines]     # raises if stdout is dirty
        assert [r["id"] for r in replies] == [1, 2]
        assert replies[0]["result"]["serverInfo"]["name"] == mcp.SERVER_NAME

        names = {t["name"] for t in replies[1]["result"]["tools"]}
        assert {"context", "blockers", "harness-lint"} <= names

    def test_the_shipped_context_tool_answers_over_the_wire(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        repo = os.path.dirname(root)
        call = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "context",
                                      "arguments": {"ticket": "CC-T002"}}})
        proc = subprocess.run(
            [sys.executable, os.path.join(root, "mcp_server.py")],
            input=call + "\n", capture_output=True, text=True, cwd=repo, timeout=60)
        reply = json.loads(proc.stdout.strip().splitlines()[0])
        assert "CC-T002" in reply["result"]["content"][0]["text"]
