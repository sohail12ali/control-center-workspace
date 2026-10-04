"""The tools an API-driven agent holds.

This is the largest blast radius in the repo — a loop the console owns, holding
file writes and a shell. The confinement tests are the ones that matter, and
they are written as adversarially as the real threat: a model that is confused,
or one following an instruction embedded in a file it just read.
"""

import os

import pytest

from server import agent_tools, tickets, verbs

VERBS = """\
[[verb]]
id = "context"
label = "Ticket context"
handler = "verb_handlers.ticket_context"
needs_ticket = true

[[verb]]
id = "harness-lint"
label = "Harness lint"
handler = "verb_handlers.harness_lint_verb"
"""


def _read(root, rel):
    """Read a workspace file the way the code under test writes it.

    Bare `open(...).read()` leaks the handle and, on Windows, decodes as cp1252
    — so a test asserting on UTF-8 content could fail for the wrong reason.
    """
    with open(os.path.join(root, *rel.split("/")), encoding="utf-8") as fh:
        return fh.read()


@pytest.fixture
def ws(repo):
    with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
              encoding="utf-8") as fh:
        fh.write(VERBS)
    verbs._cache.clear()
    os.makedirs(os.path.join(repo, "src"), exist_ok=True)
    with open(os.path.join(repo, "src", "app.py"), "w", encoding="utf-8") as fh:
        fh.write("def main():\n    return 42\n")
    with open(os.path.join(repo, ".env"), "w", encoding="utf-8") as fh:
        fh.write("OPENROUTER_API_KEY=sk-secret-do-not-read\n")
    tickets.create(repo, "CC-T001", "A ticket")
    yield repo
    verbs._cache.clear()


class TestConfinement:
    @pytest.mark.parametrize("escape", [
        "../outside.txt",
        "../../etc/passwd",
        "src/../../escape.txt",
        "/etc/passwd",
        "C:/Windows/System32/drivers/etc/hosts",
    ])
    def test_reads_outside_the_workspace_are_refused(self, ws, escape):
        assert "Error" in agent_tools.dispatch(ws, "read_file", {"path": escape})

    @pytest.mark.parametrize("escape", ["../evil.txt", "../../evil.txt"])
    def test_writes_outside_the_workspace_are_refused(self, ws, escape, tmp_path):
        agent_tools.dispatch(ws, "write_file", {"path": escape, "content": "x"})
        assert not os.path.exists(os.path.join(os.path.dirname(ws), "evil.txt"))

    def test_a_symlink_pointing_outside_does_not_get_through(self, ws, tmp_path):
        # Checking the unresolved string would pass a link whose target is
        # anywhere at all.
        secret = tmp_path / "outside-secret.txt"
        secret.write_text("classified")
        link = os.path.join(ws, "innocent.txt")
        try:
            os.symlink(str(secret), link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted in this environment")
        assert "Error" in agent_tools.dispatch(ws, "read_file", {"path": "innocent.txt"})

    def test_an_empty_path_is_refused(self, ws):
        assert "Error" in agent_tools.dispatch(ws, "read_file", {"path": ""})

    def test_run_command_cwd_is_confined(self, ws):
        out = agent_tools.dispatch(ws, "run_command",
                                   {"command": "echo hi", "cwd": "../.."})
        assert "Error" in out


class TestSecretFiles:
    def test_a_dotenv_is_not_readable(self, ws):
        # The boring case: the agent reading the key it is authenticating with.
        out = agent_tools.dispatch(ws, "read_file", {"path": ".env"})
        assert "credential" in out
        assert "sk-secret" not in out

    @pytest.mark.parametrize("name", ["deploy.pem", "server.key", "credentials.json"])
    def test_other_credential_shapes_are_refused(self, ws, name):
        with open(os.path.join(ws, name), "w") as fh:
            fh.write("secret")
        assert "Error" in agent_tools.dispatch(ws, "read_file", {"path": name})

    def test_search_does_not_leak_secret_file_contents(self, ws):
        out = agent_tools.dispatch(ws, "search_files", {"query": "sk-secret"})
        assert "sk-secret-do-not-read" not in out


class TestFileTools:
    def test_read_returns_numbered_lines_and_a_header(self, ws):
        out = agent_tools.dispatch(ws, "read_file", {"path": "src/app.py"})
        assert "src/app.py (lines 1-2 of 2)" in out
        assert "def main():" in out

    def test_read_honours_a_line_range(self, ws):
        out = agent_tools.dispatch(ws, "read_file",
                                   {"path": "src/app.py", "start_line": 2, "end_line": 2})
        assert "return 42" in out and "def main" not in out

    def test_read_refuses_an_oversized_file_and_suggests_a_way_round(self, ws):
        big = os.path.join(ws, "big.txt")
        with open(big, "w") as fh:
            fh.write("x" * (agent_tools.MAX_READ_BYTES + 1))
        out = agent_tools.dispatch(ws, "read_file", {"path": "big.txt"})
        assert "search_files" in out

    def test_write_creates_parent_directories(self, ws):
        out = agent_tools.dispatch(ws, "write_file",
                                   {"path": "a/b/c.txt", "content": "hi"})
        assert "Created" in out
        assert os.path.isfile(os.path.join(ws, "a", "b", "c.txt"))

    def test_edit_replaces_a_unique_occurrence(self, ws):
        agent_tools.dispatch(ws, "edit_file",
                             {"path": "src/app.py", "find": "42", "replace": "43"})
        assert "43" in _read(ws, "src/app.py")

    def test_edit_refuses_an_ambiguous_match(self, ws):
        # A replace-all that silently hits three places is how an edit goes
        # wrong in a way nobody notices until later.
        with open(os.path.join(ws, "src", "app.py"), "w") as fh:
            fh.write("x = 1\ny = 1\n")
        out = agent_tools.dispatch(ws, "edit_file",
                                   {"path": "src/app.py", "find": "1", "replace": "2"})
        assert "appears 2 times" in out
        assert _read(ws, "src/app.py") == "x = 1\ny = 1\n"

    def test_edit_reports_a_miss_with_a_usable_hint(self, ws):
        out = agent_tools.dispatch(ws, "edit_file",
                                   {"path": "src/app.py", "find": "nope", "replace": "x"})
        assert "whitespace" in out

    def test_list_files_filters_by_glob(self, ws):
        out = agent_tools.dispatch(ws, "list_files", {"pattern": "*.py"})
        assert "src/app.py" in out
        assert "console.toml" not in out

    def test_noise_directories_are_never_walked(self, ws):
        os.makedirs(os.path.join(ws, "node_modules", "pkg"))
        with open(os.path.join(ws, "node_modules", "pkg", "index.py"), "w") as fh:
            fh.write("noise")
        assert "node_modules" not in agent_tools.dispatch(ws, "list_files", {})

    def test_the_harness_directory_stays_visible(self, ws):
        # It is hidden, but it is the project — skipping it would blind the
        # agent to its own instructions.
        os.makedirs(os.path.join(ws, ".claude", "skills", "demo"), exist_ok=True)
        with open(os.path.join(ws, ".claude", "skills", "demo", "SKILL.md"), "w") as fh:
            fh.write("# demo\n")
        assert ".claude/skills/demo/SKILL.md" in \
            agent_tools.dispatch(ws, "list_files", {"pattern": "SKILL.md"})

    def test_search_reports_file_and_line(self, ws):
        out = agent_tools.dispatch(ws, "search_files",
                                   {"query": "def main", "glob": "*.py"})
        assert "src/app.py:1:" in out

    def test_an_invalid_regex_is_explained_not_raised(self, ws):
        assert "valid regular expression" in \
            agent_tools.dispatch(ws, "search_files", {"query": "([unclosed"})


class TestRunCommand:
    def test_returns_exit_code_and_output(self, ws):
        out = agent_tools.dispatch(ws, "run_command", {"command": "echo hello"})
        assert "exit 0" in out and "hello" in out

    def test_a_failing_command_reports_its_code(self, ws):
        assert "exit 1" in agent_tools.dispatch(ws, "run_command",
                                                {"command": "exit 1"})

    def test_an_empty_command_is_refused(self, ws):
        assert "Error" in agent_tools.dispatch(ws, "run_command", {"command": "  "})


class TestVerbTools:
    def test_every_verb_is_offered_as_a_tool(self, ws):
        names = {t["function"]["name"]
                 for t in agent_tools.tool_definitions(ws)}
        assert "console_context" in names
        assert "console_harness_lint" in names

    def test_workspace_tools_are_offered_too(self, ws):
        names = {t["function"]["name"] for t in agent_tools.tool_definitions(ws)}
        assert set(agent_tools.WORKSPACE_TOOLS) <= names

    def test_verb_schemas_match_the_mcp_generator(self, ws):
        # An agent here and an agent on Claude Code must see the same
        # description of the same verb.
        from server import mcp
        tools = {t["function"]["name"]: t["function"]
                 for t in agent_tools.tool_definitions(ws)}
        verb = verbs.get(ws, "context")
        assert tools["console_context"]["parameters"] == mcp._schema_for(verb)

    def test_a_verb_tool_actually_runs_the_verb(self, ws):
        out = agent_tools.dispatch(ws, "console_context", {"ticket": "CC-T001"})
        assert "CC-T001" in out

    def test_a_verb_gate_failure_comes_back_as_readable_text(self, ws):
        out = agent_tools.dispatch(ws, "console_context", {})
        assert "requires a ticket" in out

    def test_the_prefix_keeps_verbs_from_shadowing_file_tools(self, ws):
        # A verb called `read_file` must not be able to take over the file tool.
        assert agent_tools.verb_tool_name("read_file") == "console_read_file"
        assert "console_read_file" != "read_file"


class TestDispatchContract:
    def test_an_unknown_tool_lists_what_exists(self, ws):
        out = agent_tools.dispatch(ws, "teleport", {})
        assert "No tool named" in out and "read_file" in out

    def test_wrong_arguments_come_back_as_text_not_an_exception(self, ws):
        assert "Error" in agent_tools.dispatch(ws, "read_file", {"nonsense": 1})

    def test_dispatch_never_raises(self, ws):
        # A tool that raises ends the turn; a tool that returns its error lets
        # the model correct itself.
        for name in list(agent_tools.WORKSPACE_TOOLS) + ["console_context"]:
            assert isinstance(agent_tools.dispatch(ws, name, {}), str)
