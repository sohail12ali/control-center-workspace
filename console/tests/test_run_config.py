"""T-020 NFR-10: every Run-layer threshold comes from `console.toml` with a code
default, and a bad value falls back with one warning instead of crashing.

The `repo` fixture's console.toml gets extra sections appended, then the
loader cache is cleared, the same way the rest of the suite changes config.
"""

import os

import pytest

from server import boards, run_config

CONSOLE_TOML = os.path.join("console", "config", "console.toml")


@pytest.fixture(autouse=True)
def _fresh_warnings():
    run_config.reset_warnings()
    yield
    run_config.reset_warnings()


def _configure(repo, text):
    path = os.path.join(repo, CONSOLE_TOML)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n" + text + "\n")
    boards._console_cache.clear()


def _warnings(capsys):
    return [ln for ln in capsys.readouterr().err.splitlines() if ln.strip()]


class TestDefaults:
    def test_defaults_when_sections_absent(self, repo, capsys):
        runs = run_config.runs_cfg(repo)
        assert runs == {
            "stall_suspect_secs": 600, "stall_kill_secs": 1800,
            "watch_interval_secs": 15, "watchdog_enabled": True,
            "max_line_bytes": 1048576, "max_turn_output_bytes": 67108864,
            "linger_grace_secs": 5, "quota_parse_horizon_secs": 8 * 86400,
            "env_strip": list(run_config.DEFAULT_ENV_STRIP),
        }
        assert run_config.retry_cfg(repo) == {
            "max_total_retries": 3, "quota_max_wait_secs": 21600,
            "classes": {
                "transient_upstream": {"max": 2, "delays": [30, 120]},
                "quota": {"max": 2, "delays": [60]},
                "max_turns": {"max": 2, "delays": [1]},
                "process_lost": {"max": 1, "delays": [10]},
            },
        }
        assert run_config.claims_cfg(repo) == {"ttl_secs": 28800, "dead_grace_secs": 60}
        assert run_config.review_cfg(repo) == {"max_rounds": 3}
        assert _warnings(capsys) == []

    def test_default_env_strip_is_the_eleven_names_and_never_auth(self):
        names = run_config.DEFAULT_ENV_STRIP
        assert len(names) == 11 and len(set(names)) == 11
        for name in names:
            assert not name.startswith(("ANTHROPIC_", "CLAUDE_CODE_OAUTH_", "CLAUDE_CODE_USE_"))
        assert "CLAUDE_CODE_MAX_OUTPUT_TOKENS" not in names
        assert "CLAUDECODE" in names and "CLAUDE_CODE_MESSAGING_TOKEN" in names

    def test_results_are_copies_the_caller_may_mutate(self, repo):
        run_config.runs_cfg(repo)["env_strip"].append("X")
        run_config.retry_cfg(repo)["classes"]["quota"]["delays"].append(1)
        assert "X" not in run_config.runs_cfg(repo)["env_strip"]
        assert run_config.retry_cfg(repo)["classes"]["quota"]["delays"] == [60]

    def test_missing_or_unreadable_console_toml_gives_defaults(self, tmp_path, capsys):
        # Not a workspace at all: `clean_env()` can run with no repo root.
        root = str(tmp_path / "nowhere")
        os.makedirs(os.path.join(root, "knowledge-center"))
        os.makedirs(os.path.join(root, "console"))
        boards._console_cache.clear()
        assert run_config.runs_cfg(root)["stall_suspect_secs"] == 600
        assert len(_warnings(capsys)) == 1


class TestOverrides:
    def test_user_values_override(self, repo, capsys):
        _configure(repo, """\
[runs]
stall_suspect_secs = 100
stall_kill_secs = 200
watch_interval_secs = 5
watchdog_enabled = false
max_line_bytes = 4096
max_turn_output_bytes = 8192
linger_grace_secs = 0.2
quota_parse_horizon_secs = 3600
env_strip = ["ONE", "TWO"]

[claims]
ttl_secs = 60
dead_grace_secs = 5

[review]
max_rounds = 5
""")
        runs = run_config.runs_cfg(repo)
        assert runs["stall_suspect_secs"] == 100 and runs["stall_kill_secs"] == 200
        assert runs["watch_interval_secs"] == 5
        assert runs["watchdog_enabled"] is False
        assert runs["max_line_bytes"] == 4096 and runs["max_turn_output_bytes"] == 8192
        assert runs["linger_grace_secs"] == 0.2
        assert runs["quota_parse_horizon_secs"] == 3600
        assert runs["env_strip"] == ["ONE", "TWO"]
        assert run_config.claims_cfg(repo) == {"ttl_secs": 60, "dead_grace_secs": 5}
        assert run_config.review_cfg(repo) == {"max_rounds": 5}
        assert _warnings(capsys) == []

    def test_retry_table_nested_override(self, repo, capsys):
        _configure(repo, """\
[runs]
max_total_retries = 5

[runs.retry]
transient_upstream_delays = [5, 10, 20]
quota_max = 1
quota_max_wait_secs = 3600
process_lost_delays = [2]
""")
        retry = run_config.retry_cfg(repo)
        assert retry["max_total_retries"] == 5
        assert retry["quota_max_wait_secs"] == 3600
        assert retry["classes"]["transient_upstream"] == {"max": 2, "delays": [5, 10, 20]}
        assert retry["classes"]["quota"] == {"max": 1, "delays": [60]}
        assert retry["classes"]["process_lost"] == {"max": 1, "delays": [2]}
        assert retry["classes"]["max_turns"] == {"max": 2, "delays": [1]}
        # The nested table does not leak into, or break, the [runs] reader.
        assert run_config.runs_cfg(repo)["stall_suspect_secs"] == 600
        assert _warnings(capsys) == []

    def test_max_total_retries_zero_valid(self, repo, capsys):
        _configure(repo, "[runs]\nmax_total_retries = 0")
        assert run_config.retry_cfg(repo)["max_total_retries"] == 0
        assert _warnings(capsys) == []

    def test_claims_ttl_zero_disables_ttl(self, repo, capsys):
        _configure(repo, "[claims]\nttl_secs = 0")
        assert run_config.claims_cfg(repo)["ttl_secs"] == 0
        assert _warnings(capsys) == []

    def test_stall_kill_zero_is_valid_flag_only(self, repo, capsys):
        _configure(repo, "[runs]\nstall_kill_secs = 0")
        runs = run_config.runs_cfg(repo)
        assert runs["stall_kill_secs"] == 0 and runs["stall_suspect_secs"] == 600
        assert _warnings(capsys) == []


class TestFallback:
    def test_non_numeric_falls_back_with_exactly_one_warning(self, repo, capsys):
        _configure(repo, '[runs]\nstall_suspect_secs = "soon"')
        runs = run_config.runs_cfg(repo)
        assert runs["stall_suspect_secs"] == 600
        lines = _warnings(capsys)
        assert len(lines) == 1
        assert "stall_suspect_secs" in lines[0] and "soon" in lines[0] and "600" in lines[0]

    def test_other_bad_shapes_fall_back_too(self, repo, capsys):
        _configure(repo, """\
[runs]
watch_interval_secs = true
max_line_bytes = 1.5
max_turn_output_bytes = -4
watchdog_enabled = "yes"
linger_grace_secs = inf
""")
        runs = run_config.runs_cfg(repo)
        assert runs["watch_interval_secs"] == 15
        assert runs["max_line_bytes"] == 1048576
        assert runs["max_turn_output_bytes"] == 67108864
        assert runs["watchdog_enabled"] is True
        assert runs["linger_grace_secs"] == 5
        assert len(_warnings(capsys)) == 5

    def test_same_bad_value_warns_once_across_calls(self, repo, capsys):
        _configure(repo, '[runs]\nstall_suspect_secs = "soon"')
        for _ in range(4):
            run_config.runs_cfg(repo)
        assert len(_warnings(capsys)) == 1
        # A different bad value is a different mistake and is reported.
        _configure(repo, "[runs]\nstall_suspect_secs = \"later\"")
        run_config.reset_warnings()
        run_config.runs_cfg(repo)
        assert len(_warnings(capsys)) == 1

    def test_stall_kill_not_above_suspect_rejected_defaults_used(self, repo, capsys):
        _configure(repo, "[runs]\nstall_suspect_secs = 600\nstall_kill_secs = 600")
        runs = run_config.runs_cfg(repo)
        assert (runs["stall_suspect_secs"], runs["stall_kill_secs"]) == (600, 1800)
        lines = _warnings(capsys)
        assert len(lines) == 1 and "stall_kill_secs" in lines[0]

        _configure(repo, "[runs]\nstall_suspect_secs = 900\nstall_kill_secs = 100")
        runs = run_config.runs_cfg(repo)
        assert (runs["stall_suspect_secs"], runs["stall_kill_secs"]) == (600, 1800)

    def test_env_strip_non_list_falls_back(self, repo, capsys):
        _configure(repo, '[runs]\nenv_strip = "CLAUDECODE"')
        assert run_config.runs_cfg(repo)["env_strip"] == list(run_config.DEFAULT_ENV_STRIP)
        assert len(_warnings(capsys)) == 1

    def test_env_strip_list_of_non_names_falls_back_and_empty_list_is_valid(self, repo, capsys):
        _configure(repo, "[runs]\nenv_strip = [1, 2]")
        assert run_config.runs_cfg(repo)["env_strip"] == list(run_config.DEFAULT_ENV_STRIP)
        assert len(_warnings(capsys)) == 1

        boards._console_cache.clear()
        path = os.path.join(repo, CONSOLE_TOML)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("")  # keep the file; now replace the section below
        _configure(repo, "[claims]\nttl_secs = 1")
        # An explicit empty list means "strip nothing" and is not an error.
        text = open(path, encoding="utf-8").read().replace("env_strip = [1, 2]", "env_strip = []")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        boards._console_cache.clear()
        run_config.reset_warnings()
        assert run_config.runs_cfg(repo)["env_strip"] == []
        assert _warnings(capsys) == []

    def test_bad_retry_values_fall_back_with_a_warning_each(self, repo, capsys):
        _configure(repo, """\
[runs]
max_total_retries = -1

[runs.retry]
transient_upstream_delays = "30"
quota_max = "many"
process_lost_delays = []
quota_max_wait_secs = "later"
""")
        retry = run_config.retry_cfg(repo)
        assert retry["max_total_retries"] == 3
        assert retry["quota_max_wait_secs"] == 21600
        assert retry["classes"]["transient_upstream"]["delays"] == [30, 120]
        assert retry["classes"]["quota"]["max"] == 2
        assert retry["classes"]["process_lost"]["delays"] == [10]
        assert len(_warnings(capsys)) == 5

    def test_review_max_rounds_zero_or_non_int_falls_back_to_3(self, repo, capsys):
        _configure(repo, "[review]\nmax_rounds = 0")
        assert run_config.review_cfg(repo) == {"max_rounds": 3}
        assert len(_warnings(capsys)) == 1

        _configure(repo, '[review]\nmax_rounds = "three"')
        run_config.reset_warnings()
        assert run_config.review_cfg(repo) == {"max_rounds": 3}
        assert len(_warnings(capsys)) == 1

    def test_claims_negative_values_fall_back(self, repo, capsys):
        _configure(repo, "[claims]\nttl_secs = -5\ndead_grace_secs = \"x\"")
        assert run_config.claims_cfg(repo) == {"ttl_secs": 28800, "dead_grace_secs": 60}
        assert len(_warnings(capsys)) == 2

    def test_a_section_that_is_not_a_table_is_ignored_with_one_warning(self, repo, capsys):
        # `runs = 5` before any [section] header lands in the top level.
        path = os.path.join(repo, CONSOLE_TOML)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("runs = 5\n" + text)
        boards._console_cache.clear()
        assert run_config.runs_cfg(repo)["stall_suspect_secs"] == 600
        assert len(_warnings(capsys)) == 1


class TestNeverWrites:
    def test_module_has_no_write_path(self):
        """BR-12 / NFR-10: config is read-only to code."""
        path = os.path.join(os.path.dirname(run_config.__file__), "run_config.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        for needle in ("open(", "dump", "atomic_write", "atomic_update", "os.remove"):
            assert needle not in source, needle
