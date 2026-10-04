"""Characterise the Normalizer before any grader depends on it.

These tests run against the unmodified normalizer. The suspect-behaviour
tests pin quirks the view has to survive; if one fails, the normalizer was
fixed and the matching guard in the view can go.
"""

from server.agent_normalize import Normalizer

from evals_support import (
    assistant_text,
    assistant_tool,
    result,
    stream_text_partial,
    stream_tool,
)


def _feed(events):
    norm = Normalizer()
    out = []
    for raw in events:
        out.extend(norm.feed(raw))
    return out


class TestNormalizerCharacterisation:
    def test_assistant_tool_use_yields_tool_start_with_id_name_args(self):
        events = _feed([assistant_tool("Bash", {"command": "git status"}, "t1")])
        starts = [e for e in events if e["type"] == "tool.start"]
        assert len(starts) == 1
        assert starts[0]["id"] == "t1"
        assert starts[0]["name"] == "Bash"
        assert starts[0]["args"]["command"] == "git status"

    def test_assistant_text_yields_text_done_with_text(self):
        events = _feed([assistant_text("hello")])
        done = [e for e in events if e["type"] == "text.done"]
        assert done and done[-1]["text"] == "hello"

    def test_exitplanmode_yields_tool_start_and_plan_event(self):
        events = _feed([assistant_tool("ExitPlanMode", {"plan": "ship it"}, "p1")])
        assert any(e["type"] == "tool.start" and e["name"] == "ExitPlanMode" for e in events)
        plans = [e for e in events if e["type"] == "plan"]
        assert plans and plans[0]["plan"] == "ship it"

    def test_result_yields_turn_end_with_is_error_and_subtype_keys(self):
        events = _feed([result(is_error=True, subtype="success")])
        end = [e for e in events if e["type"] == "turn.end"][-1]
        assert "is_error" in end and "subtype" in end
        assert end["is_error"] is True
        assert end["subtype"] == "success"

    def test_non_json_is_not_the_normalizers_job(self):
        # feed takes a parsed object. A string is not parsed here.
        events = Normalizer().feed("not json {")
        assert events[0]["type"] == "raw"


class TestSuspectBehaviours:
    def test_partial_then_complete_message_gives_two_tool_start_same_id(self):
        """if this fails the Normalizer was fixed; graders stay valid, delete the matching guard in the view.

        The view de-duplicates tool.start by id because a partial block and the
        complete assistant message both emit one.
        """
        events = _feed(stream_tool("Bash", {"command": "ls"}, "same")
                       + [assistant_tool("Bash", {"command": "ls"}, "same")])
        starts = [e for e in events if e["type"] == "tool.start"]
        assert len(starts) == 2
        assert starts[0]["id"] == starts[1]["id"] == "same"

    def test_partial_path_text_done_is_empty_then_full_text_follows(self):
        """if this fails the Normalizer was fixed; graders stay valid, delete the matching guard in the view.

        The view keeps only non-empty text.done events, so the empty seal from
        the partial path does not become a text block.
        """
        events = _feed(stream_text_partial() + [assistant_text("full text")])
        done = [e for e in events if e["type"] == "text.done"]
        assert done[0]["text"] == ""
        assert done[-1]["text"] == "full text"

    def test_user_message_tool_result_is_swallowed_into_a_notice(self):
        """if this fails the Normalizer was fixed; graders stay valid, delete the matching guard in the view.

        Graders never read tool.result. A user tool_result arrives as a notice.
        """
        raw = {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t", "content": "secret output"}]}}
        events = Normalizer().feed(raw)
        assert events[0]["type"] == "notice"
        assert all(e["type"] != "tool.result" for e in events)

    def test_missing_usage_collapses_to_zero_in_turn_end(self):
        """if this fails the Normalizer was fixed; graders stay valid, delete the matching guard in the view.

        Usage is read from the raw result object. turn.end reports 0 when the
        key was absent, which is not the same as a reported zero.
        """
        raw = {"type": "result", "subtype": "success", "is_error": False, "result": "ok"}
        end = [e for e in Normalizer().feed(raw) if e["type"] == "turn.end"][-1]
        assert end["input_tokens"] == 0
        assert end["output_tokens"] == 0
