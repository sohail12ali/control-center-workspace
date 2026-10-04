"""Failure classes and precedence. One crafted input per class."""

from evals.grade import (
    Problem,
    TranscriptView,
    classify,
    primary,
)

from evals_support import assistant_text, assistant_tool, result


def _view(events):
    return TranscriptView.from_lines(events)


def _end(**kw):
    return _view([result(**kw)])


def test_auth_failure_shape_maps_to_infra_auth():
    view = _end(is_error=True, subtype="success", result_text="Failed to authenticate",
                usage={"input_tokens": 0, "output_tokens": 0}, total_cost_usd=0)
    view.raw_result["terminal_reason"] = "api_error"
    top = primary(classify(view, []))
    assert top.cls == "infra" and top.reason == "auth"


def test_no_result_is_infra_no_result():
    top = primary(classify(TranscriptView(), []))
    assert top.cls == "infra" and top.reason == "no_result"


def test_error_max_budget_is_infra_budget_cap():
    view = _end(is_error=True, subtype="error_max_budget_usd", result_text="budget")
    top = primary(classify(view, []))
    assert top.cls == "infra" and top.reason == "budget_cap"


def test_empty_turn_is_infra_empty_turn():
    view = _end(is_error=False, subtype="success", result_text="")
    top = primary(classify(view, []))
    assert top.cls == "infra" and top.reason == "empty_turn"


def test_other_is_error_is_infra_cli_error():
    view = _end(is_error=True, subtype="error", result_text="something else broke")
    top = primary(classify(view, []))
    assert top.cls == "infra" and top.reason == "cli_error"


def test_usable_completed_turn_failing_checks_is_model_behaviour():
    view = _view([assistant_text("hello"), result(result_text="hello")])
    results = [{"id": "needs-bye", "ok": False}]
    top = primary(classify(view, results))
    assert top.cls == "model" and top.reason == "behaviour"


def test_error_max_turns_is_model_max_turns():
    view = _end(is_error=True, subtype="error_max_turns", result_text="turns")
    top = primary(classify(view, []))
    assert top.cls == "model" and top.reason == "max_turns"


def test_tool_calls_above_cap_is_model_tool_cap():
    view = _view([
        assistant_tool("Bash", {"command": "a"}, "a"),
        assistant_tool("Bash", {"command": "b"}, "b"),
        assistant_text("did both"),
        result(result_text="did both"),
    ])
    top = primary(classify(view, [], {"max_tool_calls": 1}))
    assert top.cls == "model" and top.reason == "tool_cap"


def test_golden_failed_and_must_fail_passed_are_grading():
    view = _view([assistant_text("hello"), result(result_text="hello")])
    failed = [{"id": "said", "ok": False}]
    golden = primary(classify(view, failed, {"fixture": "pass"}))
    assert golden.cls == "grading" and golden.reason == "golden_failed"
    passed = [{"id": "said", "ok": True}]
    must = primary(classify(view, passed, {"fixture": "fail", "fail_checks": ["said"]}))
    assert must.cls == "grading" and must.reason == "must_fail_passed"


def test_precedence_grading_over_infra_over_product_over_model():
    view = _end(is_error=True, subtype="success", result_text="Failed to authenticate")
    view.raw_result["terminal_reason"] = "api_error"
    results = [{"id": "c", "ok": False}]
    problems = classify(view, results, problems=[
        Problem("grading", "bad_fixture", "torn"),
        Problem("product", "rule_moved", "quote"),
        Problem("model", "behaviour", "checks"),
    ])
    assert primary(problems).cls == "grading"
    rest = [p for p in problems if p.cls != "grading"]
    assert primary(rest).cls == "infra"
    rest = [p for p in rest if p.cls != "infra"]
    assert primary(rest).cls == "product"
    rest = [p for p in rest if p.cls != "product"]
    assert rest == [] or primary(rest).cls == "model"
