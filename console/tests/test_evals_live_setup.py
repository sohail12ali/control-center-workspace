"""Live refusals and argv. No real claude process."""

import os
import shutil
import subprocess

import pytest

import kanban
from server import agent_backends, agent_manager, notify, telemetry
from evals.runner import _cmd_live, build_live_command, cmd, live_plan
from evals.scenario import load_dir

from evals_support import plant_sample

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


def _guard(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("live refusal path called a side effect")

    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setattr(agent_manager, "create", boom)
    monkeypatch.setattr(telemetry, "record_turn", boom)
    monkeypatch.setattr(notify, "send", boom)


def _parse(argv):
    return kanban.build_parser().parse_args(argv)


def test_live_without_confirm_exits_2_and_fake_spawn_never_called(tmp_path, monkeypatch, capsys):
    root = _workspace(tmp_path)
    _guard(monkeypatch)
    with pytest.raises(SystemExit) as ei:
        cmd(_parse(["evals", "live", "--scenario", "sample"]), root)
    assert ei.value.code == 2
    assert "UNKNOWN until run" in capsys.readouterr().out


def test_live_with_ci_set_exits_2_even_with_confirm(tmp_path, monkeypatch, capsys):
    root = _workspace(tmp_path)
    _guard(monkeypatch)
    monkeypatch.setenv("CI", "1")
    with pytest.raises(SystemExit) as ei:
        cmd(_parse(["evals", "live", "--scenario", "sample", "--confirm"]), root)
    assert ei.value.code == 2
    assert "CI" in capsys.readouterr().out


def test_ci_zero_or_false_does_not_count_as_ci(tmp_path, monkeypatch):
    from evals_support import FakeProc, assistant_text, dumps, init, result
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    called = []
    lines = dumps([init(), assistant_text("hello"), result(result_text="hello")]).splitlines()

    def spawn(*_a, **_k):
        called.append(True)
        return FakeProc(lines)

    for value in ("0", "false"):
        called.clear()
        monkeypatch.setenv("CI", value)
        code, text = _cmd_live(
            _parse(["evals", "live", "--scenario", "sample", "--confirm"]), root, spawn=spawn)
        assert "CI is set" not in text
        assert called, value
        assert code == 0


def test_live_without_selector_or_all_exits_2(tmp_path, monkeypatch, capsys):
    root = _workspace(tmp_path)
    _guard(monkeypatch)
    with pytest.raises(SystemExit) as ei:
        cmd(_parse(["evals", "live", "--confirm"]), root)
    assert ei.value.code == 2
    assert "selector" in capsys.readouterr().out


def test_live_preflight_failure_exits_2_before_spawn(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    _guard(monkeypatch)
    open(os.path.join(root, "CLAUDE.md"), "w", encoding="utf-8").write("gone\n")
    code, text = _cmd_live(
        _parse(["evals", "live", "--scenario", "sample", "--confirm"]), root, spawn=subprocess.Popen)
    assert code == 2
    assert "refused" in text


def test_session_argv_called_with_mode_plan_only(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    backend = agent_backends.get(root, "claude")
    seen = []
    real = agent_backends.Backend.session_argv

    def spy(self, **kw):
        seen.append(kw.get("mode"))
        return real(self, **kw)

    monkeypatch.setattr(agent_backends.Backend, "session_argv", spy)
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    build_live_command(backend, scenario, repo_root=root)
    assert seen == ["plan"]


def test_scenario_cannot_request_another_mode(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    path = os.path.join(root, "console", "evals", "scenarios", "sample.toml")
    text = open(path, encoding="utf-8").read().replace('mode = "plan"', 'mode = "bypass"')
    open(path, "w", encoding="utf-8").write(text)
    with pytest.raises(Exception):
        load_dir(os.path.join(root, "console", "evals", "scenarios"))
    backend = agent_backends.get(root, "claude")
    from evals.scenario import load_file
    open(path, "w", encoding="utf-8").write(text.replace('mode = "bypass"', 'mode = "plan"'))
    scenario = load_file(path)
    argv, _prompt = build_live_command(backend, scenario, repo_root=root)
    assert argv[argv.index("--permission-mode") + 1] == "plan"


def test_argv_carries_permission_mode_plan_agent_and_max_budget_default_0_50(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    backend = agent_backends.get(root, "claude")
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    argv, _prompt = build_live_command(backend, scenario, repo_root=root)
    assert "--permission-mode" in argv and argv[argv.index("--permission-mode") + 1] == "plan"
    assert "--agent" in argv
    assert argv[-2:] == ["--max-budget-usd", "0.5"]


def test_model_flag_passed_through_and_omitted_when_empty(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    backend = agent_backends.get(root, "claude")
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    empty, _p = build_live_command(backend, scenario, model="", repo_root=root)
    assert "--model" not in empty
    named, _p = build_live_command(backend, scenario, model="opus", repo_root=root)
    assert named[named.index("--model") + 1] == "opus"


def test_prompt_built_by_compose_prompt_with_skill_and_persona(tmp_path, monkeypatch):
    root = _workspace(tmp_path)
    monkeypatch.setattr(agent_backends.shutil, "which", lambda c: "C:/fake/" + c)
    backend = agent_backends.get(root, "claude")
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    seen = {}
    real = agent_backends.Backend.compose_prompt

    def spy(self, text, skill="", persona="", repo_root=None):
        seen["call"] = (text, skill, persona, repo_root)
        return real(self, text, skill, persona, repo_root)

    monkeypatch.setattr(agent_backends.Backend, "compose_prompt", spy)
    _argv, prompt = build_live_command(backend, scenario, repo_root=root)
    assert seen["call"][0] == scenario.prompt
    assert seen["call"][2] == scenario.persona
    assert seen["call"][3] == root
    assert prompt


def test_plan_print_says_cost_unknown_until_run(tmp_path):
    root = _workspace(tmp_path)
    scenario = load_dir(os.path.join(root, "console", "evals", "scenarios"))[0]
    text = live_plan([scenario])
    assert "cost: UNKNOWN until run" in text
    assert "180 s" in text and "25 calls" in text


def test_non_stream_json_backend_refused(tmp_path, monkeypatch):
    root = _workspace(tmp_path)

    class Resume:
        transport = "resume"

    monkeypatch.setattr(agent_backends, "get", lambda *_a, **_k: Resume())
    called = []
    code, text = _cmd_live(
        _parse(["evals", "live", "--scenario", "sample", "--confirm"]),
        root, spawn=lambda *a, **k: called.append(1))
    assert code == 2
    assert "stream_json" in text
    assert called == []
