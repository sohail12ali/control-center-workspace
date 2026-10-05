"""evals list / replay exit codes. Never calls kanban.main (that loads .env)."""

import json
import os

import pytest

import kanban
from evals.runner import cmd

from evals_support import assistant_text, init, plant_sample, result, write_fixture


def _args(argv):
    return kanban.build_parser().parse_args(argv)


def _run(argv, root, capsys):
    with pytest.raises(SystemExit) as ei:
        cmd(_args(argv), root)
    out = capsys.readouterr().out
    return ei.value.code, out


def test_list_prints_every_scenario_id_subjects_and_mode_exit_0(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    code, out = _run(["evals", "list"], root, capsys)
    assert code == 0
    assert "sample" in out and "core" in out and "plan" in out


def test_replay_exit_0_on_healthy_set(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    code, out = _run(["evals", "replay"], root, capsys)
    assert code == 0
    assert "pass" in out


def test_replay_exit_1_when_a_golden_fixture_fails(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "pass", [
        init(), assistant_text("nope"), result(result_text="nope")])
    code, _out = _run(["evals", "replay"], root, capsys)
    assert code == 1


def test_replay_unknown_scenario_exit_2(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    code, out = _run(["evals", "replay", "--scenario", "missing"], root, capsys)
    assert code == 2
    assert "missing" in out


def test_changed_nothing_to_gate_exit_0(tmp_path, capsys, monkeypatch):
    root = str(tmp_path)
    plant_sample(root)

    def git(argv):
        return "README.md\n"

    monkeypatch.setattr("evals.scenario.changed_paths", lambda *a, **k: ["README.md"])
    code, out = _run(["evals", "replay", "--changed"], root, capsys)
    assert code == 0
    assert "nothing to gate" in out
    assert git  # the injectable path is covered in the selection tests


def test_changed_uncovered_exit_2(tmp_path, capsys, monkeypatch):
    root = str(tmp_path)
    plant_sample(root)
    monkeypatch.setattr(
        "evals.scenario.changed_paths",
        lambda *a, **k: [".claude/skills/do/SKILL.md"])
    code, out = _run(["evals", "replay", "--changed"], root, capsys)
    assert code == 2
    assert "UNCOVERED" in out


def test_json_flag_prints_the_results_record(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    code, out = _run(["evals", "replay", "--json"], root, capsys)
    assert code == 0
    payload = json.loads(out)
    assert payload["scenarios"][0]["verdict"] == "pass"
    assert "run_id" in payload


def test_output_is_ascii_even_when_evidence_excerpt_is_not(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "pass", [
        init(), assistant_text("café nope"), result(result_text="café nope")])
    code, out = _run(["evals", "replay"], root, capsys)
    assert code == 1
    out.encode("ascii")


def test_build_parser_wires_evals_list_replay_and_json():
    list_args = kanban.build_parser().parse_args(["evals", "list", "--json"])
    assert list_args.evals_cmd == "list" and list_args.json is True
    replay_args = kanban.build_parser().parse_args(["evals", "replay", "--scenario", "sample"])
    assert replay_args.evals_cmd == "replay"
    assert replay_args.scenario == ["sample"]


def test_non_pass_prints_scenario_check_class_reason_evidence(tmp_path, capsys):
    root = str(tmp_path)
    plant_sample(root)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "pass", [
        init(), assistant_text("nope"), result(result_text="nope")])
    code, out = _run(["evals", "replay"], root, capsys)
    assert code == 1
    assert "sample" in out and "said-hello" in out
    assert "grading" in out and "golden_failed" in out


def test_only_verb_handlers_imports_evals_among_server_modules():
    server = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server")
    hits = []
    for name in os.listdir(server):
        if not name.endswith(".py"):
            continue
        text = open(os.path.join(server, name), encoding="utf-8").read()
        if "import evals" in text or "from evals" in text:
            hits.append(name)
    assert hits == ["verb_handlers.py"]
