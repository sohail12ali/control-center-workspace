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


def reconfigure(repo, extra):
    """Rewrite the backend row with extra config and drop the cached registry."""
    with open(os.path.join(repo, "console", "config", "agents.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(BACKEND + extra + "\n")
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

    def test_extra_reaches_the_prompt_via_build(self, api):
        # T-004 C1: `extra=` threads through BaseSession -> ApiSession.start ->
        # prompt_build.build, so the assistant's injected context (tickets
        # digest/memory/capabilities) lands in the system message.
        provider = Provider(say("ok"))
        session = build(api, provider, extra="TICKET DIGEST: nothing open")
        run(session, "hi")
        system = provider.requests[0]["messages"][0]["content"]
        assert "TICKET DIGEST: nothing open" in system

    def test_extra_defaults_to_empty_and_adds_nothing(self, api):
        provider = Provider(say("ok"))
        session = build(api, provider)
        assert session.extra == ""

    def test_system_append_defaults_to_empty(self, api):
        provider = Provider(say("ok"))
        session = build(api, provider)
        assert session.system_append == ""

    def test_system_append_is_stored_when_given(self, api):
        provider = Provider(say("ok"))
        session = build(api, provider, system_append="be terse")
        assert session.system_append == "be terse"

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

    def test_the_runaway_cap_ends_the_turn_and_says_so(self, api):
        # Silently stopping is indistinguishable from finishing. Set through
        # config rather than by patching a constant, because that is the path
        # the cap actually travels now — a patched module attribute would keep
        # passing after the config route broke.
        reconfigure(api, "max_tool_rounds = 3")
        provider = Provider(*[call_tool("list_files", {}) for _ in range(10)])
        session = build(api, provider)
        run(session, "loop forever")

        notices = [e for e in events(session)
                   if e.get("type") == "notice" and e.get("kind") == "tool_limit"]
        assert notices, "hitting the cap must produce a visible notice"
        assert "3 tool rounds" in notices[0]["text"], \
            "the notice must name the limit that was actually enforced"
        end = [e for e in events(session) if e.get("type") == "turn.end"][-1]
        assert end["subtype"] == "tool_limit"


#: The renderer, as a file. The store's `case "..."` labels ARE the contract
#: between this transport and the browser, and reading them beats restating
#: them here — a list copied into this file would drift the same way the events
#: did.
STORE_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "static", "chat-store.js")


def handled_event_types():
    import re
    with open(STORE_JS, encoding="utf-8") as fh:
        return set(re.findall(r'case "([a-z][a-z._]*)"', fh.read()))


class TestEventShape:
    """The API loop must speak the renderer's vocabulary, not its own.

    It did not. `text.stop` where the store listens for `text.done`, `input`
    where it reads `args`, `tool.end` — consumed by nothing at all — instead of
    `tool.result`, and no `block` on any tool event even though `block` is the
    key items are filed under. Every one of these failed silently: the chat
    still rendered, just wrongly and only for this transport.
    """

    def test_every_event_emitted_is_one_the_store_handles(self, api):
        provider = Provider(call_tool("list_files", {}), say("here you go"))
        session = build(api, provider)
        run(session, "look around")

        handled = handled_event_types()
        assert "tool.result" in handled, "sanity: the store file was parsed"
        emitted = {e.get("type") for e in events(session)}
        unknown = {t for t in emitted if t and t not in handled}
        assert not unknown, (
            "these events reach the browser and fall through the store's "
            "switch untouched: %s" % sorted(unknown))

    def test_a_tool_call_carries_a_block_and_parsed_args(self, api):
        provider = Provider(call_tool("read_file", {"path": "README.md"}),
                            say("read it"))
        session = build(api, provider)
        run(session, "read the readme")

        start = [e for e in events(session) if e.get("type") == "tool.start"][0]
        assert start["block"], "without a block the store files it under `undefined`"
        # `args` is also where the "files touched" panel gets its paths.
        assert start["args"] == {"path": "README.md"}
        assert "input" not in start

    def test_a_tool_call_is_resolved_by_a_result(self, api):
        provider = Provider(call_tool("list_files", {}), say("done"))
        session = build(api, provider)
        run(session, "list")
        results = [e for e in events(session) if e.get("type") == "tool.result"]
        assert results and results[0]["ok"] is True
        assert results[0]["content"], "the result must carry the tool's output"

    def test_a_denied_call_resolves_as_a_failure_not_a_silence(self, api):
        provider = Provider(call_tool("write_file", {"path": "x.txt", "content": "hi"}),
                            say("understood"))
        session = build(api, provider)
        session.send("write something")
        pending = await_approval(session)
        agent_approvals.REGISTRY.decide(pending.key, "deny")
        if session._turn_thread:
            session._turn_thread.join(timeout=10)

        results = [e for e in events(session) if e.get("type") == "tool.result"]
        assert results, "a denied call must still close its block"
        assert results[0]["ok"] is False
        assert "Denied" in results[0]["content"]

    def test_blocks_are_unique_across_rounds(self, api):
        # A counter that restarts each turn makes round two overwrite round
        # one's bubbles, because the store keys every item by block.
        provider = Provider(call_tool("list_files", {}, call_id="c1"),
                            call_tool("list_files", {}, call_id="c2"),
                            say("finished"))
        session = build(api, provider)
        run(session, "twice")
        blocks = [e["block"] for e in events(session)
                  if e.get("type") in ("tool.start", "text.start")]
        assert len(blocks) == len(set(blocks)), "block numbers collided: %s" % blocks

    def test_text_is_closed_so_read_aloud_can_fire(self, api):
        # The UI speaks a reply when its block closes; an always-open block is
        # a reply that is never read.
        session = build(api, Provider(say("all done")))
        run(session, "go")
        assert [e for e in events(session) if e.get("type") == "text.done"]

    def test_a_tool_only_round_opens_no_empty_text_bubble(self, api):
        provider = Provider(call_tool("list_files", {}), say("done"))
        session = build(api, provider)
        run(session, "list")
        starts = [e for e in events(session) if e.get("type") == "text.start"]
        assert len(starts) == 1, "only the final spoken round should open text"


class TestBudgets:
    """Rounds and history are per-backend config, not one number for everyone.

    A 4k local model and a 200k hosted one cannot share a history cap: 120
    messages overflows the first long before the count is reached.
    """

    def test_a_row_that_says_nothing_gets_the_defaults(self, api):
        backend = agent_backends.get(api, "api")
        assert backend.max_tool_rounds == agent_backends.DEFAULT_TOOL_ROUNDS
        assert backend.max_history_messages == agent_backends.DEFAULT_HISTORY_MESSAGES

    def test_config_reaches_the_running_session(self, api):
        reconfigure(api, "max_tool_rounds = 4\nmax_history_messages = 9")
        session = build(api, Provider(say("hi")))
        assert session.max_tool_rounds == 4
        assert session.max_history_messages == 9

    def test_describe_reports_the_effective_budgets(self, api):
        reconfigure(api, "max_tool_rounds = 7")
        d = agent_backends.get(api, "api").describe()
        # Effective, not raw: the unset one still reports what will be enforced.
        assert d["budgets"] == {
            "tool_rounds": 7,
            "history_messages": agent_backends.DEFAULT_HISTORY_MESSAGES}

    def test_a_cli_backend_has_no_budgets_to_report(self, repo):
        # Its loop belongs to someone else, so reporting a number we do not
        # enforce would be a lie the Settings panel then displays.
        with open(os.path.join(repo, "console", "config", "agents.toml"), "w",
                  encoding="utf-8") as fh:
            fh.write('[[backend]]\nid = "cli"\ncommand = "x"\n'
                     'transport = "oneshot"\n')
        agent_backends._cache.clear()
        assert agent_backends.get(repo, "cli").describe()["budgets"] is None

    def test_a_budget_below_one_is_refused_at_load(self, api):
        # A cap of zero is a loop that ends before it starts, which looks
        # exactly like a hang. Fail beside the row that is wrong.
        reconfigure(api, "max_tool_rounds = 0")
        with pytest.raises(ValueError, match="max_tool_rounds must be at least 1"):
            agent_backends.get(api, "api")

    def test_history_is_trimmed_to_the_configured_size(self, api):
        reconfigure(api, "max_history_messages = 4")
        session = build(api, Provider(say("hi")))
        session._messages = [{"role": "system", "content": "SYS"}] + [
            {"role": "user", "content": str(i)} for i in range(20)]
        trimmed = session._trimmed_messages()
        assert len(trimmed) == 4
        # The system message carries the injected skill; losing it would
        # silently change what the agent thinks it was asked to do.
        assert trimmed[0]["content"] == "SYS"
        assert trimmed[-1]["content"] == "19"


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


class TestCaptureReachesTheModel:
    """T-007: a screenshot tool returns a PATH, and this transport has no file
    tools. Unless the picture itself follows, the model is being asked to look
    at a string. These drive the real loop and read what went on the wire."""

    def _capture_on_disk(self, repo):
        import struct, zlib
        from server import multimodal
        rel = os.path.join(multimodal.CAPTURE_DIR_REL, "e2e.png").replace("\\", "/")
        path = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        raw = b"".join(b"\x00" + bytes([0, 128, 255, 255] * 4) for _ in range(4))

        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\x0a"[:8].replace(b"\x0a", b"\n")
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9))
                     + chunk(b"IEND", b""))
        return rel

    def _screenshot_tool(self, monkeypatch, rel):
        """Make the screenshot verb return a capture without a desktop shell."""
        from server import agent_tools
        real = agent_tools.dispatch

        def fake(repo_root, name, arguments):
            if "desktop_screenshot" in name:
                return json.dumps({"ok": True, "capture": {
                    "capture_id": "e2e", "path": rel, "width": 4, "height": 4}})
            return real(repo_root, name, arguments)

        monkeypatch.setattr(agent_tools, "dispatch", fake)

    def _user_parts(self, provider):
        """Every user message on the last request, as sent."""
        last = provider.requests[-1]
        return [m for m in last["messages"] if m.get("role") == "user"]

    def test_a_vision_model_receives_the_image_itself(self, api, monkeypatch):
        rel = self._capture_on_disk(api)
        self._screenshot_tool(monkeypatch, rel)
        with open(os.path.join(api, "console", "config", "assistant.toml"),
                  "w", encoding="utf-8") as fh:
            fh.write('[assistant]\nvision_models = ["*vl*", "gpt-4o*"]\n')

        provider = Provider(
            call_tool("console_desktop_screenshot", {"target": "screen"}),
            say("I can see a small blue square."),
        )
        session = build(api, provider)
        # `build` fixes the model, so it is set here — what matters is the id
        # the request carries and that `_vision_patterns` matches it.
        session.model = "qwen2.5vl:7b"
        run(session, "what is on my screen?")

        parts = [m["content"] for m in self._user_parts(provider)
                 if isinstance(m["content"], list)]
        assert parts, "no image part reached the wire"
        kinds = [p["type"] for p in parts[0]]
        assert "image_url" in kinds
        url = [p for p in parts[0] if p["type"] == "image_url"][0]["image_url"]["url"]
        assert url.startswith("data:image/png;base64,")

    def test_a_text_only_model_is_told_to_use_ocr_instead(self, api, monkeypatch):
        rel = self._capture_on_disk(api)
        self._screenshot_tool(monkeypatch, rel)
        with open(os.path.join(api, "console", "config", "assistant.toml"),
                  "w", encoding="utf-8") as fh:
            fh.write('[assistant]\nvision_models = ["*vl*"]\n')

        provider = Provider(
            call_tool("console_desktop_screenshot", {"target": "screen"}),
            say("I used OCR."),
        )
        session = build(api, provider)
        session.model = "llama3"
        run(session, "what is on my screen?")

        texts = [m["content"] for m in self._user_parts(provider)
                 if isinstance(m["content"], str)]
        assert any("desktop_ocr" in t for t in texts), texts
        assert not any(isinstance(m["content"], list)
                       for m in self._user_parts(provider)), (
            "a text-only model must not be sent pixels")

    def test_an_ordinary_tool_call_adds_nothing(self, api):
        provider = Provider(
            call_tool("console_context", {"ticket": "CC-T001"}),
            say("done"),
        )
        session = build(api, provider)
        run(session, "what is the status?")
        # Exactly the one message the user actually sent.
        assert len(self._user_parts(provider)) == 1

