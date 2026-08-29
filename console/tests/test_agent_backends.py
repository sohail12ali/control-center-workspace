"""Backend registry.

The premise of `agents.toml` is that adding a CLI is config, not code. These
tests hold that line: argv templates, the optional-flag drop, per-transport
capability flags, and the prompt-prefix styles all have to work for a row
nobody wrote Python for.
"""

import os

import pytest

from server import agent_backends, tomlio

#: The real file this workspace ships, not a fixture. A few things can only be
#: wrong in the committed config, and are invisible to every fixture-based test.
SHIPPED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "config", "agents.toml")


class TestShippedConfig:
    """Guards against mistakes that only the real agents.toml can make."""

    def test_no_plain_key_is_swallowed_by_a_sub_table(self):
        """A key written below a `[backend.*]` header belongs to that header.

        TOML is behaving correctly and the file was wrong: `models = []` sat
        under `[backend.mode_blurbs]` on all three API rows, so it parsed as
        `mode_blurbs.models` and the shortlist could never reach the picker.
        Silent, and invisible until someone put a real model id there.
        """
        rows = tomlio.load(SHIPPED).get("backend", [])
        assert rows, "the shipped agents.toml should define backends"
        for row in rows:
            declared = set(row.get("modes", []))
            stray = set(row.get("mode_blurbs", {}) or {}) - declared
            assert not stray, (
                "backend %r: %s written after [backend.mode_blurbs], so it "
                "parsed into that sub-table instead of the backend. Move plain "
                "keys ABOVE the sub-table header." % (row.get("id"), sorted(stray)))

    def test_every_api_row_declares_its_budgets(self):
        """Not required by the loader — required by honesty.

        The Settings panel shows these numbers as this provider's limits. A row
        that omits them still works, but the template should demonstrate that
        they are per-backend rather than one global policy.
        """
        for row in tomlio.load(SHIPPED).get("backend", []):
            if row.get("transport") != "openai_api":
                continue
            for field in ("max_tool_rounds", "max_history_messages"):
                assert row.get(field), "backend %r should declare %s" % (
                    row.get("id"), field)


@pytest.fixture
def on_path(monkeypatch):
    """Pretend every configured command is installed.

    argv building resolves the command to a full path (a Windows CLI is often
    a .CMD shim that CreateProcess will not find by bare name), so a fixture
    backend has to look installed or every argv test fails on PATH lookup.
    """
    monkeypatch.setattr(agent_backends.shutil, "which",
                        lambda cmd: "/usr/bin/" + cmd)


class TestRegistry:
    def test_loads_rows_from_agents_toml(self, repo):
        assert set(agent_backends.registry(repo)) == {"alpha", "beta"}

    def test_enabled_false_row_is_absent(self, repo):
        # Not merely hidden — a disabled row must not be launchable either.
        assert "disabled-row" not in agent_backends.registry(repo)
        with pytest.raises(ValueError):
            agent_backends.get(repo, "disabled-row")

    def test_unknown_id_error_names_what_is_configured(self, repo):
        with pytest.raises(ValueError) as exc:
            agent_backends.get(repo, "ghost")
        assert "alpha" in str(exc.value) and "beta" in str(exc.value)

    def test_row_without_an_id_is_refused(self):
        with pytest.raises(ValueError):
            agent_backends.Backend({"label": "no id"})

    def test_unknown_transport_is_refused(self):
        with pytest.raises(ValueError):
            agent_backends.Backend({"id": "x", "transport": "telepathy"})

    def test_falls_back_to_legacy_console_toml(self, repo):
        """An older checkout with no agents.toml keeps working."""
        os.remove(os.path.join(repo, "console", "config", "agents.toml"))
        with open(os.path.join(repo, "console", "config", "console.toml"), "a",
                  encoding="utf-8") as fh:
            fh.write('\n[agents.backends.legacy]\n'
                     'label = "Legacy"\ncommand = "legacy-cli"\n'
                     'args = ["-p", "{prompt}"]\n')
        agent_backends._cache.clear()
        reg = agent_backends.registry(repo, force=True)
        assert reg["legacy"].transport == "oneshot"
        assert reg["legacy"].label == "Legacy"


class TestCapabilities:
    def test_stream_json_is_steerable_and_resumable(self, repo):
        b = agent_backends.get(repo, "alpha")
        assert (b.steerable, b.resumable, b.streaming) == (True, True, True)

    def test_resume_streams_and_resumes_but_cannot_steer(self, repo):
        # There is no open stdin channel, so a message can only be queued.
        b = agent_backends.get(repo, "beta")
        assert (b.steerable, b.resumable, b.streaming) == (False, True, True)

    def test_oneshot_can_do_neither(self):
        b = agent_backends.Backend({"id": "x", "transport": "oneshot"})
        assert (b.steerable, b.resumable, b.streaming) == (False, False, False)

    def test_approval_gate_only_claimed_where_the_hook_can_run(self, repo):
        # gated_tools installs a PreToolUse hook, which needs a live session.
        assert agent_backends.get(repo, "alpha").describe()["approval_gate"] is True
        beta = agent_backends.Backend({"id": "b", "transport": "resume",
                                       "gated_tools": ["Bash"]})
        assert beta.describe()["approval_gate"] is False

    def test_models_pick_up_labels_and_default_to_their_id(self, repo):
        models = {m["id"]: m for m in agent_backends.get(repo, "alpha").models}
        assert models["big"]["label"] == "Big Model"
        assert models["small"]["label"] == "small"

    def test_describe_reports_installed_state(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: None)
        assert agent_backends.get(repo, "alpha").describe()["installed"] is False


class TestArgv:
    def test_oneshot_args_win_over_session_args(self, repo, on_path):
        argv = agent_backends.get(repo, "alpha").turn_argv("do it", model="big")
        assert argv[1:] == ["-p", "do it", "--permission-mode", "plan",
                            "--model", "big"]

    def test_mode_defaults_to_the_backends_own_default(self, repo, on_path):
        argv = agent_backends.get(repo, "alpha").turn_argv("x", model="big")
        assert argv[argv.index("--permission-mode") + 1] == "plan"

    def test_an_unset_optional_flag_vanishes_with_its_value(self, repo, on_path):
        # Passing --model "" makes a CLI reject the run *after* the job record
        # exists, so the flag has to disappear entirely instead.
        argv = agent_backends.get(repo, "alpha").turn_argv("x")
        assert "--model" not in argv
        assert "--permission-mode" in argv

    def test_turn_args_used_when_there_is_no_oneshot_form(self, repo, on_path):
        argv = agent_backends.get(repo, "beta").turn_argv("hello")
        assert argv[1:] == ["-p", "hello", "--mode", "ask"]

    def test_resume_args_used_only_with_a_resume_id(self, repo, on_path):
        b = agent_backends.get(repo, "beta")
        assert "--resume" not in b.turn_argv("hi")
        argv = b.turn_argv("hi", resume_id="abc123")
        assert argv[argv.index("--resume") + 1] == "abc123"

    def test_missing_template_raises_rather_than_guessing_flags(self):
        b = agent_backends.Backend({"id": "x", "transport": "oneshot"})
        with pytest.raises(ValueError):
            b.turn_argv("x")

    def test_command_is_resolved_to_a_full_path(self, repo, on_path):
        assert agent_backends.get(repo, "alpha").turn_argv("x")[0] == "/usr/bin/alpha-cli"

    def test_session_argv_appends_one_add_dir_pair_per_directory(self, repo, on_path):
        argv = agent_backends.get(repo, "alpha").session_argv(
            model="big", add_dirs=["/a", "/b"])
        assert argv.count("--add-dir") == 2
        assert argv[-1] == "/b"

    def test_uninstalled_command_raises_before_spawning(self, repo, monkeypatch):
        monkeypatch.setattr(agent_backends.shutil, "which", lambda cmd: None)
        with pytest.raises(FileNotFoundError):
            agent_backends.get(repo, "alpha").turn_argv("x")


class TestComposePrompt:
    def test_slash_style_prefixes_persona_then_skill(self, repo):
        b = agent_backends.get(repo, "alpha")
        assert b.compose_prompt("go", skill="plan", persona="planner") == \
            "@planner /plan go"

    def test_inline_style_names_the_files_for_a_cli_without_slash_commands(self, repo):
        out = agent_backends.get(repo, "beta").compose_prompt(
            "go", skill="plan", persona="planner")
        assert ".claude/skills/plan/SKILL.md" in out
        assert ".claude/agents/planner.md" in out
        assert out.endswith("go")

    def test_none_style_passes_text_through(self):
        b = agent_backends.Backend({"id": "x", "transport": "oneshot",
                                    "prompt_prefix_style": "none"})
        assert b.compose_prompt("go", skill="plan") == "go"

    def test_bare_prompt_is_untouched_in_every_style(self, repo):
        for bid in ("alpha", "beta"):
            assert agent_backends.get(repo, bid).compose_prompt("  go  ") == "go"
