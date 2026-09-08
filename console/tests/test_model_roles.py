"""T-014: two models, two jobs.

A local 9B answers "what's open?" in about a second and is a poor engineer; a
CLI agent is the other way round. So the Assistant talks on one and hands real
work to the other. These cover the settings, the residency reporting the picker
needs, and the refusals `delegate` makes — the important one being that it never
quietly runs the task on the talk model.
"""

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import assistant_config, model_catalog, verb_handlers  # noqa: E402


class TestRoleSettings:
    def test_there_is_no_work_backend_until_you_choose_one(self, tmp_path):
        s = assistant_config.settings(str(tmp_path))
        assert s["work_backend"] == "" and s["work_model"] == ""

    def test_the_pair_round_trips(self, tmp_path):
        assistant_config.update(str(tmp_path),
                                {"work_backend": "claude", "work_model": "claude-sonnet-5"},
                                installed_backends=["claude", "lm-studio"])
        s = assistant_config.settings(str(tmp_path))
        assert (s["work_backend"], s["work_model"]) == ("claude", "claude-sonnet-5")

    def test_a_work_backend_that_is_not_installed_is_refused(self, tmp_path):
        # The same rule the talk backend has always had, applied to both.
        with pytest.raises(ValueError, match="work_backend"):
            assistant_config.update(str(tmp_path), {"work_backend": "ollama"},
                                    installed_backends=["claude"])

    def test_the_committed_file_ships_both_keys(self):
        import server.tomlio as tomlio
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        shipped = tomlio.load(os.path.join(root, "config", "assistant.toml"))["assistant"]
        for key in ("work_backend", "work_model"):
            assert shipped[key] == assistant_config.DEFAULTS[key], key


class TestResidency:
    """`loaded()` answers three different things and the UI depends on the
    difference: a set of ids, an empty set, or None for "cannot say"."""

    def test_lm_studio_shape(self):
        payload = {"models": [
            {"key": "qwen/qwen3.5-9b", "loaded_instances": [{"id": "x"}]},
            {"key": "qwen/qwen3.8-27b", "loaded_instances": []},
        ]}
        assert model_catalog._lm_studio_loaded(payload) == {"qwen/qwen3.5-9b"}

    def test_ollama_shape(self):
        assert model_catalog._ollama_loaded(
            {"models": [{"name": "qwen3:8b"}]}) == {"qwen3:8b"}

    def test_nothing_loaded_is_an_empty_set_not_none(self):
        # "nothing is resident" and "this server cannot tell me" must not
        # collapse into the same answer.
        assert model_catalog._lm_studio_loaded(
            {"models": [{"key": "a", "loaded_instances": []}]}) == set()

    def test_an_unrecognised_body_is_none(self):
        assert model_catalog._lm_studio_loaded({"nope": 1}) is None
        assert model_catalog._ollama_loaded([]) is None

    @pytest.mark.parametrize("url,host", [
        ("http://192.168.1.14:1234/v1", "http://192.168.1.14:1234"),
        ("http://127.0.0.1:11434/v1/", "http://127.0.0.1:11434"),
        ("https://api.example.com", "https://api.example.com"),
    ])
    def test_the_host_is_recovered_from_the_base_url(self, url, host):
        assert model_catalog._host_of(url) == host

    def test_a_provider_that_cannot_be_reached_says_none(self, tmp_path, monkeypatch):
        """The case that matters: a box that is asleep must not render as
        "not loaded", which would invite someone to pick a model and wait for
        a load that never starts."""
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "lan"\ntransport = "openai_api"\nenabled = true\n'
            'auth = "none"\nbase_url = "http://10.255.255.1:1234/v1"\n',
            encoding="utf-8")
        model_catalog.forget_loaded()

        def refuse(*a, **k):
            raise OSError("no route to host")

        monkeypatch.setattr(model_catalog.urllib.request, "urlopen", refuse)
        assert model_catalog.loaded(str(tmp_path), "lan") is None


class TestDelegateRefusals:
    """`delegate` starting the task on the talk model would be the worst
    outcome available — a local 9B quietly attempting a refactor. Every path
    that cannot delegate says so instead."""

    def test_an_empty_task_is_refused(self, tmp_path):
        out = verb_handlers.delegate(str(tmp_path), task="   ")
        assert out["ok"] is False and "what to delegate" in out["error"]

    def test_no_work_backend_is_refused_and_says_it_did_not_run_it(self, tmp_path):
        out = verb_handlers.delegate(str(tmp_path), task="fix the failing test")
        assert out["ok"] is False
        assert "work backend" in out["error"]
        assert "not run this on the talk model" in out["error"]

    def test_an_unknown_work_backend_is_refused(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "claude"\ntransport = "stream_json"\n', encoding="utf-8")
        assistant_config.update(str(tmp_path), {"work_backend": "nope"})
        from server import agent_backends
        agent_backends.forget_config()
        out = verb_handlers.delegate(str(tmp_path), task="do a thing")
        assert out["ok"] is False and "nope" in out["error"]


    def test_delegating_with_no_server_behind_it_is_refused(self, tmp_path):
        """Found by testing it: run from a terminal, `delegate` started a
        claude chat whose approval hook had no port to call home to, so the
        first gated tool blocked invisibly and the chat sat at `turn.start`
        forever. A refusal beats a hang."""
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "claude"\ncommand = "python"\n'
            'transport = "stream_json"\nsession_args = ["-p"]\n'
            'gated_tools = ["run_command"]\n', encoding="utf-8")
        from server import agent_backends, agent_manager
        agent_backends.forget_config()
        agent_manager.set_server_port(0)
        assistant_config.update(str(tmp_path), {"work_backend": "claude"})
        out = verb_handlers.delegate(str(tmp_path), task="do a thing")
        assert out["ok"] is False and "console server running" in out["error"]


class TestDelegateHandsOver:
    def test_it_starts_a_chat_on_the_work_backend_and_reports_where(
            self, tmp_path, monkeypatch):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "claude"\ncommand = "python"\n'
            'transport = "stream_json"\nsession_args = ["-p"]\n', encoding="utf-8")
        from server import agent_backends, agent_manager
        agent_backends.forget_config()
        assistant_config.update(str(tmp_path),
                                {"work_backend": "claude", "work_model": "sonnet"})

        seen = {}

        def fake_create(repo_root, backend_id, prompt, **kw):
            seen.update({"backend": backend_id, "prompt": prompt, **kw})
            return {"id": "chat-1", "model": kw.get("model", "")}

        agent_manager.set_server_port(8790)
        monkeypatch.setattr(agent_manager, "create", fake_create)
        out = verb_handlers.delegate(str(tmp_path), task="fix the failing test")

        assert out["ok"] is True and out["chat"] == "chat-1"
        assert seen["backend"] == "claude"
        assert seen["model"] == "sonnet"
        assert seen["prompt"] == "fix the failing test"
        # It reports where the work went and does NOT claim to have done it.
        assert "started" in out["status"]


class TestTheResultComesBack:
    def test_a_notice_lands_in_the_assistant_chat(self, monkeypatch):
        """Otherwise finding out what happened means opening the Agents tab."""
        from server import agent_manager, assistant_reply

        published = []

        class FakeStream:
            @staticmethod
            def publish(event):
                published.append(event)

        class FakeAssistant:
            id = "assistant-1"
            stream = FakeStream()

        monkeypatch.setattr(agent_manager, "get",
                            lambda sid: FakeAssistant() if sid == "assistant-1" else None)
        assistant_reply._tell_assistant(".", "assistant-1", "Finished: tests green")
        assert published and published[0]["type"] == "notice"
        assert "tests green" in published[0]["text"]

    def test_the_report_follows_the_TURN_ending_not_the_chat_dying(self, monkeypatch):
        """Found live: the delegated chat answered "24" correctly and the
        Assistant was never told, because a steerable backend keeps its
        process alive between turns and the watcher was waiting for it to die.
        """
        from server import agent_manager, assistant_reply

        told = []

        class WorkStream:
            @staticmethod
            def since(seq):
                return ([{"seq": 1, "type": "text.done", "text": "24"},
                         {"seq": 2, "type": "turn.end"}], False)

        class Work:
            id = "work-1"
            alive = True          # still alive — that is the whole point
            stream = WorkStream()

        monkeypatch.setattr(agent_manager, "get",
                            lambda sid: Work() if sid == "work-1" else None)
        monkeypatch.setattr(assistant_reply, "_tell_assistant",
                            lambda root, sid, text: told.append(text))
        assistant_reply._run_delegate(".", "work-1", "assistant-1", "count files")

        assert told, "a finished turn must be reported even though the chat lives on"
        assert "24" in told[0] and "work-1" in told[0]

    def test_it_is_quiet_when_the_assistant_chat_is_gone(self, monkeypatch):
        from server import agent_manager, assistant_reply
        monkeypatch.setattr(agent_manager, "get", lambda sid: None)
        assistant_reply._tell_assistant(".", "missing", "anything")  # must not raise


class TestDelegateIsGated:
    def test_every_api_backend_raises_a_card_for_it(self):
        """A model spending money on another model is exactly the shape of
        thing this console gates."""
        import server.tomlio as tomlio
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        rows = tomlio.load(os.path.join(root, "config", "agents.toml"))["backend"]
        for row in rows:
            if row.get("transport") == "openai_api":
                assert "console_delegate" in (row.get("gated_tools") or []), row["id"]

    def test_a_custom_provider_inherits_the_gate(self):
        from server import provider_overrides as po
        assert "console_delegate" in po.DEFAULTS_FOR_CUSTOM["gated_tools"]
