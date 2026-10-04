"""The committed starter set, against this workspace's prompt files."""

import os

import pytest

from evals.grade import TranscriptView, grade, parse_lines
from evals.runner import replay
from evals.scenario import coverage, load_dir, preflight
from evals_support import init, result

REAL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCENARIOS = os.path.join(REAL, "console", "evals", "scenarios")
FIXTURES = os.path.join(REAL, "console", "evals", "fixtures")
COVERED_SKILLS = {"trace-context", "handoff", "progress-tracker", "questions", "do", "evolve"}


def _scenarios():
    return load_dir(SCENARIOS)


@pytest.mark.parametrize("scenario", _scenarios(), ids=lambda s: s.id)
def test_real_scenarios_load_and_preflight_clean(scenario):
    assert preflight(REAL, scenario) == []


def test_real_replay_is_green_and_exit_0():
    record = replay(REAL, persist=False)
    assert record["exit"] == 0
    assert all(row["verdict"] == "pass" for row in record["scenarios"])


@pytest.mark.parametrize("scenario", _scenarios(), ids=lambda s: s.id)
def test_every_real_scenario_fails_empty_and_does_nothing_transcript(scenario):
    empty = TranscriptView()
    nothing = TranscriptView.from_lines([init(), result(result_text="")])
    for view in (empty, nothing):
        assert any(not row["ok"] for row in grade(view, scenario.checks))


@pytest.mark.parametrize("scenario", _scenarios(), ids=lambda s: s.id)
def test_must_fail_fixtures_fail_exactly_their_declared_checks(scenario):
    text = open(scenario.fixture_path("fail"), encoding="utf-8").read()
    view = parse_lines(text, strict=True)
    failed = {row["id"] for row in grade(view, scenario.checks) if not row["ok"]}
    assert failed == set(scenario.fail_checks)


@pytest.mark.parametrize("scenario", _scenarios(), ids=lambda s: s.id)
def test_each_scenario_has_a_source_a_positive_check_and_existing_subjects(scenario):
    assert scenario.sources
    assert scenario.checks
    assert preflight(REAL, scenario) == []


def test_no_committed_scenario_quotes_a_file_that_is_missing():
    for scenario in _scenarios():
        for src in scenario.sources:
            path = os.path.join(REAL, *src["file"].split("/"))
            assert os.path.isfile(path), src["file"]


def test_ten_starter_ids_present_by_membership():
    ids = {s.id for s in _scenarios()}
    assert {
        "trace-context-first", "stop-on-failed-gate", "blocker-carries-evidence",
        "no-work-exit", "never-hand-edit-ticket-toml", "no-commit-unasked",
        "post-freeze-change-uses-evolve", "deploy-is-ask-gated",
        "planner-refuses-unfrozen", "evolve-logs-before-editing",
    } <= ids


def test_at_least_twenty_fixtures():
    names = [n for n in os.listdir(FIXTURES) if n.endswith(".jsonl")]
    assert len(names) >= 20


def test_coverage_reports_7_of_7_agents_and_names_uncovered_skills():
    scenarios = _scenarios()
    cov = coverage(REAL, scenarios)
    assert len(cov["agents"]) == 7
    assert len(cov["agents_covered"]) == 7
    assert COVERED_SKILLS <= set(cov["skills_covered"])
    assert len(cov["uncovered"]) == len(cov["skills"]) - len(cov["skills_covered"])
