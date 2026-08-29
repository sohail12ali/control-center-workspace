"""The `openai_api` transport — a full agent loop, driven by a scripted provider.

No network anywhere. A fake opener returns whatever SSE the test wants, which
makes the loop's real behaviours testable: a tool call executed and fed back, a
gated call parked on a human's answer, a denial the model can read, the runaway
cap, and telemetry recorded through the same path every other backend uses.
"""

import io
import json
import os
import threading
import time

import pytest

from server import (agent_approvals, agent_backends, agent_session, telemetry,
                    tickets, verbs)

VERBS = """\
[[verb]]
id = "context"
label = "Ticket context"
handler = "verb_handlers.ticket_context"
needs_ticket = true
"""

BACKEND = """\
[[backend]]
id = "api"
label = "Test API"
transport = "openai_api"
base_url = "https://example.test/v1"
api_key_env = "TEST_API_KEY"
prompt_prefix_style = "none"
gated_tools = ["write_file", "run_command"]
approval_timeout = 2
modes = ["default"]
default_mode = "default"
models = []
"""


def sse(*chunks):
    lines = ["data: " + json.dumps(c) for c in chunks] + ["data: [DONE]"]
    return io.StringIO("\n\n".join(lines) + "\n")


def say(text, usage=None):
    chunks = [{"choices": [{"delta": {"content": text}, "finish_reason": "stop"}]}]
    chunks.append({"choices": [], "usage": usage or {"prompt_tokens": 10,
                                                     "completion_tokens": 5}})
    return sse(*chunks)


def call_tool(name, arguments, call_id="call_1"):
    return sse(
        {"choices": [{"delta": {"tool_calls": [
            {"index": 0, "id": call_id,
             "function": {"name": name, "arguments": json.dumps(arguments)}}]},
            "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 8, "completion_tokens": 3}},
    )


class Provider:
    """Returns each scripted response in turn, recording what it was sent."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(json.loads(request.data))
        if not self.responses:
            return say("done")
        return self.responses.pop(0)


@pytest.fixture
def api(repo, monkeypatch):
    monkeypatch.setenv("TEST_API_KEY", "sk-test")
    with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(VERBS)
    with open(os.path.join(repo, "console", "config", "agents.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(BACKEND)
    os.makedirs(os.path.join(repo, ".claude", "skills", "harness-standards"),
                exist_ok=True)
    with open(os.path.join(repo, ".claude", "skills", "harness-standards",
                           "core.md"), "w", encoding="utf-8") as fh:
        fh.write("---\nname: harness-standards\n---\n\nBE HONEST always.\n")
    verbs._cache.clear()
    agent_backends._cache.clear()
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()
    agent_backends._cache.clear()


def build(repo, provider, **kw):
    backend = agent_backends.get(repo, "api")
    session = agent_session.build("sid1", backend, repo, model="test/model", **kw)
    session.client.stream = _patched(session.client, provider)
    session.start()
    return session


def _patched(client, provider):
    original = client.stream

    def stream(messages, **kw):
        kw["opener"] = provider
        return original(messages, **kw)
    return stream


def run(session, text, timeout=10):
    """Send a message and block until its turn thread finishes."""
    session.send(text)
    thread = session._turn_thread
    if thread:
        thread.join(timeout=timeout)
    return events(session)


def events(session):
    """Every event the session published, straight out of the stream's ring."""
    return list(session.stream._ring)


def await_approval(session, tries=300):
    """Wait for the gated call to park on a human, the way the browser does."""
    for _ in range(tries):
        pending = [p for p in agent_approvals.REGISTRY._pending.values()
                   if p.chat == session.id]
        if pending:
            return pending[0]
        time.sleep(0.01)
    raise AssertionError("no approval was requested")


class TestTransportWiring:
    def test_build_selects_the_api_session(self, api):
        session = build(api, Provider())
        assert type(session).__name__ == "ApiSession"

    def test_installed_means_a_key_not_a_binary(self, api, monkeypatch):
        backend = agent_backends.get(api, "api")
        assert backend.installed is True
        monkeypatch.delenv("TEST_API_KEY")
        assert backend.installed is False
        assert "TEST_API_KEY" in backend.unavailable_reason

    def test_it_streams_but_cannot_be_steered(self, api):
        backend = agent_backends.get(api, "api")
        assert (backend.streaming, backend.steerable) == (True, False)

    def test_the_approval_gate_is_claimed_for_an_api_backend(self, api):
        # A CLI can only gate through a hook; this loop gates in-process, so
        # the hook-only restriction must not be applied to it.
        assert agent_backends.get(api, "api").describe()["approval_gate"] is True

    def test_an_unknown_transport_is_still_refused(self):
        with pytest.raises(ValueError):
            agent_backends.Backend({"id": "x", "transport": "carrier-pigeon"})


class TestPromptInjection:
    def test_the_skill_text_is_in_the_prompt_not_the_message(self, api):
        os.makedirs(os.path.join(api, ".claude", "skills", "demo"), exist_ok=True)
        with open(os.path.join(api, ".claude", "skills", "demo", "SKILL.md"), "w",
                  encoding="utf-8") as fh:
            fh.write("---\nname: demo\n---\n\nALWAYS COUNT BACKWARDS.\n")
        provider = Provider(say("ok"))
        session = build(api, provider, skill="demo")
        run(session, "hello")

        system = provider.requests[0]["messages"][0]
        assert system["role"] == "system"
        assert "ALWAYS COUNT BACKWARDS" in system["content"]
        # The user message stays exactly what was typed — no "/demo" prefix,
        # because there is no slash-command system to interpret one.
        assert provider.requests[0]["messages"][-1]["content"] == "hello"

    def test_the_always_on_core_is_included(self, api):
        provider = Provider(say("ok"))
        run(build(api, provider), "hi")
        assert "BE HONEST" in provider.requests[0]["messages"][0]["content"]

    def test_a_missing_skill_is_reported_rather_than_silently_absent(self, api):
        session = build(api, Provider(say("ok")), skill="nonexistent")
        assert "skill:nonexistent" in session._system_report["missing"]

    def test_frontmatter_is_stripped(self, api):
        provider = Provider(say("ok"))
        run(build(api, provider), "hi")
        system = provider.requests[0]["messages"][0]["content"]
        assert "name: harness-standards" not in system


class TestToolLoop:
    def test_a_tool_call_is_executed_and_fed_back(self, api):
        with open(os.path.join(api, "note.txt"), "w") as fh:
            fh.write("hello from the file")
        provider = Provider(call_tool("read_file", {"path": "note.txt"}),
                            say("I read it."))
        session = build(api, provider)
        run(session, "read note.txt")

        second = provider.requests[1]["messages"]
        tool_result = [m for m in second if m.get("role") == "tool"][0]
        assert "hello from the file" in tool_result["content"]
        assert tool_result["tool_call_id"] == "call_1"

    def test_console_verbs_are_offered_as_tools(self, api):
        provider = Provider(say("ok"))
        run(build(api, provider), "hi")
        names = {t["function"]["name"] for t in provider.requests[0]["tools"]}
        assert "console_context" in names
        assert "read_file" in names

    def test_a_verb_tool_call_runs_the_verb(self, api):
        provider = Provider(call_tool("console_context", {"ticket": "CC-T001"}),
                            say("got it"))
        session = build(api, provider)
        run(session, "what is CC-T001")
        tool_result = [m for m in provider.requests[1]["messages"]
                       if m.get("role") == "tool"][0]
        assert "CC-T001" in tool_result["content"]

    def test_a_failing_tool_returns_text_the_model_can_act_on(self, api):
        provider = Provider(call_tool("read_file", {"path": "../escape"}),
                            say("understood"))
        session = build(api, provider)
        run(session, "read it")
        tool_result = [m for m in provider.requests[1]["messages"]
                       if m.get("role") == "tool"][0]
        assert "outside the workspace" in tool_result["content"]

    def test_malformed_tool_arguments_are_explained_not_guessed(self, api):
        broken = sse(
            {"choices": [{"delta": {"tool_calls": [
                {"index": 0, "id": "c1",
                 "function": {"name": "read_file", "arguments": "{not json"}}]},
                "finish_reason": "tool_calls"}]},
            {"choices": [], "usage": {}})
        provider = Provider(broken, say("sorry"))
        session = build(api, provider)
        run(session, "go")
        tool_result = [m for m in provider.requests[1]["messages"]
                       if m.get("role") == "tool"][0]
        assert "not valid JSON" in tool_result["content"]

    def test_the_runaway_cap_ends_the_turn_and_says_so(self, api, monkeypatch):
        # Silently stopping is indistinguishable from finishing.
        from server import agent_api_session
        monkeypatch.setattr(agent_api_session, "MAX_TOOL_ROUNDS", 3)
        provider = Provider(*[call_tool("list_files", {}) for _ in range(10)])
        session = build(api, provider)
        run(session, "loop forever")

        notices = [e for e in events(session)
                   if e.get("type") == "notice" and e.get("kind") == "tool_limit"]
        assert notices, "hitting the cap must produce a visible notice"
        end = [e for e in events(session) if e.get("type") == "turn.end"][-1]
        assert end["subtype"] == "tool_limit"


class TestApprovalGate:
    def test_a_gated_tool_asks_before_running(self, api):
        provider = Provider(call_tool("write_file",
                                      {"path": "new.txt", "content": "x"}),
                            say("written"))
        session = build(api, provider)
        session.send("write a file")

        # The card appears; answer it the way the browser would.
        pending = await_approval(session)
        assert pending.tool == "write_file"
        agent_approvals.REGISTRY.decide(pending.key, "allow", by="test")

        session._turn_thread.join(timeout=10)
        assert os.path.isfile(os.path.join(api, "new.txt"))

    def test_a_denial_reaches_the_model_as_a_tool_result(self, api):
        provider = Provider(call_tool("write_file",
                                      {"path": "new.txt", "content": "x"}),
                            say("understood"))
        session = build(api, provider)
        session.send("write a file")

        pending = await_approval(session)
        agent_approvals.REGISTRY.decide(pending.key, "deny", by="test",
                                        reason="not this time")
        session._turn_thread.join(timeout=10)

        assert not os.path.exists(os.path.join(api, "new.txt"))
        tool_result = [m for m in provider.requests[1]["messages"]
                       if m.get("role") == "tool"][0]
        assert "Denied" in tool_result["content"]
        assert "not this time" in tool_result["content"]

    def test_silence_denies_rather_than_running(self, api):
        # Fail-closed: an unanswered card must not become an allow.
        provider = Provider(call_tool("run_command", {"command": "echo nope"}),
                            say("ok"))
        session = build(api, provider)
        run(session, "run it", timeout=15)
        tool_result = [m for m in provider.requests[1]["messages"]
                       if m.get("role") == "tool"][0]
        assert "Denied" in tool_result["content"]

    def test_read_only_console_verbs_are_not_gated(self, api):
        # Approving "look up this ticket's lane" trains people to click allow
        # without reading, which is how the gate stops working where it counts.
        provider = Provider(call_tool("console_context", {"ticket": "CC-T001"}),
                            say("done"))
        session = build(api, provider)
        run(session, "look it up")
        assert not [p for p in agent_approvals.REGISTRY._pending.values()
                    if p.chat == session.id]

    def test_reads_are_not_gated(self, api):
        with open(os.path.join(api, "note.txt"), "w") as fh:
            fh.write("data")
        provider = Provider(call_tool("read_file", {"path": "note.txt"}),
                            say("read"))
        session = build(api, provider)
        run(session, "read")
        assert not [p for p in agent_approvals.REGISTRY._pending.values()
                    if p.chat == session.id]


class TestEventsAndTelemetry:
    def test_it_emits_the_same_event_shapes_as_the_cli_backends(self, api):
        provider = Provider(say("Hello"))
        session = build(api, provider)
        run(session, "hi")
        kinds = {e.get("type") for e in events(session)}
        assert {"session.init", "turn.start", "text.start", "text.delta",
                "usage", "turn.end"} <= kinds

    def test_a_turn_writes_a_telemetry_record(self, api):
        provider = Provider(say("Hello", usage={"prompt_tokens": 100,
                                                "completion_tokens": 40}))
        session = build(api, provider, ticket="CC-T001", skill="", persona="")
        run(session, "hi")
        record = telemetry.read_records(api)[0]
        assert record["ticket"] == "CC-T001"
        assert (record["input_tokens"], record["output_tokens"]) == (100, 40)
        assert record["backend"] == "api"

    def test_usage_accumulates_across_tool_rounds(self, api):
        provider = Provider(call_tool("list_files", {}),
                            say("done", usage={"prompt_tokens": 20,
                                               "completion_tokens": 6}))
        session = build(api, provider, ticket="CC-T001")
        run(session, "go")
        record = telemetry.read_records(api)[0]
        assert record["input_tokens"] == 28      # 8 from the tool round + 20

    def test_an_api_error_becomes_a_readable_notice_not_a_crash(self, api):
        import urllib.error

        def exploding(request, timeout=None):
            raise urllib.error.HTTPError(
                request.full_url, 401, "no", {},
                io.BytesIO(json.dumps({"error": {"message": "bad key"}}).encode()))

        session = build(api, exploding)
        run(session, "hi")
        notices = [e for e in events(session) if e.get("type") == "notice"
                   and e.get("level") == "error"]
        assert notices and "bad key" in notices[0]["text"]
        assert [e for e in events(session) if e.get("type") == "turn.end"]

    def test_no_api_key_appears_in_any_event_or_record(self, api):
        provider = Provider(say("hi"))
        session = build(api, provider, ticket="CC-T001")
        run(session, "hello")
        blob = json.dumps(events(session)) + json.dumps(telemetry.read_records(api))
        assert "sk-test" not in blob
