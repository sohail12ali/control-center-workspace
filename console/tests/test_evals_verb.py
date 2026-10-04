"""The one evals verb is read-only replay. Nothing in the registry can spawn claude for evals."""

import os

import pytest

from server import mcp, verbs
from server.verb_handlers import evals_replay

from evals_support import plant_sample

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_registry_resolves_evals_replay_handler():
    reg = verbs.registry(ROOT, force=True)
    assert "evals-replay" in reg
    assert reg["evals-replay"].handler.endswith("evals_replay")
    assert reg["evals-replay"].resolve() is evals_replay


def test_verb_run_returns_same_verdicts_as_cli(tmp_path, capsys):
    import kanban
    from evals.runner import cmd

    root = str(tmp_path)
    plant_sample(root)
    with pytest.raises(SystemExit) as ei:
        cmd(kanban.build_parser().parse_args(["evals", "replay"]), root)
    assert ei.value.code == 0
    capsys.readouterr()
    result = evals_replay(root)
    assert result["exit"] == 0
    assert result["verdicts"] == {"sample": "pass"}


def test_changed_string_false_is_false_and_string_true_is_true(tmp_path, monkeypatch):
    root = str(tmp_path)
    plant_sample(root)
    monkeypatch.setattr(
        "evals.scenario.changed_paths",
        lambda *a, **k: [".claude/skills/do/SKILL.md"])
    quiet = evals_replay(root, changed="false")
    assert quiet["exit"] == 0
    assert quiet["verdicts"].get("sample") == "pass"
    with pytest.raises(SystemExit) as ei:
        evals_replay(root, changed="true")
    assert ei.value.code == 2
    with pytest.raises(SystemExit) as ei:
        evals_replay(root, changed="1")
    assert ei.value.code == 2


def test_verb_list_contains_evals_replay_by_membership_not_equality():
    ids = set(verbs.registry(ROOT, force=True))
    assert {"evals-replay"} <= ids


def test_no_verb_can_spawn_claude_for_evals():
    reg = verbs.registry(ROOT, force=True)
    for verb in reg.values():
        blob = verb.id + " " + verb.handler
        if "evals" in blob:
            assert verb.id == "evals-replay"
            assert verb.needs_confirm is False


def test_mcp_tool_list_includes_evals_replay():
    names = {tool["name"] for tool in mcp.tool_list(ROOT)}
    assert "evals-replay" in names
