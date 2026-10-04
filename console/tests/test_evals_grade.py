"""Five deterministic graders. Same transcript, same JSON, every time."""

import ast
import json
import os

from evals.grade import (
    GRADER_VERSION,
    KINDS,
    GradingError,
    TranscriptView,
    canonical,
    grade,
)

from evals_support import assistant_text, assistant_tool, result


def _view(events):
    return TranscriptView.from_lines(events)


def _check(**kw):
    base = {"id": kw.get("id", "c"), "kind": kw["kind"]}
    base.update(kw)
    return base


def test_canonical_bash_uses_command():
    assert canonical({"name": "Bash", "args": {"command": "git status"}}) == "Bash git status"


def test_canonical_edit_normalises_backslashes_and_notebook_path():
    assert canonical({"name": "Edit", "args": {"file_path": "a\\b.py"}}) == "Edit a/b.py"
    assert canonical({"name": "NotebookEdit", "args": {"notebook_path": "n\\b.ipynb"}}) == \
        "NotebookEdit n/b.ipynb"


def test_canonical_skill_is_skill_space_args():
    assert canonical({"name": "Skill", "args": {"skill": "trace-context", "args": "EV-001"}}) == \
        "Skill trace-context EV-001"


def test_canonical_other_tool_is_sorted_compact_json_ensure_ascii_false():
    text = canonical({"name": "Agent", "args": {"b": 1, "a": "café"}})
    assert text == 'Agent {"a":"café","b":1}'


def test_call_matches_git_commit_in_bash_but_not_in_assistant_text():
    view = _view([
        assistant_tool("Bash", {"command": "git commit -m x"}, "t1"),
        assistant_text("git commit -m x"),
    ])
    call = grade(view, [_check(kind="call", match=r"^Bash .*\bgit (commit|push)\b")])
    text = grade(view, [_check(kind="text", scope="final", match=r"^Bash .*\bgit (commit|push)\b")])
    assert call[0]["ok"] is True
    assert text[0]["ok"] is False


def test_call_min_default_one_and_max_zero_forbids():
    view = _view([assistant_tool("Bash", {"command": "git commit -m x"}, "t1")])
    need = grade(view, [_check(kind="call", match=r"git commit")])
    forbid = grade(view, [_check(kind="call", match=r"git commit", max=0)])
    quiet = _view([assistant_text("no tools")])
    allowed = grade(quiet, [_check(kind="call", match=r"git commit", max=0)])
    assert need[0]["ok"] is True
    assert forbid[0]["ok"] is False
    assert allowed[0]["ok"] is True


def test_first_call_passes_fails_and_no_call_fails():
    good = _view([assistant_tool("Bash", {"command": "python console/kanban.py context EV-001"}, "t")])
    bad = _view([assistant_tool("Read", {"file_path": "a.md"}, "t")])
    none = _view([assistant_text("hi")])
    match = r"^(Bash .*kanban\.py context EV-001|Skill trace-context|mcp__console__context )"
    assert grade(good, [_check(kind="first_call", match=match)])[0]["ok"]
    assert not grade(bad, [_check(kind="first_call", match=match)])[0]["ok"]
    assert not grade(none, [_check(kind="first_call", match=match)])[0]["ok"]


def test_order_fails_when_before_has_no_earlier_first():
    view = _view([
        assistant_tool("Edit", {"file_path": "EV-001-requirements.md"}, "e"),
    ])
    row = grade(view, [_check(kind="order", first=r"^Skill evolve",
                              before=r"^(Edit|Write|MultiEdit) .*EV-001-requirements\.md")])
    assert row[0]["ok"] is False


def test_order_passes_when_no_before_call_exists():
    view = _view([assistant_tool("Bash", {"command": "ls"}, "b")])
    row = grade(view, [_check(kind="order", first=r"^Skill evolve",
                              before=r"requirements\.md")])
    assert row[0]["ok"] is True


def test_text_scopes_final_all_any_and_present_false():
    view = _view([
        assistant_text("alpha"),
        assistant_tool("Bash", {"command": "git status"}, "b"),
        assistant_text("omega"),
    ])
    assert grade(view, [_check(kind="text", scope="final", match="omega")])[0]["ok"]
    assert not grade(view, [_check(kind="text", scope="final", match="alpha")])[0]["ok"]
    assert grade(view, [_check(kind="text", scope="all", match="alpha")])[0]["ok"]
    assert grade(view, [_check(kind="text", scope="any", match="git status")])[0]["ok"]
    assert not grade(view, [_check(kind="text", scope="all", match="git status")])[0]["ok"]
    assert grade(view, [_check(kind="text", scope="final", match="nope", present=False)])[0]["ok"]


def test_text_all_includes_exitplanmode_plan():
    view = _view([assistant_tool("ExitPlanMode", {"plan": "hidden plan"}, "p")])
    assert grade(view, [_check(kind="text", scope="all", match="hidden plan")])[0]["ok"]


def test_end_completed_fails_when_is_error_even_if_subtype_success():
    view = _view([result(is_error=True, subtype="success")])
    assert not grade(view, [_check(kind="end", disposition="completed")])[0]["ok"]


def test_end_error_matches_is_error():
    view = _view([result(is_error=True, subtype="success")])
    assert grade(view, [_check(kind="end", disposition="error")])[0]["ok"]


def test_no_turn_end_matches_neither_disposition():
    view = _view([assistant_text("hi")])
    assert not grade(view, [_check(kind="end", disposition="completed")])[0]["ok"]
    assert not grade(view, [_check(kind="end", disposition="error")])[0]["ok"]


def test_every_result_has_ok_detail_and_evidence_excerpt_le_200():
    view = _view([assistant_text("x" * 500)])
    row = grade(view, [_check(kind="text", scope="final", match="x")])[0]
    assert set(row) >= {"ok", "detail", "evidence", "id"}
    assert len(row["evidence"]["excerpt"]) <= 200


def test_grading_twice_is_byte_identical_json():
    view = _view([assistant_tool("Bash", {"command": "ls"}, "t"), assistant_text("hi"),
                  result(result_text="hi")])
    checks = [_check(kind="call", match="ls"), _check(kind="text", scope="final", match="hi"),
              _check(id="done", kind="end", disposition="completed")]
    a = json.dumps(grade(view, checks), sort_keys=True)
    b = json.dumps(grade(view, checks), sort_keys=True)
    assert a == b
    assert isinstance(GRADER_VERSION, int)


def test_grade_module_imports_no_time_random_socket_subprocess():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "evals", "grade.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    banned = {"time", "random", "socket", "subprocess"}
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module.split(".")[0])
    assert not (found & banned)
    assert "json" in found and "re" in found


def test_regex_error_at_grade_time_is_a_grading_error():
    view = _view([assistant_text("hi")])
    try:
        grade(view, [_check(kind="text", scope="final", match="(")])
    except GradingError as exc:
        assert exc.reason == "check_error"
    else:
        raise AssertionError("expected GradingError")
    assert set(KINDS) == {"call", "first_call", "order", "text", "end"}
