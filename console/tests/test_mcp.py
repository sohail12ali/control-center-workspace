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

from server import mcp, tickets, verbs

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
"""


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
        # Declaring resources or prompts here would have clients calling
        # methods that do not exist.
        caps = Session(wired).send("initialize", {})["result"]["capabilities"]
        assert set(caps) == {"tools"}

    def test_initialized_notification_gets_no_reply(self, session):
        # Answering a notification is a protocol violation some clients treat
        # as fatal.
        assert session.send("notifications/initialized", notification=True) is None

    def test_unknown_notification_is_ignored_silently(self, session):
        assert session.send("notifications/whatever", notification=True) is None

    def test_unknown_method_is_a_jsonrpc_error(self, session):
        reply = session.send("resources/list")
        assert reply["error"]["code"] == mcp.METHOD_NOT_FOUND

    def test_a_non_jsonrpc_message_is_rejected(self, wired):
        s = Session(wired)
        s.server.handle({"method": "initialize"})
        assert "error" in json.loads(s.out.getvalue().strip())


class TestToolList:
    def test_tools_come_from_the_verb_registry(self, session):
        names = {t["name"] for t in session.send("tools/list")["result"]["tools"]}
        assert names == {"context", "telemetry", "guarded"}

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
