"""T-017 FR-11 (Phase 4, slice 4a) — `console setup cursor|claude|vscode`.

Writes each editor's documented MCP client config + an idempotent AGENTS.md
snippet warning against hand-editing ticket/tracker TOML.
"""

import json
import os
from types import SimpleNamespace

from server import setup_editor
import kanban


def _ns(**kw):
    return SimpleNamespace(**kw)


def _read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class TestCursor:
    def test_writes_mcp_servers_config(self, repo):
        result = setup_editor.setup_editor(repo, "cursor")
        assert result["mcp_config"] == ".cursor/mcp.json"
        data = _read_json(os.path.join(repo, ".cursor", "mcp.json"))
        assert data["mcpServers"]["console"] == {"command": "python", "args": ["console/mcp_server.py"]}

    def test_second_run_is_a_no_op(self, repo):
        setup_editor.setup_editor(repo, "cursor")
        result = setup_editor.setup_editor(repo, "cursor")
        assert result["mcp_changed"] is False
        assert result["agents_changed"] is False

    def test_preserves_an_unrelated_existing_server(self, repo):
        path = os.path.join(repo, ".cursor", "mcp.json")
        os.makedirs(os.path.dirname(path))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"mcpServers": {"other-tool": {"command": "node", "args": ["x.js"]}}}, fh)
        setup_editor.setup_editor(repo, "cursor")
        data = _read_json(path)
        assert data["mcpServers"]["other-tool"] == {"command": "node", "args": ["x.js"]}
        assert "console" in data["mcpServers"]


class TestClaude:
    def test_merges_into_existing_root_mcp_json(self, repo):
        path = os.path.join(repo, ".mcp.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"mcpServers": {"other": {"command": "x"}}}, fh)
        result = setup_editor.setup_editor(repo, "claude")
        assert result["mcp_config"] == ".mcp.json"
        data = _read_json(path)
        assert data["mcpServers"]["other"] == {"command": "x"}
        assert data["mcpServers"]["console"]["args"] == ["console/mcp_server.py"]


class TestVscode:
    def test_writes_servers_key_with_stdio_type(self, repo):
        result = setup_editor.setup_editor(repo, "vscode")
        assert result["mcp_config"] == ".vscode/mcp.json"
        data = _read_json(os.path.join(repo, ".vscode", "mcp.json"))
        assert data["servers"]["console"] == {
            "type": "stdio", "command": "python", "args": ["console/mcp_server.py"],
        }


class TestAgentsSnippet:
    def test_creates_agents_md_when_missing(self, repo):
        setup_editor.setup_editor(repo, "cursor")
        text = _read_text(os.path.join(repo, "AGENTS.md"))
        assert "do not hand-edit" in text.lower()
        assert "console/kanban.py" in text

    def test_appends_to_an_existing_agents_md_without_duplicating_on_rerun(self, repo):
        path = os.path.join(repo, "AGENTS.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Existing project notes\n\nSome pre-existing content.\n")
        setup_editor.setup_editor(repo, "cursor")
        setup_editor.setup_editor(repo, "vscode")
        text = _read_text(path)
        assert "Some pre-existing content." in text
        assert text.count(setup_editor._AGENTS_START) == 1


class TestUnknownEditor:
    def test_raises_value_error(self, repo):
        try:
            setup_editor.setup_editor(repo, "notepad")
            assert False, "expected ValueError"
        except ValueError:
            pass


class TestCliOneApi:
    def test_json_flag(self, repo, capsys):
        kanban.cmd_setup(_ns(editor="cursor", json=True), repo)
        payload = json.loads(capsys.readouterr().out)
        assert payload["editor"] == "cursor"
        assert payload["mcp_changed"] is True

    def test_plain_mode(self, repo, capsys):
        kanban.cmd_setup(_ns(editor="vscode", json=False), repo)
        out = capsys.readouterr().out
        assert "vscode" in out and ".vscode/mcp.json" in out

    def test_parser_wires_the_subcommand(self):
        parser = kanban.build_parser()
        args = parser.parse_args(["setup", "claude", "--json"])
        assert args.func is kanban.cmd_setup
        assert args.editor == "claude" and args.json is True

    def test_parser_rejects_an_unknown_editor(self):
        parser = kanban.build_parser()
        try:
            parser.parse_args(["setup", "notepad"])
            assert False, "expected SystemExit"
        except SystemExit:
            pass
