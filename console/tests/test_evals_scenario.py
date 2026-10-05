"""Scenario loader, vacuity, and provenance. Tmp repos only — no real prompts."""

import os

import pytest

from evals.grade import TranscriptView, grade
from evals.scenario import assert_not_vacuous, load_dir, load_file, preflight

from evals_support import SAMPLE, plant_sample, result, write_fixture, write_scenario


def _root(tmp_path):
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "console", "evals", "scenarios"))
    os.makedirs(os.path.join(root, "console", "evals", "fixtures"))
    return root


def _put(root, name, body, fixtures=True):
    scenarios = os.path.join(root, "console", "evals", "scenarios")
    fixtures_dir = os.path.join(root, "console", "evals", "fixtures")
    write_scenario(scenarios, name, body)
    if fixtures:
        write_fixture(fixtures_dir, name, "pass", [result()])
        write_fixture(fixtures_dir, name, "fail", [result()])
    return os.path.join(scenarios, name + ".toml")


def test_loads_a_valid_scenario_with_source_and_checks(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    loaded = load_dir(os.path.join(root, "console", "evals", "scenarios"))
    assert len(loaded) == 1
    assert loaded[0].id == "sample"
    assert loaded[0].sources[0]["file"] == "CLAUDE.md"
    assert loaded[0].checks[0]["kind"] == "text"
    assert loaded[0].mode == "plan"


def test_value_starting_with_a_quote_char_is_rejected_naming_file_and_key(tmp_path):
    root = _root(tmp_path)
    commented = SAMPLE.replace(
        'quote = "every agent turn starts with `trace-context`"',
        "quote = \"hello\" # comment")
    path = _put(root, "sample", commented)
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "sample.toml" in str(ei.value) and "quote" in str(ei.value)
    single = SAMPLE.replace(
        'quote = "every agent turn starts with `trace-context`"',
        "quote = 'hello'")
    path = _put(root, "sample", single)
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "sample.toml" in str(ei.value) and "quote" in str(ei.value)


def test_unknown_scenario_key_fails_as_grading(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE + "\nextra = true\n")
    # extra at the end lands in the last table (check), which is also unknown.
    body = SAMPLE.replace("mode = \"plan\"", "mode = \"plan\"\nextra = true")
    path = _put(root, "sample", body)
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert ei.value.reason == "bad_scenario"
    assert "extra" in str(ei.value)


def test_unknown_check_kind_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('kind = "text"', 'kind = "vibe"'))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "kind" in str(ei.value)


def test_duplicate_check_id_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('id = "done"', 'id = "said-hello"', 1))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "check.id" in str(ei.value)


def test_missing_fixture_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE, fixtures=False)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "pass", [result()])
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "fail" in str(ei.value)


def test_invalid_regex_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('match = "hello"', 'match = "("'))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "regex" in str(ei.value).lower()


def test_mode_other_than_plan_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('mode = "plan"', 'mode = "default"'))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "mode" in str(ei.value)


def test_id_must_match_filename_and_pattern(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('id = "sample"', 'id = "other"'))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "id" in str(ei.value)
    bad = SAMPLE.replace('id = "sample"', 'id = "Bad_Id"')
    path = _put(root, "Bad_Id", bad, fixtures=False)
    # filename would match Bad_Id but the pattern forbids it; fixtures missing too.
    # Write fixtures under the illegal id so the id check is what we hit first.
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "Bad_Id", "pass", [result()])
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "Bad_Id", "fail", [result()])
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "id" in str(ei.value)


def test_prompt_over_800_chars_fails(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('prompt = "Say hello."',
                                               'prompt = "%s"' % ("x" * 801)))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "prompt" in str(ei.value)


def test_vacuous_scenario_rejected_order_and_end_do_not_count(tmp_path):
    root = _root(tmp_path)
    body = """\
[scenario]
id = "sample"
title = "V"
prompt = "x"
subjects = ["core"]
mode = "plan"
fail_checks = []

[[check]]
id = "ordered"
kind = "order"
first = "^Skill evolve"
before = "requirements"

[[check]]
id = "done"
kind = "end"
disposition = "completed"
"""
    path = _put(root, "sample", body)
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "vacuous" in str(ei.value)


def test_quote_with_newline_rejected(tmp_path):
    root = _root(tmp_path)
    body = SAMPLE.replace(
        'quote = "every agent turn starts with `trace-context`"',
        'quote = "line one\\nline two"')
    path = _put(root, "sample", body)
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "newline" in str(ei.value).lower()


def test_escaped_double_quote_inside_quote_value_round_trips(tmp_path):
    root = _root(tmp_path)
    body = SAMPLE.replace(
        'quote = "every agent turn starts with `trace-context`"',
        'quote = "Bash(git commit:*)"')
    # The form authors actually type when the quote itself contains quotes:
    body = body.replace('quote = "Bash(git commit:*)"',
                        'quote = "see \\"Bash(git commit:*)\\""')
    path = _put(root, "sample", body)
    loaded = load_file(path)
    assert loaded.sources[0]["quote"] == 'see "Bash(git commit:*)"'


def test_fail_checks_must_name_existing_check_ids(tmp_path):
    root = _root(tmp_path)
    path = _put(root, "sample", SAMPLE.replace('fail_checks = ["said-hello"]',
                                               'fail_checks = ["missing"]'))
    with pytest.raises(Exception) as ei:
        load_file(path)
    assert "fail_checks" in str(ei.value)


def test_preflight_quote_missing_is_product_rule_moved(tmp_path):
    root = _root(tmp_path)
    plant_sample(root, quote_ok=False)
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    problems = preflight(root, scenario)
    assert problems and problems[0].cls == "product" and problems[0].reason == "rule_moved"


def test_preflight_missing_source_file_is_product_rule_moved(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    os.remove(os.path.join(root, "CLAUDE.md"))
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    problems = preflight(root, scenario)
    assert any(p.reason == "rule_moved" and p.cls == "product" for p in problems)


def test_preflight_reads_text_mode_so_crlf_matches(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    with open(os.path.join(root, "CLAUDE.md"), "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("every agent turn starts with `trace-context`\r\n")
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    assert preflight(root, scenario) == []


def test_editing_quoted_sentence_in_temp_copy_fails_then_restore_passes(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    path = os.path.join(root, "CLAUDE.md")
    original = open(path, encoding="utf-8").read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("the sentence is gone\n")
    assert any(p.reason == "rule_moved" for p in preflight(root, scenario))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(original)
    assert preflight(root, scenario) == []


def test_missing_subject_file_is_product_subject_missing(tmp_path):
    root = _root(tmp_path)
    body = SAMPLE.replace('subjects = ["core"]',
                          'subjects = ["agent:missing", "skill:missing", "core"]')
    _put(root, "sample", body)
    with open(os.path.join(root, "CLAUDE.md"), "w", encoding="utf-8") as fh:
        fh.write("every agent turn starts with `trace-context`\n")
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    reasons = [(p.reason, p.detail) for p in preflight(root, scenario)]
    assert ("subject_missing", "agent:missing") in reasons
    assert ("subject_missing", "skill:missing") in reasons
    os.remove(os.path.join(root, "CLAUDE.md"))
    details = [p.detail for p in preflight(root, scenario)]
    assert "core" in details


def test_empty_and_does_nothing_transcripts_fail_a_synthetic_scenario(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    assert_not_vacuous(scenario)
    empty = TranscriptView()
    nothing = TranscriptView.from_lines([result()])
    for view in (empty, nothing):
        results = grade(view, scenario.checks)
        assert any(not row["ok"] for row in results)


def test_scenario_sha256_is_newline_normalised(tmp_path):
    root = _root(tmp_path)
    plant_sample(root)
    path = os.path.join(root, "console", "evals", "scenarios", "sample.toml")
    original = open(path, "rb").read()
    open(path, "wb").write(original.replace(b"\n", b"\r\n"))
    a = load_file(path).sha256
    open(path, "wb").write(original.replace(b"\r\n", b"\n"))
    b = load_file(path).sha256
    assert a == b and len(a) == 64
