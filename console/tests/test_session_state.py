"""T-020 FR-4: what a session remembers so the Run layer never reads the ring.

`last_output_at`, `started_utc`, `last_turn` and `turn_count` are plain
attributes updated as lines arrive, because the 4000-event ring can overflow
within one watchdog tick on a long turn (decision a3). Nothing here spawns a
process: lines are fed straight through `_handle_line`, the way the reader
thread does.
"""

import json
import threading
import time

from server import agent_approvals, agent_session
from server.agent_events import RING_MAX, Stream

CLOCK = "2026-10-01T12:00:00Z"


class _FakeBackend:
    """The minimum `Backend` surface the session classes touch."""

    id = "alpha"
    label = "Alpha"
    transport = "stream_json"
    default_mode = "default"
    resumable = True
    command = "alpha-cli"

    def session_argv(self, **kw):
        return ["alpha-cli", "-p"]

    def turn_argv(self, prompt, **kw):
        return ["alpha-cli", "-p", prompt]


def _live(tmp_path):
    return agent_session.LiveSession("s1", _FakeBackend(), str(tmp_path), Stream("s1"))


def _turn(tmp_path):
    return agent_session.TurnSession("s1", _FakeBackend(), str(tmp_path), Stream("s1"))


def _result(**kw):
    return json.dumps(dict({"type": "result", "subtype": "success", "is_error": False,
                            "result": "ok", "num_turns": 1}, **kw))


def _tool(name, tid="t1"):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": name, "input": {}}]}})


def _rate(status, resets=1790000000):
    return json.dumps({"type": "rate_limit_event", "rate_limit_info": {
        "status": status, "resetsAt": resets, "rateLimitType": "five_hour"}})


def _delta(text="x"):
    return json.dumps({"type": "stream_event", "event": {
        "type": "content_block_delta", "delta": {"type": "text_delta", "text": text}}})


class TestOutputTimestamp:
    def test_injected_clock_sets_last_output_at_and_snapshot(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_session, "_utc_now", lambda: CLOCK)
        sess = _live(tmp_path)
        sess._handle_line(_delta())
        assert sess.last_output_at == CLOCK
        assert sess.snapshot()["last_output_at"] == CLOCK

    def test_no_output_is_empty_string_not_now(self, tmp_path):
        sess = _live(tmp_path)
        assert sess.last_output_at == ""
        assert sess.snapshot()["last_output_at"] == ""
        assert sess.snapshot()["started_utc"] == ""

    def test_non_json_line_counts_as_output(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_session, "_utc_now", lambda: CLOCK)
        sess = _live(tmp_path)
        sess._handle_line("plain text from a backend that is not json")
        assert sess.last_output_at == CLOCK

    def test_monotonic_counterpart_is_stamped_too(self, tmp_path):
        sess = _live(tmp_path)
        assert sess._last_output_mono == 0.0
        before = time.monotonic()
        sess._handle_line(_delta())
        assert before <= sess._last_output_mono <= time.monotonic()

    def test_ten_thousand_lines_under_two_seconds(self, tmp_path):
        sess = _live(tmp_path)
        line = _delta()
        start = time.monotonic()
        for _ in range(10000):
            sess._handle_line(line)
        assert time.monotonic() - start < 2.0
        assert sess.last_output_at != ""


class _NoThread:
    def __init__(self, *a, **kw):
        pass

    def start(self):
        pass


class _StubThreading:
    """Only `Thread` is replaced, so no reader thread runs against a fake pipe."""

    Thread = _NoThread

    def __getattr__(self, name):
        return getattr(threading, name)


class _FakeProc:
    pid = 4242
    stdin = None

    def poll(self):
        return None


class TestStartedUtc:
    def test_turn_session_start_stamps_utc(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_session, "_utc_now", lambda: CLOCK)
        sess = _turn(tmp_path)
        sess.start()
        assert sess.started_utc == CLOCK
        assert sess.snapshot()["started_utc"] == CLOCK

    def test_live_session_start_stamps_utc(self, tmp_path, monkeypatch):
        monkeypatch.setattr(agent_session, "_utc_now", lambda: CLOCK)
        monkeypatch.setattr(agent_session.subprocess, "Popen", lambda *a, **kw: _FakeProc())
        monkeypatch.setattr(agent_session, "threading", _StubThreading())
        sess = _live(tmp_path)
        sess.start()
        assert sess.started_utc == CLOCK


class TestLastTurn:
    def test_none_until_a_turn_ends(self, tmp_path):
        sess = _live(tmp_path)
        assert sess.last_turn is None and sess.turn_count == 0
        assert sess.snapshot()["last_turn"] is None
        assert sess.snapshot()["turn_count"] == 0

    def test_survives_ring_overflow_by_ring_max_plus_one(self, tmp_path):
        sess = _live(tmp_path)
        sess._handle_line(_result(subtype="error_max_turns", is_error=True))
        for _ in range(RING_MAX + 1):
            sess._handle_line(_delta())
        # The ring really did lose it: a reader from seq 0 gets a gap.
        _events, gap = sess.stream.since(0)
        assert gap is True
        assert sess.last_turn["turn_end"]["type"] == "turn.end"
        assert sess.last_turn["turn_end"]["subtype"] == "error_max_turns"
        assert sess.last_turn["turn_end"]["is_error"] is True

    def test_carries_last_rate_limit_notice_of_that_turn(self, tmp_path):
        sess = _live(tmp_path)
        sess._handle_line(_rate("allowed_warning"))
        sess._handle_line(_rate("rejected", resets=1790001234))
        sess._handle_line(_result(is_error=True))
        notice = sess.last_turn["rate_limit"]
        assert notice["kind"] == "rate_limit"
        assert notice["status"] == "rejected"
        assert notice["resets_at"] == 1790001234
        assert sess.snapshot()["last_turn"]["rate_limit"] == "rejected"
        # The next turn starts clean: a notice from the old turn must not leak.
        sess._handle_line(_result())
        assert sess.last_turn["rate_limit"] is None
        assert sess.snapshot()["last_turn"]["rate_limit"] == ""

    def test_counts_tool_starts_for_the_turn(self, tmp_path):
        sess = _live(tmp_path)
        sess._handle_line(_tool("Write", "a"))
        sess._handle_line(_tool("Write", "b"))
        sess._handle_line(_tool("Bash", "c"))
        sess._handle_line(_result())
        assert sess.last_turn["tools"] == {"Write": 2, "Bash": 1}
        assert sess.snapshot()["last_turn"]["tools"] == {"Write": 2, "Bash": 1}
        sess._handle_line(_result())
        assert sess.last_turn["tools"] == {}

    def test_tool_names_are_bounded(self, tmp_path):
        sess = _live(tmp_path)
        for n in range(100):
            sess._handle_line(_tool("tool-%d" % n, "id-%d" % n))
        sess._handle_line(_result())
        tools = sess.last_turn["tools"]
        assert len(tools) == agent_session.TOOL_NAMES_MAX + 1
        assert sum(tools.values()) == 100
        assert tools["(other)"] == 100 - agent_session.TOOL_NAMES_MAX

    def test_turn_count_increments(self, tmp_path):
        sess = _live(tmp_path)
        sess._handle_line(_result())
        assert sess.turn_count == 1
        sess._handle_line(_result())
        assert sess.turn_count == 2
        assert sess.snapshot()["turn_count"] == 2

    def test_a_turn_that_exits_without_a_result_still_records_one(self, tmp_path):
        """`TurnSession` publishes a synthetic `turn.end` when the CLI dies
        without a result; the Run layer must see it as the last turn."""
        sess = _turn(tmp_path)
        sess._observe({"type": "turn.end", "subtype": "process_exit",
                       "is_error": True, "exit_code": 1, "num_turns": 1})
        assert sess.last_turn["turn_end"]["subtype"] == "process_exit"
        assert sess.turn_count == 1


class TestStopRequested:
    def test_false_until_stop_is_called(self, tmp_path):
        sess = _turn(tmp_path)
        assert sess.stop_requested is False
        sess.stop()
        assert sess.stop_requested is True

    def test_api_session_stop_sets_it(self, tmp_path):
        """`ApiSession.stop` does not call the base class, so without its own
        assignment a human stop of an API chat would read as a crash."""
        from server.agent_api_session import ApiSession

        class _ApiBackend(_FakeBackend):
            transport = "openai_api"
            raw = {"base_url": "https://example.test/v1"}
            api_key_env = ""
            max_tool_rounds = 5
            max_history_messages = 10
            gated_tools = ()

        sess = ApiSession("s1", _ApiBackend(), str(tmp_path), Stream("s1"))
        assert sess.stop_requested is False
        sess.stop()
        assert sess.stop_requested is True


class TestPendingFor:
    def _park(self, reg, chat, tool="Write"):
        """Park one request on a thread; returns once it is registered."""
        registered = threading.Event()
        out = {}

        def publish(event):
            if event["type"] == "approval.request":
                out["key"] = event["key"]
                registered.set()

        def run():
            out["answer"] = reg.request(chat, tool, {"file_path": "x"}, "use-1",
                                        publish, timeout=10)

        t = threading.Thread(target=run, daemon=True)
        t.start()
        assert registered.wait(2.0)
        return t, out

    def test_lists_while_parked_empty_after_decide_or_forget(self):
        reg = agent_approvals.Approvals()
        assert reg.pending_for("chat-1") == []

        t1, parked = self._park(reg, "chat-1", "Write")
        got = reg.pending_for("chat-1")
        assert [(p["key"], p["tool"]) for p in got] == [(parked["key"], "Write")]
        assert reg.pending_for("chat-2") == []

        reg.decide(parked["key"], "allow")
        assert reg.pending_for("chat-1") == []
        t1.join(2.0)
        assert parked["answer"][0] == "allow"

        t2, parked2 = self._park(reg, "chat-1", "Bash")
        assert len(reg.pending_for("chat-1")) == 1
        reg.forget("chat-1")
        assert reg.pending_for("chat-1") == []
        t2.join(2.0)
        assert parked2["answer"][0] == "deny"
