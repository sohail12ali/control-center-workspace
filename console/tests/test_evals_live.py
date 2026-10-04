"""Live driver, exercised only through a fake spawn. Never starts claude."""

import json
import os
import shutil
import threading

from server import agent_backends, agent_manager, audit, notify, procs, telemetry
from evals.grade import grade, parse_lines
from evals.runner import run_live
from evals.scenario import load_dir

from evals_support import FakeProc, assistant_text, dumps, init, plant_sample, result

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _workspace(tmp_path):
    root = str(tmp_path)
    plant_sample(root)
    os.makedirs(os.path.join(root, "console", "config"), exist_ok=True)
    shutil.copyfile(
        os.path.join(ROOT, "console", "config", "agents.toml"),
        os.path.join(root, "console", "config", "agents.toml"))
    with open(os.path.join(root, "console", "config", "console.toml"), "w", encoding="utf-8") as fh:
        fh.write('[general]\ndata_root = "knowledge-center/artifacts"\n')
    agent_backends._cache.clear()
    return root


def _on_path(monkeypatch):
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)


def _scenario(root):
    return load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]


def _lines(*events):
    return dumps(list(events)).splitlines()


def _spawn_factory(lines, **proc_kw):
    seen = []

    def spawn(argv, **kw):
        proc = FakeProc(lines, **proc_kw)
        proc.args = argv
        proc.kwargs = kw
        seen.append(proc)
        return proc

    spawn.seen = seen
    return spawn


def _guard(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("live path touched a chat, a turn record, or a notification")

    monkeypatch.setattr(agent_manager, "create", boom)
    monkeypatch.setattr(telemetry, "record_turn", boom)
    monkeypatch.setattr(notify, "send", boom)


def test_fake_spawn_replaying_fixture_is_graded_exactly_as_replay_and_record_mode_is_live(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    _guard(monkeypatch)
    scenario = _scenario(root)
    events = [init(), assistant_text("hello there"), result(result_text="hello there")]
    spawn = _spawn_factory(_lines(*events))
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    view = parse_lines(dumps(events), strict=True)
    offline = grade(view, scenario.checks)
    assert record["scenarios"][0]["mode"] == "live"
    assert [c["ok"] for c in record["scenarios"][0]["checks"]] == [c["ok"] for c in offline]
    assert record["scenarios"][0]["verdict"] == "pass"


def test_live_path_never_calls_agent_manager_create_record_turn_or_notify_send(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    _guard(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello"), result(result_text="hello")))
    run_live(root, [scenario], spawn=spawn, env={}, timeout=2)


def test_live_creates_no_worktree_run_or_chat_entry(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello"), result(result_text="hello")))
    run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    assert not os.path.isdir(os.path.join(root, "console", ".cache", "agent-chats"))
    assert not os.path.isdir(os.path.join(root, "console", ".cache", "runs"))
    assert not os.path.isdir(os.path.join(root, "worktrees"))
    tele = os.path.join(root, "console", ".cache", "telemetry")
    assert not os.path.isdir(tele)


def test_process_that_never_emits_result_is_terminated_at_timeout_as_infra_timeout(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory([], block=True)
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=0.2, stop_grace=0.05)
    row = record["scenarios"][0]
    assert row["class"] == "infra" and row["reason"] == "timeout"


def test_tool_calls_over_cap_terminate_as_model_tool_cap(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    scenario.max_tool_calls = 1
    from evals_support import assistant_tool
    events = [
        assistant_tool("Bash", {"command": "one"}, "a"),
        assistant_tool("Bash", {"command": "two"}, "b"),
        assistant_text("hello"),
    ]
    spawn = _spawn_factory(_lines(*events), block=True)
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2, stop_grace=0.05)
    row = record["scenarios"][0]
    assert row["class"] == "model" and row["reason"] == "tool_cap"


def test_spawn_oserror_is_infra_spawn_error(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)

    def spawn(*_a, **_k):
        raise OSError("nope")

    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    assert record["scenarios"][0]["class"] == "infra"
    assert record["scenarios"][0]["reason"] == "spawn_error"


def test_claude_not_on_path_is_infra_spawn_error(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda _c: None)
    scenario = _scenario(root)
    called = []
    record = run_live(root, [scenario], spawn=lambda *a, **k: called.append(1), env={}, timeout=2)
    assert called == []
    assert record["scenarios"][0]["reason"] == "spawn_error"
    assert record["scenarios"][0]["class"] == "infra"


def test_spawn_receives_no_window_creationflags_pipes_and_one_user_json_line(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello"), result(result_text="hello")))
    run_live(root, [scenario], spawn=spawn, env={"PLAIN": "1"}, timeout=2)
    proc = spawn.seen[0]
    import subprocess
    assert proc.kwargs["creationflags"] == procs.no_window_flags(
        getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    assert proc.kwargs["stdin"] is subprocess.PIPE
    assert proc.kwargs["stdout"] is subprocess.PIPE
    assert proc.kwargs["stderr"] is subprocess.STDOUT
    assert len(proc.stdin.buf) == 1
    payload = json.loads(proc.stdin.buf[0])
    assert payload["type"] == "user"
    assert payload["message"]["content"][0]["type"] == "text"


def test_end_closes_stdin_then_terminates_then_kills_after_grace(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    monkeypatch.setattr(procs, "kill_tree", None)
    scenario = _scenario(root)
    spawn = _spawn_factory([], block=True, ignore_terminate=True)
    run_live(root, [scenario], spawn=spawn, env={}, timeout=0.2, stop_grace=0.05)
    proc = spawn.seen[0]
    assert proc.stdin.closed is True
    assert proc.calls == ["terminate", "kill"]


def test_stop_uses_kill_tree_when_procs_provides_it(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    seen = []

    def killer(proc, grace):
        seen.append(grace)
        proc.returncode = 1

    monkeypatch.setattr(procs, "kill_tree", killer)
    scenario = _scenario(root)
    spawn = _spawn_factory([], block=True)
    run_live(root, [scenario], spawn=spawn, env={}, timeout=0.2, stop_grace=0.05)
    assert seen and seen[0] == 0.05
    assert spawn.seen[0].calls == []


def test_behaviour_failure_is_scored_not_retried_one_spawn_per_scenario(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory(_lines(init(), assistant_text("nope"), result(result_text="nope")))
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    assert len(spawn.seen) == 1
    assert record["scenarios"][0]["verdict"] == "fail"
    assert record["scenarios"][0]["class"] == "model"


def test_usage_unknown_without_result_usage_and_known_when_reported(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    bare = result(result_text="hello")
    bare.pop("usage", None)
    bare.pop("total_cost_usd", None)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello"), bare))
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    assert record["scenarios"][0]["usage"]["render"] == "UNKNOWN"
    known = result(result_text="hello", usage={"input_tokens": 4, "output_tokens": 5},
                   total_cost_usd=0)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello"), known))
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    usage = record["scenarios"][0]["usage"]
    assert usage["input_tokens"] == 4 and usage["output_tokens"] == 5
    assert usage["cost_usd"] == 0 and usage["cost_source"] == "backend"


def test_exactly_one_evals_live_audit_record_without_transcript_text(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    spawn = _spawn_factory(_lines(init(), assistant_text("hello there"), result(result_text="hello there")))
    record = run_live(root, [scenario], spawn=spawn, env={}, timeout=2)
    folder = audit.audit_dir(root)
    lines = []
    for name in os.listdir(folder):
        if name.endswith(".jsonl"):
            lines.extend(open(os.path.join(folder, name), encoding="utf-8").read().splitlines())
    hits = [json.loads(line) for line in lines if line.strip()]
    live = [h for h in hits if h.get("action") == "evals.live"]
    assert len(live) == 1
    blob = json.dumps(live[0]["detail"])
    assert "hello there" not in blob
    assert live[0]["detail"]["run_id"] == record["run_id"]
    assert live[0]["detail"]["backend"] == "claude"


def test_raw_transcript_written_only_under_the_run_dir(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    before = set()
    for dirpath, _, names in os.walk(root):
        for name in names:
            before.add(os.path.join(dirpath, name))
    record = run_live(root, [scenario], spawn=_spawn_factory(
        _lines(init(), assistant_text("hello"), result(result_text="hello"))), env={}, timeout=2)
    new = []
    for dirpath, _, names in os.walk(root):
        for name in names:
            path = os.path.join(dirpath, name)
            if path not in before:
                new.append(path)
    run_dir = os.path.join(root, "console", ".cache", "evals", record["run_id"])
    transcripts = [p for p in new if p.endswith(".raw.jsonl")]
    assert len(transcripts) == 1
    assert os.path.dirname(transcripts[0]) == run_dir
    assert any(p.endswith("results.json") and os.path.dirname(p) == run_dir for p in new)


def test_concurrent_runs_get_separate_run_id_dirs(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _on_path(monkeypatch)
    scenario = _scenario(root)
    found = []

    def once():
        spawn = _spawn_factory(_lines(init(), assistant_text("hello"), result(result_text="hello")))
        found.append(run_live(root, [scenario], spawn=spawn, env={}, timeout=2)["run_id"])

    threads = [threading.Thread(target=once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(set(found)) == 2
    cache = os.path.join(root, "console", ".cache", "evals")
    assert all(os.path.isdir(os.path.join(cache, rid)) for rid in found)
