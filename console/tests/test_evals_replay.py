"""Replay grades fixtures and writes a result record. It spawns nothing."""

import json
import os
import socket
import subprocess

import pytest

from evals.runner import FOOTER, RUN_FIELDS, SCENARIO_FIELDS, git_head, replay

from evals_support import (
    SAMPLE,
    assistant_text,
    init,
    plant_sample,
    result,
    write_fixture,
)


def _files(root):
    found = []
    for dirpath, _, names in os.walk(root):
        for name in names:
            found.append(os.path.relpath(os.path.join(dirpath, name), root))
    return sorted(found)


def test_replay_spawns_no_process_and_opens_no_socket(tmp_path, monkeypatch):
    root = str(tmp_path)
    plant_sample(root)

    def boom(*a, **k):
        raise AssertionError("replay spawned a process")

    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(socket, "socket", boom)
    record = replay(root, persist=False)
    assert record["exit"] == 0
    assert record["scenarios"][0]["verdict"] == "pass"


def test_golden_that_fails_is_grading_and_exit_1(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "pass", [
        init(), assistant_text("nope"), result(result_text="nope")])
    record = replay(root, persist=False)
    assert record["exit"] == 1
    row = record["scenarios"][0]
    assert row["class"] == "grading" and row["reason"] == "golden_failed"


def test_must_fail_fixture_that_passes_is_grading(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    write_fixture(os.path.join(root, "console", "evals", "fixtures"), "sample", "fail", [
        init(), assistant_text("hello"), result(result_text="hello")])
    record = replay(root, persist=False)
    assert record["exit"] == 1
    assert record["scenarios"][0]["reason"] == "must_fail_passed"
    assert record["scenarios"][0]["class"] == "grading"


def test_must_fail_fixture_must_fail_every_declared_check_id(tmp_path):
    root = str(tmp_path)
    body = SAMPLE.replace('fail_checks = ["said-hello"]',
                          'fail_checks = ["said-hello", "done"]')
    scenarios = os.path.join(root, "console", "evals", "scenarios")
    os.makedirs(scenarios, exist_ok=True)
    # done is an end/completed check. A successful fail fixture passes `done`,
    # so a declaration that the fail fixture must fail `done` is grading.
    plant_sample(root)
    path = os.path.join(scenarios, "sample.toml")
    open(path, "w", encoding="utf-8").write(body)
    record = replay(root, persist=False)
    assert record["scenarios"][0]["reason"] == "must_fail_passed"


def test_must_fail_fixture_with_torn_line_is_grading(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    path = os.path.join(root, "console", "evals", "fixtures", "sample.fail.jsonl")
    open(path, "w", encoding="utf-8").write('{"type":"assistant"\n')
    record = replay(root, persist=False)
    assert record["exit"] == 1
    assert record["scenarios"][0]["class"] == "grading"
    assert record["scenarios"][0]["reason"] == "bad_fixture"


def test_footer_states_replay_proves_graders_not_live_behaviour(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    record = replay(root, persist=False)
    assert FOOTER in record["text"]
    assert "not live agent behaviour" in record["text"]


def test_transcript_mode_grades_one_raw_transcript_without_fixture_expectations(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    path = os.path.join(root, "one.jsonl")
    write_fixture(root, "one", "pass", [])  # unused name; write the file directly
    from evals_support import dumps
    open(path, "w", encoding="utf-8").write(dumps([
        init(), assistant_text("nope"), result(result_text="nope")]))
    record = replay(root, persist=False, ids=["sample"], transcript=path)
    assert record["scenarios"][0]["verdict"] == "fail"
    assert record["scenarios"][0]["reason"] != "golden_failed"
    assert record["scenarios"][0]["class"] == "model"


def test_results_json_has_every_run_and_scenario_field(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    cache = os.path.join(root, "console", ".cache", "evals")
    record = replay(root, persist=True, cache_dir=cache)
    for field in RUN_FIELDS:
        assert field in record
    row = record["scenarios"][0]
    for field in SCENARIO_FIELDS:
        assert field in row
    saved = json.load(open(os.path.join(cache, record["run_id"], "results.json"), encoding="utf-8"))
    assert saved["run_id"] == record["run_id"]
    assert saved["grader_version"] == record["grader_version"]
    assert saved["complete"] is True
    assert saved["backend"] == "replay"


def test_results_written_only_under_cache_evals(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    before = _files(root)
    cache = os.path.join(root, "console", ".cache", "evals")
    replay(root, persist=True, cache_dir=cache)
    after = _files(root)
    new = [p for p in after if p not in before]
    assert new
    assert all(p.replace("\\", "/").startswith("console/.cache/evals/") for p in new)


def test_no_ticket_tracker_or_telemetry_file_changes(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    ticket = os.path.join(root, "knowledge-center", "artifacts", "T-1")
    os.makedirs(ticket)
    open(os.path.join(ticket, "ticket.toml"), "w", encoding="utf-8").write("id = \"T-1\"\n")
    tele = os.path.join(root, "console", ".cache", "telemetry")
    os.makedirs(tele)
    open(os.path.join(tele, "2026-10.jsonl"), "w", encoding="utf-8").write("")
    before = _files(root)
    replay(root, persist=False)
    assert _files(root) == before


def test_two_runs_get_separate_run_id_dirs(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    cache = os.path.join(root, "console", ".cache", "evals")
    a = replay(root, persist=True, cache_dir=cache)
    b = replay(root, persist=True, cache_dir=cache)
    assert a["run_id"] != b["run_id"]
    assert os.path.isdir(os.path.join(cache, a["run_id"]))
    assert os.path.isdir(os.path.join(cache, b["run_id"]))


def test_persist_false_writes_nothing(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    before = _files(root)
    replay(root, persist=False)
    assert _files(root) == before


def test_git_head_reads_dot_git_files_without_a_process(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("git_head spawned a process")

    monkeypatch.setattr(subprocess, "Popen", boom)
    loose = tmp_path / "loose"
    git = loose / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "refs" / "heads" / "main").write_text("abc1234\n", encoding="utf-8")
    assert git_head(str(loose)) == "abc1234"

    packed = tmp_path / "packed"
    git = packed / ".git"
    git.mkdir(parents=True)
    (git / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git / "packed-refs").write_text("# pack\nabc1234dead refs/heads/main\n", encoding="utf-8")
    assert git_head(str(packed)) == "abc1234dead"

    detached = tmp_path / "detached"
    git = detached / ".git"
    git.mkdir(parents=True)
    (git / "HEAD").write_text("0123456789abcdef\n", encoding="utf-8")
    assert git_head(str(detached)) == "0123456789abcdef"

    work = tmp_path / "work"
    real = tmp_path / "realgit"
    real.mkdir()
    (real / "HEAD").write_text("0123456789abcdef\n", encoding="utf-8")
    work.mkdir()
    (work / ".git").write_text("gitdir: %s\n" % real, encoding="utf-8")
    assert git_head(str(work)) == "0123456789abcdef"


def test_git_head_is_unknown_without_a_repo(tmp_path):
    assert git_head(str(tmp_path)) == "unknown"
