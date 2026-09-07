"""T-012: switching model providers on, and adding your own.

`agents.toml` already shipped full `ollama` and `lm-studio` rows; they sat at
`enabled = false` because a template cannot know what you run. Turning one on
meant editing a committed file that is mostly comments — which is also why the
Settings panel refuses to write it. So the choice lives in a gitignored file
beside it, and these tests are about the merge and, mostly, about the refusals.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import agent_backends, provider_overrides as po  # noqa: E402

COMMITTED = [
    {"id": "openrouter", "transport": "openai_api", "enabled": True,
     "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OR_KEY"},
    {"id": "ollama", "transport": "openai_api", "enabled": False,
     "auth": "none", "base_url": "http://127.0.0.1:11434/v1"},
    {"id": "claude", "transport": "stream_json", "enabled": True},
]


class TestMerge:
    def test_this_machine_can_switch_a_committed_row_on(self):
        rows = po.apply(COMMITTED, {"enabled": {"ollama": True}})
        assert [r for r in rows if r["id"] == "ollama"][0]["enabled"] is True
        assert [r for r in rows if r["id"] == "claude"][0]["enabled"] is True

    def test_and_off_again(self):
        rows = po.apply(COMMITTED, {"enabled": {"openrouter": False}})
        assert [r for r in rows if r["id"] == "openrouter"][0]["enabled"] is False

    def test_an_untouched_row_keeps_its_committed_answer(self):
        rows = po.apply(COMMITTED, {})
        assert [r for r in rows if r["id"] == "ollama"][0]["enabled"] is False

    def test_a_custom_row_arrives_with_the_local_defaults(self):
        rows = po.apply(COMMITTED, {"custom": [
            {"id": "mine", "label": "Mine", "base_url": "http://box:8000/v1"}]})
        mine = [r for r in rows if r["id"] == "mine"][0]
        assert mine["transport"] == "openai_api"
        assert mine["auth"] == "none", "no key named means a keyless server"
        assert "run_command" in mine["gated_tools"], (
            "a provider you added five seconds ago gets the same gate as one "
            "that shipped")
        assert mine["max_history_messages"] == 40
        assert mine["custom"] is True

    def test_naming_a_key_env_makes_it_a_key_backend(self):
        rows = po.apply(COMMITTED, {"custom": [
            {"id": "mine", "base_url": "https://api.example/v1",
             "api_key_env": "MY_KEY"}]})
        mine = [r for r in rows if r["id"] == "mine"][0]
        assert mine["auth"] == "key"
        assert mine["api_key_env"] == "MY_KEY"

    def test_a_custom_row_can_never_shadow_a_committed_one(self):
        # The committed row is the one with the comments and the review.
        rows = po.apply(COMMITTED, {"custom": [
            {"id": "ollama", "base_url": "http://evil/v1"}]})
        ollama = [r for r in rows if r["id"] == "ollama"]
        assert len(ollama) == 1
        assert ollama[0]["base_url"] == "http://127.0.0.1:11434/v1"


class TestRefusals:
    @pytest.mark.parametrize("bad", ["", "A", "no spaces", "../etc", "x" * 40,
                                     "my provider!"])
    def test_a_bad_id_is_refused(self, bad):
        with pytest.raises(ValueError, match="id must be"):
            po.validate({"id": bad, "base_url": "http://x/v1"})

    def test_a_typed_id_is_normalised_rather_than_refused(self):
        # Case and stray whitespace are a typing accident, not a mistake worth
        # an error — the id becomes a filename and a URL segment either way.
        clean = po.validate({"id": "  My-LLM  ", "base_url": "http://x/v1"})
        assert clean["id"] == "my-llm"

    def test_an_id_that_collides_with_a_shipped_row_is_refused(self):
        with pytest.raises(ValueError, match="already a provider"):
            po.validate({"id": "ollama", "base_url": "http://x/v1"},
                        committed_ids=["ollama"])

    @pytest.mark.parametrize("bad", ["", "example.com/v1", "ftp://x/v1",
                                     "file:///etc/passwd"])
    def test_a_url_that_is_not_http_is_refused(self, bad):
        with pytest.raises(ValueError, match="http"):
            po.validate({"id": "mine", "base_url": bad})

    def test_a_pasted_key_in_the_env_var_field_is_refused(self):
        """The likely mistake, and the one that matters: this project has
        never stored a secret in a file, and the refusal says what the field
        is actually for."""
        with pytest.raises(ValueError, match="NAME of an environment variable"):
            po.validate({"id": "mine", "base_url": "https://api.example/v1",
                         "api_key_env": "sk-proj-abc123def456"})

    def test_an_unknown_field_is_refused_rather_than_stored(self):
        with pytest.raises(ValueError, match="not a provider field"):
            po.validate({"id": "mine", "base_url": "http://x/v1",
                         "api_key": "sk-secret"})

    def test_an_unknown_patch_key_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="not a provider setting"):
            po.update(str(tmp_path), {"enabledd": {"ollama": True}})

    def test_enabling_something_that_does_not_exist_is_refused(self, tmp_path):
        with pytest.raises(ValueError, match="unknown provider"):
            po.update(str(tmp_path), {"enabled": {"nope": True}},
                      committed_ids=["ollama"])

    def test_only_your_own_providers_can_be_removed(self, tmp_path):
        with pytest.raises(ValueError, match="only ones you added"):
            po.update(str(tmp_path), {"remove": "ollama"},
                      committed_ids=["ollama"])


class TestPersistence:
    def test_a_choice_round_trips(self, tmp_path):
        po.update(str(tmp_path), {"enabled": {"ollama": True}},
                  committed_ids=["ollama"])
        assert po.load(str(tmp_path))["enabled"]["ollama"] is True

    def test_adding_then_editing_replaces_rather_than_duplicates(self, tmp_path):
        po.update(str(tmp_path), {"custom": {"id": "mine", "label": "One",
                                             "base_url": "http://a/v1"}})
        po.update(str(tmp_path), {"custom": {"id": "mine", "label": "Two",
                                             "base_url": "http://b/v1"}})
        stored = po.load(str(tmp_path))["custom"]
        assert len(stored) == 1 and stored[0]["label"] == "Two"

    def test_removing_forgets_its_enabled_flag_too(self, tmp_path):
        po.update(str(tmp_path), {"custom": {"id": "mine",
                                             "base_url": "http://a/v1"}})
        po.update(str(tmp_path), {"enabled": {"mine": False}})
        po.update(str(tmp_path), {"remove": "mine"})
        stored = po.load(str(tmp_path))
        assert stored["custom"] == [] and "mine" not in stored["enabled"]

    def test_a_half_wrong_patch_stores_nothing(self, tmp_path):
        po.update(str(tmp_path), {"enabled": {"ollama": True}},
                  committed_ids=["ollama"])
        with pytest.raises(ValueError):
            po.update(str(tmp_path),
                      {"custom": {"id": "ok", "base_url": "nope"}},
                      committed_ids=["ollama"])
        stored = po.load(str(tmp_path))
        assert stored["custom"] == []
        assert stored["enabled"] == {"ollama": True}, "the earlier choice stands"

    def test_a_corrupt_file_is_treated_as_no_choices(self, tmp_path):
        target = po.path(str(tmp_path))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("{not json")
        # A broken override must not take the console down: the committed rows
        # are always a working configuration.
        assert po.load(str(tmp_path)) == {"enabled": {}, "custom": []}

    def test_the_committed_file_is_never_written(self, tmp_path):
        """The whole reason this layer exists. `agents.toml` is a document —
        a TOML round-trip would delete every comment in it."""
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        committed = cfg / "agents.toml"
        original = '# a comment worth keeping\n[[backend]]\nid = "ollama"\n'
        committed.write_text(original, encoding="utf-8")
        po.update(str(tmp_path), {"enabled": {"ollama": True}},
                  committed_ids=["ollama"])
        assert committed.read_text(encoding="utf-8") == original


class TestThroughTheRegistry:
    def test_enabling_ollama_makes_it_usable(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "ollama"\ntransport = "openai_api"\n'
            'enabled = false\nauth = "none"\n'
            'base_url = "http://127.0.0.1:11434/v1"\n', encoding="utf-8")

        agent_backends.forget_config()
        assert "ollama" not in agent_backends.registry(str(tmp_path), force=True)

        po.update(str(tmp_path), {"enabled": {"ollama": True}},
                  committed_ids=["ollama"])
        agent_backends.forget_config()
        reg = agent_backends.registry(str(tmp_path), force=True)
        assert "ollama" in reg
        assert reg["ollama"].is_local, "127.0.0.1 is local"

    def test_a_custom_provider_becomes_a_real_backend(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "claude"\ntransport = "stream_json"\n',
            encoding="utf-8")
        po.update(str(tmp_path), {"custom": {
            "id": "work-vllm", "label": "vLLM (work)",
            "base_url": "http://10.0.0.5:8000/v1"}})
        agent_backends.forget_config()
        reg = agent_backends.registry(str(tmp_path), force=True)
        assert "work-vllm" in reg
        b = reg["work-vllm"]
        assert b.is_api and b.label == "vLLM (work)"
        assert b.models_url == "http://10.0.0.5:8000/v1/models"

    def test_the_provider_list_includes_the_switched_off_ones(self, tmp_path):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "ollama"\ntransport = "openai_api"\n'
            'enabled = false\nauth = "none"\n'
            'base_url = "http://127.0.0.1:11434/v1"\n', encoding="utf-8")
        agent_backends.forget_config()
        rows = agent_backends.provider_list(str(tmp_path))
        # A panel that listed only enabled providers could not be the place
        # you switch one on.
        assert [r["id"] for r in rows] == ["ollama"]
        assert rows[0]["enabled"] is False

    def test_no_key_value_ever_appears_in_the_listing(self, tmp_path, monkeypatch):
        cfg = tmp_path / "console" / "config"
        cfg.mkdir(parents=True)
        (cfg / "agents.toml").write_text(
            '[[backend]]\nid = "hosted"\ntransport = "openai_api"\n'
            'enabled = true\napi_key_env = "SECRET_KEY"\n'
            'base_url = "https://api.example/v1"\n', encoding="utf-8")
        monkeypatch.setenv("SECRET_KEY", "sk-do-not-leak")
        agent_backends.forget_config()
        rows = agent_backends.provider_list(str(tmp_path))
        blob = json.dumps(rows)
        assert "sk-do-not-leak" not in blob
        assert rows[0]["has_key"] is True and rows[0]["key_env"] == "SECRET_KEY"
