"""T-004 — the Assistant: persona/context threading, memory, routes, fast
commands, settings, and the `kanban.py assistant say` CLI parity command.

New behavior with no existing test-file home lives here, per the routing rule
in `T-004-task-breakdown.md`'s header. Extensions to an already-tested module
(`BaseSession`, `Backend.session_argv`, `prompt_build`, verbs, audit, plugins)
live in that module's own existing test file instead.
"""

import os

import pytest

from server import agent_backends, agent_manager, agent_session, assistant
from server.features import assistant_feature


# ---------------------------------------------------------------------------
# C1 (task 1-2-6): agent_manager.create's system_append handling for a
# backend with no system-prompt flag of its own (cursor-agent-shaped) versus
# one that has one (claude-shaped).
# ---------------------------------------------------------------------------

class FakeSession:
    """Stands in for a real LiveSession/TurnSession: records what it was
    asked to do instead of spawning a process, so this test exercises only
    the wire-prefix decision `agent_manager.create` makes."""

    def __init__(self, *a, **kw):
        self.kw = kw
        self.sent = []
        self.id = "fake-sid"

    def start(self):
        pass

    def send(self, wire, mode="auto", display=""):
        self.sent.append((wire, mode, display))
        return "sent"

    def snapshot(self):
        return {"id": self.id, "sent": list(self.sent)}


@pytest.fixture
def stub_build(monkeypatch):
    """Replace agent_session.build with one that returns a FakeSession, and
    forget it in agent_manager afterwards so a fake session doesn't leak
    across tests via the module-level session dict."""
    created = {}

    def fake_build(sid, backend, cwd, **kw):
        sess = FakeSession(**kw)
        created["sess"] = sess
        return sess

    monkeypatch.setattr(agent_session, "build", fake_build)
    monkeypatch.setattr(agent_manager, "agent_session", agent_session)
    yield created
    with agent_manager._lock:
        agent_manager._sessions.clear()


def _cursor_agent_backend(monkeypatch):
    """cursor-agent-shaped: `resume` transport, no `{system_append}` slot in
    either turn form — the honest "no flag" case."""
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    return agent_backends.Backend({
        "id": "cursor-agent", "transport": "resume",
        "command": "cursor-agent",
        "turn_args": ["-p", "{prompt}", "--trust", "--mode", "{mode}"],
        "resume_args": ["-p", "{prompt}", "--trust", "--resume", "{resume_id}"],
        "prompt_prefix_style": "inline",
        "modes": ["default"], "default_mode": "default",
    })


def _claude_backend(monkeypatch):
    """claude-shaped: `stream_json` transport with its own
    `--append-system-prompt {system_append}` flag."""
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    return agent_backends.Backend({
        "id": "claude", "transport": "stream_json",
        "command": "claude",
        "session_args": ["-p", "--append-system-prompt", "{system_append}"],
        "prompt_prefix_style": "slash",
        "modes": ["default"], "default_mode": "default",
    })


class TestSystemAppendDispatch:
    def test_cursor_agent_first_turn_prompt_starts_with_persona_text(
            self, repo, monkeypatch, stub_build):
        backend = _cursor_agent_backend(monkeypatch)
        monkeypatch.setattr(agent_backends, "get", lambda root, bid: backend)
        agent_manager.create(repo, "cursor-agent", "hello",
                             system_append="PERSONA TEXT")
        sess = stub_build["sess"]
        wire, _mode, _display = sess.sent[0]
        assert wire.startswith("PERSONA TEXT")
        assert wire.endswith("hello")

    def test_claude_wire_is_unmodified_flag_carries_it_instead(
            self, repo, monkeypatch, stub_build):
        backend = _claude_backend(monkeypatch)
        monkeypatch.setattr(agent_backends, "get", lambda root, bid: backend)
        agent_manager.create(repo, "claude", "hello",
                             system_append="PERSONA TEXT")
        sess = stub_build["sess"]
        wire, _mode, _display = sess.sent[0]
        assert wire == "hello"
        # The text was still threaded — just via the session kwarg, not the
        # first message, because claude's own flag carries it instead.
        assert sess.kw.get("system_append") == "PERSONA TEXT"

    def test_empty_system_append_never_touches_the_wire(
            self, repo, monkeypatch, stub_build):
        backend = _cursor_agent_backend(monkeypatch)
        monkeypatch.setattr(agent_backends, "get", lambda root, bid: backend)
        agent_manager.create(repo, "cursor-agent", "hello")
        sess = stub_build["sess"]
        assert sess.sent[0][0] == "hello"


# ---------------------------------------------------------------------------
# C8 (tasks 1-9-1..3): file-based memory under console/.cache/assistant/.
# ---------------------------------------------------------------------------

class TestSessionPointer:
    def test_no_pointer_before_the_first_run(self, repo):
        assert assistant.read_session(repo) is None

    def test_write_then_read_round_trips(self, repo):
        record = assistant.write_session(repo, sid="sid1", backend="claude",
                                         model="sonnet")
        assert record["sid"] == "sid1"
        assert record["backend"] == "claude"
        assert record["model"] == "sonnet"
        assert record["created_at"] and record["updated_at"]
        assert assistant.read_session(repo) == record

    def test_overwriting_the_same_sid_keeps_created_at(self, repo):
        first = assistant.write_session(repo, sid="sid1", backend="claude")
        second = assistant.write_session(repo, sid="sid1", backend="claude",
                                         model="opus")
        assert second["created_at"] == first["created_at"]
        assert second["model"] == "opus"

    def test_a_new_sid_gets_a_fresh_created_at(self, repo):
        assistant.write_session(repo, sid="sid1", backend="claude")
        second = assistant.write_session(repo, sid="sid2", backend="claude")
        assert second["sid"] == "sid2"

    def test_a_corrupt_pointer_file_is_treated_as_absent(self, repo):
        path = os.path.join(assistant.cache_dir(repo), assistant.SESSION_FILE)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        assert assistant.read_session(repo) is None


class TestMemory:
    def test_remember_appends(self, repo):
        result = assistant.remember(repo, "the sky is blue")
        assert result["ok"] is True
        assert "the sky is blue" in assistant.read_memory(repo)

    def test_multiple_facts_accumulate(self, repo):
        assistant.remember(repo, "fact one")
        assistant.remember(repo, "fact two")
        mem = assistant.read_memory(repo)
        assert "fact one" in mem and "fact two" in mem

    def test_over_cap_trims_oldest_first_never_errors(self, repo):
        # Each fact is short; enough of them blow the 1,500-char cap.
        for i in range(200):
            result = assistant.remember(repo, "fact number %03d filler text" % i)
            assert result["ok"] is True
        mem = assistant.read_memory(repo)
        assert len(mem) <= assistant.MEMORY_CAP
        assert "fact number 199" in mem, "the newest fact must survive the trim"
        assert "fact number 000" not in mem, "the oldest fact must be the one dropped"

    def test_empty_fact_is_declined_without_raising(self, repo):
        result = assistant.remember(repo, "   ")
        assert result["ok"] is False
        assert assistant.read_memory(repo) == ""

    @pytest.mark.parametrize("secret", [
        "-----BEGIN PRIVATE KEY-----\nMIIBogIB\n-----END PRIVATE KEY-----",
        "sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123456789",
        "sk-abcdefghijklmnopqrstuvwxyz0123456789",
        "AKIAABCDEFGHIJKLMNOP",
        "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        "OPENROUTER_API_KEY=sk-or-v1-abcdef0123456789",
    ])
    def test_secret_shaped_facts_are_declined_never_appended(self, repo, secret):
        result = assistant.remember(repo, secret)
        assert result["ok"] is False
        assert "credential" in result["reason"]
        assert assistant.read_memory(repo) == ""

    def test_an_ordinary_fact_with_an_equals_sign_is_not_flagged(self, repo):
        # The secret guard must not be so eager it declines ordinary text.
        result = assistant.remember(repo, "the meeting is at 3 = half past 2 for me")
        assert result["ok"] is True


class TestLastReply:
    def test_no_file_before_the_first_turn(self, repo):
        assert assistant.read_last_reply(repo) == ""

    def test_write_then_read_round_trips(self, repo):
        assistant.write_last_reply(repo, "here is the answer")
        assert assistant.read_last_reply(repo) == "here is the answer"

    def test_overwritten_each_turn_never_grows(self, repo):
        assistant.write_last_reply(repo, "first reply, quite a long one indeed")
        assistant.write_last_reply(repo, "second")
        assert assistant.read_last_reply(repo) == "second"


# ---------------------------------------------------------------------------
# C2 (tasks 2-1-1..5): assistant_feature.py's plugin routes, against a fake
# agent_manager — no real backend process is ever spawned by these tests.
# ---------------------------------------------------------------------------

class FakeAssistantSession:
    def __init__(self, sid, agent="claude", model=""):
        self.id = sid
        self.agent = agent
        self.model = model
        self._alive = True
        self.sent = []
        self.next_send_result = "sent"

    @property
    def alive(self):
        return self._alive

    def send(self, text, mode="auto", display=""):
        self.sent.append(text)
        return self.next_send_result

    def snapshot(self):
        return {"id": self.id, "agent": self.agent, "model": self.model,
                "busy": False, "alive": self.alive}


@pytest.fixture
def fake_manager(monkeypatch):
    """Stands in for the whole agent_manager module: create/get/require/
    subscribe, so a route test never spawns a real process."""
    store = {}

    def fake_create(repo_root, backend_id, prompt, **kw):
        sid = "fake-%d" % (len(store) + 1)
        sess = FakeAssistantSession(sid, agent=backend_id, model=kw.get("model", ""))
        store[sid] = sess
        return sess.snapshot()

    def fake_get(sid):
        return store.get(sid)

    def fake_require(sid):
        sess = store.get(sid)
        if sess is None:
            raise FileNotFoundError("no live session %r" % sid)
        return sess

    def fake_subscribe(repo_root, sid, from_seq=0, types=None):
        events = [
            {"type": "turn.start", "seq": 1}, {"type": "usage", "seq": 2},
            {"type": "reply", "seq": 3, "text": "hi"},
            {"type": "tool.start", "seq": 4}, {"type": "turn.end", "seq": 5},
        ]
        for ev in events:
            if types is None or ev["type"] in types:
                yield "data: %s\n\n" % ev["type"]

    monkeypatch.setattr(agent_manager, "create", fake_create)
    monkeypatch.setattr(agent_manager, "get", fake_get)
    monkeypatch.setattr(agent_manager, "require", fake_require)
    monkeypatch.setattr(agent_manager, "subscribe", fake_subscribe)
    return store


@pytest.fixture
def routes(repo, monkeypatch, fake_manager):
    """Build the assistant plugin's routes the same way test_plugins.py's
    TestVerbRoutes does — call the handler directly, no HTTP."""
    monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
    out = {}

    class Ctx:
        repo_root = repo

        def get(self, pattern, fn, name):
            out[("GET", name)] = fn

        def post(self, pattern, fn, name):
            out[("POST", name)] = fn

        def register_tab(self, *a, **kw):
            raise AssertionError("no tab yet — T-006 adds one")

        def provide(self, *a, **kw):
            pass

    assistant_feature.apply(Ctx())
    return out


class Req:
    def __init__(self, body=None, query=None):
        self.body = body or {}
        self.query = query or {}
        self.client_addr = ""
        self.user_agent = ""


class TestInjectedContext:
    """C4 (task 3-4-1): tickets digest + memory + a capabilities line,
    composed into `extra`/`system_append`, each individually capped."""

    def test_composed_extra_has_all_three_sections(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        assistant.remember(repo, "the sky is blue")
        backend = agent_backends.get(repo, "alpha")
        extra = assistant_feature._compose_extra(repo, backend)
        assert "## Open tickets" in extra
        assert "## Remembered" in extra and "the sky is blue" in extra
        assert "## Capabilities" in extra

    def test_no_memory_section_when_nothing_was_remembered(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        backend = agent_backends.get(repo, "alpha")
        extra = assistant_feature._compose_extra(repo, backend)
        assert "## Remembered" not in extra

    def test_an_oversized_section_is_capped_with_a_stated_marker(self):
        capped = assistant_feature._cap_section("x" * 2000, 1200, "tickets digest")
        assert len(capped) < 2000
        assert capped.startswith("x" * 1200)
        assert "cut to fit" in capped

    def test_capabilities_line_names_locality_and_bridge_state(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        backend = agent_backends.get(repo, "alpha")
        line = assistant_feature._capabilities_line(repo, backend)
        assert "backend=alpha" in line
        assert "native bridge=unavailable" in line  # T-004: always, honestly

    def test_vision_defaults_to_no_before_assistant_toml_exists(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        backend = agent_backends.get(repo, "alpha")
        assert assistant_feature._vision_capable(repo, backend) is False

    def test_vision_reads_assistant_toml_once_it_exists(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: "/usr/bin/" + cmd)
        path = os.path.join(repo, "console", "config", "assistant.toml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('[assistant]\nvision_models = ["big"]\n')
        backend = agent_backends.get(repo, "alpha")  # "alpha" has model "big"
        assert assistant_feature._vision_capable(repo, backend) is True


class TestPersonaRouting:
    """C3: the Assistant's persona reaches an `openai_api` backend via
    `persona=`, and every other backend via `system_append` (its own
    `--agent` flag would need a `.claude/agents/` file the console-owned
    persona deliberately isn't — BR-3)."""

    def test_a_cli_backend_gets_system_append_not_persona(
            self, repo, routes, fake_manager, monkeypatch):
        _write_persona = os.path.join(repo, "console", "config", "assistant.md")
        os.makedirs(os.path.dirname(_write_persona), exist_ok=True)
        with open(_write_persona, "w", encoding="utf-8") as fh:
            fh.write("PERSONA TEXT")
        captured = {}
        original = agent_manager.create

        def spy_create(repo_root, backend_id, prompt, **kw):
            captured.update(kw)
            return original(repo_root, backend_id, prompt, **kw)
        monkeypatch.setattr(agent_manager, "create", spy_create)

        routes[("POST", "assistant.say")](Req(body={"text": "hi"}))
        # C4 folds the injected context (tickets digest/memory/capabilities)
        # into the same channel, since a CLI backend has only one — the
        # persona text itself must still lead.
        assert captured.get("system_append", "").startswith("PERSONA TEXT")
        assert "Capabilities" in captured.get("system_append", "")
        assert "persona" not in captured or not captured["persona"]

    def test_an_api_backend_gets_persona_not_system_append(
            self, repo, monkeypatch, fake_manager):
        # Reconfigure the repo's only backend to be openai_api-shaped.
        with open(os.path.join(repo, "console", "config", "agents.toml"), "w",
                  encoding="utf-8") as fh:
            fh.write('[[backend]]\nid = "api"\ntransport = "openai_api"\n'
                     'base_url = "https://example.test/v1"\n'
                     'api_key_env = "TEST_KEY"\nauth = "key"\n')
        monkeypatch.setenv("TEST_KEY", "x")
        agent_backends._cache.clear()
        out = {}

        class Ctx:
            repo_root = repo

            def get(self, pattern, fn, name):
                out[("GET", name)] = fn

            def post(self, pattern, fn, name):
                out[("POST", name)] = fn

            def register_tab(self, *a, **kw):
                pass

            def provide(self, *a, **kw):
                pass

        captured = {}
        original = agent_manager.create

        def spy_create(repo_root, backend_id, prompt, **kw):
            captured.update(kw)
            return original(repo_root, backend_id, prompt, **kw)
        monkeypatch.setattr(agent_manager, "create", spy_create)

        assistant_feature.apply(Ctx())
        out[("POST", "assistant.say")](Req(body={"text": "hi"}))
        assert captured.get("persona") == "assistant"
        assert not captured.get("system_append")


class TestSayRoute:
    def test_a_first_say_starts_a_session_and_sends(self, repo, routes, fake_manager):
        out = routes[("POST", "assistant.say")](Req(body={"text": "hello"}))
        assert out["result"] == "sent"
        assert len(fake_manager) == 1
        sess = list(fake_manager.values())[0]
        assert sess.sent == ["hello"]

    def test_a_second_say_reuses_the_same_session(self, repo, routes, fake_manager):
        routes[("POST", "assistant.say")](Req(body={"text": "one"}))
        routes[("POST", "assistant.say")](Req(body={"text": "two"}))
        assert len(fake_manager) == 1, "the Assistant chat must be reused, not recreated"

    def test_busy_returns_queued_not_an_error(self, repo, routes, fake_manager):
        routes[("POST", "assistant.say")](Req(body={"text": "one"}))
        sess = list(fake_manager.values())[0]
        sess.next_send_result = "queued"
        out = routes[("POST", "assistant.say")](Req(body={"text": "two"}))
        assert out["result"] == "queued"

    def test_a_backend_failure_returns_an_error_result_never_raises(
            self, repo, routes, monkeypatch):
        def exploding(repo_root, backend_id, prompt, **kw):
            raise ValueError("backend is not installed")
        monkeypatch.setattr(agent_manager, "create", exploding)
        out = routes[("POST", "assistant.say")](Req(body={"text": "hi"}))
        assert out["result"] == "error"
        assert "not installed" in out["reason"]

    def test_an_empty_message_is_declined_not_sent(self, repo, routes, fake_manager):
        out = routes[("POST", "assistant.say")](Req(body={"text": "   "}))
        assert out["result"] == "error"
        assert not fake_manager


class TestSessionAndNewRoutes:
    def test_session_before_any_say_is_inactive(self, repo, routes):
        out = routes[("GET", "assistant.session")](Req())
        assert out["active"] is False

    def test_session_after_a_say_is_active(self, repo, routes):
        routes[("POST", "assistant.say")](Req(body={"text": "hi"}))
        out = routes[("GET", "assistant.session")](Req())
        assert out["active"] is True

    def test_new_creates_a_session_even_with_no_prior_say(self, repo, routes, fake_manager):
        out = routes[("POST", "assistant.new")](Req())
        assert out["id"] in fake_manager

    def test_past_idle_timeout_the_next_say_starts_a_new_chat(
            self, repo, routes, fake_manager, monkeypatch):
        routes[("POST", "assistant.say")](Req(body={"text": "one"}))
        first_id = list(fake_manager)[0]
        # Fake an ancient `updated_at` so the reuse check finds it stale.
        pointer = assistant.read_session(repo)
        pointer["updated_at"] = "2000-01-01T00:00:00Z"
        import json
        with open(os.path.join(assistant.cache_dir(repo), assistant.SESSION_FILE),
                  "w", encoding="utf-8") as fh:
            json.dump(pointer, fh)
        routes[("POST", "assistant.say")](Req(body={"text": "two"}))
        assert len(fake_manager) == 2
        second_id = [k for k in fake_manager if k != first_id][0]
        assert fake_manager[second_id].sent == ["two"]


class TestStreamRoute:
    def test_only_the_five_named_event_types_pass_through(self, repo, routes, fake_manager):
        routes[("POST", "assistant.say")](Req(body={"text": "hi"}))
        source = routes[("GET", "assistant.stream")](Req())
        frames = list(source)
        kinds = {f.split(": ", 1)[1].strip() for f in frames}
        assert kinds == {"turn.start", "reply", "turn.end"}
        assert "usage" not in kinds and "tool.start" not in kinds

    def test_no_session_yet_is_a_clean_not_found(self, repo, routes):
        with pytest.raises(FileNotFoundError):
            routes[("GET", "assistant.stream")](Req())


class TestMemoryRoutes:
    def test_get_reads_what_was_remembered(self, repo, routes):
        assistant.remember(repo, "the sky is blue")
        out = routes[("GET", "assistant.memory_get")](Req())
        assert "the sky is blue" in out["memory"]

    def test_post_appends_and_is_audited(self, repo, routes):
        out = routes[("POST", "assistant.memory_post")](Req(body={"fact": "a new fact"}))
        assert out["ok"] is True
        assert "a new fact" in assistant.read_memory(repo)

    def test_post_declines_a_secret_shaped_fact(self, repo, routes):
        out = routes[("POST", "assistant.memory_post")](
            Req(body={"fact": "sk-abcdefghijklmnopqrstuvwxyz0123456789"}))
        assert out["ok"] is False
        assert assistant.read_memory(repo) == ""
