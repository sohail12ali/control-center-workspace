"""`.env` loading.

The rule worth defending above all others: **an already-exported variable
wins.** The failure it prevents is one of the nastiest to diagnose — the key
you can see in your own shell is not the key being used, and nothing says so.
"""

import os

import pytest

from server import dotenv


def write_env(root, text, name=".env"):
    path = os.path.join(root, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class TestParsing:
    def test_simple_pairs(self):
        assert dotenv.parse("A=1\nB=two\n") == {"A": "1", "B": "two"}

    def test_comments_and_blank_lines_ignored(self):
        assert dotenv.parse("# lead\n\nA=1\n\n# tail\n") == {"A": "1"}

    def test_export_prefix_is_tolerated(self):
        # People paste lines straight out of a shell script.
        assert dotenv.parse("export A=1\n") == {"A": "1"}

    def test_whitespace_around_the_equals(self):
        assert dotenv.parse("A = 1\n") == {"A": "1"}

    @pytest.mark.parametrize("line,expected", [
        ('A="quoted value"', "quoted value"),
        ("A='single quoted'", "single quoted"),
        ('A=bare value', "bare value"),
        ('A=', ""),
    ])
    def test_quoting(self, line, expected):
        assert dotenv.parse(line + "\n")["A"] == expected

    def test_an_inline_comment_ends_an_unquoted_value(self):
        assert dotenv.parse("A=1 # why\n")["A"] == "1"

    def test_a_hash_inside_quotes_is_part_of_the_value(self):
        # API keys contain punctuation; truncating one at a `#` would produce
        # a key that is wrong in a way that looks right.
        assert dotenv.parse('A="sk-a#b#c"\n')["A"] == "sk-a#b#c"

    def test_an_equals_sign_in_the_value_survives(self):
        assert dotenv.parse("A=abc=def==\n")["A"] == "abc=def=="

    def test_escapes_only_apply_inside_double_quotes(self):
        assert dotenv.parse('A="one\\ntwo"\n')["A"] == "one\ntwo"
        assert dotenv.parse("A='one\\ntwo'\n")["A"] == "one\\ntwo"

    def test_a_malformed_line_is_skipped_not_fatal(self):
        # One bad line should not cost you the other nine; a file that refuses
        # to load at all is a file people stop using.
        assert dotenv.parse("A=1\nthis is nonsense\nB=2\n") == {"A": "1", "B": "2"}

    def test_a_lowercase_or_odd_name_still_parses(self):
        assert dotenv.parse("my_var=1\n_X=2\n") == {"my_var": "1", "_X": "2"}

    def test_a_name_starting_with_a_digit_is_not_a_variable(self):
        assert dotenv.parse("1BAD=x\n") == {}


class TestLoading:
    def test_values_reach_the_environment(self, repo, monkeypatch):
        monkeypatch.delenv("DOTENV_TEST_A", raising=False)
        write_env(repo, "DOTENV_TEST_A=from-file\n")
        assert dotenv.load(repo) == ["DOTENV_TEST_A"]
        assert os.environ["DOTENV_TEST_A"] == "from-file"

    def test_an_exported_variable_always_wins(self, repo, monkeypatch):
        # The whole point. A stale file value must never shadow a deliberate
        # export, because the resulting confusion is unbounded.
        monkeypatch.setenv("DOTENV_TEST_B", "from-shell")
        write_env(repo, "DOTENV_TEST_B=from-file\n")
        assert dotenv.load(repo) == []
        assert os.environ["DOTENV_TEST_B"] == "from-shell"

    def test_override_is_available_but_not_the_default(self, repo, monkeypatch):
        monkeypatch.setenv("DOTENV_TEST_C", "from-shell")
        write_env(repo, "DOTENV_TEST_C=from-file\n")
        dotenv.load(repo, override=True)
        assert os.environ["DOTENV_TEST_C"] == "from-file"

    def test_an_empty_value_does_not_count_as_set(self, repo, monkeypatch):
        # A key left blank in .env.example should be fillable from the shell.
        monkeypatch.setenv("DOTENV_TEST_D", "")
        write_env(repo, "DOTENV_TEST_D=real-value\n")
        dotenv.load(repo)
        assert os.environ["DOTENV_TEST_D"] == "real-value"

    def test_a_missing_file_is_not_an_error(self, repo):
        assert dotenv.load(repo) == []

    def test_load_returns_names_never_values(self, repo, monkeypatch):
        # So a caller can say "loaded 2 variables" without putting a
        # credential into a terminal scrollback or a CI log.
        monkeypatch.delenv("DOTENV_TEST_E", raising=False)
        write_env(repo, "DOTENV_TEST_E=sk-super-secret\n")
        assert dotenv.load(repo) == ["DOTENV_TEST_E"]

    def test_an_unreadable_file_is_not_fatal(self, repo, monkeypatch):
        write_env(repo, "A=1\n")
        monkeypatch.setattr("builtins.open",
                            lambda *a, **k: (_ for _ in ()).throw(OSError("nope")))
        assert dotenv.load(repo) == []


class TestDescribe:
    def test_reports_names_only(self, repo):
        write_env(repo, "OPENROUTER_API_KEY=sk-secret\nTELEGRAM_CHAT_ID=123\n")
        info = dotenv.describe(repo)
        assert info["present"] is True
        assert info["names"] == ["OPENROUTER_API_KEY", "TELEGRAM_CHAT_ID"]
        assert "sk-secret" not in str(info)

    def test_absent_file(self, repo):
        info = dotenv.describe(repo)
        assert info["present"] is False and info["names"] == []

    def test_a_file_defining_nothing(self, repo):
        write_env(repo, "# just a comment\n")
        info = dotenv.describe(repo)
        assert info["present"] is True and info["names"] == []


class TestAgentCannotReadIt:
    """A key the agent authenticates with must not be readable by that agent."""

    def test_the_file_tools_refuse_dot_env(self, repo):
        from server import agent_tools
        write_env(repo, "OPENROUTER_API_KEY=sk-secret-value\n")
        out = agent_tools.dispatch(repo, "read_file", {"path": ".env"})
        assert "credential" in out
        assert "sk-secret-value" not in out

    def test_search_skips_it(self, repo):
        from server import agent_tools
        write_env(repo, "OPENROUTER_API_KEY=sk-secret-value\n")
        out = agent_tools.dispatch(repo, "search_files", {"query": "sk-secret"})
        assert "sk-secret-value" not in out

    def test_a_named_variant_is_also_refused(self, repo):
        from server import agent_tools
        write_env(repo, "X=1\n", name=".env.production")
        assert "Error" in agent_tools.dispatch(
            repo, "read_file", {"path": ".env.production"})


class TestStartupAnnouncement:
    def test_it_prints_names_and_never_values(self, repo, capsys):
        from server import httpd
        write_env(repo, "OPENROUTER_API_KEY=sk-do-not-print\n")
        httpd._announce_env(repo)
        out = capsys.readouterr().out
        assert "OPENROUTER_API_KEY" in out
        assert "sk-do-not-print" not in out

    def test_it_says_nothing_when_there_is_no_file(self, repo, capsys):
        from server import httpd
        httpd._announce_env(repo)
        assert capsys.readouterr().out == ""


class TestEndToEnd:
    """The path the user actually cares about: a key in .env makes the
    OpenRouter backend usable, without exporting anything."""

    BACKEND = """
[[backend]]
id = "openrouter"
label = "OpenRouter"
transport = "openai_api"
base_url = "https://openrouter.ai/api/v1"
api_key_env = "E2E_OR_KEY"
modes = ["default"]
default_mode = "default"
models = []
"""

    def test_a_key_in_dot_env_makes_the_backend_installed(self, repo, monkeypatch):
        from server import agent_backends
        monkeypatch.delenv("E2E_OR_KEY", raising=False)
        with open(os.path.join(repo, "console", "config", "agents.toml"), "w",
                  encoding="utf-8") as fh:
            fh.write(self.BACKEND)
        agent_backends._cache.clear()

        backend = agent_backends.get(repo, "openrouter")
        assert backend.installed is False
        assert "E2E_OR_KEY" in backend.unavailable_reason

        write_env(repo, "E2E_OR_KEY=sk-or-v1-fake\n")
        dotenv.load(repo)

        assert agent_backends.get(repo, "openrouter").installed is True
        agent_backends._cache.clear()

    def test_the_client_sends_the_key_from_dot_env(self, repo, monkeypatch):
        from server import openai_client
        monkeypatch.delenv("E2E_OR_KEY2", raising=False)
        write_env(repo, "E2E_OR_KEY2=sk-or-v1-fake\n")
        dotenv.load(repo)

        captured = {}

        def opener(request, timeout=None):
            captured["auth"] = request.headers.get("Authorization")
            import io
            return io.StringIO('data: {"choices":[]}\n\ndata: [DONE]\n')

        openai_client.Client(api_key_env="E2E_OR_KEY2").stream(
            [], model="m", opener=opener)
        assert captured["auth"] == "Bearer sk-or-v1-fake"
