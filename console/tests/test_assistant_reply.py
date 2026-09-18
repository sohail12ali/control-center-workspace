"""T-006 FR-8: the reply watcher.

The gap this closes is worth stating: until now nothing called
`assistant.write_last_reply`, so `copy that` could only ever answer "there is
no last reply to copy yet". It was honest and useless. These tests pin both
halves — the reply is recorded whether or not it could be spoken, and it is
spoken only when the user has not muted it.
"""

import threading
import time

import pytest

from server import assistant, assistant_config, assistant_reply


class TestSpokenForm:
    def test_reads_the_first_paragraph_only(self):
        text = "The build is green.\n\nHere is the full log, which nobody wants read aloud."
        assert assistant_reply.spoken_form(text, 400) == "The build is green."

    def test_strips_markdown_furniture(self):
        # A model told to be terse still emits headings and bullets. Reading
        # "hash hash" and "star" aloud is worse than reading nothing.
        text = "## Result\n- **all** tests `pass`\n- nothing to do"
        out = assistant_reply.spoken_form(text, 400)
        assert "#" not in out and "*" not in out and "`" not in out
        assert "all tests pass" in out

    def test_collapses_whitespace(self):
        assert assistant_reply.spoken_form("a   b\n  c", 400) == "a b c"

    def test_caps_at_a_sentence_boundary(self):
        body = ("This first sentence is quite long and finishes here. "
                "And this one would run past the cap entirely.")
        out = assistant_reply.spoken_form(body, 60)
        assert out.endswith("."), out
        assert len(out) <= 60

    def test_caps_hard_when_there_is_no_sentence_end(self):
        out = assistant_reply.spoken_form("x" * 500, 100)
        assert len(out) == 100

    def test_a_cap_of_zero_means_no_cap(self):
        long = "y" * 5000
        assert len(assistant_reply.spoken_form(long, 0)) == 5000

    @pytest.mark.parametrize("empty", ["", "   ", "\n\n", None])
    def test_nothing_in_nothing_out(self, empty):
        assert assistant_reply.spoken_form(empty, 400) == ""


class FakeStream:
    """Stands in for `agent_events.Stream` — `since()` and `publish()` are the
    only two things the watcher touches."""

    def __init__(self, events=()):
        self.events = [dict(e, seq=i + 1) for i, e in enumerate(events)]
        self.published = []
        self._lock = threading.Lock()

    def since(self, seq):
        with self._lock:
            return [e for e in self.events if e["seq"] > seq], False

    def publish(self, event):
        with self._lock:
            self.published.append(event)
        return event

    def add(self, event):
        with self._lock:
            self.events.append(dict(event, seq=len(self.events) + 1))


class FakeSession:
    def __init__(self, stream, alive=True, sid="chat-1"):
        self.stream = stream
        self.alive = alive
        self.id = sid


@pytest.fixture
def spoken(monkeypatch):
    """Capture what would have been spoken, instead of speaking it."""
    said = []

    def fake_speak(repo_root, text, opener=None):
        said.append(text)
        return {"ok": True, "chars": len(text)}

    monkeypatch.setattr(assistant_reply.native_bridge, "speak", fake_speak)
    return said


def _drive(repo_root, session, event):
    """Run one event through the watcher's handler, without the poll loop."""
    assistant_reply._handle(repo_root, session, event)


class TestRecording:
    def test_a_finished_reply_becomes_the_last_reply(self, repo, spoken):
        # This is the bit `copy that` depends on.
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "The build is green."})
        assert assistant.read_last_reply(repo) == "The build is green."

    def test_it_is_recorded_even_when_speech_fails(self, repo, monkeypatch):
        """No shell, no synthesiser, muted — none of those should stop a reply
        being copyable."""
        monkeypatch.setattr(assistant_reply.native_bridge, "speak",
                            lambda *a, **k: {"ok": False, "reason": "shell not running"})
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "still copyable"})
        assert assistant.read_last_reply(repo) == "still copyable"

    def test_a_failed_speak_is_reported_as_a_notice_not_an_error(self, repo, monkeypatch):
        monkeypatch.setattr(assistant_reply.native_bridge, "speak",
                            lambda *a, **k: {"ok": False, "reason": "shell not running"})
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "hello"})
        kinds = [e["type"] for e in stream.published]
        assert "notice" in kinds
        assert "shell not running" in stream.published[-1]["text"]

    def test_a_reply_event_carries_the_spoken_form(self, repo, spoken):
        stream = FakeStream()
        _drive(repo, FakeSession(stream),
               {"type": "text.done", "text": "## Done\nAll **green**.\n\nlong tail here"})
        reply = [e for e in stream.published if e["type"] == "reply"][0]
        assert reply["text"] == "Done All green."
        assert reply["full_chars"] > len(reply["text"])

    def test_an_empty_reply_records_nothing(self, repo, spoken):
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "   "})
        assert assistant.read_last_reply(repo) == ""
        assert stream.published == []

    def test_only_finished_text_counts(self, repo, spoken):
        # Speaking deltas would stutter a word at a time.
        stream = FakeStream()
        for kind in ("text.delta", "text.start", "turn.start", "thinking.done"):
            _drive(repo, FakeSession(stream), {"type": kind, "text": "fragment"})
        assert assistant.read_last_reply(repo) == ""
        assert spoken == []


class TestMuting:
    def test_muted_records_but_does_not_speak(self, repo, spoken):
        assistant_config.update(repo, {"speak": False})
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "quietly noted"})
        assert assistant.read_last_reply(repo) == "quietly noted"
        assert spoken == [], "muted must mean silent"

    def test_unmuted_speaks_the_trimmed_form(self, repo, spoken):
        assistant_config.update(repo, {"speak": True, "reply_chars": 400})
        stream = FakeStream()
        _drive(repo, FakeSession(stream),
               {"type": "text.done", "text": "Short answer.\n\nLong appendix."})
        assert spoken == ["Short answer."]

    def test_the_reply_chars_setting_is_honoured(self, repo, spoken):
        assistant_config.update(repo, {"speak": True, "reply_chars": 20})
        stream = FakeStream()
        _drive(repo, FakeSession(stream), {"type": "text.done", "text": "z" * 200})
        assert len(spoken[0]) == 20


class TestOneWatcherPerChat:
    def test_a_second_watch_on_the_same_chat_is_refused(self, repo, monkeypatch):
        """Two watchers would speak every reply twice."""
        stream = FakeStream()
        session = FakeSession(stream, sid="chat-dup")
        monkeypatch.setattr(assistant_reply.agent_manager, "get", lambda sid: session)
        try:
            assert assistant_reply.watch(repo, "chat-dup") is True
            assert assistant_reply.watch(repo, "chat-dup") is False
            assert assistant_reply.watching("chat-dup")
        finally:
            session.alive = False
            time.sleep(assistant_reply.IDLE_EXIT_SECONDS + 1.0)

    def test_a_watcher_on_a_dead_chat_exits(self, repo, monkeypatch):
        monkeypatch.setattr(assistant_reply.agent_manager, "get", lambda sid: None)
        assert assistant_reply.watch(repo, "chat-gone") is True
        for _ in range(40):
            if not assistant_reply.watching("chat-gone"):
                break
            time.sleep(0.1)
        assert not assistant_reply.watching("chat-gone"), (
            "a watcher must not outlive the chat it watches")

    def test_a_handler_that_raises_does_not_kill_the_watcher(self, repo, monkeypatch):
        """A watcher that dies takes speech AND `copy that` with it for the
        rest of the session, which is worse than skipping one event."""
        stream = FakeStream([{"type": "text.done", "text": "one"}])
        session = FakeSession(stream, sid="chat-raise")
        monkeypatch.setattr(assistant_reply.agent_manager, "get", lambda sid: session)
        boom = {"n": 0}

        def sometimes_raises(repo_root, text):
            boom["n"] += 1
            raise RuntimeError("disk full")

        monkeypatch.setattr(assistant_reply.assistant, "write_last_reply", sometimes_raises)
        try:
            assistant_reply.watch(repo, "chat-raise")
            time.sleep(1.0)
            stream.add({"type": "text.done", "text": "two"})
            time.sleep(1.0)
            assert boom["n"] >= 2, "it kept going after the first failure"
        finally:
            session.alive = False
            time.sleep(assistant_reply.IDLE_EXIT_SECONDS + 1.0)
