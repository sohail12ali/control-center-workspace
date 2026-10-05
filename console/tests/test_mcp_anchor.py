"""T-024 FR-3: the Claude MCP entry carries `CONSOLE_REPO_ROOT`, and an MCP
server started inside a worktree serves the MAIN repo's tickets (AC-3a/3b/3e).

AC-3d (a live Claude chat on a fresh worktree) is a manual smoke, not here.
"""

import json
import os
import subprocess
import sys

from server import setup_editor, tickets

CONSOLE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(CONSOLE_DIR)

EXPECTED_ENTRY = {
    "command": "python",
    "args": ["console/mcp_server.py"],
    "env": {"CONSOLE_REPO_ROOT": "${CONSOLE_REPO_ROOT:-}"},
}


CONTEXT_VERB = """[[verb]]
id = "context"
label = "Ticket context"
handler = "verb_handlers.ticket_context"
needs_ticket = true
"""


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_ac3a_the_committed_mcp_json_entry():
    assert _read(os.path.join(REPO, ".mcp.json"))["mcpServers"]["console"] == EXPECTED_ENTRY


class TestSetupEditorClaude:
    def test_ac3b_writes_the_committed_entry_and_is_idempotent(self, repo):
        path = os.path.join(repo, ".mcp.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"mcpServers": {"other": {"command": "x"}}}, fh)

        first = setup_editor.setup_editor(repo, "claude")
        data = _read(path)
        assert first["mcp_changed"] is True
        assert data["mcpServers"]["console"] == _read(
            os.path.join(REPO, ".mcp.json"))["mcpServers"]["console"]
        assert data["mcpServers"]["other"] == {"command": "x"}

        assert setup_editor.setup_editor(repo, "claude")["mcp_changed"] is False

    def test_ac3c_cursor_and_vscode_entries_carry_no_env(self, repo):
        setup_editor.setup_editor(repo, "cursor")
        setup_editor.setup_editor(repo, "vscode")
        cursor = _read(os.path.join(repo, ".cursor", "mcp.json"))
        vscode = _read(os.path.join(repo, ".vscode", "mcp.json"))
        assert "env" not in cursor["mcpServers"]["console"]
        assert "env" not in vscode["servers"]["console"]


class TestServerFromAWorktree:
    def test_ac3e_the_variable_points_a_worktree_started_server_at_main(self, repo, tmp_path):
        with open(os.path.join(repo, "console", "config", "verbs.toml"), "w",
                  encoding="utf-8") as fh:
            fh.write(CONTEXT_VERB)
        tickets.create(repo, "CC-T001", "Lives in main only")
        wt = str(tmp_path / "wt")  # a worktree is a full checkout: a root itself
        os.makedirs(os.path.join(wt, "knowledge-center"))
        os.makedirs(os.path.join(wt, "console"))
        call = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                           "params": {"name": "context",
                                      "arguments": {"ticket": "CC-T001"}}})
        env = dict(os.environ, CONSOLE_REPO_ROOT=repo)
        proc = subprocess.run(
            [sys.executable, os.path.join(CONSOLE_DIR, "mcp_server.py")],
            input=call + "\n", capture_output=True, text=True, cwd=wt, env=env,
            timeout=60)

        reply = json.loads(proc.stdout.strip().splitlines()[0])
        assert "Lives in main only" in reply["result"]["content"][0]["text"]
