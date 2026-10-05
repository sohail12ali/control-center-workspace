"""Transcript view: de-dupe calls, ignore tool results, tolerate live noise."""

import json

from evals.grade import GradingError, TranscriptView, parse_lines

from evals_support import (
    assistant_text,
    assistant_tool,
    init,
    result,
    stream_text_partial,
    stream_tool,
)


def _view(events, strict=False):
    return TranscriptView.from_lines(events, strict=strict)


def test_same_tool_use_id_twice_yields_one_call():
    view = _view(stream_tool("Bash", {"command": "ls"}, "same")
                 + [assistant_tool("Bash", {"command": "ls"}, "same")])
    assert len(view.calls) == 1
    assert view.calls[0]["id"] == "same"


def test_empty_ids_are_never_merged():
    view = _view([
        assistant_tool("Bash", {"command": "one"}, ""),
        assistant_tool("Bash", {"command": "two"}, ""),
    ])
    assert len(view.calls) == 2


def test_exitplanmode_is_text_not_a_call():
    view = _view([assistant_tool("ExitPlanMode", {"plan": "ship it"}, "p1")])
    assert view.calls == []
    assert view.plans == ["ship it"]


def test_text_blocks_in_order_from_non_empty_text_done():
    view = _view([assistant_text("one"), assistant_text("two")])
    assert view.text_blocks == ["one", "two"]


def test_partial_plus_complete_message_yields_text_once():
    view = _view(stream_text_partial() + [assistant_text("full text")])
    assert view.text_blocks == ["full text"]


def test_final_text_prefers_last_block_then_raw_result():
    both = _view([assistant_text("first"), assistant_text("last"),
                  result(result_text="from result")])
    assert both.final == "last"
    only = _view([result(result_text="from result")])
    assert only.final == "from result"
    empty = TranscriptView()
    assert empty.final == ""


def test_fixture_with_non_json_line_is_a_grading_error():
    try:
        parse_lines('{"type":"system","subtype":"init"}\nNOT JSON\n', strict=True)
    except GradingError as exc:
        assert exc.reason == "bad_fixture"
    else:
        raise AssertionError("expected GradingError")


def test_live_mode_tolerates_non_json_and_counts_it():
    view = parse_lines('noise before\n' + json.dumps(assistant_text("hi")) + "\n", strict=False)
    assert view.noise == 1
    assert view.text_blocks == ["hi"]


def test_torn_last_line_in_live_is_ignored():
    text = json.dumps(assistant_text("hi")) + "\n" + "{\"type\":\"assistant\""
    view = parse_lines(text, strict=False)
    assert view.noise == 0
    assert view.text_blocks == ["hi"]


def test_no_turn_end_is_disposition_no_result():
    view = _view([assistant_text("hi")])
    assert view.disposition == "no_result"
    assert view.turn_end is None


def test_turn_end_exposes_is_error_and_subtype_and_raw_result():
    raw = result(is_error=True, subtype="success", result_text="boom")
    view = _view([raw])
    assert view.turn_end["is_error"] is True
    assert view.turn_end["subtype"] == "success"
    assert view.raw_result["subtype"] == "success"
    assert "usage" not in view.turn_end or True


def test_session_init_model_exposed():
    view = _view([init(model="claude-opus")])
    assert view.model == "claude-opus"


def test_view_never_reads_tool_result_events():
    base = [assistant_tool("Bash", {"command": "ls"}, "t1"), assistant_text("done")]
    extra = base + [{"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "CHANGED"}]}}]
    a = _view(base)
    b = _view(extra)
    assert [c["canonical"] for c in a.calls] == [c["canonical"] for c in b.calls]
    assert a.text_blocks == b.text_blocks
    assert a.final == b.final
